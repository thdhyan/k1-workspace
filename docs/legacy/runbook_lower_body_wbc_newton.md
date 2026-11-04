# Runbook: lower-body WBC (velocity + height) on Newton

Plan, gates and thresholds live in `PLAN_LOWER_BODY_WBC_NEWTON.md`. This file holds the commands. Each step is
`do → check → record`. Fill the **Record** tables as you go and keep the rest unchanged.

Hosts and rules:

- **Training hosts:** only zz-bw GPU0, dl GPU0 and dl GPU1. Render bursts of ≤ 20 min run on zz-bw or lambda GPU0. The laptop is a client and runs only CPU MuJoCo.
- **Reach dl through zz-bw:** `ssh -J zz-bw dl` and `rsync -e "ssh -J zz-bw"`.
- **Laptop Python:** `uv run` only, never base python3.
- **Reporting:** every smoke or eval goes to the HRL deck and Drive folder. Every 3 h of training add a clip and a slide.
  - Deck `1ajV8oRv6RN_PpIYA1ybf643cwmeRmcVMeu0Si5cy2k8`
  - Drive folder `1ZMm2iUQxu5Y1sxLD52Yn1nfrwMpwhf0n`

```bash
WS=/home/thakk100/Projects/booster_ws
ZZ_LOG=/export/scratch/thakk100/k1/logs     # zz-bw logs
DL_LOG='~/k1_logs'                          # dl logs
WALK=Isaac-LowerBody-Walk-K1-v0;  WALK_PLAY=Isaac-LowerBody-Walk-K1-Play-v0
STAND=Isaac-LowerBody-Stand-K1-v0; STAND_PLAY=Isaac-LowerBody-Stand-K1-Play-v0
```

---

## 0. Pre-train code (plan §3, WP A1–A7 + B)

Do not launch anything until every box below is ticked.

- [ ] A1 `preserve_order=True` on the leg action, leg obs and upper obs, plus a test that the resolved order equals `K1_LEG_JOINTS`
- [ ] A2 `policy_meta.json` written on export, plus a round-trip test
- [ ] A3 launchers pin `K1_PHYSICS=newton`:
  - `scripts/k1_launch_hrl.sh` `ENV=`
  - dl `~/run_k1_train_dl.sh` (docker `-e K1_PHYSICS`)
  - zz-bw `~/run_k1_train.sh` (`--env K1_PHYSICS=…`, because `--containall` drops host env)
- [ ] A4 `play_record.py` gets the `--height` pin and the trace keys `command`, `root_ang_vel`, `z_rel`, `upper_q`
- [ ] A4b env flag `K1_FORCE_CURRICULUM=1` (smoke only), which opens the pose, force and squat ramps at it 0
- [ ] A5 `scripts/height_gate.py`
- [ ] A6 `K1_PLAY_CURRICULUM=trained` in the Play cfgs
- [ ] B1–B6 `scripts/mujoco_eval.py`, with the gaitfix regression reproducing the findings A/B
- [ ] A7 commit + push. zz-bw: `git pull` in its clone. dl: rsync.

Check the remote launchers forward the backend. Each command should print a line, and an empty result means A3 is not done:

```bash
ssh -J zz-bw dl 'grep -n K1_PHYSICS ~/run_k1_train_dl.sh'
ssh zz-bw 'grep -n K1_PHYSICS ~/run_k1_train.sh ~/k1_train_tmux.sh'
```

Sync code:

```bash
cd $WS && git push origin main
ssh zz-bw 'cd /export/scratch/thakk100/k1/tmp/booster_ws && git pull --ff-only && git log -1 --oneline'
rsync -az -e "ssh -J zz-bw" --exclude logs --exclude .git $WS/isaac_tasks/ dl:~/k1_run_ws/isaac_tasks/
ssh -J zz-bw dl 'grep -n "\"newton\"" ~/k1_run_ws/isaac_tasks/k1_velocity/source/k1_velocity/sim_backend.py'
```

## T0. Static checks (laptop)

