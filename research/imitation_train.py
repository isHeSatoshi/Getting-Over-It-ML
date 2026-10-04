"""Three-arm imitation/PPO trainer pipeline. Full remote dispatch is not admitted."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np

from research.behavior_cloning import warm_start
from research.browser_bridge import ROOT
from research.demonstrations import load, require
from research.imitation_study import plan
from research.optimizer_work import OptimizerWork
from research.provenance import fingerprint
from research.reward import RewardConfig
from research.training_timing import PhysicalWork

VERSION = "imitation-three-arm-trainer-v1"


def settings(arm, smoke):
    study = plan()
    require(arm in study["arms"] and type(smoke) is bool, "Unknown imitation arm or run type")
    rl = arm != "behavior_cloning_only"
    cloning = arm != "ppo_from_scratch"
    return {"version": VERSION, "arm": arm, "pipeline_smoke": smoke,
            "frame_skip": 1, "gamma": RewardConfig().gamma(1),
            "gae_lambda": study["ppo"]["gae_lambda"],
            "architecture": [64, 64] if smoke else study["ppo"]["architecture"],
            "cloning_updates": (8 if smoke else study["cloning"]["updates"]) if cloning else 0,
            "cloning_batch_size": 64 if smoke else study["cloning"]["batch_size"],
            "cloning_learning_rate": study["cloning"]["learning_rate"],
            "rl_transitions": (256 if smoke else study["ppo"]["transitions"]) if rl else 0,
            "episode_decisions": 1024 if smoke else 12000,
            "evaluation_decisions": 128 if smoke else 1800,
            "ppo": {"n_steps": 256 if smoke else study["ppo"]["rollout_steps"],
                    "batch_size": 128 if smoke else study["ppo"]["batch_size"],
                    "n_epochs": 2 if smoke else study["ppo"]["epochs"],
                    "gae_lambda": study["ppo"]["gae_lambda"]},
            "normalization": "Eligible demo RMS, frozen for every arm including scratch PPO",
            "work_caveat": "BC-only has no RL; BC+PPO adds supervised work to the common PPO budget"}


def fit_common_normalizer(vector, observations):
    require(vector.norm_obs and not vector.norm_reward
            and vector.gamma == RewardConfig().gamma(1)
            and vector.obs_rms.count == 0.0001,
            "Common normalizer must be fresh, one-tick and raw-reward")
    observations = np.asarray(observations)
    require(observations.dtype == np.float32 and observations.ndim == 2
            and observations.shape[1] == 217 and 1 <= len(observations) <= 12000
            and np.isfinite(observations).all(), "Invalid common normalization data")
    vector.obs_rms.update(observations)
    vector.training = False
    return {"source": "Eligible training demonstrations only", "samples": len(observations),
            "raw_observations_sha256": hashlib.sha256(observations.tobytes()).hexdigest(),
            "frozen": True, "clip_obs": vector.clip_obs, "epsilon": vector.epsilon}


def rms_snapshot(vector):
    return {key: np.asarray(getattr(vector.obs_rms, key)).copy() for key in ("mean", "var", "count")}


def require_frozen_rms(vector, expected):
    require(vector.training is False and all(np.array_equal(
        expected[key], np.asarray(getattr(vector.obs_rms, key))) for key in expected),
        "Training changed the declared frozen normalization")


def require_model_settings(model, timing):
    require(model.n_envs == 1 and model.device.type == "cpu"
            and model.gamma == timing["gamma"] and model.gae_lambda == timing["gae_lambda"]
            and model.policy_kwargs.get("net_arch") == timing["architecture"]
            and all(getattr(model, key) == value for key, value in timing["ppo"].items()),
            "Actual PPO model differs from the bounded declared settings")


def learn_arm(model, vector, observations, actions, timing, physical_work, seed):
    require(timing == settings(timing["arm"], True),
            "Full imitation training requires future remote runner admission")
    require_model_settings(model, timing)
    require(physical_work.frame_skip == 1 and vector.gamma == timing["gamma"]
            and vector.norm_obs and not vector.norm_reward,
            "Imitation environment/normalizer differs from its physical contract")
    require(model.num_timesteps == physical_work.decisions == 0,
            "Imitation arm requires a fresh model/environment, no resume")
    frozen = rms_snapshot(vector)
    clone = None
    if timing["cloning_updates"]:
        clone = warm_start(model, vector, observations, actions,
                           updates=timing["cloning_updates"], batch_size=timing["cloning_batch_size"],
                           seed=seed, learning_rate=timing["cloning_learning_rate"],
                           fit_normalization=False)
    require_frozen_rms(vector, frozen)
    return clone, frozen


def fine_tune(model, vector, timing, physical_work, frozen, callback=None):
    require(timing == settings(timing["arm"], True),
            "Full PPO fine-tuning requires future remote runner admission")
    require_model_settings(model, timing)
    require(physical_work.frame_skip == 1 and vector.gamma == timing["gamma"]
            and vector.norm_obs and not vector.norm_reward,
            "Imitation environment/normalizer differs from its physical contract")
    require(model.num_timesteps == physical_work.decisions == 0, "No silent learner resume")
    require_frozen_rms(vector, frozen)
    begin = time.perf_counter()
    with OptimizerWork(model, "ppo") as work:
        if timing["rl_transitions"]:
            model.learn(total_timesteps=timing["rl_transitions"], callback=callback)
    require(model.num_timesteps == physical_work.decisions == timing["rl_transitions"],
            "Imitation PPO transitions disagree with physical accounting")
    require_frozen_rms(vector, frozen)
    return {"rl_transitions": model.num_timesteps, "optimizer_work": work.summary(),
            "physical_work": physical_work.summary(),
            "learning_wall_seconds": time.perf_counter() - begin,
            "normalization_unchanged": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=plan()["arms"], required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--seed", type=int, choices=plan()["training_seeds"], default=6)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--remote-training", action="store_true")
    args = parser.parse_args()
    if not args.smoke or args.remote_training:
        parser.error("Full imitation runs require the separately admitted remote runner")
    timing = settings(args.arm, True)
    current = fingerprint()
    arrays, data = load(args.dataset, current)
    eligible = arrays["eligible"]
    require(eligible.any(), "No physically successful training demonstrations")
    observations, actions = arrays["observations"][eligible], arrays["actions"][eligible]
    import torch
    import stable_baselines3 as sb3
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    from research.fast_bridge import FastBridge
    from research.browser_bridge import BrowserBridge
    from research.env import RealGettingOverItEnv
    from research.evaluation_cases import STANDARD_CASES
    from research.study_metrics import benchmark_contract, enable_platform_support
    from research.train import evaluate
    torch.set_num_threads(1)
    output = args.output_dir or ROOT / "artifacts" / (
        "imitation_arm_smoke_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    require(output.is_absolute() and not output.exists(), "Use a new absolute output directory")
    output.mkdir(parents=True, exist_ok=False)

    def write(filename, value):
        (output / filename).write_text(json.dumps(value, indent=2), encoding="utf-8")

    with FastBridge(headless=True) as bridge:
        env = RealGettingOverItEnv(bridge=bridge, frame_skip=1,
                                  horizon=timing["episode_decisions"])
        enable_platform_support(env)
        physical = PhysicalWork(env)
        vector = VecNormalize(DummyVecEnv([lambda: physical]), norm_reward=False,
                              gamma=timing["gamma"], clip_reward=np.inf)
        try:
            normalization = fit_common_normalizer(vector, observations)
            model = sb3.PPO("MlpPolicy", vector, seed=args.seed, device="cpu",
                            gamma=timing["gamma"], **timing["ppo"],
                            policy_kwargs={"net_arch": timing["architecture"]})
            write("manifest.json", {"version": VERSION, "purpose": "Pipeline-only three-arm smoke",
                  "config": vars(args) | {"dataset": str(args.dataset), "output_dir": str(output)},
                  "settings": timing, "dataset_sha256": data["data_sha256"],
                  "normalization_contract": normalization, "reward_contract": RewardConfig().describe(1),
                  "evaluation_contract": {"cases": [c.describe() for c in STANDARD_CASES],
                                          "benchmarks": benchmark_contract(True)},
                  "python": platform.python_version(), "numpy": np.__version__,
                  "torch": torch.__version__, "stable_baselines3": sb3.__version__, **current})
            vector.save(str(output / "normalization.pkl"))

            def reference_evaluation():
                with BrowserBridge(driver="selenium", headless=True) as reference:
                    return evaluate(model, vector, reference, "absolute", True,
                                    timing["evaluation_decisions"], (), cases=STANDARD_CASES,
                                    frame_skip=1, physical_case_clock=True, secondary_support=True)

            untrained = reference_evaluation()
            clone, frozen = learn_arm(model, vector, observations, actions, timing, physical, args.seed)
            after_cloning = reference_evaluation() if clone else None
            if clone:
                model.save(str(output / "after_cloning_model"))
            class Trace(BaseCallback):
                def _on_step(self):
                    info = {key: value for key, value in self.locals["infos"][0].items()
                            if key not in ("terminal_observation", "episode")}
                    info.update(transition=self.num_timesteps,
                                action=self.locals["actions"][0].tolist(),
                                controlled_physics_ticks_total=physical.controlled_ticks,
                                reset_settling_physics_ticks_total=physical.reset_ticks)
                    with (output / "physical_trace.jsonl").open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(info) + "\n")
                    return True
            training = fine_tune(model, vector, timing, physical, frozen, Trace())
            final = reference_evaluation() if timing["rl_transitions"] else after_cloning
            model.save(str(output / "model"))
            vector.save(str(output / "normalization.pkl"))
            write("training_summary.json", {"complete": True, "settings": timing, "cloning": clone,
                  **training, "scope": "BC and RL recorded separately; evaluation/reset work not training"})
            write("evaluation.json", {"evaluation_backend": "reference", "untrained": untrained,
                  "after_cloning": after_cloning, "final": final,
                  "warning": "Pipeline-only smoke; no skill, robustness or full-game claim"})
        finally:
            vector.close()
    print("Evidence:", output)


if __name__ == "__main__":
    main()
