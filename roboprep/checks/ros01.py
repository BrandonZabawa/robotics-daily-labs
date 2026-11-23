import time
from roboprep import ros

ANSWERS = {"M1": 50, "M2": 0.5, "M3": 9150}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Each process has a DDS participant that announces itself by multicast (participant discovery)",
    "Participants exchange their readers and writers (endpoint discovery) and match peer to peer, no broker",
    "Topic name and message type must match",
    "Publisher QoS must be compatible with the subscriber's request (and same domain ID)",
]}
HINTS = {
    "sensor": "create_publisher(Float32, '/joint1/temperature', 10) and create_timer(0.05, self.tick).",
    "monitor": "Append to a deque(maxlen=10) and publish Bool(data=avg > 44.0).",
}


ROS_CPP = {}   # check name -> (executable, dependencies) for C++ nodes
ROS_CPP["sensor"] = ("sensor_node", ['rclcpp', 'std_msgs'])
ROS_CPP["monitor"] = ("monitor_node", ['rclcpp', 'std_msgs'])


def setup(lab):
    ros.ensure_ros()


SENSOR_CHECK = r'''
import time, rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
rclpy.init()
n = Node("checker")
vals = []
n.create_subscription(Float32, "/joint1/temperature", lambda m: vals.append((time.time(), m.data)), 10)
t0 = time.time()
while time.time() - t0 < 4.0:
    rclpy.spin_once(n, timeout_sec=0.05)
names = [x for x in n.get_node_names()]
late = [(t, v) for t, v in vals if t - t0 > 1.0]
recent = [v for _, v in late]
rate = (len(late) - 1) / (late[-1][0] - late[0][0]) if len(late) > 5 else 0.0
print("PASS node name" if "joint1_sensor" in names else f"FAIL node name: saw {names}")
print("PASS rate" if 16 <= rate <= 24 else f"FAIL rate {rate:.1f} Hz, want 20")
ok = recent and all(34.9 <= v <= 45.1 for v in recent) and max(recent) - min(recent) > 0.5
print("PASS values" if ok else "FAIL values not 40 + 5 sin(t)")
'''

MONITOR_CHECK = r'''
import time, rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32
rclpy.init()
n = Node("checker")
pub = n.create_publisher(Float32, "/joint1/temperature", 10)
got = []
n.create_subscription(Bool, "/joint1/overheat", lambda m: got.append(m.data), 10)
t0 = time.time()
while n.count_subscribers("/joint1/temperature") == 0 and time.time() - t0 < 10:
    rclpy.spin_once(n, timeout_sec=0.1)
time.sleep(0.5)
def send(values):
    for v in values:
        pub.publish(Float32(data=v))
        for _ in range(3):
            rclpy.spin_once(n, timeout_sec=0.02)
    t = time.time()
    while time.time() - t < 0.5:
        rclpy.spin_once(n, timeout_sec=0.05)
send([50.0] * 10)
hot = list(got)
got.clear()
send([30.0] * 10)
cold = list(got)
got.clear()
send([45.0] * 5)
mixed = list(got)
print("PASS hot" if hot and hot[-1] is True else f"FAIL after ten 50.0 readings overheat={hot[-1:] }")
print("PASS cold" if cold and cold[-1] is False else f"FAIL after ten 30.0 readings overheat={cold[-1:]}")
print("PASS window" if mixed and mixed[-1] is False else "FAIL the average must use the last 10 values (5 x 45 + 5 x 30 = 37.5)")
print("PASS one output per input" if 8 <= len(hot) <= 10 else f"FAIL {len(hot)} outputs for 10 inputs")
'''


def check_sensor(node_cmd="python sensor_node.py"):
    try:
        ros.start(node_cmd, log="sensor_check.log")
        time.sleep(1.5)
        ros.expect(ros.run_script(SENSOR_CHECK, timeout=40), 3)
    finally:
        ros.stop_all()


def check_monitor(node_cmd="python monitor_node.py"):
    try:
        ros.start(node_cmd, log="monitor_check.log")
        ros.expect(ros.run_script(MONITOR_CHECK, timeout=40), 4)
    finally:
        ros.stop_all()
