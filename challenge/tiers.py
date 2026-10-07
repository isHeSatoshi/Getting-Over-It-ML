"""Challenge tiers, held-out cases, and the scoring contract.

Scoring is defined here once so every submission is measured identically.
Nothing in this file can be changed by a submission.
"""
from dataclasses import asdict, dataclass, field
import math

# --- Physical task definition (from the original game's own blocks) -------
SUCCESS_Y = 16000.0
DEATH_Y = -180.0
PHYSICS_HZ = 30.0
START_Y_MIN, START_Y_MAX = 15.0, 30.0


@dataclass(frozen=True)
class Region:
    """A physical box the body must be inside and hold inside."""
    name: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    hold_seconds: float = 3.0
    max_speed_per_tick: float = 2.0
    min_body_contact_fraction: float = 0.8

    def __post_init__(self):
        if not self.name:
            raise ValueError("Region needs a name")
        values = (self.x_min, self.x_max, self.y_min, self.y_max,
                  self.hold_seconds, self.max_speed_per_tick,
                  self.min_body_contact_fraction)
        if not all(math.isfinite(v) for v in values):
            raise ValueError(f"Region {self.name} has non-finite values")
        if self.x_min >= self.x_max or self.y_min >= self.y_max:
            raise ValueError(f"Region {self.name} is not a real box")
        if self.hold_seconds <= 0 or self.max_speed_per_tick <= 0:
            raise ValueError(f"Region {self.name} has non-positive limits")
        if not 0.0 <= self.min_body_contact_fraction <= 1.0:
            raise ValueError(f"Region {self.name} has an invalid contact fraction")


# Tier 0: settle and stay on the original starting terrain.
# Measured: spawn rests at world (0, 21) with body contact true.
TIER0 = Region("tier0_settled_ground", -20.0, 20.0, 15.0, 30.0)

# Tier 1: the first ledge. The hand-designed controller holds at (322.59, 104).
TIER1 = Region("tier1_first_ledge", 305.0, 335.0, 100.0, 112.0)

# Tier 2: the wall-side approach held by the coarse-phase controller (~289.5, 104).
TIER2 = Region("tier2_wall_approach", 280.0, 300.0, 100.0, 112.0)

TIER_REGIONS = (TIER0, TIER1, TIER2)

#: Consecutive qualifying ticks required for a hold, for the default 3s/30Hz.
REGION_HOLD_TICKS = int(round(TIER0.hold_seconds * PHYSICS_HZ))


@dataclass(frozen=True)
class EvaluationCase:
    """One reproducible evaluation condition.

    A case is fully described by legal inputs only. Nothing is privileged.
    """
    name: str
    reset_seed: int
    warmup: tuple = ()
    action_noise_std: float = 0.0
    noise_seed: int = 0
    public: bool = True

    def describe(self):
        return asdict(self)


def _standard_cases():
    cases = [
        EvaluationCase("nominal", 1001),
        EvaluationCase("hammer_left", 1001, ((-0.5, 0.5),) * 3),
        EvaluationCase("hammer_right", 1001, ((0.5, 0.5),) * 3),
    ]
    cases += [
        EvaluationCase(f"action_noise_{i}", 1001, action_noise_std=0.02,
                       noise_seed=8100 + i)
        for i in range(6)
    ]
    return tuple(cases)


#: The nine public cases every submission is scored on.
STANDARD_CASES = _standard_cases()

#: Held-out seeds. Seeds are published; the *gates* below are not.
HOLDOUT_SEEDS = (2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008)


def holdout_cases():
    """Unpublished-case generator.

    The seed list is public so results are reproducible, but these cases are
    not part of the public leaderboard. A submission that special-cases the
    public set will not transfer.
    """
    return tuple(EvaluationCase(f"holdout_{seed}", seed, public=False)
                 for seed in HOLDOUT_SEEDS)


# --- Promotion gates --------------------------------------------------------
# A result counts as a *pass* only if every one of these holds.
GATES = {
    "tier0_required": True,
    "holdout_pass_fraction": 0.8,
    "heldout_case_count": 20,
    "deaths_allowed_on_nominal": 0,
    "summit_required_for_full_climb": True,
}


def gate_report(tier_pass_fraction, holdout_pass_fraction, nominal_deaths,
                summit_reached, heldout_cases):
    """Evaluate the promotion gates. Pure function, easy to audit."""
    checks = {
        "tier0_passed": tier_pass_fraction >= 0.8,
        "holdout_cases_run": heldout_cases >= GATES["heldout_case_count"],
        "holdout_passed": holdout_pass_fraction >= GATES["holdout_pass_fraction"],
        "nominal_deaths_clean": nominal_deaths <= GATES["deaths_allowed_on_nominal"],
        "summit": bool(summit_reached) if GATES["summit_required_for_full_climb"] else True,
    }
    return {"checks": checks, "passed": all(checks.values())}


# --- Baseline to beat -------------------------------------------------------
#: Measured on the reference (uncached, fully drawn) worker.
BASELINE = {
    "name": "contact-sign-stroke-controller-v1",
    "kind": "hand-designed causal controller (NOT learned)",
    "retained_gain_units": 83.0,
    "terminal_position": [322.585886, 104.0],
    "nominal_deaths": 0,
    "measured_push_control": {
        "description": "hold the pointer at (0, -128) for 120 ticks from spawn",
        "start_y": 21.0,
        "end_y": 86.46260379880928,
        "note": "Causal sanity check only. Not a climb.",
    },
    "note": "Reaches and holds the tier1 ledge region. Beating this with "
            "learning is the headline goal.",
}

SCORING = {
    "primary": "highest tier region held, then retained height (units)",
    "tiebreak": "fewer nominal deaths, then fewer decisions to first hold",
    "never_accepted_as_score": [
        "transient maximum height (high-water mark without retained hold)",
        "shaped reward return from an unfinished episode",
        "a single deterministic replay seed",
    ],
}
