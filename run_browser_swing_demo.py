import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from GettingOverItEnv import GettingOverItEnv

def main():
    print("==================================================")
    print("AUTOMATED PROGRAMMATIC CONTROLLER SWING DEMO")
    print("==================================================")

    # Launch browser env on port 8080
    env = GettingOverItEnv(port=8080, headless=False, pmdp_cfg={"bridge_type": "selenium"})
    obs, info = env.reset()

    print("\n🌐 Automated Controller connected to browser!")
    print("Executing 1,000 automated 360-degree hammer swings (~30 seconds)...")
    print("Sit back and watch the browser tab — do NOT move your mouse!\n")

    try:
        for i in range(1000):
            # Smooth circular swing trajectory
            angle = (i / 15.0) * 2 * np.pi
            nx = float(np.cos(angle))
            ny = float(np.sin(angle))

            obs, reward, term, trunc, info = env.step([nx, ny])

            if i % 50 == 0:
                print(f"Step {i:04d} | Target: ({nx:+0.2f}, {ny:+0.2f}) | Player Y: {info.get('player_world_y', 0.0):5.1f}")

            time.sleep(0.03) # ~33 FPS continuous swing playback

        print("\n✅ Automated swinging demo completed successfully!")
    except KeyboardInterrupt:
        print("\n🛑 Stopped demo.")
    finally:
        env.close()

if __name__ == "__main__":
    main()
