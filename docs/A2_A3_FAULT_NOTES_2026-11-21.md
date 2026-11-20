# A2 / A3 hardware fault notes — 2026-11-21

Status: demo/video skipped for the day. `bdb config apply` **skipped** by user decision.
No policy runs on A2 or A3 until the checks below pass. A1 was the only healthy unit.

## Safety

- Power off before touching connectors or covers. Support arms; never let an unpowered robot fall.
- A fall can plausibly cause both classes of fault (yanked harness, loose CAN connector, loosened coupling). Not proven in either case.

## A2 — left elbow pitch unheld (joint index 4)

### What we measured
- From `~/realrun_0704.npy` (41 s of WALK), commanded target vs actual `q`:
  - joint [4] left elbow pitch: target range −0.19…+0.12 rad, actual +0.03…+0.72 rad,
    mean |error| 0.572 rad (33°), max 0.866 rad (50°).
  - all other left-arm joints [2],[3],[5] and right arm [6..9]: mean |error| ≤ 0.038 rad.
  - A1 same joint [4]: mean |error| 0.002 rad under the same gains.
- User report: joint can be rotated by hand with no resistance, including in stock standing mode.

### What we did NOT measure
- **Motor temperature was never read on A2.** Early A2 probe printed only `q`/`dq`;
  the `.npy` log has no temperature field. `check_k1_motor.py` (which reports
  `mode/temperature/lost/tau_est`) was written after A2 was powered off and the
  copy to A2 failed (`No route to host`). So "temperature was correct" is unknown.
- No evidence yet for coupling vs driver vs encoder vs calibration.
  Calibration is unlikely: a wrong zero offset still holds torque, just at the wrong angle.

### Why it looks local, not a whole arm bus fault
A2's other left-arm joints (same CAN channel 7) tracked normally. That points to
one joint/motor/driver channel rather than a full CAN channel loss (unlike A3).

### Next actions (when A2 is powered)
1. Robot in DAMP or stock Walking, arm supported. Run the read-only checker:
   ```bash
   scp -F ~/.ssh/config.good-20261027 \
     ~/Projects/booster_proj/scripts/check_k1_motor.py boosterk1.a2:~/
   ssh -F ~/.ssh/config.good-20261027 boosterk1.a2 \
     'source /opt/booster/BoosterRos2Interface/install/setup.bash; python3 ~/check_k1_motor.py 4 5'
   ```
2. Move joint 4 by hand during the 6 s sample:
   - `q` tracks hand motion → encoder alive; compare `mode`, `temperature`, `lost`,
     `tau_est` against joint 5 (mirror channel) and against A1.
   - `lost` > 0 or `mode` ≠ 0 → driver/comm fault.
   - normal fields but no holding torque → mechanical coupling / motor output.
3. Power off. Inspect the left elbow-pitch flange/coupling bolts and reseat the
   motor/encoder connector. Do not open the gearbox without a service guide.

## A3 — CAN bus fault (head + both arms)

### Evidence
- Boot 07:21: `usb 2-1-port3: config error`; config draft reset to template defaults.
- `device_gateway` log, still active at 07:30:
  - `devhub.cpp:443 Hub0: error(1) arbitration protocol occurred on CAN logical channel 6/7/8 ... lec is ack error`
  - `joint_manager.cpp:250 Read joint failed: can chan = 6` (head yaw/pitch),
    `7` (left shoulder/elbow), `8` (right shoulder/elbow), `lost_cnt` growing into the 100k+.
  - `device_gateway.cpp:953 Publish abnormal robot status ... error_code=-1, is_connected=0`
    for head and left-arm joints.
- All 22 `MotorState` fields were zero (`q=0, temp=0, mode=0, lost=0`) on a read-only probe.
- `booster_rpc_service` advertises ready but `GetStatus` (api_id 2018) hangs.
- `bdb config status`: `State READY, Active yes` — config already active.
- Symptoms match user report: red light, head unresponsive, upper body no holding torque.

### Decision
`bdb config apply` **skipped**. It cannot fix CAN ACK errors, and the draft is
template defaults, so applying could overwrite custom config. Config status is
already READY/Active.

### Next actions
1. Power A3 off, wait ~30 s.
2. Reseat connectors at the device hub / body bus for CAN ch 6 (head), 7 (left arm),
   8 (right arm). Check for loose plugs, bent pins, damaged harness, hub power.
3. Power on; confirm no new errors:
   ```bash
   ssh -F ~/.ssh/config.good-20261027 boosterk1.a3 \
     'grep -hE "ack error|is_connected=0|Read joint failed" /var/log/booster/*/device_gateway/*.log | tail -5'
   ```
   Expected: no new lines. Head responds; arms resist hand movement in stock Walking.
4. If errors persist after reseat → hub board / wiring harness fault; contact Booster support.

## Opening / cabling guide search

- No K1 teardown, service, or cabling guide found in this repo (`docs/`, `libs/*/README*`).
- Web search attempt failed with HTTP 402 (search provider unavailable) — not retried.
- Attempt to search A3's `/opt/booster` and `/usr/share/doc` for manuals failed because
  A3 went offline (`No route to host`) before the command could run.
- Treat physical opening as **not documented here**. Get the guide from Booster support
  before opening covers. External connector reseating is the only step in scope today.

## Deployment/code state (for later, after hardware is fixed)
- `libs/k1-deploy-laptop`: `pad_udp_send.py` supports `--hosts IP [IP ...]`, R3 = trunk-height
  reset, Share/Select = active-robot switch. Pushed `feat/push-ik-web-console` 50f4ae4.
- `libs/k1-deploy-robot`: runner re-arms on Circle stop; X re-engages without restart.
  Falls/stale still Damp + exit. Pushed `refactor/decouple` 3e95983.
- Runner + `walk_still_v2/model_8998.pt` copied to A1, A2, A3; A3 verified 07:20.
- Helper scripts: `scripts/deploy_to_robots.sh`, `scripts/run_single_pad.sh`,
  `scripts/check_k1_motor.py`. All pushed.
- Multi-robot demo (A1 + A3) command, only after A3 passes the CAN check:
  `pad_udp_send.py --hosts 192.168.50.82 192.168.50.230`; runner on each with
  `--udp 9870 --allow-dds-peers --log ~/run_$(date +%H%M).npy`.
