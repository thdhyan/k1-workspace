# booster_ws decoupling plan (2026-11-03)

Figures: `docs/decoupling/booster_ws_dependencies.html`, published as artifact
https://claude.ai/artifact/D9nx3WYwrSoyVr1akPQ4qw. Regenerate (from `docs/decoupling`):
`python3 lib_deps.py ../.. ../../../wt-k1-tools > lib_deps.json`, then
`$(cat ../../graphify-out/.graphify_python) cluster.py ../.. ../../../wt-k1-tools > clusters.json`, then
`python3 gen_library.py template.html booster_ws_dependencies.html`.
Status: **proposal only, nothing moved yet.**

## Findings (measured on `dev/push-training-wip` working tree + 10 worktrees + `origin`/`org`)

- **Cycle:** `scripts/` ↔ `isaac_tasks/` (3 py imports + 49 shell launchers one way, 18 path refs back).
- **Training code leaks into runtime:** `src/k1_sim_isaac` imports `k1_velocity` + `k1_teleop`;
  `k1_locomotion` path-refs isaac_tasks; `isaac_tasks/scripts/play_push_ik.py` imports `mjlab_k1/deploy/push_ik_core`;
  `assets_mjlab.py` reads the mjlab-exported USD by relative path.
- **Robot contract duplicated:** 32 files carry their own joint-name list; URDF copies in `k1_teleop/` and `real_robot/urdf/`.
- **36 `sys.path` inserts** instead of installable packages.
- **Unversioned work:** 186 untracked files (59 mjlab_k1, 55 docs, 53 models = 1.2 GB `models/mjlab_k1`), 71 modified.
- **113 host-specific shell scripts** (`dl_*`, `spark_*`, `zzbw_*`, `msi/`) hard-code paths into every package.
- **k1_chat is already a separate repo:** `feat/k1-chatbot|asr|tools|vision` have no merge base with `main`.
- **Remotes drift:** `org/main` is 78 behind `origin/main`, has 2 licence commits origin lacks;
  `org/feat/k1-chatbot` is a main-based copy diverged from the orphan line.

## Target (hybrid, chosen)

Monorepo with hard boundaries + split out `k1_chat` and `k1m`. Imports only downward:
apps/ops → train → `k1_core` → `k1_description`. Policies cross boundaries only as ONNX + manifest.

```
packages/k1_core          joints, gains, obs/action layout, policy-manifest loader
packages/k1_train_isaac   isaac_tasks/k1_velocity + compass_k1 + k1_kicking
packages/k1_train_mjlab   mjlab_k1/src + scripts_* -> CLI subcommands
packages/k1_teleop
packages/k1_policies      manifest.yaml (name, backend, obs-layout version, sha256, URL); blobs in LFS/Drive
ros_ws/src/k1_*           + k1_deploy (from mjlab_k1/deploy); sdk/ submodule stays read-only
description/              k1_description + assets submodule (single URDF/MJCF/USD source)
ops/                      docker, hosts/*.yaml, jobs/*.yaml, real_robot, tools, fleet_dashboard
split repos               k1_chat (orphan branches), k1m (git filter-repo, keeps history)
```

## Steps (each verifiable)

0. **Freeze:** commit + push untracked work in booster_ws and `wt-k1-tools`/`wt-k1-chat`/`wt-k1-vision`;
   merge `org/chore/license` into main; push main to `org`. → verify: `git status` clean in all worktrees.
1. **k1_core:** canonical joints (from `docs/k1_joint_order_canonical.md`, `mjlab_k1/k1_constants.py`), gains,
   obs IO (`docs/policy_io_reference.md`), `resolve_model(name)` via `K1_MODELS_DIR`. Swap the 32 joint lists.
   → verify: `grep -rl Left_Hip_Pitch` hits only k1_core + description; `tests/test_k1_wiring.py`, `test_agile_parity.py` pass.
2. **Break the cycle:** move `k1_wiring.py`, `mujoco_eval.py`, `motion_feasibility_gate.py`, gates into owning packages;
   `scripts/` keeps shell only. → verify: no `scripts/` path strings in any `.py`.
3. **Installable packages:** pyproject per package, uv workspace; delete 36 `sys.path` inserts.
   → verify: `grep -rn sys.path` = 0; each package's tests pass in isolation.
4. **Cut isaac→mjlab:** `push_ik_core`, `ds4` → `k1_deploy`; USD path via k1_description.
5. **Policies registry:** move `models/` blobs to LFS/Drive, keep manifest in git. ROS + sim load via manifest only.
   → verify: `k1_sim_isaac`, `k1_locomotion` import no training package.
