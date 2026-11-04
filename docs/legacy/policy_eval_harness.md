# Policy evaluation harness (MuJoCo, standalone)

Implements WP-B / T7 of `PLAN_LOWER_BODY_WBC_NEWTON.md` without Isaac Sim, Isaac Lab or torch. Needs `mujoco`, `numpy`, `onnxruntime` only. Run everything through uv (`env -u PYTHONPATH` avoids the sourced ROS python path).

| file | role |
|---|---|
| `scripts/mujoco_eval.py` | evaluator: ONNX policy + `policy_meta.json` + K1 MJCF, command grid, switch test, push test, report writer |
| `scripts/gait_gate.py` | thin wrapper over the existing `isaac_tasks/k1_velocity/scripts/gait_gate.py` (reused, not copied) plus `evaluate()` for reports |
| `scripts/height_gate.py` | new S1/S2/S3 gate on a trace: xy/yaw err, per-H* `abs(z_rel-H*)`, falls |
| `tests/test_mujoco_eval.py` | zero-action-policy harness test, stacking test, tiny ONNX test, height-gate test |

MJCF: `src/k1_description/assets/robots/K1/K1_22dof.xml` (read only, not edited; solver options and ground friction are overridden in memory).

## Run

```bash
cd /home/thakk100/Projects/booster_ws
E="env -u PYTHONPATH uv run --no-project --with mujoco --with onnxruntime --with onnx --with numpy"
$E scripts/mujoco_eval.py --walk models/lbn_walk.onnx --stand models/lbn_stand.onnx \
   --meta models/lbn_walk.policy_meta.json --grid default --upper random --seconds 20 \
   --switch_test --push_test --out ~/lbn_mj/
$E scripts/height_gate.py ~/lbn_mj/trace.npz --mult 1.5
$E scripts/gait_gate.py   ~/lbn_mj/trace_walk.npz
$E --with pytest pytest -q tests/test_mujoco_eval.py          # harness test (4 pass)
$E scripts/mujoco_eval.py --walk zero --meta meta.json --grid smoke --seconds 2 --out /tmp/x   # dummy policy
```

Outputs in `--out`: `report.json`, `report.md`, `trace.npz` (grid cells), `trace_walk.npz` (walking grid cells, gait_gate input). Exit 0 only when every gate passes.

## policy_meta.json schema (the contract A2 must write)

`joint_order` (12, = action order), `default_pos`, `action_scale`, `action_clip`, `kp`, `kd`, `effort`, `delay_physics_steps` [min,max] (physics steps), `physics_dt` 0.005, `decimation` 4 (control rate must be 50 Hz or load fails), `obs_terms` [{name, dim, scale}], `history`, `stacking` term-major, `clock_hz`, `init_height`, optional `upper_*`, `friction`. Supported obs terms: `base_lin_vel base_ang_vel projected_gravity command joint_pos_rel joint_vel last_action clock upper_joint_pos_rel upper_joint_vel` (full field list in the `mujoco_eval.py` docstring). Anything else raises, so a layout mismatch fails loudly instead of silently.

Findings-doc bugs handled: delay in physics steps (4), history filled with the first obs (5), policy at 50 Hz only (6), single ground plane and impratio/timestep set explicitly (7), meta-driven order, scale and gains (1-3).

## Gates (PLAN section 1)

| gate | implementation |
|---|---|
| S1 | xy err <= 0.15, yaw err <= 0.25 (scaled by `--tol_mult`, default 1.5 for S5, or pass measured Isaac values via `--isaac_xy/--isaac_yaw/--isaac_h`) |
| S2 | mean `abs(z - H*)` <= 0.03 (times mult); `height_gate.py` bins by H* for cells with speed <= 0.3 |
| S3 | push group: fall fraction <= 5 % |
| S4 | `gait_gate` on walking cells: cadence 1.2-4.0, stride >= 0.15, jerk < 0.06, plus no-swing check from foot contacts |
| S5 | 0 falls on every grid cell, switch cells no fall, all of the above within 1.5x |

Fall = trunk z < 0.25 m or tilt > 60 deg. First 2 s excluded from tracking. Grid `default` = vx {0, 0.3, -0.3, 0.5} x vy {0, 0.2, -0.2} x wz {0, 0.5, -0.5} x H* {0.55, 0.47, 0.40} (108 cells; the plan's B5 also lists upper default/random, selected with `--upper`). Stand policy is used when `|(vx,vy,wz)| < 0.05`. Switch test alternates cmd 0 and 0.3 m/s every 3 s at H* 0.55 and 0.47. Push test: random 0.4 m/s velocity kicks every 2-4 s, 3 seeds, stand and 0.3 m/s.

## AGILE-style signals (per cell and per joint, in report)

Joint-limit violation (beyond 95 % of range), torque saturation fraction (PD command >= 99 % of effort, before clipping), action rate (mean abs first difference), action jerk (mean abs third difference), per-joint mean and max abs velocity.

## Verified vs unverified

Verified (laptop, mujoco 3.17, onnxruntime): harness runs end to end with the zero policy (stand cell holds 20 s with default and random upper pose; walking cells correctly FAIL tracking and gait gate); ONNX path with a zero-weight MatMul model; term-major stacking; height gate pass/fail on synthetic traces; 8 cells x 20 s take about 5 s of CPU. 4 tests pass.

Not verified:
- No real exported walk/stand policy or real `policy_meta.json` exists yet (A2 not implemented). The sample meta used in tests (default pose, gains from the findings doc, 48-dim obs) is an assumption.
- B6 regression (gaitfix student falls at 1.7-2.5 s) not run: that checkpoint is TorchScript with BFS joint order and has no meta; the harness takes ONNX only.
- B3 (dump Newton's mjModel and diff contact params, masses, armature against this MJCF) not done; contacts use the MJCF values (solref/solimp from the XML, friction 1.0 set here).
- Upper-body geoms have collisions disabled (Isaac default assumed). Upper PD defaults to kp 40 / kd 2 unless the meta gives `upper_kp/kd`. No stub-tip wrenches (B4 optional part); `step_control` has a `stub_force` hook.
- Raw `qvel` of the trunk chatters at the 2-physics-step level (about 0.35 rad/s on a still stand, up to 1.4 with random arms) while the real heading drift is about 0.03 rad/s. Tracking metrics therefore use the substep-mean velocity; the policy obs use the instantaneous value. If a policy reads `base_ang_vel`, check whether Newton/MJWarp shows the same chatter before trusting S5 on that term.
- The `trace_walk.npz` for gait_gate is only written when all walking cells survive; knee indices default to (3, 9) (joint order L x6, R x6).
- /Storage showed I/O errors during this session (corrupt venv there); the venv for testing was created under `~/.cache/k1eval`. Check the disk.
