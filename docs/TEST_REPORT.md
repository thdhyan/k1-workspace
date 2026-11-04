# K1 workspace: module and refactor test report

Date: **2026-11-03**. Source snapshot: umbrella commit `0536fe4513f947883f76de0a48244d10643e4e94`, with the local submodule contents recorded in [source hashes](audit/2026-11-03/source_hashes.json). This audits the local checkout, not unpublished remote branches.

**Result: the refactor is not yet verified end to end. Several CPU-only entry points fail before reaching ROS, a simulator, or a robot.** Much of the inherited test suite also still addresses the old monorepo layout. Passing syntax checks or building wheels does not establish that a module works.

## Scope and method

Reviewed root README, all 15 library READMEs and package manifests, architecture/migration/known-issues documents, and relevant test/source-directory READMEs. Queried the existing graphify graph as an orientation aid; findings below were checked against current files and executed tests. The graph contains code relationships only and uses older source-path labels.

The workspace consists of `libs/k1-*` submodules, root integration tests, migration/document generators in `tools/`, bootstrap scripts, and generated documentation. Its declared layers are:

| Layer | Libraries |
|---|---|
| L0 contract | common, description |
| L1 core | runtime, utils |
| L2 domain | rl-isaac, rl-mj, mimic, teleop, perception, vla, data |
| L3 applications | deploy-robot, deploy-laptop, web-console, ops |

Checks performed:

1. Ran **57 inherited test files separately**, so a collection error in one file could not hide another file's results. Activated current `libs/*/src` paths through `PYTHONPATH`; no legacy checkout was added to the test import path. Excluded tests marked `robot`, `net`, or `onprem`.
2. Added **91 refactor contract cases** in [test_refactor_contracts.py](../tests/test_refactor_contracts.py): compilation, shell parsing, explicit relative imports, declared sibling imports, CPU imports, motion CSV round-trip, WBC checkpoint/history/reset, shared gamepad configuration/FK, arm IK, data freshness, dashboard heartbeat parsing, resources, and wheel runtime probes.
3. Built all **9 libraries declaring a build backend** with Hatchling; probed extracted wheels outside the checkout source path. No dependency-resolution or clean-machine full installation was performed.
4. Ran a **diagnostic-only** pass over temporary copies of 27 inherited test files. Updated only test path/import references using the migration map. Production files and behavioral assertions were not changed. Exact substitutions: [adaptations.json](audit/2026-11-03/diagnostic/adaptations.json). These are not passing results for the unmodified suite.
5. Ran Pyflakes over production Python. Compared selected defects to the available original `booster_ws` files to distinguish inherited defects from broken relocation.

Environment: Python 3.12.3, pytest 7.4.4, NumPy 2.5.4, Torch 2.14.1+cu130, MuJoCo 3.12.0. Small test/build dependencies (`respx`, `hatchling`, `websockets`) were installed into an isolated `/tmp` venv for supplemental checks. No repository dependency manifests or production files were changed. Full details: [environment.json](audit/2026-11-03/environment.json).

No live robot, remote host, GPU simulation, training, retargeting inference, or camera pipeline was started. Local mock HTTP/UDP tests did run. No saved simulation video is claimed because no simulation/play/evaluation run was completed.

## Measured outcomes

| Run | Passed | Failed assertions | Collection/setup errors | Skipped | Meaning |
|---|---:|---:|---:|---:|---|
| Inherited tests, unchanged sources, 57 files | 204 | 155 | 15 | 5 | 379 JUnit outcome records; collection failures prevent additional tests from being counted |
| New contract suite, isolated test venv | 70 | 15 | 0 | 6 | 91 cases; six skips are modules with no shell scripts |
| VLA suite with missing test dependencies supplied | 192 | 2 | 0 | 0 | Six live tests deselected; remaining failures are missing image fixture |
| Temporary path/import-adapted diagnostics | 361 | 25 | 0 | 9 | 395 records across 27 files; not a clean-checkout pass |

These runs overlap; **do not add their totals together**. Deselected live tests are not skips and are not included in these counts. No test-file timeout occurred. Exit code 5 occurred for a fully skipped file and for a script containing no pytest test functions; it does not prove broken production code.

