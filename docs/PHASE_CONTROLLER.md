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
The default `feature_set="kinematic"` retains that first frozen matcher.
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

The subsequent single-axis prototype change adds existing pointer/control-memory
features to the distance, keeping the prior, fixed RMS, phase window, actions,
weights and cases unchanged. Those inputs were omitted here and may help
distinguish similar poses during an unfinished stroke. This is a hypothesis,
not a demonstrated cause or fix. No retry or parameter sweep is part of the
closed first test.

## Second frozen physical check: pointer/control-history feedback

Opt-in `feature_set="control_history"` adds eight existing inputs:
pointer_x/y, last_tx/ty, control_memory_x/y, last_hammer_distance and last_effort.
It leaves the prior, RMS, weights, phase window, actions and three cases fixed.
Only version and feature list differ in the scientific contract. Both variants
still reproduce every one of the 600 actual recorded-input controls exactly.

The original 13-feature variant's six full backend traces exactly reproduce
the pinned first check. The new 21-feature variant still holds nominally.
After the left warm-up it now ends at `(280.249, 79.011)`, retained gain 58.011,
instead of gain 0.996 near the floor. It stalls at phase 280, with no central
or secondary hold. The noisy case ends at `(33.936, 19)`, retained gain -2,
and stalls at phase 135. Both new final 120-tick phase ranges are constant.
This selected partial-height improvement is not recovery or learned skill.

Fourteen bounded rollouts use 8400 control and 1680 reset ticks, no updates,
summits or deaths. The nominal time-indexed reference/fast gate passes first.
All seven full backend trace pairs agree exactly; all fourteen milestone
traces independently reconstruct from raw position, velocity and contact.
Final warm-up contact and zero speed confirm stationary support below the
ledge, not ledge acquisition. No detector changes or teacher/data admission.
Evidence: `artifacts/phase_history_probe_20261004T200234917165Z/verification.json`.

Reject further nearest-feature/window sweeps. Next inspect the original
pointer-to-hammer servo and stalled strokes, then freeze a legal stroke-progress
controller with observable completion gates and bounded state-error action
correction. Physical recovery and fidelity must precede labels or learning.
The structural design remains a hypothesis, not an established fix.

Nearest-state proximity does **not** establish a corrective target. Physical
nominal/perturbation tests and independent reference/fast agreement must pass
before any new teacher data or learning is admitted. Failed trajectories stay
diagnostic. New labels must be actual applied controls at their exact captured
pre-action observations, not an arbitrary suffix assigned to unrelated states.

No privileged reset, modified physics, optimizer, paid reservation, deployment
or public release is part of this prototype. A bounded test declaration must
be persisted before running the game. Neither a short success nor backend
duplication counts as multi-seed saved-policy robustness or summit completion.
