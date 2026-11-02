#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0

exec python3 "${SCRIPT_DIR}/scripts/autoresearch_bench.py" "$@"
