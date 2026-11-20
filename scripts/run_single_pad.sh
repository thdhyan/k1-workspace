#!/usr/bin/env bash
# Laptop: one DS4 -> one K1 robot over UDP. Wraps pad_udp_send.py with --hosts <one IP>.
#
# Usage:
#   ./scripts/run_single_pad.sh                    # default A3 (192.168.50.230)
#   ./scripts/run_single_pad.sh 192.168.50.82      # A1
#   ./scripts/run_single_pad.sh boosterk1.a3       # alias also works
#
# Controls: X/Cross engage, Circle/B stop (runner stays alive, re-arm),
#           Share/Select switch active robot (no effect with one host),
#           R3 trunk-height reset, left/right sticks walk, D-pad head,
#           L1/R1 hand IK, L3 arm home, Y get-up (if --getup on robot).
set -euo pipefail

ROOT="${ROOT:-$HOME/Projects/booster_proj}"
HOST="${1:-192.168.50.230}"

case "$HOST" in
  boosterk1.a1|A1|a1) HOST=192.168.50.82 ;;
  boosterk1.a2|A2|a2) HOST=192.168.50.215 ;;
  boosterk1.a3|A3|a3) HOST=192.168.50.230 ;;
esac

export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
exec env PYTHONNOUSERSITE=1 uv run --no-project --with evdev python "$ROOT/libs/k1-deploy-laptop/deploy/pad_udp_send.py" --hosts "$HOST"
