"""Read-only private research status. Never loads a model or prints credentials."""
import argparse
import json
import subprocess
from huggingface_hub import HfApi, hf_hub_download

SPACE = "isHeSatoshi/rl-over-it-poc-20261004"
REPO = "isHeSatoshi/rl-over-it-research-artifacts"
SESSION = "poc-20261004-v1"


def selected_session(api, requested=None):
    if requested is not None:
        session = requested
    else:
        configured = api.get_space_variables(SPACE).get("RL_SESSION_ID")
        session = configured.value if configured is not None else SESSION
    if not session or not session.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid artifact session")
    return session


def campaign_prefix(session):
    campaign = ("onstate_campaign" if session.startswith("onstate-")
                else "imitation_campaign" if session.startswith("imitation-")
                else "timing_campaign" if session.startswith("timing-") else "pilot_campaign")
    return f"{session}/{campaign}/runs/"


def inference_summary(payload):
    if any(payload.get(key) != 0 for key in ("controlled_ticks", "reset_ticks", "training_updates")):
        raise ValueError("Inference-only result contains physical/training work")
    count = payload.get("actual_inference_presentations")
    if type(count) is not int or not 0 <= count <= 3600:
        raise ValueError("Invalid inference-only work counter")
    return {key: payload.get(key) for key in (
        "kind", "status", "actual_inference_presentations", "controlled_ticks",
        "reset_ticks", "training_updates", "dependencies", "raw_normalization_comparison",
        "versus_local_archived_same_inputs", "singleton_repeat_comparison")}


def noise_probe_summary(payload):
    if (payload.get("training_updates") != 0 or not 0 <= payload.get("controlled_ticks", -1) <= 14400
            or not 0 <= payload.get("reset_ticks", -1) <= 1920
            or not 0 <= payload.get("case_rollouts", -1) <= 8):
        raise ValueError("Physics-only probe exceeds its declared work")
    outcomes = {}
    for condition, backends in payload.get("rollouts", {}).items():
        if "reference" in backends:
            final = backends["reference"]["final"]
            outcomes[condition] = {"retained_gain": final["retained_gain"],
                                   "central_held_event": final["milestone_success"]["first_ledge_v1"],
                                   "secondary_held_event": final["milestone_success"][
                                       "first_platform_support_diagnostic_v2"],
                                   "summit": final["success"], "dead": final["dead"]}
    return {"status": payload.get("status"), "controlled_ticks": payload["controlled_ticks"],
            "reset_ticks": payload["reset_ticks"], "rollouts": payload["case_rollouts"],
            "training_updates": 0, "reference_outcomes": outcomes,
            "limit": "Selected exploratory cases, never held-out robustness or goal promotion"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", help="Inspect a historical session instead of the configured active one")
    args = parser.parse_args()
    result = subprocess.run(["hf", "spaces", "info", SPACE, "--expand", "runtime", "--json"],
                            capture_output=True, text=True, check=True)
    runtime = json.loads(result.stdout)["runtime"]
    api = HfApi()
    session = selected_session(api, args.session)
    revision = api.repo_info(REPO, repo_type="dataset").sha
    files = api.list_repo_files(REPO, repo_type="dataset", revision=revision)
    state = {"phase": "awaiting_first_snapshot"}
    if f"{session}/control/status.json" in files:
        status_path = hf_hub_download(REPO, repo_type="dataset", revision=revision,
                                      filename=f"{session}/control/status.json")
        with open(status_path, encoding="utf-8") as handle:
            state = json.load(handle)
    report = {"space": SPACE, "session": session, "artifact_revision": revision,
              "stage": runtime["stage"], "phase": state.get("phase"),
              "updated_utc": state.get("updated_utc"), "deadline_epoch": state.get("deadline_epoch"),
              "error": state.get("error"), "completed_runs": [], "progress_samples": []}
    if session.startswith(("inference-", "noise-probe-")):
        noise = session.startswith("noise-probe-")
        path = f"{session}/{'noise_probe_result' if noise else 'inference_result'}/report.json"
        if path in files:
            metadata = api.repo_info(REPO, repo_type="dataset", revision=revision, files_metadata=True)
            item = next(item for item in metadata.siblings if item.rfilename == path)
            if not metadata.private or not 0 < item.size <= 2 * 2**20:
                raise ValueError("Inference result is not private bounded JSON")
            local = hf_hub_download(REPO, repo_type="dataset", revision=revision, filename=path)
            with open(local, encoding="utf-8") as handle:
                report["physics_only_probe" if noise else "inference_only"] = (
                    noise_probe_summary(json.load(handle)) if noise else inference_summary(json.load(handle)))
        print(json.dumps(report, indent=2))
        return
    prefix = campaign_prefix(session)
    for path in files:
        if path.startswith(prefix) and path.endswith("/evaluation.json"):
            local = hf_hub_download(REPO, repo_type="dataset", revision=revision, filename=path)
            with open(local, encoding="utf-8") as handle:
                evaluation = json.load(handle)
            records = (evaluation["after_cloning"] if session.startswith("onstate-")
                       else evaluation["final"] if session.startswith("imitation-") else evaluation["after"])
            report["completed_runs"].append({
                "name": path.split("/")[-2],
                "reference_cases": len(records),
                "ledge_successes": sum(bool(r["final"]["milestone_success"]["first_ledge_v1"]) for r in records),
                "full_climb_successes": sum(bool(r["final"]["success"]) for r in records),
                "secondary_support_successes": sum(bool(r["final"]["milestone_success"].get(
                    "first_platform_support_diagnostic_v2", False)) for r in records)
                    if session.startswith(("timing-", "imitation-", "onstate-")) else None,
            })
        if path.startswith(prefix) and path.endswith("/physical_trace.jsonl"):
            local = hf_hub_download(REPO, repo_type="dataset", revision=revision, filename=path)
            with open(local, encoding="utf-8") as handle:
                lines = [line for line in handle if line.strip()]
            if lines:
                sample = json.loads(lines[-1])
                report["progress_samples"].append({
                    "name": path.split("/")[-2], "transition": sample.get("transition"),
                    "body_x": sample.get("player_world_x"), "body_y": sample.get("player_world_y"),
                    "retained_gain": sample.get("retained_gain"), "max_gain": sample.get("max_gain"),
                    "milestone_success": sample.get("milestone_success"),
                    "controlled_physics_ticks_total": sample.get("controlled_physics_ticks_total"),
                    "reset_settling_physics_ticks_total": sample.get("reset_settling_physics_ticks_total"),
                })
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
