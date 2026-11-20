#!/usr/bin/env bash
# Deploy K1 walk-base code + latest trained policy to one or more robots.
#
# Usage:
#   ./scripts/deploy_to_robots.sh boosterk1.a1 boosterk1.a2
#   ./scripts/deploy_to_robots.sh 192.168.50.82 192.168.50.215
#
# Copies:
#   libs/k1-deploy-robot/deploy/k1_gamepad_deploy.py        (robot runner)
#   libs/k1-runtime/src/k1_runtime/{gamepad_core,wbc}.py    (shared runtime)
#   ~/k1_models/mjlab_k1/walk_still_v2/model_8998.pt        (latest trained policy)
#
# to ~/k1_mjlab_deploy/{deploy,deploy/k1_runtime} on each robot and confirms no
# old k1_gamepad_deploy is still running (only one joint-command sender per robot).
set -euo pipefail

ROOT="${ROOT:-$HOME/Projects/booster_proj}"
L="$ROOT/libs"
SSH_CFG="${SSH_CFG:-$HOME/.ssh/config.good-20261027}"
KSSH="ssh -F $SSH_CFG"
KSCP="scp -F $SSH_CFG"
POLICY_SRC="${POLICY_SRC:-$HOME/k1_models/mjlab_k1/walk_still_v2/model_8998.pt}"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <robot-alias-or-ip> [<robot-alias-or-ip> ...]"
  exit 1
fi

if [ ! -f "$POLICY_SRC" ]; then
  echo "ERROR: policy not found at $POLICY_SRC (set POLICY_SRC env var)"
  exit 1
fi

for R in "$@"; do
  echo "==> deploying to $R ..."
  $KSSH "$R" 'mkdir -p ~/k1_mjlab_deploy/deploy/k1_runtime'
  $KSCP "$L/k1-deploy-robot/deploy/k1_gamepad_deploy.py" "$R:k1_mjlab_deploy/deploy/"
  $KSCP "$L/k1-runtime/src/k1_runtime/gamepad_core.py" "$L/k1-runtime/src/k1_runtime/wbc.py" "$R:k1_mjlab_deploy/deploy/k1_runtime/"
  $KSCP "$POLICY_SRC" "$R:k1_mjlab_deploy/walk_still_v2.pt"
  echo "==> checking for stale runner on $R:"
  $KSSH "$R" 'pgrep -af k1_gamepad_deploy || echo "  none (ok)"'
done
echo "done. policy: $POLICY_SRC"
