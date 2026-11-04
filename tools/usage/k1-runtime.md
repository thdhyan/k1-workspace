Policy runtime with torch and numpy only. The same files run on the laptop and on the robot.

| Module | What |
|---|---|
| `wbc` | decoupled WBC: `LocoCmd`, `HeadCmd`, `ArmCmd`, `DecoupledWBC`, joint tables |
| `gamepad_core` | gains, `Walker`, `Body`, `ArmJog`, UDP `Gamepad` parser. Shared by the robot runner (k1-deploy-robot) and the sim (k1-deploy-laptop) |
| `push_ik_core` | `PushIKController` for the two-robot box push |
| `k1_arm_ik` | `ArmIK` (default URDF from k1-description) |
| `ds4` | DS4 pad reader and light bar |

`CAP` (command limits) is a module global. Set `gamepad_core.CAP` before you build a `Gamepad`.

On the robot, `k1_gamepad_deploy.py` needs `gamepad_core.py` and `wbc.py` in a `k1_runtime/` directory next to it.
Copy recipe: [docs/ROBOTS.md section 4](https://github.com/thdhyan/k1-workspace/blob/main/docs/ROBOTS.md).
