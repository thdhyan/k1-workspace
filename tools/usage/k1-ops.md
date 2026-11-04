Host launchers, training containers and job chains.

```bash
docker/run.sh --task Isaac-Velocity-Flat-K1-Mjlab-v0 --num-envs 4096 --iters 3000   # clones k1-workspace in the container
docker/run.sh --source ...                                                          # bind-mount this checkout instead
```
- `scripts/remote_train.sh`: run an mjlab training (k1-rl-mj) on any SSH host with a CUDA GPU. No host is built in:
  list yours in `K1_HOSTS`.
  ```bash
  export K1_HOSTS="gpu-host-1 gpu-host-2"          # ssh aliases / names; key login required
  scripts/remote_train.sh pick                     # first host with an idle GPU -> "<host> <gpu>"
  scripts/remote_train.sh up Mjlab-PushIK-Booster-K1 --name pik_try1 -- --agent.max-iterations 3000
  scripts/remote_train.sh status pik_try1          # RUNNING / FINISHED, last log lines, GPU use
  scripts/remote_train.sh fetch pik_try1           # checkpoints + log -> $K1_MODELS_DIR/mjlab_k1/pik_try1
  scripts/remote_train.sh stop pik_try1
  ```
  `up` copies the five source libraries to `~/k1_run/<name>/` on the host, builds one shared venv there (third-party
  deps only, rebuilt when they change), and starts `k1-train` in tmux. The host needs python3, tmux and an NVIDIA
  driver. `K1_NUM_ENVS` defaults to 1024 (sized for a 16 GB GPU). `K1_DRY_RUN=1` prints every command without running
  it. Hosts that refuse a key login are skipped; if a host says "Too many authentication failures", put
  `IdentitiesOnly yes` and the right `IdentityFile` for it in `~/.ssh/config`.
- `docker/entrypoint.sh` supports two layouts, set with `K1_LAYOUT`. `workspace` (the default) fetches only
  description, common, utils, runtime and rl-isaac. `legacy` is the old `booster_ws`.
- `apptainer/` holds the Singularity build for hosts without Docker.
- **Legacy, not ported yet:** most `scripts/spark_*_host.sh`, `dl_*_host.sh`, `phase6_env.sh` and
  `dl_k1_teleop_up.sh` still assume `booster_ws` paths and container scripts next to them. Those scripts now live in
  k1-rl-isaac `jobs/`.

Hosts: [docs/ROBOTS.md section 8](https://github.com/thdhyan/k1-workspace/blob/main/docs/ROBOTS.md).
