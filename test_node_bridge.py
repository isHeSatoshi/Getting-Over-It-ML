import os
import sys
import time
import numpy as np

# Ensure root dir is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vm_bridge.node_bridge import NodeBridge
from GettingOverItEnv import GettingOverItEnv

def test_node_bridge_standalone():
    print("==================================================")
    print("1. Testing NodeBridge Standalone & Virtual Clock")
    print("==================================================")
    
    bridge = NodeBridge(port=8000)
    
    # Initial state after reset
    state = bridge.reset()
    assert state is not None, "Reset state is None!"
    print(f"Initial state: FRAME={state.get('frame_id')}, PLAYER Y={state.get('player_world_y')}, PLAYER X={state.get('player_world_x')}")
    
    initial_y = float(state.get('player_world_y', 0.0))
    assert abs(initial_y - 21.0) < 15.0, f"Expected initial PLAYER Y approx 21, got {initial_y}"
    
    # Step 500 ticks and verify frame advancement
    start_t = time.time()
    total_steps = 500
    for i in range(total_steps):
        # Move mouse in a small circular sweep
        angle = (i / 50.0) * 2 * np.pi
        nx = float(np.cos(angle) * 0.5)
        ny = float(np.sin(angle) * 0.5)
        state = bridge.step_screen_pointer(i + 1, nx * 240.0, ny * 180.0, is_down=True, n_steps=1)
        assert state is not None, f"State at step {i} is None!"

    elapsed = time.time() - start_t
    sps = total_steps / elapsed
    
    final_frame = state.get('frame_id')
    final_y = state.get('player_world_y')
    print(f"500 steps completed in {elapsed:.3f}s ({sps:.1f} steps/sec)")
    print(f"Final state: FRAME={final_frame}, PLAYER Y={final_y:.2f}, HAMMER Y={state.get('hammer_world_y'):.2f}")
    
    assert final_frame >= 100, f"Virtual clock patch failed! FRAME stayed at {final_frame}"
    print("[SUCCESS] Virtual clock patch verified! FRAME advanced properly.")

    # Test death-unblock state pulse (simulating fall below y=-180)
    print("\n--------------------------------------------------")
    print("2. Testing Death-Unblock Space Pulse & Reset")
    print("--------------------------------------------------")
    
    # Trigger episode reset
    state_after_reset = bridge.reset()
    frame_after_reset = state_after_reset.get('frame_id')
    y_after_reset = state_after_reset.get('player_world_y')
    print(f"State after reset: FRAME={frame_after_reset}, PLAYER Y={y_after_reset:.2f}")
    assert abs(y_after_reset - 21.0) < 15.0, f"Expected reset PLAYER Y approx 21, got {y_after_reset}"
    print("[SUCCESS] Episode reset verified!")

    bridge.close()
    print("[SUCCESS] Standalone NodeBridge test passed successfully!")


def test_gym_env_integration():
    print("\n==================================================")
    print("3. Testing Gymnasium GettingOverItEnv Integration")
    print("==================================================")
    
    env = GettingOverItEnv(k_frames=4)
    obs, info = env.reset()
    assert obs.shape == (200,), f"Expected observation shape (200,), got {obs.shape}"
    print(f"Env reset successful. Observation shape: {obs.shape}")

    start_t = time.time()
    num_decisions = 100  # 100 decision steps * 4 frame repeat = 400 physics ticks
    for i in range(num_decisions):
        action = np.random.uniform(-1.0, 1.0, size=(2,)).astype(np.float32)
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            print(f"Env ended at decision {i}: terminated={terminated}, truncated={truncated}")
            obs, info = env.reset()

    elapsed = time.time() - start_t
    physics_ticks = num_decisions * 4
    sps = physics_ticks / elapsed
    print(f"100 decision steps ({physics_ticks} physics ticks) in {elapsed:.3f}s ({sps:.1f} ticks/sec)")
    print(f"Latest info: player_y={info['player_world_y']:.2f}, max_progress={info['max_progress']:.2f}")

    env.close()
    print("[SUCCESS] Gymnasium env integration test passed successfully!")


if __name__ == "__main__":
    test_node_bridge_standalone()
    test_gym_env_integration()
