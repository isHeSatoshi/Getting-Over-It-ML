# Managed research campaign and resource budget

Prepared 2026-10-03. The controlled pilot is now executing on the private
Hugging Face CPU Upgrade worker. See `docs/HF_DEPLOYMENT.md` for live deployment
evidence and `autoresearch.md` for the subsequently delegated autonomous
research scope. Historical pre-deployment resource measurements remain below.

## The next question, not a promised solution

Can a learned controller land on and retain the first raised platform, instead
of merely jumping high or traversing low terrain? The platform is near X=320.
Asset sampling places its top at about Y=65, and the real Player settles at
body Y=104.

`first_ledge_v1` requires:

- Body X in `[305,335]`, Y in `[100,112]`.
- Three continuous seconds in this region at at most 2 units/tick body speed.
- Actual **body** collision-query hits on at least 80% of those ticks.

Hammer support over the original ground, a high-water mark, a fast fly-through,
and the earlier 34-unit retained-height trajectory do not pass. This is an
evaluation metric only; there is no new milestone payment or privileged
training reset. A genuine full-climb completion supersedes an intermediate
ledge hold.

## Baseline evidence and an important timing result

The detector passes an explicitly labelled placement/calibration test on the
reference game. Calibration is **not policy success**.

Idle, constant downward target, fixed clockwise sweep, and random-pointer
baselines did not pass the first-ledge hold test.

A bounded 24-candidate exact-game search found a legal mouse trajectory that
lands at approximately `(322.59,104)` and holds the ledge on the reference
game. It controls the mouse **every tick**.

Resampling that trajectory to the RL interface's four-tick held actions fails.
A further 24-candidate search under four-tick actions reached the goal region
but did not achieve the hold. This does **not** prove four-tick control is
incapable; it does identify action timing/feedback as a concrete research risk.
The current pilot keeps four-tick timing fixed to isolate algorithm/action
parameterization. If all variants fail, a predeclared next investigation is
one-tick versus four-tick control, reporting both physical ticks and gradient
updates. Do not secretly change timing inside a reported run.

Evidence:

- Per-tick success: `artifacts/milestone_baselines_20261003T182302603105Z/report.json`
- Four-tick failure: `artifacts/milestone_baselines_20261003T182521058233Z/report.json`

This is first-obstacle feasibility, not a high-probability full-game solution
and not a learned reactive skill.

### Subsequent matched-timing diagnostic

`python -m research.timing_probe --source-report /absolute/trusted/report.json`
replays the known successful trajectory and all four coarse sampling phases,
600 ticks each, on both fast and uncached reference backends. The measured
fast/reference telemetry error is zero in all five cases.

The per-tick replay holds v1 at `(322.59,104)`. Coarse phases 1/2 also physically
hold the raised platform at approximately `(289.50,104)` / `(289.92,104)`, with
83 units retained and body contact on every final-four-second tick, but v1's
narrow X region rejects them. Coarse phases 0/3 do not retain this platform.
This supports sampling sensitivity, not four-tick impossibility.

The pilot's frozen v1 contract and promotion gates remain unchanged. A labelled
post-hoc secondary diagnostic uses X `[285,345]` with the original Y, speed,
three-second hold, and body-contact conditions. It distinguishes actual
edge-supported platform landings from central-target precision. It must not be
retroactively presented as a predeclared pilot result or a trained policy.
Future experiments should predeclare both measures after physical calibration.

Evidence: `artifacts/timing_probe_20261003T211346899540Z/report.json` and
`artifacts/timing_support_review_20261003T211614229092Z/report.json`.

## Pilot: nine controlled remote runs

Three variants, each with training seeds 0, 1, 2:

1. PPO + absolute targets.
2. SAC + absolute targets, isolating the algorithm change.
3. SAC + integrated velocity, testing the control parameterization.

Each receives **98,304 transitions**, a common PPO-rollout multiple that
avoids unequal SB3 rounding of a nominal 100,000-step request.