```bash
cd $WS
uv run pytest -q tests/test_physx_gpu_capacity.py tests/test_env_cfg_wiring.py tests/test_import_order.py \
  tests/test_policy_meta.py tests/test_leg_joint_order.py
```

Pass: all green. The baseline before this plan was 84 passed and 6 skipped.

## T1. Smoke: 16 envs, 50 it, Newton

```bash
# walk on zz-bw GPU0
ssh zz-bw "K1_PHYSICS=newton K1_FORCE_CURRICULUM=1 K1_GPU=0 ~/k1_train_tmux.sh lbn_walk_smoke $ZZ_LOG/lbn_walk_smoke.log \
  --task $WALK --num_envs 16 --max_iterations 50 --viz none --video --video_length 200 --video_interval 25"
# stand on dl GPU0 (by hand: k1_launch_hrl.sh has no --max_iterations)
ssh -J zz-bw dl "tmux new-session -d -s lbn_stand_smoke 'K1_PHYSICS=newton K1_FORCE_CURRICULUM=1 K1_GPU=0 \
  ~/run_k1_train_dl.sh --task $STAND --num_envs 16 --max_iterations 50 --viz none > $DL_LOG/lbn_stand_smoke.log 2>&1; echo RUN_RC=\$? >> $DL_LOG/lbn_stand_smoke.log'"
```

Check each log:

```bash
L=$ZZ_LOG/lbn_walk_smoke.log   # or the dl one via ssh -J zz-bw dl
ssh zz-bw "grep -m1 -i 'newton_mjwarp' $L; grep -ci 'nan' $L; grep -i -E 'overflow|nefc|ncon|njmax' $L | head; \
  grep -E 'Learning iteration|Mean reward|RUN_RC' $L | tail -4"
```

| Check | Pass |
|---|---|
| backend banner | `Physics newton_mjwarp` present |
| NaN | 0 |
| MJWarp buffer warnings | none. If present, raise `njmax`/`nconmax` in the solver cfg and redo T1 |
| reward logged 50 its | yes, `RUN_RC=0` |
| clip (`logs/rsl_rl/k1_lower_body_walk/<run>/videos/`) | non-black; robot upright at t=0; feet on ground (not sunk); arms moving (forced curriculum) |

Then write a Drive note and add a slide (Haiku agent) with the result plus a frame.

**Record T1**

| task | host | banner | NaN | overflow | it/s at 16 | clip | note |
|---|---|---|---|---|---|---|---|
| walk | zz-bw/0 | | | | | | |
| stand | dl/0 | | | | | | |

## T2. Throughput sweep (walk, 20 it each)

```bash
for N in 1024 2048 4096 8192; do
  ssh zz-bw "K1_PHYSICS=newton K1_GPU=0 ~/k1_train_tmux.sh lbn_tp$N $ZZ_LOG/lbn_tp$N.log \
    --task $WALK --num_envs $N --max_iterations 20 --viz none"
  # wait for RUN_RC in the log before starting the next N (one at a time on the shared GPU)
done
ssh zz-bw "for f in $ZZ_LOG/lbn_tp*.log; do echo \$f; grep -E 'Iteration time|Computation' \$f | tail -3; done"
nvidia-smi    # on the host, note other users' load at measurement time
```

Pick the largest N where steady s/it ≤ 30, with no overflow warnings and VRAM headroom ≥ 20 %. Use the same N on dl, or measure dl separately if its load differs.

**Record T2** (host zz-bw/0, load: ___)

| N | s/it (it 10–20) | VRAM GB | overflow | pick |
|---|---|---|---|---|
| 1024 | | | | |
| 2048 | | | | |
| 4096 | | | | |
| 8192 | | | | |

## T3 + T4. Training runs

Walk runs on zz-bw GPU0 and stand on dl GPU1, at the N picked in T2 (`$N`).

