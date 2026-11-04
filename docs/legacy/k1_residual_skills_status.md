# K1 residual skills: status (2026-11-01)

Full policy index, including 2026-11-02 kick work and current training: `docs/k1_trained_policies.md`. Train and publish steps: `docs/k1_mjlab_training_runbook.md`.

Every skill below rides on a frozen walk base. The task policy adds on top; nothing below has run on hardware.

| Skill | Layer on the frozen base | Box attached? | State | Evidence |
|---|---|---|---|---|
| Pick up a free box | none yet | no | **Not started: no task, no reward, no checkpoint** | In every carry task the box starts already in the hands |
| Carry free box to a goal, 1 kg (`Mjlab-Carry2`, carry2_v1) | velocity command + 8 arm offsets, no leg residual | no, after a 1 s weld hand-off | Trained 6000 iters on the older base | Last training log window: goal_reached ~32, fell ~0.1, box_lost ~0.08. Log counts, no separate eval, 1 kg only |
| Carry welded box to a goal, 3 kg (`Mjlab-Carry`, carry_v1) | velocity command + 8 arm offsets | yes, welded | Trained 3000 iters | Log window: goal_reached ~13, fell ~2 |
| Carry free box, 0.5-5 kg, velocity command (`Mjlab-CarryVel`, carry_vel_v1) | 12 leg residuals + 8 arm offsets | no, after a 1 s weld hand-off | Trained 6000 iters (`models/mjlab_k1/carry_vel_v1/`, base walk_still_v4) | Eval, 512 envs, first episode, 20 s: time_out 100%, fell 0%, box_lost 0%. Training-range commands only. Grid below |
| Kick (`Mjlab-Kick`, kick_res_v1) | velocity command + 12 leg residuals | n/a | Trained 6000 iters (`models/mjlab_k1/kick_res_v1/`, base walk_still_v4) | Eval, 512 envs, first episode: goal 32.6%, time_out 54.3%, fell 13.1%. Ball over 2 m away: 208 of 400 scored (52.0%). kick_v1 was never evaluated this way, so no direct comparison |
| Stairs (`Mjlab-Steps`, steps_res_v2) | 12 leg residuals | n/a | Trained 6000 iters (`models/mjlab_k1/steps_res_v2/`, base rough_walk_v2) | Eval, 512 envs, first episode, training terrain: time_out 90.8%, fell 9.2%, mean 19.35 s. Final training window tracking error: xy 0.42, yaw 0.65 |

"Balancing": the box is squeezed between the forearms, not balanced on an open surface. No balance-on-top task exists.

Blockers to real use of any carry policy:
- It observes the box pose and tilt, so the robot needs a live source for them (a PhaseSpace cap on the box, for instance).
- Carry2 and CarryVel also observe forearm contact flags. No source for those on the robot has been identified.
- CarryVel takes the box mass as an input, which the operator would enter.

## Velocity profile

`mjlab_k1/scripts_velocity_grid.py` (per weight, JSON) and `scripts_velocity_grid_html.py` (page with weight slider). Page and data: `docs/velocity_grid/`.

Grid: vx 0-3 m/s step 0.1, yaw -pi to +pi step pi/16, 8 robots per cell, in the mjlab training sim. Definitions are at the top of the script.

Baseline, walk_still_v4, no box (1023 cells): tracks both 76, vx only 260, yaw only 54, neither but upright 633, fell 0. Worst cell 25% fell.
Measured top speed at yaw 0 is about 1.3 m/s even at 3 m/s command; tracking holds to about 1.4 m/s. At vx 0, a 3.14 rad/s command gives about 1.4-1.6 rad/s. Yaw response is lopsided at 1.57 rad/s: -0.83 vs +0.67. The base saturates rather than falls.
Training ranges were vx up to 1.3 m/s and yaw well under pi, so cells beyond them are extrapolation.

Walk v3 vs v4 on the same grid (measured): at vx 0, command +-1.57 rad/s gives -1.41/+1.16 on v3, -0.83/+0.67 on v4. At 3 m/s command, top speed 1.09 on v3, 1.33 on v4. Worst cell fell 62.5% on v3, 25% on v4. The shove training cost midrange yaw.

## Carry velocity profile by weight

carry_vel_v1, same grid, 1023 cells, 8 robots per cell. "In range" is vx up to 1.0 m/s and |yaw| up to 1.0 rad/s, 121 cells; no drops or falls there at any weight. Sim only. Beyond the trained range is extrapolation.

