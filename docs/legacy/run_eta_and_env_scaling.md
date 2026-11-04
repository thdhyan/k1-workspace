# ETA for a 20-25 h run, and what more environments actually buy

**Date:** 2026-10-02 · **Host:** zz-bw `cs-zhang-net-01`, GPU 1 (RTX PRO 6000 Blackwell, 97 887 MiB)

## Short answer

- **Without video** the run is already video-free (the recorder is opt-in behind
  `--video_during_training` since `f941d15`). Nothing to remove.
- **20-25 h buys ~4 000-5 000 iterations at 4 096 envs**, which is *the same
  iteration count as the 5 000-iteration run that just failed 8/8 gait gates*.
  So the honest framing is: this budget buys **one more shot at the new
  phase-locked stride term**, not a guaranteed walking policy.
- **Raising env count buys samples/hour, not iterations.** The GPU is at
  **4-15% util and 6.5 of 97 GB used** — we are not compute-bound, we are
  under-filling the card.

## Measured throughput (no video, GPU 1)

| config | collection | GPU mem | GPU util |
|---|---|---|---|
| 4 096 envs, `--video` **on** | 21 → 23 s/iter (degrading) | — | 4-13% |
| 4 096 envs, `--video` **off** | **0.85-1.14 s/iter** (smoke) | 6.5 GB | 4-15% |
| 4 096 envs, `--video` off, full env | **11.8 → 17.6 s/iter** (climbing) | 6.5 GB | 4-15% |

The video cost is **~25x**, and it is paid on every step, not just the ~200 a
clip covers: `render_mode="rgb_array"` makes the renderer capture every control
step. Fixed in `f941d15`.

## The unaddressed problem: collection time climbs

At 4 096 envs with no video, collection time over the first 20 iterations:

```
11.8  11.9  12.0  12.1  12.6  13.3  13.7  14.8  15.3  15.7  16.5  17.6
```

This is **not** the video flag and **not** my changes — the pre-existing
`gaitfix_teacher2` run showed the same 15.5 → 26.5 s climb on unmodified code.
Three candidates, none yet isolated:

1. **Terrain curriculum.** `terrain_levels` advances robots to rougher tiles, and
   rougher terrain means more collision pairs. `max_init_terrain_level=0`, so this
   should be near its floor early — worth checking what level it has reached.
2. **Episode length growth.** Resets are cheap; as the policy survives longer,
   fewer envs reset. Should make it *faster*, not slower, so this is unlikely.
3. **GPU-side fragmentation / a slow leak.** RSS was flat at 14 GB and VRAM flat
   at 6.5 GB when last checked, which argues against it.

An ETA computed from the *current* rate will therefore be optimistic. The numbers
below use the worst observed rate (17.6 s) deliberately.

## ETA arithmetic

Fixed per-iteration overhead: learning time is **0.08 s**, so iteration ≈
collection + 0.08.

| target | 4 096 envs @ 17.6 s | env-steps |
|---|---|---|
| 20 h | ~4 090 iterations | 0.40 B |
| 25 h | ~5 110 iterations | 0.50 B |

**This is the crux:** the failed 5 000-iteration run is 0.49 B env-steps. A 25 h
budget at 4 096 envs reproduces it almost exactly, with the new stride term as the
only difference. That is a legitimate A/B, but it is not headroom.

## Why more environments is the right lever

PPO performs one policy update per iteration regardless of env count, so the two
levers are not equivalent:

- **iterations** → number of gradient updates
- **env-steps** → data per update, and wall-clock throughput

At 4-15% GPU util and 6.5/97 GB, the simulation is leaving most of the card idle.
Spending the same hours on more envs trades a few updates for proportionally more
data:

| envs | collection (est) | iterations in 20 h | env-steps in 20 h |
|---|---|---|---|
| 4 096 | 17.6 s | 4 090 | 0.40 B |
| 8 192 | ~20 s | 3 600 | **0.71 B** |
| 16 384 | ~26 s | 2 769 | **1.09 B** |

Doubling envs costs *less* than 2x per iteration because there is fixed per-step
overhead, so env-steps per hour rises. At 16 384 the run gets **2.7x the data of
4 096** for a ~32% loss of updates.

The caveat: env counts above 4 096 are **estimates, not measurements** — the A/B
that would confirm them was still running when this was written. If the
per-iteration cost turns out to scale linearly, the env-step advantage largely
disappears and 4 096 is the better setting.

## Recommendation

**8 192 envs.** It captures most of the data-per-hour win (0.71 B vs 0.40 B) while
keeping ~3 600 policy updates, only ~12% fewer than the 4 096 setting. 16 384
buys more data still, but giving up a quarter of the gradient updates is a bad
trade for a task where the policy is not yet walking — early in learning,
update count matters more than sample count.

Set `max_iterations` from the time budget, not from a number:

```
20 h at 8 192 envs ~ 20 s/iter  ->  3 600 iterations
```

Then **gate at 1 500 and 3 000 iterations** with `gait_gate.py`, not at the end.
The stride term is unvalidated; if cadence/stride have not moved by 1 500
iterations, the remaining budget is better spent on the fix than on the run. The
run saves checkpoints periodically, so it can be evaluated without waiting.

## Two caveats that outrank all of the above

1. **The 4 m/s curriculum has still never fired.** Its gate needs upright ≥0.80
   sustained, and the measured upright ratio is ~0.02-0.15. Whatever iteration
   budget is chosen, the top speed range remains untested until that gate opens.
2. **zz-bw is heavily contended** — load average 58 on 64 cores, 23-24 users, and
   SSH resets several times per attempt. Every remote call needs a retry loop. All
   throughput numbers above are from a *shared* box and will improve on an idle
   one.