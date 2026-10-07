"""Replay a search result or evaluate this harness's model with saved normalization."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from research.browser_bridge import ROOT
from research.diagnose import summarize
from research.env import RealGettingOverItEnv
from research.trajectory_search import commands_from_knots
from research.reward import RewardConfig, REWARD_VERSION
from research.backends import make_bridge


def main():
    parser = argparse.ArgumentParser()
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--search", type=Path, help="Absolute path to search.json")
    selection.add_argument("--trial", type=Path, help="Absolute path to a trusted trial directory")
    parser.add_argument("--driver", choices=["auto", "embedded", "selenium"], default="auto")
    parser.add_argument("--backend", choices=["reference", "fast"], default="reference")
    parser.add_argument("--decisions", type=int, default=256)
    args = parser.parse_args()
    if not 1 <= args.decisions <= 3000:
        parser.error("Evaluation must be bounded to 1..3000 decisions")
    source = args.search or args.trial
    if not source.is_absolute():
        parser.error("Pass an absolute input path")
    output = ROOT / "artifacts" / ("replay_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True)
    with make_bridge(args.backend, args.driver) as bridge:
        if args.search:
            data = json.loads(args.search.read_text(encoding="utf-8"))
            knots = np.asarray(data["best_knots"], dtype=np.float64)
            if (knots.ndim != 2 or knots.shape[1] != 2 or not 2 <= len(knots) <= 1000
                    or not np.isfinite(knots).all() or np.abs(knots).max() > 128):
                raise ValueError("Invalid trajectory knots")
            ticks = data["config"]["ticks"]
            if not isinstance(ticks, int) or not 1 <= ticks <= 2400:
                raise ValueError("Invalid replay tick budget")
            commands = commands_from_knots(knots, ticks)
            start = bridge.reset(1001)
            trace = bridge.step_commands(commands)
            last = commands[-1]
            hold = bridge.step_commands([{**last, "id": len(commands) + i + 1} for i in range(120)])
            result = {**summarize(start, trace),
                      "retained_gain_after_hold": (hold[-1] if hold else trace[-1])["player_world_y"] - start["player_world_y"],
                      "commands": commands, "start": start, "trace": trace, "hold_trace": hold}
        else:
            import stable_baselines3 as sb3
            from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
            from research.train import evaluate
            from research.provenance import fingerprint
            manifest = json.loads((args.trial / "manifest.json").read_text(encoding="utf-8"))
            current = fingerprint()
            for key in ("project_sha256", "runtime_sha256", "asset_set_sha256"):
                if key not in manifest:
                    continue
                if current[key] != manifest[key]:
                    raise ValueError("Checkpoint game fingerprint mismatch")
            if manifest.get("reward_contract", {}).get("version") != REWARD_VERSION:
                raise ValueError("Checkpoint predates the current reward/observation contract")
            if manifest.get("reward_normalization", {}).get("enabled") is not False:
                raise ValueError("Checkpoint does not use the raw-reward contract")
            for path in ("research/runtime.js", "research/collision_memo.js", "research/fast_rpc.js",
                         "research/env.py", "research/terrain.py", "research/reward.py"):
                recorded = manifest.get("source_sha256", {}).get(path)
                if recorded and recorded != current["source_sha256"][path]:
                    raise ValueError("Checkpoint environment contract changed: " + path)
            config = manifest["config"]
            reward_config = RewardConfig(profile=config["reward_profile"],
                                         discount_half_life_seconds=config["discount_half_life"])
            if manifest["reward_contract"] != reward_config.describe(4):
                raise ValueError("Checkpoint reward configuration mismatch")
            vector = DummyVecEnv([lambda: RealGettingOverItEnv(
                bridge=bridge, action_mode=config["action"], terrain=not config["no_terrain"],
                reward_config=reward_config)])
            normalization = VecNormalize.load(str(args.trial / "normalization.pkl"), vector)
            algorithm = sb3.PPO if config["algorithm"] == "ppo" else sb3.SAC
            model = algorithm.load(str(args.trial / "model.zip"), device="cpu")
            if model.gamma != reward_config.gamma(4) or normalization.gamma != model.gamma:
                raise ValueError("Policy, normalization, and reward discounts disagree")
            try:
                result = evaluate(model, normalization, bridge, config["action"],
                                  not config["no_terrain"], args.decisions, (1001, 1002, 1003), reward_config)
            finally:
                normalization.close()
        bridge.evaluate("research.render()")
        if bridge.driver:
            bridge.driver.save_screenshot(str(output / "last.png"))
        else:
            bridge._command(["screenshot", str(output / "last.png")])
    (output / "evidence.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.search:
        print({k: v for k, v in result.items() if k not in ("commands", "start", "trace", "hold_trace")})
    else:
        print([{"seed": r["seed"], "final": r["final"]} for r in result])
    print("Evidence:", output)


if __name__ == "__main__":
    main()
