# Private Hugging Face PoC deployment

Space: `isHeSatoshi/rl-over-it-poc-20261004` (private, Docker, CPU Upgrade).
Artifacts: `isHeSatoshi/rl-over-it-research-artifacts` (private dataset).
Session prefix: `poc-20261004-v1`.

The authenticated HF CLI was used to create repos, configure variables/secrets,
upload the allowlisted source bundle, and inspect build/runtime logs. Tokens
are never embedded in the bundle or printed; the runtime secret is excluded
from browser and training child environments.

## Budget and execution

- CPU Upgrade only, quoted/confirmed at $0.03/hour.
- One sequential research run at a time, no replicas or hardware upgrades.
- 16-hour persisted campaign wall-clock cap, approximately $0.48 compute
  at the quoted tier, with small startup/shutdown overhead possible.
- Automatic pause after preflight, failure, campaign completion, or timeout.
- Read-only private status endpoint, no arbitrary remote execution API.
- Periodic/final artifacts go to the private dataset, not just ephemeral disk.
- Mid-job restarts stop and preserve evidence rather than silently replaying
  or overwriting experiments.
- Full local training remains disabled.

Credits/payment eligibility was established by successful CPU Upgrade
provisioning, not by reading the user's credit balance. No CPU XL or GPU tier
was requested. Build time is not billed according to HF documentation.

## Remote preflight evidence

Initial startup hit app-directory ownership permissions; it was paused and
fixed before any training. The repaired container then passed:

- Python/unit and JS collision-cache tests.
- 17 golden-trace/environment fidelity cases, maximum error **0**.
- Headless/software-renderer benchmark.
- Owned-process resource probe.

Remote environment throughput with terrain was about **242 decisions/second**,
without optimizer updates. One fast worker peaked near **3.18 GiB summed RSS**;
worker plus reference evaluation peaked near **6.08 GiB summed RSS**.
The CPU-only deployment works without an ML GPU.

The host appears much larger through ordinary psutil metrics; resource guards
use cgroup CPU/memory limits and affinity rather than pretending the Space
owns those host resources.

Artifacts:

- `poc-20261004-v1/fast_fidelity_20261003T202113487642Z/report.json`
- `poc-20261004-v1/benchmark_20261003T202232534904Z/report.json`
- `poc-20261004-v1/resources_20261003T202244793737Z/report.json`
- `poc-20261004-v1/control/status.json`

These are infrastructure results, not learned climbing results.

## Current pilot launch

After successful preflight, the quota-aware image was deployed and `RL_MODE`
was intentionally set to `pilot`. The live container reports effective limits
of **8 CPU equivalents and 32,000,000,000 bytes RAM** via cgroup v2.
The persisted original budget deadline remains
**2026-10-04 12:21:08 UTC**, rather than resetting on this restart.

The managed queue contains nine runs: PPO/absolute, SAC/absolute, SAC/velocity,
each with seeds 0/1/2 and 98,304 transitions. Concurrency is one. The campaign
runs another fidelity preflight on the target image before the first learner.
Running status does not imply a trained competent policy; physical evaluations
and the eventual aggregation determine that.

### Preliminary checkpoint evidence

A bounded, evaluation-only local check of the trusted 20,000-transition
PPO/absolute seed-0 checkpoint used its matching frozen observation normalizer
and the original reference renderer. Across the nine standard cases, each
capped at 64 decisions, none held `first_ledge_v1`. The nominal case moved to
approximately `(109.28, 79.70)`, retaining 58.70 height units above spawn.
Some perturbations produced no useful movement. This demonstrates real
control, not robust learned climbing or a completed campaign result.

Evidence: `artifacts/checkpoint_reference_eval_20261003T203732890911Z/evaluation.json`.
The policy pose was captured separately **before** automatic episode reset:
`artifacts/checkpoint_visual_20261003T203855308937Z/decision_64.png`.
The earlier evaluation directory's `last.png` depicts a reset, not that pose.

