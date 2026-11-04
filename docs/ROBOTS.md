# K1 fleet: addresses, network and how to control each robot

Current as of 2026-11-04. Gathered from `~/.ssh/config`, `libs/k1-vla/src/k1_chat/fleet.json`, and the runbooks in
[`docs/legacy/`](legacy/): `ROBOTS.md`, `network_robotics_5G_2026-10-26.md`, `k1_rl_policy_runbook.md`,
`k1_push_ik_web_runbook.md`, `k1_push_ik_phasespace_runbook.md`. Commands use the k1-workspace layout (`libs/k1-*`).
The legacy runbooks still use `booster_ws` paths.

> **Safety.** Have a spotter or harness ready. Clear flat floor of at least 3 m x 3 m. Battery above 40% (a robot
> fell at about 15%). Before you start any script, the robot must stand in stock **Walking** mode. To stop:
> **○** on the DS4, **B** on the K1 remote, or **STOP** / Esc in the web tool.

## 1. Fleet

| Robot | SSH alias | IP (robotics_5G) | Firmware | Status |
|---|---|---|---|---|
| A1 "Apollo" | `boosterk1.a1` | 192.168.50.82 | | in use (VLA demo, push-IK default robot a); `fleet.json` still says "out of commission", see the note below |
| A2 | `boosterk1.a2` | 192.168.50.215 | 1.8.1.2-release-02884 | active; do not use while someone is working on it |
| A3 | `boosterk1.a3` | 192.168.50.230 | 1.6.2.2-release.global-02145 | active (push-IK default robot b) |
| B1 | `boosterk1.b1` | 192.168.50.105 | 1.6.2.2-release.global-02145 | active |
| B2 | `boosterk1.b2` | 192.168.50.62 | 1.7.0.7 (old record) | active, identity unconfirmed |
| B3 | `boosterk1.b3` | 192.168.50.248 | 1.6.2.2-release.global-02145 | active |

- SSH: user `booster`, key `~/.ssh/booster_k1`. Something rewrites `~/.ssh/config`. The runbooks use the known-good
  copy: `alias kssh='ssh -F ~/.ssh/config.good-20261027'` and `alias kscp='scp -F ~/.ssh/config.good-20261027'`.
- Every K1 also has `usb_eth0` 192.168.127.101 (internal body bus) and `enP8p1s0` 192.168.13.101 (Ethernet port).
- Robot OS: ROS 2 Humble, Python 3.10. Booster ROS interface: `/opt/booster/BoosterRos2Interface/install/setup.bash`.
- Ports on the robot (`fleet.json`): Studio websocket 51111, RPC 50051, update engine 50052, heartbeat UDP 9000,
  depth SBS HTTP 8090. Ours: policy pad / task UDP **9870**, VLA console **8091**, YOLO + depth service **8092**.
- Note: `fleet.json` (k1-vla package data) has A1 `ip: null, out of commission`. The SSH config, the runbooks and the
  2026-10-28 NAT service record all have A1 at .82, and A1 runs the VLA demo. Fix `fleet.json` when A1's state is confirmed.

## 2. Network

