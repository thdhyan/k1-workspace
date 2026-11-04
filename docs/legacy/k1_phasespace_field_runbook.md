# Runbook: two K1s and a box in the PhaseSpace room

Written 2026-11-01. **Nothing here has run on hardware or with real PhaseSpace input.** Tested: `test_push_ik_web.py` with fake caps, sim preview and fake robots over UDP. Not tested: a real DS4, the light bar, `ssh` start, real status packets, the DDS guard on a K1, PushIK on any robot.

Other docs: cap calibration and trained limits in `docs/k1_push_ik_phasespace_runbook.md`, page details in `docs/k1_push_ik_web_runbook.md`, single robot deploy in `docs/k1_rl_policy_runbook.md`.

## 0. Real box push: run sheet

Sections 1-8 hold the detail. Do not skip a line or reorder. Stop the day at the first failed check.

**Box:** 0.4-0.7 deep x 0.8-1.5 wide x 0.3-0.6 m high, 2-5 kg, cap 3 fixed at top centre. Drag under 29 N on the floor (trained friction 0.3-0.6); scripted hand pushing stalled above about 35 N. Check with a luggage scale. Tape the goal on the floor. First goal under 1 m.

**People:** one operator with the DS4 and the page. One spotter on each robot, with its K1 remote, from stage 3 on.

| Step | Do | Pass | Fail, stop and |
|---|---|---|---|
| Night before | Section 2: DS4 permissions, copy code to both robots, charge, `WEB TEST OK` | All done | Fix before leaving |
| Network | Section 3 | Laptop 192.168.50.250, PhaseSpace pings, both robots ping. Record worst ping | See section 3 fallback |
| 1. DDS | `ros2 topic info /low_state` on each robot | Publisher count 1 | Do not run both robots |
| 2. Dry | `--dry` on each robot | `/low_state` arrives, policy rate near 50 Hz | Read `~/push.log` |
| 3. Pad only | `--no-mocap --pad --send` | Each robot moves only when selected. `gap` under 500 ms. B on one remote stops the other within 0.5 s. Pulling the pad stops both | Do not add caps |
| 4. Caps | `--capture` per cap, tape `--head-cap`, rebuild | Yaw reads non-zero | Execute stays refused |
| 5. Caps, no send | Without `--send`, walk the caps for several minutes | Poses and yaw match the floor. Cap age rarely over 0.25 s | Use wired PhaseSpace link |
| 6. No box | `--send`, box cap on a stand, goal about 1 m | Both walk to the spot, arms move, Share takes over at once. End with ○ | Share, then ○, read `~/push.log` |
| 7. Light box | 2 kg, goal under 1 m, policy v10. Preview must succeed before Execute | Box moves toward goal, robots stay up | Back to stage 6 |
| 8. Full | Up to 5 kg, goal up to 2.5 m | Box centre within 0.2 m and 10 deg | Back to stage 7 |

**During a run:** Share = manual at once. ○ = stop both. Before each new run, robots stand in stock Walking and hold △ again, because the script exits after a stop.

**Keep from every run:** `~/push_*.npy` from both robots, the page's `gap` and cap age, an external camera video, box mass and pull force, outcome. No hardware result exists yet, so these are the first real numbers.

**Expect:** one-handed shoving, not a two-hand push: both hands touch 0.13% of the time in sim. v10 has 95.5% success in sim only. The base is `walk_still_v2`, and only A1 has run it on hardware.

## 1. How it fits together

```
PhaseSpace server  --eduroam, wlo1-->  LAPTOP  --enp2s0, Ethernet-->  ROUTER  ~~robotics_5G~~>  robot a, robot b
cs-phasespace.cs.umn.edu                 |                                                      each runs walk_still_v2 onboard
                                         +-- tracker (ROS, localhost only)
                                         +-- push_ik_web.py: page, push policy, arm IK, DS4
```

- **Robots do not talk to each other.** Each one gets a UDP packet from the laptop at 50 Hz on port 9870: walk command, height, arm targets. Each sees its mate only through the mocap on the laptop.
- **Robot to laptop:** a status packet at 5 Hz, carrying state, reason, gravity z and longest packet gap. If one robot falls or stops, the laptop stops the other.
- **No DDS over Wi-Fi.** It ran a K1 out of memory before. ROS stays on localhost on the laptop and onboard on each robot.
- **Only one sender per robot.** `pad_udp_send.py` next to the web tool makes the robot see start and stop presses at once. The DS4 is read by the web tool for this reason. Do not run `pad_udp_send.py` during this work.

