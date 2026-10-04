"""Bounded owned-process local diagnostic. Never trains, deploys or resumes."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import gymnasium as gym

from research.browser_bridge import ROOT
from research.fast_fidelity import NUMERIC, DISCRETE
from research.provenance import fingerprint
from research.timing_campaign import PROVENANCE_KEYS

SPACE = "isHeSatoshi/rl-over-it-poc-20261004"
REPO = "isHeSatoshi/rl-over-it-research-artifacts"
CONDITIONS = {"nominal": [], "full_noise_8105": [[0, 1800]],
              "early_noise_8105": [[0, 60]], "late_noise_8105": [[60, 1800]]}


class PhysicalCapture(gym.Wrapper):
    """Capture final physical telemetry before VecEnv's automatic reset."""
    def step(self, action):
        result = self.env.step(action)
        self.last_physical_state = dict(self.env.unwrapped.state)
        return result


def require(value, message):
    if not value:
        raise ValueError(message)


def read_json(path, maximum=2 * 2**20):
    require(path.is_absolute() and path.is_file() and path.stat().st_size <= maximum,
            "Missing, relative or oversized diagnostic input")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def digest_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_plan(plan):
    require(plan["version"] == "causal-noise-prefix-suffix-probe-v1"
            and plan["launched"] is False, "Changed diagnostic declaration")
    require(plan["reset_seed"] == 1001 and plan["ordinary_start"] is True
            and plan["warmup"] == [] and plan["frame_skip"] == 1
            and plan["physics_hz"] == 30 and plan["case_ticks"] == 1800,
            "Changed legal physical probe contract")
    require({x["name"]: x["noise_active_intervals_ticks"] for x in plan["conditions"]} == CONDITIONS
            and len(plan["conditions"]) == 4 and plan["cutoff_tick"] == 60
            and plan["backends"] == ["reference", "fast"], "Changed interventions")
    require(plan["noise_seed"] == 8105 and plan["noise_std"] == .02
            and plan["noise_hold_ticks"] == 4, "Changed perturbation stream")
    require(plan["maximum_case_rollouts"] == 8 and plan["maximum_controlled_ticks"] == 14400
            and plan["maximum_counted_reset_ticks"] == 1920
            and plan["maximum_counted_physics_ticks"] == 16320, "Changed physical budget")
    require(plan["limits"] == {"training_updates": 0, "new_paid_reservation": 0,
                              "wall_seconds": 600, "owned_browser_processes_only": True,
                              "binary_max_bytes_each": 8 * 2**20}, "Changed resource limits")
    require(plan["controller"] == {
        "arm": "behavior_cloning_only", "training_seed": 7, "deterministic": True,
        "torch_threads": 1, "device": "cpu", "normalization": "Matching saved frozen RMS, no fitting"},
        "Changed selected saved controller")
    revision = plan["source_dataset_revision"]
    require(revision == "5df6c20390ca641d8d10a2c62471e7f4142b922e",
            "The frozen immutable source dataset is required")
    base = "imitation-20261004-v1/imitation_campaign/runs/behavior_cloning_only_seed_7/"
    expected = {
        "model": (1000930, "25ec7c319b7a9eb11c2e3b184debe12c256730af0a36d11762e75a82f7acdb87"),
        "normalizer": (7385, "59bdee0d177e6724b10e84f9797c5a823e97f1ef81652ed23fb0e3c37b0e2493")}
    for key, name in (("model", "model.zip"), ("normalizer", "normalization.pkl")):
        spec = plan[key]
        require(spec == {"path": base + name, "size": expected[key][0],
                         "lfs_sha256": expected[key][1]}, "Changed saved companion identity")


class MaskedNoise:
    """Advance the global stream even when a condition masks the current block."""
    def __init__(self, condition):
        require(condition in CONDITIONS, "Unknown noise condition")
        self.intervals, self.rng = CONDITIONS[condition], np.random.default_rng(8105)
        self.block, self.tick, self.noise = -1, -1, np.zeros((1, 2))

    def apply(self, prediction, tick):
        prediction = np.asarray(prediction, dtype=np.float32)
        require(prediction.shape == (1, 2) and np.isfinite(prediction).all()
                and np.abs(prediction).max() <= 1, "Invalid normalized policy action")
        require(type(tick) is int and tick == self.tick + 1 and 0 <= tick < 1800,
                "Probe clock must advance exactly one physical tick")
        block = tick // 4
        if block != self.block:
            self.noise = self.rng.normal(0, .02, (1, 2))
            self.block = block
        active = any(start <= tick < end for start, end in self.intervals)
        self.tick = tick
        return np.clip(prediction + (self.noise if active else 0), -1, 1).astype(np.float32)


