#!/usr/bin/env bash
# Editable-install the python libraries in dependency order into the active venv.
set -euo pipefail
cd "$(dirname "$0")/.."
for r in k1-common k1-utils k1-runtime k1-rl-mj k1-rl-isaac k1-mimic k1-teleop k1-vla; do
  uv pip install -e "libs/$r" --no-deps
done
