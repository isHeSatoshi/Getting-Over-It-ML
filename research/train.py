"""Explicit algorithm/action ablations. Local runs are bounded CPU smoke tests."""
import argparse
from datetime import datetime, timezone
import json
import os
import platform
import time
import numpy as np

from research.browser_bridge import ROOT
from research.env import RealGettingOverItEnv
from research.validate import validate
from research.provenance import fingerprint
from research.reward import RewardConfig, PROFILES
from research.backends import make_bridge
from research.evaluation_cases import STANDARD_CASES, EvaluationCase, perturb
from research.optimizer_work import OptimizerWork, WORK_VERSION
from research.case_clock import PhysicalCaseClock


def evaluate(model, normalization, bridge, action_mode, terrain, decisions, seeds,
             reward_config=None, cases=None, *, frame_skip=4, physical_case_clock=False):
    if (type(frame_skip) is not int or frame_skip not in (1, 4)
            or type(decisions) is not int or decisions < 1
            or type(physical_case_clock) is not bool):
        raise ValueError("Invalid evaluation timing configuration")
    if frame_skip != 4 and not physical_case_clock:
        raise ValueError("One-tick evaluation requires the physical case clock")
    reward_config = reward_config if reward_config is not None else RewardConfig()
    gamma = reward_config.gamma(frame_skip)
    if model.gamma != gamma or normalization.gamma != model.gamma:
        raise ValueError("Reward, learner, and normalization discounts must match")
    if normalization.norm_reward:
        raise ValueError("This reward contract requires raw, unnormalized training rewards")
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    environment = RealGettingOverItEnv(
        bridge=bridge, action_mode=action_mode, terrain=terrain, horizon=decisions,
        frame_skip=frame_skip, reward_config=reward_config)
    evaluation = VecNormalize(DummyVecEnv([lambda: environment]),
                              norm_obs=True, norm_reward=False, gamma=gamma)
    evaluation.obs_rms = normalization.obs_rms
    evaluation.training = False
    records = []
    selected = cases if cases is not None else tuple(EvaluationCase(f"reset_{seed}", seed) for seed in seeds)
    try:
        for case in selected:
            seed = case.reset_seed
            evaluation.seed(seed)
            observation = evaluation.reset()
            rng = np.random.default_rng(case.noise_seed)
            clock = PhysicalCaseClock(case) if physical_case_clock else None
            controlled_ticks = 0
            reset_ticks = environment.state["tick"] if physical_case_clock else 0
            trace = []
            for index in range(decisions):
                action, _ = model.predict(observation, deterministic=True)
                if clock is not None:
                    applied = clock.apply(action, controlled_ticks)
                else:
                    applied = (np.asarray([case.warmup[index]], dtype=np.float32)
                               if index < len(case.warmup) else perturb(action, case, rng))
                observation, _, done, info = evaluation.step(applied)
                if clock is not None:
                    ticks = info[0]["physics_ticks"]
                    if type(ticks) is not int or not 1 <= ticks <= frame_skip:
                        raise RuntimeError("Invalid controlled physics tick count")
                    controlled_ticks += ticks
                    # VecEnv already settled a new spawn on terminal/truncated
                    # steps; count its reset work separately from the trajectory.
                    if done[0]:
                        reset_ticks += environment.state["tick"]
                trace.append({"action": action[0].tolist(),
                              "applied_action": applied[0].tolist(),
                              **{k: v for k, v in info[0].items()
                                 if k not in ("terminal_observation", "episode")}})
                if done[0]:
                    break
            record = {"case": case.describe(), "seed": seed, "final": trace[-1],
                      "decisions": len(trace), "trace": trace}
            if clock is not None:
                record.update(
                    timing_contract={"version": "physical-case-evaluation-v1",
                                     "frame_skip": frame_skip,
                                     "physics_hz": reward_config.physics_hz,
                                     "perturbation_hold_ticks": clock.hold_ticks,
                                     "requested_physics_ticks": decisions * frame_skip},
                    controlled_physics_ticks=controlled_ticks,
                    reset_settling_physics_ticks=reset_ticks)
            records.append(record)
    finally:
        evaluation.close()
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--algorithm", choices=["ppo", "sac"], required=True)
    parser.add_argument("--action", choices=["absolute", "velocity", "polar"], default="absolute")
    parser.add_argument("--no-terrain", action="store_true")
    parser.add_argument("--driver", choices=["auto", "embedded", "selenium"], default="auto")
    parser.add_argument("--backend", choices=["reference", "fast"], default="fast")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--remote-training", action="store_true")
    parser.add_argument("--steps", type=int)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--reward-profile", choices=PROFILES, default="settled")
    parser.add_argument("--discount-half-life", type=float, default=120.0, help="Discount half-life in game seconds")
    parser.add_argument("--evaluation-decisions", type=int, default=450)
    parser.add_argument("--evaluation-suite", choices=["standard", "replay"], default="standard")
    parser.add_argument("--replay-buffer-size", type=int, default=200000)
    parser.add_argument("--output-dir", type=str, help="New absolute output directory; refuses existing paths")
    args = parser.parse_args()
    if args.smoke == args.remote_training:
        parser.error("Choose exactly one: --smoke or --remote-training")
    steps = args.steps if args.steps is not None else (512 if args.smoke else 1_000_000)
    if steps < 1 or (args.smoke and steps > 2048):
        parser.error("Local smoke tests are capped at 2048 transitions")
    if not 32 <= args.evaluation_decisions <= 3000 or not 1000 <= args.replay_buffer_size <= 1000000:
        parser.error("Invalid evaluation or replay buffer budget")
    if args.remote_training and os.environ.get("FACTORY_DESKTOP_CDP_PORT"):
        parser.error("Full training is disabled on this desktop. Use a separate training host.")
    if args.remote_training and args.driver == "embedded" and args.backend == "reference":
        parser.error("Remote training requires an isolated browser worker")
    try:
        reward_config = RewardConfig(profile=args.reward_profile,
                                     discount_half_life_seconds=args.discount_half_life)
    except ValueError as error:
        parser.error(str(error))
    gamma = reward_config.gamma(4)

    import torch
    import stable_baselines3 as sb3
    from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    torch.set_num_threads(1)
    from pathlib import Path
    output = Path(args.output_dir) if args.output_dir else ROOT / "artifacts" / (
        "trial_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    if not output.is_absolute():
        parser.error("Output directory must be absolute")
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_text(json.dumps({
        "config": vars(args), "steps": steps, "device": "cpu",
        "python": platform.python_version(), "numpy": np.__version__,
        "torch": torch.__version__, "stable_baselines3": sb3.__version__,
        "reward_contract": reward_config.describe(4),
        "reward_normalization": {"enabled": False, "clipping": "disabled", "units": "raw_task_units"},
        "optimizer_work_contract": {"version": WORK_VERSION,
                                    "units": "Completed optimizer.step calls per named optimizer"},
        "evaluation_contract": {"suite": args.evaluation_suite, "cases": [
            c.describe() for c in STANDARD_CASES] if args.evaluation_suite == "standard" else [],
            "decisions": 32 if args.smoke else args.evaluation_decisions},
        **fingerprint(),
        "purpose": "pipeline-only smoke test" if args.smoke else "remote research run",
    }, indent=2), encoding="utf-8")
    with make_bridge(args.backend, args.driver) as bridge:
        print("Validating the real-game state/action loop before training...", flush=True)
        proof = validate(bridge)
        (output / "validation.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
        vector = DummyVecEnv([lambda: Monitor(RealGettingOverItEnv(
            bridge=bridge, action_mode=args.action, terrain=not args.no_terrain,
            horizon=256 if args.smoke else 3000, reward_config=reward_config), str(output / "monitor.csv"),
            info_keywords=("max_gain", "retained_gain", "success"))])
        # Keep the raw objective. Online reward rescaling and nonlinear clipping
        # invalidate the fixed-scale potential-return contract during training.
        vector = VecNormalize(vector, norm_obs=True, norm_reward=False, gamma=gamma, clip_reward=np.inf)
        algorithm = sb3.PPO if args.algorithm == "ppo" else sb3.SAC
        kwargs = dict(seed=args.seed, device="cpu", verbose=1, gamma=gamma,
                      policy_kwargs={"net_arch": [64, 64] if args.smoke else [256, 256]})
        if args.algorithm == "ppo":
            kwargs.update(n_steps=64 if args.smoke else 2048, batch_size=32 if args.smoke else 256,
                          n_epochs=2 if args.smoke else 10)
        else:
            kwargs.update(learning_starts=64 if args.smoke else 10000,
                          buffer_size=4096 if args.smoke else args.replay_buffer_size,
                          batch_size=32 if args.smoke else 256)
        model = algorithm("MlpPolicy", vector, **kwargs)
        evaluation_budget = 32 if args.smoke else args.evaluation_decisions
        evaluation_cases = STANDARD_CASES if args.evaluation_suite == "standard" else None
        # Evaluation uses the rendered, uncached reference, not the training worker.
        with make_bridge("reference", "selenium") as reference:
            before = evaluate(model, vector, reference, args.action, not args.no_terrain,
                              evaluation_budget, (1001, 1002, 1003), reward_config, evaluation_cases)
        class PhysicalTrace(BaseCallback):
            def _on_step(self):
                if args.smoke or self.num_timesteps % 100 == 0:
                    info = self.locals["infos"][0]
                    record = {k: v for k, v in info.items() if k not in ("terminal_observation", "episode")}
                    record.update(transition=self.num_timesteps, action=self.locals["actions"][0].tolist())
                    with (output / "physical_trace.jsonl").open("a", encoding="utf-8") as log:
                        log.write(json.dumps(record) + "\n")
                return True
        try:
            learning_start = time.perf_counter()
            with OptimizerWork(model, args.algorithm) as optimizer_work:
                model.learn(total_timesteps=steps, callback=[PhysicalTrace(), CheckpointCallback(
                    save_freq=10000, save_path=str(output / "checkpoints"),
                    save_vecnormalize=True, save_replay_buffer=False)])
            training_summary = {"actual_transitions": model.num_timesteps, "requested_transitions": steps,
                                "optimizer_work": optimizer_work.summary(),
                                "learning_wall_seconds": time.perf_counter() - learning_start,
                                "complete": True, "learner_gamma": model.gamma,
                                "torch_threads": torch.get_num_threads()}
            model.save(str(output / "model"))
            vector.save(str(output / "normalization.pkl"))
            if args.algorithm == "sac" and not args.smoke:
                model.save_replay_buffer(str(output / "replay_buffer.pkl"))
            with make_bridge("reference", "selenium") as reference:
                after = evaluate(model, vector, reference, args.action, not args.no_terrain,
                                 evaluation_budget, (1001, 1002, 1003), reward_config, evaluation_cases)
            (output / "training_summary.json").write_text(json.dumps(training_summary, indent=2), encoding="utf-8")
            (output / "evaluation.json").write_text(
                json.dumps({"training_backend": args.backend, "evaluation_backend": "reference",
                            "before": before, "after": after,
                            "warning": "Smoke trials do not establish learning or competence." if args.smoke else ""}, indent=2),
                encoding="utf-8")
            for label, records in (("before", before), ("after", after)):
                print(label, [{"case": r["case"]["name"], "seed": r["seed"], "max_gain": r["final"]["max_gain"],
                               "retained_gain": r["final"]["retained_gain"],
                               "success": r["final"]["success"],
                               "milestone_success": r["final"]["milestone_success"]} for r in records], flush=True)
        finally:
            vector.close()
    print("Evidence:", output)


if __name__ == "__main__":
    main()
