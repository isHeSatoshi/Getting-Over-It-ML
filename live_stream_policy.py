import os
import sys
import time
import json
import subprocess
import numpy as np
from sb3_contrib import RecurrentPPO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from GettingOverItEnv import GettingOverItEnv

def main():
    raise SystemExit(
        "Legacy action-file streaming is not synchronized gameplay evaluation. "
        "Use python -m research.replay with a trusted research trial directory."
    )
    print("==================================================", flush=True)
    print("📡 LIVE AI POLICY BROWSER STREAMER")
    print("==================================================", flush=True)

    game_dir = os.path.join(os.path.dirname(__file__), "Getting Over It v1")
    live_json_path = os.path.join(game_dir, "live_action.json")
    server_script = os.path.join(os.path.dirname(__file__), "threading_server.py")

    print("🚀 Launching HTTP Web Server for browser tab on port 8080...", flush=True)
    server_process = subprocess.Popen(
        [sys.executable, server_script, "8080", game_dir],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)

    model_path = os.path.join(os.path.dirname(__file__), "models", "ppo_gettingoverit_final.zip")
    if not os.path.exists(model_path):
        model_path = os.path.join(os.path.dirname(__file__), "models", "recurrent_ppo_gettingoverit_131072_steps.zip")

    print(f"🧠 Loading trained model: {model_path}", flush=True)
    model = RecurrentPPO.load(model_path, device="cuda")

    print(f"🎮 Initializing Node.js physics engine...", flush=True)
    env = GettingOverItEnv(port=8081, headless=True, pmdp_cfg={"bridge_type": "node"})
    
    obs, info = env.reset()
    lstm_states = None
    episode_starts = np.ones((1,), dtype=bool)

    print("\n✅ LIVE STREAM SERVER ONLINE ON PORT 8080!")
    print("👉 Open http://127.0.0.1:8080 in your browser to watch the AI play in real time!\n", flush=True)

    step_count = 0
    total_reward = 0.0
    cmd_id = 0

    try:
        while True:
            action, lstm_states = model.predict(
                obs,
                state=lstm_states,
                episode_start=episode_starts,
                deterministic=True
            )

            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            episode_starts = np.array([done], dtype=bool)
            step_count += 1
            total_reward += float(reward)
            cmd_id += 1

            nx, ny = float(action[0]), float(action[1])
            screen_x = nx * 240.0
            screen_y = ny * 180.0

            action_payload = {
                "command_id": cmd_id,
                "screen_x": round(screen_x, 2),
                "screen_y": round(screen_y, 2),
                "is_down": True
            }

            with open(live_json_path, "w", encoding="utf-8") as f:
                json.dump(action_payload, f)

            if step_count % 10 == 0 or done:
                st = env.prev_state or {}
                y_val = float(st.get("player_world_y", 0.0))
                x_val = float(st.get("player_world_x", 0.0))
                h_ang = float(st.get("hammer_angle", 0.0))
                contacts = info.get("contact_points", 0) if info else 0
                print(f"Step {step_count:4d} | Pos=({x_val:5.1f}, {y_val:6.1f}) | Hammer={h_ang:6.1f}° | Action=[{nx:+.2f}, {ny:+.2f}] | Contact={contacts}", flush=True)

            time.sleep(0.02) # ~50 FPS stream rate

            if done:
                print(f"🔄 Episode reset after {step_count} steps...", flush=True)
                obs, info = env.reset()
                lstm_states = None
                episode_starts = np.ones((1,), dtype=bool)

    except KeyboardInterrupt:
        print("\n🛑 Stopped stream.", flush=True)
    except Exception as e:
        print(f"\n❌ Error during stream: {e}", flush=True)
    finally:
        env.close()
        if server_process:
            server_process.terminate()
        if os.path.exists(live_json_path):
            try:
                os.remove(live_json_path)
            except Exception:
                pass
        print("✅ Stream closed.", flush=True)

if __name__ == "__main__":
    main()
