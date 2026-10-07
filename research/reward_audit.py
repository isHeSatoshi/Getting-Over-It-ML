"""Bounded physical reward ablations. Replays identical actions across profiles."""
import argparse
from datetime import datetime, timezone
import json
import math

import numpy as np
from research.browser_bridge import BrowserBridge, ROOT
from research.diagnose import summarize
from research.env import RealGettingOverItEnv
from research.provenance import fingerprint
from research.reward import ClimbReward, RewardConfig, PROFILES
from research.trajectory_search import commands_from_knots
from research.validate import validate, project_trace


def score_trace(start, trace, profile, frame_skip=4):
    reward = ClimbReward(RewardConfig(profile=profile), frame_skip)
    reward.reset(start)
    terms = []
    for i in range(0, len(trace), frame_skip):
        terms.append(reward.advance(trace[i:i + frame_skip]))
    discounted_shaping = sum(reward.gamma ** i * t["potential_shaping"] for i, t in enumerate(terms))
    expected = reward.gamma ** len(terms) * terms[-1]["reward_potential_after"]
    if not math.isclose(discounted_shaping, expected, abs_tol=1e-10):
        raise AssertionError("Potential telescoping contract failed on real trace")
    return {
        "profile": profile, "gamma": reward.gamma,
        "undiscounted_reward": sum(t["reward_total"] for t in terms),
        "discounted_reward": sum(reward.gamma ** i * t["reward_total"] for i, t in enumerate(terms)),
        "discounted_task_reward": sum(reward.gamma ** i * t["task_reward"] for i, t in enumerate(terms)),
        "discounted_shaping": discounted_shaping,
        "final_potential": terms[-1]["reward_potential_after"],
        "settled_gain": terms[-1]["settled_gain"], "terms": terms,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--driver", choices=["auto", "embedded", "selenium"], default="auto")
    args = parser.parse_args()
    output = ROOT / "artifacts" / ("reward_audit_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True)
    report = {"provenance": fingerprint(), "reward_contract": RewardConfig().describe(4), "experiments": {}}
    with BrowserBridge(driver=args.driver) as bridge:
        proof = validate(bridge)
        (output / "control_validation.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
        cases = {
            "idle": [{"x": 0, "y": 0, "id": i + 1} for i in range(180)],
            "down_hold": [{"x": 0, "y": -80, "id": i + 1} for i in range(180)],
            "sweep": [{"x": 90 * math.cos(-i * math.pi / 60),
                       "y": 90 * math.sin(-i * math.pi / 60), "id": i + 1} for i in range(240)],
        }
        rng = np.random.default_rng(0)
        actions = rng.uniform(-128, 128, size=(60, 2))
        cases["random"] = [{"x": float(a[0]), "y": float(a[1]), "id": 4 * i + j + 1}
                           for i, a in enumerate(actions) for j in range(4)]
        # Recreate the fixed initial search trajectory, not a new optimization.
        angles = -np.linspace(0, 359 * math.pi / 60, 19)
        knots = np.stack([90 * np.cos(angles), 90 * np.sin(angles)], axis=1)
        cases["smooth_sweep_hold"] = commands_from_knots(knots, 360)
        final = cases["smooth_sweep_hold"][-1]
        cases["smooth_sweep_hold"] += [{**final, "id": 361 + i} for i in range(120)]
        for name, commands in cases.items():
            start = bridge.reset(42)
            trace = bridge.step_commands(commands)
            results = [score_trace(start, trace, profile) for profile in PROFILES]
            assert all(r["discounted_task_reward"] == results[0]["discounted_task_reward"] for r in results)
            report["experiments"][name] = {"physical": summarize(start, trace), "profiles": results}
            (output / (name + ".json")).write_text(
                json.dumps({"start": start, "commands": commands[:len(trace)], "trace": trace}), encoding="utf-8")
            print(name, json.dumps({
                "physical": summarize(start, trace),
                "profiles": [{k: v for k, v in r.items() if k != "terms"} for r in results],
            }), flush=True)
        # Online observations/reward must match offline scoring, with no
        # reward-profile dependence in the game's underlying physics.
        direct_start = bridge.reset(42)
        direct = bridge.step_commands(cases["down_hold"][:120])
        online_metrics = []
        for profile in PROFILES:
            config = RewardConfig(profile=profile)
            env = RealGettingOverItEnv(bridge=bridge, terrain=False, horizon=30, reward_config=config)
            env.reset(seed=42)
            observed = []
            totals = []
            for _ in range(30):
                obs, total, term, trunc, info = env.step([0, -80 / 128])
                assert not term
                assert env.observation_space.contains(obs)
                observed.append(dict(env.state))
                totals.append(total)
            assert trunc
            assert project_trace(observed) == project_trace(direct[3::4])
            scored = score_trace(direct_start, direct, profile)
            assert np.allclose(totals, [t["reward_total"] for t in scored["terms"]], atol=1e-12)
            assert info["reward_gamma"] == env.gamma
            online_metrics.append({"profile": profile, "observation_size": len(obs),
                                   "retained_gain": info["retained_gain"], "reward_matches_offline": True})
        report["online_contracts"] = online_metrics
        # Terminal event is explicitly diagnostic, not claimed gameplay.
        start = bridge.reset(42)
        bridge.evaluate(
            "(()=>{const v=Object.values(vm.runtime.getTargetForStage().variables);"
            "for(const n of ['PLAYER X','HAMMER X']) v.find(x=>x.name===n).value=-900;return true;})()")
        falling = bridge.step_commands([{"x": 0, "y": 0, "id": i + 1} for i in range(120)])
        death_scores = [score_trace(start, falling, profile) for profile in PROFILES]
        assert all(math.isclose(s["discounted_reward"], death_scores[0]["discounted_reward"], abs_tol=1e-10)
                   for s in death_scores)
        assert all(s["final_potential"] == 0 for s in death_scores)
        report["diagnostic_death"] = death_scores
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Online contracts:", json.dumps(online_metrics))
    print("Evidence:", output)


if __name__ == "__main__":
    main()
