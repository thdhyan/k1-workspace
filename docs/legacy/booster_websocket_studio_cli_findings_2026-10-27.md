# Booster K1 websocket, booster-cli and Booster Studio findings — 2026-10-27

Robot: A2 (`Booster K1_UMN_A2`, 192.168.50.215), firmware v1.6.2.2-release.global-02145-2026-06-03, before the OTA to 1.8.1.2 that started during this test.
Laptop: Booster Studio 1.110.1 (VS Code fork), `/usr/share/booster-studio`.

## 1. Robot websocket `ws://<ip>:51111`
Protobuf messages, no schema published. Envelope: `{1: msg_type (varint), 2: uuid (string), 3: payload (submessage)}`.
Only two message types seen in 8-25 s captures. Scripts: `uv run` PEP 723 scripts `wstypes.py` / `wsdump.py` (scratchpad; generic protobuf decoder).

| field1 | meaning | size | rate | payload |
|---|---|---|---|---|
| 10001 | camera frame | ~124 KiB | ~10 fps (~10 Mbit/s) | `3 { 1: JPEG bytes }` RGB only, no depth |
| 10000 | robot status | ~0.9 KiB | ~1 Hz (about 8 per 8 s) | see below |

Status (10000) payload `3 { 1:"" , 2:{robot info}, 3:{joint}* ... }` (battery is a `{1:'battery', 3:float32}` entry, see dashboard):
- robot info (field 2): serial `(serial redacted)`, model "Booster K1", firmware string, build epoch, robot IP, field7=50051 (RPC port), field8=51111 (this ws),
  field12 nickname `Booster K1_UMN_A2`, field14 version `1.2.1`, field16=50052 (update-engine port).
- repeated joint entries (field 3): name (leading letter junk is a protobuf tag artifact of my generic decoder: `AAHead_Yaw` = `Head_Yaw`), index, enabled flag, and a temperature-like value (33-42).
  Joints reported: Head_Yaw, Head_Pitch, Left/Right_Shoulder_Pitch/Roll, Elbow_Pitch/Yaw, Left/Right_Hip_Pitch/Roll/Yaw, Knee_Pitch, Ankle_Pitch/Roll (22 DoF).
- The stream is server-push only; client sends nothing in our tests. Depth, IMU, odometry, lidar not present.

## 2. Why depth is not on the websocket / why :8765 is closed
Studio's native addon (`resources/app/booster-native/@booster-studio/native-addon.linux-x64-gnu.node`, NAPI-RS, typings in `index.d.ts`) shows:
- `ServiceName` = MotionControl, **RosBridge**, Jupyter, Terminal, RosBagRecord, AgentDebuggerLog. Studio starts these ON DEMAND over SSH
  (error codes RosBridgeSyncFileFailed / FindSetupBashFailed / InstallFailed / StartFailed; JupyterPortForwardFailed; Terminal SSH channels).
  So the ROS bridge (default `ros_bridge_server_port` 8765, sqlite `default_robots` column) only exists after Studio connects and starts it. Nothing listens on :8765 by default on the robot.
- RobotDetail fields: motionBoardIp, boosterServerWebsocketPort, motionBoardRosEnv, perceptionBoardRosEnv, rosBridgeServerBoard (MotionBoard | PerceptionBoard), agentDebuggerPort, jupyter_server_address.
  Camera depth goes through the ROS bridge (tiered send), not :51111.
- K1 listed as `SingleBoardBoosterRobot`/`DualBoardBoosterRobot`; Studio also supports T1, T2, remote virtual robots (webots/physics websocket ports, cameraHubPort).
- API calls to the robot (NAPI exports): getApis, callApi(serial, apiName, params), execAgentApi, activateRobot/deactivateRobot, reconnectRobot,
  restartService, createShellChannel/writeShellChannel (SSH terminal), getRobotRerunLogFiles/loadRobotRerunLog/switchRerunListener (Rerun logs),
  getRobotStatusHistory, executeCustomTrainedTrajectory(artifactUrl), agentDev* (build/deploy agents in docker), simulatorLibrary* (scene/asset import).
