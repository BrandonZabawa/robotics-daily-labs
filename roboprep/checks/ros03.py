import time
from roboprep import ros

ANSWERS = {"M1": 100, "M2": (30, {"rel": 0.15})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "VOLATILE: only messages published after matching are delivered",
    "TRANSIENT_LOCAL: publisher keeps the last N and sends them to new TRANSIENT_LOCAL subscribers",
    "/robot_description is latched (depth 1) so late tools still get the URDF",
    "Depth = KEEP_LAST queue size; for transient local it is also how many old messages a late joiner gets",
]}
HINTS = {
    "rules": "Offer must be at least as strong as the request for each policy.",
    "latched": "QoSProfile(depth=1, reliability=RELIABLE, durability=TRANSIENT_LOCAL).",
    "sensor_qos": "Use qos_profile_sensor_data for the subscription.",
}


ROS_CPP = {}   # check name -> (executable, dependencies) for C++ nodes
ROS_CPP["latched"] = ("map_publisher", ['rclcpp', 'std_msgs'])
ROS_CPP["sensor_qos"] = ("scan_counter", ['rclcpp', 'std_msgs'])


def setup(lab):
    ros.ensure_ros()


def check_rules(fn):
    R, B, V, T = "reliable", "best_effort", "volatile", "transient_local"
    q = lambda r, d, dl=None: {"reliability": r, "durability": d, "deadline": dl}
    assert fn(q(R, V), q(R, V)) == (True, []), "identical default QoS"
    assert fn(q(B, V), q(R, V)) == (False, ["reliability"]), "best-effort publisher, reliable subscriber"
    assert fn(q(R, V), q(B, V)) == (True, []), "reliable publisher, best-effort subscriber is fine"
    assert fn(q(R, V), q(R, T)) == (False, ["durability"]), "volatile publisher, transient-local subscriber"
    assert fn(q(R, T), q(R, V)) == (True, []), "transient-local publisher serves volatile subscribers"
    assert fn(q(R, V, 0.1), q(R, V, 0.05)) == (False, ["deadline"]), "offered 100 ms vs requested 50 ms"
    assert fn(q(R, V, 0.05), q(R, V, 0.1)) == (True, []), "offered 50 ms vs requested 100 ms"
    assert fn(q(R, V, None), q(R, V, 0.1)) == (False, ["deadline"]), "no offered deadline vs requested 100 ms"


LATCH = r'''
import time, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import String
rclpy.init()
n = Node("late_joiner")
got = []
qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
n.create_subscription(String, "/map_lite", lambda m: got.append(m.data), qos)
t0 = time.time()
while time.time() - t0 < 5 and not got:
    rclpy.spin_once(n, timeout_sec=0.1)
print("PASS late joiner got the map" if got == ["map v1"] else f"FAIL late joiner received {got}")
'''

SCAN = r'''
import time, rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import Float32, Int32
rclpy.init()
n = Node("scan_source")
pub = n.create_publisher(Float32, "/scan_fake", qos_profile_sensor_data)
counts = []
n.create_subscription(Int32, "/scan_count", lambda m: counts.append(m.data), 10)
t0 = time.time()
while n.count_subscribers("/scan_fake") == 0 and time.time() - t0 < 10:
    rclpy.spin_once(n, timeout_sec=0.1)
for k in range(40):
    pub.publish(Float32(data=float(k)))
    rclpy.spin_once(n, timeout_sec=0.05)
t = time.time()
while time.time() - t < 1.5:
    rclpy.spin_once(n, timeout_sec=0.05)
last = counts[-1] if counts else None
print("PASS best-effort data received" if last is not None and last >= 30 else f"FAIL scan_count is {last} after 40 best-effort messages")
'''


def check_latched(node_cmd="python map_publisher.py"):
    try:
        ros.start(node_cmd, log="map.log")
        time.sleep(3.0)
        ros.expect(ros.run_script(LATCH, "_latch.py", timeout=40), 1)
    finally:
        ros.stop_all()


def check_sensor_qos(node_cmd="python scan_counter.py"):
    try:
        ros.start(node_cmd, log="scan.log")
        ros.expect(ros.run_script(SCAN, "_scan.py", timeout=40), 1)
    finally:
        ros.stop_all()
