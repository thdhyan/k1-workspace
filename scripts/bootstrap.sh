#!/usr/bin/env bash
# Clone the workspace with all library repos (git submodules under libs/).
set -euo pipefail
git submodule update --init --recursive
