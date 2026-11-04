# Runbook: start the PushIK web debug tool

Browser page for the two-K1 box push: set the scene from the PhaseSpace caps, preview it in sim, execute it on the robots.
Tool: `mjlab_k1/deploy/push_ik_web.py`, page at http://127.0.0.1:8765 (localhost only: it can command robots and has no login).
Cap calibration, trained limits and the stops table: `docs/k1_push_ik_phasespace_runbook.md`.

**Status: never run on hardware or with real PhaseSpace input.** Tested with fake caps and in sim only.

**Day in the PhaseSpace room, network, DS4, staged tests: `docs/k1_phasespace_field_runbook.md`.**

## A. Try it with no PhaseSpace and no robots

```bash
cd ~/Projects/booster_ws/mjlab_k1/deploy
PYTHONNOUSERSITE=1 uv run --no-project --python 3.12 --with torch --with numpy --with pyyaml --with mujoco python push_ik_web.py --fake
```
Open http://127.0.0.1:8765. Drag robots, box and goal in the top view (wheel over one turns it), then press `Preview in sim`.

If port 8765 is taken, add `--port N`. The first `uv run` downloads packages; later ones start in a few seconds.

## B. Real caps, nothing sent to the robots (do this first)

Terminal 1, tracker:
```bash
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST   # never DDS over Wi-Fi: it runs the K1 out of memory
source /opt/ros/jazzy/setup.bash
ros2 launch phasespace_ros2 phasespace.launch.py rviz:=false profile:="Dhyan Hat"
```
Terminal 2, tool. It refuses to start without the `ROS_AUTOMATIC_DISCOVERY_RANGE` line:
```bash
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
source /opt/ros/jazzy/setup.bash
cd ~/Projects/booster_ws/mjlab_k1/deploy
PYTHONNOUSERSITE=1 uv run --no-project --python 3.12 --with torch --with numpy --with pyyaml --with mujoco python push_ik_web.py \
  --head-cap X Y Z --robots 192.168.50.82 192.168.50.230
```
`--head-cap X Y Z` is the measured cap origin in the trunk frame (m, head at zero). It has no default, because its error becomes robot position error. Caps without a reference show "no orientation reference": capture them first (other runbook, section 1).

Without `--send`, Execute runs everything but sends nothing. The top of the terminal output says which mode is on.

## C. Real run on the robots

Same as B with `--send` added. Default robots: A1 (.82) and A3 (.230). Do not use A2 while someone is working on it.

Press `Start robot scripts` on the page (or hold triangle on the DS4). By hand instead, on **each** robot, standing in stock Walking, and again before **each** run because the script exits after a stop:
```bash
source /opt/booster/BoosterRos2Interface/install/setup.bash
cd ~/k1_mjlab_deploy/deploy
python3 k1_gamepad_deploy.py --policy ../walk_still_v2.pt --udp 9870 --task --log ~/push_$(date +%H%M).npy
```
Use harnesses or spotters, a light box and a short goal distance on the first run.

## D. Page steps

1. **Goal**: hold cap 3 where the box centre should end up, turned as it will be on the box. Press `Cap` on the goal row.
2. **Box**: fix cap 3 on the box, press `Cap` on the box row. Enter size, mass, friction. Mass and friction are your estimates.
3. **Robots**: press `Cap` on each robot row, or type or drag a pose.
4. **Preview**: pick policy and `limit s`, press `Preview in sim`. Press it again while it runs to cancel.
5. **Execute**: tick `spotters ready`, press Execute, confirm. **STOP** or Esc stops both robots.

`limit s` (default 180, range 10-600) is the sim time the preview may push before it counts as `timeout`. It costs only wall time, and it is unrelated to the 30 s training episode. A longer limit lets you see whether a slow run finishes. The real run has no time limit: it ends on success, a stop, or mocap loss.

Execute is refused unless all 3 caps are fresh and have a yaw reference, and each live pose is within 0.30 m and 20 deg of the form (2026-11-02: the preview is optional). The page lists the reasons. A missing, timed-out or outdated preview shows only as a yellow note.

After a run ends (success, STOP, timeout), the robot script fades over 2 s (`FADE_S`) from the last arm pose, height and head back to the walk base with zero velocity, then hands over to stock Walking. A fall or stale state during the fade goes to Damping.

Each robot reports its state at 5 Hz. A fall or stop on one stops the other; 1.5 s of silence does too. Stay ready on STOP anyway. The page going away for 3 s also stops them.

Execute is also refused unless both robot scripts report `waiting` (with `--send`).

**Track live** (bottom of the top view) copies the live robot and box poses into the form every 0.1 s, so the form and 3D scene follow PhaseSpace. Untick it before Preview, or the form drifts from what was previewed. Ticking it switches the 3D view to live.

In the live 3D view the box follows the box cap in full 3D (tilt and yaw). The cap is taken as the top-face centre, and the box is drawn from the h x w x l in the form.

**Walk to box** (no policy, no push, added 2026-11-02): robot a walks on the live caps to `stop at` m from the box centre and faces the box centre, arms at home, then the run ends (stock Walking).
- Side `push` stands on the side away from the form's goal; side `nearest` stands on the side facing the robot now.
- Laptop P-controller in `push_ik_web.py`: it turns first while the heading is more than 0.8 rad off. Speed caps are 0.30 m/s forward, 0.15 m/s back and sideways, 0.5 rad/s. The walk speed floor is 0.08 m/s.
- Arrives at 6 cm and 8 deg. Times out after 60 s.
- Refused if the straight path would cross the box (box half diagonal + 0.2 m): drive around it with the DS4 first.
- Same stops as Execute: STOP, mocap, page gone, robot status. Needs the robot script `waiting` and `spotters ready`.
- The white dotted robot in the top view is the target.
- Tested only in a kinematic model and with fake caps, not on the real walk base.

## E. Trouble

| Symptom | Cause, fix |
|---|---|
| `export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST first` | Set it in that terminal |
| `--head-cap is required` | Add the measured offset, or use `--fake` |
| `cap 'x' not tracked` | Cap out of view, or tracker not running |
| `no orientation reference` | Capture the cap reference (other runbook, section 1) and rebuild `phasespace_ros2` |
| `preview ended in timeout` (note) | Not at goal within `limit s`. Warning only, does not block Execute |
| `moved ... from the form` | Live pose more than 0.30 m / 20 deg from the form: press Cap or tick Track live |
| `no scene from the page yet` | Server restarted: reload the page |
| Policy missing from the list | Its checkpoint is not in `models/mjlab_k1/` |

Test without hardware: `cd mjlab_k1/test`, then run `test_push_ik_web.py` with the same `uv run` line. It should print `WEB TEST OK`.
