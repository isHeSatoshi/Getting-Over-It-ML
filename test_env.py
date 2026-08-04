import time
import subprocess
import os
import sys

# Import our formal Gymnasium environment
from GettingOverItEnv import GettingOverItEnv

def main():
    print("🚀 Starting Local Game Server...")
    # Start the HTTP server to host the game (identical to how brain.py did it)
    server_process = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8000"],
        cwd=os.path.join(os.getcwd(), "Getting Over It v1"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Give the server a moment to spin up
    time.sleep(2)
    
    env = None
    try:
        print("🎮 Instantiating GettingOverItEnv...")
        env = GettingOverItEnv(port=8000, max_mouse_speed=30.0)
        
        print("🔄 Calling env.reset()...")
        obs, info = env.reset()
        print(f"✅ Reset complete. Initial Observation: {obs}")
        
        print("⚡ Entering random action loop. Press Ctrl+C to stop.")
        step_count = 0
        
        while True:
            # 1. Sample a random continuous action [-1.0, 1.0] for [dx, dy]
            action = env.action_space.sample()
            
            # 2. Step the environment
            obs, reward, terminated, truncated, info = env.step(action)
            
            # 3. Extract current altitude from the environment's telemetry records
            current_altitude = env.prev_telemetry['py']
            
            # 4. Print the telemetry out for monitoring
            print(f"Step: {step_count:04d} | Action: [{action[0]:+0.2f}, {action[1]:+0.2f}] | Reward: {reward:+0.4f} | Alt: {current_altitude:0.2f}")
            
            step_count += 1
            
            # Throttle the loop slightly so we don't instantly blitz the browser thread
            time.sleep(1/60.0) # ~60 FPS
            
    except KeyboardInterrupt:
        print("\n🛑 Stopped testing via KeyboardInterrupt.")
    finally:
        print("🧹 Cleaning up...")
        if env is not None:
            env.close()
        if server_process is not None:
            server_process.terminate()

if __name__ == "__main__":
    main()
