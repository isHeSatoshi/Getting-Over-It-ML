# Deferred hypotheses

- After the current nine-run pilot: one-tick feedback versus four-tick holds.
  Match physical exposure, gamma, episode/evaluation duration, and warm-ups.
  Treat samples and optimizer steps as separate resource axes.
- Retain v1's narrow central-landing target, but calibrate and predeclare a
  separate actual-platform-support metric for the next study. Four-tick phases
  1/2 of the known legal trajectory already hold the platform at X about 290;
  rejecting those as "no climbing" would misdiagnose timing capability.
- Verify whether failures near X=277-280 are controller saturation, missed
  contacts, or deficient observations before modifying the action interface.
- Use the legal successful first-ledge trajectory as a skill-acquisition
  baseline. Imitation may initialize a reactive controller; open-loop replay
  alone is not learned robustness.
- Test ordinary-start skill composition before a privileged-reset curriculum.
  Never include diagnostic placements in claimed policy success.
- Completed locally: named optimizer-step accounting with weight/checkpoint
  compatibility and bounded PPO/SAC integration checks. Deploy only after the
  current pilot, as a new source snapshot; old pilot fields retain old units.
- Extend golden contact traces to learned upper-route sections before claiming
  full-game fast-backend fidelity.
- Add independent held-out final verification and a saved-policy replay package.
- Test whether current CPU Upgrade concurrency can improve useful throughput
  before spending on CPU XL. Never resize during an active batch.
