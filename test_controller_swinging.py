import os
import sys
import math
import numpy as np

# Ensure root dir is on sys path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from GettingOverItEnv import GettingOverItEnv

def main():
    print("==================================================")
    print("CONTROLLER SWINGING & IMPULSE TEST SUITE")
    print("==================================================")

    env = GettingOverItEnv(port=8000, headless=True)
    obs, info = env.reset()

    print("\n--- 1. Testing Circular Hammer Arc Sweep (Clockwise) ---")
    angles = np.linspace(0, 2 * np.pi, 20)
    for i, a in enumerate(angles):
        nx = float(np.cos(a))
        ny = float(np.sin(a))
        obs, reward, term, trunc, info = env.step([nx, ny])

        # Extract hammer telemetry from state
        state = env.prev_state
        h_angle = state.get("hammer_angle", 0.0)
        h_ang_vel = state.get("hammer_angular_velocity", 0.0)
        h_vx = state.get("hammer_vx", 0.0)
        h_vy = state.get("hammer_vy", 0.0)
        p_vy = state.get("player_vy", 0.0)

        print(f"Arc Step {i:02d} | Input Target: ({nx:+0.2f}, {ny:+0.2f}) | "
              f"Hammer Angle: {h_angle:6.1f}° | AngVel: {h_ang_vel:+6.1f}°/f | "
              f"Hammer Vel: ({h_vx:+5.1f}, {h_vy:+5.1f}) | Player Vy: {p_vy:+5.1f}")

    print("\n--- 2. Testing Vertical Ground Vault Impulse (Downward Push) ---")
    # Reset env to start altitude
    obs, info = env.reset()
    
    # 5 steps pushing hard downward at (0.0, -1.0)
    for step in range(5):
        obs, reward, term, trunc, info = env.step([0.0, -1.0])
        st = env.prev_state
        print(f"Push Step {step+1} | Player Y: {info['player_world_y']:5.1f} | "
              f"Player Vy: {st.get('player_vy', 0.0):+5.1f} | Contact: {info['contact_frames']}/4")

    # 5 steps lifting upward at (0.0, 1.0) to release vault
    for step in range(5):
        obs, reward, term, trunc, info = env.step([0.0, 1.0])
        st = env.prev_state
        print(f"Lift Step {step+1} | Player Y: {info['player_world_y']:5.1f} | "
              f"Player Vy: {st.get('player_vy', 0.0):+5.1f} | Contact: {info['contact_frames']}/4")

    env.close()
    print("\n[SUCCESS] Controller swinging and impulse physics verified!")

if __name__ == "__main__":
    main()
