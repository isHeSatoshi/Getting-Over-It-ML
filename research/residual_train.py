"""Fresh residual PPO trainer; actual full work is remote-permit only."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform

import numpy as np

from research.demonstrations import require
from research.optimizer_work import OptimizerWork
from research.provenance import fingerprint
from research.residual_execution import load_trainer_grant, require_permit
from research.residual_policy import ZeroResidualPolicy, new_normalizer, checkpoint_contract, validate_checkpoint
from research.residual_study import MAX_RESETS, SEEDS, TRANSITIONS, plan
from research.training_timing import PhysicalWork


class BoundedPhysicalWork(PhysicalWork):
    def __init__(self, env, *, decisions=TRANSITIONS, resets=MAX_RESETS):
        super().__init__(env)
        require(self.frame_skip == 1 and type(decisions) is int and 1 <= decisions <= TRANSITIONS
                and type(resets) is int and 1 <= resets <= MAX_RESETS, "Invalid bounded residual work")
        self.gamma = env.gamma
        self.decision_cap, self.reset_cap = decisions, resets

    def reset(self, **kwargs):
        require(self.resets < self.reset_cap, "Residual reset budget exhausted before resetting")
        return super().reset(**kwargs)

    def step(self, action):
        require(self.decisions < self.decision_cap, "Residual transition budget exhausted before physics")
        return super().step(action)


def settings(mock_smoke=False):
    require(type(mock_smoke) is bool, "Explicit mock-smoke flag")
    record = deepcopy(plan()["ppo"])
    if mock_smoke:
        record.update(n_steps=8, batch_size=4, n_epochs=1, target_kl=None)
    return record


def initialize(adapter, seed, *, mock_smoke=False):
    import torch
    from stable_baselines3 import PPO
    torch.set_num_threads(1)
    require(type(seed) is int and seed in SEEDS, "Undeclared residual seed")
    physical = BoundedPhysicalWork(adapter, decisions=8 if mock_smoke else TRANSITIONS)
    vector = new_normalizer(physical)
    model = PPO(ZeroResidualPolicy, vector, seed=seed, device="cpu", **settings(mock_smoke))
    return model, vector, physical


def learn(model, vector, physical, seed, *, permit=None, mock_smoke=False, callback=None):
    require(type(mock_smoke) is bool and model.seed == seed and model.device.type == "cpu"
            and model.n_envs == 1 and model.num_timesteps == physical.decisions == physical.resets == 0,
            "Residual training requires a fresh matched model/environment, not resume")
    if not mock_smoke:
        require_permit(permit, seed)
        require(physical.env.case is None, "No forced/noisy teacher controls during training")
    else:
        require(getattr(physical.env.unwrapped, "pipeline_mock_only", False) is True
                and not hasattr(physical.env.unwrapped, "bridge"),
                "Local optimizer smoke may use ONLY an explicit mock, never original game")
    expected = settings(mock_smoke)
    require(all(getattr(model, key) == value for key, value in expected.items() if key != "clip_range")
            and model.clip_range(1.) == expected["clip_range"]
            and vector.training and vector.norm_obs and not vector.norm_reward,
            "Residual PPO/normalizer settings changed")
    from stable_baselines3.common.callbacks import BaseCallback
    class Guard(BaseCallback):
        def _on_step(self):
            if not mock_smoke:
                require_permit(permit, seed)
            return True
    requested = 8 if mock_smoke else TRANSITIONS
    with OptimizerWork(model, "ppo") as work:
        model.learn(total_timesteps=requested, callback=[Guard()]+([] if callback is None else [callback]))
    calls = work.summary()["total_optimizer_step_calls"]
    require(model.num_timesteps == physical.decisions == physical.controlled_ticks == requested
            and 0 < calls <= (2 if mock_smoke else 3072), "Residual learner/physics/optimizer budget mismatch")
    return {"complete": True, "transitions": model.num_timesteps, "physical": physical.summary(),
            "optimizer": work.summary(), "mock_smoke": mock_smoke, "ppo": expected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, choices=SEEDS, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--remote-training", action="store_true")
    parser.add_argument("--mock-smoke", action="store_true")
    args = parser.parse_args()
    if not args.remote_training or args.mock_smoke:
        parser.error("CLI requires a fresh remote permit; local mock smoke is test API only")
    permit = load_trainer_grant(args)
    from research.phase_controller import load_prior
    from research.fast_bridge import FastBridge
    from research.browser_bridge import BrowserBridge
    from research.env import RealGettingOverItEnv
    from research.residual_env import ResidualGettingOverItEnv
    from research.residual_evaluation import evaluate
    from research.residual_campaign import write_evaluation
    from research.study_metrics import enable_platform_support
    import torch
    import stable_baselines3 as sb3
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import VecNormalize, DummyVecEnv
    current = fingerprint()
    prior, actions, _ = load_prior(args.prior, current)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False)
    def write(name, record):
        temporary = output/(name+".tmp")
        temporary.write_text(json.dumps(record, indent=2, allow_nan=False))
        temporary.replace(output/name)
    with FastBridge(headless=True) as fast, BrowserBridge(driver="selenium", headless=True) as reference:
        bootstrap = fast.read_state()["tick"]+reference.read_state()["tick"]
        require(bootstrap == 240, "Unexpected bridge bootstrap work")
        raw = RealGettingOverItEnv(bridge=fast, action_mode="absolute", terrain=True, frame_skip=1, horizon=1800)
        enable_platform_support(raw)
        adapter = ResidualGettingOverItEnv(raw, prior, actions)
        model, vector, physical = initialize(adapter, args.seed)
        schema = checkpoint_contract(adapter)
        write("manifest.json", {"version": "residual-trainer-v1", "purpose": "admitted remote residual PPO",
              "seed": args.seed, "plan": plan(), "admission": permit.record(), "provenance": current,
              "checkpoint_contract": schema, "device": "cpu", "python": platform.python_version(),
              "numpy": np.__version__, "torch": torch.__version__, "stable_baselines3": sb3.__version__})
        def guard():
            permit.verify(args.seed)
        baseline = evaluate(model.policy, vector, reference, prior, actions, zero_actor=True, guard=guard)
        write_evaluation(output, "baseline", baseline)
        checkpoints = []
        class Capture(BaseCallback):
            def _on_step(self):
                if self.num_timesteps % 256 == 0:
                    info = deepcopy(self.locals["infos"][0])
                    info.pop("terminal_observation", None)
                    with (output/"training_trace.jsonl").open("a") as stream:
                        stream.write(json.dumps({"transition": self.num_timesteps, "info": info,
                            "policy_sample_before_residual_clipping": self.locals["actions"][0].tolist(),
                            "physical": physical.summary()}, allow_nan=False)+"\n")
                return True
            def _on_rollout_start(self):
                # Previous rollout's optimizer is complete; snapshot exactly that update boundary.
                if self.num_timesteps in (65536,):
                    save_checkpoint(self.num_timesteps)
        def save_checkpoint(step):
            guard()
            model.save(output/f"model_{step}.zip")
            vector.save(output/f"normalizer_{step}.pkl")
            write(f"checkpoint_{step}.json", {"contract": schema, "transitions": step,
                  "model_sha256": hashlib.sha256((output/f"model_{step}.zip").read_bytes()).hexdigest(),
                  "normalizer_sha256": hashlib.sha256((output/f"normalizer_{step}.pkl").read_bytes()).hexdigest(),
                  "physical": physical.summary(), "admission": permit.record()})
            checkpoints.append(step)
        try:
            training = learn(model, vector, physical, args.seed, permit=permit, callback=Capture())
            save_checkpoint(TRANSITIONS)
            require(checkpoints == [65536, TRANSITIONS], "Missing declared update-boundary snapshots")
            vector.training = False
            after = evaluate(model.policy, vector, reference, prior, actions, guard=guard)
            write_evaluation(output, "final", after)
            loaded_vector = VecNormalize.load(output/f"normalizer_{TRANSITIONS}.pkl",
                                              DummyVecEnv([lambda: physical]))
            loaded_vector.training = False
            loaded = sb3.PPO.load(output/f"model_{TRANSITIONS}.zip", env=loaded_vector, device="cpu")
            validate_checkpoint(loaded.policy, loaded_vector, schema, adapter)
            contexts = np.asarray([row["trace"][0]["actor_input"] for row in after], np.float32)
            require(np.array_equal(model.predict(vector.normalize_obs(contexts), deterministic=True)[0],
                                   loaded.predict(loaded_vector.normalize_obs(contexts), deterministic=True)[0]),
                    "Saved residual policy/normalizer replay mismatch")
            training.update(seed=args.seed, plan=plan(), checkpoints=checkpoints,
                            bootstrap_ticks=bootstrap, saved_reload_exact=True,
                            normalization_source="Actual online training contexts only; evaluation frozen")
            write("training_summary.json", training)
        finally:
            vector.close()
    print("Residual PPO run complete, physical goal requires independent contract review")


if __name__ == "__main__":
    main()
