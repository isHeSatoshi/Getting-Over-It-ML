"""Actor-only logged-success trainer; full work requires an exact Linux parent grant."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import platform

import gymnasium as gym
import numpy as np

from research.behavior_cloning import warm_start
from research.demonstrations import require
from research.onstate_campaign import dataset_contract
from research.onstate_data import load
from research.onstate_study import ARMS, SEEDS, VALIDATION_CASES, plan
from research.provenance import fingerprint
from research.reward import RewardConfig

VERSION = "onstate-trainer-v1"


class NoTrainingPhysics(gym.Env):
    observation_space = gym.spaces.Box(-np.inf, np.inf, (217,), dtype=np.float32)
    action_space = gym.spaces.Box(-1, 1, (2,), dtype=np.float32)

    def reset(self, **kwargs):
        raise RuntimeError("Actor-only learning must never reset the training environment")

    def step(self, action):
        raise RuntimeError("Actor-only learning must never step the training environment")


def settings(smoke):
    require(type(smoke) is bool, "Invalid on-state run type")
    return {"architecture": [256, 256], "updates": 8 if smoke else 2000,
            "batch_size": 64 if smoke else 256, "learning_rate": .001,
            "gamma": RewardConfig().gamma(1), "gae_lambda": .95**.25,
            "n_steps": 128, "ppo_batch_size": 64, "n_epochs": 1}


def parameter_hash(model, nonactor=False):
    result = hashlib.sha256()
    for key, tensor in sorted(model.policy.state_dict().items()):
        if nonactor and key.startswith(("mlp_extractor.policy_net.", "action_net.")):
            continue
        result.update(key.encode())
        result.update(tensor.detach().cpu().numpy().tobytes())
    return result.hexdigest()


def run(args, permit=None, evaluator=None):
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    from research.imitation_train import rms_snapshot, require_frozen_rms
    require(args.arm in ARMS and type(args.seed) is int and args.seed in SEEDS
            and type(args.smoke) is type(args.remote_training) is bool
            and args.smoke != args.remote_training, "Invalid declared on-state run")
    if not args.smoke:
        from research.onstate_execution import require_permit
        require_permit(permit, args.arm, args.seed)
    require(evaluator is None or args.smoke, "Full stages require the original independent reference evaluator")
    current = fingerprint()
    data = load(Path(args.dataset), current)
    if permit:
        permit.verify(args.arm, args.seed, data.record["data_sha256"])
    cfg = settings(args.smoke)
    torch.set_num_threads(1)
    output = Path(args.output_dir)
    require(output.is_absolute() and not output.exists(), "Use a fresh absolute on-state output")
    output.mkdir(parents=True, exist_ok=False)

    def write(name, value):
        temporary = output / (name + ".tmp")
        temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
        temporary.replace(output / name)

    vector = VecNormalize(DummyVecEnv([NoTrainingPhysics]), norm_obs=True, norm_reward=False,
                          gamma=cfg["gamma"], clip_reward=np.inf)
    vector.obs_rms = copy.deepcopy(data.rms)
    vector.training = False
    try:
        model = PPO("MlpPolicy", vector, seed=args.seed, device="cpu", gamma=cfg["gamma"],
                    gae_lambda=cfg["gae_lambda"], n_steps=cfg["n_steps"],
                    batch_size=cfg["ppo_batch_size"], n_epochs=cfg["n_epochs"],
                    policy_kwargs={"net_arch": cfg["architecture"]})
        frozen = rms_snapshot(vector)
        initial, nonactor = parameter_hash(model), parameter_hash(model, True)
        require(model.num_timesteps == 0 and not model.policy.optimizer.state, "Fresh actor-only model required")
        write("manifest.json", {
            "version": VERSION, "purpose": ("Pipeline-only on-state smoke" if args.smoke else
                                           "admitted remote on-state comparison"),
            "config": {"arm": args.arm, "seed": args.seed, "smoke": args.smoke,
                       "remote_training": args.remote_training},
            "onstate_admission": permit.record() if permit else None,
            "settings": cfg, "dataset": dataset_contract(Path(args.dataset), current),
            "initial_parameters_sha256": initial, "reward_contract": plan()["reward_contract"],
            "device": "cpu",
            "reward_normalization": {"enabled": False, "clipping": "disabled", "units": "raw_task_units"},
            "environment_contract": plan()["environment"], "evaluation_contract": json.loads(
                json.dumps(plan()["evaluation"])), "python": platform.python_version(),
            "numpy": np.__version__, "torch": torch.__version__,
            "stable_baselines3": __import__("stable_baselines3").__version__, **current})
        vector.save(str(output / "normalization.pkl"))
        cases, decisions = (VALIDATION_CASES[:1], 128) if args.smoke else (VALIDATION_CASES, 1800)

        def evaluate_stage(stage):
            if permit:
                permit.verify(args.arm, args.seed)
            if evaluator is not None:
                records = evaluator(model, vector, cases, decisions)
            else:
                from research.browser_bridge import BrowserBridge
                from research.train import evaluate
                with BrowserBridge(driver="selenium", headless=True) as reference:
                    records = evaluate(model, vector, reference, "absolute", True, decisions, (),
                                       cases=cases, frame_skip=1, physical_case_clock=True,
                                       secondary_support=True)
            require_frozen_rms(vector, frozen)
            write(stage + "_evaluation.json", records)
            return records

        before = evaluate_stage("untrained")
        with (output / "cloning_progress.jsonl").open("x", encoding="utf-8") as progress:
            def record_progress(calls, original, logged):
                progress.write(json.dumps({"optimizer_step_calls": calls,
                    "sample_presentations": original + logged, "original_presentations": original,
                    "logged_success_presentations": logged,
                    "scope": "Durable completed prefix, not unreported work or full run completion"}) + "\n")
                progress.flush()
            clone = warm_start(model, vector, *data.training_arrays(args.arm), updates=cfg["updates"],
                               batch_size=cfg["batch_size"], learning_rate=cfg["learning_rate"],
                               seed=args.seed, fit_normalization=False, pipeline_smoke=args.smoke,
                               permit=permit, onstate_data=data, onstate_arm=args.arm,
                               onstate_progress=record_progress)
        require_frozen_rms(vector, frozen)
        require(parameter_hash(model, True) == nonactor and model.num_timesteps == 0
                and not model.policy.optimizer.state, "BC changed value/logstd/PPO state")
        model.save(str(output / "model"))
        vector.save(str(output / "normalization.pkl"))
        restored = PPO.load(str(output / "model.zip"), device="cpu")
        probe = data.arrays["normalized_observations"][:32]
        require(parameter_hash(restored) == parameter_hash(model)
                and np.array_equal(restored.predict(probe, deterministic=True)[0],
                                   model.predict(probe, deterministic=True)[0]),
                "Saved policy reload differs")
        # Durable completed learning work before potentially interrupted evaluation.
        training = {"complete": False, "settings": cfg, "cloning": clone, "normalization_unchanged": True,
                    "nonactor_parameters_unchanged": True, "saved_reload_exact": True,
                    "initial_parameters_sha256": initial, "final_parameters_sha256": parameter_hash(model),
                    "rl_transitions": 0, "ppo_optimizer_calls": 0,
                    "training_control_ticks": 0, "training_reset_ticks": 0, "torch_threads": torch.get_num_threads()}
        write("training_summary.json", training)
        after = evaluate_stage("after_cloning")
        if permit:
            permit.verify(args.arm, args.seed)
        write("evaluation.json", {"evaluation_backend": "reference",
                                 "checkpoints": ["untrained", "after_cloning"],
                                 "untrained": before, "after_cloning": after})
        training["complete"] = True
        write("training_summary.json", training)
        return training
    finally:
        vector.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--seed", choices=SEEDS, type=int, default=9)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--remote-training", action="store_true")
    args = parser.parse_args()
    if args.smoke == args.remote_training:
        parser.error("Choose bounded smoke or separately admitted remote execution")
    permit = None
    if args.remote_training:
        try:
            from research.onstate_execution import load_trainer_grant
            permit = load_trainer_grant(args)
        except (ValueError, KeyError, OSError):
            parser.error("Full on-state runs require the fresh data-bound Linux parent admission")
    run(args, permit)
    print("Completed declared on-state run:", args.output_dir)


if __name__ == "__main__":
    main()
