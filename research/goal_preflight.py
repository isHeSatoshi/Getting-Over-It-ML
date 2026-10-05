"""Goal pipeline and bounded legal-prefix/feedback reference-fast fidelity only."""
import argparse
import json
from pathlib import Path

import numpy as np

from research.demonstrations import require
from research.goal_env import GoalEnv, schema
from research.goal_archive import snapshot, compare_snapshot, extend_chain, digest
from research.goal_train import make_model, TickBudget
from research.provenance import fingerprint


def pipeline(output):
    import torch
    from research.goal_replay import GoalReplayBuffer
    from research.goal_env import relabel, local_reward
    model = make_model(21, 64)
    buffer = model.replay_buffer
    buffer.begin_suffix()
    for index in range(32):
        positions = np.asarray([[index, 21]]*4, np.float64)
        next_positions = positions+np.asarray([1, 0])
        observation = relabel(np.zeros(620, np.float32), positions, [30, 21])
        nxt = relabel(np.zeros(620, np.float32), next_positions, [30, 21])
        buffer.add_transition({"observation": observation, "next_observation": nxt, "bodies": positions,
            "next_bodies": next_positions, "action": np.zeros(2, np.float32), "goal": np.asarray([30., 21.]),
            "achieved": next_positions[-1], "speed": 1., "dead": False, "terminal": False, "eligible": index >= 12})
    require(buffer.sample(16).observations.shape == (16, 620), "HER pipeline shape mismatch")
    # Bounded toy tensor update only, not original-game training.
    from research.optimizer_work import OptimizerWork
    with OptimizerWork(model, "sac") as calls:
        model.train(1, 16)
    require(calls.summary()["total_optimizer_step_calls"] == 3, "SAC optimizer callback accounting drift")
    model.save(output/"mock_model.zip")
    from stable_baselines3 import SAC
    from research.goal_train import SpacesOnly
    loaded = SAC.load(output/"mock_model.zip", env=SpacesOnly(), device="cpu")
    probe = np.zeros((16, 620), np.float32)
    require(np.array_equal(model.predict(probe, deterministic=True)[0],
                           loaded.predict(probe, deterministic=True)[0]), "Goal actor reload mismatch")
    buffer.save(output/"mock_replay.pkl.gz")
    return {"passed": True, "check": "pipeline", "schema": schema(), "mock_transitions": 32,
            "mock_cycles": 1, "mock_optimizer_calls": 3, "physics_ticks": 0}


def fidelity(prior, output):
    from research.phase_controller import load_prior
    from research.browser_bridge import BrowserBridge
    from research.fast_bridge import FastBridge
    from research.env import RealGettingOverItEnv
    from research.goal_archive import make_prefix, prefix_identity, replay_prefix
    from research.study_metrics import enable_platform_support
    _, opening, _ = load_prior(prior)
    model = make_model(21, 32)
    budget = TickBudget(maximum=10000)
    reference_records = None
    physics = []
    for backend, factory in (("reference", lambda: BrowserBridge(driver="selenium", headless=True)),
                             ("fast", lambda: FastBridge(headless=True))):
        with factory() as bridge:
            budget.add("bridge_bootstrap", bridge.read_state()["tick"])
            raw = RealGettingOverItEnv(bridge=bridge, action_mode="absolute", terrain=True, frame_skip=1, horizon=2400)
            enable_platform_support(raw)
            env = GoalEnv(raw, budget=budget)
            env.reset(seed=6001)
            reset, commands, route, histories = snapshot(env), [], [], []
            chain = digest(reset)
            for issued in opening:
                env.step_recorded(issued, issued, category="scaffold")
                command = {"issued": issued.tolist(), "applied": issued.tolist()}
                history = snapshot(env)
                commands.append(command); route.append(history["state"]); histories.append(history)
                chain = extend_chain(chain, command, history["state"], history)
            record = make_prefix(env, commands, route, reset, fingerprint(), chain=chain)
            record["snapshots"] = histories
            record["id"] = prefix_identity(record)
            require(raw.state["player_world_y"] == 104, "Known legal opening no longer holds")
            replay_prefix(env, record)
            if reference_records is None:
                reference_records = record
            else:
                compare_snapshot(record["endpoint"], reference_records["endpoint"])
                compare_snapshot(record["reset"], reference_records["reset"])
            observation = env.begin_suffix([322.58588646662605, 104])
            rows = []
            for _ in range(60):
                issued = model.predict(observation, deterministic=True)[0].astype(np.float32)
                observation, _, terminal, truncated, info = env.step(issued)
                rows.append(snapshot(env))
                if terminal or truncated:
                    break
            physics.append(rows)
            env.close()
    require(len(physics[0]) == len(physics[1]) == 60, "Prefix-plus-feedback comparison stopped early")
    for a, b in zip(physics[0], physics[1]):
        compare_snapshot(a, b)
    return {"passed": True, "check": "prefix_fidelity", "prefix_ticks": 600,
            "feedback_ticks": 60, "both_backends_verified": True, "physics_ticks": budget.total,
            "work": budget.record(), "learned_success_claimed": False}


def resources(output):
    """One simulator only; count every bootstrap, reset and measured command."""
    from research.fast_bridge import FastBridge
    from research.env import RealGettingOverItEnv
    from research.resources import effective_limits, OwnedProcessSampler
    budget = TickBudget(maximum=10000)
    with OwnedProcessSampler() as sampled:
        with FastBridge(headless=True) as bridge:
            budget.add("bridge_bootstrap", bridge.read_state()["tick"])
            raw = RealGettingOverItEnv(bridge=bridge, action_mode="absolute", frame_skip=1, terrain=True, horizon=65)
            env = GoalEnv(raw, budget=budget)
            env.reset(seed=6001)
            for _ in range(64):
                _, _, terminal, truncated, _ = env.step_recorded(np.asarray([0., -.625], np.float32),
                    np.asarray([0., -.625], np.float32), category="resource")
                if terminal or truncated:
                    break
            env.close()
    return {"passed": True, "check": "resources", "physics_ticks": budget.total,
            "work": budget.record(), "effective_limits": effective_limits(), "owned_resources": sampled.summary(),
            "one_simulator_at_a_time": True}


def benchmark(output):
    from research.fast_bridge import FastBridge
    from research.benchmark import benchmark as measure
    with FastBridge(headless=True) as bridge:
        report = measure(bridge)
    # This existing fixed benchmark's known resets/commands have a conservative
    # allocation (5000 vs3496 nominal), explicitly separate from measured ticks.
    return {"passed": True, "check": "benchmark", "physics_ticks_allocated": 5000,
            "one_simulator_at_a_time": True, "benchmark": report}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", choices=("pipeline", "fidelity", "resources", "benchmark"), required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(args.prior.is_absolute() and args.output_dir.is_absolute()
            and not args.output_dir.exists(), "Fresh absolute goal preflight paths required")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    result = (pipeline(args.output_dir) if args.check == "pipeline" else
              fidelity(args.prior, args.output_dir) if args.check == "fidelity" else
              resources(args.output_dir) if args.check == "resources" else benchmark(args.output_dir))
    result["provenance"] = fingerprint()
    (args.output_dir/"report.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({key: value for key, value in result.items() if key != "provenance"}, indent=2))


if __name__ == "__main__":
    main()
