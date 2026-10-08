#!/usr/bin/env bash
# Baselines + one-factor-at-a-time ablations, equal budget per config-seed, fixed seeds.
# Serialized on purpose: 4 cores / ~7 GB, and each run starts 4 Chrome workers (~1 GB each).
set -u
cd /home/factory-user/repos/Getting-Over-It-ML
export PYTHONPATH=/home/factory-user/repos/Getting-Over-It-ML
export RL_CHROME_NO_SANDBOX=1
source .venv/bin/activate
SEEDS="5100 5200 5300"
{
  echo "=== baselines (240s x 4 islands) ==="
  python explore/experiments.py run --suite baselines --seeds $SEEDS --secs 240 --workers 4
  echo "=== last_leg (150s x 4 islands) ==="
  python explore/experiments.py run --suite last_leg --seeds $SEEDS --secs 150 --workers 4
  echo "=== staged_goals (240s x 4 islands) ==="
  python explore/experiments.py run --suite staged_goals --seeds $SEEDS --secs 240 --workers 4
  echo "=== mid_leg (300s x 4 islands) ==="
  python explore/experiments.py run --suite mid_leg --seeds $SEEDS --secs 300 --workers 4
  echo "=== table ==="
  python explore/experiments.py table
  echo "=== DONE ==="
} 2>&1
