"""Approved goal-conditioned SAC/HER pilot; no job is launched by this module."""
import json

from research.evaluation_cases import EvaluationCase

VERSION = "legal-prefix-goal-sac-her-v1"
SEEDS = (21, 22, 23)
MAX_LEARNER = 160000
MAX_PHYSICS = 1200000
MAX_CYCLES = 77952
MAX_PREFIX = 1800
SUFFIX_TICKS = 600
CASES = (
    EvaluationCase("nominal", 18001),
    EvaluationCase("left", 18001, ((-.75, -.125),)*3),
    EvaluationCase("right", 18001, ((.75, -.125),)*3),
    *(EvaluationCase(f"noise_{i}", 18001, action_noise_std=.02, noise_seed=17100+i) for i in range(7)),
)


def plan():
    return json.loads(json.dumps({
        "version": VERSION, "seeds": list(SEEDS), "algorithm": "SAC", "goal_frame": 155,
        "stack_frames": 4, "observation_dimension": 620, "action": "own absolute float32 pointerBox2",
        "network": [128, 128], "activation": "ReLU", "learning_rate": .0003,
        "batch_size": 256, "tau": .005, "gamma": .995, "entropy": "auto",
        "target_entropy": -2, "replay_capacity": 300000, "her_sample_fraction": .5,
        "learning_starts": 4096, "one_update_per_learner_ticks": 2,
        "max_learner_transitions_per_seed": MAX_LEARNER,
        "max_total_physics_ticks_per_seed": MAX_PHYSICS,
        "max_sac_cycles_per_seed": MAX_CYCLES, "max_prefix_ticks": MAX_PREFIX,
        "suffix_ticks": SUFFIX_TICKS, "archive_cells": 256, "representatives_per_cell": 2,
        "start_probabilities": [.4, .4, .2], "goal_probabilities": [.5, .25, .25],
        "training_perturbations": ["nominal", "left12", "right12", "noise.02held4"],
        "normalizer": "Fixed existing feature scales; goal deltas/150; no RMS or clipping",
        "reward": "-min(distance/100,2)-.05*min(speed/2,10)+I[distance<=12,speed<=2]-10*I[death]",
        "evaluation_cases": [case.describe() for case in CASES], "evaluation_ticks": 3600,
        "pilot_gate": {"nominal_first_ledge_each_seed": True, "first_ledge_cases_required": 8,
                       "cases": 10, "nominal_retained_y": 180, "retained_ticks": 90,
                       "maximum_speed": 2, "prefix_or_playback_in_evaluation": False,
                       "stop_after_first_seed_failure": True},
        "budget": {"maximum_paid_seconds": 36000, "maximum_reserved_usd": .30,
                   "cumulative_ceiling_usd": 10, "hardware": "cpu-upgrade", "replicas": 1,
                   "sequential_seeds": True, "one_simulator_at_a_time": True,
                   "new_session_deadline_preflight_required": True},
        "final_goal": "Unchanged3seed ordinary-spawn summit,>=80% of20untouched cases/seed, "
                      "upper-route reference/fast fidelity and closed-loop saved-policy replay.",
        "resume": "Never automatically resume interrupted work, even when replay/optimizer backups exist.",
    }))
