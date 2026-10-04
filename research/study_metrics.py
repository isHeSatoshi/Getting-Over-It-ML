"""Opt-in calibrated diagnostics; never reward terms or changes to pilot gates."""
from research.milestones import FIRST_LEDGE, MilestoneTracker
from research.timing_probe import PLATFORM_SUPPORT


def benchmark_contract(secondary_support=False):
    if type(secondary_support) is not bool:
        raise ValueError("Invalid secondary support setting")
    milestones = (FIRST_LEDGE, PLATFORM_SUPPORT) if secondary_support else (FIRST_LEDGE,)
    return [milestone.__dict__.copy() for milestone in milestones]


def enable_platform_support(environment):
    env = environment.unwrapped
    if env.state is not None:
        raise ValueError("Configure secondary support before the first reset")
    if env.milestones.milestones != (FIRST_LEDGE,):
        raise ValueError("Secondary support requires the unchanged default v1 tracker")
    env.milestones = MilestoneTracker(
        (FIRST_LEDGE, PLATFORM_SUPPORT), physics_hz=env.reward_config.physics_hz)
    return environment