## 2. Before you leave (at home or in the lab)

Bring: router and its power, Ethernet cable, both robots with remotes and charged batteries, DS4 and USB cable, 3 caps, tape measure, harnesses, light box, floor tape.

**Why bring the router:** the robots keep their IPs and Wi-Fi, so nothing needs reconfiguring. The laptop's card cannot be on eduroam and run a good hotspot at once: both would share one channel, and the robots would get new IPs.

1. Let the laptop read the DS4 and write its light bar, then log out and back in:
   ```bash
   sudo usermod -aG input $USER
   sudo tee /etc/udev/rules.d/99-ds4-light.rules <<'RULE'
   ACTION=="add", SUBSYSTEM=="leds", KERNEL=="input*:rgb:indicator", RUN+="/bin/chmod a+w /sys/class/leds/%k/multi_intensity /sys/class/leds/%k/brightness"
   RULE
   sudo udevadm control --reload
   ```
2. Pair the DS4 (hold Share + PS until it flashes, then `bluetoothctl`: `scan on`, `pair`, `trust`, `connect`), or use the USB cable.
3. Copy the code to **each** robot. It changed, so this is required. For A1, then repeat for the second robot (`boosterk1.a3`):
   ```bash
   cd ~/Projects/booster_ws; alias kssh='ssh -F ~/.ssh/config.good-20261027' kscp='scp -F ~/.ssh/config.good-20261027'
   kssh boosterk1.a1 'mkdir -p ~/k1_mjlab_deploy/deploy ~/k1_mjlab_deploy/src/mjlab_k1'
   kscp mjlab_k1/deploy/k1_gamepad_deploy.py boosterk1.a1:k1_mjlab_deploy/deploy/
   kscp mjlab_k1/src/mjlab_k1/wbc.py boosterk1.a1:k1_mjlab_deploy/src/mjlab_k1/
   kscp models/mjlab_k1/walk_still_v2/model_8998.pt boosterk1.a1:k1_mjlab_deploy/walk_still_v2.pt
   ```
4. Dry test: `cd mjlab_k1/test`, then the `uv run` line from section 4 with `python test_push_ik_web.py`. It must print `WEB TEST OK`.

**Which robots.** Default `--robots` is A1 (.82) and A3 (.230). Only A1 has run the walk base so far. To use others, pass their IPs (A2 .215 only if nobody else is on it; B1 .105, B2 .62). A1 has no static IP: check it with `/robot-discover` or the router if .82 does not answer.

## 3. Network in the room

1. Plug in the router, Ethernet from router to laptop `enp2s0`. No internet is needed on that side.
2. `nmcli con up robotics-lan`, then `ip addr show enp2s0` must show 192.168.50.250/24.
3. `wlo1` on eduroam, with VPN off. `ping cs-phasespace.cs.umn.edu` must answer.
4. Power on the robots, stand them in stock Walking. `ping -c 20 192.168.50.82` and the same for the other robot. Earlier Wi-Fi pings were 24-250 ms, so write down the worst value.

If eduroam does not work there, use a room Ethernet jack for PhaseSpace (`enp2s0` is then taken). Run `wlo1` as a hotspot for the robots, which must be joined to it one by one with new IPs. This path is unplanned and slow, so treat it as a day lost.

**Mocap latency is unknown over eduroam.** The tool zeroes walking after 0.25 s of stale caps and stops at 1 s. Step 7 measures this, before anything can move.

## 4. Laptop commands

Same base for each stage. `U` below stands for:
```bash
cd ~/Projects/booster_ws/mjlab_k1/deploy
PYTHONNOUSERSITE=1 uv run --no-project --python 3.12 --with torch --with numpy --with pyyaml --with mujoco --with evdev python push_ik_web.py
```
With mocap, both terminals first need:
```bash
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; source /opt/ros/jazzy/setup.bash
```
Tracker terminal: `ros2 launch phasespace_ros2 phasespace.launch.py rviz:=false profile:="Dhyan Hat"`.

Page: http://127.0.0.1:8765. **Keep it open during any run, also manual: if it stops polling for 3 s, both robots stop.**

