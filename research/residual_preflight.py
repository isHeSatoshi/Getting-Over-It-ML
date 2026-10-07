"""Bounded zero-actor physics, no-optimizer pipeline and mock optimizer checks."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from research.demonstrations import require
from research.phase_controller import load_prior
from research.provenance import fingerprint


def write(directory, name, payload):
    with (directory/name).open("x") as stream:
        json.dump(payload, stream, indent=2, allow_nan=False)


def pipeline(prior, actions, output):
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    from research.residual_controller import ResidualController
    from research.residual_policy import (ZeroResidualPolicy, checkpoint_contract,
                                          new_normalizer, validate_checkpoint)
    from research.residual_env import ResidualGettingOverItEnv
    from tests.test_residual_env import MockRawEnv
    torch.set_num_threads(1)
    controller = ResidualController(prior, actions)
    controller.reset(prior[0])
    contexts = []
    for index in range(600):
        context = controller.prepare(prior[index])
        contexts.append(context)
        issued = controller.action(np.zeros(2, np.float32))
        require(issued.tobytes() == actions[index].tobytes(), "Pipeline nominal prior parity failed")
        controller.observe(prior[min(index+1, 599)], issued)
    contexts = np.asarray(contexts, np.float32)
    adapter = ResidualGettingOverItEnv(MockRawEnv(), prior, actions)
    vector = new_normalizer(adapter)
    vector.training = False
    model = PPO(ZeroResidualPolicy, vector, seed=12, device="cpu", n_steps=8, batch_size=4,
                n_epochs=1, gamma=vector.gamma)
    expected = model.predict(vector.normalize_obs(contexts), deterministic=True)[0]
    require(np.array_equal(expected, np.zeros((600, 2), np.float32)) and not model.policy.optimizer.state,
            "Zero-head pipeline changed or optimized")
    model.save(output/"untrained.zip")
    vector.save(output/"normalizer.pkl")
    schema = checkpoint_contract(adapter)
    other = ResidualGettingOverItEnv(MockRawEnv(), prior, actions)
    reloaded_vector = VecNormalize.load(output/"normalizer.pkl", DummyVecEnv([lambda: other]))
    reloaded_vector.training = False
    loaded = PPO.load(output/"untrained.zip", env=reloaded_vector, device="cpu")
    validate_checkpoint(loaded.policy, reloaded_vector, schema, other)
    require(np.array_equal(expected, loaded.predict(reloaded_vector.normalize_obs(contexts), deterministic=True)[0])
            and loaded.num_timesteps == model.num_timesteps == 0
            and not loaded.policy.optimizer.state, "Owned model/RMS pipeline reload failed")
    vector.close()
    reloaded_vector.close()
    return {"check": "pipeline", "rows": 600, "actor_dimension": 222,
            "optimizer_calls": 0, "new_gameplay_ticks": 0, "new_reset_ticks": 0,
            "zero_mean_and_reload_exact": True}


def optimizer(output):
    from research.residual_env import ResidualGettingOverItEnv
    from research.residual_train import initialize, learn
    from tests.test_residual_env import MockRawEnv, fixture
    raw = MockRawEnv()
    raw.pipeline_mock_only = True
    adapter = ResidualGettingOverItEnv(raw, *fixture())
    model, vector, physical = initialize(adapter, 12, mock_smoke=True)
    result = learn(model, vector, physical, 12, mock_smoke=True)
    require(result["transitions"] == 8 and result["optimizer"]["total_optimizer_step_calls"] == 2,
            "Mock optimizer accounting mismatch")
    vector.close()
    return {"check": "optimizer", "mock_work": result,
            "new_gameplay_ticks": 0, "new_reset_ticks": 0, "mock_only": True}


def fidelity(prior, actions, output):
    from research.browser_bridge import BrowserBridge
    from research.fast_bridge import FastBridge
    from research.env import RealGettingOverItEnv
    from research.residual_env import ResidualGettingOverItEnv
    from research.stroke_controller import StrokeController
    from research.study_metrics import enable_platform_support
    from research.fast_fidelity import NUMERIC, DISCRETE
    histories, total, resets = {}, 0, 0
    with BrowserBridge(driver="selenium", headless=True) as reference, FastBridge(headless=True) as fast:
        bootstrap = reference.read_state()["tick"]+fast.read_state()["tick"]
        require(bootstrap == 240, "Preflight bridge bootstrap changed")
        for arm in ("baseline", "zero_adapter"):
            for backend, bridge in (("reference", reference), ("fast", fast)):
                raw = RealGettingOverItEnv(bridge=bridge, action_mode="absolute", terrain=True,
                                          frame_skip=1, horizon=1800)
                enable_platform_support(raw)
                adapter = ResidualGettingOverItEnv(raw, prior, actions) if arm == "zero_adapter" else None
                env = adapter or raw
                observation, _ = env.reset(seed=6001)
                resets += raw.state["tick"]
                require(raw.state["player_world_x"] == 0 and raw.state["player_world_y"] == 21,
                        "Preflight not at ordinary spawn")
                base = StrokeController(prior, actions, "contact_timed_feedback")
                rows = []
                try:
                    with (output/f"{arm}_{backend}.jsonl").open("x") as stream:
                        for tick in range(600):
                            pre = observation[:217].copy()
                            proposed = base.action(pre)
                            actor = observation.copy() if adapter else None
                            observation, reward, terminal, truncated, info = env.step(
                                np.zeros(2, np.float32) if adapter else proposed)
                            require(not terminal and not truncated and info["physics_ticks"] == 1,
                                    "Unexpected fidelity terminal/clock")
                            residual = info.pop("residual_transition", None)
                            if adapter:
                                require(residual["last_transition"]["final_issued"] == proposed.tolist()
                                        and actor[218:220].tobytes() == proposed.tobytes()
                                        and residual["steps"] == residual["base_calls"] == tick+1,
                                        "Adapter/control/source fidelity failed")
                            row = {"pre": pre.tolist(), "action": proposed.tolist(), "post": observation[:217].tolist(),
                                   "reward": float(reward), "info": info,
                                   "state": {key: raw.state[key] for key in NUMERIC+DISCRETE},
                                   "base": base.last}
                            stream.write(json.dumps(row, separators=(",", ":"), allow_nan=False)+"\n")
                            rows.append(row)
                            total += 1
                finally:
                    env.close()
                require(rows[-1]["info"]["retained_gain"] == 83
                        and all(rows[-1]["info"]["milestone_success"].values()),
                        "Known nominal hand-designed ledge hold missing")
                histories[(arm, backend)] = rows
        require(histories[("baseline", "reference")] == histories[("baseline", "fast")]
                == histories[("zero_adapter", "reference")] == histories[("zero_adapter", "fast")],
                "Full baseline/adapter/reference/fast physical histories differ")
    require(total == 2400 and resets == 480, "Preflight fidelity work cap changed")
    return {"check": "fidelity", "rollouts": 4, "controlled_ticks": total, "episode_reset_ticks": resets,
            "bridge_bootstrap_ticks": bootstrap, "total_reset_ticks": resets+bootstrap,
            "all_four_physical_histories_exact": True, "retained_gain": 83,
            "summits": 0, "deaths": 0, "optimizer_calls": 0,
            "limit": "Known nominal hand-designed baseline fidelity, not learned benefit."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", choices=("fidelity", "pipeline", "optimizer"), required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(args.prior.is_absolute() and args.output_dir.is_absolute()
            and not args.output_dir.exists(), "Fresh absolute owned preflight inputs/output required")
    prior, actions, _ = load_prior(args.prior)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    result = fidelity(prior, actions, args.output_dir) if args.check == "fidelity" else (
        pipeline(prior, actions, args.output_dir) if args.check == "pipeline" else optimizer(args.output_dir))
    result.update(passed=True, provenance=fingerprint(),
                  prior_observations_sha256=hashlib.sha256(prior.tobytes()).hexdigest(),
                  prior_actions_sha256=hashlib.sha256(actions.tobytes()).hexdigest())
    write(args.output_dir, "report.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "provenance"}, indent=2))


if __name__ == "__main__":
    main()
