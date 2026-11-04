Code that runs **on the K1** (Python 3.10, ROS 2 Humble, `/opt/booster/BoosterRos2Interface`).

- `deploy/k1_gamepad_deploy.py`: the policy runner. It walks the RL base from DS4 UDP packets on :9870, or takes
  `--task` packets from the PushIK tools. It needs `k1_runtime/{gamepad_core,wbc}.py` next to it.
- `real_robot/`: stereo, walk and rosbag recorders, the TF service, and the stereo watchdog (`install_watchdog.sh`).
- `sdk_bridge/`: the on-robot half of the former `k1_control` package. Its `setup.py` entry points still need splitting.

Copy, dry run, real run and stops: [docs/ROBOTS.md section 4](https://github.com/thdhyan/k1-workspace/blob/main/docs/ROBOTS.md).
```bash
source /opt/booster/BoosterRos2Interface/install/setup.bash
cd ~/k1_mjlab_deploy/deploy
python3 k1_gamepad_deploy.py --policy ../walk_still_v2.pt --udp 9870 --dry   # sends nothing to the motors
```
