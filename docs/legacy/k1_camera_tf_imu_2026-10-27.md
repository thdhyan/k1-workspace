# K1 A2/A3 camera, IMU and TF check: 2026-10-27

Goal: decide whether on-robot visual SLAM (cuVSLAM) plus leg odometry is viable.
Firmware: A2 = 1.8.1.2-release-02884 (read with `grep Version /opt/booster/version.txt | tail -1`; `head` shows the oldest history entry and misleads). A3 not re-read (offline).
Robots: A2 `boosterk1.a2` (192.168.50.215), A3 `boosterk1.a3` (192.168.50.230). Humble, Orin NX, services under `/opt/booster/bin/containerd`.

## 1. Camera rates

| topic | A2 (up 69-75 min) | A3 (up 92-96 min) |
|---|---|---|
| `/boostercamera/head/rgb` (nv12 544x448) | 29-30 Hz | 28-30 Hz |
| `/boostercamera/head/depth` (float32 mm) | 24-31 Hz | 22-30 Hz |
| `/boostercamera/head/right/rgb`, `/raw/rgb`, `/raw/right/rgb` | 0 (no publisher) | 0 (no publisher) |

- No dropout seen on either robot. Both were already past the old 10-12 min X5 failure window when the test started.
- That is NOT a proof the dropout is fixed: neither robot was watched from cold boot. Cold-boot test still open.
- A3 went offline (low battery) ~10:55, so its 60 min log (`~/cam_monitor.log`) stops early. A2's run continues. Re-run A3 after charging.
- Claimed vs measured: target was 20 fps video + depth. Measured 28-30 Hz RGB and 22-30 Hz depth in 30 s windows (>= 20: met). Through the browser server below, 25 s average was RGB 23.5, depth 20.8, side-by-side 20.7 fps (includes startup and JPEG encode on the Orin), so ~20 fps end to end.
- Monitor: `tools/k1_camera/cam_monitor.py` (run on the robot; QoS RELIABLE+VOLATILE). 60 min runs write `~/cam_monitor.log` on both robots.
- Right-eye images are not published, so stereo cuVSLAM from ROS topics is not possible. Use **RGBD mode** (rgb + aligned depth; depth is derived from the left image).

## 2. IMU: bridge not needed

`/imu/data` is a real `sensor_msgs/Imu`, 340-410 Hz, `frame_id: trunk`, valid orientation quaternion, gravity ~9.4 m/s^2 on z. The old blocker in `docs/k1_walk_data_plan.md` (Euler-only IMU inside `low_state`) no longer applies on this firmware. `/odom` is a real `nav_msgs/Odometry` (odom -> trunk), `/joint_states` ~340-410 Hz.

## 3. TF: `k1-tf.service` (systemd, enabled, both robots)

The vendor `/tf` only carried `aahead_pitch_link -> head_color_optical_frame` (+ a static pair). The body tree was missing.

- `/robot_description` (25 KB URDF) saved to `real_robot/urdf/k1_robot_description.urdf`. Link names carry the vendor `aa` prefix (`aahead_pitch_link`, `aaleft_shoulder_pitch_link`); this matches the camera driver's TF, so do not rename them.
- `real_robot/tf_service/`: `k1_tf.sh` runs `robot_state_publisher` (URDF + `/joint_states`) and `k1_odom_tf.py` (`/odom` -> TF `odom -> trunk`). Unit `k1-tf.service`, `Restart=always`, `Nice=10`, `MemoryMax=300M`. Install: `real_robot/tf_service/install.sh boosterk1.a2`.
- systemd, not containerd: `booster-daemon`, `booster-update-engine` and the other host services are systemd units; containerd only holds the vendor `server_*` binaries.
- Verified on both robots: `odom -> trunk -> head_color_optical_frame` and `trunk -> left_ankle_roll_link` resolve. Camera optical frame sits at about (0.115, 0.047, 0.257) m from `trunk`.
- Gotcha: passing the URDF as `-p robot_description:=...` crashes (`Failed to parse global arguments`) because of its comments/newlines. The script feeds it through a params YAML.

## 4. Open

1. `/odom` pose is 0 while standing. Need a walk to confirm it integrates; if not, use `/odometer_state` (x, y, theta) instead.
2. Cold-boot dropout test on A2 and A3 (reboot, run `cam_monitor.py` from boot, 20 min).
3. Fresh-map cuVSLAM RGBD run + nvblox (map save/load deferred).

## 5. Browser view with depth

`tools/k1_camera/depth_sbs_server.py` (run on the robot, `source /opt/ros/humble/setup.bash; python3 depth_sbs_server.py`): subscribes to ROS `/boostercamera/head/{rgb,depth}`, serves RGB | turbo-colourised depth as MJPEG at `http://<robot>:8090/` (`/snapshot.jpg`, `/stats`). Not running at boot on either robot; copied to A2 and A3 `~/`. Next step per user: also publish the side-by-side / colourised depth back as a ROS topic.

## 6. Runbook for a fresh agent (on the robot)

Prereqs: laptop on the robotics LAN, `ssh boosterk1.a2` works (key `~/.ssh/booster_k1`, user `booster`, IPs in `~/.ssh/config`: A2 192.168.50.215, A3 192.168.50.230). On the robot always `source /opt/ros/humble/setup.bash` (domain 0). Use `ros2 topic list --no-daemon`-style discovery carefully: the CLI daemon was stale once; python `rclpy` scripts are more reliable. Camera topics need QoS RELIABLE + VOLATILE.

1. Check the TF service: `systemctl is-active k1-tf` (expect `active`). If missing: `real_robot/tf_service/install.sh boosterk1.a2` from the repo root. Verify with `python3 ~/tfchk.py` (copy from the session scratch or re-create: tf2 Buffer lookups of `odom->trunk`, `trunk->head_color_optical_frame`).
2. Camera rates: `scp tools/k1_camera/cam_monitor.py boosterk1.a2:~/` then `python3 ~/cam_monitor.py --minutes 20 --window 10`. Columns: rgb, right/rgb, depth, raw/rgb, raw/right/rgb. Right/raw columns are expected 0; flag a drop when rgb or depth < 5 Hz.
3. Cold-boot dropout test (still open): `sudo reboot` the robot, wait for SSH, start the monitor within 1 min, watch 20 min. Note the uptime of the first stall.
4. Depth in the browser: `python3 ~/depth_sbs_server.py` -> `http://192.168.50.215:8090/`, `/stats` for fps.
5. Odometry check (needs the robot to walk): echo `/odom` and `/odometer_state` while walking; if `/odom` pose stays 0, switch `k1_odom_tf.py` to `/odometer_state`.
6. Then: cuVSLAM RGBD on a fresh map (`~/cuvslam/bin`, v17 native; no map save/load yet), nvblox on dl.

Cautions: never run `booster-cli upgrade` (ignores all args, installs latest). A3 and others need charge before tests; they power off at low battery. Do not edit `/opt/booster`.
