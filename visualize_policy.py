import os
import sys
import time
import numpy as np
from sb3_contrib import RecurrentPPO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from GettingOverItEnv import GettingOverItEnv

def trigger_game_start(env):
    """Broadcast 'New Game' + pulse Space key to clear Scratch intro screen and spawn cat at ground rock."""
    if env.bridge and hasattr(env.bridge, "driver") and env.bridge.driver:
        print("🎮 Pressing Space key & starting Scratch physics engine...", flush=True)
        env.bridge.driver.execute_script("""
            if (window.vm && window.vm.runtime) {
                window.vm.runtime.stopAll();
                window.vm.runtime.startHats('event_whenbroadcastreceived', { BROADCAST_OPTION: 'New Game' });
                var kb = window.vm.runtime.ioDevices.keyboard;
                if (kb && !kb._keysPressed.includes('space')) {
                    kb._keysPressed.push('space');
                }
                window.isResetting = true;
            }
        """)
        # Step VM for 2 seconds to finish intro transition & land on starting rock
        for _ in range(60):
            env.bridge.driver.execute_script("""
                if (window.vm && window.vm.runtime) {
                    var kb = window.vm.runtime.ioDevices.keyboard;
                    if (kb) kb._keysPressed.length = 0;
                    window.vm.runtime._step();
                }
            """)
            time.sleep(0.02)
        env.bridge.driver.execute_script("window.isResetting = true;")

def main():
    print("==================================================", flush=True)
    print("🎮 LAUNCHING HEADED BROWSER - RECURRENT PPO MODEL EVALUATION", flush=True)
    print("==================================================", flush=True)

    model_path = os.path.join(os.path.dirname(__file__), "models", "ppo_gettingoverit_final.zip")
    if not os.path.exists(model_path):
        model_path = os.path.join(os.path.dirname(__file__), "models", "recurrent_ppo_gettingoverit_131072_steps.zip")

    print(f"🧠 Loading trained policy from: {model_path}", flush=True)
    model = RecurrentPPO.load(model_path, device="cuda")

    print("\n🌐 Launching visible Chrome Browser window (port 8080)...", flush=True)
    env = GettingOverItEnv(port=8080, headless=False, pmdp_cfg={"bridge_type": "selenium"})
    
    obs, info = env.reset()
    trigger_game_start(env)

    lstm_states = None
    episode_starts = np.ones((1,), dtype=bool)

    print("\n🚀 Autonomous locomotion active! Look at your screen for the Chrome window.", flush=True)
    print("Press Ctrl+C in terminal to stop evaluation.\n", flush=True)

    step_count = 0
    total_reward = 0.0

    try:
        for _ in range(2000):
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

            st = env.prev_state or {}
            y_val = float(st.get("player_world_y", 0.0))
            x_val = float(st.get("player_world_x", 0.0))
            h_ang = float(st.get("hammer_angle", 0.0))

            if step_count % 5 == 0 or done:
                contacts = info.get("contact_points", 0) if info else 0
                hooks = info.get("hook_points", 0) if info else 0
                print(f"Step {step_count:4d} | Pos=({x_val:5.1f}, {y_val:6.1f}) | Hammer={h_ang:6.1f}° | Action=[{action[0]:+.2f}, {action[1]:+.2f}] | Contact={contacts}", flush=True)

            time.sleep(0.02) # ~50 FPS real-time playback speed

            if done:
                print(f"🔄 Episode finished after {step_count} steps. Resetting to rock...", flush=True)
                obs, info = env.reset()
                trigger_game_start(env)
                lstm_states = None
                episode_starts = np.ones((1,), dtype=bool)

    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.", flush=True)
    except Exception as e:
        print(f"\n❌ Error during visualization: {e}", flush=True)
    finally:
        env.close()
        print("✅ Headed browser session completed.", flush=True)

if __name__ == "__main__":
    main()
