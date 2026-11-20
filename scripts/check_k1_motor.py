"""Read-only K1 motor health / driver-fault check (run ON the robot).

No commands are published: only /low_state (and /joint_ctrl if a runner is live) are
subscribed. Reports each motor's q/dq plus any error/state/temperature fields the
booster_interface message exposes, and compares commanded vs actual when possible.

Usage on the robot:
  source /opt/booster/BoosterRos2Interface/install/setup.bash
  python3 ~/check_k1_motor.py 4 6         # left elbow pitch (idx 4) + right elbow (idx 6)
  python3 ~/check_k1_motor.py              # all 22 motors

Procedure for a "free" joint (e.g. A2 left elbow pitch = 4):
  1. Robot in DAMP or STOCK WALKING (never Custom/policy). Arm supported.
  2. Run this script. Move the joint by hand through its range.
  3. If q tracks the movement -> encoder OK. If q freezes -> encoder/wiring.
  4. Note any error/temp/state field flagged on that index vs its mirror joint.
  5. Power off, inspect coupling/flange bolts and reseat motor connector.
"""
from __future__ import annotations

import sys
import time

import rclpy
from booster_interface.msg import LowCmd, LowState
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

IDX = [int(x) for x in sys.argv[1:]] or list(range(22))


def fields(msg):
    return getattr(msg, "get_fields_and_field_types", lambda: {})()


rclpy.init()
node = rclpy.create_node("k1_motor_check")
qos_s = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT, history=HistoryPolicy.KEEP_LAST)
qos_c = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST)
state, cmd = {}, {}
node.create_subscription(LowState, "/low_state", lambda m: state.update(
    {i: s for i, s in enumerate(m.motor_state_serial[:22])}), qos_s)
node.create_subscription(LowCmd, "/joint_ctrl", lambda m: cmd.update(
    {i: s for i, s in enumerate(m.motor_cmd[:22])}), qos_c)

print(f"watching indices {IDX} for 6 s ... move the suspect joint by hand now")
t = time.monotonic()
while time.monotonic() - t < 6:
    rclpy.spin_once(node, timeout_sec=0.05)
if not state:
    print("no /low_state received - is the robot on and ROS up?")
    rclpy.shutdown()
    sys.exit(1)

motor_fields = list(fields(next(iter(state.values()))))
print("available MotorState fields:", ", ".join(motor_fields))
print(f"{'idx':>4} {'q':>8} {'dq':>8} {'tau_est':>8} {'temp':>5} {'mode':>5} {'lost':>6} {'cmd_q':>8}")
for i in IDX:
    if i not in state:
        continue
    s = state[i]
    c = cmd.get(i)
    cq = f"{float(c.q):+8.3f}" if c is not None else "     n/a"
    tau = f"{float(s.tau_est):+8.3f}" if hasattr(s, "tau_est") else "     n/a"
    temp = f"{int(s.temperature):5d}" if hasattr(s, "temperature") else "  n/a"
    mode = f"{int(s.mode):5d}" if hasattr(s, "mode") else "  n/a"
    lost = f"{int(s.lost):6d}" if hasattr(s, "lost") else "   n/a"
    print(f"[{i:2d}] {float(s.q):+8.3f} {float(s.dq):+8.3f} {tau} {temp} {mode} {lost} {cq}")

print("\nflags (vs all motors):")
for f in ("temperature", "lost", "mode"):
    if not all(hasattr(s, f) for s in state.values()):
        continue
    vals = {i: int(getattr(s, f)) for i, s in state.items()}
    baseline = max(set(vals.values()), key=list(vals.values()).count)
    odd = {i: v for i, v in vals.items() if v != baseline}
    print(f"  {f}: baseline={baseline}" + (f"  DIFFERENT at {odd}" if odd else "  all same"))
rclpy.shutdown()
