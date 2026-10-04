"""Predeclared follow-up proposal only. No job launch or budget admission."""
from research.behavior_cloning import VERSION as CLONING_VERSION
from research.demonstrations import TRAINING_CASES, VERSION as DATA_VERSION
from research.evaluation_cases import STANDARD_CASES
from research.reward import RewardConfig
from research.study_metrics import benchmark_contract


def plan():
    return {
        "version": "demonstration-assisted-first-skill-v1",
        "activation": "Requires complete validated timing results, independently verified PAUSED, "
                      "new source/preflight/session/reservation and remote-only trainer admission",
        "hypothesis": "Successful legal observation/action demonstrations improve ordinary-start "
                      "reactive first-ledge retention compared with from-scratch PPO",
        "training_seeds": [6, 7, 8],
        "arms": ["ppo_from_scratch", "behavior_cloning_only", "behavior_cloning_then_ppo"],
        "observations": "Unchanged 217-feature terrain/raw settled-history observation",
        "action_mode": "absolute", "frame_skip": 1, "ordinary_start": True,
        "privileged_resets": False, "reward_contract": RewardConfig().describe(1),
        "data": {"version": DATA_VERSION, "expert_ticks": 600,
                 "cases": [case.describe() for case in TRAINING_CASES],
                 "eligibility": "Central-held trajectories only, exclude forced warm-up labels; "
                                "preserve failed physical trajectories as diagnostics",
                 "normalization": "Fit RMS on eligible training demonstrations only, freeze in all arms",
                 "recovery_limit": "Time-indexed teacher is not a DAgger corrective oracle"},
        "cloning": {"version": CLONING_VERSION, "actor_only": True, "updates": 2000,
                    "batch_size": 256, "learning_rate": 0.001,
                    "ppo_optimizer_reset": "BC uses a separate optimizer; PPO remains fresh",
                    "sample_presentations": 512000,
                    "admission": "Not executable through the current smoke-only API"},
        "ppo": {"transitions": 393216, "rollout_steps": 8192, "batch_size": 1024,
                "epochs": 10, "gae_lambda": 0.95**0.25,
                "planned_policy_optimizer_calls": 3840, "episode_seconds": 400,
                "architecture": [256, 256],
                "exploration_std": "Same original PPO initialization across arms; no silent tuning"},
        "evaluation": {"backend": "reference", "seconds": 60,
                       "physical_case_clock": True,
                       "cases": [case.describe() for case in STANDARD_CASES],
                       "benchmarks": benchmark_contract(True),
                       "checkpoints": ["untrained", "after_cloning_if_applicable", "final"],
                       "held_out": "Declare new streams only after choosing a promising candidate"},
        "gate": "No scaling unless all three seeds reproduce nominal central retention and "
                "at least 8/9 central holds in frozen reference cases; full summit remains separate",
        "budget": {"hardware": "CPU Upgrade", "one_replica": True, "sequential": True,
                   "maximum_hours": 16, "new_reservation_required": True,
                   "cumulative_ceiling_usd": 10, "auto_pause": True,
                   "interrupted_training_resume": False},
        "caveats": ["BC-only has zero RL transitions; arms are not equal total compute.",
                    "BC adds labeled sample/optimizer work beyond the matched PPO budget.",
                    "Training demos and standard cases do not verify final held-out full-game success.",
                    "This plan neither launches nor guarantees successful skill acquisition."],
    }
