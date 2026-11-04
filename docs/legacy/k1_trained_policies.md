# K1 trained policies: index and status (2026-11-02)

All policies below come from mjlab (MuJoCo Warp, rsl_rl PPO). Files live in `models/mjlab_k1/<name>/`. Shared drive copy: `Development/policies_2026-11-02/` with `MD5SUMS.txt`. Evidence for each number: `docs/k1_residual_skills_status.md`, `HANDOFF.md`, `docs/eval_*.json`.

## Under training

Nothing. kick_ma_v3 finished 2026-11-02.

## Has run on a real robot

| Policy | Robot | Result |
|---|---|---|
| walk_still_v1 | A1, 2026-10-29, user spotting, DS4 from laptop | Run 1 stood 24 s, then fell on a small push, cause unknown (no log). Run 2 ran 224 s. Weak vy tracking; feet came together (lateral spacing min 3.3 cm) and tripped |
| walk_still_v2 | A1 | Marked proven in `docs/k1_rl_policy_runbook.md`: wider feet, better vy. No logged numbers from that run in the repo |

Nothing else has run on hardware.

## Sim only

Walk bases read joint state, IMU, last action and command only, so `k1_gamepad_deploy.py` can run them. See `docs/k1_rl_policy_runbook.md`.

| Policy | File | Sim result | Limit |
|---|---|---|---|
| walk_still_v3 | `walk_still_v3/model_13997.pt` | Smoother than v2, top speed 1.09 m/s | Worst grid cell fell 62.5% |
| walk_still_v4 | `walk_still_v4/model_18996.pt` | Top speed about 1.3 m/s, worst grid cell fell 25%, far fewer falls under shoves | Midrange yaw worse than v3: at command +-1.57 rad/s gives -0.83/+0.67 |
| flat_air08, flat_swing10 | `flat_swing10/model_4999.pt` | Older flat walk | Marches at zero command |
| rough_swing10 | `rough_swing10/model_11999.pt` | Older rough walk | Check actor obs before deploying |
| rough_walk_v1 | `rough_walk_v1/model_6400.pt` | Blind actor | Fails at first 4 cm step |
| rough_walk_v2 | `rough_walk_v2/model_16399.pt` | Stairs and slope focus, base for steps_res_v2 | Not climb-profiled in this index |

Task layers need the frozen walk base plus task inputs that the robot does not yet have, unless noted.

| Policy | Task | File | Sim result | Blocker for real use |
|---|---|---|---|---|
| push_ik_v10 | `Mjlab-PushIK` (2 robots, box to pose) | `push_ik_v10/model_12496.pt` | Success 95.5% | PhaseSpace input; deploy tool tested with fake caps and fake robots only |
| push_ik_v6 to v9 | same | `push_ik_v*/` | v7 90.4%, v8 92.2% | Superseded by v10 |
| carry_vel_v1 | `Mjlab-CarryVel` (0.5-5 kg) | `carry_vel_v1/model_5999.pt` | 20 s, no falls or drops in training range | Needs box pose, forearm contact flags, mass input |
| kick_res_v1 | `Mjlab-Kick` | `kick_res_v1/model_5999.pt` | Goal 32.6%, fell 13.1% | Ball position source. Task has a reset overlap bug, effect not measured |
| kick_res_v2 | `Mjlab-Kick` | `kick_res_v2/model_5999.pt` | Goal 36.3%, fell 8.0% | Same |
| kick_dir_v1 | `Mjlab-KickDir` (any target) | `kick_dir_v1/model_11998.pt` | Heading error p50 21 deg, p95 124 deg, fell 11.4% | Ball and target source. Targets behind robot poor |
| kick_strike_v1 | `Mjlab-KickStrike` (teacher, strike point) | `kick_strike_v1/model_5999.pt` | Heading p50 5.0 deg, p95 43 deg, line miss std 1.06 m, fell 4.2% | One-sided setup. Uses true state |
| kick_ma_v1, v2, v3 | `Mjlab-KickMA` (pass, then shoot) | `kick_ma_v3/model_17997.pt` | v3 goal 23.8%, pass and shot 5.5%. See below | Sim state only |
| steps_res_v2 | `Mjlab-Steps` | `steps_res_v2/model_5999.pt` | Fell 9.2% | Tracking error xy 0.42, yaw 0.65 |
| jump_v3 | `Mjlab-Jump` | `jump_v3/model_6799.pt` | Trunk rise p50 0.13 m, air 0.26 s, 8 falls in 511 windows | Torque-speed cap is assumed, not measured on motors |

