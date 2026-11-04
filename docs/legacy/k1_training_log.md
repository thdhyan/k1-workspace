# K1 mjlab training log

Every mjlab training run, 2026-10-27 to 2026-11-02. Older Isaac Lab runs: `TRAINING.md`. Policy files and md5: `docs/k1_trained_policies.md`. How to run: `docs/k1_mjlab_training_runbook.md`. Details per day: `HANDOFF.md`.

Run directory: `<host>:<root>/mjlab/logs/rsl_rl/<experiment>/<run>/`. Roots: zz-bw `/export/scratch/thakk100/k1_mjlab`, dl `~/k1_mjlab`. Last checkpoint is the newest `model_N.pt` there. Results are sim only unless the Real column says otherwise. "No eval" means only training log counts exist.

## Walk bases (`k1_velocity`, `k1_velocity_rough`)

| Run | Host | Start | Warm start | Last ckpt | Result | Real |
|---|---|---|---|---|---|---|
| smoke1 | zz-bw | 10-28 00:00 | none | 299 | Smoke | |
| base_flat, base_rough | zz-bw | 10-28 00:03 | none | 2999 | First mjlab bases. No eval recorded | |
| air_a, air_b | zz-bw | 10-28 00:51 | none | 2999 | Air-time weight trials. No eval recorded | |
| flat_air08, rough_air08 | zz-bw | 10-28 01:12 | none | 4999 | flat_air08 evals in `models/mjlab_k1/flat_air08/eval_*` (ONNX only) | |
| flat_swing4, flat_swing10 | zz-bw | 10-28 16:35 | none | 4999 | flat_swing10: Isaac sim2sim, 5 commands, 0 falls in Newton and PhysX. Marches at zero command | |
| rough_swing10 | zz-bw | 10-28 17:49 | none | 11999 | Base for steps_v1 | |
| walk_still_v1 | zz-bw | 10-28 21:05 | none | 5999 | 0 steps/s at zero command, survives 0.6 m/s pushes | A1: 24 s then fell; 224 s run, feet came together |
| walk_still_v2 | dl | 10-29 17:23 | walk_still_v1 5999 | 8998 | Feet spacing and vy terms. vx +0.75/-0.58, vy +-0.32, wz +-1.03; feet over 13 cm apart. Earlier 17:20 dir stopped at 6100 | A1, marked proven in runbook, no logged numbers |
| walk_still_v3 | dl | 10-31 12:55 | walk_still_v2 8998 | 13997 | Smoother, `K1_VX_MAX=1.3`. Shove fell standing 100 N 48%, walking 100 N 79% | Never |
| walk_still_v4 | dl | 11-01 16:45 | walk_still_v3 13997 | 18996 | Side shoves up to 100 N. Top vx 1.33. Worst grid cell fell 25% (v3 62.5%). Yaw at +-1.57 command: -0.83/+0.67 (v3 -1.41/+1.16) | Never |
| rough_walk_v1 | dl | 10-29 16:14 | none | 9999 (6400 kept) | Terrain curriculum, pushes 0.7 m/s. Fails at first 4 cm step | Never |
| rough_walk_v2 | dl | 10-29 19:45 | rough_walk_v1 6400 | 16399 | Stairs and slope focus. Base for steps_res_v2 | Never |

## Task layers on a frozen walk base

