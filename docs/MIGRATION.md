# Migration from booster_ws

- Membership rules: `tools/decoupling/lib_deps.py` (`RULES`). Builder: `tools/build_workspace.py` (copy + split + rewrite), then `tools/gen_docs.py` (pyproject, READMEs, measured edges), then `tools/gen_viz.py`.
- Every file's old and new location: [`migration_map.tsv`](migration_map.tsv).
- Rebuild from scratch: `python3 tools/build_workspace.py && python3 tools/gen_docs.py && python3 tools/gen_viz.py` (reads `~/Projects/booster_ws` and `~/Projects/wt-k1-tools`, never writes to them).
- Original plan and order of work: `tools/decoupling/DECOUPLING_PLAN.md`. Old runbooks and plans: `docs/legacy/` (paths in them still use the old layout).

| Old | New |
|---|---|
| `mjlab_k1/src/mjlab_k1/wbc.py` | `k1-runtime: k1_runtime.wbc` |
| `mjlab_k1/src/mjlab_k1/k1_constants.py` | `k1-common: k1_common.k1_constants` |
| `scripts/k1_wiring.py` | `k1-common: k1_common.k1_wiring` |
| `mjlab_k1/deploy/k1_gamepad_deploy.py` | `k1-runtime gamepad_core` + `k1-deploy-robot/deploy/` + `k1-deploy-laptop/deploy/gamepad_sim.py` |
| `isaac_tasks/k1_velocity/source/*` | `k1-rl-isaac/src/*` |
| `mjlab_k1/scripts_X.py` | `k1-rl-mj/scripts/X.py` |