def child_environment(environment):
    return {key: value for key, value in environment.items()
            if not any(s in key.upper() for s in ("TOKEN", "PASSWORD", "SECRET", "API_KEY"))
            and key not in ("AGENT_BROWSER_CDP", "AGENT_BROWSER_SESSION")}


def first_backend_difference(reference, fast):
    if len(reference["rows"]) != len(fast["rows"]):
        return {"kind": "length"}
    for index, (a, b) in enumerate(zip(reference["rows"], fast["rows"])):
        for key in ("action", "applied_action", "pre_observation", "observation"):
            if not np.array_equal(a[key], b[key]):
                return {"kind": key, "tick": index + 1,
                        "maximum_error": float(np.max(np.abs(np.asarray(a[key]) - b[key])))}
        if a["reward"] != b["reward"] or a["info"] != b["info"]:
            return {"kind": "reward_or_info", "tick": index + 1}
        for state_key in ("pre_state", "post_state"):
            for key in NUMERIC + DISCRETE:
                if a[state_key][key] != b[state_key][key]:
                    return {"kind": "physical_telemetry", "field": key,
                            "state": state_key, "tick": index + 1}
    if reference["control_ticks"] != fast["control_ticks"] or reference["reset_ticks"] != fast["reset_ticks"]:
        return {"kind": "exposure"}
    return None


def first_remote_difference(local, remote):
    if len(local["rows"]) != len(remote["trace"]):
        return {"kind": "length"}
    for index, (actual, expected) in enumerate(zip(local["rows"], remote["trace"])):
        for key in ("action", "applied_action"):
            if not np.array_equal(actual[key], expected[key]):
                return {"kind": key, "tick": index + 1,
                        "actual": actual[key], "expected": expected[key],
                        "maximum_error": float(np.max(np.abs(np.asarray(actual[key]) - expected[key])))}
        for key in ("player_world_x", "player_world_y", "retained_gain", "success", "dead",
                    "body_hit_frames", "hammer_hit_frames", "milestone_success"):
            if actual["info"][key] != expected[key]:
                return {"kind": "physical_outcome", "field": key, "tick": index + 1,
                        "actual": actual["info"][key], "expected": expected[key]}
    return None


def check_deadline(deadline):
    require(time.time() < deadline, "Diagnostic wall budget reached; stop owned work")


def configure_bounded_http(deadline, hub=None):
    """Support both installed Hub HTTP APIs without unbounded request waits."""
    if hub is None:
        import huggingface_hub as hub
    if hasattr(hub, "set_client_factory"):
        import httpx

        def before_request(request):
            check_deadline(deadline)
            remaining = min(30, max(.1, deadline - time.time()))
            request.extensions["timeout"] = {"connect": 5, "read": remaining,
                                             "write": remaining, "pool": 5}

        hub.set_client_factory(lambda: httpx.Client(
            timeout=httpx.Timeout(30, connect=5, pool=5), follow_redirects=True,
            event_hooks={"request": [before_request]}))
    else:
        import requests

        class BoundedSession(requests.Session):
            def send(self, request, **kwargs):
                check_deadline(deadline)
                kwargs["timeout"] = (5, min(30, max(.1, deadline - time.time())))
                return super().send(request, **kwargs)

        hub.configure_http_backend(backend_factory=BoundedSession)


def require_owned_parent(prepared, process_factory=None, platform=None):
    """Windows venv python.exe inserts one verified launcher, unlike Linux."""
    if process_factory is None:
        import psutil
        process_factory = psutil.Process
    platform = sys.platform if platform is None else platform
    actual = process_factory(os.getpid()).parent()
    require(actual is not None, "Owned diagnostic parent vanished")
    if actual.pid != prepared["parent_pid"]:
        require(platform == "win32"
                and Path(actual.exe()) == Path(prepared["launcher_executable"]),
                "Unexpected diagnostic parent or launcher")
        actual = actual.parent()
    require(actual is not None and actual.pid == prepared["parent_pid"]
            and actual.create_time() == prepared["parent_creation_time"],
            "Probe requires its exact live owned parent ancestry")


