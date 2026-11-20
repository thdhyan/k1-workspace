# Known issues after extraction

Honest list of what the mechanical move did **not** fix.

1. **Not run.** Imports were rewritten and checked with `ruff` (undefined names, syntax); no test suite or training/sim run was executed (needs Isaac, mjlab, ROS, robot).
2. **Corrupt source file.** `k1-rl-isaac/src/k1_velocity/tasks/push/push_things_rewards.py` is all NUL bytes in booster_ws itself (committed that way). Restore it from a backup.
3. **Pre-existing undefined names** (also in booster_ws): `ArticulationCfg` in `k1-rl-isaac/scripts/probe_k1_bodies.py`, `CurriculumCfg` in `k1_kicking/.../kicking_env_cfg.py`.
4. **Hard-coded path strings** into other repos remain (listed per repo README). Step 6 of the plan: replace with arguments / config / `resolve_model()`.
5. **sys.path hacks**: 28 top-level inserts to moved siblings were removed; conditional ones (skrl fork, Isaac overlay, repo-root inserts in `multi_k1_sim.py`, `k1_teleop_sim.py`, `k1m_service.py`, `app.py`) remain.
6. **Split ROS package**: `k1_control` is split between k1-deploy-robot (`sdk_bridge/`) and k1-deploy-laptop; its `setup.py` entry points need updating.
7. **`k1_gamepad_deploy.py` no longer has `--sim`**: use `k1-deploy-laptop/deploy/gamepad_sim.py`. `CAP` is now `gamepad_core.CAP`.
8. **Joint-name lists** (`Left_Hip_Pitch`) still exist as copies in several repos; consolidation into k1-common is plan step 2.
9. **Duplicate**: `k1-vla/tools/depth_sbs_server.py` equals `k1-web-console/tools/k1_camera/depth_sbs_server.py`.
10. **Not copied**: model checkpoints, videos, meshes (booster_assets submodule), `.env`, files >500 KB, vendored JS (three.js in `deploy/push_ik_web/vendor` was kept only if <500 KB), git history. Uncommitted work in booster_ws was copied as is; booster_ws was not modified.
11. **Public-repo hygiene**: no tokens/keys found by regex scan. Private LAN IPs (192.168.x.x), the lab host name `cs-zhang-net-01`, your e-mail in ROS `package.xml` maintainer fields, and `/home/thakk100` paths remain. No LICENSE file was added.
12. graphify: code only (AST). READMEs/docs were not semantically extracted.
13. **A2 left elbow pitch (joint 4)**: unheld / drifts under policy (target ~0 rad, actual +0.03…+0.72 rad, mean err 0.57 rad; A1 same joint 0.002 rad). Temperature/lost/mode NOT measured — the checker was written after A2 was powered off. Do not run policy on A2 until triaged.
14. **A3 CAN bus fault**: `ack error` on CAN ch 6/7/8 (head + both arms), `is_connected=0`, `lost_cnt` increasing, red light, head dead, upper body no torque. `bdb config status` = READY/Active — config is fine; `bdb config apply` skipped (would not fix CAN, risks template-default overwrite). Do not run policy on A3.

Full triage notes: [`docs/A2_A3_FAULT_NOTES_2026-11-21.md`](A2_A3_FAULT_NOTES_2026-11-21.md).
