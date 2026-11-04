#!/usr/bin/env bash
# Editable-install every buildable python library, in layer order, into the
# active venv. Deps between k1-* libraries resolve to these editable checkouts.
set -euo pipefail
cd "$(dirname "$0")/.."
# Init only empty submodules: `update` on a populated one would detach its HEAD.
for p in $(git config -f .gitmodules --get-regexp path | awk '{print $2}'); do
  [ -e "$p/.git" ] || git submodule update --init -- "$p"
  if [ -f "$p/.gitmodules" ]; then
    for q in $(git -C "$p" config -f .gitmodules --get-regexp path | awk '{print $2}'); do
      [ -e "$p/$q/.git" ] || git -C "$p" submodule update --init -- "$q"
    done
  fi
done
for r in k1-description k1-common k1-utils k1-runtime \
         k1-rl-mj k1-rl-isaac k1-mimic k1-teleop k1-vla \
         k1-deploy-laptop; do
  uv pip install -e "libs/$r" --no-deps
done