def rollout(model, normalization, bridge, condition, deadline, trace_path=None):
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    from research.env import RealGettingOverItEnv
    from research.study_metrics import enable_platform_support
    from research.imitation_train import rms_snapshot, require_frozen_rms
    check_deadline(deadline)
    env = RealGettingOverItEnv(bridge=bridge, action_mode="absolute", terrain=True,
                              frame_skip=1, horizon=1800)
    enable_platform_support(env)
    capture = PhysicalCapture(env)
    vector = VecNormalize(DummyVecEnv([lambda: capture]), norm_obs=True, norm_reward=False,
                          gamma=env.gamma, clip_obs=normalization.clip_obs,
                          epsilon=normalization.epsilon)
    vector.obs_rms = copy.deepcopy(normalization.obs_rms)
    vector.training = False
    frozen = rms_snapshot(vector)
    trace_file = None
    try:
        vector.seed(1001)
        observation = vector.reset()
        reset_ticks, control_ticks = env.state["tick"], 0
        records, schedule = [], MaskedNoise(condition)
        trace_file = trace_path.open("x", encoding="utf-8") if trace_path else None
        for tick in range(1800):
            check_deadline(deadline)
            before, pre_state = observation[0].tolist(), dict(env.state)
            action, _ = model.predict(observation, deterministic=True)
            applied = schedule.apply(action, tick)
            observation, reward, done, infos = vector.step(applied)
            info = {k: v for k, v in infos[0].items() if k not in ("terminal_observation", "episode")}
            require(info["physics_ticks"] == 1, "Unexpected short/extra physical step")
            control_ticks += 1
            if done[0]:
                reset_ticks += env.state["tick"]
            record = {"action": action[0].tolist(), "applied_action": applied[0].tolist(),
                      "pre_observation": before, "observation": observation[0].tolist(),
                      "reward": float(reward[0]), "info": info, "pre_state": pre_state,
                      "post_state": capture.last_physical_state,
                      "controlled_ticks_total": control_ticks, "reset_ticks_total": reset_ticks}
            records.append(record)
            if trace_file:
                trace_file.write(json.dumps(record, allow_nan=False) + "\n")
                trace_file.flush()
            if done[0]:
                break
        require_frozen_rms(vector, frozen)
    finally:
        try:
            vector.close()
        finally:
            if trace_file:
                trace_file.close()
    require(reset_ticks <= 240, "Reset exposure exceeded declared per-case budget")
    return {"condition": condition, "rows": records, "control_ticks": control_ticks,
            "reset_ticks": reset_ticks, "final": records[-1]["info"]}


