import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from GettingOverItEnv import GettingOverItEnv

def main():
    print("==================================================")
    print("FULL BROWSER EDGE-CASE DIAGNOSTIC & SNAPSHOT CAPTURE")
    print("==================================================")

    out_dir = os.path.join(os.path.dirname(__file__), "diagnostic_snapshots")
    os.makedirs(out_dir, exist_ok=True)

    log_path = os.path.join(os.path.dirname(__file__), "diagnostic_telemetry.log")

    # Clean previous snapshots if any
    for f in os.listdir(out_dir):
        if f.endswith(".png"):
            os.remove(os.path.join(out_dir, f))

    env = GettingOverItEnv(port=8080, headless=False, pmdp_cfg={"bridge_type": "selenium"})
    obs, info = env.reset()

    print("\n🌐 Fresh Browser Session Initialized! Port: http://127.0.0.1:8080")
    print("Capturing diagnostic snapshots every 20 steps...\n")

    with open(log_path, "w", encoding="utf-8") as f_log:
        f_log.write(f"RESET | Initial Y={info.get('player_world_y', 0.0):.1f}\n")

        for step in range(1, 401):
            # Phase-based action sequence to stress-test mechanics
            if step <= 100:
                # Phase 1: 360-degree circular arc swings
                angle = (step / 15.0) * 2 * np.pi
                action = [float(np.cos(angle)), float(-np.sin(angle))]
            elif step <= 200:
                # Phase 2: Downward vault push-offs to gain altitude
                phase_tick = step - 100
                if phase_tick % 10 < 5:
                    action = [0.0, -1.0] # Downward push
                else:
                    action = [0.0, 1.0]  # Upward release
            elif step <= 300:
                # Phase 3: Push hard left to trigger water drop (-X)
                action = [-1.0, 0.0]
            else:
                # Phase 4: Gentle centering post-respawn
                action = [0.0, 0.0]

            obs, reward, term, trunc, info = env.step(action)

            py = info.get("player_world_y", 0.0)
            px = info.get("player_world_x", 0.0)
            c = info.get("contact_frames", 0)
            m = info.get("max_progress", 0.0)
            s_drop = info.get("setback_drop", 0.0)

            line = f"Step {step:03d} | Pos: ({px:6.1f}, {py:6.1f}) | Max: {m:5.1f} | Drop: {s_drop:4.1f} | Contact: {c}/4 | Term: {term} | Trunc: {trunc}"
            f_log.write(line + "\n")

            if step % 20 == 0 or term or trunc:
                img_name = f"diag_{step:03d}.png"
                img_path = os.path.join(out_dir, img_name)
                env.bridge.screenshot(img_path)
                print(f"[SNAPSHOT] {img_name} | {line}")

            if term or trunc:
                print(f"Episode end at step {step} (Term={term}, Trunc={trunc}). Resetting...")
                obs, info = env.reset()

            time.sleep(0.03)

    env.close()
    print("\n✅ Full Diagnostic Snapshot Capture Complete!")

if __name__ == "__main__":
    main()
