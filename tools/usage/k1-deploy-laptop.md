The laptop side: a ROS 2 Jazzy colcon workspace (`src/`), and the push-IK and pad tools (`deploy/`).

```bash
# ROS packages: k1_bringup, k1_control (needs the Booster SDK), k1_fleet_rviz, k1_locomotion, k1_sim_gazebo, k1_wbc
git submodule update --init sdk/booster_robotics_sdk    # Booster SDK, which k1_control's CMake expects here
source /opt/ros/jazzy/setup.bash && colcon build && source install/setup.bash
ros2 launch k1_fleet_rviz fleet_rviz.launch.py
```
| Tool (`deploy/`) | What |
|---|---|
| `pad_udp_send.py --host IP` | DS4 -> robot runner over UDP :9870 |
| `push_ik_web.py [--fake] [--send] --robots A B` | browser tool for the two-robot box push, http://127.0.0.1:8765 |
| `push_ik_sim.py` | CPU MuJoCo preview used by the web tool |
| `gamepad_sim.py` | MuJoCo sim-to-sim of the walk base (same `gamepad_core` as the robot) |

Robot IPs, safety and step-by-step runs: [docs/ROBOTS.md](https://github.com/thdhyan/k1-workspace/blob/main/docs/ROBOTS.md). The end-to-end test runs without hardware:
`pytest tests` (runs `tests/e2e_push_ik_web.py` and prints `WEB TEST OK`).