Compilation: **378 of 379 library Python files compile**, including inherited tests. **All 137 library shell scripts pass `bash -n`**. These are syntax checks, not execution. All 15 declared sibling-import checks pass for recognized `src` packages; dynamic imports, shell paths, and external dependencies are outside that check.

All nine Python wheel builds succeed. Three independent runtime probes fail: VLA fleet config, laptop ROS module resolution, and missing `k1_kicking` package. See [wheel builds](audit/2026-11-03/wheel_builds.json) and [wheel probes](audit/2026-11-03/wheel_probes.json).

## Per-module assessment

“Partial” means the named checks passed, not that the whole module works. “Blocked” means required runtime/assets were unavailable. None of the robot/GPU applications receives an end-to-end pass.

| Module | Assessment | Executed evidence and remaining failures |
|---|---|---|
| **k1-common** | Partial; contract boundary broken | Wiring's three asset-independent tests and new CSV/joint-order round-trip pass. Four inherited tests fail on old URDF/MJCF/SDK paths; USD test skips. `k1_constants` import requires absent `mjlab`, despite L0 “no heavy deps” contract. Its default MJCF path also retains old layout. |
| **k1-description** | Fails local resource/XML checks | Default `k1.urdf.xacro` is invalid XML. `assets/` and `meshes/` are absent but unconditionally listed in CMake install sources. No nested asset submodule is registered. ROS/xacro execution not validated. |
| **k1-utils** | Partial; evaluator blocked | Current `height_gate`/`mujoco_eval` imports pass. Path-adapted tests: 2 pass, 1 fails on nonexistent default MJCF, 1 skips missing `onnx`. Original tests cannot collect because they import removed top-level names. Synthetic height gate and history stacking pass. |
| **k1-runtime** | Core checks pass; default IK fails | New WBC checkpoint/history/reset, mirror, gamepad/FK/config checks pass. Arm IK works with an explicitly supplied existing teleop URDF; default `ArmIK()` fails because it looks beside its relocated Python file. Adapted WBC suite: 5 pass, 1 stale clamp expectation. Script-style MuJoCo arm test collects zero tests and its `main()` was not executed. |
| **k1-rl-isaac** | Fails source/gate checks; simulator blocked | New check finds NUL-filled reward source. Gait gate wrapper cannot find its implementation. `k1_kicking` omitted from wheel. Adapted diagnostics: **348 pass, 16 fail, 8 skip**; many source/tensor contracts work after test path repair. Isaac/booster dependencies unavailable, so task initialization and rollout remain unverified. |
| **k1-rl-mj** | Build/syntax pass; runtime blocked | Python and shell syntax pass; wheel builds. `mjlab`, assets, and policy checkpoints unavailable. `tests/check_push_ik_parity.py` is a CUDA/checkpoint script, not a pytest test, and was not run. No training or policy-parity pass established. |
| **k1-mimic** | Fails package import | `import k1m` fails on missing local `schema`. Local gate/render scripts resolve to nonexistent `src/scripts/`. Wheel builds but import is broken. No inherited unit suite; remote retargeting and UI not executed. |
| **k1-teleop** | Mapping passes; IK default/ROS blocked | Four root mapping/clutch/head tests pass; three root IK tests fail through runtime's missing default URDF. Current mapping and PhaseSpace modules import. ROS integration test cannot collect without `rclpy`; it also retains a bare old module import. No headset or mocap run. |
| **k1-perception** | Syntax only; integration unverified | Eight Python and five shell files parse. No inherited automated suite. cuVSLAM, ROS, nvblox, calibrated sensors, and stream integration not available in tested environment. No claim that SLAM works. |
| **k1-vla** | Strong unit coverage; fixture/wheel failures | Supplemental suite: **192 pass, 2 fail**, six live tests deselected. Missing `tests/fixtures/ball_right.jpg` causes both failures. Mock LLM, audio segmentation, safety, console, tools and conversation tests pass. Extracted wheel cannot load default fleet config. Real ASR/TTS/VLM/robot operation remains unverified. |
| **k1-data** | One utility passes; pipeline unverified | New SQLite/CDR test confirms frozen vs advancing messages produce expected stamp/payload counts. Six Python and three shell files parse. No inherited suite. Real rosbag conversion/SDK camera queries not executed. |
| **k1-deploy-robot** | Shared core partial; runner unverified | Shared classes resolve from runtime and configuration/FK checks pass without robot access. Original suite cannot import runner via current src paths; diagnostic pass adds its deploy directory, then gets 1 pass/7 failures due to old API assumptions and model path. No SDK/robot control or watchdog execution. |
| **k1-deploy-laptop** | Fails web import and wheel layout | Fake web test fails before serving because of bare `push_ik_phasespace` import. ROS node suite cannot collect without ROS. Adapted root layout checks all 5 pass. Wheel installs nested packages one level too deep; bootstrap also omits this buildable library. No simulation or ROS integration pass. |
| **k1-web-console** | Parser/building blocks partial | New protobuf heartbeat parser test passes with `websockets` supplied. Four Python files parse. No inherited suite. Live dashboard polling, Streamlit UI, and camera paths unverified; ROS/Streamlit dependencies are environment-provided or unresolved. |
| **k1-ops** | Shell syntax passes; new-layout launch incompatible | All 64 shell files parse. Container defaults still clone `booster_ws` and address `isaac_tasks/...`, so they cannot launch this workspace layout as-is. No Docker/Apptainer build, remote job, CI, or SLURM run attempted. |

