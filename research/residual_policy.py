"""Zero-mean residual actor initialization and matching checkpoint contracts."""
import hashlib
import math
from pathlib import Path

from gymnasium import spaces
import numpy as np
import torch
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from research.demonstrations import require
from research.residual_controller import (ACTOR_DIMENSION, contract as scaffold_contract,
                                          validate_normalizer)
from research.residual_env import contract as adapter_contract
from research.reward import RewardConfig

VERSION = "zero-mean-residual-actor222-v1"
ARCHITECTURE = [256, 256]
LOG_STD = math.log(.01)


def contract():
    return {
        "version": VERSION, "adapter": adapter_contract(), "architecture": ARCHITECTURE.copy(),
        "actor_dimension": ACTOR_DIMENSION, "initial_mean_head": "Exact zero weight and bias",
        "initial_log_std": LOG_STD, "initial_residual_std": .01,
        "initial_final_command_std_before_clipping": .02, "use_sde": False,
        "normalizer": {"shape": [ACTOR_DIMENSION], "clip_obs": 10., "epsilon": 1e-8,
                       "norm_obs": True, "norm_reward": False, "clip_reward": "infinite",
                       "gamma": RewardConfig().gamma(1)},
        "optimizer_updates": 0,
        "limit": "Initialization and checkpoint schema only, not learned benefit or a training budget."
    }


class ZeroResidualPolicy(ActorCriticPolicy):
    """PPO-compatible class; saved state overwrites initialization on reload."""

    def __init__(self, observation_space, action_space, lr_schedule, **kwargs):
        require(isinstance(observation_space, spaces.Box)
                and observation_space.shape == (ACTOR_DIMENSION,)
                and observation_space.dtype == np.float32
                and isinstance(action_space, spaces.Box) and action_space.shape == (2,)
                and action_space.dtype == np.float32 and np.all(action_space.low == -1)
                and np.all(action_space.high == 1), "Residual actor requires222/residualBox2 spaces")
        require(kwargs.get("net_arch", ARCHITECTURE) == ARCHITECTURE
                and kwargs.get("log_std_init", LOG_STD) == LOG_STD
                and not kwargs.get("use_sde", False) and not kwargs.get("squash_output", False),
                "Changed zero-residual initialization contract")
        kwargs.update(net_arch=ARCHITECTURE.copy(), log_std_init=LOG_STD, use_sde=False)
        super().__init__(observation_space, action_space, lr_schedule, **kwargs)
        with torch.no_grad():
            self.action_net.weight.zero_()
            self.action_net.bias.zero_()


def new_normalizer(adapter):
    vector = VecNormalize(DummyVecEnv([lambda: adapter]), norm_obs=True, norm_reward=False,
                          gamma=adapter.gamma, clip_obs=10., epsilon=1e-8, clip_reward=np.inf)
    validate_normalizer(vector.obs_rms, scaffold_contract())
    return vector


def checkpoint_contract(adapter):
    directory = Path(__file__).resolve().parent
    names = ("residual_controller.py", "residual_env.py", "residual_policy.py", "stroke_controller.py")
    return {
        "schema": contract(), "prior": dict(adapter.prior_hashes),
        "source_sha256": {name: hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in names},
        "episode_memory": "Actual reset before standalone policy replay; adapter owns live raw/source/own history. "
                          "A weights-only save is not a claim of mid-episode replay or game fidelity."
    }


def validate_checkpoint(policy, vector, saved_contract, adapter):
    require(saved_contract == checkpoint_contract(adapter), "Residual saved source/prior/schema mismatch")
    validate_normalizer(vector.obs_rms, scaffold_contract())
    settings = contract()["normalizer"]
    require(vector.observation_space.shape == policy.observation_space.shape == (ACTOR_DIMENSION,)
            and vector.action_space.shape == policy.action_space.shape == (2,)
            and np.all(policy.action_space.low == -1) and np.all(policy.action_space.high == 1)
            and np.all(vector.action_space.low == -1) and np.all(vector.action_space.high == 1)
            and isinstance(policy, ZeroResidualPolicy)
            and policy.net_arch == ARCHITECTURE and not policy.use_sde
            and vector.norm_obs and not vector.norm_reward
            and vector.gamma == settings["gamma"] and vector.clip_obs == settings["clip_obs"]
            and vector.epsilon == settings["epsilon"] and vector.clip_reward == np.inf,
            "Changed residual actor or normalization settings")
