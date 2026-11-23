import time
from roboprep import ros

ANSWERS = {"M1": 100, "M2": 3000}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Underlay = the ROS install you build against; overlay = your workspace's install/ folder",
    "Sourcing prepends install paths (AMENT_PREFIX_PATH, PATH, LD_LIBRARY_PATH, PYTHONPATH, CMAKE_PREFIX_PATH)",
    "Overlay packages shadow same-named underlay packages",
    "Environment is per shell, so each new terminal must source underlay then overlay",
]}
HINTS = {"build_run": "rosidl_generate_interfaces(${PROJECT_NAME} \"msg/JointCommand.msg\"); install the executable to lib/${PROJECT_NAME}."}


def setup(lab):
    ros.ensure_ros(extras=("build",))


ECHO = r'''
import time, rclpy
from rclpy.node import Node
from rdl_interfaces.msg import JointCommand
rclpy.init()
n = Node("checker")
got = []
n.create_subscription(JointCommand, "joint_command", lambda m: got.append((time.time(), m)), 10)
t0 = time.time()
while time.time() - t0 < 4:
    rclpy.spin_once(n, timeout_sec=0.05)
ok = len(got) >= 10 and all(m.name == "shoulder" and m.max_velocity == 1.5 for _, m in got)
print("PASS fields" if ok else f"FAIL {len(got)} messages; first: {got[0][1] if got else None}")
steps = [round(b.position - a.position, 6) for (_, a), (_, b) in zip(got, got[1:])]
print("PASS position ramps by 0.01" if steps and all(abs(s - 0.01) < 1e-9 for s in steps) else f"FAIL position steps {steps[:5]}")
rate = (len(got) - 1) / (got[-1][0] - got[0][0]) if len(got) > 2 else 0
print("PASS 10 Hz" if 8 <= rate <= 12 else f"FAIL rate {rate:.1f} Hz")
'''


def check_build_run():
    out = ros.ros("cd ws && colcon build 2>&1 | tail -4", timeout=900, show=False)
    assert "2 packages finished" in out and "failed" not in out, "colcon build failed:\n" + out[-1500:]
    show = ros.ros("source ws/install/setup.bash && ros2 interface show rdl_interfaces/msg/JointCommand", show=False)
    for field in ("string name", "float64 position", "float64 max_velocity"):
        assert field in show, f"message is missing '{field}'"
    try:
        ros.start("source ws/install/setup.bash && exec ros2 run rdl_cpp joint_commander", log="jc.log")
        time.sleep(1.5)
        out = ros.ros(f"source ws/install/setup.bash && python {lab_path('_jc.py', ECHO)}", timeout=40, show=False)
        ros.expect(out, 3)
    finally:
        ros.stop_all()


def lab_path(name, code):
    import pathlib
    p = pathlib.Path(name).resolve()
    p.write_text(code)
    return p
