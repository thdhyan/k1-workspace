SLAM chain for the K1 head cameras. Not an installable library: run the scripts in place.

- `real_robot/slam_onboard/`: cuVSLAM node, TCP relay, nvblox stream and grid map on the robot. `laptop_rviz.sh`
  and `laptop_nvblox.sh` are the laptop viewers. Meshes come from k1-description (`K1_ASSETS_DIR` overrides).
- `real_robot/slam_dl/`: the same SLAM in a container on a GPU host.
- `real_robot/map_run/record_rgbd.py`: RGB-D recorder.

Runbook: `docs/legacy/k1_slam_runbook.md` in k1-workspace. Robot addresses: [docs/ROBOTS.md](https://github.com/thdhyan/k1-workspace/blob/main/docs/ROBOTS.md).
