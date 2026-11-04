# Runbook: two K1s push a box to a goal pose, with the 3 PhaseSpace caps

**Status: never run on hardware.** Tested only in sim and with fake mocap (see "What has been tested"). First run:
harnesses or spotters on both robots, a light box, low goal distance.

Who does what:
- **PhaseSpace tracker** (laptop) publishes each cap's pose on the laptop's local `/tf`.
- **`push_ik_phasespace.py`** (laptop) runs the shared policy + arm IK at 50 Hz and sends UDP to both robots.
- **`k1_gamepad_deploy.py --task`** (each robot) runs the walk base and the joint commands onboard. No DDS over Wi-Fi.

Caps: `dhyan-hat` = robot a, `dhyan-hat-2` = robot b, `dhyan-hat-3` = box (session profile `Dhyan Hat`).

## 0. Trained limits

| Thing | Range |
|---|---|
| Box full size depth x width x height | 0.4-0.7 x 0.8-1.5 x 0.3-0.6 m |
| Box mass, floor friction | 2-5 kg, 0.3-0.6 (drag <= 29 N; scripted hand pushing stalls above ~35 N, so use a light box) |
| Goal distance | up to 2.5 m, any box yaw (box counts as 180 deg symmetric) |
| Robot speed cap | vx 0.5, vy 0.3 m/s, wz 0.8 rad/s |
| Success | box centre within 0.2 m and yaw within 10 deg |

## 1. Cap calibration (once per mounting)

Orientation comes from a per-cap reference layout (`phasespace_ros2/trackers`, currently empty). Capture needs >= 3 visible LEDs.

1. Fit a cap on robot a's head, head at zero. Stand the robot so its **forward axis points along PhaseSpace +x**.
   ```bash
   cd ~/Projects/Phasespace
   ros2 run phasespace_ros2 tracker --capture dhyan-hat --ref-dir ~/Projects/Phasespace/phasespace_ros2/phasespace_ros2/trackers
   ```
   Repeat for `dhyan-hat-2` on robot b.
2. Fix `dhyan-hat-3` on top of the box, centred. Turn the box so its **depth axis (the short horizontal side) points along +x**, then capture.
3. Rebuild `phasespace_ros2` so the references install.
4. Measure the cap frame origin in the trunk frame (m, x forward, z up), with the head at zero. This is `--head-cap X Y Z`.
   It is required and has no default: **cap position error becomes robot position error**.

The hat must not slip or the head turn: `--task` deploy holds the head at zero.

## 2. Robots

Set up each robot as in `docs/k1_rl_policy_runbook.md` sections 4 and 5: stock Walking, standing, then copy the walk base,
`k1_gamepad_deploy.py` and `wbc.py`. Base used in training: `walk_still_v2`. Start on **each** robot:
```bash
source /opt/booster/BoosterRos2Interface/install/setup.bash
cd ~/k1_mjlab_deploy/deploy
python3 k1_gamepad_deploy.py --policy ../walk_still_v2.pt --udp 9870 --task --log ~/push_$(date +%H%M).npy
```
Default robots are A1 (192.168.50.82) and A3 (.230), because A2 may be in use. Do not use A2 while someone is working on it.

Place the box inside the tracked area with the robots standing about 0.5-1.5 m from it, not touching it or each other.

## 3. Laptop, two terminals

Both need this, so DDS never leaves the laptop (DDS over Wi-Fi runs the K1 out of memory):
```bash
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
source /opt/ros/jazzy/setup.bash
```
Terminal 1:
```bash
ros2 launch phasespace_ros2 phasespace.launch.py rviz:=false profile:="Dhyan Hat"
```
Terminal 2:
```bash
cd ~/Projects/booster_ws/mjlab_k1/deploy
PYTHONNOUSERSITE=1 uv run --no-project --python 3.12 --with torch --with numpy --with pyyaml python push_ik_phasespace.py \
  --policy ../../models/mjlab_k1/push_ik_v7/model_6998.pt --box-size DEPTH WIDTH HEIGHT --head-cap X Y Z --robots 192.168.50.82 192.168.50.230
```
`--dry` runs everything and sends nothing. Do that first: walk the caps around and read the printed commands.

## 4. The run