def worker(prepared_path, output):
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import VecNormalize
    import pickle
    import torch
    from research.browser_bridge import BrowserBridge
    from research.fast_bridge import FastBridge
    from research.imitation_train import require_model_settings, settings
    from research.reward import RewardConfig
    prepared = read_json(prepared_path)
    require_owned_parent(prepared)
    require(digest_file(Path(__file__).resolve()) == prepared["diagnostic_source_sha256"],
            "Diagnostic implementation changed after parent admission")
    plan = read_json(Path(prepared["plan"]))
    validate_plan(plan)
    require(digest_file(Path(prepared["plan"])) == prepared["plan_sha256"], "Declaration changed")
    require(output == Path(prepared["output"]), "Unexpected probe output path")
    deadline = prepared["deadline_epoch"]
    check_deadline(deadline)
    for key, filename in (("model", "model.zip"), ("normalizer", "normalization.pkl")):
        path = output / filename
        require(path.stat().st_size == plan[key]["size"]
                and digest_file(path) == plan[key]["lfs_sha256"], "Saved companion bytes changed")
    current = fingerprint()
    for key in PROVENANCE_KEYS:
        require(current[key] == prepared["provenance"][key], "Probe source drift")
    torch.set_num_threads(1)
    model = PPO.load(str(output / "model.zip"), device="cpu")
    require_model_settings(model, settings("behavior_cloning_only", False))
    require(model.num_timesteps == 0, "Selected clone contains RL training")
    # Only our owned, pinned, byte-verified SB3 artifact is deserialized.
    with (output / "normalization.pkl").open("rb") as handle:
        normalization = pickle.load(handle)
    require(isinstance(normalization, VecNormalize) and normalization.training is False
            and normalization.norm_obs and not normalization.norm_reward
            and normalization.gamma == model.gamma == RewardConfig().gamma(1)
            and normalization.obs_rms.mean.shape == (217,), "Invalid saved frozen normalizer")
    remote = read_json(output / "remote_baselines.json", 16 * 2**20)
    report = {"version": plan["version"], "plan_sha256": prepared["plan_sha256"],
              "diagnostic_source_sha256": prepared["diagnostic_source_sha256"],
              "status": "baseline_running", "training_updates": 0, "rollouts": {},
              "backend_differences": {}, "remote_differences": {},
              "source": prepared["provenance"], "dependencies": {
                  "torch": torch.__version__, "numpy": np.__version__,
                  "device": "cpu", "threads": torch.get_num_threads()}}

    def save():
        totals = [value for by_backend in report["rollouts"].values() for value in by_backend.values()]
        report["case_rollouts"] = len(totals)
        report["controlled_ticks"] = sum(x["control_ticks"] for x in totals)
        report["reset_ticks"] = sum(x["reset_ticks"] for x in totals)
        require(report["case_rollouts"] <= 8 and report["controlled_ticks"] <= 14400
                and report["reset_ticks"] <= 1920, "Diagnostic work budget exceeded")
        write_json(output / "report.json", report)

    trajectories = {}
    # Dedicated fresh headless instances, never an embedded/user browser.
    with BrowserBridge(driver="selenium", headless=True) as reference, FastBridge(headless=True) as fast:
        for condition in CONDITIONS:
            if condition == "early_noise_8105":
                if any(report["backend_differences"].values()) or any(report["remote_differences"].values()):
                    report["status"] = "baseline_fidelity_or_portability_failed"
                    save()
                    return report
                report["status"] = "interventions_running"
            trajectories[condition], report["rollouts"][condition] = {}, {}
            for name, bridge in (("reference", reference), ("fast", fast)):
                result = rollout(model, normalization, bridge, condition, deadline,
                                 output / (condition + "_" + name + ".partial.jsonl"))
                trajectories[condition][name] = result
                write_json(output / (condition + "_" + name + ".json"), result)
                report["rollouts"][condition][name] = {
                    key: result[key] for key in ("control_ticks", "reset_ticks", "final")}
                save()
            difference = first_backend_difference(
                trajectories[condition]["reference"], trajectories[condition]["fast"])
            report["backend_differences"][condition] = difference
            if condition in remote:
                report["remote_differences"][condition] = first_remote_difference(
                    trajectories[condition]["reference"], remote[condition])
            elif difference:
                report["status"] = "intervention_backend_fidelity_failed"
                save()
                return report
            save()
        report["status"] = "completed_exploratory_diagnostic"
        report["limit"] = "Selected stream/reset only; no held-out competence, corrective oracle or promotion"
        save()
    return report


