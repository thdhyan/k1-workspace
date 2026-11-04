# Runbook: RL lower-body policy on a real K1, driven by the laptop DS4

From everything off (robot and laptop) to the trained leg policy walking the robot with your DS4.
Tested on A1 (2026-10-29) with `walk_still_v1`. **Do not use A2 while someone is working on it.**

Who does what:
- **You** power the robot, put it in Walking mode, spot it, and press the buttons.
- The **laptop** sends the DS4 sticks to the robot over UDP (`mjlab_k1/deploy/pad_udp_send.py`).
- The **robot** runs the policy itself (`k1_gamepad_deploy.py`, on its CPU). Nothing runs over ROS/DDS across Wi-Fi.

## 0. What can be deployed

Only **blind walk bases** from mjlab: their actor reads joint pos/vel, IMU gyro + gravity, last action, command
(225 dims, or 230 with the height command). No height scan, no camera.

| Policy | Local file | Notes |
|---|---|---|
| walk_still_v4 | `models/mjlab_k1/walk_still_v4/model_18996.pt` | fewer falls under shoves than v3 and faster, but weaker midrange yaw in sim; not yet run on a robot |
| walk_still_v3 | `models/mjlab_k1/walk_still_v3/model_13997.pt` | smoother and slightly faster than v2 in sim; not yet run on a robot. `--cap VX VY WZ` raises the speed limits |
| walk_still_v2 | `models/mjlab_k1/walk_still_v2/model_8998.pt` | proven on A1: wider feet, better vy |
| walk_still_v1 | `models/mjlab_k1/walk_still_v1/model_5999.pt` | ran 224 s on A1 |
| flat_swing10 | `models/mjlab_k1/flat_swing10/model_4999.pt` | old, marches at zero command |
| rough_walk_v1 / v2 | `models/mjlab_k1/rough_walk_v1/model_6400.pt`, `models/mjlab_k1/rough_walk_v2/model_16399.pt` | blind actor, sim only so far |

Not deployable with this script: task layers (push/kick/carry/track), old Isaac `models/*.pt`, any rough base
that reads `height_scan` in the actor. If unsure, run it in the sim first (step 3) — the script refuses a
checkpoint whose input size is wrong.

## 1. Laptop: power on and network

1. Boot the laptop and log in.
2. Plug the Ethernet cable from the robotics router into the laptop (`enp2s0`). The NetworkManager
   profile `robotics-lan` gives it `192.168.50.250/24`. Check:
   ```bash
   nmcli -t -f NAME,DEVICE con show --active    # expect robotics-lan:enp2s0
   ip -4 addr show enp2s0                         # expect 192.168.50.250/24
   ```
   Eduroam on `wlo1` can stay connected.
3. (Only if the robot needs internet, e.g. pip installs. Not needed to run a policy.) Re-create the NAT, which is
   lost on every laptop reboot: see `docs/network_robotics_5G_2026-10-26.md`, "Robot internet via laptop".

## 2. Laptop: pair and check the DS4

1. If the DS4 is not yet paired: hold **Share + PS** until the light bar flashes fast, then
   ```bash
   bluetoothctl
   # scan on   -> wait for "Wireless Controller", note its MAC
   # pair <MAC>; trust <MAC>; connect <MAC>; quit
   ```
   Already paired: press **PS** once; the light bar goes solid.
2. Check Linux sees it:
   ```bash
   grep -A1 '"Wireless Controller"' /proc/bus/input/devices
   ```
3. Your user must be able to read `/dev/input/event*`. If step 3 below says no pad found:
   `sudo usermod -aG input $USER` then log out and back in (quick test only: `sudo chmod a+r /dev/input/event*`).

Button map (evdev): **✕ = A = start**, **○ = B = stop**, △ = Y, □ = X. Left stick = vx/vy, right stick X = yaw,
right stick Y = trunk height (height bases only), R3 = height back to stand, D-pad = head.

