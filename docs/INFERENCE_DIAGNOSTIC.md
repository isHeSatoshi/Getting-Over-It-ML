# Matched-input inference diagnostic

This path investigates numeric portability only. It cannot train a controller,
dispatch a browser/environment, or promote recorded trajectory replay as skill.

`tools.matched_host_inference` accepts exactly the declared 1,800-row raw and
normalized float32 fixture and the owned saved clone7/model RMS hashes.
It checks ZIP member sizes and NPY headers before allocating arrays, never
loads object arrays, and predicts twice with CPU, one thread and singleton
batches. It preserves parameters, timestep count, RMS and input files.
Completed inference presentations are flushed to an append-only JSONL file.

Local pipeline validation requires `--local-diagnostic`, absolute input/output
paths and a fresh output directory. It is bounded at 120 seconds and claims no
remote admission. Do not put substantive local training in this path.

Remote `RL_MODE=inference_probe` requires a fresh `inference-*` session on the
owned private Space/dataset. The pinned JSON context is
`<session>/operator/inference_context.json`, containing:

- `ticket`, version `matched-host-inference-admission-v1`, with the exact
  `contract_sha256`, targets, source SHA, start/deadline, verified paused
  admission and one never-sleep CPU Upgrade replica policy.
- `ledger`, with a unique `reserved_inference` batch, all other batches closed,
  at most 1,200 seconds including startup and at most $0.01 reserved under the
  $10 cumulative ceiling.
- `provenance`, matching the deployed source/game fingerprint.
- `inputs`, one metadata/hash-bound entry per exact frozen file. The fixture
  belongs to this fresh session; model/RMS remain pinned to the recorded
  immutable clone7 dataset revision.

The worker backs up admission and a no-resume claim before its single child.
The child requires the exact direct-parent PID/creation time, claimed output
paths, grant hash and worker deadline, with the recorded Linux dependencies.
It has no parent credential variables. Execution stops at 120 seconds,
progress backups run every 20 seconds, and final flush always yields to pause.
Repeated, interrupted, failed and completed sessions never restart inference.

The read-only monitor reports inference comparisons separately from campaign
holds/summits. A numeric mismatch is a diagnostic result, not authorization to
tune batches, change the frozen policy, relax evaluation or scale training.
Any deployment needs a new verified source/context/reservation; this document
does not authorize restarting a completed learning batch.
