---
title: RL-Over-It private research worker
sdk: docker
app_port: 7860
startup_duration_timeout: 1h
---

# RL-Over-It research worker

Private, budget-bounded research using the original Griffpatch Scratch game.
There is no claim of learned game completion. The read-only status page shows
preflight and campaign progress; it offers no arbitrary execution endpoint.

The downloaded game is attributed to Griffpatch:
https://scratch.mit.edu/projects/389464290/
The packaged Scratch/TurboWarp runtime and game assets retain their respective
attribution and terms. This private research deployment is not a public
redistribution or declaration of an overall project license.

Hardware: CPU Upgrade only. Artifacts are backed up to a separate private Hub
dataset. The worker pauses on completion, preflight failure, interruption, or
budget timeout. Changing `RL_MODE` intentionally restarts the worker.
