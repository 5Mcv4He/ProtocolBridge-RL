#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${1:?Usage: environment/reproduce.sh NEW_OUTPUT_DIRECTORY [--agent]}"
python3 -m environment.check_baseline
python3 -m environment.validate "$1/controls"
if [[ "${2:-}" == --agent ]]; then
  python3 -m environment.agent "$1/agent"
fi
