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
    for path in files:
        if path.startswith(f"{session}/pilot_campaign/runs/") and path.endswith("/evaluation.json"):
            local = hf_hub_download(REPO, repo_type="dataset", revision=revision, filename=path)
            with open(local, encoding="utf-8") as handle:
                evaluation = json.load(handle)
            records = evaluation["after"]
            report["completed_runs"].append({
                "name": path.split("/")[-2],
                "reference_cases": len(records),
                "ledge_successes": sum(bool(r["final"]["milestone_success"]["first_ledge_v1"]) for r in records),
                "full_climb_successes": sum(bool(r["final"]["success"]) for r in records),
            })
        if path.startswith(f"{session}/pilot_campaign/runs/") and path.endswith("/physical_trace.jsonl"):
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
                })
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