Hand IK mode: hold **R1** = right hand, **L1** = left hand, both = mirrored. While held the walk command is zero; left stick
moves the hand forward/back and left/right, right stick Y moves it up/down (trunk frame, 0.15 m/s). Release: the hand stays
where it is and walking works again. **L3** = arms back to the default pose. Press L3 before ○: the stock controller takes
over the arms on stop. Needs the current `pad_udp_send.py` and `k1_gamepad_deploy.py` on both sides.

## 3. Laptop: try the policy in sim first (recommended for any new checkpoint)

```bash
cd ~/Projects/booster_ws/mjlab_k1/deploy
POL=../../models/mjlab_k1/walk_still_v2/model_8998.pt
# scripted check, headless: prints tracking per segment, must end with "sim-to-sim OK: no fall"
PYTHONNOUSERSITE=1 uv run --no-project --with mujoco --with torch --with numpy python k1_gamepad_deploy.py --policy $POL --sim
# live with the DS4 in the MuJoCo viewer (add --terrain rough for bumps/stairs/slope/waves); ✕ reset, ○ quit
PYTHONNOUSERSITE=1 uv run --no-project --with mujoco --with torch --with numpy --with evdev \
  python k1_gamepad_deploy.py --policy $POL --sim --pad
```
Run one sim at a time; several in parallel overload the laptop.

## 4. Robot: power on and stand it up (stock Booster)

1. Clear area ≥ 3 m × 3 m, flat floor. Spotter (or harness) ready. Remote charged.
2. Robot on its stand or lying safely, power it on, wait for boot (~1–2 min).
3. With the **K1 remote or the Booster app**, bring it up the normal way: **Damping → Prepare → Walking**.
4. Leave it **standing still in stock Walking mode**, sticks centred. This is the start state.
   Do not start the policy from Damping, sitting or lying: the script refuses when the trunk is tilted
   more than ~60° (gravity z > −0.5) and switches to Damping.

## 5. Laptop → robot: connect and copy the policy

The robot must be on the robotics Wi-Fi. A1 = `192.168.50.82` (A2 .215, A3 .230, B1 .105, B2 .62, B3 .248).
Use the known-good ssh config (the default `~/.ssh/config` gets rewritten):

```bash
alias kssh='ssh -F ~/.ssh/config.good-20261027'
alias kscp='scp -F ~/.ssh/config.good-20261027'
kssh boosterk1.a1 hostname          # must answer; else check Wi-Fi / ping 192.168.50.82
```

Copy the deploy code and the policy (only needed when they changed; same 3 paths every time):
```bash
cd ~/Projects/booster_ws
kssh boosterk1.a1 'mkdir -p ~/k1_mjlab_deploy/deploy ~/k1_mjlab_deploy/src/mjlab_k1'
kscp mjlab_k1/deploy/k1_gamepad_deploy.py boosterk1.a1:k1_mjlab_deploy/deploy/
kscp mjlab_k1/src/mjlab_k1/wbc.py          boosterk1.a1:k1_mjlab_deploy/src/mjlab_k1/
kscp models/mjlab_k1/walk_still_v2/model_8998.pt boosterk1.a1:k1_mjlab_deploy/walk_still_v2.pt
# verify: the checksums must match
md5sum mjlab_k1/deploy/k1_gamepad_deploy.py models/mjlab_k1/walk_still_v2/model_8998.pt
kssh boosterk1.a1 'md5sum ~/k1_mjlab_deploy/deploy/k1_gamepad_deploy.py ~/k1_mjlab_deploy/walk_still_v2.pt'
```
Make sure nothing else is sending joint commands (another deploy, stock teleop scripts):
```bash
kssh boosterk1.a1 'pgrep -af k1_gamepad_deploy || echo none'
```

## 6. Start the DS4 sender on the laptop (terminal 1)