| What | Value |
|---|---|
| SSID | `robotics_5G` (2.4 GHz: `robotics`); password from the lab, not kept in git |
| Subnet / router | 192.168.50.0/24, router 192.168.50.1 (**no internet uplink**; its DNS returns 10.0.0.1 for every name) |
| Laptop (dhyan-LOQ) | `enp2s0` profile `robotics-lan`: 192.168.50.250/24 (the robots' gateway) + static 192.168.123.222 (G1 subnet); internet on `wlo1` (eduroam) |
| Robot DNS | 8.8.8.8, 1.1.1.1 |

Robot internet goes through the laptop by NAT. The laptop side is **lost on laptop reboot**. Re-create it:
```bash
sudo sysctl -w net.ipv4.ip_forward=1
sudo nft add table ip k1nat
sudo nft 'add chain ip k1nat post { type nat hook postrouting priority srcnat; policy accept; }'
sudo nft add rule ip k1nat post oifname "wlo1" ip saddr 192.168.50.0/24 masquerade
# check from a robot: ping -c1 8.8.8.8; curl -sI https://pypi.org
```
`libs/k1-vla/scripts/demo.sh up` does the same. The robot side persists through reboots: on every K1,
`k1-nat-route.service` runs `/home/booster/nat-route.sh` (default route via .250, DNS 8.8.8.8/1.1.1.1).

**Never run DDS over Wi-Fi**: it runs the K1 out of memory. Set this in every laptop terminal that sources ROS:
`export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`.

## 3. Stock control (Booster remote or app)

| Mode | Meaning |
|---|---|
| DAMP | joints soft; safe for transport and shutdown |
| PREP | stands and holds posture (flat ground) |
| WALK | stock walk controller |
| CUSTOM | joint control handed to user code (our scripts switch to it themselves) |
| PROTECT | entered automatically on an anomaly |

Start-up: **Damping, then Prepare, then Walking**. Shut down: Damping with the robot lying or on its stand, then power off.

## 4. RL walk policy driven by the laptop DS4

Code: `libs/k1-deploy-robot/deploy/k1_gamepad_deploy.py` (runner, on the robot) imports `k1_runtime.gamepad_core`
and `k1_runtime.wbc` (`libs/k1-runtime`). On the laptop: `libs/k1-deploy-laptop/deploy/pad_udp_send.py`.
Checkpoint: `~/k1_models/mjlab_k1/walk_still_v2/model_8998.pt` (`$K1_MODELS_DIR`).

**Copy to the robot.** Do this when the code or the policy changed. Replace `R` with the robot's alias. The
script directory is on `sys.path`, so `k1_runtime/` next to it is enough and the robot needs no `PYTHONPATH`
(this layout was checked locally with `--help`).
```bash
R=boosterk1.a1; L=~/Projects/booster_proj/libs
kssh $R 'mkdir -p ~/k1_mjlab_deploy/deploy/k1_runtime'
kscp $L/k1-deploy-robot/deploy/k1_gamepad_deploy.py $R:k1_mjlab_deploy/deploy/
kscp $L/k1-runtime/src/k1_runtime/gamepad_core.py $L/k1-runtime/src/k1_runtime/wbc.py $R:k1_mjlab_deploy/deploy/k1_runtime/
kscp ~/k1_models/mjlab_k1/walk_still_v2/model_8998.pt $R:k1_mjlab_deploy/walk_still_v2.pt
kssh $R 'pgrep -af k1_gamepad_deploy || echo none'   # nothing else may send joint commands
```
Older copies put `wbc.py` in `~/k1_mjlab_deploy/src/mjlab_k1/`. The current runner does not read that file.

**Laptop, terminal 1** (DS4 over Bluetooth). Start it before pressing ✕. If it stops for more than 1 s, the robot
goes back to stock Walking.
```bash
cd ~/Projects/booster_proj/libs/k1-deploy-laptop/deploy
PYTHONNOUSERSITE=1 uv run --no-project --with evdev python pad_udp_send.py --host 192.168.50.82
```
**Robot, terminal 2.** First do a dry run, which sends nothing to the motors. Check that `low_state age` is under
about 30 ms, that `grav` is about `[0, 0, -1]`, and that `cmd` follows the sticks:
```bash
kssh boosterk1.a1
source /opt/booster/BoosterRos2Interface/install/setup.bash
cd ~/k1_mjlab_deploy/deploy
python3 k1_gamepad_deploy.py --policy ../walk_still_v2.pt --udp 9870 --dry
python3 k1_gamepad_deploy.py --policy ../walk_still_v2.pt --udp 9870 --log ~/run_$(date +%H%M).npy   # real run
```
Press **✕** with the sticks centred. The script checks that the robot is upright, switches to Custom, ramps to the
policy pose over 2 s, and prints `policy on`. Speed is capped at vx 0.5, vy 0.3, wz 0.8. **○** returns to stock Walking.

| Automatic stop | Result |
|---|---|
| ○, K1 remote B, or no pad packets for 1 s | stock Walking |
| fall (gravity z > -0.5) during ramp or policy | **Damping** (spotter catches) |
| `/low_state` older than 0.25 s | **Damping** |

## 5. Two-robot box push (PushIK) from the browser

Tool: `libs/k1-deploy-laptop/deploy/push_ik_web.py`, page http://127.0.0.1:8765 (localhost only, no login: it can
command robots). Default robots: a = A1 (.82), b = A3 (.230). Robot code: section 4 copy, started with `--task`.
Full page guide: [`legacy/k1_push_ik_web_runbook.md`](legacy/k1_push_ik_web_runbook.md). Cap calibration:
[`legacy/k1_push_ik_phasespace_runbook.md`](legacy/k1_push_ik_phasespace_runbook.md).

