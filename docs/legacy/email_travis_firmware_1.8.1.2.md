**To:** Travis Henderson
**Subject:** K1 firmware 1.8.1.2: new camera control and RGB + depth streaming at ~25 Hz

Hi Travis,

I updated K1 A2 from 1.6.2.2 to 1.8.1.2-release-02884 (2026-10-15) over the lab robotics_5G network. Camera results on A2 after the update:

- **New camera control surface.** The robot now exposes `/CameraApiTopicReq` and `/CameraApiTopicResp` next to `/X5CameraControlReq` and `/X5CameraControlResp`. There is also a new `/boostercamera/head/combine/rgb` topic (about 19 Hz). Camera processes now run under a new container service (`booster_camera`, `cam_stream_receiver_ros2` and `booster-video-stream`).
- **Continuous, faster streaming.** On 1.6.2.2 the head camera gave about 4 Hz RGB and depth, and an earlier test saw the stream stop a few minutes after boot. On 1.8.1.2, `/boostercamera/head/rgb` runs at about 27 Hz and `/boostercamera/head/depth` at about 21-28 Hz. Both are 544x448. RGB is NV12 and depth is float32 in millimetres.
- **RGB and depth side by side.** A small server on the robot (`tools/k1_camera/depth_sbs_server.py` in booster_ws) streams RGB next to a colourised depth map as MJPEG at about 23-28 fps and about 8 Mbit/s: `http://192.168.50.215:8090/`.

Caveats: I have only run this on A2, for a few minutes, so I have not yet confirmed that it stays up for hours. The Studio websocket (`:51111`) still carries RGB only (about 10 fps) and no depth, so depth comes through ROS or the side-by-side server. The update installs only the latest version and cannot be pinned, so other robots will move to 1.8.1.2 too if updated.

Notes: `docs/booster_websocket_studio_cli_findings_2026-10-27.md` (also on the shared Drive).

Thanks,
Dhyan
