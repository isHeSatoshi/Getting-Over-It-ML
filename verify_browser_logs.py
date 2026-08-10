import os
import sys
import time
import numpy as np

# Ensure root dir is on sys path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from GettingOverItEnv import GettingOverItEnv

def main():
    print("==================================================")
    print("BROWSER LOG VS. VISUAL OBSERVABILITY VERIFICATION")
    print("==================================================")

    env = GettingOverItEnv(port=8000, headless=True, pmdp_cfg={"bridge_type": "selenium"})
    obs, info = env.reset()

    out_dir = os.path.join(os.path.dirname(__file__), "browser_snapshots")
    os.makedirs(out_dir, exist_ok=True)

    log_path = os.path.join(os.path.dirname(__file__), "browser_verification.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"RESET | player_world_y={info.get('player_world_y')}\n")

    env.bridge.screenshot(os.path.join(out_dir, "step_000.png"))
    print("Captured initial reset snapshot: step_000.png")

    checkpoints = [50, 100, 150, 200, 250, 300]
    
    for i in range(1, 301):
        action = np.random.uniform(-1.0, 1.0, size=(2,)).astype(np.float32)
        obs, reward, term, trunc, info = env.step(action)

        py = info.get("player_world_y", 0.0)
        px = info.get("player_world_x", 0.0)
        c = info.get("contact_frames", 0)
        m = info.get("max_progress", 0.0)

        log_line = f"Step {i:03d} | y={py:.1f} | x={px:.1f} | contact={c} | max={m:.1f}"
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")

        if i in checkpoints:
            img_path = os.path.join(out_dir, f"step_{i:03d}.png")
            env.bridge.screenshot(img_path)
            print(f"Captured snapshot: step_{i:03d}.png -> {log_line}")

    env.close()
    print("\n[SUCCESS] Browser verification script complete! Log and snapshots saved.")

if __name__ == "__main__":
    main()
