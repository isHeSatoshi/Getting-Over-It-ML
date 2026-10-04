"""Prepare a conditional physical-time control study. Never launches training."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from research.browser_bridge import ROOT
from research.evaluation_cases import STANDARD_CASES
from research.milestones import FIRST_LEDGE
from research.provenance import fingerprint
from research.reward import RewardConfig
from research.timing_probe import PLATFORM_SUPPORT


def plan():
    reward = RewardConfig()
    physical_ticks = 98304 * 4
    rollout_ticks, minibatch_ticks = 2048 * 4, 256 * 4
    arms = []
    for repeat in (1, 4):
        steps = physical_ticks // repeat
        rollout_steps, batch_size = rollout_ticks // repeat, minibatch_ticks // repeat
        optimizer_calls = (steps // rollout_steps) * 10 * (rollout_steps // batch_size)
        arms.append({
            "name": f"ppo_absolute_repeat_{repeat}", "algorithm": "ppo", "action": "absolute",
            "frame_skip": repeat, "transitions": steps, "max_training_physics_ticks": physical_ticks,
            "gamma": reward.gamma(repeat), "gae_lambda": 0.95 ** (repeat / 4),
            "rollout_steps": rollout_steps, "batch_size": batch_size, "epochs": 10,
            "planned_optimizer_calls": optimizer_calls,
            "gradient_sample_presentations": steps * 10,
            "episode_decisions": 12000 // repeat, "episode_physics_ticks": 12000,
            "evaluation_decisions": 1800 // repeat, "evaluation_physics_ticks": 1800,
        })
    cases = []
    for case in STANDARD_CASES:
        descriptor = case.describe()
        cases.append({
            "name": case.name, "reset_seed": case.reset_seed,
            "warmup_targets": list(case.warmup),
            "warmup_target_hold_ticks": 4,
            "warmup_total_ticks": len(case.warmup) * 4,
            "action_noise_std": case.action_noise_std,
            "noise_seed": case.noise_seed, "noise_hold_ticks": 4,
            "noise_semantics": "Draw once per physical four-tick block, hold noise offset; "
                               "one-tick policy predictions still update every tick",
        })
    return {
        "version": "physical-time-control-study-v1",
        "state": "prepared_only_not_executable",
        "activation": "Only after a complete validated pilot with no follow-up eligible variant; "
                      "a new diagnostic, never promotion of a failed pilot",
        "hypothesis": "Finer reactive observation/control timing improves first-platform retention "
                      "under matched nominal physical-time budget and optimizer-call count",
        "training_seeds": [3, 4, 5],
        "fixed": {"backend": "fast", "evaluation_backend": "reference",
                  "terrain": True, "reward": reward.describe(4),
                  "reward_contract_note": "Same reward parameters; each arm substitutes its own frame_skip/gamma",
                  "policy_architecture": [256, 256], "learning_rate": 0.0003,
                  "raw_rewards": True, "frozen_evaluation_normalization": True,
                  "ordinary_training_start": True, "privileged_resets": False,
                  "torch_threads": 1},
        "arms": arms,
        "cases": cases,
        "benchmarks": {"frozen_central_target": FIRST_LEDGE.__dict__,
                       "secondary_platform_support": PLATFORM_SUPPORT.__dict__,
                       "requires_secondary_physical_calibration_before_activation": True},
        "primary_comparison": "Worst-training-seed reference central-target hold fraction; "
                              "report calibrated platform support alongside without rewriting pilot outcomes",
        "compute_caveat": "Equal optimizer-call count is not equal FLOPs or identical gradient information. "
                         "One-tick arm has four times more decisions/gradient sample presentations, "
                         "larger minibatches, different correlation, and greater observation/RPC overhead. "
                         "Terminal decisions can be shorter than nominal repeats; report actual controlled "
                         "ticks and reset-settling ticks separately rather than claiming identical exposure.",
        "measurements": ["actual_transitions", "actual_physics_ticks_including_terminal_short_steps",
                         "completed_optimizer_step_calls", "gradient_sample_presentations",
                         "learning_wall_seconds", "process_cpu_rss", "compute_cost",
                         "central_target_holds", "secondary_support_holds",
                         "retained_gain", "deaths", "full_climb_completions"],
        "preconditions": ["Complete and pause the original pilot",
                          "Implement/version timing-aware training, GAE, horizon, evaluation and perturbations",
                          "Pass unit/smoke and frame-skip-specific fast/reference fidelity",
                          "Calibrate the separate platform-support descriptor physically",
                          "Reserve a new bounded budget/session and verify unattended runtime admission"],
        "resource_policy": {"tier": "cpu-upgrade", "replicas": 1, "concurrency": 1,
                            "maximum_hours": 16, "no_automatic_hardware_upgrade": True},
        "stopping": "Six predeclared fresh runs, or technical failure/persisted deadline; "
                    "no blind resume, no automatic scaling, no completion claim from first-platform results",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New absolute JSON file, refuses overwrite")
    args = parser.parse_args()
    output = args.output or ROOT / "artifacts" / (
        "timing_study_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")) / "plan.json"
    if not output.is_absolute():
        parser.error("Pass an absolute output path")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump({"provenance": fingerprint(), "plan": plan()}, handle, indent=2)
    print("Prepared only, no jobs launched:", output)


if __name__ == "__main__":
    main()
