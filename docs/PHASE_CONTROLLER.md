# State-matched trajectory prototype

This is a non-learning experimental controller, not a validated corrective
expert. It asks whether matching the current body/hammer/contact state to a
local part of the successful nominal trajectory works better than advancing
its controls by elapsed time.

The frozen prior is the 600-row nominal episode in the original legal
demonstration corpus. Controls and raw pre-action observations are hash-bound.
Scaling uses the unchanged RMS from the original 3576 eligible rows.

At each one-tick decision the controller searches only eight rows behind and
twelve rows ahead of its previous phase. A weighted distance uses thirteen
body, hammer and contact features from the existing raw 217-feature input.
World position and altitude receive squared-distance weight 4; other selected
features receive weight 1. Reward history, terrain, pointer targets and elapsed
time do not select the phase. It may wait or backtrack. There is no unconditional
phase advance. It outputs the actual legal control stored at the selected row.

`time_indexed` mode is a separate declared control arm. It never masquerades
as state-responsive feedback.

## First frozen physical check

The 13-feature matcher reproduces the nominal recorded controls and reaches
the same central hold as time-indexed playback. On a legal left warm-up it
stalls at phase 28 near the ordinary floor; on one fresh noise stream it
stalls at phase 106. Time-indexed playback reaches a central hold under the
warm-up and a secondary-region hold under that noise stream (its final X is
335.292, just outside the unchanged central range).

All twelve rollouts (two modes, three cases, two backends) match exactly
between reference and fast, with 7200 controlled and 1440 reset ticks, no
learning updates, summit or death. All frozen milestone fields are independently
reconstructed from captured raw position, velocity and body-contact telemetry.
The backend copies are fidelity checks,
not twelve independent robustness trials. This matcher is not admitted for
corrective data or policy learning.

The next single-axis prototype change is to add existing pointer/control-memory
features to the distance, keeping the prior, fixed RMS, phase window, actions,
weights and cases unchanged. Those inputs were omitted here and may help
distinguish similar poses during an unfinished stroke. This is a hypothesis,
not a demonstrated cause or fix. No retry or parameter sweep is part of the
closed first test.

Nearest-state proximity does **not** establish a corrective target. Physical
nominal/perturbation tests and independent reference/fast agreement must pass
before any new teacher data or learning is admitted. Failed trajectories stay
diagnostic. New labels must be actual applied controls at their exact captured
pre-action observations, not an arbitrary suffix assigned to unrelated states.

No privileged reset, modified physics, optimizer, paid reservation, deployment
or public release is part of this prototype. A bounded test declaration must
be persisted before running the game. Neither a short success nor backend
duplication counts as multi-seed saved-policy robustness or summit completion.