def stop_owned_tree(process, creation_time):
    import psutil
    try:
        root = psutil.Process(process.pid)
        if root.create_time() != creation_time:
            return
        owned = [(child, child.create_time()) for child in root.children(recursive=True)]
        owned.append((root, creation_time))
        for item, created in reversed(owned):
            try:
                if item.create_time() == created:
                    item.terminate()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs([item for item, _ in owned], timeout=10)
        times = {item.pid: created for item, created in owned}
        for item in alive:
            try:
                if item.create_time() == times[item.pid]:
                    item.kill()
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--closure", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--worker", type=Path)
    args = parser.parse_args()
    if args.worker:
        require(args.output_dir and args.output_dir.is_absolute(), "Worker needs its owned output")
        result = worker(args.worker, args.output_dir)
        print(result["status"], flush=True)
        return
    require(args.plan and args.closure, "Use the frozen plan and reviewed closed comparison")
    started, deadline = time.time(), time.time() + 570  # Thirty seconds reserved for cleanup.
    plan, closure = read_json(args.plan), read_json(args.closure)
    validate_plan(plan)
    require(closure["all_nine_full_contracts_valid"] and closure["rechecked_paused"]
            and closure["terminal_phase"] == "imitation_complete", "Study closure is incomplete")
    current = fingerprint()
    manifest_dir = args.closure.parent / "imitation_campaign/runs/behavior_cloning_only_seed_7"
    manifest = read_json(manifest_dir / "manifest.json")
    for key in PROVENANCE_KEYS:
        require(manifest[key] == current[key], "Saved-controller source/game differs: " + key)
    ledger = read_json(ROOT / "autoresearch.costs.json")
    require(all(x["verified_end_epoch"] is not None for x in ledger["batches"]),
            "Another paid reservation is active")
    batch = next(x for x in ledger["batches"] if x["session"] == closure["session"])
    require(batch["status"] == "imitation_complete_validated_paused"
            and batch["verified_end_epoch"] == closure["independent_paused_epoch"],
            "Closure and persistent ledger differ")
    from huggingface_hub import HfApi, hf_hub_download
    configure_bounded_http(deadline)
    api = HfApi()
    runtime, info = api.get_space_runtime(SPACE), api.space_info(SPACE)
    variables = api.get_space_variables(SPACE)
    require(str(runtime.stage) == "PAUSED" and info.private
            and info.sha == closure["source_space_revision"]
            and variables["RL_SESSION_ID"].value == closure["session"]
            and variables["RL_MODE"].value == "imitation_study", "Closed Space changed")
    metadata = api.repo_info(REPO, repo_type="dataset", revision=plan["source_dataset_revision"],
                             files_metadata=True)
    require(metadata.private, "Probe inputs must remain private")
    output = args.output_dir or ROOT / "artifacts" / (
        "imitation_noise_probe_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    require(output.is_absolute() and not output.exists(), "Use a new absolute diagnostic output")
    output.mkdir(parents=True)
    for key, name in (("model", "model.zip"), ("normalizer", "normalization.pkl")):
        check_deadline(deadline)
        spec = plan[key]
        item = next(x for x in metadata.siblings if x.rfilename == spec["path"])
        require(item.size == spec["size"] and item.lfs.sha256 == spec["lfs_sha256"],
                "Pinned saved companion metadata differs")
        source = Path(hf_hub_download(REPO, repo_type="dataset",
                                      revision=plan["source_dataset_revision"], filename=spec["path"],
                                      etag_timeout=10))
        require(source.stat().st_size == spec["size"] and digest_file(source) == spec["lfs_sha256"],
                "Pinned saved companion hash/size mismatch")
        (output / name).write_bytes(source.read_bytes())
    evaluation_path = manifest_dir / "evaluation.json"
    require(evaluation_path.stat().st_size <= 128 * 2**20
            and digest_file(evaluation_path) == "bc5548f20fe1eec2b905f2f2223ee41244c0dc8f6dc068ac8cd7f22173d0febb",
            "Saved remote baseline evidence changed")
    evaluation = read_json(evaluation_path, 128 * 2**20)
    baselines = {name: next(r for r in evaluation["final"] if r["case"]["name"] == case)
                 for name, case in (("nominal", "nominal"), ("full_noise_8105", "action_noise_5"))}
    write_json(output / "remote_baselines.json", baselines)
    write_json(output / "admission.json", {"checked_epoch": time.time(), "paused": True,
               "closed_session": closure["session"], "closure_dataset_revision": closure["dataset_revision"],
               "source_space_revision": info.sha, "plan_sha256": digest_file(args.plan),
               "model_sha256": digest_file(output / "model.zip"),
               "normalizer_sha256": digest_file(output / "normalization.pkl"),
               "no_remote_writes_or_paid_reservation": True})
    prepared_path = output / "prepared.json"
    import psutil
    write_json(prepared_path, {"parent_pid": os.getpid(), "output": str(output),
               "plan": str(args.plan), "plan_sha256": digest_file(args.plan), "provenance": current,
               "deadline_epoch": deadline, "parent_creation_time": psutil.Process().create_time(),
               "launcher_executable": sys.executable,
               "diagnostic_source_sha256": digest_file(Path(__file__).resolve())})
    check_deadline(deadline)
    with (output / "worker.log").open("x", encoding="utf-8") as log:
        process = subprocess.Popen([sys.executable, "-m", "tools.imitation_noise_probe",
                                    "--worker", str(prepared_path), "--output-dir", str(output)],
                                   cwd=ROOT, env=child_environment(os.environ),
                                   stdout=log, stderr=subprocess.STDOUT)
        creation = psutil.Process(process.pid).create_time()
        try:
            code = process.wait(timeout=max(.1, deadline - time.time()))
            require(code == 0, "Owned probe worker failed; preserve its log and stop. Evidence: " + str(output))
        except subprocess.TimeoutExpired:
            write_json(output / "termination.json", {"status": "wall_budget_exhausted",
                       "training_updates": 0, "deadline_epoch": deadline})
            raise
        finally:
            stop_owned_tree(process, creation)
    result = read_json(output / "report.json")
    require(time.time() - started <= 600, "Diagnostic exceeded declared wall cap")
    print(json.dumps({k: v for k, v in result.items() if k not in ("source", "rollouts")}, indent=2))
    print("Evidence:", output, flush=True)


if __name__ == "__main__":
    main()
