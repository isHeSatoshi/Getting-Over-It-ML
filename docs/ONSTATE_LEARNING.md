# Logged-success data comparison

The player occasionally holds the first ledge but does not do so reliably.
This comparison tests a learning change, not another physics or portability
diagnostic: add the controls actually applied at states in one successful
learner trajectory.

## Frozen comparison

`research/onstate_study.py` declares three fresh seeds (9, 10, 11) and two
actor-only behavior-cloning arms:

| Arm | Original examples per batch | Logged-success examples |
| --- | ---: | ---: |
| Original demonstrations | 256 | 0 |
| Original plus logged success | 192 | 64 |

Both use 2000 updates, 512000 sample presentations, the same initial policy
per seed, the same `[256, 256]` architecture and the original frozen RMS.
Value parameters, action log-standard-deviation and the PPO optimizer remain
unchanged. There is no PPO training. Equal update and presentation counts are
not equal FLOPs or wall time.

Nine fresh reference cases, including nominal play, new legal warm-ups and
noise seeds 10100..10105, are declared before training. The first-skill gate
remains nominal central retention in every seed and at least 8/9 central
holds per seed. A first-ledge result is not summit completion. Final full-climb
verification still needs independent held-out cases, upper-route fidelity and
saved-policy replay.

## Data admission

`research/onstate_data.py` binds the original eligible corpus, captured raw
replay and successful feedback trace to reviewed SHA-256 identities. It checks
the exact pre-action inputs, actually applied controls, global noise clock,
original physical tick order and frozen held-event contract.

The derived corpus retains 3576 original rows and all 1800 logged-success
rows. Source IDs and row indices prevent accidental time shifts or duplication
of the reference/fast copies. The loader checks ZIP membership, decoded sizes,
NPY shape/dtype headers before allocation, array hashes and exact normalization.
It never loads object arrays or unverified pickle files.

Some normalized inputs are clipped. Raw inputs come from the previous validated
legal replay, not inverse normalization. The existing shared-input action
ambiguity remains visible; labels are not averaged, replaced or silently removed.
The additional trajectory is post-hoc selected noise8105 development/training
data, not an off-state corrective expert or independent validation. Nearest
demonstration actions and successful time-index suffixes are never relabeling
oracles.

## Execution boundary

Data derivation does not run the game or learn. `warm_start` supports the new
source-balanced data path only as a bounded smoke, at most 8 updates of at most
64 samples, and requires the exact original frozen RMS. Full on-state training
is intentionally refused, even with an old imitation permit.

This proposal does not reserve money or launch a Space. Before full execution,
implement separate data/contract/source-bound Linux admission, a fresh
session and immutable deadline, remote preflight, durable claims/backups and
automatic pause. The declared envelope is CPU Upgrade, one replica, at most
2 hours including startup and at most $0.06, inside the cumulative $10 ceiling.
Never restart or reuse a closed imitation or diagnostic session.