Keep original-game fast execution, four-tick repeat, terrain observations,
`climb-v2` settled reward, 120-second discount half-life, and CPU learner
settings fixed. Record actual transitions, gradient updates, dependency
versions, and learning wall time. Different algorithms intrinsically perform
different update counts; equal samples alone are not equal compute.

The live pilot's `gradient_updates` field is SB3's `_n_updates`, which counts
PPO epochs rather than minibatch optimizer calls. Future local source replaces
the ambiguous field with versioned `optimizer_work`: named completed policy,
actor, critic, and entropy-temperature optimizer calls, plus the separately
labelled internal SB3 counter. Hooks do not change tested policy weights or
checkpoint loading. Do not reinterpret existing pilot counts under new units,
and do not equate optimizer-call totals with FLOPs or wall time.

Reference evaluation runs nine declared cases for at most 60 game seconds:

- Nominal controller start.
- Left/right hammer warm-up through legal actions, not coordinate injection.
- Six independent seeded streams of small normalized-action noise.

All noise is recorded alongside predicted/applied actions. Warm-ups use the
same normalized command definition, not identical physical perturbations
across different action parameterizations. These are structured robustness
cases, **not IID physical worlds**. Do not derive a binomial confidence interval
from their success fraction. Independent training seeds measure learning
variation; cosmetic game seeds do not create independent physical levels.

## Evidence-gated expansion

Pilot aggregation rejects missing/duplicate cases, changed benchmark/reward/
observation settings, mixed code/game/dependency versions, smoke runs, unequal
transition budgets, non-reference evaluation, and early evaluation exit without
a real terminal outcome.

### Follow-up gate

Require all three training seeds of a variant to achieve:

- At least 80% success on the nine reference cases (in practice at least 8/9).
- At least 0.2 improvement in success fraction over its untrained baseline.

Rank passing variants by worst-seed success, then full completions, fewer falls,
and retained height. These are predeclared selection rules, not statistical
proof that an algorithm is globally best.

A passing pilot may prepare a **controlled follow-up**, not unrestricted scale:
the selected variant, three seeds, 499,712 transitions each, and longer
400-game-second reference evaluations. This tests broader/full-climb progress.

### Large-scale gate

First-ledge success alone cannot authorize scaling. Require actual reference
full-climb completion in the nominal case and at least 50% of declared cases
for every training seed, along with the progress/improvement gates.

Only then may the tool prepare a five-new-seed replication campaign with
999,424 transitions per run. Its execution revalidates the original promotion
evidence and current source/assets. “Scale” prepares a plan; it does not rent
resources or start jobs by itself. The user subsequently authorized autonomous
CPU Upgrade research and CPU XL after this pilot when evidence justifies it.
This does not waive these scientific gates or the persisted batch budgets.
A failed pilot may motivate a separately declared diagnostic experiment, not
an unearned promotion.

These gates are conservative operational decisions, not a numerical claim
that the probability of solving every variant of the game is known.

## Your local hardware, measured

The machine reports:

| Resource | Specification |
|---|---|
| CPU | Intel Core i7-12700K, 12 physical cores / 20 logical processors |
| RAM | One 32 GiB module, configured at 6000 MT/s; OS-visible total about 31.8 GiB |
| GPU | NVIDIA RTX 4060 Ti, 16 GiB VRAM |
| Project drive | About 116 GiB free at inspection |
| Available RAM | About 11.7–12.3 GiB during inspection, varies with other apps |

This is ample for bounded diagnostics. The user's prohibition on full local
training remains in force regardless of hardware capacity.

`python -m research.resources` measures only this Python process and its child
workers, not unrelated applications or process command lines. A 256-decision
fast-worker probe, with PyTorch imported and one learner thread configured:

| Phase | Peak summed RSS | Peak private commit | CPU |
|---|---:|---:|---|
| One worker + terrain, startup | 2.81 GiB | 3.50 GiB | Startup peak ~4.59 core equivalents |
| Steady environment stepping | 2.81 GiB | 3.51 GiB | Median ~1.06, peak ~1.16 core equivalents |
| Worker plus separate reference evaluator | 5.18 GiB | 5.71 GiB | Startup/evaluation peak ~5.06 core equivalents |

