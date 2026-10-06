# Prompt for the cheaper execution agent

Copy the text below into a new execution-agent session.

---

Use the reviewed working tree in `D:\Project\cat`, including the review
fixes AFTER commit `6e5c3f9`; do not deploy that commit alone or discard
uncommitted work. Read `docs/GOAL_REVIEW.md` first. Execute **one bounded
goal-conditioned SAC/HER/legal-prefix pilot**, not the old residual-PPO
study and not the canceled94-invocation loop. Ask no decision questions.
This is execution/management, not a new design session.

Read `docs/GOAL_SAC_DESIGN.md`, the current top sections of `autoresearch.md`
and `autoresearch.ideas.md`, latest journal entries, `autoresearch.costs.json`,
and `research.goal_study.plan()`. These and actual Space variables are
authoritative. Preserve user work and unfinished residual integration.

The approved designer's clarification is
`artifacts/goal_design_handoff_20261005_v1/clarification_reply.txt`.
Do not change the algorithm/gates or widen prefix tolerances to rescue failure.

Implemented entrypoints:
- `research.goal_checks`: active/established tests (explicitly excludes12
  tests belonging to the canceled unfinished residual worker).
- `research.goal_preflight`: pipeline, legal-prefix fidelity, resources,
  benchmark.
- `research.goal_campaign`: pure reservation/context/training-approval
  helpers, no remote writes.
- `deploy.bundle`: allowlisted fresh source bundle.
- `deploy.goal_worker`: modes `goal_preflight` and `goal_study`.
- `research.goal_run`: grant-only remote seed trainer/evaluation.
- `tools.hf_research_status`: auto-discovers current session, now understands
  goal results.

Private HF Space: `isHeSatoshi/rl-over-it-poc-20261004`.
Private artifact dataset: `isHeSatoshi/rl-over-it-research-artifacts`.
Use existing authenticated CLI/API; never print credentials or publish.
Last verified state (2026-10-06): Space PAUSED, eleven reservations closed,
conservative compute estimate about$0.8340 (not a bill). Attempts3/4 both
completed full training plus learned-only evaluation and both failed the
physical gates (0/10 first-ledge, no Y180 hold); 3x data did not fix the
fixed-point collapse. The demo-seeded exploration probe v5 (contract
`legal-prefix-goal-sac-her-demo-seed-v1`) adds state-matched demonstration
bursts to training exploration only, with evaluation, cases, gates and
caps unchanged. Do not reopen old source/session deadlines, resume
interrupted work, or relaunch without explicit authorization.

1. Run active tests and both JS checks. Windows CUDA import may exhaust
   paging capacity; the isolatedCPU validation Python is
   `artifacts/goal_build_20261005_v1/cpu_testenv/Scripts/python.exe`.
   Original venv and unrelated processes must remain untouched.

2. Inspect actual private Space source, variables, runtime and paused state.
   Reverify current CPU Upgrade pricing. Use one replica/never-sleep (HF may
   report `sleep_time=None`). No GPU, XL or new paid provider.

3. Prepare one fresh immutable source bundle and `goal-...` session.
   Persist the start/deadline and explicit reservation before paid launch:
   at most$0.30 AND ten total paid hours including build/preflight/evaluation,
   within cumulative$10. Never extend the deadline. Use
   `research.goal_campaign.reserve` and `context`, pin actual uploaded
   source and dataset revisions, and verify private targets.

4. Upload only the allowlisted source and trusted historical scaffold
   (`artifacts/demonstrations_20261004T072714652488Z/manifest.json,data.npz`)
   into the NEW session's `operator/prior/` at one pinned dataset revision.
   Store `operator/goal_context.json` using the helper's context.
   Set fresh session/targets/context/deadline and `RL_MAX_HOURS=10`,
   `RL_MODE=goal_preflight` while PAUSED; intentionally restart preflight.
   Keep the same source, budget start and deadline afterward.

5. Require durable private `preflight_complete` with every declared check
   passed, matching source/plan/prior/runtime/provenance, and independently
   verify PAUSED. Do not launch on missing, failed or partial preflight.
   Prepare the NEW approval context with `approve_training`, binding the
   original preflight-context revision. Only then intentionally set
   `RL_MODE=goal_study` and restart within the SAME deadline/reservation.

6. Scale probe: seed21 only, no learned weights or discovered routes
   shared. Per seed:<=480000 learner transitions,<=1.2million total
   physics ticks including prefixes/resets/preflight/evaluation,<=237952
   SAC cycles. Evaluation is final-only learned play from ordinary spawn,
   no prefix/baseline/playback. Each seed needs nominal first-ledge hold,
   >=8/10 existing first-ledge successes, and nominal Y>=180 held90ticks
   with speed<=2. Stop the whole pilot after the first failed seed.
   A physics-reserve stop saves a final checkpoint and runs the reserved
   evaluation, but `training_summary.complete=false` makes the pilot fail
   even if `physical_gate_passed=true`. Never reinterpret partial work as
   permission to run the next seed, resume, or extend the reservation.

7. While running, do not upload code/restart/resize/change variables/secrets.
   Read only bounded JSON pinned to a single artifact commit. Inspect
   actual tick/update progress and errors, not stale logs/rewards alone.
   Distinguish `physical_gate_passed` from the admission
   `pilot_gate_passed`, and report `training_summary.stop_reason`.
   Preserve backups/checkpoint companions and verify PAUSED at completion,
   failure or deadline. Pause only this owned Space if the watchdog failed.

8. If a scheduled loop is needed, create a **temporary goal-pilot monitoring
   loop only**. Its prompt must bind this fresh session/deadline/caps, be
   read-only during active work, and cancel after completion/failure/deadline.
   Never recreate the old generic loop or automatically reserve/run another
   batch. No indefinite loop. Report the completed pilot and stop.

After completion, report per seed: actual learner/prefix/reset/evaluation
ticks, update cycles, training completeness/stop reason, nominal first-ledge
and Y180 holds, first-ledge fraction, deaths/summits, saved checkpoint and
pinned artifact revision. Close only this fresh reservation using verified
end evidence. Cancel its temporary monitoring loop and independently verify
PAUSED. No unattended progression to another batch.

Record contracts, failures, costs and actual physical results. Scaffold
holds and engineering checks are not learned progress. A pilot pass still
is not a summit: final three-seed nominal summits,>=80% completion on20new
untouched cases/seed, upper-route fidelity and saved closed-loop replay
remain required. Expand only under a separately authorized bounded batch.

If an implementation bug blocks execution, fix narrowly and retest; do not
alter the scientific gates, silently renew caps, or blindly resume.