- Studio listens for robot UDP discovery (getUdpListenerStatus, getRobotDiscoveryPortOwner, repairRobotDiscoveryPort). UDP :9000 heartbeat each second (fields: serial, model, fw, ip, nickname).

## 3. booster-cli (on robot, `/usr/bin/booster-cli`)
- `launch -c start|stop|restart -m motion|perception`
- `upgrade` : ignores all args (even `-h`), runs OTA flow to LATEST (1.8.1.2-release-02884-2026-10-15). No version pinning, no dry run. Talks to booster-update-engine (tcp :50052).
- `log -st YYYYMMDD-HHMMSS [-et ...] [-o /abs/path.zip]` : extract robot logs (default /home/master/Downloads/<ts>.zip).
- `upload_log -lt <unix sec> -rt <unix sec>` : upload robot log for a time range to Booster cloud (sends data off-robot; not run).
- Listeners on A2 (idle, upgrading): :22 ssh, :111 rpcbind, :6868 + :16888/:16889 booster_agent_manager, :50052 update-engine.
  :51111 and :50051 vanished while the OTA installer ran (services stopped).
- OTA metadata: POST https://pubdataprod.boosterobotics.com/ota/api/get_ota_metadata/ ; payload .run from boosterobotics.s3.ap-southeast-1.amazonaws.com/ota_single/f8190bd1/.

## 4. ROS camera (on robot, humble) vs websocket
`/boostercamera/head/rgb` and `/boostercamera/head/depth` ~4.3 Hz on-robot before upgrade (jittery). Websocket JPEG ~10 fps from a separate encoder path.
Depth only through ROS (DDS domain 0, or the Studio-started ROS bridge ws :8765).

## 5. Upgrade note
A2 OTA 1.6.2.2 -> 1.8.1.2 was started during this session by the user (`sudo booster-cli upgrade`); installer still running at last check (02:20 elapsed).
Re-run `wstypes.py` after reboot: new firmware may add message types / depth. Not yet tested.

## 6. After OTA to 1.8.1.2-release-02884 (A2, 2026-10-27 07:16 CST)
- Architecture change: services now run under `/opt/booster/bin/containerd` (+ containerd_gateway :20011, `server_motion` owns :50051/:51111/:51112/:51113, `server_perception`, `booster_camera`). `booster-daemon` and `booster-update-engine` still systemd. New dirs: `env`, `ros2`, `python3`, `share`, `BoosterAutoHandeyeCalib`. ROS still humble, Ubuntu 22.04.
- Websocket :51111 unchanged (still only 10001 JPEG ~127 KB, 10000 status). :51112 also sends 10000-type status; :51113 silent in 8 s.
- New ROS: `/CameraApiTopicReq|Resp`, `/boostercamera/head/combine/rgb` (~19 Hz), handeye calib topics. Rates: rgb ~27 Hz (nv12 544x448), depth ~21-28 Hz (float32 **millimetres**, 544x448, values 650-7600 mm).
- `tools/k1_camera/depth_sbs_server.py` (run on robot): RGB | turbo-colourised depth MJPEG, http://<robot>:8090/ , /stats. Measured 23-28 fps, ~8 Mbit/s.
- depth_sbs_server.py transport: plain HTTP MJPEG (`multipart/x-mixed-replace`, TCP :8090). Not a websocket, not ROS on the wire. ROS (rclpy) is used only on the robot to read `/boostercamera/head/{rgb,depth}`. `/snapshot.jpg` = one frame, `/stats` = fps.
- Fix after browser report ("black after few frames, dies on refresh"): old tabs kept writing forever. Now TCP_NODELAY, 3 s send timeout drops stale clients, `Connection: close`, boundary `frame`. OpenCV client test: 400-450 frames/15 s, max gap <0.2 s, reconnect OK. Headless Chrome crashed on this laptop, so browser behaviour was not reproduced.
