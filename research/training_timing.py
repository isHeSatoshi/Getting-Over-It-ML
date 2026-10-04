"""Explicit trainer timing and observed work, separate from campaign admission."""
import gymnasium as gym

from research.reward import RewardConfig


def training_settings(algorithm, smoke, *, frame_skip=4, timing_study=False,
                      steps=None, evaluation_decisions=None, reward_config=None):
    if (algorithm not in ("ppo", "sac") or type(smoke) is not bool
            or type(timing_study) is not bool or type(frame_skip) is not int
            or frame_skip not in (1, 4)):
        raise ValueError("Invalid training timing configuration")
    if frame_skip != 4 and not timing_study:
        raise ValueError("One-tick training requires the explicit timing study")
    reward = reward_config if reward_config is not None else RewardConfig()
    if timing_study:
        if algorithm != "ppo" or reward != RewardConfig():
            raise ValueError("The prepared timing study fixes PPO and the default settled reward")
        from research.timing_study import plan
        study = plan()
        arm = next(arm for arm in study["arms"] if arm["frame_skip"] == frame_skip)
        default_steps = 512 // frame_skip if smoke else arm["transitions"]
        declared_evaluation = arm["evaluation_decisions"]
        rollout = 256 // frame_skip if smoke else arm["rollout_steps"]
        batch_size = 128 // frame_skip if smoke else arm["batch_size"]
        horizon = 1024 // frame_skip if smoke else arm["episode_decisions"]
        evaluation_budget = 128 // frame_skip if smoke else arm["evaluation_decisions"]
        gae = arm["gae_lambda"]
        version = study["version"]
    else:
        default_steps = 512 if smoke else 1_000_000
        declared_evaluation = 450
        rollout, batch_size = (64, 32) if smoke else (2048, 256)
        horizon, evaluation_budget = (256, 32) if smoke else (3000, None)
        gae, version = 0.95, "legacy-four-tick-v1"
    steps = default_steps if steps is None else steps
    evaluation_decisions = declared_evaluation if evaluation_decisions is None else evaluation_decisions
    if (type(steps) is not int or steps < 1 or (smoke and steps > 2048)
            or type(evaluation_decisions) is not int or not 32 <= evaluation_decisions <= 3000):
        raise ValueError("Invalid training or evaluation budget")
    if timing_study:
        if evaluation_decisions != declared_evaluation:
            raise ValueError("Timing-study evaluation duration differs from its prepared plan")
        if not smoke and steps != arm["transitions"]:
            raise ValueError("Timing-study sample budget differs from its prepared plan")
        if steps % rollout:
            raise ValueError("Timing-study steps must contain complete PPO rollouts")
    if evaluation_budget is None:
        evaluation_budget = evaluation_decisions
    epochs = 2 if smoke else 10
    return {
        "version": version, "timing_study": timing_study, "frame_skip": frame_skip,
        "requested_transitions": steps, "nominal_controlled_physics_ticks": steps * frame_skip,
        "episode_decisions": horizon, "episode_physics_ticks": horizon * frame_skip,
        "evaluation_decisions": evaluation_budget,
        "declared_evaluation_decisions": evaluation_decisions,
        "evaluation_physics_ticks": evaluation_budget * frame_skip,
        "gamma": reward.gamma(frame_skip), "gae_lambda": gae,
        "ppo": {"n_steps": rollout, "batch_size": batch_size, "n_epochs": epochs,
                "gae_lambda": gae},
        "checkpoint_every_decisions": 40000 // frame_skip,
        "trace_every_decisions": 400 // frame_skip if timing_study else 100,
        "physical_case_clock": timing_study,
        "budget_caveat": "Requested ticks are nominal. Terminal short steps reduce actual control; "
                        "resets are separate work. Equal optimizer calls are not equal FLOPs.",
    }


class PhysicalWork(gym.Wrapper):
    """Observe actual training work without altering observations/rewards/info."""
    def __init__(self, env):
        super().__init__(env)
        self.frame_skip = env.unwrapped.frame_skip
        if type(self.frame_skip) is not int or not 1 <= self.frame_skip <= 16:
            raise ValueError("Invalid physical-work frame skip")
        self.decisions, self.controlled_ticks, self.reset_ticks = 0, 0, 0
        self.resets, self.terminal_short_decisions = 0, 0

    def reset(self, **kwargs):
        result = self.env.reset(**kwargs)
        ticks = self.env.unwrapped.state["tick"]
        if type(ticks) is not int or ticks < 0:
            raise RuntimeError("Invalid reset-settling tick count")
        self.reset_ticks += ticks
        self.resets += 1
        return result

    def step(self, action):
        old_tick = self.env.unwrapped.state["tick"]
        result = self.env.step(action)
        _, _, terminated, _, info = result
        ticks = info["physics_ticks"]
        if (type(ticks) is not int or not 1 <= ticks <= self.frame_skip
                or self.env.unwrapped.state["tick"] - old_tick != ticks
                or (ticks < self.frame_skip and not terminated)):
            raise RuntimeError("Invalid observed controlled physics ticks")
        self.decisions += 1
        self.controlled_ticks += ticks
        self.terminal_short_decisions += int(ticks < self.frame_skip)
        return result

    def summary(self):
        return {
            "version": "controlled-reset-ticks-v1",
            "scope": "Training environment only; excludes preflight, evaluation and runtime boot",
            "decision_steps": self.decisions, "frame_skip": self.frame_skip,
            "nominal_controlled_physics_ticks": self.decisions * self.frame_skip,
            "controlled_physics_ticks": self.controlled_ticks,
            "reset_settling_physics_ticks": self.reset_ticks, "resets": self.resets,
            "total_counted_physics_ticks": self.controlled_ticks + self.reset_ticks,
            "terminal_short_decisions": self.terminal_short_decisions,
        }
