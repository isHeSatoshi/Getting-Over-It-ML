import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from GettingOverItEnv import GettingOverItEnv

def main():
    print("==================================================")
    print("MONITORING RUN: CAPTURING SNAPSHOTS & LOGS (20 SECONDS)")
    print("==================================================")

    out_dir = os.path.join(os.path.dirname(__file__), "monitor_snapshots")
    os.makedirs(out_dir, exist_ok=True)

    log_path = os.path.join(os.path.dirname(__file__), "monitor_run.log")

    # Clean old snapshots
    for f in os.listdir(out_dir):
        if f.endswith(".png"):
            os.remove(os.path.join(out_dir, f))

    env = GettingOverItEnv(port=8080, headless=True, pmdp_cfg={"bridge_type": "selenium"})
    obs, info = env.reset()

    start_t = time.time()
    step = 0

    with open(log_path, "w", encoding="utf-8") as f_log:
        f_log.write(f"MONITOR RUN STARTED | Initial Y={info.get('player_world_y', 0.0):.1f}\n")

        print("Capturing screenshots every 2 seconds over a 20-second run...\n")

        while time.time() - start_t < 20.0:
            step += 1
            angle = (step / 15.0) * 2 * np.pi
            nx = float(np.cos(angle))
            ny = float(-np.sin(angle))

            obs, reward, term, trunc, info = env.step([nx, ny])

            py = info.get("player_world_y", 0.0)
            px = info.get("player_world_x", 0.0)
            c = info.get("contact_frames", 0)

            line = f"Step {step:03d} | Elapsed: {time.time()-start_t:4.1f}s | Pos: ({px:6.1f}, {py:6.1f}) | Contact: {c}/4"
            f_log.write(line + "\n")

            if step % 20 == 0:
                img_name = f"frame_{step:03d}.png"
                img_path = os.path.join(out_dir, img_name)
                env.bridge.screenshot(img_path)
                print(f"[CAPTURED] {img_name} -> {line}")

            time.sleep(0.04)

    env.close()
    print("\n✅ 20-second Monitoring Run Complete! Snapshots saved.")

if __name__ == "__main__":
    main()
