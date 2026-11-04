Fleet dashboard (laptop) and camera tools (robot).

```bash
uv run tools/fleet_dashboard/dashboard.py   # laptop: online state (UDP heartbeat :9000) and battery (Studio ws :51111) for every K1
# on a robot (ROS 2 Humble):
python3 tools/k1_camera/cam_monitor.py      # per-window Hz of the head camera topics (dropout check)
python3 tools/k1_camera/depth_sbs_server.py # depth side by side at http://<robot-ip>:8090/
```
Robot addresses: [docs/ROBOTS.md](https://github.com/thdhyan/k1-workspace/blob/main/docs/ROBOTS.md).