The completed seed-0 PPO run subsequently passed campaign contract validation:
98,304 transitions, with all nine final reference cases run for 450 decisions.
It held the first ledge in **0/9** cases and completed the game in **0/9**.
Median retained gain was 24 units, versus 0 before training. No case died within
this evaluation horizon. These movement gains do not satisfy promotion gates.
The other eight runs were still missing at this inspection.
Evidence: `artifacts/remote_pilot_review_20261003T204729761166Z/partial_summary.json`.
The recorded `gradient_updates` field is SB3's internal `_n_updates` counter;
for PPO it counts epochs, not individual minibatch optimizer steps.

The running image's stable-file backup filter can skip continuously appended
telemetry/log files. A local, tested patch snapshots only complete text lines
up to the file size at snapshot start, while retaining stability checks for
binary checkpoints. It is **not deployed to the active campaign**, to avoid
interrupting training. Completed-file final backups are still supported by
the existing image. A stale uploaded log is not proof that training stalled.

## CLI operations

### Interrupted first batch and fresh replacement

The provider's configured one-hour idle sleep stopped the first batch during
SAC/absolute seed 0. Background optimizer activity did not prevent idle sleep.
The operator verified SLEEPING, then PAUSED the owned Space. Three full PPO
runs remain durable, with v1 ledge holds 0/9, 0/9, 1/9 and no game completions.
The partial SAC run has a 20k checkpoint and telemetry to 21,500 transitions,
but no final evaluation or saved replay buffer; it cannot silently resume.

Incident evidence:
`artifacts/provider_sleep_incident_20261003T213845836829Z/incident.json`.
The local cost ledger conservatively closes the interrupted batch at about
$0.039 compute, not an actual bill.

A separately labelled fresh replacement is reserved as `poc-20261004-v2`.
It reruns the full controlled matrix under one new source snapshot rather than
mixing old completed models with changed measurement code. Scientific training
settings are unchanged; the replacement includes tested append-only backups,
precise optimizer-call accounting, and startup admission checks requiring
provider sleep time `-1`, CPU Upgrade, and one requested replica.
Its absolute deadline remains **2026-10-04 12:21:08 UTC**. The new reservation
does not extend that deadline or reset the original paid-compute bound.
Deploy only after pause; require a successful fresh remote preflight before
switching it to pilot.

```powershell
hf spaces info isHeSatoshi/rl-over-it-poc-20261004 --expand runtime --json
hf spaces logs isHeSatoshi/rl-over-it-poc-20261004 --tail 50
hf spaces pause isHeSatoshi/rl-over-it-poc-20261004
hf download isHeSatoshi/rl-over-it-research-artifacts poc-20261004-v1/control/status.json --repo-type dataset
```

Preflight automatically pauses. After inspection, setting `RL_MODE=pilot`
and restarting begins the bounded nine-run campaign only if a durable
`preflight_complete` state exists. A fresh-source campaign still runs its own
fidelity preflight before training.

```powershell
hf spaces variables add isHeSatoshi/rl-over-it-poc-20261004 -e RL_MODE=pilot
hf spaces restart isHeSatoshi/rl-over-it-poc-20261004
```

For unattended paid batches, configure provider sleep time to `-1` while
paused and verify it before startup. Background jobs alone do not keep a Space
awake. Never-sleep is paired with the persisted application watchdog,
explicit absolute deadline, durable backup, operator checks and automatic pause,
not an unbounded paid status server.

Changing mode is an intentional remote action, not a public button. Do not
restart blindly after a mid-job failure; inspect artifacts and missing runs.
No checkpoint-resume protocol is implemented yet.

## Container security boundary

Runs as UID 1000 with owned writable app files. Chromium uses software ANGLE
and a container-specific no-sandbox option, because ordinary Chrome sandboxing
is not available in this hosted container. This is a private, single-purpose
worker and does not navigate untrusted sites or expose Chrome debugging ports.
The option is not enabled for ordinary local diagnostics.

Game assets retain Griffpatch attribution and are uploaded only to the private
research Space. A public release still requires resolving licensing and
redistribution rights.
