#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python="${PYTHON:-python3}"
if [[ $# -ne 1 || "$1" != /* ]]; then
  echo "Usage: bash autoresearch.sh /absolute/validated_campaign_snapshot" >&2
  exit 2
fi
cd "$root"
"$python" -c "import ast; from pathlib import Path; ast.parse(Path('tools/research_goal_metrics.py').read_text())"
"$python" -m tools.research_goal_metrics --directory "$1"