## 5. DS4

**Selection stays until you change it.** It starts on robot a. Sticks only reach the selected robot. The other gets zero. Sticks self-centre, so letting go means zero.

| Input | When | Does |
|---|---|---|
| **○ Circle** | any time | Stop both, to stock Walking |
| **Share**, press | during a run | Manual takeover at once: walking zero, arms and height stay where they are |
| **Share**, hold 1 s | nothing running | Both robots start in manual, no policy |
| **Options**, hold 1 s | ready | Start the policy, same checks as Execute |
| **Options**, hold 1 s | in manual | Back to the policy, needs fresh caps. Arms return at 1.5 rad/s |
| **△ Triangle**, hold 1 s | nothing running | Start the robot scripts over ssh |
| **L1**, press | any time | Select robot a |
| **R1**, press | any time | Select robot b |
| **L1 + R1**, press one while holding the other | any time | Select both |
| **Left stick** | manual | Selected robot: forward/back, sideways (max 0.5, 0.3 m/s) |
| **Right stick X** | manual | Selected robot: turn (max 0.8 rad/s) |
| **L2**, hold | manual | Selected robot, left hand by IK. Walking zero |
| **R2**, hold | manual | Selected robot, right hand by IK. Walking zero |
| **L2 + R2**, hold | manual | Selected robot, both hands, mirrored. Walking zero |

While L2 or R2 is held, hand speed is up to 0.15 m/s in the trunk frame:

| Stick | Left hand | Right hand (y mirrored) |
|---|---|---|
| Left stick up / down | forward / back | forward / back |
| Left stick left / right | left / right | right / left |
| Right stick up / down | up / down | up / down |

The hand stays where it is on release. Joint limits and the arm clearance check still apply, as in the robot's own jog. The arm IK runs on the laptop and is sent as arm targets. Under the policy, L2, R2 and the sticks do nothing.

### Light bar

| Light | Status | Selected robot |
|---|---|---|
| Dim white-grey, steady | Not ready: scripts are not waiting, or dry run | - |
| Blue, steady | Ready: both scripts waiting | - |
| Yellow, steady | Settling, 4 s after start | - |
| Green, steady | Policy running | - |
| Orange, steady | Policy, mocap stale: walking zero, arms held | - |
| Cyan, steady | Manual, walking | Robot a |
| Magenta, steady | Manual, walking | Robot b |
| Bright white, steady | Manual, walking | Both |
| Cyan, blinking | Manual, hand IK (L2/R2 held) | Robot a |
| Magenta, blinking | Manual, hand IK (L2/R2 held) | Robot b |
| Bright white, blinking | Manual, hand IK (L2/R2 held) | Both |
| Red, steady | Stopped: reason on the page | - |
| Red, blinking for 1 s | Press refused: reason on the page | - |

Pressing L1 or R1 shows that robot's colour for 0.6 s in any mode, also when idle or under the policy, then the light returns to its status.

Pad disconnecting during a run stops both. The K1 remote B still stops that robot, to Walking, and the laptop then stops the other.

## 6. Stages. Pass each before the next.

Spotter on each robot from stage 3 on. **Stock K1 remote in hand.**

**Stage 1. DDS go/no-go, both robots on.** Never verified: both robots use domain 0 on one Wi-Fi, so a robot's joint commands might reach the other.
```bash
ssh -F ~/.ssh/config.good-20261027 boosterk1.a1 'source /opt/booster/BoosterRos2Interface/install/setup.bash; ros2 topic info /low_state'
```
Publisher count must be 1, on each robot. If it shows 2, stop: do not run both robots. The script also refuses to start in that case (`another /low_state publisher visible`), and the override `--allow-dds-peers` is not for this situation. Try `ROS_LOCALHOST_ONLY=1` for the script, and confirm with `--dry` that `/low_state` still arrives.

**Stage 2. Dry on each robot**, no motors:
```bash
source /opt/booster/BoosterRos2Interface/install/setup.bash; cd ~/k1_mjlab_deploy/deploy
python3 k1_gamepad_deploy.py --policy ../walk_still_v2.pt --udp 9870 --task --dry
```
Check the `DDS:` line and the policy rate.