```bash
# walk (20k it max; runner default max_iterations is 10000 → pass it)
ssh zz-bw "K1_PHYSICS=newton K1_GPU=0 ~/k1_train_tmux.sh lbn_walk $ZZ_LOG/lbn_walk.log \
  --task $WALK --num_envs $N --max_iterations 20000 --viz none"
# stand (8k it)
ssh -J zz-bw dl "tmux new-session -d -s lbn_stand 'K1_PHYSICS=newton K1_GPU=1 ~/run_k1_train_dl.sh \
  --task $STAND --num_envs $N --max_iterations 8000 --viz none > $DL_LOG/lbn_stand.log 2>&1; echo RUN_RC=\$? >> $DL_LOG/lbn_stand.log'"
```

Monitor from the laptop:

```bash
scripts/k1_train_status.sh 'lbn_'
```

Plateau auto-stop runs on each host in its own tmux window. `DEFAULT_KEY` is mean reward:

```bash
ssh zz-bw "tmux new-session -d -s lbn_walk_plateau 'python3 ~/k1_run_ws/isaac_tasks/k1_velocity/scripts/plateau_stop.py \
  --log $ZZ_LOG/lbn_walk.log --window 500 --patience 4 --tmux lbn_walk'"
```

**T3 check at it 500 / 1000 / 2000.** Read these from the log or tensorboard.

| metric | it 500 | it 1000 | it 2000 | pass at 2000 |
|---|---|---|---|---|
| action std (`Policy/mean_noise_std`) | | | | in [0.15, 1.0] |
| `Curriculum/survival` | | | | ≥ 0.5 |
| `Curriculum/gated_iter` | | | | > 0 |
| mean reward | | | | rising |
| `error_vel_xy` | | | | < 0.3 |
| `Episode_Termination/base_orientation` | | | | falling |

When to act:

- Survival < 0.3 at it 1500: stop, have Opus audit the rewards, then have Haiku tune them. Relaunch fresh.
- Std pinned at 0.15 while reward slides: lower the upright-gated penalty ramp end weights. Resume from the best checkpoint, which is allowed because it uses the same backend.
- Reward < 0 after a peak, or episode length halving: stop and roll back to the best checkpoint.

**Resume** (same backend only; never resume a PhysX checkpoint under Newton). `--load_run` is relative to the clone.

```bash
... --task $WALK --num_envs $N --resume --load_run <run_dir_name> --checkpoint model_<it>.pt
```

**Every 3 h** (cron on the laptop): render a debug clip from the latest checkpoint, upload it to Drive and add a slide. The burst runs on zz-bw GPU0 or lambda GPU0 and must finish in ≤ 20 min, so use the settings that were measured to fit:

```bash
CK=$(ssh zz-bw "ls -t /export/scratch/thakk100/k1/tmp/booster_ws/logs/rsl_rl/k1_lower_body_walk/*/model_*.pt | head -1")
ssh zz-bw "K1_PHYSICS=newton K1_TRAIN_SCRIPT=play_record.py K1_GPU=0 ~/run_k1_train.sh --task $WALK_PLAY --checkpoint $CK \
  --num_envs 4 --steps 250 --panel_video --panel_size 1280 720 --panel_spp 4 --panel_subframes 1 \
  --label 'lb walk newton' --video_out \$HOME/k1_rec/lbn_walk_\$(date +%m%d_%H%M).mp4"
```

## T5. Isaac eval (Newton): S1–S4

Run one trace per H*. The pinned command is a slow walk, and the upper body sits at end-of-curriculum poses.

```bash
for H in 0.55 0.47 0.40; do
  ssh zz-bw "K1_PHYSICS=newton K1_PLAY_CURRICULUM=trained K1_TRAIN_SCRIPT=play_record.py K1_GPU=0 ~/run_k1_train.sh \
    --task $WALK_PLAY --checkpoint $CK --num_envs 64 --steps 1000 --cmd 0.3 0.0 0.0 --height $H \
    --trace_out \$HOME/k1_rec/lbn_eval_h$H.npz"
done
# stand: --cmd 0 0 0, task $STAND_PLAY
scp zz-bw:'~/k1_rec/lbn_eval_h*.npz' /Storage/tmp/lbn_eval/
cd $WS && for f in /Storage/tmp/lbn_eval/lbn_eval_h*.npz; do
  uv run isaac_tasks/k1_velocity/scripts/gait_gate.py $f; uv run isaac_tasks/k1_velocity/scripts/height_gate.py $f; done
```

