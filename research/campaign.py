"""Controlled research matrix and evidence gates. Launching is remote-only."""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import psutil
from research.browser_bridge import ROOT
from research.evaluation_cases import STANDARD_CASES
from research.milestones import FIRST_LEDGE
from research.provenance import fingerprint
from research.resources import effective_limits

CAMPAIGN_VERSION = "first-obstacle-v1"
VARIANTS = (("ppo_absolute", "ppo", "absolute"), ("sac_absolute", "sac", "absolute"),
            ("sac_velocity", "sac", "velocity"))
RUN_RAM_GIB = 8


def plan(stage="pilot", selected_variant=None):
    if stage not in ("pilot", "followup", "scale") or (
            stage != "pilot" and selected_variant not in {v[0] for v in VARIANTS}):
        raise ValueError("Invalid campaign stage or selected variant")
    variants = VARIANTS if stage == "pilot" else tuple(v for v in VARIANTS if v[0] == selected_variant)
    seeds = (3, 4, 5, 6, 7) if stage == "scale" else (0, 1, 2)
    steps = {"pilot": 98304, "followup": 499712, "scale": 999424}[stage]
    result = {
        "version": CAMPAIGN_VERSION, "stage": stage, "selected_variant": selected_variant,
        "research_question": {"pilot": "Learn to reach and hold the first raised ledge",
                              "followup": "Validate broader/full-climb progress before scaling",
                              "scale": "Replicate full-climb success on new training seeds"}[stage],
        "benchmark": FIRST_LEDGE.__dict__, "training_seeds": list(seeds),
        "fixed": {"backend": "fast", "reward_profile": "settled", "discount_half_life": 120,
                  "terrain": True, "evaluation_backend": "reference",
                  "evaluation_decisions": 450 if stage == "pilot" else 3000,
                  "evaluation_cases": [c.describe() for c in STANDARD_CASES], "replay_buffer_size": 200000},
        "runs": [{"name": f"{name}_seed_{seed}", "variant": name, "algorithm": algorithm,
                  "action": action, "seed": seed, "steps": steps}
                 for name, algorithm, action in variants for seed in seeds],
        "resource_policy": {"max_parallel_runs": 2, "ram_gib_per_run_reserved": RUN_RAM_GIB,
                            "host_ram_reserve_gib": 4, "suggested_logical_cpus_per_run": 4},
        "promotion": {
            "minimum_training_seeds": len(seeds), "minimum_cases_per_seed": len(STANDARD_CASES),
            "minimum_success_rate_each_seed": 0.8, "minimum_improvement_each_seed": 0.2,
            "next_stage": "controlled_next_obstacle_study",
            "large_scale_authorized": False,
            "large_scale_reason": "First-ledge success alone does not establish a likely full-climb solution",
            "full_climb_success_rate_each_seed_required_for_scale": 0.5,
            "nominal_full_climb_required_each_seed": True,
        },
    }
    # JSON is the persisted protocol; tuple/list differences must not masquerade
    # as source/protocol drift after loading a freshly prepared campaign.
    return json.loads(json.dumps(result))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def command(run, fixed, output, smoke=False):
    args = [sys.executable, "-m", "research.train", "--algorithm", run["algorithm"], "--action", run["action"],
            "--backend", fixed["backend"], "--reward-profile", fixed["reward_profile"],
            "--discount-half-life", str(fixed["discount_half_life"]), "--seed", str(run["seed"]),
            "--steps", "128" if smoke else str(run["steps"]), "--evaluation-suite", "standard",
            "--evaluation-decisions", str(fixed["evaluation_decisions"]),
            "--replay-buffer-size", str(fixed["replay_buffer_size"]), "--output-dir", str(output),
            "--smoke" if smoke else "--remote-training"]
    return args


