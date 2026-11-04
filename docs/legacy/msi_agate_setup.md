# UMN MSI Agate as extra training host (2026-10-27)

Status: SSH config fixed, **not yet logged in** (needs the user). Slurm script drafted, untested.

## 1. SSH diagnosis and fix
- Old `Host agate` had no IdentitiesOnly; the agent held 6 keys, so sshd (low MaxAuthTries) cut the
  connection before password/2FA. No local key is known to be authorised on MSI
  (`~/.ssh/authorized_keys` irrelevant; no msi/umn key exists).
- Server offers: `publickey,keyboard-interactive,hostbased` (probe with PreferredAuthentications=none).
- Fix applied in `~/.ssh/config` (backup `~/.ssh/config.bak-20261027`): `IdentitiesOnly yes`, no IdentityFile,
  `PreferredAuthentications publickey,keyboard-interactive`, plus ControlMaster (ControlPersist 8h) so
  password + Duo is entered once. `User thakk100` is a guess: MSI user = UMN x500 id; change if different.
- `ssh -o BatchMode=yes agate hostname` now fails with a clean "Permission denied" (not "too many failures"), as expected.
- Requires UMN VPN or campus network? MSI login nodes are reachable from the internet with Duo; the probe above connected from the current network.

### Needs the user (interactive, password + Duo)
```
! ssh agate hostname          # enter password + Duo once; keeps a 8h shared socket
```
Optional key login (nothing was generated or uploaded): 
```
! ssh-keygen -t ed25519 -f ~/.ssh/msi_agate -C thakk100@dhyan-LOQ-msi
! ssh-copy-id -i ~/.ssh/msi_agate.pub agate     # after the first login works
```
then add `IdentityFile ~/.ssh/msi_agate` to the agate Host block. Confirm MSI policy allows keys.

## 2. Cluster facts (from MSI web pages; not yet verified on cluster)
| GPU | Partition | VRAM | Walltime | Max nodes |
|---|---|---|---|---|
| H100 (8 nodes x4) | msigpu | 80 GB | 24 h | 4 |
| A100 (23 nodes x4, verified) | a100-4, msigpu | 40 GB | 24 h | 4 |
| A100 (8 nodes x8) | a100-8, msigpu | 40 GB | 24 h | 1 |
| L40S | interactive-gpu | 48 GB | 24 h | 2 |
| A40 | preempt-gpu | 48 GB | 24 h | 1 |
| V100 | v100, msigpu | 32 GB | 24 h | 1 |
- All partitions allow node sharing; 850 GB local SSD scratch per node (228 GB on interactive-gpu).
- Storage: home 200 GB / 1M files; global scratch 40 TB / 13.2M files (use `/scratch.global/$USER`); Tier 1 up to 20 TB.
- Python: `module load miniforge` then mamba (MSI docs). The page says nothing on pip/venv/uv or compute-node internet.
- Not documented on the pages: QOS names, gres names, apptainer/cuda module names, compute-node internet.
  The 2-minute `scripts/msi/hello_gpu.sbatch` answers these (prints GPU, modules, curl to pypi/github/HF/wandb).

## 3. After login: checklist
```
ssh agate 'sinfo -o "%P %G %l %D" | head -30; sacctmgr show qos format=name,maxwall,maxtrespu; groups; quota -s 2>/dev/null; module avail 2>&1 | grep -iE "apptainer|singularity|cuda|miniforge"'
scp -r scripts/msi agate:booster_ws_msi/ ; ssh agate 'cd booster_ws_msi && sbatch hello_gpu.sbatch'
```
If the A100 gres name differs, fix `--gres` in both sbatch files (`gpu:1` works if unsure).
If compute nodes lack internet: build the venv / SIF on the login node (or build the SIF on zz-bw per skill
isaac-training-containers, `scp` it), use `WANDB_MODE=offline`, `wandb sync` later, pre-download HF assets to `$HF_HOME`.

## 4. Training script
`scripts/msi/train_k1.sbatch` (DRAFT): a100-4 1 GPU, 24 h, `--requeue`, `--signal=B:USR1@300`,
resume from newest checkpoint in `/scratch.global/$USER/k1/<RUN_NAME>/logs`, `WANDB_MODE=offline|online`
(key from `~/.wandb_env`), `BACKEND=venv` (uv) or `sif` (apptainer `--nv`). Placeholders to confirm:
mjlab task id (`TASK`), project path `$WS/mjlab_env`, mjlab resume flag, gres name. Per the GPU budget rule
use at most 1 GPU per job until agreed.

## 5. Status
- Done: ssh config, probe, docs research, sbatch drafts.
- Blocked: login (password + Duo), everything cluster-side.

## 6. Verified 2026-10-28 (job 4895255, node aga43)
- Login works (`ssh agate`, login node ahl01). Slurm account `ceyang`. gres `gpu:a100` correct. a100-4 max walltime 24 h.
- Compute nodes: A100-SXM4-40GB, driver 580.178.04, internet OK (pypi, github, huggingface 200; wandb API 404 on bare URL = reachable).
- No module needed: use uv venv in `/scratch.global/$USER/k1`.
