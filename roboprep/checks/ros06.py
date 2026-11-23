import time
from roboprep import ros

ANSWERS = {"M1": 500, "M2": 4}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Configure (load parameters, open hardware) is separate from activate (start streaming or accepting commands)",
    "A supervisor can configure all drivers, verify, then activate in a known order",
    "Recovery: deactivate, cleanup, configure again without restarting the process",
    "A plain node starts publishing on creation and has no standard state to query or reset",
]}
HINTS = {
    "executor": "MultiThreadedExecutor plus a separate MutuallyExclusiveCallbackGroup for the timer and for the service.",
    "lifecycle": "create_lifecycle_publisher and create_timer in on_configure; destroy both in on_cleanup.",
}


ROS_CPP = {}   # check name -> (executable, dependencies) for C++ nodes
ROS_CPP["lifecycle"] = ("lc_sensor", ['rclcpp', 'rclcpp_lifecycle', 'std_msgs'])
ROS_CPP["executor"] = ("busy_node", ['rclcpp', 'std_srvs'])


def setup(lab):
    ros.ensure_ros()


PING = r'''
import time, rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
rclpy.init()
n = Node("checker")
c = n.create_client(Trigger, "/busy_node/ping")
if not c.wait_for_service(timeout_sec=15):
    print("FAIL no ping service"); raise SystemExit
lat = []
t_end = time.time() + 3.0
while time.time() < t_end:
    t = time.time()
    f = c.call_async(Trigger.Request())
    rclpy.spin_until_future_complete(n, f, timeout_sec=2)
    lat.append(time.time() - t)
    time.sleep(0.07)
worst = max(lat)
print("PASS ping stays responsive" if worst < 0.35 else f"FAIL worst ping latency {worst*1000:.0f} ms")
'''

LIFE = r'''
import subprocess, time, rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
rclpy.init()
n = Node("checker")
got = []
n.create_subscription(Float32, "/lc_sensor/data", lambda m: got.append(m.data), 10)
def wait(s):
    t = time.time()
    while time.time() - t < s:
        rclpy.spin_once(n, timeout_sec=0.05)
def phase(cmd, s=1.5):
    if cmd:
        r = subprocess.run(f"ros2 lifecycle set /lc_sensor {cmd}", shell=True, capture_output=True, text=True)
        if "successful" not in (r.stdout + r.stderr).lower():
            return None
    wait(0.5)               # drain messages queued while the CLI ran
    got.clear(); wait(s); return len(got)
wait(2)
unconf = phase(None)
inactive = phase("configure")
active = phase("activate")
deact = phase("deactivate")
clean = phase("cleanup")
print("PASS silent before activate" if unconf == 0 and inactive == 0 else f"FAIL messages before activate: {unconf}, {inactive}")
print("PASS publishes when active" if active and active >= 8 else f"FAIL {active} messages in 1.5 s while active")
print("PASS silent after deactivate" if deact is not None and deact <= 1 else f"FAIL {deact} messages after deactivate")
print("PASS cleanup succeeded" if clean == 0 else "FAIL cleanup transition failed")
'''


def check_executor(node_cmd="python busy_node.py"):
    try:
        ros.start(node_cmd, log="busy.log")
        ros.expect(ros.run_script(PING, "_ping.py", timeout=40), 1)
    finally:
        ros.stop_all()


def check_lifecycle(node_cmd="python lc_sensor.py"):
    try:
        ros.start(node_cmd, log="lc_check.log")
        ros.expect(ros.run_script(LIFE, "_life.py", timeout=90), 4)
    finally:
        ros.stop_all()
