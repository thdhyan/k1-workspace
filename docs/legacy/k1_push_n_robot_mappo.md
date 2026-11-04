# One policy for N robots: MAPPO architecture for box push

Status: design, 2026-11-01. Nothing below is trained. Goal: train once, load the same weights on any N robots, no model change.

## What exists today

`Mjlab-PushIK` (and `PushMA`) is MAPPO-style CTDE with parameter sharing, on the single-agent rsl-rl runner (`mjlab_k1/marl.py`, `SharedActorModel`):
- N robots are packed in one env row. One MLP runs on each agent's slice. Team log-prob is the sum. Reward is shared.
- The critic is a plain MLP on the full state.

Three things pin it to N = 2:

| Blocker | Where |
|---|---|
| Actor obs has exactly one mate slot (xy + heading) | `tasks_push_ik.py`, actor obs |
| Critic input size grows with N | `marl.py`, critic MLP on concatenated state |
| Fixed agent entities in the scene, and a fixed action and obs width per env | `tasks_push_ik.AGENTS`, `num_agents` |

`Mjlab-Push` (one robot) is plain PPO, not MAPPO.

## Design

**Actor: permutation-invariant mate encoder.** Same weights for every robot and every N.

```
self obs (box, goal, half sizes, last action, 5-step history) ----------------+
                                                                              +--> MLP --> walk cmd, hand goals
each mate (xy, heading in my frame, 5-step history) --> phi MLP --> mean pool + max pool
```
- No mates (N = 1): pool outputs a learned "alone" vector.
- Use mean + max rather than sum, so the input scale does not grow with N.
- Deep Sets first. It is the smallest change, about 15 lines in `SharedActorModel`. Move to attention only if success stalls at N >= 3, because ONNX-free deploy of the MLP path stays simple and `push_ik_core.py` needs only the pool added.

**Critic: same pooling on full state.** Team value from box state + pooled per-robot state (true hands, velocities). Size is independent of N.

**Env: fixed maximum, active mask.** MuJoCo Warp needs one model per batch, so build `N_MAX` robots (start at 4) in every env and sample active N per env at reset.
- Inactive robots park outside the field, with collisions off and base held, costing few solver contacts.
- Obs for parked mates are masked out of the pool. Actions and log-probs for parked robots are zeroed in the team sum.
- PPO stays valid: the team log-prob and entropy are sums over active agents only.
- Cost: every env simulates `N_MAX` robots whatever the sample. Expect steps per second to fall by roughly `N_MAX / 2` against v10 (not measured).

**Reset and task.** Robots start along the push face, spaced to fit. Box width range scales with N so that all can reach: about 0.41 m of face per robot, from the two-hand estimate in `docs/k1_push_ik_reset_strategy.md`. Mass range also scales with N (per-robot force limit, see `docs/push_limits/`).

**Curriculum.** Start from v10 weights at N = 2, then sample N in {1, 2, 3, 4} with weights that shift toward large N as success rises. A failed episode at N does not lower the other Ns: keep one success rate per N.

## Transfer from v10

v10's actor takes the mate as raw inputs, so weights do not copy directly into a pooled actor. Two options:
- Distill v10 at N = 2 into the new actor (supervised, fast). **Chosen.** Gives a working start and tests the encoder before any RL.
- Train from scratch at about 5000 iterations per N, slower.

## Deploy

`push_ik_phasespace.py` and `push_ik_web.py` hardcode two robots. They need: list of robot caps, per-robot UDP, pooling in `push_ik_core.py`. PhaseSpace needs one more cap per robot. The robot-side script is unchanged.

## Steps and acceptance

1. Pooled `SharedActorModel` and critic, unit test: output unchanged when mates are permuted; same weights run with 0, 1 and 3 mates.
2. Distill v10 at N = 2. Pass: success within 3 points of v10's 95.5% on the same eval.
3. Env with `N_MAX` and mask. Pass: N = 2 run with two parked robots matches step 2 within 3 points; steps per second measured.
4. RL training with N in {1, 2, 3, 4}. Pass: success at N = 2 not below v10, and a higher maximum movable mass at N = 4 than at N = 2.
5. Deploy changes, Isaac closed-loop check at N = 3.

## Risks

- Crowding: four robots may not fit one face, so they may need several faces, which raises the assignment problem. Mean pooling carries no robot identity, so symmetric robots can pick the same spot. If it shows up, add a pairwise-distance penalty or an index-free slot term from the box-frame angle.
- `both_hands` stayed at 0.13% in v10, so more robots may add force only through one-handed shoves or shins.
- Mass and size limits for one robot are narrow on `push_v1` (see `docs/push_limits/`), so a mass gain must be measured, not assumed.
