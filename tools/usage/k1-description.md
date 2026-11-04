Owns every robot model file. No other library computes model paths itself: they all ask this one.

```python
import k1_description as d
d.robot_file(d.URDF)        # K1_22dof.urdf;  also URDF_ZED, MJCF, MJCF_MJLAB, MJCF_MJLAB_ARMS
d.robot_file(d.USD_MJLAB)   # usd_mjlab/ USD for Isaac mjlab-asset tasks; also USD_MJLAB_ARMS, USD_MJLAB_SOLID
d.assets_dir()              # $K1_ASSETS_DIR, else the bundled assets/ (booster_assets submodule)
d.robot_description()       # URDF text for robot_state_publisher
```
The meshes, MJCF and USD come from the nested `assets/` submodule (booster_assets). Fetch them with
`git submodule update --init assets`, or let `scripts/dev-install.sh` do it.

As a ROS 2 package (installs `share/k1_description/assets/robots/K1`):
```bash
source /opt/ros/jazzy/setup.bash
ros2 launch k1_description view_robot.launch.py   # RSP + joint_state_publisher_gui + RViz
```
