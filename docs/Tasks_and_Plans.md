# K1 workspace: test + refactor plan

Started 2026-11-03. Baseline: [TEST_REPORT.md](TEST_REPORT.md) (umbrella `0536fe4`).

## Decisions (from user, 2026-11-03)

- Order: **fix P1 seams first**, then ROS/sim end-to-end, then redesign, re-test after every phase.
- Git: branch `refactor/decouple` in each touched `libs/k1-*` repo, **push** to `github.com/thdhyan/k1-*`.
- Refactor scope: **full redesign** allowed (cross-library APIs may change; call sites updated together).
- Remote sim hosts: the user's GPU servers (x86 A6000 / RTX 6000 Ada / Blackwell with Singularity only, and aarch64 GB10). Host list kept locally in `docs/HOSTS.local.md` (gitignored).
- Hardware: user powers robots on request (`boosterk1.a1..b3`). Never command a robot without a live confirmation.

## Local environment

- ROS Jazzy at `/opt/ros/jazzy` (source it; rclpy, xacro, colcon OK).
- RTX 4060 8 GB. Missing locally: mjlab, Isaac Lab, pinocchio, onnx, Booster SDK.

## Phase 1: P1 seams (TEST_REPORT F1-F10) + test migration

Each item: failing test first, then fix, then green.

- [x] F1 k1-mimic `.schema` imports -> `k1_common.clip_schema` (k1-mimic b870c81)
- [x] F2 runtime `ArmIK` default URDF via `k1_description` (k1-runtime ea4ba03); teleop duplicate URDF removed (k1-teleop 8a322de)
- [x] F3 deploy-laptop `push_ik_web` imports `k1_teleop.push_ik_phasespace` (k1-deploy-laptop bb5536e)
- [x] F4 mimic gate/render moved into package (`python -m k1m.gate|render`); gate + render verified on real clip
- [x] F5 rl-isaac `gait_gate` implementation restored (7cb6af3), then moved to L1 `k1_utils.gait_gate` (k1-utils 87bac75); rl-isaac `scripts/gait_gate.py` is a thin CLI
- [x] F6 vla `fleet.json` as package data (k1-vla 28e2cea)
- [x] F7 deploy-laptop wheel roots (3d1476a)
- [x] F8 rl-isaac wheel includes `k1_kicking` (7cb6af3)
- [x] F9 `dev-install.sh` covers all buildable libs + safe submodule init; SDK submodule `sdk/booster_robotics_sdk` @d5d8f7ae (deploy-laptop a173812); code paths via `k1_description` / `k1_common.paths` in deploy-laptop b7713f9, rl-isaac 724eafe, utils 87bac75, perception acf9aaa; `usd_mjlab` added to booster_assets (b9e650a) + `USD_MJLAB*` constants (description e8581d6). Legacy bucket left for Phase 2 (container layout): rl-isaac `jobs/*.sh`, 13/14 ops `spark_*_host.sh`, utils `zero_step.sh`, ops `phase6_env.sh`, `dl_k1_teleop_up.sh`
- [x] F10 ops entrypoint new-layout mode (k1-ops 0e9d148)
- [x] P2 invalid `k1.urdf.xacro` removed; view_robot uses real URDF (ROS-verified: RSP, TF, 22 joint_states)
- [x] P2 k1-common mjlab import: `k1_constants` moved to k1-rl-mj
- [x] P2: NUL-filled `push_things_rewards.py` removed, VLA fixture + markers
- [x] Real bug: rl-isaac mjlab-compat env did not call `ensure_physx_gpu_capacity` (659e47e)
- [x] Stale `test_push_ik_web.py` rewritten to current semantics (preview = note in `state.notes`, not a blocker; stop packet keeps arms 1 s): scenario now `tests/e2e_push_ik_web.py`, pytest wrapper runs it in a subprocess (deploy-laptop 3372b29). WEB TEST OK
- [x] Teleop ROS e2e now `tests/e2e_push_ik_node.py` + pytest wrapper (skips without rclpy/checkpoint; `$K1_PUSH_IK_POLICY`) (k1-teleop e52e012). NODE TEST OK
- [x] Inherited tests migrated: runtime 9ef5ff8/ac9d591 (wbc, arm_ik, gamepad_core), deploy-robot 107a72f, utils 87bac75, rl-isaac 27bb332 (paths, `isaac` marker deselected by default, 2 stale tests updated with same intent)
- [x] READMEs regenerated for all 15 libs (usage from `tools/usage/<repo>.md`, tests, env vars, ROBOTS.md link); `tools/gen_docs.py` no longer writes `pyproject.toml`/`.gitignore`, reads declared deps from pyproject, skips `third_party/`. Robots/IPs/control: [ROBOTS.md](ROBOTS.md)
- [ ] `tests/test_phase1_launch_contracts.py` (untracked, origin unknown): 2 fail. k1-ops docker host launcher passes `K1_GIT_BRANCH=dev/phase-0` (workspace entrypoint defaults to main) and mounts `libs/k1-ops` instead of the workspace root. Fix with the Phase 2 container-layout work
- [ ] Umbrella `tests/test_carry_geometry.py`, `test_k1_teleop.py`, `test_locomotion_node_layout.py` (tracked, from booster_ws) still use old `isaac_tasks/` paths: move into owning libs or delete

