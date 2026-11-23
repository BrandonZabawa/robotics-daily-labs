import time
from roboprep import ros

ANSWERS = {"M1": (0.9, {"abs": 0.05}), "M2": 5}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "execute() blocks the only executor thread while it sleeps",
    "The cancel request waits in the queue, so is_cancel_requested never turns true and the goal finishes anyway",
    "MultiThreadedExecutor plus a reentrant group lets the cancel callback run concurrently with execute()",
]}
HINTS = {
    "action": "goal_callback returns GoalResponse.REJECT for bad orders; check gh.is_cancel_requested each step.",
    "launch": "ExecuteProcess(cmd=['python', 'heartbeat.py', '--ros-args', '-r', 'chatter:=/robot/heartbeat', '-p', 'rate:=5.0']).",
}


ROS_CPP = {}   # check name -> (executable, dependencies) for C++ nodes
ROS_CPP["action"] = ("fib_server", ['rclcpp', 'rclcpp_action', 'example_interfaces'])


def setup(lab):
    ros.ensure_ros()


ACTION = r'''
import time, rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from example_interfaces.action import Fibonacci
rclpy.init()
n = Node("checker")
c = ActionClient(n, Fibonacci, "fibonacci")
if not c.wait_for_server(timeout_sec=15):
    print("FAIL no /fibonacci action server"); raise SystemExit
fb = []
def run(order, cancel_after=None):
    f = c.send_goal_async(Fibonacci.Goal(order=order), feedback_callback=lambda m: fb.append(list(m.feedback.sequence)))
    rclpy.spin_until_future_complete(n, f, timeout_sec=5)
    gh = f.result()
    if not gh.accepted:
        return "rejected", None
    if cancel_after:
        t = time.time()
        while time.time() - t < cancel_after:
            rclpy.spin_once(n, timeout_sec=0.05)
        cf = gh.cancel_goal_async(); rclpy.spin_until_future_complete(n, cf, timeout_sec=5)
    rf = gh.get_result_async(); rclpy.spin_until_future_complete(n, rf, timeout_sec=15)
    r = rf.result()
    return r.status, list(r.result.sequence)
st, seq = run(5)
print("PASS result" if st == GoalStatus.STATUS_SUCCEEDED and seq == [0, 1, 1, 2, 3, 5] else f"FAIL order 5 -> {st}, {seq}")
print("PASS feedback" if len(fb) >= 3 and fb[-1][:3] == [0, 1, 1] else f"FAIL feedback messages: {fb}")
st, _ = run(60)
print("PASS rejects 60" if st == "rejected" else "FAIL order 60 must be rejected")
t0 = time.time()
st, seq = run(40, cancel_after=0.5)
print("PASS cancel" if st == GoalStatus.STATUS_CANCELED and time.time() - t0 < 2.5 else f"FAIL cancel: status {st} after {time.time() - t0:.1f} s")
'''

LAUNCH = r'''
import time, rclpy
from rclpy.node import Node
from std_msgs.msg import String
rclpy.init()
n = Node("checker")
stamps = []
n.create_subscription(String, "/robot/heartbeat", lambda m: stamps.append(time.time()), 10)
t0 = time.time()
while time.time() - t0 < 4:
    rclpy.spin_once(n, timeout_sec=0.05)
names = n.get_node_names()
rate = (len(stamps) - 1) / (stamps[-1] - stamps[0]) if len(stamps) > 2 else 0
print("PASS both nodes" if "fib_server" in names and "heartbeat" in names else f"FAIL nodes seen: {names}")
print("PASS remap and rate" if 4.0 <= rate <= 6.0 else f"FAIL /robot/heartbeat at {rate:.1f} Hz, want 5")
'''


def check_action(node_cmd="python fib_server.py"):
    try:
        ros.start(node_cmd, log="fib.log")
        ros.expect(ros.run_script(ACTION, "_action.py", timeout=60), 4)
    finally:
        ros.stop_all()


def check_launch():
    try:
        ros.start("ros2 launch bringup.launch.py", log="launch_check.log")
        time.sleep(3)
        ros.expect(ros.run_script(LAUNCH, "_launch.py", timeout=40), 2)
    finally:
        ros.stop_all()