Press Enter at each prompt:
1. **Goal**: hold cap 3 still at the place the **box centre** should end up, turned the way it will be on the box. Enter latches 1 s of samples.
2. **Mount** cap 3 on the box and arrange robots. Enter checks all 3 caps are tracked and prints the distances.
3. **Start**: spotters ready. Enter starts both robots: 2 s ramp, about 2 s stand, then the policy moves them.
4. It ends by itself on success (box within 0.2 m and 10 deg), or press **Ctrl-C**.

## 5. Stops

| Event | Result |
|---|---|
| Success or Ctrl-C | both robots stock Walking |
| A cap unseen for 0.25 s | walk command zero, arms hold |
| A cap unseen for 1 s | both robots stock Walking |
| A robot over 4.5 m from the goal | both robots stock Walking |
| Laptop or Wi-Fi gone for 1 s | that robot stock Walking |
| K1 remote B on a robot | that robot stock Walking |
| Robot falls | **that** robot Damping |

**This command-line tool is not told when one robot falls or stops: the other keeps pushing. Press Ctrl-C.** `push_ik_web.py` reads robot status and stops both (`docs/k1_phasespace_field_runbook.md`); use that one.

## What has been tested

- `test/test_arm_ik.py`: arm FK against MuJoCo, IK reach, no limit cycle in the hand-goal box.
- `test/check_push_ik_parity.py`: controller inside the training env: obs, commands, height and arm targets match it.
- `test/test_push_ik_node.py`: fake `/tf` -> node -> UDP -> robot packet parser: latch, start, commands, stop on mocap loss.

Not tested: real PhaseSpace input, real robots, `--task` gains on hardware, real mocap latency, the real box's friction.

## Browser tool: see the run in sim, then execute

Start commands and troubleshooting: `docs/k1_push_ik_web_runbook.md`.

`mjlab_k1/deploy/push_ik_web.py` replaces section 3 terminal 2 and section 4. It uses the same UDP protocol and the same stops, and adds two more stops: the STOP button (or Esc), and the page not polling for 3 s during a run.
Sections 1 and 2 still apply: the cap references and `--head-cap` are required for real use.

Terminal 2, with the environment of section 3 (`--send` is what allows Execute to command the robots; leave it off for a dry run):
```bash
cd ~/Projects/booster_ws/mjlab_k1/deploy
PYTHONNOUSERSITE=1 uv run --no-project --python 3.12 --with torch --with numpy --with pyyaml --with mujoco python push_ik_web.py \
  --head-cap X Y Z --robots 192.168.50.82 192.168.50.230 --send
```
Open http://127.0.0.1:8765 (served on localhost only). To try the page with no PhaseSpace and no robots, run `python push_ik_web.py --fake`.

1. **Goal**: hold cap 3 where the box centre should end up, turned as it will be on the box. Press `Cap` on the goal row (1 s average).
2. **Box**: fix cap 3 on the box and press `Cap` on the box row. Enter the box size, mass and friction. Mass and friction are your estimates.
3. **Robots**: press `Cap` on each robot row. You can also type a pose, or drag it in the top view and wheel to turn it.
4. **Preview**: pick the policy and press `Preview in sim`. The page shows the outcome and plays the run in 2D and 3D. Robot end poses are a sim prediction, not an input: the policy only has a box goal.
5. **Execute**: start `k1_gamepad_deploy.py --task` on each robot (section 2), tick `spotters ready`, press Execute and confirm. Restart that script on the robots before each run, because it exits after a stop.

Execute is refused unless all of these hold:
- the last preview ended in success
- the form has not changed since that preview
- all 3 caps are fresh and have a yaw reference
- each live pose is within 0.30 m and 20 deg of its previewed start

Robots report status at 5 Hz; if one falls or goes silent for 1.5 s, the tool stops both. Press STOP if you see trouble first. The preview is CPU MuJoCo with no mocap noise, not the training engine, so a preview success is not a guarantee.

Measured on preview, v8, box 0.5 x 1.2 x 0.4 m, 3 kg, 10 random scenes: 8 success, 2 timeouts at 0.26 and 0.27 m (just outside the 0.2 m success radius). Most box contact is the left hand, with shins second. Commands often saturate the speed cap. Expect one-handed shoving and fast turning, not a flat two-handed push.

Tested: `test/test_push_ik_web.py` (fake caps -> server -> UDP -> robot packet parser: latch, preview, refusals, commands, stop, page gone, mocap loss, stop during settle), and the page in headless Chromium with fake caps. Not tested: real PhaseSpace input to this tool, real robots.