Not copied to `models/`, final eval not recorded: getup_v1 (zz-bw `k1_getup/2026-10-29_14-12-04_getup_v1/model_5999.pt`), push_ma_v1 (zz-bw `k1_push_ma/`), track_v2 and carry2_v1 (dl `~/k1_mjlab/`).

### kick_ma by layout (%)

| Measure | v2 old layout | v2 new init, instant cut | v2 new init, 1 s fade | v3 new init, 1 s fade |
|---|---|---|---|---|
| Goal | 11.0 | 11.9 | 12.0 | 23.8 |
| Pass received | 36.7 | 26.4 | 23.2 | 39.3 |
| Pass and shot | 0.8 | 1.9 | 1.4 | 5.5 |
| Ball out of bounds | n/a | 62.7 | 61.1 | 64.6 |
| robot_a fell | 25.3 | 21.2 | 23.3 | 7.2 |
| robot_a fell with ball over 1 m away | 1.1 | n/a | 1.7 | 1.0 |

v3, 512 envs: most goals are still not a pass then a robot_b shot, and ball out of bounds ends 64.6% of episodes. 62 of 270 robot_b touches send the ball away from goal (v2 55 of 190). Eval: `docs/eval_kick_ma_v3.json`.

## Needs training or building

| Item | State | Next step |
|---|---|---|
| Kick point cloud teacher | Not built | Visible ball samples, momentum model, one-sided penalty, warm start kick_strike_v1 |
| Depth student | Frozen ResNet18 encoder exists, no trainer | DAgger from the teacher, after the teacher works |
| Kick_ma next | v3 pass and shot only 5.5% | Reward goals only for pass then robot_b; reduce ball out of bounds |
| Pick up a free box | No task | Write task |
| Get-up on hardware | Policy trained, FSM in deploy | Sim test `--sim --getup`, then A1 with spotter |
| Ball rolling resistance | Sim ball has none | Measure on real floor; rest position is not measurable until then |
| Real box push | Never run | `docs/k1_phasespace_field_runbook.md` stages |
| Walk v3, v4 on a robot | Never run | `docs/k1_rl_policy_runbook.md` |

## MD5

```
4e715772eddf96c6ce97d7cbe1c8730e  carry_vel_v1/model_5999.pt
b4c1a637a741a0b0a60a23c7f6143b8c  flat_swing10/model_4999.pt
3a3d723f250677f63046b9339f212599  jump_v3/model_6799.pt
f3e49ddca53d050cc9658d4ce32d4bb2  kick_dir_v1/model_11998.pt
3cade701f3bad3c31ac66abcf45fae2c  kick_ma_v1/model_5999.pt
8a92429cdaea468db1fc87c98ef3ed8b  kick_ma_v2/model_11998.pt
b81c907be47deb9e7c4c93aac447d4a0  kick_res_v1/model_5999.pt
bb259cd994cc657ee11046739f45d814  kick_res_v2/model_5999.pt
07d8e06575d3c41a4a42735f60344288  kick_strike_v1/model_5999.pt
1497324e856c5069207ce5c9c62eac42  push_ik_v10/model_12496.pt
ff9195a570117c4cc8adcff8eb508a85  push_ik_v6/model_4999.pt
7d00ba6c82e6268d34796e99475992bc  push_ik_v7/model_6998.pt
2afc96d764456f3eca74851b812bdbdd  push_ik_v8/model_9497.pt
bd8382aa5e65433f0ea2b0615e33ebd7  push_ik_v9/model_12496.pt
3bd6d041ce60d651417b646e2d91e2f7  rough_swing10/model_11999.pt
0eeb8598c65b89d2c32b664200ea59b4  rough_walk_v1/model_6400.pt
c9b2c5860511adc059afe7f6b7aaca2e  rough_walk_v2/model_16399.pt
01e2c22a5a71d8d7ec3182b29f28843f  steps_res_v2/model_5999.pt
316415843105caa5e848d924889f545d  walk_still_v1/model_5999.pt
060ece838dd9b6244d47166d9cf8299d  walk_still_v2/model_8998.pt
53d752504259c040d99026db5b4f7d7e  walk_still_v3/model_13997.pt
d2b4a20f258d00568d4aba2dfee1754f  walk_still_v4/model_18996.pt
ae7f1ace281693d8b663382d0957f444  kick_ma_v3/model_17997.pt
```
