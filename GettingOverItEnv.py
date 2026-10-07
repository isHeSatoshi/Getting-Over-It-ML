"""
PMDP config for "Getting Over It" (Scratch remake id 389464290).
The real goal: reach PLAYER Y == 16000 (summit). Start altitude is y=21.
"""

import os
import sys
import time
import math
import json
import subprocess
from typing import Optional, Dict, Any

import numpy as np
import gymnasium as gym
from gymnasium import spaces

# High-speed Node.js Physics Server bridge import
try:
    from vm_bridge.node_bridge import NodeBridge
    _HAVE_NODE = True
except Exception:
    _HAVE_NODE = False

# Selenium bridge imports (fallback)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.options import Options
    os.environ.setdefault('WDM_SSL_VERIFY', '0')
    _HAVE_SELENIUM = True
except Exception:
    _HAVE_SELENIUM = False

from StaticCollisionMap import StaticCollisionMap


# ----------------------------------------------------------------------------
# PMDP config — the knobs that define "progress-asymmetry" for this domain.
# These are read by both the env (reward) and the trainer (value shaping).
#
# ML-researcher notes on the redesign (2026-08-05):
#   * Phi(s) = Y_rel = Y_t - Y_spawn.  Phi(s_spawn) = 0.  Camping at
#     spawn now yields zero shaping reward (was +2.65/frame at Y=-264).
#   * Terminal falls detected via the game's own respawn (huge Y drop in
#     one k_frames window), not by absolute altitude.  The physics bridge
#     never lets the agent leave the world: when the body hits the water,
#     Scratch auto-respawns the player.  Reward must reflect that.
#   * Milestone bonus replaces the absolute-Y potential as the dominant
#     shaping signal.  Each new high adds a fixed positive reward.  This
#     gives PPO an explorable gradient the whole way to summit (16,000).
#   * Hammer-placement alignment bonus uses raycast normals of ledges
#     above the player.  Rewards pointing the hammer at overhead
#     hookable surfaces — the actual skill the game demands.
#   * Stalled truncation based on *episode-local* high; episode variable
#     reset EVERY reset() call.
# ----------------------------------------------------------------------------
PMDP_CONFIG = {
    "gamma": 0.99,                     # discount for potential-based shaping

    # ---- Potential (zero-based; centered at spawn) ----
    "potential_scale": 0.01,           # 1 unit of Y_rel -> 0.01 potential.

    # ---- Per-frame shaping ----
    "time_penalty_per_frame": -0.01,
    "contact_bonus_per_frame": 0.002,

    # ---- New-high milestone (per k_frames decision chunk) ----
    # Reward paid only the FIRST time a new episode high is crossed.
    # Scale: 1 unit of gain -> milestone_scale reward.  At the start,
    # climbing from ground to first ledge is +50 -> +0.5 reward.
    "milestone_scale": 0.5,            # big lump-sum for each new unit of high

    # ---- Hammer-placement alignment ----
    # Look up; if a ledge exists with sufficient clearance above, reward
    # pointing the hammer roughly toward it.  This is the actual
    # "hook-up" skill the game requires.
    "hook_bonus_per_frame": 0.02,      # active only when aligned
    "hook_align_cos_min": 0.5,         # cos(angle) >= 0.5 (within 60 deg)

    # ---- Action smoothness (gentle; LSTMs shouldn't jitter) ----
    "smooth_penalty_scale": 0.005,

    # ---- Success / termination ----
    "success_y": 16000.0,
    "success_bonus": 100.0,

    # The game world physically respawns the player on water contact
    # (PLAYER Y drops to ~-264.7 from any height).  Detect terminal falls
    # by a large negative Y-jump within one k_frames window.
    "respawn_drop_threshold": 100.0,   # Y dropped >100 in one decision
    "respawn_penalty": -5.0,           # explicit, learnable cost

    # Stalled truncation: episode-local high hasn't moved in N frames.
    # 300 frames @ 60fps = 5 seconds of game time — enough to attempt one
    # swing but short enough that exploration doesn't get permanently
    # stuck at a local plateau.
    "stall_frame_budget": 300,
}


