# PushIK: reset strategy and two-hand rewards (2026-11-01)

## Why

v8 in the CPU preview, 10 random scenes: 8 success, 2 timeouts at 0.26 and 0.27 m from the goal, so endings get little practice.
Training smoke of v8 under the v10 rewards: left hand on box 12-31% of steps, right hand 0.3-0.9%, both hands of a robot under 0.1%.

## What the papers do

| Paper | Start states | Stated result | Read how |
|---|---|---|---|
| [OmniReset](https://arxiv.org/html/2603.15789) | 4 offline datasets: reaching, near-object, stable grasp, near-goal. Sample uniformly over the union. No curriculum | PPO scales with envs as reset diversity grows. No numeric ablation of the mix in the part read | Text through Sec. 4.2 |
| [DoorMan](https://arxiv.org/html/2512.01061v1) | Rolling buffer of the 100 latest snapshots (all generalized coordinates) when an env enters a new stage. Reset law sets the fraction from each stage; values not stated | Buffer 100: all stages by about 1700 iters. Buffer 10: over 4000. None: exploration fails | Sec. 2.2 verbatim |
| [BeyondMimic](https://arxiv.org/html/2508.08241) | Motion tracking: start bins sampled by empirical failure rate, reverting to uniform as failures drop | Without it, 3 of 4 motions fail in hard segments after 30k iters | Signal verbatim; formula details from a summary, not checked against the PDF |

## What v10 does

OmniReset-style analytic resets, added to the existing curriculum:
- `K1_PIK_NEAR_FRAC=0.2`: box 0.25-0.7 m from goal, yaw error up to 20 deg, robots squared up at the push face.
- `K1_PIK_FACE_FRAC=0.2`: robots squared up at the face, normal goal distance.
- Near-goal episodes do not count toward the curriculum's success rate, or easy starts would widen the ranges. Eval (`play`) never uses these resets.

Not done, and why:
- DoorMan snapshots: a snapshot would not hold the frozen walk base's history or the arm IK state, so a restored scene would not match what the policy saw. Revisit if analytic resets do not help.
- BeyondMimic sampling: it needs discrete segments of a reference motion. PushIK has none. The nearest analogue is sampling scene types by failure rate: try it later if one scene type dominates failures.

## Two-hand rewards in v10

Obs and actions unchanged, so v10 resumes v8 and deploys the same way. All env-gated; defaults reproduce v8.
- `K1_PIK_ONE_HAND=0.3`: positive push progress and goal credit scale from 0.3 up to 1 with the share of robots with both hands on the box. Losses are not scaled.
- `K1_PIK_BOTH_W=1`: per second, per robot, `exp(-d/0.1)` with d = distance of its farther hand to the box. Distance, because contact alone almost never fires from a one-handed policy.
- Logged: `Metrics/both_hands`, `left_on_box`, `right_on_box`. `scripts_push_ik_eval.py` reports the same.

Limit: two robots side by side need about 0.82 m of face for four hands (lateral 0.33 m each, hands at least 0.08 m from centre), so the narrowest trained boxes (0.8 m) barely fit.

Success criterion: `both_hands_frac` well above the v8 baseline, success rate not below it. 

## v10 result (512 envs, same eval)

| | v8 | v10 |
|---|---|---|
| Success | 92.2% | 95.5% |
| Both hands of a robot on box (share of steps) | 0.12% | 0.13% |
| Left hand on box | 16.3% | 15.6% |
| Right hand on box | 0.34% | 0.51% |
| Fell | 0.6% | 0% |
| Box tipped | 5.3% | 3.7% |
| Timeout | 2.1% | 0.8% |

Near and face resets go with better success and fewer timeouts. **The two-hand criterion failed**: both-hands share did not move, and the policy still pushes with the left hand.
