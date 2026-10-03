#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$root"
"${PYTHON:-python3}" -m unittest discover -s tests -p 'test_*.py' -v
node tests/collision_memo.test.js