def summarize_evaluation(records):
    expected = {case.name for case in STANDARD_CASES}
    if len(records) != len(expected) or {r["case"]["name"] for r in records} != expected:
        raise ValueError("Missing, duplicate, or unexpected evaluation cases")
    success = []
    full_success = []
    for record in records:
        if record["case"] != json.loads(json.dumps(next(c.describe() for c in STANDARD_CASES
                                                        if c.name == record["case"]["name"]))):
            raise ValueError("Evaluation perturbation contract changed")
        if record["decisions"] != len(record["trace"]) or record["decisions"] < 1:
            raise ValueError("Invalid evaluation trace length")
        # Requiring the complete reference trace prevents fabricated final highs
        # or a diagnostic calibration report from passing this gate.
        final = record["final"]
        if final != {k: v for k, v in record["trace"][-1].items() if k not in ("action", "applied_action")}:
            # Current evaluator stores the final full trace row, including actions.
            if final != record["trace"][-1]:
                raise ValueError("Final result disagrees with trace")
        if final["milestone_contract"] != [FIRST_LEDGE.__dict__]:
            raise ValueError("Physical benchmark definition changed")
        complete = bool(final.get("success", False))
        if complete and final.get("player_world_y", 0) <= 16000:
            raise ValueError("Claimed completion disagrees with original game height")
        full_success.append(complete)
        # A genuine completed climb supersedes holding an intermediate ledge;
        # never reject a competent fast solver for skipping a three-second stop.
        success.append(bool(final["milestone_success"][FIRST_LEDGE.name]) or complete)
    return {"success_rate": sum(success) / len(success), "cases": len(success),
            "falls": sum(bool(r["final"]["dead"]) for r in records),
            "full_climb_success_rate": sum(full_success) / len(full_success),
            "nominal_full_climb_success": bool(next(r["final"].get("success", False) for r in records
                                                  if r["case"]["name"] == "nominal")),
            "median_retained_gain": float(sorted(r["final"]["retained_gain"] for r in records)[len(records) // 2])}


def promotion(rows, template):
    eligible, scale_eligible = [], []
    gate = template["promotion"]
    for name, _, _ in VARIANTS:
        results = [r for r in rows if r["variant"] == name]
        if (len(results) == gate["minimum_training_seeds"]
                and {r["seed"] for r in results} == set(template["training_seeds"])
                and all(r["after"]["success_rate"] >= gate["minimum_success_rate_each_seed"]
                        and r["improvement"] >= gate["minimum_improvement_each_seed"] for r in results)):
            eligible.append(name)
            if all(r["after"]["full_climb_success_rate"] >= gate["full_climb_success_rate_each_seed_required_for_scale"]
                   and r["after"]["nominal_full_climb_success"] for r in results):
                scale_eligible.append(name)
    return eligible, scale_eligible


def aggregate(directory):
    directory = Path(directory)
    campaign = json.loads((directory / "campaign.json").read_text(encoding="utf-8"))
    template = campaign["plan"]
    if template != plan(template["stage"], template.get("selected_variant")):
        raise ValueError("Campaign protocol changed; aggregate under the recorded version")
    rows, missing = [], []
    dependency_versions = None
    for run in template["runs"]:
        path = directory / "runs" / run["name"]
        if not (path / "evaluation.json").exists():
            missing.append(run["name"])
            continue
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        evaluation = json.loads((path / "evaluation.json").read_text(encoding="utf-8"))
        training = json.loads((path / "training_summary.json").read_text(encoding="utf-8"))
        config = manifest["config"]
        versions = {key: manifest[key] for key in ("numpy", "torch", "stable_baselines3")}
        if dependency_versions is None:
            dependency_versions = versions
        elif dependency_versions != versions:
            raise ValueError("Campaign mixes different learner dependency versions")
        if (manifest["purpose"] != "remote research run" or config["smoke"] or not config["remote_training"]
                or manifest["steps"] != run["steps"] or evaluation["evaluation_backend"] != "reference"):
            raise ValueError("Smoke, wrong budget, or non-reference evaluation cannot promote a run")
        if training["actual_transitions"] != run["steps"] or not training["complete"]:
            raise ValueError("Incomplete or unequal transition budget")
        for key in ("algorithm", "action", "seed"):
            if config[key] != run[key]:
                raise ValueError("Run configuration mismatch")
        fixed = template["fixed"]
        for key in ("backend", "reward_profile", "discount_half_life", "evaluation_decisions", "replay_buffer_size"):
            if config[key] != fixed[key]:
                raise ValueError("Fixed campaign setting changed")
        if config["no_terrain"] or config["evaluation_suite"] != "standard":
            raise ValueError("Observation/evaluation contract changed")
        contract = manifest["evaluation_contract"]
        if contract["suite"] != "standard" or contract["decisions"] != fixed["evaluation_decisions"]:
            raise ValueError("Recorded evaluation budget changed")
        for phase in ("before", "after"):
            for record in evaluation[phase]:
                if not record["final"]["dead"] and not record["final"]["success"]:
                    if record["decisions"] != fixed["evaluation_decisions"]:
                        raise ValueError("Evaluation stopped early without a real terminal outcome")
        for key in ("project_sha256", "runtime_sha256", "asset_set_sha256", "source_sha256"):
            if manifest[key] != campaign["provenance"][key]:
                raise ValueError("Campaign mixes different code or game versions")
        before, after = summarize_evaluation(evaluation["before"]), summarize_evaluation(evaluation["after"])
        rows.append({"run": run["name"], "variant": run["variant"], "seed": run["seed"],
                     "before": before, "after": after, "improvement": after["success_rate"] - before["success_rate"]})
    eligible, scale_eligible = promotion(rows, template)
    def rank(variant):
        results = [r for r in rows if r["variant"] == variant]
        return (min(r["after"]["success_rate"] for r in results),
                sum(r["after"]["full_climb_success_rate"] for r in results) / len(results),
                -sum(r["after"]["falls"] for r in results),
                sum(r["after"]["median_retained_gain"] for r in results) / len(results))
    eligible.sort(key=rank, reverse=True)
    scale_eligible.sort(key=rank, reverse=True)
    return {"campaign_version": CAMPAIGN_VERSION, "rows": rows, "missing_runs": missing,
            "followup_eligible_variants": eligible,
            "scale_eligible_variants": scale_eligible,
            "large_scale_authorized": bool(scale_eligible and not missing),
            "decision": "followup" if eligible and not missing else ("incomplete" if missing else "stop_and_diagnose"),
            "warning": "Cases are structured perturbations, not IID trials; no binomial confidence claim is made"}


def execute(directory, max_workers):
    if os.environ.get("FACTORY_DESKTOP_CDP_PORT"):
        raise RuntimeError("Research campaigns cannot execute on this desktop; use a separate host")
    directory = Path(directory)
    campaign = json.loads((directory / "campaign.json").read_text(encoding="utf-8"))
    current = fingerprint()
    critical = ("project_sha256", "runtime_sha256", "asset_set_sha256", "source_sha256")
    expected_plan = plan(campaign["plan"]["stage"], campaign["plan"].get("selected_variant"))
    if campaign["plan"] != expected_plan or any(campaign["provenance"][key] != current[key] for key in critical):
        raise RuntimeError("Campaign code, assets, or protocol changed; prepare again on the target host")
    if expected_plan["stage"] in ("followup", "scale"):
        evidence = aggregate(campaign["promotion_evidence"]["pilot_directory"])
        if (digest(evidence) != campaign["promotion_evidence"]["summary_sha256"]
                or expected_plan["selected_variant"] not in (
                    evidence["scale_eligible_variants"] if expected_plan["stage"] == "scale"
                    else evidence["followup_eligible_variants"])
                or (expected_plan["stage"] == "scale" and not evidence["large_scale_authorized"])):
            raise RuntimeError("Scale-up promotion evidence is missing or no longer valid")
    policy = campaign["plan"]["resource_policy"]
    if not 1 <= max_workers <= policy["max_parallel_runs"]:
        raise ValueError("Worker count exceeds this stage's resource budget")
    limits = effective_limits()
    available_gib = limits["available_ram_bytes"] / 2**30
    if available_gib < max_workers * RUN_RAM_GIB + policy["host_ram_reserve_gib"]:
        raise RuntimeError("Insufficient available RAM for requested concurrency")
    if limits["logical_cpus"] < 4 * max_workers:
        raise RuntimeError("Insufficient logical CPUs for the declared concurrency budget")
    if psutil.disk_usage(str(directory)).free < 20 * 2**30:
        raise RuntimeError("Insufficient free disk for campaign artifacts and safety margin")
    preflight = directory / "fidelity_preflight.log"
    with preflight.open("x", encoding="utf-8") as log:
        result = subprocess.run([sys.executable, "-m", "research.fast_fidelity", "--headless"],
                                cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise RuntimeError("Remote-host fidelity preflight failed; no training jobs launched")
    (directory / "runs").mkdir(exist_ok=True)
    def launch(run):
        output = directory / "runs" / run["name"]
        if output.exists():
            raise RuntimeError("Refusing to overwrite existing run: " + run["name"])
        log = directory / (run["name"] + ".log")
        with log.open("x", encoding="utf-8") as handle:
            result = subprocess.run(command(run, campaign["plan"]["fixed"], output),
                                    cwd=str(ROOT), stdout=handle, stderr=subprocess.STDOUT, check=False,
                                    env={**os.environ, "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
        return {"run": run["name"], "returncode": result.returncode}
    # No uploads, rented resources, or provider API calls. This runs only on the
    # explicitly chosen host, with bounded concurrency and preserved run output.
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        pending = iter(campaign["plan"]["runs"])
        active = {pool.submit(launch, next(pending)) for _ in range(max_workers)}
        failed = False
        while active:
            completed, active = wait(active, return_when=FIRST_COMPLETED)
            for future in completed:
                result = future.result()
                print(json.dumps(result), flush=True)
                failed |= result["returncode"] != 0
            if not failed:
                for _ in completed:
                    run = next(pending, None)
                    if run is not None: active.add(pool.submit(launch, run))
        if failed:
            raise RuntimeError("Campaign stopped scheduling new runs after a failure; outputs preserved")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="operation", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--directory", type=Path)
    p = sub.add_parser("summarize"); p.add_argument("--directory", type=Path, required=True)
    p = sub.add_parser("execute"); p.add_argument("--directory", type=Path, required=True); p.add_argument("--max-workers", type=int, default=1)
    p = sub.add_parser("scale"); p.add_argument("--directory", type=Path, required=True)
    p = sub.add_parser("followup"); p.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "prepare":
        directory = args.directory or ROOT / "artifacts" / ("campaign_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        if not directory.is_absolute(): parser.error("Use an absolute campaign directory")
        directory.mkdir(parents=True, exist_ok=False)
        record = {"plan": plan(), "provenance": fingerprint()}
        (directory / "campaign.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        commands = [command(r, record["plan"]["fixed"], directory / "runs" / r["name"]) for r in record["plan"]["runs"]]
        (directory / "commands.json").write_text(json.dumps(commands, indent=2), encoding="utf-8")
        print("Prepared nine equal-budget remote runs:", directory)
    elif args.operation == "summarize":
        print(json.dumps(aggregate(args.directory), indent=2))
    elif args.operation in ("scale", "followup"):
        result = aggregate(args.directory)
        print(json.dumps(result, indent=2))
        if args.operation == "scale" and not result["large_scale_authorized"]:
            raise SystemExit("Large-scale launch refused: first-ledge success is insufficient; require reproducible reference full-climb evidence.")
        choices = result["scale_eligible_variants"] if args.operation == "scale" else result["followup_eligible_variants"]
        if not choices or result["missing_runs"]:
            raise SystemExit("Follow-up refused: complete the controlled matrix and pass the physical-progress gates first.")
        winner = choices[0]
        target = ROOT / "artifacts" / (args.operation + "_campaign_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        target.mkdir(parents=True)
        record = {"plan": plan(args.operation, winner), "provenance": fingerprint(),
                  "promotion_evidence": {"pilot_directory": str(args.directory.resolve()), "summary_sha256": digest(result)}}
        (target / "campaign.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        print("Prepared gated campaign (not launched):", target)
    else:
        execute(args.directory, args.max_workers)


if __name__ == "__main__":
    main()