### How to run the suites

```bash
source /opt/ros/jazzy/setup.bash; source /tmp/k1-audit-system-venv/bin/activate
export PYTHONPATH=$(ls -d $PWD/libs/*/src | tr '\n' ':'):$PYTHONPATH   # keep ROS's path (rclpy)
export BOOSTER_SDK_ROOT=$PWD/libs/k1-deploy-laptop/sdk/booster_robotics_sdk
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1   # ROS launch_testing plugins abort collection after a module-level skip
cd libs/<lib> && python -m pytest -q -p no:cacheprovider tests
```

Last green (2026-11-03, before the plugin finding): common 7/1s, deploy-laptop 1 (e2e), deploy-robot 1, description 11, mimic 6, rl-isaac 362/8s/2d, runtime 15, teleop 1 (e2e), utils 5/1s, vla 194/6d; contracts 87/5s. rl-mj has no tests.

## Phase 2: end-to-end verification

- [ ] Local: colcon build of ROS packages, xacro/URDF check, `ros2 launch` smoke, laptop nodes vs mock
- [ ] Local: MuJoCo eval / WBC sim-to-sim with debug video
- [ ] Remote: Isaac Lab task init + single-env play with video (GPU host)
- [ ] Remote: mjlab train smoke + eval with video (GPU host, x86 and aarch64)
- [ ] Remote: mimic retargeting pipeline (GPU host)
- [ ] Hardware (user-assisted): deploy-robot runner, watchdog, gamepad, perception cameras

## Phase 3: redesign (decoupling)

Design doc first (`docs/REDESIGN.md`), reviewed before large moves. Re-run Phase 1/2 suites after.

## Design decisions taken

- **Asset ownership**: `k1-description` owns model files. `booster_assets` is its nested submodule `assets/`; Python resolver `k1_description` (`assets_dir()`, `robot_file()`, `robot_description()`), env override `K1_ASSETS_DIR`; wheel bundles `robots/K1`. No library computes model paths from its own `__file__`.
- `booster_assets` got branch `refactor/decouple` (adds the two `K1_22dof_mjlab*.xml` that were untracked in booster_ws).
- Booster SDK (public `BoosterRobotics/booster_robotics_sdk`) to live at `libs/k1-deploy-laptop/sdk/booster_robotics_sdk` (where `k1_control` CMake expects it); tests find it via `BOOSTER_SDK_ROOT`.
- `usd_mjlab/` assets only exist on one GPU host (path in `docs/HOSTS.local.md`); needed for Isaac mjlab-asset tasks.
- **Checkpoints**: `k1_common.paths.models_dir()` = `$K1_MODELS_DIR` or `~/k1_models` (locally a symlink to `~/Projects/booster_ws/models`). ROS `policy_path` relative names not found from cwd resolve there. No `<repo>/models` guessing.
- When merging `refactor/decouple` to main: `[tool.uv.sources]` git pins have no branch, so merge description before dependants.

## Log

- 2026-11-03: plan written; hosts surveyed.
- 2026-11-03: slice 1 pushed (description, common, rl-mj, mimic, deploy-laptop, booster_assets). Tests: description 8 pass; common 6 pass/2 skip (pxr, SDK); mimic 6 pass.
- 2026-11-03: slice 2 pushed (common 27efc78 paths, runtime ea4ba03, teleop 8a322de, rl-mj cb2ed30, deploy-laptop bb5536e). Contract suite: 107 pass / 6 fail (all = open F5-F8, F10, NUL file). Teleop ROS e2e `test_push_ik_node.py` with push_ik_v8: NODE TEST OK.
- 2026-11-03: Phase 1 done (see list above). Next: Phase 2 local colcon build + launch smoke, then remote.
- 2026-11-04: READMEs regenerated and pushed (refactor/decouple in all 15 libs; k1-data and k1-web-console got the branch). Contracts 87/5s.