## Confirmed failures and fixes to prioritize

### P1: failures introduced or exposed by relocation/packaging

| ID | Failure / evidence | Impact and smallest corrective direction |
|---|---|---|
| F1 | [k1m local_stages.py](../libs/k1-mimic/src/k1m/local_stages.py#L17), `__init__.py`, `pipeline.py`, and `cli.py` still import `.schema`; only `k1_common.clip_schema` exists. New `test_cpu_library_import[k1m]` fails. | Entire mimic package import fails. Rewrite callers to shared schema or provide an explicit supported compatibility module. |
| F2 | [runtime k1_arm_ik.py](../libs/k1-runtime/src/k1_runtime/k1_arm_ik.py#L31) resolves default URDF beside itself; URDF remains under teleop. New default-resource test and three inherited IK tests fail. Explicit-resource check passes. | XR/default IK fails before solving. Give resource a proper owner/package location and resolve it there; do not restore old checkout path hacks. |
| F3 | [push_ik_web.py](../libs/k1-deploy-laptop/deploy/push_ik_web.py#L39) uses `from push_ik_phasespace import ...`; module moved to `k1_teleop`. | Web tool fails even with `--fake`. Use declared package import; migrate matching integration test import too. |
| F4 | [mimic local_stages.py](../libs/k1-mimic/src/k1m/local_stages.py#L19) computes `_REPO` as `libs/k1-mimic/src`; subprocess targets are actually in `libs/k1-mimic/scripts`. | Gate/render subprocesses cannot start after package import is repaired. Resolve actual scripts and define how they are distributed. |
| F5 | [gait_gate.py](../libs/k1-rl-isaac/scripts/gait_gate.py#L15) is the thin wrapper and points into removed `isaac_tasks/...`. Original implementation exists in old checkout but is absent from new checkout. | Five adapted gait CLI tests fail through this missing dependency. Preserve one actual gate implementation and point wrapper/callers at it. |
| F6 | [VLA fleet.py](../libs/k1-vla/src/k1_chat/fleet.py#L5) computes config path relative to repo root; root `fleet.json` is absent from wheel. | Source-checkout tests pass, installed distribution fails. Package config as data and resolve it with package-resource APIs, retaining explicit path override. |
| F7 | [laptop pyproject.toml](../libs/k1-deploy-laptop/pyproject.toml) packages ROS project directories instead of their inner Python packages. Wheel contains `k1_wbc/k1_wbc/wbc_node.py`; expected `k1_wbc.wbc_node` cannot resolve. | Advertised Python installation does not expose normal ROS module paths. Correct wheel roots or explicitly support/document colcon-only distribution. Colcon build itself was not tested. |
| F8 | [Isaac pyproject.toml](../libs/k1-rl-isaac/pyproject.toml) packages `compass_k1` and `k1_velocity`, omitting present `src/k1_kicking`. | Source-tree availability hides missing installed task code. Include intended package or retire/document it explicitly. |
| F9 | [dev-install.sh](../scripts/dev-install.sh) omits buildable `k1-deploy-laptop`; description/common/utils/simulation defaults retain old asset paths. | Root README's install flow does not prepare every advertised Python library or assets. Define complete bootstrap and explicit model/asset configuration. |
| F10 | [ops entrypoint.sh](../libs/k1-ops/docker/entrypoint.sh) defaults to `booster_ws`, its branch, and old editable-install/training paths. | Legacy-container mode may still work against the old repository; **new workspace mode is incompatible**. Add a new-layout launch path before calling migrated ops working. |

### P2: inherited defects and architectural gaps

- **Corrupt reward source:** [push_things_rewards.py](../libs/k1-rl-isaac/src/k1_velocity/tasks/push/push_things_rewards.py) contains 13,379 NUL bytes; compilation raises `source code string cannot contain null bytes`. Byte-identical to original source, confirming known inherited corruption. Restore a valid implementation before loading task paths that use it.
- **Invalid description XML:** [k1.urdf.xacro](../libs/k1-description/urdf/k1.urdf.xacro#L6) contains `--init` inside an XML comment, which XML forbids. `ElementTree` raises `not well-formed (invalid token): line 6, column 42`. Byte-identical to original source. After syntax repair it still describes a placeholder base link rather than the 22-joint robot. `view_robot.launch.py` uses this file.
- **Missing description assets:** `assets/` and `meshes/` are unconditional CMake install sources, but absent. README describes manually adding assets; recursive umbrella clone alone cannot provide them because nested asset submodule is not registered. This is a missing prerequisite and incomplete bootstrap, not evidence of broken mesh geometry.
- **L0 common depends on mjlab:** [k1_constants.py](../libs/k1-common/src/k1_common/k1_constants.py#L16) imports mjlab entity/actuator config types at module import; `mjlab` is not a declared install dependency there. Separate simulator config from pure contract data to satisfy documented L0 boundary.
- **Undefined names:** Pyflakes finds `ArticulationCfg` in `probe_k1_bodies.py:31` and `CurriculumCfg` in `kicking_env_cfg.py:298`. Both were already documented. These are static findings; simulator execution was not available to exercise them. [Full output](audit/2026-11-03/pyflakes.log).

Origin comparisons are recorded in [origin_comparisons.json](audit/2026-11-03/origin_comparisons.json). They compare available local files, not historical Git revisions.

## Test-suite failures that must not be mistaken for production regressions

- Most Isaac tests use `isaac_tasks/k1_velocity/source/...` beneath the relocated repo. Fixing only these test paths reveals hundreds of passing checks: 35 manager-config checks, phase-clock/stride checks, SG push reward numerics, curriculum/ramp behavior, keyboard controller, plateau stopper, and import ordering.
- Original import-order guards report **2 skips and zero executed guards** because old script directory is empty. Diagnostic path repair discovers 66 cases: 59 pass, seven skip scripts without launchers. Empty discovery can look deceptively healthy.
- Runtime WBC test expects command caps `(1.0, 0.5, 1.0)` while implementation's declared range permits forward `1.4` and yaw `1.2`. This is a contract disagreement, not proof that current clamp arithmetic is wrong. Resolve intended envelope before changing either side.
- Robot tests still expect helper exports on `k1_gamepad_deploy` that now belong to `gamepad_core` (`Still`, `ArmJog`, `hand_fk`, `stick_to_cmd`, and `CAP`). Update ownership in tests; preserve behavior checks. Existing FK test also unpacks two values while implementation returns three.
- Remaining adapted Isaac failures include absent Isaac/Gym/booster reference dependencies, tests tied to old actuator configuration/source/submodule structure, a gait AST test that demands a direct `joint_vel` read now delegated to a helper, a shell-launcher path assembled with an unmigrated directory, and one PhysX capacity guard complaint. These require review, not automatic production-code changes merely to make tests green.
- `test_mujoco_eval.py` imports removed top-level `mujoco_eval`/`height_gate` names. Once imports are adapted, synthetic gate/history tests pass; physics harness still fails on missing/default model path and ONNX-specific test skips absent `onnx`.
- VLA vision fixture `tests/fixtures/ball_right.jpg` was not carried over. Both remaining offline VLA failures share that root cause. `respx` is also missing from declared test dependencies; adding it in isolated test environment removes the two initial LLM collection failures.
- Several “test” files are executable scenarios with setup at import time. `test_push_ik_web.py` starts a local process during collection and then masks its import failure with `NameError: name 's' is not defined`. Convert these to explicit integration tests with fixtures, prerequisite checks, and clear startup failure reporting.
- Root pytest configuration/registered custom markers are absent. Always deselect live markers explicitly. Standalone scripts such as MuJoCo arm IK and CUDA push parity do not become tested merely because pytest scans their directories.

The architecture document also says `tools/gen_docs.py` “fails loudly” on disallowed imports. Current generator prints violations at the end without raising or returning failure, and rewrites manifests/READMEs before that print. It was inspected, not run, to preserve existing source/document state.

## Reproduce

From repository root, rerun inherited files with current source-path activation and captured evidence:

```bash
rtk proxy python3 scripts/audit-tests.py --output /tmp/k1-existing-audit
```

New suite, using installed pytest/numpy/torch/MuJoCo:

```bash
rtk pytest tests/test_refactor_contracts.py -q --tb=short
```

For wheel/parser tests and complete mocked VLA coverage, create an isolated test environment. This adds only small test/build dependencies; it does not install ROS, Isaac, mjlab, models, or robot SDKs:

```bash
UV_CACHE_DIR=/tmp/k1-audit-uv-cache uv venv --python /usr/bin/python3 --system-site-packages /tmp/k1-audit-system-venv
UV_CACHE_DIR=/tmp/k1-audit-uv-cache uv pip install --python /tmp/k1-audit-system-venv/bin/python hatchling respx websockets
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  rtk proxy /tmp/k1-audit-system-venv/bin/python -m pytest \
  tests/test_refactor_contracts.py -q --tb=short -p no:cacheprovider
PYTHONPATH=libs/k1-vla/src:libs/k1-runtime/src:libs/k1-common/src:libs/k1-utils/src \
  PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  rtk proxy /tmp/k1-audit-system-venv/bin/python -m pytest libs/k1-vla/tests \
  -q -m 'not robot and not net and not onprem' -p no:cacheprovider
```

New tests intentionally remain red for unresolved defects; failures are not hidden with `xfail`. Optional Hatchling/WebSockets tests skip when dependencies are absent. Tested Python version is 3.12; new audit checks use standard-library `tomllib` (3.11+).

Evidence: [inherited summary](audit/2026-11-03/existing_summary.json), [per-file commands/results](audit/2026-11-03/existing_results.json), [new suite log](audit/2026-11-03/refactor_contracts.log), [new suite JUnit](audit/2026-11-03/refactor_contracts.xml), [VLA log](audit/2026-11-03/vla_with_test_dependencies.log), and [diagnostic summary](audit/2026-11-03/diagnostic_summary.json). All 57 original file logs/JUnit files are alongside those summaries. Temporary diagnostic test copies are not part of the checked-in test suite; their recorded adaptations document the experimental pass.

## Remaining acceptance work

First repair import/resource/wheel/bootstrap seams and migrate tests without weakening assertions. Restore corrupted source and missing test fixtures. Re-run CPU suites from source and from built distributions. Then validate ROS packages, Isaac/mjlab task initialization, checkpoint parity, rendered single-environment smoke/evaluation runs, SLAM/camera/bag pipelines, retargeting, and robot deployment on their appropriate hosts. Save and inspect debug video for simulation checks. Until those integrations run, training quality and physical-robot behavior remain **unverified**.
