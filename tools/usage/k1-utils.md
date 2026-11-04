Evaluation gates and checkpoint tools. Only torch, numpy and mujoco are needed.

```bash
python -m k1_utils.gait_gate --help        # gait gate for a walk checkpoint (rl-isaac scripts/gait_gate.py wraps it)
python -m k1_utils.mujoco_eval --help      # MuJoCo sim-to-sim eval on k1_description's MJCF
```
`scripts/zero_step.sh` still uses the old `booster_ws` container layout and has not been ported.
