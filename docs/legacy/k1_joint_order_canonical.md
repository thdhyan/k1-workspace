# K1 canonical joint order and wiring spec

Machine-checkable twin: `scripts/k1_wiring.py` + `tests/test_k1_wiring.py`
(`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH= uv run --no-project --with pytest --with usd-core pytest tests/test_k1_wiring.py`).
Date 2026-10-27. Nothing existing was modified; fixes below are proposals only.

Honesty note: this repo has never commanded a joint on hardware (HANDOFF.md ~1294 "robot stays disconnected";
`docs/k1_walk_data_plan.md:74` `/joint_ctrl` has zero publishers). "Tested on the real robot" evidence is
therefore READ-side only (recorded bag of Booster's own walking mode). Command-side facts are unverified.

## 1. Confirmed order (22 DoF, no waist)

SDK `JointIndexK1` (`sdk/booster_robotics_sdk/include/booster/robot/b1/b1_api_const.hpp:64-96`, `kJointCntK1=22` at :143)
== URDF `K1_22dof.urdf` revolute-joint file order == MJCF `K1_22dof.xml` joints (after free `world_joint`) AND the
22 `<motor>` actuators == real `/joint_states` order (bag `real_robot/bags/k1_walk_20260929_023045/seg001`)
== `src/k1_control/k1_control/sim_bridge_node.py:23-33`.

| idx | URDF/MJCF name | SDK enum | axis | limit (rad) |
|---|---|---|---|---|
| 0 | AAHead_yaw | kHeadYaw | z | -1.0 .. 1.0 |
| 1 | Head_pitch | kHeadPitch | y | -0.349 .. 0.855 |
| 2 | ALeft_Shoulder_Pitch | kLeftShoulderPitch | y | -3.316 .. 1.22 |
| 3 | Left_Shoulder_Roll | kLeftShoulderRoll | x | -1.74 .. 1.57 |
| 4 | Left_Elbow_Pitch | kLeftElbowPitch | y | -2.27 .. 2.27 |
| 5 | Left_Elbow_Yaw | kLeftElbowYaw | z | -2.44 .. 0 |
| 6 | ARight_Shoulder_Pitch | kRightShoulderPitch | y | -3.316 .. 1.22 |
| 7 | Right_Shoulder_Roll | kRightShoulderRoll | x | -1.57 .. 1.74 |
| 8 | Right_Elbow_Pitch | kRightElbowPitch | y | -2.27 .. 2.27 |
| 9 | Right_Elbow_Yaw | kRightElbowYaw | z | 0 .. 2.44 |
| 10 | Left_Hip_Pitch | kLeftHipPitch | y | -3.0 .. 2.21 |
| 11 | Left_Hip_Roll | kLeftHipRoll | x | -0.4 .. 1.57 |
| 12 | Left_Hip_Yaw | kLeftHipYaw | z | -1.0 .. 1.0 |
| 13 | Left_Knee_Pitch | kLeftKneePitch | y | 0 .. 2.23 |
| 14 | Left_Ankle_Pitch | kCrankUpLeft | y | -0.87 .. 0.345 |
| 15 | Left_Ankle_Roll | kCrankDownLeft | x | -0.345 .. 0.345 |
| 16-21 | Right_* same as 10-15 | kRight*/kCrankUpRight(20)/kCrankDownRight(21) | same | Right roll -1.57..0.4 |

Signs: axes identical left/right (roll +x both sides); only roll and elbow-yaw LIMITS are mirrored. Knee flexes positive.
No per-joint sign flips exist between SDK/URDF/MJCF (all asserted in tests).
Names: the odd `A`/`AA` prefixes (`AAHead_yaw`, `ALeft_Shoulder_Pitch`, `ARight_Shoulder_Pitch`) are real.
Real robot `/joint_states` spells head `AAHead_Yaw`, `Head_Pitch` (capital Y/P): match case-insensitively.

Evidence: header :64-96; URDF joint list; MJCF actuators; bag `/joint_states` names (22, SDK order);
bag `/low_state` decoded with SDK IDL: `/joint_states.position == motor_state_serial[i].q` for all 22 in 3 samples.

### 1.1 Ankle (4-bar) space
SDK names legs 14/15/20/21 `CrankUp/CrankDown` (motor space). `motor_state_parallel[14,15,20,21]` are crank-motor angles
(e.g. 0.086,0.085,0.084,0.064); `motor_state_serial` are ankle pitch/roll (e.g. -0.103,0.006,-0.088,0.016) and equal
`/joint_states`. The other 18 joints are identical in both arrays. Index 14 = ankle PITCH, 15 = ankle ROLL in serial space
(consistent with `docs/policy_io_reference.md:403-430`).

## 2. Isaac / PhysX (BFS) order vs deploy order

Isaac Lab resolves `joint_names` with `preserve_order=False` to articulation (BFS) order, interleaving L/R.
`velocity_env_cfg.py:301-309` `JointPositionActionCfg(joint_names=K1_LEG_JOINTS (:66-71, [L*6,R*6]))` has no `preserve_order`,
so the trained 12-dim action/obs are in BFS-leg order, NOT [L*6,R*6].

Full 22 BFS (derived from USD tree `K1_flat.usd`, Trunk children Head, LArm, RArm, LHip, RHip):
0 AAHead_yaw, 1 ALeft_SP, 2 ARight_SP, 3 L_Hip_Pitch, 4 R_Hip_Pitch, 5 Head_pitch, 6 L_Sh_Roll, 7 R_Sh_Roll,
8 L_Hip_Roll, 9 R_Hip_Roll, 10 L_Elb_Pitch, 11 R_Elb_Pitch, 12 L_Hip_Yaw, 13 R_Hip_Yaw, 14 L_Elb_Yaw, 15 R_Elb_Yaw,
16 L_Knee, 17 R_Knee, 18 L_Ank_Pitch, 19 R_Ank_Pitch, 20 L_Ank_Roll, 21 R_Ank_Roll.

Leg-only 12 in BFS: [LHipP, RHipP, LHipR, RHipR, LHipY, RHipY, LKnee, RKnee, LAnkP, RAnkP, LAnkR, RAnkR];
ids [3,4,8,9,12,13,16,17,18,19,20,21]. Leg ids are EVIDENCE-CONFIRMED (HANDOFF.md:644 play log `[3,4,8,9,...]`;
sim2sim findings doc Bug 1 :10). Arm/head positions in the 22-BFS are derived, not logged.

Maps (in `k1_wiring.py`): `SDK_TO_BFS`, `BFS_TO_SDK`, `LEG_DEPLOY_TO_BFS`, `LEG_BFS_TO_DEPLOY`, `LEG_SDK_INDEX=10..21`.
Use `reorder(vec, LEG_BFS_ORDER, LEG_DEPLOY_ORDER)` on policy output before sending to `motor_cmd[10..21]`.

## 3. Default / stand pose

| source | legs | arms/head |
|---|---|---|
| Sim `booster.py:83-92` init_state (action offset) | all 0, base z 0.57 | L/R shoulder roll -1.3/+1.3, rest 0 |
| Real stand (bag first frame, Booster walking mode) | knee 0.105, ankle pitch -0.103/-0.088, hips ~0 | shoulder roll -1.451/+1.452, shoulder pitch 0.187/0.194, elbow yaw -0.496/+0.485 |
| Official prepare (secondhand, `k1_ros_deployment_plan.md:236-240`) | knee +0.105, ankle pitch -0.10 | n/a |

`locomotion_node.py:93` `DEFAULT_LEG_POS = zeros(12)` matches sim, not the real stand pose: a first command moves the
robot knee 0.105 / ankle -0.10 away from where Booster's own prepare leaves it (step on enable).

## 4. PD gains

Sim-trained (derived `kp=I w^2, kd=2 zeta I w`, `actuator.py:233-236`, `booster.py:94-165`): hip pitch 30.2/3.60,
hip roll 21.45/2.56, hip yaw 17.85/2.13, knee 60.4/4.81, ankle pitch 24.98/2.98, ankle roll 7.14/0.85, arms/head 3.95/0.251.
Pre-`8e019b2` gaitfix checkpoints trained with hand-tuned override (~100/5; see HANDOFF.md ~1155-1200).
Never-run bridge `sdk_bridge_node.cpp:121-148`: kp 30.2/21.4/17.8/60.4/35.7/35.7, no arm/head gains (0).
Vendor example `b1_low_sdk_example.cpp:82-95` (23-DoF layout): legs kp 350,350,180,350,550,550 kd 7.5,7.5,3,5.5,1.5,1.5; arms 40,50,20,10; head 5.
Official K1 prepare (secondhand): legs 350,350,180,350,250,250 kd 7.5,7.5,3,5.5,5,5; walk gains legs 100..65 kd 2..1, arms 20, head 4.
**No gains verified on hardware by us.**

## 5. Action scale, timing

- Training cfg: scale 1.0, clip +-1 (`velocity_env_cfg.py:301-309`, since `5d5af78` 2026-09-27). Kick legs 0.25, head 0.5, carry arm 0.25, push arms 1.0.
- Deploy defaults 0.25: `locomotion_node.py:126,356`, `guide_real.md:133`, `policy_io_reference.md:129-146`, `run_sim.py` `--k1-scale`.
- Control 50 Hz = dt 0.005 x decimation 4 (`velocity_env_cfg.py:973-974`); obs history 10.
- Sim actuator delay `min_delay=2,max_delay=8` PHYSICS steps = 10-40 ms (`booster.py`, `actuator.py:96-98`).

## 6. Discrepancies (all unresolved in code; proposed fix, not applied)

| # | Disagreement | Where | Proposed fix |
|---|---|---|---|
| 1 | BFS interleaved (trained) vs [L*6,R*6] (deploy) | `velocity_env_cfg.py:301`; `locomotion_node.py:85-91`; `run_sim.py`; docs; `lower_body_env_cfg.py` lacks `preserve_order` | "A1": `preserve_order=True` in env and retrain, OR permute with `LEG_BFS_TO_DEPLOY` at deploy for existing checkpoints |
| 2 | Action scale 1.0 (cfg) vs 0.25 (node/docs/run_sim) | see s5 | read scale from the checkpoint's env cfg; set node default accordingly; fix docs |
| 3 | Delay units: physics steps 10-40 ms vs `run_sim.py:233` control steps 40-160 ms | run_sim | `delay_n = randint(2,8)` physics substeps |
| 4 | History init: Isaac fills with first obs vs zeros (`locomotion_node.py:161`, `run_sim.py:452-454`) | | fill with first obs |
| 5 | Wrong names: `wbc_node.py:25-33` (no A/AA), `CLAUDE.md` joint list, stray A prefixes in `policy_io_reference.md:403-430` | | use `k1_wiring.JOINTS` |
| 6 | Real head name case `AAHead_Yaw` vs URDF `AAHead_yaw` | bag vs URDF | case-insensitive match |
| 7 | **`sdk_bridge_node.cpp:209` reads `motor_state_parallel`** -> ankle values in crank space; real `/joint_states` = `motor_state_serial`. Cmd uses `PARALLEL` (:71) while official deploy uses SERIAL | | read `motor_state_serial`; decide cmd_type by bench test |
| 8 | Default pose: sim legs 0 vs real stand knee 0.105 / ankle -0.10; sim shoulder roll +-1.3 vs real +-1.45 | | blend from current state at enable; or train with real default |
| 9 | Gains: sim ~30-60 vs hand-tuned 100 vs vendor 350-550 vs bridge 30-60 vs prepare 250 | | bench decision, see s7 |
| 10 | Effort limits URDF/MJCF 30/35/20/40/20 vs sim actuators 68/76/38.3/112/38.3 | | sim2sim must use sim limits |
| 11 | Arm/head kd `run_sim` 0.126 vs sim 0.251 | | align to 0.251 |
| 12 | MJCF head armature 0.002 vs sim 0.001; MJCF ankle 0.0565 vs sim 1.4x/0.4x of 0.0282528 | | note only |
| 13 | CLAUDE.md "22 DoF" joint list omits 2 DoF per arm wrist; arms are 4 DoF each (2+4+4+6+6=22) | CLAUDE.md s3 | doc fix |

## 7. Needs human check on the real robot
1. Isaac: `print(robot.joint_names)` to confirm full 22-BFS (legs already confirmed).
2. Ankle bench test, robot hung, Custom mode, small kp, single joint +-0.10 rad on idx 14/15: confirm `motor_state_serial` readback and foot direction; confirm which `cmd_type` (SERIAL vs PARALLEL) firmware expects.
3. Safe PD gains on hardware (nothing verified).
4. Whether `rt/joint_states` vs `/low_state` is the right feedback topic, and Custom-mode switching procedure.

## Confidence
High: order and names (SDK, URDF, MJCF, bag agree). Medium: full 22-BFS (leg ids confirmed). Low: gains, cmd_type and ankle command semantics.
