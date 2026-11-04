Isaac Lab tasks. Needs Isaac Sim and Isaac Lab, so run it on a GPU host.

```bash
python scripts/train.py --task Isaac-Velocity-Flat-K1-Mjlab-v0 --num_envs 4096 --headless
python scripts/play.py  --task Isaac-Velocity-Rough-K1-Play-v0 --checkpoint <run>/model_N.pt --num_envs 20 [--export policy.pt]
```
- Task families: `Isaac-Velocity-*`, `Isaac-Push-*`, `Isaac-Carry-*`, `Isaac-Kick-Ball-*`, `Isaac-HeadTrack-*`,
  `Isaac-Basic-*`. The packages are `k1_velocity`, `k1_kicking` and `compass_k1`.
- USD assets come from `k1_description` (`USD_MJLAB*`). Override them with `K1_MJLAB_USD` / `K1_MJLAB_USD_ARMS`.
- `third_party/booster_train` is a submodule (the reference task code).
- Containers and batch jobs: `jobs/*.sh` and k1-ops `docker/run.sh`. `jobs/` still uses the `booster_ws` container
  layout and is not ported yet.