6. **Ops:** one `k1_ops launch --host dl|spark|zzbw|msi --job <yaml>` replaces the 113 scripts.
7. **Split repos:** new remote for k1_chat (push the 4 orphan branches, reconcile `org/feat/k1-chatbot`, close `feat/k1-chat-pr`);
   `git filter-repo` k1m (+ app.py, docker/Dockerfile.k1m, k1m_service/ui, gmr/soma converters).
8. **Docs:** per-package HANDOFF; root keeps README, CLAUDE.md, STATE.md as index.
9. **Cleanup:** remove merged worktrees (trackb, squat, vr-teleop, soma, smplx) and branches; tag `archive/phase-0`, `archive/phase-6`.
10. **CI:** import-linter contracts per package in `.github/workflows/build.yml`.

Branch → target mapping: section 4 of the HTML.

## Move units (2026-11-03, supersedes the folder figures)

No file-level import cycles. Every strongly connected group closes through path strings or AST calls.
So "stays together" = same Louvain cluster of the file graph. Edge weights: import 3, path string 2, AST call 1.

| Unit | Files | LOC | Ships as | Cut at the seam |
|---|---|---|---|---|
| Isaac tasks | 92 | 20,251 | k1_rl_isaac tasks/ + sim/ | src/k1_sim_isaac moves here |
| Isaac scripts + jobs | 105 | 10,308 | k1_rl_isaac scripts/ + jobs/ | 21 multi-host chain scripts → jobs/*.yaml run by ops |
| mjlab tasks | 76 | 8,107 | k1_rl_mj | k1_constants → common, wbc.py → runtime |
| ROS bringup + SLAM | 41 | 5,124 | deploy_laptop · perception · deploy_robot | SLAM chain moves as one package |
| k1_chat | 29 | 3,927 | k1_vla, own repo | 2 edges leave the unit |
| k1m | 17 | 3,435 | k1_mimic, own repo | 0 edges leave; app.py comes along |
| Push-IK runtime (focal) | 11 | 2,993 | k1_runtime + 3 entry points | split k1_gamepad_deploy: core → runtime, run_robot → deploy_robot |
| Teleop | 21 | 3,797 | k1_teleop | k1_arm_ik → runtime |
| Eval gates | 3 | 717 | k1_utils | policy/asset paths as arguments |
| Recording | 6 | 769 | k1_data · deploy_robot | on-robot recorders stay in deploy_robot |

Tests and host launchers follow the library holding ≥60 % of their targets (26 tests, 49 launchers moved).

Result: cross-library edges 366 → 139; forbidden imports 0; 33 forbidden path strings left
(rl_isaac→ops 14, utils→rl_isaac 3, perception→data 3, mimic→ops 3, mimic→web_console 3, ...).

## Library layout

Layers, imports only downward: L0 common · L1 utils, runtime (new) · L2 rl_isaac, rl_mj, mimic, teleop,
perception, vla, data · L3 deploy_robot, deploy_laptop, web_console, ops. Full table: section 6 of the HTML.

## Order of work (replaces Steps above where they differ)

0. Freeze: commit + push untracked work in all worktrees; merge `org/chore/license`. → `git status` clean.
1. Split out k1m and k1_chat as own repos. → both install and test without booster_ws.
2. k1_common: joints, gains, k1_constants, k1_wiring, manifest, clip schema. → `grep -rl Left_Hip_Pitch` only common + description.
3. k1_runtime: split k1_gamepad_deploy; move wbc, push_ik_core, ds4, k1_arm_ik. → robot install needs only torch + common + runtime.
4. Remaining units: SLAM chain → perception, teleop, eval gates, recording. → each package's tests pass alone.
5. Training libraries take their units, launchers, tests, plus k1_sim_isaac, tasks_track, YOLO-kick check. → no upward imports in lib_deps.
6. Replace the 33 forbidden path strings with arguments/config/`resolve_model()`. → no dashed cells in the matrix.
7. pyproject per library, uv workspace; delete `sys.path` inserts. → `grep -rn sys.path` = 0.
8. Policy registry: blobs to LFS/Drive, manifest in git. → ROS + sim load via manifest only.
9. Ops: host chain scripts → `jobs/*.yaml`; web_console shell. → one command launches any job on any host.
10. CI: import-linter contracts + `lib_deps.py`, failing on forbidden cells. → CI green on main.
