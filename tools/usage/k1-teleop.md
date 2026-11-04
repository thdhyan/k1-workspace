Teleop nodes (ROS 2 Jazzy on the laptop).

| Entry | What |
|---|---|
| `python -m k1_teleop.push_ik_phasespace` | PhaseSpace caps -> PushIK policy -> UDP to 2 robots (command line; the browser tool in k1-deploy-laptop adds robot-status stops) |
| `k1_teleop.xr_teleop_node` | Quest 3 -> K1 through Isaac Teleop (CloudXR) |
| `multi_k1_sim.py`, `multi_k1_view.py` | multi-robot sim and viewer |
| `hmd_poser/` | HMD poser |

Robot addresses and the push procedure: [docs/ROBOTS.md section 5](https://github.com/thdhyan/k1-workspace/blob/main/docs/ROBOTS.md). Always
`export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` (DDS over Wi-Fi runs the K1 out of memory).
