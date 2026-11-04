mjlab (MuJoCo Warp) tasks. Needs `mjlab` and a CUDA GPU.

```bash
k1-train Mjlab-Velocity-Height-Flat-Booster-K1 --help   # mjlab's train flags
k1-play  Mjlab-PushIK-Booster-K1 --help
```
- `k1-train` / `k1-play` import the K1 tasks, which registers them, then hand over to mjlab's own CLIs. Run
  `k1-train --help` to see the flags.
- Tasks: Velocity-Height-{Flat,Rough}, Stand, Squat, Steps, Jump, GetUp, Track, HeadTrack, Kick*, Push, PushIK,
  PushMA, Carry*.
- Probes and exports are in `scripts/`. There are no tests yet.
