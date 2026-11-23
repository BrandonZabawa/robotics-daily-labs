import time
from roboprep import ros

ANSWERS = {"M1": (0.3905, {"abs": 1e-3}), "M2": (0.9659, {"abs": 1e-3})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "base_link is fixed to the robot body",
    "odom -> base_link from odometry: continuous, smooth, drifts",
    "map -> odom from localization: corrects drift, may jump",
    "One parent per frame, so the localizer publishes map -> odom (not map -> base_link)",
]}
HINTS = {
    "tf": "Static quaternion (0, sin 15deg, 0, cos 15deg); dynamic yaw quaternion (0, 0, sin(yaw/2), cos(yaw/2)).",
    "urdf": "Elbow origin xyz='0.3 0 0', axis z; tool_joint fixed with origin xyz='0.25 0 0'.",
}


ROS_CPP = {}   # check name -> (executable, dependencies) for C++ nodes
ROS_CPP["urdf"] = ("joint_pub", ['rclcpp', 'sensor_msgs'])
ROS_CPP["tf"] = ("tf_demo", ['rclcpp', 'tf2_ros', 'geometry_msgs'])


def setup(lab):
    ros.ensure_ros()


TF = r'''
import math, time, rclpy
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener
rclpy.init()
n = Node("checker")
buf = Buffer(); TransformListener(buf, n)
def get(target, source):
    t0 = time.time()
    while time.time() - t0 < 6:
        rclpy.spin_once(n, timeout_sec=0.05)
        if buf.can_transform(target, source, Time()):
            return buf.lookup_transform(target, source, Time()).transform
    return None
s = get("base_link", "camera_link")
ok = s and abs(s.translation.x - 0.1) < 1e-6 and abs(s.translation.z - 0.3) < 1e-6 and abs(s.rotation.y - math.sin(math.radians(15))) < 1e-4 and abs(s.rotation.w - math.cos(math.radians(15))) < 1e-4
print("PASS static camera mount" if ok else f"FAIL base_link->camera_link: {s}")
bad = 0
for _ in range(5):
    d = get("odom", "base_link")
    if d is None:
        bad += 1; continue
    x, y = d.translation.x, d.translation.y
    yaw = 2 * math.atan2(d.rotation.z, d.rotation.w)
    err = (yaw - (math.atan2(y, x) + math.pi / 2) + math.pi) % (2 * math.pi) - math.pi
    if abs(math.hypot(x, y) - 1.0) > 1e-3 or abs(err) > 1e-3:
        bad += 1
    for _ in range(4):
        rclpy.spin_once(n, timeout_sec=0.05)
print("PASS moving base on the circle, facing along it" if bad == 0 else "FAIL odom->base_link is not on the unit circle with yaw = angle + 90 deg")
c = get("odom", "camera_link")
print("PASS chained lookup odom->camera_link" if c else "FAIL odom->camera_link not available")
'''

ARM = r'''
import math, time, rclpy
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener
rclpy.init()
n = Node("checker")
buf = Buffer(); TransformListener(buf, n)
t0 = time.time(); tr = None
while time.time() - t0 < 8 and tr is None:
    rclpy.spin_once(n, timeout_sec=0.05)
    if buf.can_transform("base_link", "tool0", Time()):
        tr = buf.lookup_transform("base_link", "tool0", Time()).transform.translation
ex, ey = 0.3 * math.cos(0.5) + 0.25 * math.cos(0.2), 0.3 * math.sin(0.5) + 0.25 * math.sin(0.2)
ok = tr and abs(tr.x - ex) < 1e-3 and abs(tr.y - ey) < 1e-3 and abs(tr.z - 0.1) < 1e-3
print("PASS tool0 matches forward kinematics" if ok else f"FAIL base_link->tool0 = {tr}, expected ({ex:.4f}, {ey:.4f}, 0.1)")
'''


def check_tf(node_cmd="python tf_demo.py"):
    try:
        ros.start(node_cmd, log="tf.log")
        ros.expect(ros.run_script(TF, "_tf.py", timeout=60), 3)
    finally:
        ros.stop_all()


def check_urdf(node_cmd="python joint_pub.py"):
    try:
        ros.start('ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:="$(cat arm.urdf)"',
                  log="rsp_check.log")
        ros.start(node_cmd, log="jp.log")
        ros.expect(ros.run_script(ARM, "_arm.py", timeout=40), 1)
    finally:
        ros.stop_all()