| Run | Task | Host | Start | Warm start, base | Last ckpt | Result |
|---|---|---|---|---|---|---|
| kick_v1 | Kick | zz-bw | 10-28 18:32 | none, flat_swing10 | 2999 | RTX replay, 3 walk-up goals. Not evaluated like later kicks |
| head_v1 | HeadTrack | zz-bw | 10-28 19:46 | none | 1499 | Sends targets past head joint range |
| carry_v1 | Carry, welded 3 kg | zz-bw | 10-28 19:32 | none | 2999 | Log: goal ~13.5, fell ~2 |
| push_v1 | Push, one robot | zz-bw | 10-28 20:07 | none | 2999 | Log: goal ~15.5. Limits in `docs/push_limits/README.md` |
| squat_v1 | Squat | zz-bw | 10-28 20:19 | none | 5999 | Height error 0.018 m |
| steps_v1_flat | Steps | zz-bw | 10-28 20:27 | none, rough_swing10 | 2999 | Stairs up weak, level 0.25. First steps_v1 dir has no ckpt |
| stand_v1 | Stand | zz-bw | 10-28 20:46 | none | 2999 | Terrain 2.5/5 |
| getup_v1 | GetUp | zz-bw | 10-29 14:12 | none | 5999 | No eval. FSM in deploy, `--sim --getup` test not rerun on final |
| push_ma_v1 | PushMA, 2 robots | zz-bw | 10-29 14:36 | none | 5999 | No eval. 14:32 dir has no ckpt |
| track_v2 | Track | dl | 10-29 15:58 | none | 3999 | No eval |
| carry2_v1 | Carry2, free 1 kg | dl | 10-29 15:58 | none | 5999 | Log: goal ~32, fell ~0.1, box_lost ~0.08 |
| carry_vel_v1 | CarryVel, 0.5-5 kg | dl | 11-01 18:03 | none, walk_still_v4 | 5999 | 20 s eval: 0 falls, 0 drops. Clips: 0 drops in range; 5 kg at 3 m/s drops 7/8 |
| kick_res_v1 | Kick | dl | 11-01 18:03 | none, walk_still_v4 | 5999 | Goal 32.6%, fell 13.1% |
| steps_res_v2 | Steps | dl | 11-01 18:03 | none, rough_walk_v2 | 5999 | Fell 9.2% |
| kick_res_v2 | Kick, gated residual | dl | 11-02 00:00 | none, walk_still_v4 | 5999 | Goal 36.3%, fell 8.0% |
| jump_pilot | Jump | dl | 11-02 00:00 | none | 1499 | Tucks legs: feet 0.41 m vs 0.08 target. MDP replaced after |
| jump_v2 | Jump | dl | 11-02 00:45 | none | 800 | Stopped at 800; at 200: rise 0.09 m, air 0.20 s |
| jump_v3 | Jump | dl | 11-02 00:55 | jump_v2 800 | 6799 | Rise 0.13 m, air 0.26 s, level stuck 0.55 |
| kick_dir_v1 | KickDir | dl | 11-02 01:02 | kick_res_v2 | 11998 | Heading p50 21 deg, p95 124, fell 11.4%. Curriculum stayed at level 0 |
| kick_strike_v1 | KickStrike | zz-bw | 11-02 11:57 | kick_dir_v1 (init script) | 5999 | Heading p50 5.0 deg, p95 43, fell 4.2%. Targets one-sided |
| kick_ma_v1 | KickMA | zz-bw | 11-02 11:46 | kick_dir_v1 (init script) | 5999 | Near-fixed layout: received 0.74, goal 0.004 |
| kick_ma_v2 | KickMA | zz-bw | 11-02 15:14 | kick_ma_v1 | 11998 | Random layout: goal 11.5%, pass and shot 1.9% (1024 envs) |
| kick_ma_v3 | KickMA | zz-bw | 11-02 18:11 | kick_ma_v2 | 17997 | Goal half init, 1 s release fade: goal 23.8%, pass and shot 5.5%, fell_a 7.2%, oob 64.6%. 17:57 dir is the stopped instant-cut run |

## PushIK (2 robots, box to pose, `k1_push_ik`, zz-bw)

| Run | Start | Warm start | Last ckpt | Result |
|---|---|---|---|---|
| push_ik_v1 to v5 | 10-31 12:04-14:11 | none | 200-2000 | All failed. Fixes: success paid after dt and hand-only scaling, adaptive curriculum, std cap 0.6, box 2-5 kg, gamma 0.998. 12:04 run used a limit-cycling IK |
| push_ik_v6 | 10-31 14:40 | none | 4999 | Success 90.2% |
| push_ik_v7 | 10-31 17:33 | v6 4999 | 6998 | 90.4%, tip 5.9%. Isaac PhysX 100% (28 eps), Newton 91.7% (24) |
| push_ik_v8 | 11-01 02:44 | v7 6998 | 9497 | Corner loss: 93.4%, tip 4.7% |
| push_ik_v9 | 11-01 04:23 | v8 | 12496 | Tall boxes 0.71-1.90 m, per-episode DR: 91.4%, tip 8.0%. Needs `K1_PIK_HALF_Z=0.356,0.95` for eval |
| push_ik_v10 | 11-01 15:45 | v8 | 12496 | Two-hand credit, near-goal resets: 95.5%. Both hands still 0.13% |

None has run on a robot. Push deployment findings from the real setup: see next section.

## Push deployment findings (real setup)

To be added from the user's findings on the current Push deployment, with what the current run needs.

## Not trained yet

Kick point cloud teacher, depth student (DAgger), pick up a free box, kick_ma with goals paid only for pass then robot_b.
