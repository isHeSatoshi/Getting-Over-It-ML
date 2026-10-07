# Reward Function Redesign - 2026-08-05

> **Superseded by the 2026-10-03 audit.** The assumed ground height of -264.7
> was produced by missing terrain collisions, not a real spawn rock. Reward
> changes alone could not repair that backend. This file is historical;
> use `docs/RESEARCH_AUDIT.md` and `research/env.py` for the current contract.

## What was broken

The previous run (163,840 steps) produced a policy that climbed to Y=-216,
then **camped at the spawn rock** indefinitely.  Explained variance was 0.996
(the Critic learned perfectly), but the policy never explored.  Diagnosis
showed three stacked bugs all pushing the agent toward "don't move":

### Bug 1 — Camping is optimal under the old shaping

```python
# OLD (broken)
frame_reward = gamma * Y_t - Y_{t-1}
# At spawn, Y = -264.7.  Stationary => gamma*(-264.7) - (-264.7) = +2.647.
```

Standing still at spawn yielded **+2.65 reward per frame** — about
10x more than actually climbing.  The policy correctly learned that
doing nothing dominates every other strategy.  This is a textbook
mis-specified potential function.  **Fix:** shift potential to be
**zero at episode spawn**: `Phi(s) = (Y - Y_spawn) * 0.01`.
Camping now yields `0.99 * 0 - 0 = 0` reward.  No exploit.

### Bug 2 — max_progress leaked across episodes

The old `reset()` did `self.max_progress = state.get('player_world_y')`,
but the game state could carry over a previous episode's high (logs
showed `max=98.7` while the player was actually at `y=-264.7`).
The stall-timer then truncated every episode at decision ~75 because
the "high" was unreachable.
**Fix:** `episode_high_y` is reset every `reset()` call, and the
bridge state is read twice to absorb reset lag.

### Bug 3 — Setback penalty taught "don't fall => don't climb"

`setback_threshold=60.0, scale=0.05` punished any single-decision drop
> 60 units with an *extra* penalty on top of the lost potential.  In
*Getting Over It*, falling is **how you climb** — every upward swing
involves a moment of downward momentum.  The agent learned this was
toxic and stopped swinging altogether.
**Fix:** removed entirely.  Altitude loss already costs potential;
double-penalizing paralyzed the policy.

## The new reward contract

```
Step reward (per k_frames=4 decision):
    sum over k frames of:
        0.99 * Phi(s_{t+1}) - Phi(s_t)         [zero-based potential]
      - 0.01                                    [time penalty]
      + 0.002 if contact_flag                   [hammer on something]
      + 0.02  if hammer pointed at overhead ledge [hook alignment]
    + milestone_bonus                            [new-high hook]
    - 0.005 * |a_t - a_{t-1}|                    [smoothness]

Milestone bonus (per decision, only on new-high crossings):
    0.5 * (gain * 0.01 * 100) = 0.5 * gain_in_y_units*  

Termination:
    +100  on player_world_y >= 16000
    -5    if Y drops >100 in one decision (respawn detected)
    truncate  if no new episode high for 300 frames
```

## What the new incentives actually teach

1. **Stand still** — net -0.04 reward/decision (pure time cost).  Bad.
2. **Climb 50 units** — ~+25 reward.  Excellent.
3. **Fall to water** — episode ends with -5.  Bad but recoverable.
4. **Hook an overhead ledge** — steady +0.02/frame while aligned,
   AND the resulting climb gives a milestone bonus.  Double incentive.
5. **Reach a new plateau, get stuck** — 300-frame stall timer truncates
   and forces a fresh episode.  Encourages exploration.

## Trainer-side changes

| Param | Old | New | Why |
|-------|-----|-----|-----|
| `ent_coef` | 0 (default) | **0.01** | Force exploration.  The #1 reason PPO collapses onto "don't move" is entropy collapse. |
| `batch_size` | 64 | **256** | LSTMs need bigger mini-batches to average gradient noise; 64 was useless. |
| `ortho_init` | default | **True** | Orthogonal init keeps LSTM cells well-conditioned through long horizons. |
| `max_episode_steps` | 15000 | **4000** | Env-side stall truncation kicks in much sooner now; the outer TimeLimit was redundant. |
| Resume behavior | auto-load latest | requires env var | Old checkpoint was trained on broken rewards; resuming from it would lock in the camping policy.  Set `RESUME_CHECKPOINT=...` to opt in. |

## Verification

```
$ python test_reward_math.py
✅ camping 10 decisions: total reward = -0.4000   (was +26.5 in old code)
✅ climb +50 units over 5 decisions: total reward = +25.2875
✅ respawn fall: terminated=True, reward=-6.9630
✅ stall truncation at 75 decisions
✅ episode_high_y properly reset to spawn
```

All critical paths verified by hand-simulated trajectories.

## How to train

```powershell
# Fresh start (recommended given the reward rewrite)
python train_ppo.py

# Or, to specifically resume a known-good checkpoint
$env:RESUME_CHECKPOINT = "./models/recurrent_ppo_gettingoverit_XXXXX_steps.zip"
python train_ppo.py
```

Monitor TensorBoard:
```powershell
tensorboard --logdir ./ppo_tensorboard/
```

Watch `rollout/ep_rew_mean` **rise** and `rollout/ep_len_mean` **stay long**
(currently 103); both together mean the agent is making real progress,
not gaming the reward.
