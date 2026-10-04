"""Closed-loop inference parity, optionally for a trusted saved research trial."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import numpy as np

from research.browser_bridge import BrowserBridge, ROOT
from research.fast_bridge import FastBridge
from research.env import RealGettingOverItEnv
from research.provenance import fingerprint
from research.reward import RewardConfig
from research.fast_fidelity import compare
from research.evaluation_cases import STANDARD_CASES, perturb
from research.case_clock import PhysicalCaseClock
from research.study_metrics import enable_platform_support


def rollout(model, rms, bridge, config, decisions, case=None):
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    repeat = config.get("frame_skip", 4)
    physical_clock = config.get("timing_study", False)
    if (type(decisions) is not int or not 1 <= decisions <= 512
            or type(repeat) is not int or repeat not in (1, 4)
            or type(physical_clock) is not bool or (repeat != 4 and not physical_clock)):
        raise ValueError("Invalid policy fidelity timing contract")
    reward = RewardConfig(profile=config.get("reward_profile", "settled"),
                          discount_half_life_seconds=config.get("discount_half_life", 120))
    if hasattr(model, "gamma") and model.gamma != reward.gamma(repeat):
        raise ValueError("Policy discount differs from its fidelity environment")
    env = RealGettingOverItEnv(bridge=bridge, action_mode=config.get("action", "absolute"),
                              terrain=not config.get("no_terrain", False), horizon=decisions,
                              frame_skip=repeat, reward_config=reward)
    if physical_clock:
        enable_platform_support(env)
    vector = VecNormalize(DummyVecEnv([lambda: env]), norm_obs=True, norm_reward=False, gamma=env.gamma)
    vector.obs_rms = rms
    vector.training = False
    vector.seed(case.reset_seed if case else 42)
    observation = vector.reset()
    rng = np.random.default_rng(case.noise_seed if case else 0)
    clock = PhysicalCaseClock(case) if physical_clock and case else None
    elapsed_ticks = 0
    records = []
    begin = time.perf_counter()
    try:
        for index in range(decisions):
            action, _ = model.predict(observation, deterministic=True)
            if clock is not None:
                applied = clock.apply(action, elapsed_ticks)
            else:
                applied = (np.asarray([case.warmup[index]], dtype=np.float32)
                           if case and index < len(case.warmup)
                           else perturb(action, case, rng) if case else action)
            observation, rewards, done, info = vector.step(applied)
            if physical_clock:
                ticks = info[0]["physics_ticks"]
                if type(ticks) is not int or not 1 <= ticks <= repeat:
                    raise RuntimeError("Invalid fidelity physical tick count")
                elapsed_ticks += ticks
            records.append({"action": action[0].tolist(), "observation": observation[0].tolist(),
                            "applied_action": applied[0].tolist(),
                            "reward": float(rewards[0]), "info": {
                                k: v for k, v in info[0].items() if k not in ("terminal_observation", "episode")},
                            # VecEnv auto-resets on done; info is the authoritative
                            # final physical state, not the freshly reset env.state.
                            "state": dict(env.state) if not done[0] else None})
            if done[0]: break
    finally:
        vector.close()
    return records, time.perf_counter() - begin


def compare_rollouts(reference, fast):
    if not reference or len(reference) != len(fast):
        raise AssertionError("Policy trajectory lengths differ or are empty")
    errors = {"max_normalized_observation_error": 0.0, "max_reward_error": 0.0,
              "max_telemetry_error": 0.0}
    for a, b in zip(reference, fast):
        if not np.array_equal(a["action"], b["action"]):
            raise AssertionError("Policy actions diverge")
        if not np.array_equal(a["applied_action"], b["applied_action"]):
            raise AssertionError("Applied actions diverge")
        if not np.allclose(a["observation"], b["observation"], rtol=0, atol=1e-6):
            raise AssertionError("Normalized observations diverge")
        if abs(a["reward"] - b["reward"]) >= 1e-8:
            raise AssertionError("Rewards diverge")
        if a["info"] != b["info"] or (a["state"] is None) != (b["state"] is None):
            raise AssertionError("Physical/reward/outcome info diverges")
        errors["max_normalized_observation_error"] = max(
            errors["max_normalized_observation_error"],
            float(np.max(np.abs(np.asarray(a["observation"]) - b["observation"]))))
        errors["max_reward_error"] = max(errors["max_reward_error"], abs(a["reward"] - b["reward"]))
        if a["state"] is not None:
            errors["max_telemetry_error"] = max(
                errors["max_telemetry_error"], max(compare([a["state"]], [b["state"]]).values()))
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", type=Path, help="Absolute path to a trusted current trial")
    parser.add_argument("--decisions", type=int, default=128)
    parser.add_argument("--case", choices=[case.name for case in STANDARD_CASES],
                        help="Replay an explicitly selected declared legal perturbation")
    args = parser.parse_args()
    if not 1 <= args.decisions <= 512:
        parser.error("Local policy fidelity budget must be 1..512 decisions")
    import torch
    import stable_baselines3 as sb3
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    torch.set_num_threads(1)
    output = ROOT / "artifacts" / ("policy_fidelity_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True)
    report = {"provenance": fingerprint(), "cases": {}}
    selected_case = next((case for case in STANDARD_CASES if case.name == args.case), None)
    report["evaluation_case"] = selected_case.describe() if selected_case else None
    with BrowserBridge(driver="selenium", headless=False) as reference, FastBridge(headless=False) as fast:
        if args.trial:
            if not args.trial.is_absolute():
                parser.error("Pass an absolute trial directory")
            manifest = json.loads((args.trial / "manifest.json").read_text(encoding="utf-8"))
            current = fingerprint()
            for key in ("project_sha256", "runtime_sha256", "asset_set_sha256"):
                if manifest.get(key) != current[key]: raise ValueError("Trial game fingerprint mismatch")
            for path in ("research/env.py", "research/reward.py", "research/runtime.js",
                         "research/terrain.py", "research/collision_memo.js", "research/fast_rpc.js"):
                if manifest["source_sha256"].get(path) != current["source_sha256"][path]:
                    raise ValueError("Trial contract changed: " + path)
            config = manifest["config"]
            repeat = config.get("frame_skip", 4)
            reward_config = RewardConfig(profile=config["reward_profile"],
                                         discount_half_life_seconds=config["discount_half_life"])
            dummy = VecNormalize(DummyVecEnv([lambda: RealGettingOverItEnv(
                bridge=reference, action_mode=config["action"], terrain=not config["no_terrain"],
                frame_skip=repeat, reward_config=reward_config)]),
                norm_obs=True, norm_reward=False, gamma=reward_config.gamma(repeat))
            normalizer = VecNormalize.load(str(args.trial / "normalization.pkl"), dummy.venv)
            if normalizer.norm_reward:
                raise ValueError("Trial uses an incompatible normalized reward")
            algorithm = sb3.PPO if config["algorithm"] == "ppo" else sb3.SAC
            fixtures = [("saved_" + config["algorithm"], algorithm.load(str(args.trial / "model.zip"), device="cpu"), config)]
            if fixtures[0][1].gamma != reward_config.gamma(repeat) or normalizer.gamma != reward_config.gamma(repeat):
                raise ValueError("Trial reward/normalization/policy discounts disagree")
            rms = normalizer.obs_rms
        else:
            dummy = VecNormalize(DummyVecEnv([lambda: RealGettingOverItEnv(bridge=reference)]),
                                 norm_obs=True, norm_reward=False, gamma=RewardConfig().gamma(4))
            rms = dummy.obs_rms
            config = {"action": "absolute", "no_terrain": False}
            fixtures = [(name, algorithm("MlpPolicy", dummy, seed=0, device="cpu",
                                        gamma=RewardConfig().gamma(4), policy_kwargs={"net_arch": [32, 32]}), config)
                        for name, algorithm in (("untrained_ppo", sb3.PPO), ("untrained_sac", sb3.SAC))]
            # A network-output fixture tests contact-rich closed-loop transfer.
            # It is not learned behavior or a competent policy.
            push = sb3.PPO("MlpPolicy", dummy, seed=0, device="cpu", gamma=RewardConfig().gamma(4),
                          policy_kwargs={"net_arch": [32, 32]})
            with torch.no_grad():
                push.policy.action_net.weight.zero_()
                push.policy.action_net.bias.copy_(torch.tensor([0.0, -0.625]))
            fixtures.append(("constant_push_network_fixture", push, config))
        for name, model, config in fixtures:
            a, a_time = rollout(model, rms, reference, config, args.decisions, selected_case)
            b, b_time = rollout(model, rms, fast, config, args.decisions, selected_case)
            errors = compare_rollouts(a, b)
            report["cases"][name] = {"decisions": len(a), "reference_seconds": a_time, "fast_seconds": b_time,
                                    **errors,
                                    "actions_observations_rewards_match": True,
                                    "max_gain": a[-1]["info"]["max_gain"],
                                    "retained_gain": a[-1]["info"]["retained_gain"],
                                    "milestone_success": a[-1]["info"]["milestone_success"],
                                    "success": a[-1]["info"]["success"]}
            (output / (name + ".json")).write_text(json.dumps({"reference": a, "fast": b}), encoding="utf-8")
            print(name, report["cases"][name], flush=True)
        dummy.close()
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Evidence:", output)


if __name__ == "__main__":
    main()
