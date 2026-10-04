"""Actor-only PPO warm start. CLI permits bounded pipeline smokes only."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import numpy as np

from research.browser_bridge import ROOT
from research.demonstrations import load, require
from research.provenance import fingerprint
from research.reward import RewardConfig

VERSION = "ppo-actor-demonstration-warm-start-v1"


def warm_start(model, normalization, observations, actions, *, updates=8, batch_size=64,
               seed=0, learning_rate=0.001, pipeline_smoke=True):
    """Separate BC optimizer leaves value, log-std and PPO optimizer state alone."""
    import torch
    from stable_baselines3 import PPO
    require(isinstance(model, PPO) and type(pipeline_smoke) is bool and pipeline_smoke,
            "Full cloning requires a separately admitted remote experiment")
    require(type(updates) is int and 1 <= updates <= 8
            and type(batch_size) is int and 1 <= batch_size <= 64
            and type(seed) is int and 0 <= seed < 2**32
            and np.isfinite(learning_rate) and 0 < learning_rate <= 0.01,
            "Invalid bounded cloning smoke budget")
    require(not normalization.norm_reward and normalization.norm_obs
            and model.gamma == normalization.gamma == RewardConfig().gamma(1),
            "Warm start needs matching one-tick discounts and raw rewards")
    # Default MlpPolicy shares a parameter-free FlattenExtractor. It is safe,
    # but a trainable shared extractor would also change the value function.
    require(not any(True for _ in model.policy.features_extractor.parameters()),
            "Warm start does not support a trainable shared feature extractor")
    observations, actions = np.asarray(observations), np.asarray(actions)
    n = len(observations)
    require(observations.dtype == actions.dtype == np.float32 and 1 <= n <= 12000
            and observations.shape == (n, 217) and actions.shape == (n, 2)
            and np.isfinite(observations).all() and np.isfinite(actions).all()
            and np.abs(actions).max() <= 1 and model.observation_space.shape == (217,)
            and model.action_space.shape == (2,), "Invalid cloning data/model shapes")
    require(model.num_timesteps == 0 and not model.policy.optimizer.state
            and not getattr(model, "_demonstration_warm_started", False),
            "Warm start requires a fresh learner, never silent checkpoint resume")
    normalization.obs_rms.update(observations)
    normalization.training = False
    normalized = normalization.normalize_obs(observations)
    inputs = torch.as_tensor(normalized, device=model.device)
    targets = torch.as_tensor(actions, device=model.device)
    actor = list(model.policy.mlp_extractor.policy_net.parameters()) + list(model.policy.action_net.parameters())
    require(bool(actor), "Missing actor parameters")
    optimizer = torch.optim.Adam(actor, lr=learning_rate)
    rng = np.random.default_rng(seed)
    was_training = model.policy.training

    def prediction(obs):
        return model.policy.get_distribution(obs).distribution.mean

    with torch.no_grad():
        before = float(torch.mean((prediction(inputs) - targets) ** 2).cpu())
    begin = time.perf_counter()
    try:
        model.policy.set_training_mode(True)
        for _ in range(updates):
            indices = rng.integers(0, n, size=batch_size)
            optimizer.zero_grad(set_to_none=True)
            loss = torch.mean((prediction(inputs[indices]) - targets[indices]) ** 2)
            require(bool(torch.isfinite(loss)), "Non-finite cloning loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(actor, 1.0, error_if_nonfinite=True)
            optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        with torch.no_grad():
            after = float(torch.mean((prediction(inputs) - targets) ** 2).cpu())
    finally:
        model.policy.set_training_mode(was_training)
    model._demonstration_warm_started = True
    return {"version": VERSION, "purpose": "Pipeline-only smoke, NOT skill acquisition evidence",
            "samples": n, "optimizer_step_calls": updates, "batch_size": batch_size,
            "sample_presentations": updates * batch_size, "learning_rate": learning_rate,
            "seed": seed, "mean_squared_action_error_before": before,
            "mean_squared_action_error_after": after,
            "wall_seconds": time.perf_counter() - begin,
            "rl_transitions": 0, "ppo_optimizer_state_preserved": True,
            "normalization": "Raw demo observations fit RMS once, then frozen for BC/evaluation",
            "limit": "Lower supervised error is not physical success or recovery coverage"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--updates", type=int, default=8)
    parser.add_argument("--seed", type=int, default=6)
    parser.add_argument("--headless", action="store_true", help="Keep a separate user's replay window undisturbed")
    args = parser.parse_args()
    if not args.smoke or not 1 <= args.updates <= 8:
        parser.error("Only --smoke with 1..8 cloning updates is admitted")
    current = fingerprint()
    arrays, data = load(args.dataset, current)
    selected = arrays["eligible"]
    require(selected.any(), "No physically successful demonstrations to clone")
    import torch
    import stable_baselines3 as sb3
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    from research.browser_bridge import BrowserBridge
    from research.fast_bridge import FastBridge
    from research.env import RealGettingOverItEnv
    from research.study_metrics import enable_platform_support
    from research.train import evaluate
    from research.evaluation_cases import STANDARD_CASES
    torch.set_num_threads(1)
    output = args.output_dir or ROOT / "artifacts" / (
        "cloning_smoke_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    require(output.is_absolute() and not output.exists(), "Use a new absolute output directory")
    output.mkdir(parents=True, exist_ok=False)
    with FastBridge(headless=args.headless) as bridge:
        env = RealGettingOverItEnv(bridge=bridge, frame_skip=1, horizon=128)
        enable_platform_support(env)
        vector = VecNormalize(DummyVecEnv([lambda: env]), norm_obs=True, norm_reward=False,
                              gamma=env.gamma, clip_reward=np.inf)
        try:
            model = sb3.PPO("MlpPolicy", vector, seed=args.seed, gamma=env.gamma,
                            gae_lambda=0.95**0.25, n_steps=128, batch_size=64,
                            device="cpu", policy_kwargs={"net_arch": [64, 64]})
            work = warm_start(model, vector, arrays["observations"][selected],
                              arrays["actions"][selected], updates=args.updates, seed=args.seed)
            model.save(str(output / "model"))
            vector.save(str(output / "normalization.pkl"))
            with BrowserBridge(driver="selenium", headless=args.headless) as reference:
                records = evaluate(model, vector, reference, "absolute", True, 128, (),
                                   cases=STANDARD_CASES[:1], frame_skip=1,
                                   physical_case_clock=True, secondary_support=True)
            (output / "manifest.json").write_text(json.dumps({
                "purpose": "Pipeline-only cloning smoke, NOT remote training or competence",
                "dataset_sha256": data["data_sha256"], "warm_start": work,
                "config": {"algorithm": "ppo", "action": "absolute", "frame_skip": 1,
                           "no_terrain": False, "timing_study": True, "reward_profile": "settled",
                           "discount_half_life": 120.0},
                "reward_contract": RewardConfig().describe(1), **current,
                "torch": torch.__version__, "stable_baselines3": sb3.__version__,
            }, indent=2), encoding="utf-8")
            (output / "evaluation.json").write_text(json.dumps({
                "evaluation_backend": "reference", "controlled_ticks_budget": 128,
                "records": records, "warning": "Bounded pipeline smoke, not learned robustness"},
                indent=2), encoding="utf-8")
        finally:
            vector.close()
    print("Evidence:", output)


if __name__ == "__main__":
    main()