**Record T5** (ckpt ___)

| H* | xy err | yaw err | \|z−H*\| | falls % | cadence | stride | jerk | gait gate | pass |
|---|---|---|---|---|---|---|---|---|---|
| 0.55 | | | | | | | | | |
| 0.47 | | | | | | | | | |
| 0.40 | | | | | | | | | |
| stand 0.55/0.40 | | | | | — | — | | — | |

## T6. Cross-solver check (PhysX Play, robustness signal)

This is the T5 command with `K1_PHYSICS=physx`. Record the falls ratio PhysX/Newton; the target is ≤ 2×. This is a play-only run and needs no resume, so the backend switch is safe.

## T7. MuJoCo sim-to-sim gate (laptop CPU): S5

First export the policy. This writes `.onnx` plus `policy_meta.json` per A2:

```bash
ssh zz-bw "K1_PHYSICS=newton K1_TRAIN_SCRIPT=play_record.py K1_GPU=0 ~/run_k1_train.sh --task $WALK_PLAY --checkpoint $CK \
  --num_envs 1 --steps 1 --export_onnx \$HOME/k1_rec/lbn_walk.onnx"
scp zz-bw:'~/k1_rec/lbn_walk.{onnx,policy_meta.json}' $WS/models/      # LFS-tracked *.onnx
```

Run the harness regression (B6) first. It must reproduce the findings A/B, where the gaitfix student falls at about 1.7–2.5 s:

```bash
cd $WS && uv run isaac_tasks/k1_velocity/scripts/mujoco_eval.py --policy models/k1_velocity_student_gaitfix.pt \
  --meta models/k1_velocity_student_gaitfix.policy_meta.json --regression
```

Then run the full gate:

```bash
uv run isaac_tasks/k1_velocity/scripts/mujoco_eval.py --walk models/lbn_walk.onnx --stand models/lbn_stand.onnx \
  --grid default --upper random --seconds 20 --switch_test --out /Storage/tmp/lbn_mj/
uv run isaac_tasks/k1_velocity/scripts/gait_gate.py /Storage/tmp/lbn_mj/trace.npz
uv run isaac_tasks/k1_velocity/scripts/height_gate.py /Storage/tmp/lbn_mj/trace.npz
```

The pass criteria are:

- 0 falls on every grid cell;
- tracking err ≤ 1.5× the T5 value;
- gait gate PASS;
- the switch test passes with no fall at stand↔walk transitions.

If the gate fails, follow plan §6: open-loop replay, then model diff, then DR fine-tune. Record a clip with the MuJoCo viewer offscreen and post the note and slide.

**Record T7**

| cell group | falls | xy err | yaw err | \|z−H*\| | gait gate | pass |
|---|---|---|---|---|---|---|
| walk, upper default | | | | | | |
| walk, upper random | | | | | | |
| stand, H* grid | | | | | — | |
| switch transitions | | — | — | — | — | |

## T8. Deploy parity (no hardware)

```bash
cd $WS && uv run pytest -q tests/test_locomotion_node_layout.py --meta models/lbn_walk.policy_meta.json
```

The `k1_locomotion` node reads its joint order, scale and gains from the meta, not from constants. Hardware stays blocked until T7 and T8 both pass and the user approves.

## Stop / cleanup

```bash
ssh zz-bw 'tmux kill-session -t "=k1_lbn_walk"'       # exact match: tmux -t prefix-matches
ssh -J zz-bw dl 'tmux kill-session -t "=lbn_stand"'
```

When you stop, copy the best checkpoint plus `params/{env,agent}.yaml` to `models/` (git LFS) and add a line to `PLAN_HRL_CONTROLLER.md` §6.
