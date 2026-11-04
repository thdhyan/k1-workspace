# K1: run a leg policy (.pt) from the robot

For someone already SSHed into the robot. Full version, including laptop setup, sim testing and DS4 pairing: `docs/k1_rl_policy_runbook.md` in the booster_ws repo.

## 1. Before you start

- [ ] Flat, clear floor, at least 3 m x 3 m. Spotter ready.
- [ ] Robot **standing still in stock Walking mode** (remote or app: Damping → Prepare → Walking). Sticks centred.
- [ ] No one else is using this robot.
- [ ] DS4 sender running on the **laptop** (below). If its packets stop for 1 s, the robot leaves the policy.

Laptop terminal, leave it running:

```bash
cd ~/Projects/booster_ws/mjlab_k1/deploy
PYTHONNOUSERSITE=1 uv run --no-project --with evdev python pad_udp_send.py --host <ROBOT_IP>
```

| Robot | A1 | A2 | A3 | B1 | B2 | B3 |
|---|---|---|---|---|---|---|
| IP `192.168.50.` | .82 | .215 | .230 | .105 | .62 | .248 |

## 2. Set up the shell and check the robot

```bash
source /opt/booster/BoosterRos2Interface/install/setup.bash
cd ~/k1_mjlab_deploy/deploy
ls -la ../*.pt
pgrep -af k1_gamepad_deploy || echo none
```

`pgrep` must print `none`. If it shows a run, **someone may be using the robot**: find out who before going further. Never run two deploys at once.

## 3. Dry run (sends nothing to the motors)

```bash
python3 k1_gamepad_deploy.py --policy ../<NAME>.pt --udp 9870 --dry
```

Torch takes about 20 s to load. Watch for about 10 s, then press Ctrl-C.

| Line | Good |
|---|---|
| `DDS: /low_state publishers ...` | 1 and 1 |
| `low_state age` | mostly under 30 ms (spikes to 100 ms are normal on A1) |
| `grav` | about `[0, 0, -1]` |
| `cmd` | changes when you move the DS4 sticks |

## 4. Real run

```bash
python3 k1_gamepad_deploy.py --policy ../<NAME>.pt --udp 9870 --log ~/run_$(date +%H%M).npy
```

1. Wait for `press A to start`.
2. Sticks centred, press **✕**. The script switches to Custom mode and eases the joints to the policy's home pose over 2 s.
3. At `ramp done: policy on`, keep the sticks centred for a few seconds. It should stand quietly.
4. Then use small stick inputs. Default limits: 0.5 m/s forward, 0.3 m/s sideways, 0.8 rad/s yaw.

To survive an SSH drop, run it detached instead (stop with ○):

```bash
(setsid nohup python3 -u k1_gamepad_deploy.py --policy ../<NAME>.pt \
  --udp 9870 --log ~/run.npy > ~/run.log 2>&1 < /dev/null &)
tail -f ~/run.log | tr '\r' '\n'
```

## 5. Stop

**Press ○ on the DS4, or B on the K1 remote.** The robot returns to stock Walking.

If you moved the hands with L1/R1, press **L3** first to bring the arms back.

| Event | Result |
|---|---|
| ○, K1 remote B, or no pad packets for 1 s | Stock Walking |
| Fall (gravity z > −0.5) | **Damping: robot goes limp, spotter catches** |
| `/low_state` older than 0.25 s | **Damping: robot goes limp, spotter catches** |

After a fall: Damping → Prepare → Walking on the remote before trying again.

## 6. DS4 controls

| Input | Action |
|---|---|
| ✕ / ○ | Start / stop |
| Left stick | Walk forward/back and sideways |
| Right stick X | Yaw |
| Right stick Y | Trunk height (height policies only). R3 returns to stand |
| D-pad | Head |
| Hold R1 / L1 / both | Right hand / left hand / mirrored IK. Walking is paused while held |
| L3 | Arms back to default pose |

## 7. Which .pt can run

Only blind mjlab walk bases (225 or 230 inputs). The script refuses a wrong input size, but **a matching size does not prove a policy is safe**.

| Policy | Status |
|---|---|
| `walk_still_v2` | Proven on A1. **Use this one by default** |
| `walk_still_v1` | Ran on A1 |
| `walk_still_v3`, `walk_still_v4`, `rough_walk_v1`, `rough_walk_v2` | Sim only so far: test with `--sim` on the laptop first |
| `flat_swing10` | Old, marches at zero command |
| Push, kick, carry, track layers; old Isaac `models/*.pt`; rough bases reading `height_scan` | **Do not run with this script** |

A policy missing from the robot is copied from the **laptop**:

```bash
cd ~/Projects/booster_ws
scp -F ~/.ssh/config.good-20261027 models/mjlab_k1/walk_still_v2/model_8998.pt \
  boosterk1.<robot>:k1_mjlab_deploy/walk_still_v2.pt
```

## 8. Troubleshooting

| Message or symptom | Fix |
|---|---|
| `REFUSING: another /low_state publisher visible` | DDS is crossing robots, so the policy could read another robot's state. Fix that first; do not reach for `--allow-dds-peers` |
| `not upright: refusing, Damping` | Robot was not standing in Walking mode when ✕ was pressed |
| `ChangeMode(3) FAILED` or `booster_rpc_service unavailable` | Booster services not up yet. Wait after boot, then re-run the `source` line |
| Robot ignores the pad | Sender has the wrong `--host` IP, or the script was started without `--udp 9870` |
| Wobble during the 2 s ramp | Press ○ before `policy on` |

Log columns, per 50 Hz step: age, gyro 3, grav 3, rpy 3, q 22, dq 22, target 22, cmd 3.
