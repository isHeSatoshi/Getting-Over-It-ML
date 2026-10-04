"""Frozen data-addition comparison proposal, never a training admission."""
from research.evaluation_cases import EvaluationCase
from research.reward import RewardConfig
from research.study_metrics import benchmark_contract

VERSION = "logged-success-data-comparison-v1"
ARMS = ("original_demonstrations", "original_plus_logged_success")
SEEDS = (9, 10, 11)
VALIDATION_CASES = (
    EvaluationCase("nominal", 10001),
    EvaluationCase("new_hammer_left", 10001, ((-0.625, 0.375),) * 3),
    EvaluationCase("new_hammer_right", 10001, ((0.625, 0.375),) * 3),
    *(EvaluationCase(f"new_action_noise_{i}", 10001, action_noise_std=0.02,
                    noise_seed=10100 + i) for i in range(6)),
)


def plan():
    return {
        "version": VERSION,
        "activation": "Proposal only. Requires fresh source, passed Linux preflight, verified PAUSED, "
                      "new session/reservation/deadline and separate data-bound remote trainer admission.",
        "hypothesis": "Adding controls actually applied at successful learner states improves closed-loop "
                      "first-ledge control over the original demonstrations alone.",
        "training_seeds": list(SEEDS), "arms": list(ARMS),
        "run_order": [{"arm": arm, "seed": seed} for seed in SEEDS for arm in ARMS],
        "environment": {"ordinary_start": True, "privileged_resets": False,
                        "observations": 217, "terrain": True, "action_mode": "absolute",
                        "frame_skip": 1, "physics_hz": 30.0},
        "reward_contract": RewardConfig().describe(1),
        "initialization": {"architecture": [256, 256], "device": "cpu", "threads": 1,
                           "matched_seed_initial_parameters_exact": True,
                           "fresh_models": True, "resume": False},
        "data": {"original_rows": 3576, "logged_success_rows": 1800,
                 "augmented_rows": 5376,
                 "normalization": "Original eligible demonstration RMS only, exact and frozen in both arms",
                 "clip_obs": 10.0, "epsilon": 1e-8,
                 "raw_source": "Previously captured exact legal replay; never inverse clipping",
                 "targets": "Actual applied legal controls at exact pre-action observations only",
                 "ambiguity": "Retain all logged labels, including the shared-input noisy target range. "
                              "No averaging, replacement or hidden removal in data preparation.",
                 "selection": "Post-hoc clone7/noise8105 success. Development/training data, not a "
                              "corrective oracle or independent validation.",
                 "failed_cases": "Diagnostics only, never relabel with the successful time-index suffix"},
        "cloning": {"actor_only": True, "updates": 2000, "batch_size": 256,
                    "learning_rate": 0.001, "sample_presentations_per_run": 512000,
                    "original_arm_per_batch": {"original": 256, "logged_success": 0},
                    "augmented_arm_per_batch": {"original": 192, "logged_success": 64},
                    "sampling": "Uniform with replacement within each source, then shuffle batch",
                    "value_logstd_and_ppo_optimizer_preserved": True,
                    "rl_transitions": 0, "ppo_optimizer_calls": 0,
                    "admission": "Current on-state warm-start support is smoke-only, at most8updates x64"},
        "evaluation": {"backend": "reference", "seconds": 60, "decisions": 1800,
                       "physical_case_clock": True, "noise_hold_ticks": 4,
                       "cases": [case.describe() for case in VALIDATION_CASES],
                       "benchmarks": benchmark_contract(True),
                       "checkpoints": ["untrained", "after_cloning"],
                       "initial_matched_seed_traces_exact": True,
                       "old_noise8105": "Training-selected development case, never counted in validation",
                       "final_held_out": "At least20new predeclared cases per seed and upper-route fidelity "
                                         "still required for full-climb verification"},
        "gate": {"nominal_central_hold_every_seed": True,
                 "minimum_central_holds_per_seed": 8, "cases_per_seed": 9,
                 "full_goal_verified_from_this_comparison": False,
                 "primary_goal": "Unchanged worst-seed independent full-climb completion, not BC loss"},
        "budget": {"hardware": "CPU Upgrade", "one_replica": True, "sequential": True,
                   "maximum_session_seconds": 7200, "maximum_estimated_usd": 0.06,
                   "new_reservation_required": True, "cumulative_ceiling_usd": 10,
                   "auto_pause": True, "interrupted_training_resume": False,
                   "maximum_reference_rollouts": 108, "maximum_control_ticks": 194400,
                   "maximum_reset_ticks": 25920},
        "caveats": ["Equal optimizer calls and sample presentations are not equal FLOPs or wall time.",
                    "Only one selected successful trajectory is added; robustness is not assumed.",
                    "Fresh structured perturbations are not IID physical worlds.",
                    "No additional PPO, new physics features, reward changes or kernel experiments."],
    }
