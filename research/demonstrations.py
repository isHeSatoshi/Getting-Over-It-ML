"""Legal ordinary-start expert data. Demonstrations are not learned policies."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np

from research.browser_bridge import ROOT
from research.case_clock import PhysicalCaseClock
from research.env import RealGettingOverItEnv
from research.evaluation_cases import EvaluationCase
from research.provenance import fingerprint
from research.reward import RewardConfig
from research.study_metrics import enable_platform_support

VERSION = "legal-observation-action-demo-v1"
MAX_SAMPLES = 12000
MAX_BYTES = 32 * 2**20
CRITICAL = ("research/env.py", "research/reward.py", "research/terrain.py",
            "research/runtime.js", "research/collision_memo.js", "research/fast_rpc.js")
# Separate training streams, not the standard evaluation noise seeds 8100..8105.
TRAINING_CASES = (
    EvaluationCase("demo_nominal", 6001),
    EvaluationCase("demo_left", 6001, ((-0.5, 0.5),) * 3),
    EvaluationCase("demo_right", 6001, ((0.5, 0.5),) * 3),
    *(EvaluationCase(f"demo_noise_{i}", 6001, action_noise_std=0.02, noise_seed=9100 + i)
      for i in range(6)),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def game_contract_matches(recorded, current):
    for key in ("project_sha256", "runtime_sha256", "asset_set_sha256"):
        require(recorded[key] == current[key], "Demo game/assets changed: " + key)
    for key in CRITICAL:
        require(recorded["source_sha256"][key] == current["source_sha256"][key],
                "Demo environment/physics changed: " + key)


def load_expert(directory, current):
    directory = Path(directory)
    require(directory.is_absolute(), "Use an absolute trusted expert directory")
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    for key in ("project_sha256", "runtime_sha256", "asset_set_sha256"):
        require(report["provenance"][key] == current[key], "Expert game/assets mismatch")
    for key in ("research/runtime.js", "research/collision_memo.js", "research/fast_rpc.js"):
        require(report["provenance"]["source_sha256"][key] == current["source_sha256"][key],
                "Expert physics mismatch")
    require(report["cases"]["per_tick"]["milestone_success"]["first_ledge_v1"] is True,
            "Expert lacks a reference-validated central hold")
    payload = (directory / "per_tick.json").read_bytes()
    require(len(payload) <= MAX_BYTES, "Expert JSON exceeds limit")
    commands = json.loads(payload)["commands"]
    require(len(commands) == 600 and all(c["id"] == i + 1 for i, c in enumerate(commands)),
            "Expected the reference-validated 600-tick expert")
    actions = np.asarray([[c["x"] / 128, c["y"] / 128] for c in commands], dtype=np.float32)
    require(actions.shape == (600, 2) and np.isfinite(actions).all()
            and np.abs(actions).max() <= 1, "Invalid legal expert targets")
    return actions, hashlib.sha256(payload).hexdigest()


def collect(environment, targets, case):
    """Record the pre-action observation, never a post-action or reset label."""
    targets = np.asarray(targets, dtype=np.float32)
    require(environment.frame_skip == 1 and environment.action_mode == "absolute",
            "Demonstrations require one-tick absolute controls")
    require(targets.ndim == 2 and targets.shape[1] == 2 and 1 <= len(targets) <= 2400
            and np.isfinite(targets).all() and np.abs(targets).max() <= 1,
            "Invalid bounded legal demonstration")
    observation, _ = environment.reset(seed=case.reset_seed)
    clock = PhysicalCaseClock(case)
    rows, actions, ticks = [], [], 0
    reset_ticks = environment.state["tick"]
    final = None
    for target in targets:
        applied = clock.apply(target[None, :], ticks)[0]
        rows.append(observation.copy())
        actions.append(applied.copy())
        observation, _, terminated, truncated, final = environment.step(applied)
        require(final["physics_ticks"] == 1, "Demo physics tick mismatch")
        ticks += 1
        if terminated or truncated:
            break
    return np.asarray(rows, dtype=np.float32), np.asarray(actions, dtype=np.float32), {
        "case": json.loads(json.dumps(case.describe())), "controlled_ticks": ticks,
        "warmup_ticks": len(case.warmup) * clock.hold_ticks,
        "reset_settling_ticks": reset_ticks, "final": final,
        "teacher": "Time-indexed legal trajectory, NOT an off-trajectory corrective expert",
    }


def validate_arrays(observations, actions, episode_ids, eligible):
    require(observations.dtype == actions.dtype == np.float32
            and episode_ids.dtype == np.int64 and eligible.dtype == np.bool_,
            "Unexpected demonstration dtypes")
    n = len(observations)
    require(1 <= n <= MAX_SAMPLES and observations.shape == (n, 217)
            and actions.shape == (n, 2) and episode_ids.shape == eligible.shape == (n,),
            "Invalid demonstration dimensions or sample budget")
    require(np.isfinite(observations).all() and np.isfinite(actions).all()
            and np.abs(actions).max() <= 1 and (episode_ids >= 0).all(),
            "Invalid observation/action values")


def save(directory, observations, actions, episode_ids, eligible, metadata):
    directory = Path(directory)
    require(directory.is_absolute() and not directory.exists(), "Use a new absolute demo directory")
    validate_arrays(observations, actions, episode_ids, eligible)
    require(metadata["version"] == VERSION and metadata["ordinary_start"] is True
            and metadata["placement"] is False and metadata["training"] is False,
            "Invalid legal demonstration declaration")
    directory.mkdir(parents=True, exist_ok=False)
    path = directory / "data.npz"
    np.savez_compressed(path, observations=observations, actions=actions,
                        episode_ids=episode_ids, eligible=eligible)
    record = {**metadata, "samples": len(observations), "eligible_samples": int(eligible.sum()),
              "data_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "purpose": "Expert data, NOT learned-policy or held-out success"}
    (directory / "manifest.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def load(directory, current):
    directory = Path(directory)
    require(directory.is_absolute(), "Use an absolute trusted demonstration directory")
    metadata = directory / "manifest.json"
    require(metadata.stat().st_size <= 2 * 2**20, "Demo metadata exceeds limit")
    record = json.loads(metadata.read_text(encoding="utf-8"))
    require(record["version"] == VERSION and record["ordinary_start"] is True
            and record["placement"] is False and record["training"] is False
            and record["frame_skip"] == 1 and record["action_mode"] == "absolute"
            and record["reward_contract"] == RewardConfig().describe(1),
            "Incompatible demonstration contract")
    game_contract_matches(record["provenance"], current)
    path = directory / "data.npz"
    require(path.stat().st_size <= MAX_BYTES, "Demo archive exceeds limit")
    require(hashlib.sha256(path.read_bytes()).hexdigest() == record["data_sha256"],
            "Demo archive hash mismatch")
    with zipfile.ZipFile(path) as archive:
        require(len(archive.infolist()) == 4
                and sum(item.file_size for item in archive.infolist()) <= MAX_BYTES,
                "Demo decompressed data exceeds limit")
    with np.load(path, allow_pickle=False) as archive:
        require(set(archive.files) == {"observations", "actions", "episode_ids", "eligible"},
                "Unexpected demonstration arrays")
        arrays = {key: archive[key].copy() for key in archive.files}
    validate_arrays(**arrays)
    require(record["samples"] == len(arrays["observations"])
            and record["eligible_samples"] == int(arrays["eligible"].sum()),
            "Demonstration counts disagree")
    episodes = record["episodes"]
    require(len(episodes) >= 1 and set(arrays["episode_ids"].tolist()) == set(range(len(episodes))),
            "Missing or changed demonstration episode IDs")
    for index, episode in enumerate(episodes):
        selected = arrays["episode_ids"] == index
        passed = bool(episode["final"]["milestone_success"]["first_ledge_v1"])
        warmup = episode["warmup_ticks"]
        require(type(warmup) is int and 0 <= warmup <= episode["controlled_ticks"],
                "Invalid demonstration warm-up duration")
        expected = np.arange(int(selected.sum())) >= warmup
        expected &= passed
        require(int(selected.sum()) == episode["controlled_ticks"]
                and bool(np.all(arrays["eligible"][selected] == expected)),
                "Demo eligibility differs from physical central-hold evidence")
    return arrays, record


def conflict_summary(observations, actions):
    """Exact observable-state conflicts; not proof of local recovery coverage."""
    groups = {}
    worst, conflicts = 0.0, 0
    for observation, action in zip(observations, actions):
        key = observation.tobytes()
        if key in groups:
            low, high = groups[key]
            low[:] = np.minimum(low, action)
            high[:] = np.maximum(high, action)
        else:
            groups[key] = (action.copy(), action.copy())
    for low, high in groups.values():
        difference = float(np.max(high - low))
        conflicts += int(difference > 1e-6)
        worst = max(worst, difference)
    return {"exact_observation_groups": len(groups), "conflicting_groups": conflicts,
            "max_normalized_target_range": worst,
            "limit": "Only exact float32 observations; near-state conflicts/recovery remain untested"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expert", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--backend", choices=("reference", "fast"), default="fast")
    parser.add_argument("--cases", choices=("nominal", "training"), default="nominal")
    args = parser.parse_args()
    current = fingerprint()
    targets, source_hash = load_expert(args.expert, current)
    output = args.output_dir or ROOT / "artifacts" / (
        "demonstrations_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    require(output.is_absolute() and not output.exists(), "Use a new absolute output directory")
    from research.backends import make_bridge
    selected = TRAINING_CASES[:1] if args.cases == "nominal" else TRAINING_CASES
    observations, actions, episode_ids, eligible, episodes = [], [], [], [], []
    with make_bridge(args.backend, "selenium") as bridge:
        for index, case in enumerate(selected):
            env = RealGettingOverItEnv(bridge=bridge, frame_skip=1, horizon=len(targets) + 1)
            enable_platform_support(env)
            try:
                obs, act, record = collect(env, targets, case)
            finally:
                env.close()
            passed = bool(record["final"]["milestone_success"]["first_ledge_v1"])
            observations.append(obs); actions.append(act); episodes.append(record)
            episode_ids.append(np.full(len(obs), index, dtype=np.int64))
            # Warm-up is an external evaluation intervention, not a policy
            # label. Teaching opposite warm-ups at the same spawn is ambiguous.
            eligible.append((np.arange(len(obs)) >= record["warmup_ticks"]) & passed)
            print(case.name, "ticks", len(obs), "central hold", passed, flush=True)
    obs, act = np.concatenate(observations), np.concatenate(actions)
    save(output, obs, act, np.concatenate(episode_ids), np.concatenate(eligible), {
        "version": VERSION, "ordinary_start": True, "placement": False, "training": False,
        "frame_skip": 1, "action_mode": "absolute", "reward_contract": RewardConfig().describe(1),
        "provenance": current, "expert_source_sha256": source_hash,
        "collection_backend": args.backend, "episodes": episodes,
        "exact_state_conflicts": conflict_summary(obs, act),
        "eligible_state_conflicts": conflict_summary(obs[np.concatenate(eligible)],
                                                     act[np.concatenate(eligible)]),
        "evaluation_separation": "Training reset 6001/noise 9100..9105, not standard 1001/8100..8105",
    })
    print("Evidence:", output)


if __name__ == "__main__":
    main()
