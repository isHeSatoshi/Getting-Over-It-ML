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
# ----------------------------------------------------------------------------
PMDP_CONFIG = {
    "gamma": 0.99,                 # discount for potential-based shaping
    "potential": "altitude",       # Phi(s) = player_world_y
    "time_penalty_per_frame": -0.01,
    "contact_bonus_per_frame": 0.002,   # small reward for being in contact (latched)
    "setback_threshold": 60.0,         # if y drops >60 in one decision, it's a "setback"
    "setback_penalty_scale": 0.05,      # asymmetric penalty proportional to drop
    "success_y": 16000.0,
    "fall_budget_base": 100.0,         # terminal-fall slack at spawn
    "fall_budget_per_high": 1.5,        # extra slack per unit of max_progress
    "fall_suppress_decisions": 50,     # no terminal fall for first 50 decisions
    "stall_frame_budget": 300,         # fixed truncation horizon (frames w/o new high)
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
            history = self.driver.execute_script("return window.stateHistory;")
            if not history:
                return None
            # Latest frame = max key
            latest_id = max(int(k) for k in history.keys())
            return history[str(latest_id)]
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
        self.max_progress = 0.0
        self.start_y = 0.0
        self.steps_since_new_high = 0
        self.total_steps = 0
        self.decision_idx = 0
        self.last_command_id = 0
        self._decision_start_y = 0.0
        self.prior_action = np.zeros(2, dtype=np.float32)
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

        # Terrain rays + ledges
        if self.collision_map is not None:
            try:
                rays, ledges = self.collision_map.get_terrain_descriptor(px, py, hx, hy)
            except Exception:
                rays = [[150.0, 0.0, 0.0, 0.0]] * 32
                ledges = [[0.0] * 5] * 8
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

        state = self.bridge.read_state()
        if state is None:
            state = self.prev_state
            if state is None:
                raise RuntimeError("Telemetry not active.")

        prev_y = float(state.get('player_world_y', 0.0))
        prev_potential = prev_y
        self._decision_start_y = prev_y  # altitude at decision start
        accumulated_reward = 0.0
        contact_frames = 0

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
            curr_potential = curr_y

            # Potential-based shaping (policy-invariant).
            frame_reward = gamma * curr_potential - prev_potential
            frame_reward += time_pen
            if float(state.get('contact_flag', 0.0)) > 0:
                frame_reward += contact_b
                contact_frames += 1

            # Progress bookkeeping (for success/stall only, NOT for reward).
            if curr_y > self.max_progress:
                self.max_progress = curr_y
                self.steps_since_new_high = 0
            else:
                self.steps_since_new_high += 1

            accumulated_reward += frame_reward
            prev_potential = curr_potential
            prev_y = curr_y

        # ---- PMDP setback measurement (asymmetric) ----
        # A "setback" = losing a lot of altitude in one decision. We add an
        # asymmetric penalty so the value function learns setbacks are costly
        # beyond the lost potential. This is the measurement; the cure lives
        # in the training-time value shaping (see train_ppo.py ablations).
        decision_start_y = float(self._decision_start_y)
        end_y = float(state.get('player_world_y', prev_y)) if state else prev_y
        net_drop = max(0.0, decision_start_y - end_y)
        if net_drop > self.cfg["setback_threshold"]:
            accumulated_reward -= self.cfg["setback_penalty_scale"] * (
                net_drop - self.cfg["setback_threshold"]
            )

        # Tiny action-smoothness term (NOT the old -0.1 jerk; this is gentle).
        accumulated_reward -= 0.01 * float(np.sum(np.abs(action - self.prior_action)))
        self.prior_action = action.copy()

        obs = self._get_obs(state)

        # ---- Termination ----
        terminated = False
        truncated = False
        end_y = float(state.get('player_world_y', prev_y)) if state else prev_y

        if end_y >= self.cfg["success_y"]:
            terminated = True
            accumulated_reward += 100.0
            self._log(f"[SUCCESS] at y={end_y:.1f}!")

        # Terminal fall: only after the suppress window, with a growing budget.
        # max_progress/start_y are SCRATCH-WORLD Y, so this budget is in world units.
        if not terminated and self.decision_idx >= self.cfg["fall_suppress_decisions"]:
            budget = (self.cfg["fall_budget_base"]
                      + self.cfg["fall_budget_per_high"] * max(0.0, self.max_progress - self.start_y))
            if end_y < max(self.start_y - 100.0, self.max_progress - budget):
                terminated = True
                accumulated_reward -= 25.0
                self._log(f"[TERMINAL FALL] y={end_y:.1f}, max={self.max_progress:.1f}")

        # Truncation: fixed frame budget (NOT action-dependent).
        if self.steps_since_new_high >= self.cfg["stall_frame_budget"]:
            truncated = True
            self._log(f"[TRUNCATED] stalled {self.steps_since_new_high} frames.")

        self.prev_state = state
        self.total_steps += self.k_frames
        self.decision_idx += 1

        if self.total_steps % 100 < self.k_frames:
            self._log(f"[STEP] step {self.total_steps} | y={end_y:.1f} | max={self.max_progress:.1f} "
                      f"| contact={contact_frames}/{self.k_frames} | r={accumulated_reward:+.3f}")

        if self.render_every and (self.total_steps % self.render_every == 0):
            try:
                self.bridge.screenshot(
                    os.path.join(os.path.dirname(__file__), "live_playback.png")
                )
            except Exception:
                pass

        info = {
            "player_world_x": float(state.get('player_world_x', 0.0)) if state else 0.0,
            "player_world_y": end_y,
            "max_progress": self.max_progress,
            "setback_drop": max(0.0, net_drop),
            "contact_frames": contact_frames,
        }
        return obs, float(accumulated_reward), terminated, truncated, info

    # ------------------------------------------------------------------ reset
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._log(f"[RESET] Resetting env (decision {self.decision_idx})...")
        state = self.bridge.reset()
        if state is None:
            raise RuntimeError("Bridge.reset() returned no state.")
        self.prev_state = state
        self.max_progress = float(state.get('player_world_y', 0.0))
        self.start_y = self.max_progress
        self.steps_since_new_high = 0
        self.total_steps = 0
        self.decision_idx = 0
        self.last_command_id = 0
        self.prior_action = np.zeros(2, dtype=np.float32)
        self._decision_start_y = float(state.get('player_world_y', 0.0))
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
