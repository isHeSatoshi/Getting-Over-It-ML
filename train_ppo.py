import os
import sys
import time
import subprocess
import shutil

from GettingOverItEnv import GettingOverItEnv
from gymnasium.wrappers import TimeLimit
from sb3_contrib import RecurrentPPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.vec_env import SubprocVecEnv
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
PORT_BASE = 8000  # Will map to 8001, 8002, 8003, 8004 for rank 0, 1, 2, 3
GAME_DIR = "Getting Over It v1"

class EnvWrapper:
    def __init__(self, rank, port_base, driver_path):
        self.rank = rank
        self.port_base = port_base
        self.driver_path = driver_path

    def __call__(self):
        # Stagger startup by 1.5s per rank to allow Node server ready signals to resolve cleanly
        time.sleep(self.rank * 1.5)
        # Headless=True to use fast NodeBridge physics server
        env = GettingOverItEnv(port=self.port_base + self.rank + 1, headless=True)
        env = TimeLimit(env, max_episode_steps=4000)   # hard cap; stalls truncate much earlier
        env = Monitor(env)
        return env

def main():
    print("==================================================")
    print("MISSION: Phase 3 - Training the Autonomous Locomotion Policy")
    print("ARCHITECTURE: Recurrent PPO (LSTM)")
    print("HARDWARE TARGET: Intel Core i7-12700K / NVIDIA RTX 4060 Ti")
    print("ESTIMATED TIME: ~5 hours for 1,000,000 steps")
    print("==================================================\n")

    os.makedirs("./models/", exist_ok=True)
    os.makedirs("./ppo_tensorboard/", exist_ok=True)

    # Clean up stale chrome profiles to prevent SingletonLock hangs
    chrome_profiles_dir = os.path.join(os.path.dirname(__file__), "chrome_profiles")
    if os.path.exists(chrome_profiles_dir):
        print("🧹 Cleaning up stale Chrome profiles and locks...")
        try:
            shutil.rmtree(chrome_profiles_dir)
        except Exception as e:
            print(f"⚠️ Profile cleanup warning: {e}")

    env = None
    
    try:
        # Pre-resolve chrome driver once to prevent multiprocessing clashes
        print("🔍 Checking Chrome driver installation...")
        os.environ['WDM_SSL_VERIFY'] = '0'
        driver_path = ChromeDriverManager().install()

        # Initialize parallel envs tuned for Intel i7-12700K (8 Performance Cores)
        num_envs = 8
        print(f"🎮 Initializing {num_envs} Parallel GettingOverIt Environments (i7-12700K P-Core Scaled)...")
        env = SubprocVecEnv([EnvWrapper(i, PORT_BASE, driver_path) for i in range(num_envs)])

        # 3. Load or Initialize Model
        potential_models = []
        # Important: do NOT auto-resume from a checkpoint trained on the OLD
        # (broken) reward function.  Continuing from a poisoned policy is
        # worse than starting fresh because the LSTM hidden state has locked
        # in "don't move" biases.  Set RESUME_CHECKPOINT env var to a path
        # explicitly if you intentionally want to resume.
        resume_override = os.environ.get("RESUME_CHECKPOINT", "")
        if resume_override and os.path.exists(resume_override):
            potential_models = [resume_override]

        if potential_models:
            checkpoint_path = max(potential_models, key=os.path.getmtime)
            print(f"🔄 Resuming from latest checkpoint: {checkpoint_path}")
            model = RecurrentPPO.load(checkpoint_path, env=env, device="cuda")
            model.tensorboard_log = "./ppo_tensorboard/"
        else:
            print("🧠 Initializing a fresh Recurrent PPO Model (new reward fn)...")
            model = RecurrentPPO(
                policy="MlpLstmPolicy",
                env=env,
                device="cuda",
                learning_rate=3e-4,
                n_steps=2048,
                batch_size=256,             # 2048/8 sequences per batch fits LSTM better
                n_epochs=10,
                gamma=0.99,
                gae_lambda=0.95,
                clip_range=0.2,
                ent_coef=0.01,              # CRITICAL: positive entropy to force exploration
                vf_coef=0.5,
                max_grad_norm=0.5,
                policy_kwargs=dict(
                    lstm_hidden_size=128,
                    net_arch=[128, 128],
                    # Orthogonal init helps LSTMs break early symmetry.
                    ortho_init=True,
                ),
                tensorboard_log="./ppo_tensorboard/",
                verbose=1
            )

        checkpoint_callback = CheckpointCallback(
            save_freq=16384,
            save_path='./models/',
            name_prefix='recurrent_ppo_gettingoverit'
        )

        # 4. Training Loop.  Note the env already truncates stalled episodes,
        # so each iteration produces a mixture of (fall, summit, truncated)
        # trajectories — exactly the data distribution PPO needs.
        print("\n🚀 Starting Training (200,000 steps on 8 parallel Node workers)...")
        model.learn(
            total_timesteps=200_000,
            callback=checkpoint_callback,
            reset_num_timesteps=False
        )
        
        print("\n🎉 Training Complete! Saving final model...")
        model.save("./models/ppo_gettingoverit_final.zip")

    except KeyboardInterrupt:
        print("\n⚠️ KeyboardInterrupt caught.")
        if env is not None:
            # We must use model.save since KeyboardInterrupt typically happens during learn()
            # If model was initialized, it's safe to save.
            try:
                model.save("ppo_interrupted.zip")
                print("🛑 Training suspended. Model saved as 'ppo_interrupted.zip'.")
            except:
                print("⚠️  Warning: Failed to save model during interrupt.")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("🧹 Cleaning up...")
        if env is not None:
            print("🛑 Closing GettingOverIt Environment...")
            env.close()
        print("✅ Cleanup complete.")

if __name__ == "__main__":
    main()
