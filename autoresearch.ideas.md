# Deferred hypotheses

- After the current nine-run pilot: one-tick feedback versus four-tick holds.
  Match physical exposure, gamma, episode/evaluation duration, and warm-ups.
  Treat samples and optimizer steps as separate resource axes.
  A tested non-executing plan now exists in `research.timing_study`, including
  physical-time GAE, noise cadence, new seeds, equal planned optimizer calls,
  larger one-tick minibatches and explicit actual-exposure/compute caveats.
  Trainer/evaluator support and calibration remain required before activation.
- Retain v1's narrow central-landing target, but calibrate and predeclare a
  separate actual-platform-support metric for the next study. Four-tick phases
  1/2 of the known legal trajectory already hold the platform at X about 290;
  rejecting those as "no climbing" would misdiagnose timing capability.
  Physical placement calibration now passes at six sampled X positions
  285..345 and rejects outside low ground and too-short hold controls, with
  exact fast/reference parity. This is detector evidence, never policy success.
- Replacement PPO seed-2 noise_5 has genuine edge support under exact recorded
  remote actions, but local model inference diverges after a ~6e-8 action change
  at decision 2. Isolate fixed-input network/normalizer differences and test
  tiny-perturbation robustness. Exact physics parity does not imply a portable
  learned trajectory.
- Causal refinement: changing decision-7 X by ~0.000252 pixel, or all first
  seven local targets by <=0.00253 pixel, still holds under the recorded suffix.
  Closed-loop target drift exceeds 1 pixel by decision 16. Investigate later
  feedback/observation amplification rather than blaming the first tiny
  physics perturbation.
- Fixed-input fixture now exists locally: singleton calls and tested thread
  counts reproduce stored local actions exactly; batching differs <7e-7.
  Compare the same hashed normalized inputs on a later paused Linux host.
  Do not assume batching explains the current singleton evaluator divergence.
- Verify whether failures near X=277-280 are controller saturation, missed
  contacts, or deficient observations before modifying the action interface.
- Use the legal successful first-ledge trajectory as a skill-acquisition
  baseline. Imitation may initialize a reactive controller; open-loop replay
  alone is not learned robustness.
- SAC/absolute seeds 0/1/2 all complete mean-policy evaluation with the hammer
  above the player, no hammer terrain contact, and no meaningful movement
  from spawn despite substantial optimizer work. Cohort is validated and fails
  the frozen gate; do not scale this configuration. Await velocity controls and
  investigate safe/stalled behavior, exploration and
  reward/entropy scale rather than blindly increasing sample count. Preserve
  the raw task contract and isolate any proposed change in a new experiment.
- Test ordinary-start skill composition before a privileged-reset curriculum.
  Never include diagnostic placements in claimed policy success.
- Completed and deployed in the fresh v2 recovery: named optimizer-step
  accounting with weight/checkpoint compatibility and bounded integrations.
  Historical v1 fields retain old units; never pool its incomplete matrix into
  the new source-pinned pilot.
- Extend golden contact traces to learned upper-route sections before claiming
  full-game fast-backend fidelity.
- Add independent held-out final verification and a saved-policy replay package.
- Test whether current CPU Upgrade concurrency can improve useful throughput
  before spending on CPU XL. Never resize during an active batch.
- Completed locally for the next paused snapshot: bounded initial/final artifact
  flush, with pause guaranteed after upload failure or timeout. Do not deploy
  during v2. Confirm durable final evidence despite bounded shutdown.
