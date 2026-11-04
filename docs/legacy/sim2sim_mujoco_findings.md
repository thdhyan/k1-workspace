# K1 sim-to-sim (Isaac PhysX → MuJoCo) failure — findings 2026-10-23

Context: `/Storage/Projects/duck_walk_sim/scripts/run_sim.py` ran `models/k1_velocity_student_gaitfix.pt`
in MuJoCo and every policy collapsed. That report blamed physics only ("obs layout verified correct").
The obs/action wiring was **not** correct. Evidence and A/B scripts were run on the laptop
(single K1, CPU MuJoCo).

## Wiring bugs (fix before judging physics)

1. **Joint order is wrong — also in the real-robot node.** Isaac Lab resolves
   `joint_names=K1_LEG_JOINTS` (no `preserve_order=True`) to *articulation (BFS) order*:
   `[L_Hip_Pitch, R_Hip_Pitch, L_Hip_Roll, R_Hip_Roll, L_Hip_Yaw, R_Hip_Yaw,
     L_Knee, R_Knee, L_Ankle_Pitch, R_Ankle_Pitch, L_Ankle_Roll, R_Ankle_Roll]`.
   Proof from `isaac_tasks/k1_velocity/videos/p2_gaitfix_5k_trace.npz` obs[12:24] ranges:
   only idx 6,7 have min ≈ 0 (knee limit [0, 2.23]); idx 8,9 hit −0.85 (ankle-pitch limit −0.87);
   idx 4,5 clip at ±1.01 (hip-yaw ±1); idx 3 reaches −0.55, impossible for a knee in the
   `[L×6, R×6]` order. `run_sim.py`, `docs/policy_io_reference.md`,
   `src/k1_locomotion/k1_locomotion/locomotion_node.py` (`LEG_JOINTS`), `k1_wbc`, `k1_control`
   all use `[L×6, R×6]`. **Do not deploy any leg policy on hardware until this is fixed.**
2. **Action scale**: cfg uses `scale=1.0` since `5d5af78` (2026-09-27); run_sim defaults to 0.25
   (stale `policy_io_reference.md`).
3. **Gains**: gaitfix student (file 2026-10-01 20:15) predates `8e019b2` (2026-10-01 22:46), so it
   trained with the hand-tuned override (hip pitch/roll/knee kp 100 kd 5, hip yaw 60/3, ankle pitch
   100/5, ankle roll 35.69/4.26, ankle armature 0.0565 both). run_sim used manufacturer gains (3–5× softer).
   Match gains to the checkpoint's commit, not to HEAD.
4. **Delay units**: `DelayedPDActuator` min/max_delay are *physics* steps (5 ms → 10–40 ms);
   run_sim buffers *control* steps (40–160 ms).
5. **History init**: Isaac `CircularBuffer` fills all 10 slots with the first obs; run_sim zero-pads
   (projected gravity = 0 for 9 frames).
6. **Unthrottled policy** in `build_scene` settle and the `--png` path (policy at 500 Hz, clock 10×).
7. **Contacts**: duplicate ground plane (`<prefix>_ground` from K1 XML + scene floor) → doubled
   contacts; post-compile masking enables the foot *visual mesh* (no convex hull built → falls
   through floor) plus the box. K1 XML `impratio=10`/`timestep=0.001` dropped on attach.

Stacking check: term-major (oldest→newest) confirmed — replaying Isaac frames term-major gives
corr 0.58 with recorded actions, frame-major ≈ 0.

## A/B result (box feet, 20 s, cmd 0.3 m/s)

| fixes | falls after start |
|---|---|
| original | ~1.3 s |
| + BFS order + scale 1.0 + delay + hist fill | ~1.3 s |
| + training-time gains/armature | ~1.7–2.5 s |
| same, scale 0.25 | never (stands, no walk) |

Wiring fixed, it still falls: the gaitfix student is a known 6–8 steps/s shuffle (HANDOFF
2026-10-02: 11 mm strides, hip yaw parked near −1 rad) that leans on PhysX contact; such a gait
does not survive a different contact model. Hence Newton (MJWarp) became the default training
backend (`sim_backend.py`, 2026-10-23): train and validate on the same solver family.
