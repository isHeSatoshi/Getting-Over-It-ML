import os
import sys
import time
import numpy as np

# Ensure root dir is on sys path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from GettingOverItEnv import GettingOverItEnv

def main():
    print("==================================================")
    print("SWING MONITORING & SNAPSHOT CAPTURE DEMO")
    print("==================================================")

    out_dir = os.path.join(os.path.dirname(__file__), "swing_snapshots")
    os.makedirs(out_dir, exist_ok=True)

    log_path = os.path.join(os.path.dirname(__file__), "swing_telemetry.log")

    # Use port 8005 to avoid port collision
    env = GettingOverItEnv(port=8005, headless=False, pmdp_cfg={"bridge_type": "selenium"})
    obs, info = env.reset()

    print("\n🌐 Chrome window active! Port: http://127.0.0.1:8005")
    print("Capturing swinging snapshots to swing_snapshots/...\n")

    checkpoints = [10, 25, 40, 60, 80, 100, 120, 140, 160, 180, 200]

    with open(log_path, "w", encoding="utf-8") as log_f:
        log_f.write("RESET | Game Started\n")
        
        for i in range(1, 220):
            # Smooth 360-degree circular swing trajectory
            angle = (i / 15.0) * 2 * np.pi
            nx = float(np.cos(angle))
            ny = float(np.sin(angle))

            obs, reward, term, trunc, info = env.step([nx, ny])

            st = env.prev_state
            py = info.get("player_world_y", 0.0)
            px = info.get("player_world_x", 0.0)
            h_ang = st.get("hammer_angle", 0.0) if st else 0.0
            h_ang_vel = st.get("hammer_angular_velocity", 0.0) if st else 0.0

            line = f"Step {i:03d} | Target: ({nx:+0.2f}, {ny:+0.2f}) | Pos: ({px:5.1f}, {py:5.1f}) | Hammer Angle: {h_ang:6.1f}° | AngVel: {h_ang_vel:+6.1f}°/f"
            log_f.write(line + "\n")

            if i in checkpoints:
                img_name = f"swing_step_{i:03d}.png"
                img_path = os.path.join(out_dir, img_name)
                env.bridge.screenshot(img_path)
                print(f"[CAPTURED] {img_name} -> Angle: {h_ang:6.1f}° | Target: ({nx:+0.2f}, {ny:+0.2f})")

            time.sleep(0.04)

    env.close()
    print("\n✅ Swinging monitoring demo complete!")

if __name__ == "__main__":
    main()