The probe does **not** measure sustained optimizer updates. Summed RSS can
double-count shared pages. Private commit is Windows-specific and is not
equivalent to physically resident RAM. Peak thread counts around 286–558
include mostly idle browser/library threads, not that many active CPU cores.
First-sample/new-process CPU accounting can miss short startup bursts.

The measured loop ran about 151 decisions/second, without optimizer updates.
That is not a promised full-training throughput.

GPU readings are whole-device totals shared with other applications. The
sample moved from about 4,062 MiB to 3,984 MiB used; that is **not** an estimate
of negative worker VRAM consumption. Exclusive per-worker VRAM was not
established under Windows/WDDM. The current small MLP learner uses CPU;
a large ML GPU is not intrinsically required. Remote Chrome may use hardware
WebGL or software rendering, so fidelity and capacity must be remeasured there.

Resource evidence:
`artifacts/resources_20261003T181741151184Z/report.json`.

### Planning reservations, not claimed measurements

- Reserve **4 logical CPUs and 8 GiB RAM per active run**.
- Reserve **4 GiB RAM for the host**.
- Start with one run; allow at most two after profiling the remote host.
- A practical initial remote host is **8 vCPU / 32 GiB RAM**.
- Nine experiments are a queue, **not nine simultaneous browsers**.
- The runner checks available RAM and logical CPU counts before starting.
- SAC's 200,000-entry replay buffer needs about **335 MiB** for 217-element
  observations; the old million-entry setting needs about **1.64 GiB**.
- Budget roughly **20 GiB of free disk** for pilot artifacts/checkpoints and
  safety margin. The runner checks this. SAC replay is saved once at run end,
  not copied into every periodic checkpoint. Actual disk use still depends
  on artifact volume.

CPU allocations are reservations, not enforced processor affinity. No remote
provider cost, wall-time estimate for full jobs, or multiworker scaling is
claimed from the local probe.

## Operate on a separate host

Prepare the campaign **on the target host** so platform/software and code
provenance reflect its actual environment:

```bash
python -m research.campaign prepare --directory /absolute/new/campaign_directory
python -m research.campaign execute --directory /absolute/new/campaign_directory --max-workers 1
python -m research.campaign summarize --directory /absolute/new/campaign_directory
```

Execution refuses this desktop, runs uncached-versus-fast fidelity preflight,
then starts bounded jobs with dedicated output directories and logs. It never
overwrites existing runs. It stops scheduling new jobs after a run failure;
already-running owned jobs finish and preserve their outputs.

After sufficient evidence:

```bash
python -m research.campaign followup --directory /absolute/pilot_directory
python -m research.campaign scale --directory /absolute/followup_directory
```

Both preparation operations refuse unmet gates. Existing output is never
deleted. Current training is fresh-start, not resumable; a partially completed
campaign cannot silently resume or overwrite earlier runs.

Local-safe preparation and inspection:

```powershell
python -m research.campaign prepare
python -m research.resources --decisions 256
python -m research.milestone_baselines --search --frame-skip 4
```

The prepared local pilot is
`artifacts/campaign_20261003T183533863535Z/`. At preparation time no real results
existed; its aggregation correctly reported all nine runs missing and no scale
permission. The live remote campaign is a separate source-pinned instance.
Older prepared plans predate protocol changes and are deliberately refused.

Final validation passed 50 Python tests and the JS collision-memo tests.
A 128-transition CPU smoke run exercised all nine evaluation cases, actual
transition accounting, and new milestone metrics without demonstrating a
learned ledge hold. Closed-loop fast/reference parity still passes after the
metric additions. These checks validate orchestration and measurements, not
the effectiveness of the proposed learner configurations.

## What remains blocked or unproven

Remote hosting and private deployment are now established. CPU Upgrade is
running within its persisted budget. No learned first-ledge skill or full-climb
success has been demonstrated. If the pilot fails, diagnose control timing,
exploration, and feedback using the successful per-tick trajectory before
increasing compute. Public redistribution rights remain unresolved.
