# K1 onboard SLAM + mapping — runbook

Code: `real_robot/slam_onboard/`. Robot used so far: **A1** (192.168.50.82, ssh `boosterk1.a1`). State as of 2026-10-29.

## What runs where

| Where | Process | Role |
|---|---|---|
| K1 | `k1-tf.service` (systemd, `real_robot/tf_service/`) | URDF TF + odom→trunk. Must be active. |
| K1 | `k1_cuvslam_node.py` (PyCuVSLAM 17.0.1, `~/k1_slam/venv`) | cuVSLAM RGB-D SLAM on the head camera, 12–14 Hz |
| K1 | `k1_slam_relay.py` | TCP :7447 stream of viz topics (serialized CDR) |
| Laptop | `k1_slam_rx.py` | republishes the stream on ROS domain 42, localhost only |
| Laptop | `robot_state_publisher` | robot model from `real_robot/urdf/k1_robot_description.urdf` |
| Laptop | `k1_grid_map.py` | 2-D occupancy map, costmap, collision marker (stand-in for nvblox) |
| Laptop | `rviz2 -d k1_slam.rviz` + `ros2 bag record` | view + recording |

**No DDS across Wi-Fi.** Humble FastDDS on the K1 talking to Jazzy FastDDS on the laptop made whichever K1 process the
laptop read from grow by GBs until a global OOM (killed k1-tf, SLAM, a DDS relay). Keep the TCP relay.

## Start

1. Robot on, walking mode via remote (built-in walking controller). Laptop on the robot LAN (enp2s0 192.168.50.250).
   Check: `ssh boosterk1.a1 systemctl is-active k1-tf` → `active`.
2. Deploy (only after code changes):
   `scp real_robot/slam_onboard/{k1_cuvslam_node.py,k1_slam_relay.py,run_slam.sh,fastdds_slam.xml} boosterk1.a1:~/k1_slam/slam_onboard/`
3. Robot: `ssh -t boosterk1.a1 ~/k1_slam/slam_onboard/run_slam.sh` (Ctrl-C stops). Wait for `tracker ready` and
   `tracked ~13 Hz`. Logs: `~/k1_slam/logs/<timestamp>/`. Hold the robot still for the first ~3 s (map frame = start pose).
4. Laptop: `real_robot/slam_onboard/laptop_rviz.sh` (default robot 192.168.50.82). Closing RViz stops everything and
   finalizes the bag in `real_robot/bags/a1_slam_<timestamp>/`. `REC=0` = no recording.

## RViz displays

Robot model + TF, SLAM pose, SLAM path (re-solved after loop closures), global landmark map (loop-closed), local
landmarks (green), camera image with tracked features, status text (local/global landmark count, lost frames),
2-D map, costmap, collision ring (red < 0.35 m to an obstacle, distance text above the robot), depth points (off).

## How the pose is made

- cuVSLAM tracks the **camera** (rig = camera). Trunk pose = camera pose × live head kinematics (`/joint_states` head
  yaw/pitch at the image stamp, URDF joint origins). Head turns no longer move the robot in the map (fixed 2026-10-29,
  deployed, **not yet tested with a walk**).
- `ground_lock` (default on): x, y, yaw from SLAM; roll/pitch from the IMU (gravity); trunk z held at its start height.
- Features are tracked on the RGB camera (luma channel); depth only gives each feature its 3-D position (RGB-D mode).
- cuVSLAM inertial modes need a fixed camera–IMU rig (Inertial = stereo only; Multisensor = experimental, needs a cuNLS
  build). K1's IMU is in the trunk and the camera is on the moving head, so IMU fusion is not used.

## Data so far

| Bag | Content |
|---|---|
| `real_robot/bags/a1_slam_run1_20261029_1955/` (21 MB, 15 s) | end state of run 1 (big loop): path, global map, TF. Raw run not recorded. |
| `real_robot/bags/a1_slam_20261029_195735/` (450 MB, 271 s) | run 2 (clean history, smaller loop): full stream incl. depth points, map, costmap. Head turns corrupted the pose (ended at (-34, -10) m) — before the head-kinematics fix. |

Replay: `ROS_DOMAIN_ID=42 ros2 bag play <bag>` with `rviz2 -d real_robot/slam_onboard/k1_slam.rviz`.

## Known issues

- Tracking rate drops when the SLAM loop does extra work: keep debug exports cheap (per-point Python packing took it to 5 Hz).
- K1 `net.core.rmem_max` must be 8 MB (run_slam.sh sets it; lost on reboot) or camera input collapses.
- A1 memory grows slowly with the map (~3.8 → 4.2 GB used over a few minutes). Watch `free -m` on long runs.
- Repo URDF ends with a stray `---` line (laptop_rviz.sh cuts it off).
- nvblox (3-D mesh, voxels, real 2-D/ESDF map): ready but untested, see below.

## Next plan (tomorrow)

1. **Head-turn test, robot standing:** start SLAM, turn the head left/right/up/down. Pass = robot pose and model stay
   put in RViz (< 5 cm, < 2°). Check the startup log line `... in head pitch link (URDF 0.060 0.035 0.093)`.
2. **Small loop (~3 × 3 m)** walking with the remote, head still, return to the start. Pass = loop closes, path comes
   back within ~10 cm, global map has no doubled walls, 2-D map/costmap look like the room.
3. **Same loop with head scanning** while walking.
4. Save each run's bag (automatic) and note results on the Slides/Drive status deck.
5. **Save the cuVSLAM map** (`tracker.save_map`) at the end of a good run → then localize-only mode (`localize_in_map`)
   on the robot.
6. **nvblox on the laptop** (from the side session): first repair the laptop disk — `/generalSSD` (docker root) is
   read-only after an EXT4 journal abort: stop docker + containerd, `sudo umount /generalSSD`,
   `sudo e2fsck -f /dev/sda2` (check `dmesg` for drive errors first), remount/reboot. Then with SLAM running:
   `real_robot/slam_onboard/laptop_nvblox.sh` (first run builds `docker/Dockerfile.nvblox`, ~10 GB download; streams
   depth/colour from the K1 over TCP :7448 via `k1_nvblox_stream.py` → `k1_nvblox_rx.py` → nvblox, RViz
   `k1_nvblox.rviz`). Stream code tested only on laptop loopback; nvblox_node itself and the 4.5 topic names untested.
   Laptop apt has a pre-existing MRPT 2→3 conflict (untouched); nvblox lives in Docker for that reason.