**Stage 3. One DS4, two robots, no PhaseSpace, no box.** This is the rough test.
```bash
U --no-mocap --pad --send --robots 192.168.50.82 192.168.50.230
```
1. Hold △. The page must show both robots `waiting`, and the light goes blue. Torch takes about 20 s to load.
2. Hold Share. Yellow, robots ramp over 2 s and stand, then cyan (robot a selected).
3. Walk robot a a little: robot b must not move. Press R1, light magenta, and walk robot b: robot a must not move. Stay on small commands until both feel right.
4. Select one robot, hold L2 and move the left stick gently: only that robot's left hand moves, and the light blinks. Then R2.
5. Press ○: both go to stock Walking, and the scripts exit.
6. Read `gap` on the page. Over 500 ms means the Wi-Fi is too poor: the robot stops at 1 s without packets.
7. Stop test: repeat, then press B on one K1 remote. The other must stop within 0.5 s. Pull the DS4 cable or kill the page: both must stop.

**Stage 4. Caps.** Calibrate as in `docs/k1_push_ik_phasespace_runbook.md` section 1: `--capture` per cap, `--head-cap X Y Z` measured with a tape, rebuild `phasespace_ros2`. Yaw reads 0 and Execute refuses until this is done.

**Stage 5. Real caps, sends nothing.**
```bash
U --pad --head-cap X Y Z --robots 192.168.50.82 192.168.50.230
```
Walk the caps around. Confirm that positions and yaw match the floor, and watch cap age on the page for several minutes. If age passes 0.25 s often, the policy will keep stopping. Then use a wired PhaseSpace link if the room has one. Set goal and scene, Preview, Execute: it runs and prints commands, and nothing reaches the robots.

**Stage 6. First policy run: no box.** Add `--send`. Place the box cap on a stand as a stand-in, and a goal about 1 m away. Hold △, then Execute or hold Options. Press Share as soon as anything looks wrong. Expect both robots to walk to the box spot and move their arms. A run with no box should never succeed, so end it with ○.

**Stage 7. Light box, short goal.** Harnesses or spotters. Box in the trained range: 0.4-0.7 x 0.8-1.5 x 0.3-0.6 m, 2-5 kg, goal within 1 m at first (trained up to 2.5 m). Policy v10.

**Stage 8. Full run.** Heavier box, longer goal.

Before each run: the script exits after each stop, so hold △ again. Robots must be standing in stock Walking first.

## 7. What to expect, and known holes

- v10: 95.5% success in sim, **almost always one hand** (both hands on the box 0.13% of the time). Expect shoving, not a clean two-hand push.
- `--task` gains have never run on hardware. Only A1 has run the walk base.
- The status packet is the only fall link to the partner. If it is lost, the partner stops 1.5 s later, on silence. A robot that falls in the 4 s settle only stops the partner when the settle ends.
- Mocap yaw depends on the cap reference. Error in `--head-cap` becomes robot position error.
- Manual ignores mocap, success and the arena limit. Nothing but you stops a robot walking into something.
- Selection is latched, so a stick moves whichever robot is selected. Check the light colour before touching a stick. Selection is not reset between runs.
- Hand IK has an arm clearance check against the robot's own body only. It knows nothing about the box.
- The light bar path assumes the `hid-playstation` driver (`input*:rgb:indicator`). If the page says `bar not writable`, the pad still works, so read the mode from the page.

## 8. Trouble

| Symptom | Cause, fix |
|---|---|
| `robot a: script not answering` | Hold △. Or read `~/push.log` on the robot. Also needs `--send`, because the robot replies only to packets it gets |
| `robot a: exit another /low_state publisher` | Stage 1 failed |
| `no DS4 connected` | Not paired or wrong permissions: run `groups`, it must list `input` |
| `ssh failed` | Key `~/.ssh/booster_k1` or IP. Start the script by hand as in stage 2, without `--dry` and with `--log ~/push.npy` |
| Robot stops about 1 s after start | Packet gaps: see `gap`, move the router closer |
| Stops at once with `mocap lost` | Caps hidden, or tracker down |
| Cap pose fresh (age ms) but lags or stays put while the robot walks | Tracker from before 2026-11-02 read one OWL packet per loop, so the startup backlog stayed as constant lag of seconds. Fixed in `phasespace_ros2/tracker.py`, which now drains the queue and keeps the newest frame (port of `thesis/g1_perception_ws` fix). Restart the tracker if it is old |
