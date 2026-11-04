Host launchers, training containers and job chains.

```bash
docker/run.sh --task Isaac-Velocity-Flat-K1-Mjlab-v0 --num-envs 4096 --iters 3000   # clones k1-workspace in the container
docker/run.sh --source ...                                                          # bind-mount this checkout instead
```
- `docker/entrypoint.sh` supports two layouts, set with `K1_LAYOUT`. `workspace` (the default) fetches only
  description, common, utils, runtime and rl-isaac. `legacy` is the old `booster_ws`.
- `apptainer/` holds the Singularity build for hosts without Docker.
- **Legacy, not ported yet:** most `scripts/spark_*_host.sh`, `dl_*_host.sh`, `phase6_env.sh` and
  `dl_k1_teleop_up.sh` still assume `booster_ws` paths and container scripts next to them. Those scripts now live in
  k1-rl-isaac `jobs/`.

Hosts: [docs/ROBOTS.md section 8](https://github.com/thdhyan/k1-workspace/blob/main/docs/ROBOTS.md).
