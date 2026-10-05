"""Frozen residual-PPO proposal; preparation is not paid-work authorization."""
import json

from research.evaluation_cases import EvaluationCase
from research.residual_policy import contract as policy_contract
from research.reward import RewardConfig
from research.study_metrics import benchmark_contract

VERSION = "explicit-context-residual-ppo-study-v1"
SEEDS = (12, 13, 14)
CASES = (
    EvaluationCase("nominal", 15001),
    EvaluationCase("new_left", 15001, ((-.75, -.125),)*3),
    EvaluationCase("new_right", 15001, ((.75, -.125),)*3),
    *(EvaluationCase(f"new_noise_{i}", 15001, action_noise_std=.02, noise_seed=14100+i)
      for i in range(6)),
)
TRANSITIONS = 131072
MAX_RESETS = 257


def plan():
    return json.loads(json.dumps({
        "version": VERSION,
        "activation": "Proposal only; new reservation/source/session/preflight/verified PAUSED "
                      "and direct-parent Linux permit required. Never resume interrupted work.",
        "hypothesis": "Starting from exact legal zero-correction control and explicit222 causal "
                      "context lets on-policy residual PPO improve physical acquisition/retention "
                      "beyond the same hand-designed baseline, without supervised target labels.",
        "training_seeds": list(SEEDS), "policy": policy_contract(),
        "environment": {"ordinary_start": True, "frame_skip": 1, "horizon": 1800,
                        "observations": 222, "raw_observations": 217, "action": "residualBox2",
                        "training_backend": "fast", "evaluation_backend": "reference"},
        "reward": RewardConfig().describe(1),
        "ppo": {"n_steps": 1024, "batch_size": 128, "n_epochs": 3,
                "learning_rate": .0001, "gamma": RewardConfig().gamma(1),
                "gae_lambda": .95**.25, "clip_range": .2, "ent_coef": 0.,
                "vf_coef": .5, "max_grad_norm": .5, "target_kl": .01},
        "training": {"transitions_per_seed": TRANSITIONS, "maximum_resets_per_seed": MAX_RESETS,
                     "maximum_optimizer_calls_per_seed": 3072,
                     "normalization": "Fresh222 RMS, online ONLY actual training contexts, frozen for evaluation",
                     "evaluation_updates_normalizer": False, "reward_normalization": False,
                     "checkpoints": [65536, TRANSITIONS], "checkpoint_selection": "Final only, no case-based selection",
                     "trace_every_transitions": 256, "device": "cpu", "torch_threads": 1,
                     "external_warmup_or_noise_during_training": False, "teacher_labels": False},
        "evaluation": {"cases": [case.describe() for case in CASES], "benchmarks": benchmark_contract(True),
                       "decisions": 1800, "noise_hold_ticks": 4,
                       "checkpoints": ["zero_actor", "final"], "zero_actor_residual": [0., 0.],
                       "normalization": "Copy/freeze training RMS for learned evaluation; zero actor bypasses policy",
                       "reset_scope": "Direct Gym evaluation: one120-tick reset/case, no VecEnv auto-reset",
                       "legal_full_trace": "Actual pre/post raw217/actor222/residual/final-issued/applied/physical state",
                       "freshness": "Reset15001/noise14100..14105 absent from prior artifacts before declaration"},
        "comparison": {"primary": "Worst-seed reference original full-climb completion, unchanged goal",
                       "learned_first_ledge_benefit": "All3 nominal central holds, >=8/9 central each, "
                       "no extra deaths, no lower median retained gain, each seed gains >=1 central hold "
                       "over SAME zeroactor OR gains a full completion. Otherwise no reliable benefit claim.",
                       "baseline_holds_are_learning": False, "final_goal_verified_from_this_study": False,
                       "final_evidence": ">=20new heldout cases/seed, >=80%completion/nominaleach, "
                                         "upper-route fast/reference fidelity and saved-policy replay still required"},
        "budget": {"hardware": "cpu-upgrade", "replicas": 1, "sleep": "never",
                   "maximum_session_seconds": 7200, "maximum_estimated_usd": .06,
                   "cumulative_ceiling_usd": 10., "new_reservation_required": True,
                   "maximum_training_control_ticks": 3*TRANSITIONS,
                   "maximum_training_reset_ticks": 3*MAX_RESETS*120,
                   "maximum_evaluation_rollouts": 54, "maximum_evaluation_control_ticks": 97200,
                   "maximum_evaluation_reset_ticks": 6480, "maximum_bridge_bootstrap_ticks": 720,
                   "maximum_total_physics_ticks": 590136, "auto_pause": True},
        "caveats": ["Structured cases are not IID worlds.", "Initial baseline holds are not ML progress.",
                    "Small first-ledge improvement is not a summit or scale admission.",
                    "Current hourly price must be reverified before a real reservation."],
    }))
