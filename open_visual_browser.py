import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from GettingOverItEnv import GettingOverItEnv

def main():
    print("==================================================")
    print("LAUNCHING CHROME BROWSER WINDOW ON SCREEN")
    print("==================================================")

    # Launch visible Chrome
    env = GettingOverItEnv(port=8080, headless=False, pmdp_cfg={"bridge_type": "selenium"})
    obs, info = env.reset()

    print("\n🌐 Chrome browser window launched on screen!")
    print("Unpausing browser step loop for manual & automated viewing...")

    # Unpause HTML step guard so browser plays continuously
    env.bridge.driver.execute_script("window.isResetting = true;")

    print("Stepping 500 actions (50 FPS). Look at your screen for the Chrome window!")
    
    for i in range(500):
        angle = (i / 15.0) * 2 * np.pi
        nx = float(np.cos(angle))
        ny = float(np.sin(angle))

        obs, reward, term, trunc, info = env.step([nx, ny])
        time.sleep(0.02) # ~50 FPS

    env.close()
    print("✅ Visual Chrome session completed.")

if __name__ == "__main__":
    main()
