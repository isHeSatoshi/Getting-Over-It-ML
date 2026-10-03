# Deferred hypotheses

- After the current nine-run pilot: one-tick feedback versus four-tick holds.
  Match physical exposure, gamma, episode/evaluation duration, and warm-ups.
  Treat samples and optimizer steps as separate resource axes.
- Verify whether failures near X=277-280 are controller saturation, missed
  contacts, or deficient observations before modifying the action interface.
- Use the legal successful first-ledge trajectory as a skill-acquisition
  baseline. Imitation may initialize a reactive controller; open-loop replay
  alone is not learned robustness.
- Test ordinary-start skill composition before a privileged-reset curriculum.
  Never include diagnostic placements in claimed policy success.
- Correct PPO epoch-versus-minibatch update reporting in a future snapshot.
- Extend golden contact traces to learned upper-route sections before claiming
  full-game fast-backend fidelity.
- Add independent held-out final verification and a saved-policy replay package.
- Test whether current CPU Upgrade concurrency can improve useful throughput
  before spending on CPU XL. Never resize during an active batch.