The tool imports `k1_common`, `k1_runtime` and `k1_teleop`. Run it in a venv where `scripts/dev-install.sh` has
been run (see the workspace README, "Set up a dev venv").
```bash
# no PhaseSpace, no robots
cd ~/Projects/booster_proj/libs/k1-deploy-laptop/deploy && python push_ik_web.py --fake
# real caps, nothing sent (do this first). Terminal 1: the tracker
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; source /opt/ros/jazzy/setup.bash
ros2 launch phasespace_ros2 phasespace.launch.py rviz:=false profile:="Dhyan Hat"
# terminal 2: the tool (same two lines first); add --send to command the robots
python push_ik_web.py --head-cap X Y Z --robots 192.168.50.82 192.168.50.230
```
- `Start robot scripts` on the page (or holding triangle on the DS4) starts `k1_gamepad_deploy.py --task` on both
  robots over SSH. The script exits after every stop.
- Execute is refused until all 3 caps are fresh and have a yaw reference, each pose is within 0.30 m and 20 deg of
  the form, and both robot scripts report `waiting`.
- The preview is optional: a missing or timed-out preview is a yellow note, not a blocker (since 2026-11-02).
- Stops: STOP / Esc; the page not polling for 3 s; mocap loss (walk zeroed at 0.25 s, stop at 1 s); either robot
  falling, stopping, or silent for 1.5 s, which stops both.
- Never tested on hardware or with real PhaseSpace input. Local test without hardware:
  `libs/k1-deploy-laptop/tests/e2e_push_ik_web.py` (prints `WEB TEST OK`).

Command-line alternative without the robot-status stop (**a fallen robot does not stop the other one**):
`python -m k1_teleop.push_ik_phasespace --policy ~/k1_models/mjlab_k1/push_ik_v8/model_9497.pt --box-size D W H --head-cap X Y Z --robots 192.168.50.82 192.168.50.230 [--dry]`.

## 6. Voice / VLM agent (A1 "Apollo")

Runbook: [`libs/k1-vla/docs/DEMO_RUNBOOK.md`](../libs/k1-vla/docs/DEMO_RUNBOOK.md). Stand the robot up
(Damping, then Prepare), then run `bash libs/k1-vla/scripts/demo.sh up` on the laptop. It sets up STT on :8090, NAT,
YOLO on the robot :8092, and the agent + console on the robot :8091. Console: http://192.168.50.82:8091/. Start every
command with "Apollo". "Stop" always works: the robot goes to Prepare and chat motion locks.

## 7. Other robot-side tools

| Tool | Where | Doc |
|---|---|---|
| Stereo / walk / rosbag recorders, TF service, stereo watchdog | `libs/k1-deploy-robot/real_robot/` | its README |
| SLAM (cuVSLAM, nvblox, grid map), onboard and on a GPU host | `libs/k1-perception/real_robot/` | [`legacy/k1_slam_runbook.md`](legacy/k1_slam_runbook.md) |
| Camera queries, bag tools, SFTP sync | `libs/k1-data/real_robot/` | its README |
| Fleet dashboard, camera viewer | `libs/k1-web-console/tools/` | its README |

## 8. Remote compute

Training and sim run on any GPU host you have SSH access to; no host is assumed by the code. What each job needs:

| Job | Needs |
|---|---|
| Isaac Lab tasks (`k1-rl-isaac`) | NVIDIA GPU, Isaac Sim + Isaac Lab, or the container from `libs/k1-ops` (Docker or Singularity/Apptainer) |
| mjlab train / play (`k1-rl-mj`) | NVIDIA GPU, mjlab (MuJoCo Warp); x86_64 or aarch64 |
| Mimic retargeting (`k1-mimic`) | NVIDIA GPU, GVHMR / GMR models |
| SLAM container (`k1-perception/real_robot/slam_dl`) | NVIDIA GPU, Docker, on the robot LAN |

Keep your own host list (alias, address, user, GPUs) in `~/.ssh/config`, outside this repo.
