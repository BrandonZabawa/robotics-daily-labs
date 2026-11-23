import json
import time
from roboprep import ros

ANSWERS = {"M1": 0.01, "M2": 6.0}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Python timers and the default executor add jitter (garbage collector, interpreter lock, callback ordering)",
    "Run the loop in a ros2_control controller or a C++ real-time thread (SCHED_FIFO on PREEMPT_RT)",
    "Lock memory, no allocation or blocking in the loop, absolute-time sleeps",
    "Isolate a core, lock-free buffers to the rest of ROS, and monitor missed deadlines",
]}
HINTS = {
    "closed_loop": "Subscriptions to /joint/setpoint (latched) and /joint_states, a 0.01 s timer, PID as in M03 with D = -kd * velocity.",
}


ROS_CPP = {}   # check name -> (executable, dependencies) for C++ nodes
ROS_CPP["closed_loop"] = ("pid_node", ['rclcpp', 'std_msgs', 'sensor_msgs'])


def setup(lab):
    ros.ensure_ros()


def _metrics(data, t0, t1, target, start):
    seg = [(t, p) for t, p in data if t0 <= t < t1]
    span = target - start
    peak = max(p for _, p in seg) if span > 0 else min(p for _, p in seg)
    over = (peak - target) / span * 100
    outside = [t for t, p in seg if abs(p - target) > 0.02 * abs(span)]
    settle = (outside[-1] - t0) if outside else 0.0
    return over, settle, seg[-1][1]


def check_closed_loop(node_cmd=None):
    try:
        if node_cmd:   # C++ node: start the plant and your node directly (the launch file is graded in Python)
            ros.start("python joint_sim.py", log="sim_check.log")
            ros.start(node_cmd + " --ros-args -p kp:=3.6 -p ki:=0.3 -p kd:=0.86", log="pid_check.log")
        else:
            ros.start("ros2 launch control.launch.py", log="launch_check.log")
        time.sleep(3)
        out = ros.ros("python step_logger.py", timeout=60, show=False).strip().splitlines()
    finally:
        ros.stop_all()
    try:
        data = json.loads(out[-1])
    except Exception:
        raise AssertionError("no joint data logged; are both nodes running?\n" + "\n".join(out[-5:]))
    assert len(data) > 500, f"only {len(data)} joint states in 8 s"
    over, settle, final = _metrics(data, 0.0, 4.0, 1.0, 0.0)
    assert final == final and abs(final - 1.0) < 0.02, f"step to 1.0 ends at {final:.3f}"
    assert over < 20 and settle < 3.0, f"step to 1.0: overshoot {over:.1f}%, settling {settle:.2f} s"
    over, settle, final = _metrics(data, 4.0, 8.0, -0.5, 1.0)
    assert abs(final + 0.5) < 0.03 and settle < 3.0, f"step to -0.5: final {final:.3f}, settling {settle:.2f} s"
