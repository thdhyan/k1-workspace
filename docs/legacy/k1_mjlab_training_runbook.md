# Runbook: train, evaluate, render and publish a K1 mjlab policy

Example is `kick_ma`; other tasks follow the same steps with their own task name and scripts. To put a walk policy on a robot, use `docs/k1_rl_policy_runbook.md`.

## 1. Rules

- Train only on zz-bw GPU0 or dl GPU0 and GPU1. Other users share these machines. Check `nvidia-smi` and `tmux ls` first.
- Render in 15-20 min bursts on zz-bw GPU0 or lambda GPU0.
- `/Storage` on the laptop has write errors. Fetch to the repo disk and compare md5.
- Laptop python goes through `uv`, never base `python3`.

## 2. Paths and connection

```bash
Z=/export/scratch/thakk100/k1_mjlab      # zz-bw; dl uses ~/k1_mjlab
S="/usr/bin/ssh -o ControlMaster=no -o ControlPath=none -o ClearAllForwardings=yes -o BatchMode=yes"
```

Layout: `$Z/mjlab` (trainer, `.venv`, `logs/rsl_rl/<experiment>/<run>/`), `$Z/mjlab_k1` (tasks and scripts), `$Z/base` (frozen walk bases).

Sync code from the laptop before training. `mjlab_k1/src` has drifted before:

```bash
rsync -a -e "$S" mjlab_k1/ zz-bw:$Z/mjlab_k1/
```

## 3. Train

Copy `scripts/zzbw_kick_ma_v3.sh`, change the run name, iterations and resume target, then start it in tmux:

```bash
$S zz-bw "tmux new -d -s kma3 'bash $Z/zzbw_kick_ma_v3.sh'"
```

Key options: `--agent.max-iterations` counts added iterations on a resume; `--agent.load-run` is a regex on run directories, so a stopped run with the same name can match. Check which run it loaded in the log.

Check progress:

```bash
$S zz-bw "grep 'Learning iteration' $Z/kick_ma_v3.log | tail -1; grep ETA $Z/kick_ma_v3.log | tail -1"
```

Log counts in `Episode_Termination/*` are not success rates. Quote numbers only from the eval in step 4.

## 4. Evaluate

Set this for every script in steps 4 and 5, and run from `$Z/mjlab`:

```bash
export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl K1_KMA_BASE=$Z/base/walk_still_v4.pt K1_BASE_CKPT=$Z/base/walk_still_v4.pt
CK=logs/rsl_rl/k1_kick_ma/<run>/model_<N>.pt
.venv/bin/python ../mjlab_k1/scripts_kick_ma_eval.py $CK 512 $Z/eval_kick_ma.json
.venv/bin/python ../mjlab_k1/scripts_kick_ma_checks.py        # task logic checks, must all pass
```

Other tasks: `scripts_skill_eval.py`, `scripts_kick_spread.py`, `scripts_push_ik_eval.py`, `scripts_jump_probe.py`.

## 5. Render

```bash
.venv/bin/python ../mjlab_k1/scripts_kick_grid_render.py ma $CK $Z/grid9.mp4 20 "kick_ma_vN"   # 9 envs, none picked
.venv/bin/python ../mjlab_k1/scripts_kick_ma_goal_video.py $CK $Z/goal.mp4 512                 # one picked goal
```

State that a picked clip is picked. The goal script prints how many episodes qualified; report that rate with it. Its on-screen label is hard-coded, so edit the policy name before rendering.

Replays must subtract `env.scene.env_origins[i]` from free joints, or robots and ball draw away from the pitch.

## 6. Fetch and verify

```bash
rsync -a -e "$S" zz-bw:$Z/mjlab/$CK models/mjlab_k1/kick_ma_vN/
$S zz-bw "md5sum $Z/mjlab/$CK"; md5sum models/mjlab_k1/kick_ma_vN/model_<N>.pt
```

## 7. Publish

Copy, then compare hashes with `rclone lsjson --hash`.

- Team shared drive: `rclone copy <f> gdrive-thakk100:<folder>/ --drive-team-drive 0AA_Sxypkffa8Uk9PVA --drive-root-folder-id 0AA_Sxypkffa8Uk9PVA`. Append; do not overwrite other people's files.
- Add the result to `docs/k1_trained_policies.md` and `HANDOFF.md`.

## 8. When something goes wrong

| Symptom | Cause and fix |
|---|---|
| Robots or ball missing from video | Origin not subtracted, step 5 |
| Eval loop never ends | Play config has a very long episode; take length from the non-play config |
| Checkpoint will not load | Observation or task changed; warm start through an init script such as `scripts_kick_ma_init.py` |
| Curriculum stays at level 0 | Open on kick_dir_v1; read the level rule and how the metric is averaged |
| File differs after fetch | Written to `/Storage`; fetch again to NVMe |