# ============================================================================
# Selenium bridge — visible Chrome via TurboWarp scaffolding. Slow but
# debuggable. Used for Phase-1 verification only.
# ============================================================================
class SeleniumBridge:
    """Frame-synchronized bridge to the TurboWarp Scratch game in Chrome.

    Contract with index.html:
      - window.nextCommand = { command_id, screen_x, screen_y, is_down }
        The patched _step sets mouse._scratchX = screen_x, _scratchY = screen_y.
      - window.stateHistory[frameId] holds per-frame telemetry; the latest
        entry has command_id_applied == the id we just sent.
    """

    def __init__(self, port: int, headless: bool = True, driver_path: Optional[str] = None,
                 log_file=None):
        self.port = port
        self.headless = headless
        self.driver_path = driver_path
        self.log_file = log_file
        self.driver = None
        self.server_process = None
        self.server_log_file = None
        self._start_server()
        self._setup_selenium()

    def _log(self, msg):
        print(msg)
        sys.stdout.flush()
        if self.log_file:
            try:
                self.log_file.write(msg + "\n")
                self.log_file.flush()
            except Exception:
                pass

    def _start_server(self):
        self._log(f"🚀 Starting game server on port {self.port}...")
        server_script = os.path.join(os.path.dirname(__file__), "threading_server.py")
        game_dir = os.path.join(os.path.dirname(__file__), "Getting Over It v1")
        log_path = os.path.join(os.path.dirname(__file__), f"server_{self.port}.log")
        self.server_log_file = open(log_path, "w")
        self.server_process = subprocess.Popen(
            [sys.executable, server_script, str(self.port), game_dir],
            stdout=self.server_log_file, stderr=self.server_log_file,
        )
        time.sleep(2.0)

    def _is_alive(self):
        try:
            if self.driver:
                _ = self.driver.title
                return True
        except Exception:
            pass
        return False

    def _setup_selenium(self):
        self._log("Launching Selenium Chrome...")
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
        debugging_port = 9220 + (self.port - 8000)
        chrome_options.add_argument(f"--remote-debugging-port={debugging_port}")
        user_data_path = os.path.join(os.path.dirname(__file__), "chrome_profiles", f"profile_{self.port}")
        os.makedirs(user_data_path, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={user_data_path}")
        if self.headless:
            chrome_options.add_argument("--headless=new")

        if self.driver_path:
            service = Service(executable_path=self.driver_path)
        else:
            service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_window_size(1280, 720)
        self.driver.get(f"http://127.0.0.1:{self.port}")
        time.sleep(2.0)
        self.driver.execute_script("if (window.vm) { window.vm.runtime.start(); }")
        # Wait for project + New Game auto-start
        start_t = time.time()
        while time.time() - start_t < 30.0:
            try:
                n = self.driver.execute_script("return window.vm ? window.vm.runtime.targets.length : 0;")
                if n > 5:
                    self._log(f"Project loaded: {n} targets.")
                    break
            except Exception:
                pass
            time.sleep(0.5)

    def reset(self):
        if not self._is_alive():
            self._log("🚨 Driver dead, re-launching...")
            self._setup_selenium()
        self.driver.execute_script(
            "window.nextCommand=null; window.lastAppliedCommandId=-1;"
            "window.stateHistory={}; window.frameCounter=0; window.isResetting=true;"
            "if (window.resetGame) { window.resetGame(); }"
        )
        time.sleep(2.0)
        # Poll for a valid state
        start_t = time.time()
        state = None
        while time.time() - start_t < 30.0:
            state = self.read_state()
            if state and state.get("player_world_y") is not None:
                break
            time.sleep(0.1)
        self.driver.execute_script("window.isResetting = false;")
        return state

    def read_state(self):
        if not self._is_alive():
            return None
        try:
            return self.driver.execute_script(
                "var h = window.stateHistory; if (!h) return null;"
                "var keys = Object.keys(h); if (keys.length === 0) return null;"
                "var maxK = keys[0];"
                "for (var i = 1; i < keys.length; i++) { if (parseInt(keys[i]) > parseInt(maxK)) maxK = keys[i]; }"
                "var latest = h[maxK];"
                "if (keys.length > 5) { for (var j = 0; j < keys.length; j++) { if (keys[j] !== maxK) delete h[keys[j]]; } }"
                "return latest;"
            )
        except Exception:
            return None

    def step_screen_pointer(self, command_id: int, screen_x: float, screen_y: float,
                            is_down: bool = True, timeout: float = 1.0):
        """Inject one pointer command and block until the VM applies it."""
        if not self._is_alive():
            return None
        js = (
            f"window.nextCommand = {{ command_id: {int(command_id)}, "
            f"screen_x: {float(screen_x):.4f}, screen_y: {float(screen_y):.4f}, "
            f"is_down: {'true' if is_down else 'false'} }};"
        )
        self.driver.execute_script(js)
        return self._wait_applied(command_id, timeout)

    def _wait_applied(self, command_id: int, timeout: float = 1.0):
        start_t = time.time()
        while time.time() - start_t < timeout:
            state = self.read_state()
            if state and state.get("command_id_applied") == command_id:
                return state
            time.sleep(0.002)
        return self.read_state()

    def screenshot(self, path: str):
        if self._is_alive():
            try:
                self.driver.save_screenshot(path)
            except Exception:
                pass

    def execute_js(self, script):
        if self._is_alive():
            return self.driver.execute_script(script)
        return None

    def close(self):
        self._log("Closing bridge...")
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except Exception:
                pass
        for f in (self.server_log_file, self.log_file):
            if f:
                try:
                    f.close()
                except Exception:
                    pass
        self._log("✅ Bridge closed.")


# ============================================================================
# Environment
# ============================================================================
class GettingOverItEnv(gym.Env):
    """Gymnasium env over any bridge implementing the SeleniumBridge interface."""

    metadata = {"render_modes": ["human"]}

    # Scratch stage extent (for normalizing screen pointer).
    STAGE_W = 480.0
    STAGE_H = 360.0
    STAGE_HALF_W = 240.0
    STAGE_HALF_H = 180.0

    def __init__(self, bridge=None, port=8000, headless=True, driver_path=None,
                 k_frames=4, render_every=0, pmdp_cfg=None, port_for_log=None):
        if bridge is None:
            raise RuntimeError(
                "Legacy backends are unvalidated (Node has no collisions; browser stepping is asynchronous). "
                "Use research.env.RealGettingOverItEnv. Injected legacy bridges are forensic-only."
            )
        super().__init__()
        self.k_frames = int(k_frames)
        self.render_every = int(render_every)
        self.cfg = dict(PMDP_CONFIG)
        if pmdp_cfg:
            self.cfg.update(pmdp_cfg)

        # Action: normalized screen pointer target in [-1,1]^2
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)

        # Observation: 200-dim (base 20 + one-hot 12 + rays 128 + ledges 40).
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(200,), dtype=np.float32)

        # State tracking
        self.prev_state: Optional[Dict[str, Any]] = None
        self.prev_potential = 0.0                       # potential at last step
        self.spawn_y = 0.0                              # Y at episode start
        self.start_y = 0.0                              # kept for info dict
        self.episode_high_y = 0.0                       # episode-local high
        self.max_progress = 0.0                         # legacy alias -> info
        self.steps_since_new_high = 0
        self.total_steps = 0
        self.decision_idx = 0
        self.last_command_id = 0
        self.prior_action = np.zeros(2, dtype=np.float32)
        # Cache for terrain descriptor — recomputed ONCE per decision,
        # not per frame.  StaticCollisionMap.raycast is expensive
        # (16 rays x binary search x pixel lookups), so caching it
        # matters on a hot path.
        self._terrain_cache: Optional[tuple] = None     # (rays, ledges)
        self._render_mode = "human" if render_every > 0 else None

        log_port = port_for_log if port_for_log is not None else port
        self.log_file = open(
            os.path.join(os.path.dirname(__file__), f"env_{log_port}.log"),
            "w", encoding="utf-8"
        )

        # Bridge: inject one for tests; default to NodeBridge if available.
        if bridge is not None:
            self.bridge = bridge
            self._owns_bridge = False
        else:
            bridge_type = self.cfg.get("bridge_type", "node")
            if bridge_type == "node" and _HAVE_NODE:
                self.bridge = NodeBridge(port=port, headless=headless, log_file=self.log_file)
                self._owns_bridge = True
            elif _HAVE_SELENIUM:
                self.bridge = SeleniumBridge(port=port, headless=headless,
                                             driver_path=driver_path, log_file=self.log_file)
                self._owns_bridge = True
            elif _HAVE_NODE:
                self.bridge = NodeBridge(port=port, headless=headless, log_file=self.log_file)
                self._owns_bridge = True
            else:
                raise RuntimeError("Neither NodeBridge nor SeleniumBridge is available.")

        # Static terrain map (used for ray/ledge obs). The synthetic PMDP env
        # does not need it; guard against missing game dir.
        game_dir = os.path.join(os.path.dirname(__file__), "Getting Over It v1")
        if os.path.exists(os.path.join(game_dir, "assets", "project.json")):
            try:
                self.collision_map = StaticCollisionMap(game_dir)
            except Exception as exc:
                self._log(f"⚠️ StaticCollisionMap init failed: {exc}; rays will be zero.")
                self.collision_map = None
        else:
            self.collision_map = None

    def _log(self, msg):
        print(msg)
        sys.stdout.flush()
        if self.log_file:
            try:
                self.log_file.write(msg + "\n")
                self.log_file.flush()
            except Exception:
                pass

    # ------------------------------------------------------------------ utils
    def _get_obs(self, state):
        if state is None:
            return np.zeros(200, dtype=np.float32)
        px = float(state.get('player_world_x', 0.0))
        py = float(state.get('player_world_y', 0.0))
        pvx = float(state.get('player_vx', 0.0))
        pvy = float(state.get('player_vy', 0.0))
        hx = float(state.get('hammer_world_x', 0.0))
        hy = float(state.get('hammer_world_y', 0.0))
        hvx = float(state.get('hammer_vx', 0.0))
        hvy = float(state.get('hammer_vy', 0.0))
        hammer_angle = float(state.get('hammer_angle', 0.0))
        hammer_ang_vel = float(state.get('hammer_angular_velocity', 0.0))
        # Convert Scratch direction (0=up, 90=right) to std radians (0=right).
        rad = math.radians(90 - hammer_angle)
        sin_theta = math.sin(rad)
        cos_theta = math.cos(rad)

        player_touch = float(state.get('contact_flag', 0.0))
        head_touch = 1.0 if state.get('contact_point', [0])[0] != 0 else 0.0
        limbs_touch = 0.0  # not separately exposed in current bridge
        contact_age = float(state.get('contact_age', 100.0))
        effort = max(0.0, min(1.0, float(state.get('effort', 0.0))))
        hammer_air = float(state.get('hammer_air', 0.0))

        # Terrain rays + ledges.  Computed once per decision in step() and
        # cached — not on every obs getter call.
        if self._terrain_cache is not None:
            rays, ledges = self._terrain_cache
        else:
            rays = [[150.0, 0.0, 0.0, 0.0]] * 32
            ledges = [[0.0] * 5] * 8

        # Base observation (20 dims). Comment is now accurate.
        base_obs = np.array([
            px / 500.0,
            py / 500.0,
            pvx / 10.0,
            pvy / 10.0,
            (hx - px) / 102.0,
            (hy - py) / 102.0,
            (hvx - pvx) / 20.0,
            (hvy - pvy) / 20.0,
            sin_theta,
            cos_theta,
            hammer_ang_vel / 180.0,      # was /10; degrees/frame -> [-1,1]
            self.prior_action[0],        # last nx command (helps BC/continuity)
            self.prior_action[1],        # last ny command
            1.0,                          # bias term
            player_touch,
            head_touch,
            limbs_touch,
            contact_age / 100.0,
            effort,
            hammer_air / 200.0,
        ], dtype=np.float32)

        # Prior action one-hot (primitive=1 since we have a single continuous
        # action now; keep 7 slots for backward compatibility / future primitives,
        # but the meaningful signal is the continuous prior_action above).
        prior_oh = np.zeros(7, dtype=np.float32)
        prior_oh[0] = 1.0
        dur_oh = np.zeros(5, dtype=np.float32)
        dur_oh[0] = 1.0

        rays_flat = np.array(rays, dtype=np.float32).flatten()  # 32*4 = 128
        ledges_flat = np.array(ledges, dtype=np.float32).flatten()  # 8*5 = 40

        obs = np.concatenate([base_obs, prior_oh, dur_oh, rays_flat, ledges_flat])
        # Safety: pad/truncate to exactly 200.
        if obs.shape[0] < 200:
            obs = np.pad(obs, (0, 200 - obs.shape[0]))
        elif obs.shape[0] > 200:
            obs = obs[:200]
        return obs.astype(np.float32)

    # ------------------------------------------------------------------ step
    def step(self, action):
        action = np.clip(np.asarray(action, dtype=np.float32), -1.0, 1.0)
        nx, ny = float(action[0]), float(action[1])
        screen_x = nx * self.STAGE_HALF_W   # [-240, 240]
        screen_y = ny * self.STAGE_HALF_H   # [-180, 180]

        gamma = self.cfg["gamma"]
        time_pen = self.cfg["time_penalty_per_frame"]
        contact_b = self.cfg["contact_bonus_per_frame"]
        potential_scale = self.cfg["potential_scale"]
        milestone_scale = self.cfg["milestone_scale"]
        hook_bonus = self.cfg["hook_bonus_per_frame"]
        hook_cos_min = self.cfg["hook_align_cos_min"]
        smooth_pen = self.cfg["smooth_penalty_scale"]
        respawn_drop_threshold = self.cfg["respawn_drop_threshold"]
        respawn_penalty = self.cfg["respawn_penalty"]
        stall_budget = self.cfg["stall_frame_budget"]

        state = self.bridge.read_state()
        if state is None:
            state = self.prev_state
            if state is None:
                raise RuntimeError("Telemetry not active.")

        prev_y = float(state.get('player_world_y', 0.0))

        # Potential is zero-based at episode spawn: stationary at spawn => 0.
        prev_potential = (prev_y - self.spawn_y) * potential_scale
        accumulated_reward = 0.0
        contact_frames = 0
        hook_frames = 0

        # Terrain descriptor is computed ONCE per decision, here, using
        # the pre-step position as the physics proxy.  Cached for obs.
        if self.collision_map is not None:
            try:
                px = float(state.get('player_world_x', 0.0))
                py = float(state.get('player_world_y', 0.0))
                hx = float(state.get('hammer_world_x', 0.0))
                hy = float(state.get('hammer_world_y', 0.0))
                self._terrain_cache = self.collision_map.get_terrain_descriptor(px, py, hx, hy)
            except Exception:
                self._terrain_cache = None

        # Use the pre-step terrain to derive the overhead ledge target.
        # Convention: ledge rows are [dx, dy, nx, ny, clearance];
        # we only consider ledges above the player (dy > 10) with
        # clearance, and take the closest one.
        hook_target = None
        if self._terrain_cache is not None:
            _, ledges = self._terrain_cache
            best = None
            best_dist = float('inf')
            for row in ledges:
                if len(row) < 5:
                    continue
                dx, dy, nx_l, ny_l, clr = float(row[0]), float(row[1]), float(row[2]), float(row[3]), float(row[4])
                if clr > 0.5 and dy > 10.0:
                    d = math.hypot(dx, dy)
                    if d < best_dist:
                        best_dist = d
                        best = (dx, dy, nx_l, ny_l)
            hook_target = best

        initial_y = prev_y
        ep_decision_gain = 0.0          # track milestones paid within this decision
        for _ in range(self.k_frames):
            self.last_command_id += 1
            state = self.bridge.step_screen_pointer(
                self.last_command_id, screen_x, screen_y, is_down=True
            )
            if state is None:
                state = self.prev_state
                if state is None:
                    break

            curr_y = float(state.get('player_world_y', prev_y))
            curr_potential = (curr_y - self.spawn_y) * potential_scale

            # ---- Dense potential shaping (zero-based) ----
            # gamma * Phi(s_{t+1}) - Phi(s_t).  Phi(spawn)=0, so standing at
            # spawn yields exactly 0 reward per frame (no camping exploit).
            frame_reward = gamma * curr_potential - prev_potential
            frame_reward += time_pen

            if float(state.get('contact_flag', 0.0)) > 0:
                frame_reward += contact_b
                contact_frames += 1

            # ---- Hook alignment bonus ----
            # Active when an overhead ledge exists and hammer-head sits at
            # least hook_cos_min of the way toward it.  This teaches the
            # policy to lift the hammer toward grabbable surfaces.
            if hook_target is not None:
                dx, dy, nx_l, ny_l = hook_target
                ledge_dir_x, ledge_dir_y = dx, dy
                norm = math.hypot(ledge_dir_x, ledge_dir_y)
                if norm > 1e-6:
                    ux, uy = ledge_dir_x / norm, ledge_dir_y / norm
                    hdx = float(state.get('hammer_world_x', 0.0)) - float(state.get('player_world_x', 0.0))
                    hdy = float(state.get('hammer_world_y', 0.0)) - float(state.get('player_world_y', 0.0))
                    hnorm = math.hypot(hdx, hdy)
                    if hnorm > 1e-6:
                        cos_angle = (hdx * ux + hdy * uy) / hnorm
                        if cos_angle >= hook_cos_min:
                            frame_reward += hook_bonus
                            hook_frames += 1

            # ---- Episode-local high progress bookkeeping ----
            if curr_y > self.episode_high_y and (curr_y <= -200.0 or self.decision_idx >= 15):
                # Milestone bonus proportional to gain (dense, larger than
                # the shaped reward, and paid only on NEW highs).  This is
                # the main "you are doing the right thing" signal.
                gain = curr_y - self.episode_high_y
                milestone_amount = milestone_scale * (gain * potential_scale * 100.0)
                accumulated_reward += milestone_amount
                ep_decision_gain += milestone_amount
                self.episode_high_y = curr_y
                self.steps_since_new_high = 0
            else:
                self.steps_since_new_high += 1

            accumulated_reward += frame_reward
            prev_potential = curr_potential
            prev_y = curr_y

        end_y = float(state.get('player_world_y', prev_y)) if state else prev_y
        decision_drop = initial_y - end_y

        # Gentle smoothness penalty — LSTMs shouldn't jitter output.
        accumulated_reward -= smooth_pen * float(np.sum(np.abs(action - self.prior_action)))
        self.prior_action = action.copy()

        obs = self._get_obs(state)

        # ---- Termination ----
        terminated = False
        truncated = False

        # Summit success
        if end_y >= self.cfg["success_y"]:
            terminated = True
            accumulated_reward += self.cfg["success_bonus"]
            self._log(f"[SUCCESS] at y={end_y:.1f}!")
        # Fall: the game's bridge auto-respawns the player.  We detect the
        # respawn event (huge Y-drop in one decision) and terminate the
        # episode with a penalty.
        elif decision_drop > 150.0 and initial_y > -100.0 and end_y <= -200.0:
            terminated = True
            accumulated_reward += respawn_penalty
            self._log(f"[RESPAWN FALL] drop={decision_drop:.1f} (y {initial_y:.1f} -> {end_y:.1f})")
        # Stall: no new episode high in N frames.
        elif self.steps_since_new_high >= stall_budget:
            truncated = True
            self._log(f"[STALL TRUNCATION] high={self.episode_high_y:.1f}, frames={self.steps_since_new_high}")

        self.prev_state = state
        self.total_steps += self.k_frames
        self.decision_idx += 1

        if self.total_steps % 100 < self.k_frames:
            self._log(
                f"[STEP] {self.total_steps} | y={end_y:.1f} | high={self.episode_high_y:.1f}"
                f" | mile=+{ep_decision_gain:.3f}"
                f" | contact={contact_frames}/{self.k_frames}"
                f" | hook={hook_frames}/{self.k_frames}"
                f" | r={accumulated_reward:+.3f}"
            )

        if self.render_every and (self.total_steps % self.render_every == 0):
            try:
                self.bridge.screenshot(
                    os.path.join(os.path.dirname(__file__), "live_playback.png")
                )
            except Exception:
                pass

        # Keep legacy info key working
        self.max_progress = self.episode_high_y
        info = {
            "player_world_x": float(state.get('player_world_x', 0.0)) if state else 0.0,
            "player_world_y": end_y,
            "max_progress": self.max_progress,
            "episode_high_y": self.episode_high_y,
            "setback_drop": max(0.0, decision_drop),
            "contact_frames": contact_frames,
            "hook_frames": hook_frames,
            # Pass through values the trainer's LSTM state needs
            "_terrain_cache_present": self._terrain_cache is not None,
        }
        return obs, float(accumulated_reward), terminated, truncated, info

    # ------------------------------------------------------------------ reset
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._log(f"[RESET] Resetting env (decision {self.decision_idx})...")
        state = self.bridge.reset()
        if state is None:
            raise RuntimeError("Bridge.reset() returned no state.")

        # Double read to absorb any reset lag; some bridges return a stale
        # first state packet.  We only accept a state whose player_world_y
        # is finite and non-None.
        state2 = self.bridge.read_state()
        if state2 and state2.get("player_world_y") is not None:
            state = state2

        # Ensure state has settled to true ground level (<= -200.0)
        attempts = 0
        while float(state.get('player_world_y', 0.0)) > -200.0 and attempts < 20:
            time.sleep(0.02)
            st = self.bridge.read_state()
            if st and st.get("player_world_y") is not None:
                state = st
            attempts += 1

        self.prev_state = state
        raw_y0 = float(state.get('player_world_y', -264.7))
        # Starting rock altitude is -264.7. If Scratch VM returns air height (> -200), anchor to ground.
        y0 = -264.7 if raw_y0 > -200.0 else raw_y0
        self.spawn_y = y0
        self.prev_potential = 0.0
        self.episode_high_y = y0
        self.start_y = y0
        self.max_progress = y0
        self.steps_since_new_high = 0
        self.total_steps = 0
        self.decision_idx = 0
        self.last_command_id = 0
        self.prior_action = np.zeros(2, dtype=np.float32)
        # Terrain cache gets recomputed lazily on first step() after reset.
        self._terrain_cache = None

        return self._get_obs(state), {}

    # ------------------------------------------------------------------ close
    def close(self):
        self._log("Closing env...")
        if getattr(self, "_owns_bridge", False) and self.bridge is not None:
            self.bridge.close()
        if self.log_file:
            try:
                self.log_file.close()
            except Exception:
                pass