| Box | Both | Vx only | Yaw only | Neither | Fell | Dropped | In-range both (of 121) | Top vx (m/s) |
|---|---|---|---|---|---|---|---|---|
| none, walk v4 | 76 | 260 | 54 | 633 | 0 | 0 | 64 | 1.36 |
| 0.5 kg | 287 | 116 | 76 | 469 | 6 | 69 | 112 | 1.28 |
| 1 kg | 276 | 140 | 71 | 481 | 5 | 50 | 110 | 1.30 |
| 2 kg | 258 | 169 | 67 | 494 | 2 | 33 | 107 | 1.33 |
| 3 kg | 242 | 207 | 61 | 478 | 8 | 27 | 107 | 1.33 |
| 4 kg | 209 | 246 | 63 | 452 | 5 | 48 | 102 | 1.35 |
| 5 kg | 188 | 278 | 46 | 321 | 5 | 185 | 95 | 1.40 |

Page with weight slider: `docs/velocity_grid/index.html`. GIF: `docs/velocity_grid/carry_weight_profile.gif`. Drive: https://drive.google.com/open?id=1W3g1DJAGbJWbdwllO5dUBCooh_VYKRj-
Videos and eval JSON: https://drive.google.com/open?id=1Ym5nqvIIrvWgI7m0vxGVdka791-F-lQf

## In progress, 2026-11-02

kick_res_v2: teacher only beyond 1.2 m from ball, residual full within 0.8 m, command filter alpha 0.3. Trained 6000 iters (`models/mjlab_k1/kick_res_v2/`). Eval, 512 envs, first episode (`docs/eval_kick_res_v2.json`): goal 36.3%, time_out 55.7%, fell 8.0%, mean 10.41 s. Ball over 2 m away: 307 of 397 scored (77.3%, v1 was 52.0%). Both v1 and v2 numbers include a reset bug on `Mjlab-Kick`: the ball is placed from the env origin while the robot spawns up to 0.5 m off with random yaw, so some episodes start with the ball overlapping the robot. Not fixed on that task.

Kick spread, heading error measured at 1 m of ball travel (`mjlab_k1/scripts_kick_spread.py`, multi-touch included):
- v2, fixed goal, 1024 envs (`docs/eval_kick_spread_v2_fixed_goal.json`): kicked 98.1%, fell 8.0%, abs error p50 32.7 deg, p95 152 deg, signed std 66.6 deg, speed at 1 m p50 1.05 m/s.
- v2, any target, hardest level, overlap fixed (`docs/eval_kick_spread_v2_any_target.json`): kicked 95.9%, fell 11.0%, abs error p50 55.5 deg, mean 69 deg, p95 166 deg, signed std 87 deg, speed at 1 m p50 1.01 m/s.
- Rest position is not measurable in this sim: the ball has no rolling resistance (condim 3), keeps about 1.1 m/s and ends 5-20 m away. Only heading and line crossing are meaningful until rolling resistance is measured on the real ball.

kick_dir_v1 (`Mjlab-KickDir-Booster-K1`, `mjlab_k1/src/mjlab_k1/tasks_kick_dir.py`, `models/mjlab_k1/kick_dir_v1/model_11998.pt`): target sampled in robot frame at reset, warm start from kick_res_v2. Any bearing, 1024 envs: abs heading error p50 21.0 deg (v2 57.8), p68 34.3, p95 124.1. Lateral miss at target line, 2-5 m: abs p50 0.89 m, p68 1.49, p95 4.92 (v2 1.90, 3.14, 7.96). Within 1 m of target: 43.8% of episodes (v2 16.0%). Fell 11.4% (v2 9.0%). Targets behind the robot stay poor (p50 67 deg). Curriculum stayed at level 0. Full table: `HANDOFF.md`, 2026-11-02.

jump_v3: adds air_time (grows with flight) and a one-shot landing_air reward, resumed from jump_v2 iter 800, 6000 more iters on dl GPU1. Final (`models/mjlab_k1/jump_v3/model_6799.pt`), standing starts, level 1.0: 510 landings of 511 windows, 8 falls, rise p50 0.131 m, air p50 0.26 s, drift 0.047 m, target met 0%. Level 0.55: same rise and air, 46.3% met. Training level stuck at 0.55; air flat from iter 1000.

jump_pilot, 1500 iters, ramp at target 0.04-0.125 m. Probe, 512 envs, 20 s, 2533 windows, 2504 landings: foot clearance p50 0.41 m, target p50 0.08 m, trunk rise p50 0.13 m, air p50 0.34 s, drift p50 0.09 m. Reached target 99.8%, because the policy tucks its legs far past target. Sim only. Clips: https://drive.google.com/open?id=1O7Wlm5Vm5BRPvaTNP5SxrOVtXCjVRJ4a

jump_v2, checkpoint at iter 200 of 6000, torque-speed cap on, standing starts only, 256 envs, 8 s. Level 0.5: 514 windows, 511 landings, 1 fall, trunk rise above standing p50 0.085 m, air p50 0.18 s, drift p50 0.03 m, reached target 61.6%. Level 1.0 (target p50 0.143 m): 513 windows, 512 landings, 0 falls, rise p50 0.092 m, air p50 0.20 s, reached target 5.1%. Air 0.20 s is about 0.05 m of ballistic flight; the rest of the rise is leg extension. The torque-speed line is an assumption, not measured on the motors.

