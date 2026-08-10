"""
Sanity-check of the new reward function at a purely mathematical level.

Simulates a fixed sequence of player-world-y values and asserts the
exact reward that the env should produce.  No bridge, no game — just
verifying the math by hand so we can trust it before burning GPU time.

Run:  python test_reward_math.py
"""
import numpy as np
from GettingOverItEnv import GettingOverItEnv, PMDP_CONFIG


class FakeBridge:
    """Minimal bridge that returns a scripted sequence of states."""

    def __init__(self, script):
        self.script = script
        self.idx = 0
        self.last = None

    def reset(self):
        st = self.script[0]
        self.last = st
        self.idx = 1
        return st

    def read_state(self):
        return self.last

    def step_screen_pointer(self, cid, sx, sy, is_down=True, **kw):
        if self.idx < len(self.script):
            self.last = self.script[self.idx]
            self.idx += 1
        return self.last

    def close(self):
        pass


def make_state(y, contact=0.0, hammer_dx=0.0, hammer_dy=0.0):
    return {
        "player_world_x": 0.0,
        "player_world_y": float(y),
        "player_vx": 0.0,
        "player_vy": 0.0,
        "hammer_world_x": hammer_dx,
        "hammer_world_y": float(y) + hammer_dy,
        "hammer_vx": 0.0,
        "hammer_vy": 0.0,
        "hammer_angle": 0.0,
        "hammer_angular_velocity": 0.0,
        "contact_flag": float(contact),
        "contact_point": [0, 0],
        "contact_age": 100.0,
        "effort": 0.0,
        "hammer_air": 0.0,
    }


def test_camping_at_spawn_yields_no_positive_shaping():
    """Stand still at spawn (Y=-264.7) for 10 decisions.  Net reward should
    be dominated by time penalty only (~ -0.04), not the +2.65 per-frame
    exploit the old formula had."""
    spawn = -264.7
    script = [make_state(spawn) for _ in range(50)]
    env = GettingOverItEnv(bridge=FakeBridge(script), k_frames=4)
    env.reset()

    total = 0.0
    idle_action = np.zeros(2, dtype=np.float32)
    for _ in range(10):
        _, r, term, trunc, _ = env.step(idle_action)
        total += r
        if term or trunc:
            break
    env.close()

    # Camping should be ~ -0.04 total; never positive.
    assert total < 0.0, f"Camping yielded positive reward: {total:.4f}"
    assert -0.5 < total < 0.0, f"Camping reward out of expected band: {total:.4f}"
    print(f"  ✅ camping 10 decisions: total reward = {total:+.4f}  (target: negative, ~ -0.04)")


def test_upward_progress_yields_positive_reward():
    """Climb 50 units in 5 decisions.  Reward should be clearly positive."""
    spawn = -264.7
    ys = [spawn + i * 2.5 for i in range(30)]   # smooth +2.5/frame climb
    script = [make_state(y, contact=1.0) for y in ys]
    env = GettingOverItEnv(bridge=FakeBridge(script), k_frames=4)
    env.reset()

    total = 0.0
    for _ in range(5):
        _, r, term, trunc, _ = env.step(np.zeros(2, dtype=np.float32))
        total += r
        if term or trunc:
            break
    env.close()

    assert total > 0.5, f"Climbing +50 units yielded too-low reward: {total:.4f}"
    print(f"  ✅ climb +50 units over 5 decisions: total reward = {total:+.4f}")


def test_respawn_terminates_with_penalty():
    """Drop >100 units in one decision.  Should terminate with -5 penalty."""
    spawn = -264.7
    script = [
        make_state(spawn),
        make_state(spawn + 200.0),  # climb high
        make_state(spawn + 200.0),
        make_state(spawn + 200.0),
        make_state(spawn + 200.0),
        make_state(spawn + 200.0),
        # Now a huge drop — this is a respawn event.
        make_state(spawn + 10.0),
        make_state(spawn + 10.0),
        make_state(spawn + 10.0),
        make_state(spawn + 10.0),
    ]
    env = GettingOverItEnv(bridge=FakeBridge(script), k_frames=4)
    env.reset()
    env.decision_idx = 15

    # First decision: establish high alt.
    _, r1, term, trunc, info = env.step(np.zeros(2, dtype=np.float32))
    assert not term

    # Second decision: big drop.  Must terminate with penalty.
    _, r2, term, trunc, info = env.step(np.zeros(2, dtype=np.float32))
    env.close()
    assert term, "Big drop did not terminate the episode"
    assert r2 < -4.0, f"Expected respawn penalty ~-5, got {r2:.4f}"
    print(f"  ✅ respawn fall: terminated=True, reward={r2:+.4f}")


def test_stall_truncates_fast():
    """Stay at a plateau (no new high).  Episode must truncate at ~75
    decisions (300 frames / 4 frames-per-decision)."""
    spawn = -264.7
    script = [make_state(spawn)] * 400
    env = GettingOverItEnv(bridge=FakeBridge(script), k_frames=4)
    env.reset()

    decisions = 0
    for _ in range(100):
        _, r, term, trunc, _ = env.step(np.zeros(2, dtype=np.float32))
        decisions += 1
        if term or trunc:
            break
    env.close()

    assert trunc and not term, "Expected truncation (stall), not termination"
    assert 70 <= decisions <= 80, f"Expected truncation at ~75 decisions, got {decisions}"
    print(f"  ✅ stall truncation at {decisions} decisions (= {decisions*4} frames)")


def test_max_progress_resets_per_episode():
    """After reaching a high then resetting, the new episode should NOT
    inherit the previous high.  Critical bug from the old run."""
    spawn = -264.7
    script = [make_state(spawn)] * 1000
    bridge = FakeBridge(script)
    env = GettingOverItEnv(bridge=bridge, k_frames=4)
    env.reset()

    # Manually push episode_high_y high.
    env.episode_high_y = spawn + 500.0

    # Now reset.  high must come back to spawn.
    env.reset()
    env.close()
    assert env.episode_high_y == spawn, \
        f"episode_high_y not reset: {env.episode_high_y}, expected {spawn}"
    print(f"  ✅ episode_high_y properly reset to spawn ({spawn})")


if __name__ == "__main__":
    print("🧪 Testing new reward function math...")
    test_camping_at_spawn_yields_no_positive_shaping()
    test_upward_progress_yields_positive_reward()
    test_respawn_terminates_with_penalty()
    test_stall_truncates_fast()
    test_max_progress_resets_per_episode()
    print("\n🎉 All reward-function checks passed.  Safe to train.")
