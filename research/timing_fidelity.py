"""Contact-rich timing-study fidelity with a reactive untrained network fixture."""
import argparse
from datetime import datetime, timezone
import json
from types import SimpleNamespace

import numpy as np

from research.browser_bridge import BrowserBridge, ROOT
from research.env import RealGettingOverItEnv
from research.evaluation_cases import STANDARD_CASES
from research.fast_bridge import FastBridge
from research.policy_fidelity import compare_rollouts, rollout
from research.provenance import fingerprint
from research.reward import RewardConfig
from research.study_metrics import benchmark_contract
from research.train import evaluate


def check(reference, fast, ticks):
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    if type(ticks) is not int or not 96 <= ticks <= 512 or ticks % 4:
        raise ValueError("Timing fidelity fixture must use 96..512 ticks, divisible by four")
    torch.set_num_threads(1)
    reward = RewardConfig()
    cases = tuple(case for case in STANDARD_CASES if case.name in (
        "nominal", "hammer_left", "action_noise_2"))
    report = {"purpose": "NOT_POLICY_SUCCESS: observation-dependent untrained network fixture",
              "physics_ticks_per_case": ticks, "cases": {},
              "limit": "Local tested contact sequences only, not all-game or cross-host policy equivalence"}
    evidence = {}
    for repeat in (1, 4):
        config = {"action": "absolute", "no_terrain": False, "frame_skip": repeat, "timing_study": True}
        dummy = VecNormalize(DummyVecEnv([lambda: RealGettingOverItEnv(
            bridge=reference, frame_skip=repeat)]), norm_obs=True, norm_reward=False,
            gamma=reward.gamma(repeat))
        try:
            model = PPO("MlpPolicy", dummy, seed=19, device="cpu", gamma=reward.gamma(repeat),
                        policy_kwargs={"net_arch": [32, 32]})
            # Leave the random observation-dependent feature network intact.
            # The small output weights vary targets with observations around
            # a legal downward plant; no learning or placement occurs.
            with torch.no_grad():
                model.policy.action_net.weight.zero_()
                model.policy.action_net.weight[0, 0] = 0.02
                model.policy.action_net.weight[1, 1] = 0.02
                model.policy.action_net.bias.copy_(torch.tensor([0.0, -0.625]))
            normalization = SimpleNamespace(gamma=model.gamma, norm_reward=False, obs_rms=dummy.obs_rms)
            for case in cases:
                key = f"repeat_{repeat}_{case.name}"
                a, a_time = rollout(model, dummy.obs_rms, reference, config, ticks // repeat, case)
                b, b_time = rollout(model, dummy.obs_rms, fast, config, ticks // repeat, case)
                errors = compare_rollouts(a, b)
                controlled_ticks = sum(row["info"]["physics_ticks"] for row in a)
                hammer_hits = sum(row["info"]["hammer_hit_frames"] for row in a)
                body_hits = sum(row["info"]["body_hit_frames"] for row in a)
                variation = float(np.ptp(np.asarray([row["action"] for row in a]), axis=0).max())
                if controlled_ticks != ticks or hammer_hits == 0 or body_hits == 0 or variation <= 1e-6:
                    raise AssertionError("Fixture lacks the declared duration, contacts or reactive actions")
                production = evaluate(
                    model, normalization, reference, "absolute", True, ticks // repeat, (), cases=(case,),
                    frame_skip=repeat, physical_case_clock=True, secondary_support=True)[0]
                expected = [{"action": row["action"], "applied_action": row["applied_action"], **row["info"]}
                            for row in a]
                if production["trace"] != expected:
                    raise AssertionError("Production evaluator and independent fidelity rollout differ")
                if production["final"]["milestone_contract"] != benchmark_contract(True):
                    raise AssertionError("Frozen central and secondary metric contracts differ")
                report["cases"][key] = {
                    "decisions": len(a), "controlled_ticks": controlled_ticks,
                    "hammer_hit_ticks": hammer_hits, "body_hit_ticks": body_hits,
                    "normalized_action_variation": variation, **errors,
                    "production_evaluator_trace_equal": True,
                    "retained_gain": a[-1]["info"]["retained_gain"],
                    "milestone_success": a[-1]["info"]["milestone_success"],
                    "full_climb_success": a[-1]["info"]["success"],
                    "reference_seconds": a_time, "fast_seconds": b_time,
                }
                evidence[key] = {"reference": a, "fast": b, "production_evaluation": production}
                print(key, report["cases"][key], flush=True)
        finally:
            dummy.close()
    return report, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticks", type=int, default=384)
    parser.add_argument("--headless", action="store_true", help="For an isolated remote preflight host")
    args = parser.parse_args()
    if not 96 <= args.ticks <= 512 or args.ticks % 4:
        parser.error("Use 96..512 ticks divisible by four")
    output = ROOT / "artifacts" / (
        "timing_fidelity_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True, exist_ok=False)
    with BrowserBridge(driver="selenium", headless=args.headless) as reference, FastBridge(
            headless=args.headless) as fast:
        report, evidence = check(reference, fast, args.ticks)
    report["provenance"] = fingerprint()
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "traces.json").write_text(json.dumps(evidence), encoding="utf-8")
    print("Evidence:", output)


if __name__ == "__main__":
    main()
