# Remote experiment protocol

**Do not run full training on the user's desktop.** The entry point refuses
`--remote-training` when Factory's desktop environment is detected. A smoke
run is CPU-only and capped at 2,048 transitions.

## Host setup and preflight

Use a separate machine with Python 3.11, Chrome/Chromium, and the game assets.
Install PyTorch appropriate to that host, then `requirements-research.txt`.
No Node physics worker or GPU is required by the current baseline.
Selenium launches an isolated browser; no existing user Chrome profile is used.

```bash
python -m pip install -r requirements-research.txt
python -m unittest discover -s tests -p 'test_*.py' -v
node tests/collision_memo.test.js
python -m research.validate --driver selenium
python -m research.reward_audit --driver selenium
python -m research.fast_fidelity --headless
python -m research.train --algorithm ppo --action absolute --smoke --steps 512 --driver selenium
```

Do not waive a failed collision, frame-acknowledgement, reset, or causal-control
check to make training start. `research.compare_runtime` additionally needs
the existing `vm_bridge` Node dependencies because it measures the legacy defect.

## First matrix

The predeclared managed pilot is now specified in `RESEARCH_CAMPAIGN.md` and
`research/campaign.py`: PPO/absolute, SAC/absolute, and SAC/velocity, each with
three training seeds and exactly 98,304 transitions. Use that nine-run
campaign first. The broader matrix below is a later proposal, not an additional
set of jobs to launch blindly alongside the pilot.

Run all six combinations of `{ppo,sac}` x `{absolute,velocity,polar}` with
training seeds 0, 1, 2 and the same transition budget. Start at 100,000
transitions per run on the remote host, inspect physical traces, and stop
expanding failing variants. This is a budget proposal, not completed evidence.

```bash
python -m research.train --algorithm sac --action absolute --remote-training --steps 100000 --seed 0 --driver selenium
```

Each run owns its browser and loopback asset server. Start with one worker
until remote profiling establishes a reason to parallelize. Do not use the
old trainer's eight-process launch or delete shared Chrome profiles.

`--backend fast` is now the training default. It accelerates the original
engine, not an approximate physics port; details and measured fidelity are in
`FAST_BACKEND.md`. Before/after policy evaluation uses a separate reference
worker. Include `--backend reference` runs when comparing execution throughput
and keep the RL/reward settings identical.

Reward semantics and exploit tests are specified in `REWARD_DESIGN.md`.
The current reward/learner/normalizer gamma is 0.9992301329658564, corresponding
to a 120-second half-life. Do not independently change the learner's gamma.
Use `--discount-half-life` to change the shared contract. Observation statistics
are normalized; reward units are not dynamically rescaled or clipped.

Algorithms are experimental baselines with library defaults unless overridden
in `research/train.py`. The environment uses four physics ticks per decision
at 30 Hz. PPO and SAC train different amounts per transition by construction;
report gradient updates and wall time as well as transitions.

## Required reporting

- Store `manifest.json`, validation, monitor, sampled physical traces,
  evaluations, model, and `normalization.pkl` together.
- Never evaluate a normalized policy on raw observations or update
  normalization statistics during evaluation.
- Save `reward_contract` and `reward_normalization` from the manifest. Do not
  clip terminal rewards or dynamically normalize the shaped reward stream.
- Report maximum **and retained** world-height gain, falls, completed climbs,
  action/tick counts, contact-query events, and time to first reach.
- Distinguish a transient jump from reaching and holding terrain. The CEM
  baseline explicitly checks a 120-tick final-pointer hold.
- Compare against idle, random-pointer, fixed sweep, and bounded exact-game
  trajectory search. A learned policy must outperform physical baselines.
- The current code automatically evaluates three fixed reset seeds. In this
  game's tested region these yield the same physical start; this is a replay
  consistency check, not three independent test environments.
- Add physically justified reset/state perturbations and standardized
  intermediate-state tasks before claiming generalization.
- Keep reward/observation/action versions and source/asset hashes immutable
  within a run. Do not resume legacy 200-dimensional recurrent checkpoints.

Evaluate trusted outputs with:

```bash
python -m research.replay --trial /absolute/path/to/trial_directory --driver selenium --decisions 3000
```

Model/normalization loading uses Python serialization; never load untrusted
checkpoint files. Evaluation is bounded and does not train.

## Progress gates and ablations

1. Verify action-sensitive transitions and actual body/hammer contact events.
2. Require reproducible improvement in retained height, not explained variance.
3. If all variants fail on the first substantial obstacle, inspect trajectories
   before increasing the step budget.
4. Compare terrain versus `--no-terrain`, absolute versus integrated actions,
   and explicit state versus short history/recurrent state in separate runs.
   First compare `--reward-profile sparse`, `height`, and `settled` with
   everything else fixed. Then compare half-lives 60/120/240 seconds. All
   profiles expose identical reward-history features to avoid confounding
   reward choice with information available to the policy.
5. If long-horizon exploration remains the bottleneck, prioritize
   goal-conditioned reach-and-hold tasks or a replayable exploration archive.
   HER/HRL/archive learning are not implemented yet.
6. Treat learned-model MPC and custom FastSim as later alternatives requiring
   contact-stratified fidelity and real-game transfer results.

The current script trains fresh models and saves periodic checkpoints and
normalization. The campaign runner now supplies bounded same-host concurrency,
reference perturbation evaluation, physical milestone metrics, and evidence
gates. It still does not implement resumable training, cross-host distributed
orchestration, or a learning curriculum. No remote campaign has run yet.