```bash
cd ~/Projects/booster_ws/mjlab_k1/deploy
PYTHONNOUSERSITE=1 uv run --no-project --with evdev python pad_udp_send.py --host 192.168.50.82
```
It prints `Wireless Controller -> udp 192.168.50.82:9870 at 50 Hz ...` and the live stick values. Start it before pressing ✕. Leave it running.
If this sender stops (Ctrl-C, laptop sleep, Wi-Fi drop) for more than 1 s, the robot stops the policy and
goes back to stock Walking.

## 7. Dry run on the robot (terminal 2) — sends nothing to the motors

```bash
kssh boosterk1.a1
source /opt/booster/BoosterRos2Interface/install/setup.bash
cd ~/k1_mjlab_deploy/deploy
python3 k1_gamepad_deploy.py --policy ../walk_still_v2.pt --udp 9870 --dry
```
Torch takes ~20 s to load. Check the printed lines for ~10 s, then Ctrl-C:
- `low_state age` mostly under ~30 ms (spikes to 100 ms are normal on A1),
- `grav` ≈ `[0, 0, -1]` (robot upright),
- moving the DS4 sticks changes `cmd`.

## 8. Real run (terminal 2) — spotter ready

```bash
python3 k1_gamepad_deploy.py --policy ../walk_still_v2.pt --udp 9870 --log ~/run_$(date +%H%M).npy
```
1. Wait for `press A to start (cap vx/vy/wz = (0.5, 0.3, 0.8)), B to stop`.
2. Sticks centred. Press **✕**. The script checks upright, switches the robot to **Custom** mode itself,
   eases the joints from the stock stance to the policy's home pose over 2 s (arms go to the bent-elbow
   pose in front), then prints `ramp done: policy on`.
3. First few seconds: sticks centred — it should stand quietly. Then small stick inputs. Speeds are capped at
   0.5 m/s forward, 0.3 m/s sideways, 0.8 rad/s yaw.
4. Stop: press **○** on the DS4 (or **B** on the K1 remote). The robot goes back to stock **Walking** mode and
   keeps standing on Booster's controller.

Automatic stops:
| Event | Result |
|---|---|
| ○ / K1 remote B / no pad packets for 1 s | stock Walking mode |
| fall (gravity z > −0.5) during ramp or policy | **Damping** (robot goes limp — spotter catch) |
| `/low_state` older than 0.25 s | **Damping** |

Run it detached instead (survives an ssh drop; stop with ○):
```bash
cd ~/k1_mjlab_deploy/deploy && (setsid nohup python3 -u k1_gamepad_deploy.py --policy ../walk_still_v2.pt \
  --udp 9870 --log ~/run.npy > ~/run.log 2>&1 < /dev/null &)
tail -f ~/run.log | tr '\r' '\n'
```

## 9. After the run

- If it fell: robot is in Damping. With the K1 remote: Damping → Prepare → Walking again before the next try.
- Pull the log to the laptop: `kscp boosterk1.a1:run_HHMM.npy ~/Projects/booster_ws/...`
  Columns per 50 Hz step: age, gyro 3, grav 3, rpy 3, q 22, dq 22, target 22, cmd 3.
- Ctrl-C the DS4 sender on the laptop.
- Shut down the stock way (Damping, robot lying or on the stand, then power off).

## Quick troubleshooting

| Symptom | Fix |
|---|---|
| `kssh` hangs / no route | Laptop on `robotics-lan`? Robot on robotics Wi-Fi? `ping 192.168.50.82` |
| sender: `StopIteration` / no pad | DS4 not connected (press PS) or no `/dev/input` permission (step 2.3) |
| robot ignores the pad | sender `--host` wrong IP, or robot not started with `--udp 9870` |
| `not upright: refusing, Damping` | robot was not standing in Walking mode when ✕ was pressed |
| `ChangeMode(3) FAILED` / `booster_rpc_service unavailable` | Booster services not up yet; wait after boot, re-source setup.bash |
| wobble during the 2 s ramp | press ○ before `policy on`; check the stance first in sim |
