# K1 jump strategies, 2026-11-02

Sim only. Evidence: `docs/eval_jump_pilot.json`, `docs/eval_jump_motor_test.json`, `mjlab_k1/scripts_jump_probe.py`, `mjlab_k1/scripts_jump_motor_test.py`.

## Leg limits: resolved

The URDF read from the real robot, `real_robot/urdf/k1_robot_description.urdf`, matches the training actuators. The repo's vendored `K1_22dof.xml` and `K1_locomotion.urdf` have lower numbers and do not match it. Speed limits are not enforced in sim.

| Joint | Robot URDF, training | Vendored files | Robot URDF speed | Vendored speed |
|---|---|---|---|---|
| Hip pitch | 68 N·m | 30 N·m | 14.66 rad/s | 7.1 rad/s |
| Knee | 112 N·m | 40 N·m | 12.57 rad/s | 12.5 rad/s |
| Ankle pitch | 38.3 N·m | 20 N·m | 17.59 rad/s | 18.1 rad/s |

## Open-loop motor test

Hold a squat for 1 s, then request a set share of the torque limit on hip, knee and ankle pitch until liftoff. No policy and no arm swing. 90 cells, 8 robots each. Height is v^2/2g from trunk speed at liftoff, kept only where tilt at liftoff is under 0.5 rad.

| Torque limits | Best height | Cell | Peak knee / hip speed |
|---|---|---|---|
| Robot URDF | 0.132 m | knee 1.8 (settled 2.0), full torque, lean -0.15, tilt 0.39 | 15.8 / 15.8 rad/s |
| Vendored files | 0.007 m | same cell, tilt 0.15 | 8.0 / 6.4 rad/s |

Limits of this test: a simple torque profile, not an optimum, so it is no upper bound on height. The 0.132 m cell exceeds robot speed limits on knee (15.8 vs 12.57) and hip (15.8 vs 14.66), so it is optimistic. Many cells tipped during the settle, and lean 0.3 fell before launch and 0.15 was mixed.

## Literature

| Work | Robot | Start state | Reference | Takeoff and height reward | Limits model | Result |
|---|---|---|---|---|---|---|
| Olsen et al. 2025 | Quadruped | Random across squat, in-flight, pre-touchdown, landed; deep squats favoured early | None before takeoff; desired joints in air and after landing | Once-per-jump height, plus height predicted from projectile equations | Not extracted | Not extracted |
| Li et al. 2023 | Cassie | Stage 1 jumps at t=0; later stands 1-15 s first | One hand-made animation, weight reduced later | Tracking terms, including foot and pelvis height; impact and torque costs | Not stated | Hardware 1.4 m long, 0.44 m platform |
| Zhu et al. 2025 (abstract only) | Tendon biped | Not read | Not read | Torque-aware reward | Torque limit depends on joint speed | Abstract: meets actuator limits on hardware |
| Soni et al. 2023 | One leg on rail | Not stated | None | Energy gain plus barrier above target height | Velocity penalty | About 0.2-0.24 m for 0.25 m command |
| Guan et al. 2024 | Quadruped | Not read | Not read | Not read | Impedance matching of sim and real | 38 cm, about 85% of trajectory-optimisation height |
| Spraggett 2025 | Bez humanoid | Ready state | AMP on mocap | Imitation only | None | Sim-to-real unsuccessful |

## Decision

1. Add a speed limit to the jump task from the robot URDF, as a torque-speed cap or at least a penalty. Rated peak torque may also not hold at speed; no motor curve found.
2. Start states as Olsen: squat, in-flight on a projectile, pre-touchdown, landed. Deep squats first, then widen. This covers the squat reset and trains landing directly.
3. Reward trunk height, predicted from v^2/2g, with a cost above target. Remove foot clearance. Add left-right symmetry.
4. Drop the frozen walk base during the jump window. Learn absolute crouch-push-land targets; our reasoning, not tested: the walk base was trained to hold a stand and may fight the crouch. The base can take over after landing.
5. Then trajectory optimisation for a height ceiling and a reference, only if RL stalls. Trajectory optimisation gives the physical limit (Guan et al.).
