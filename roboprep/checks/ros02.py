import time
from roboprep import ros

ANSWERS = {"M1": 0.2, "M2": 60}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "The callback refuses bad values before they are stored, with a reason the caller sees",
    "Every way of setting the parameter (launch, CLI, GUI) gets the same check; the node never runs with a bad value",
    "Parameters go through a service round trip with no streaming semantics: use a topic for per-cycle setpoints",
]}
HINTS = {
    "server": "declare_parameter, add_on_set_parameters_callback, create_service(SetBool, name, callback).",
    "client": "create_client, wait_for_service, call_async, rclpy.spin_until_future_complete.",
}


ROS_CPP = {}   # check name -> (executable, dependencies) for C++ nodes
ROS_CPP["server"] = ("gripper_server", ['rclcpp', 'std_srvs', 'rcl_interfaces'])
ROS_CPP["client"] = ("client", ['rclcpp', 'std_srvs'])


def setup(lab):
    ros.ensure_ros()


SERVER_CHECK = r'''
import subprocess, rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool
rclpy.init()
n = Node("checker")
cli = n.create_client(SetBool, "/gripper/set_closed")
if not cli.wait_for_service(timeout_sec=15):
    print("FAIL service /gripper/set_closed not found"); raise SystemExit
def call(v):
    f = cli.call_async(SetBool.Request(data=v)); rclpy.spin_until_future_complete(n, f, timeout_sec=5); return f.result()
r = call(True)
print("PASS close default" if r.success and r.message == "closed with 20.0 N" else f"FAIL close: {r.success} {r.message!r}")
r = call(False)
print("PASS open" if r.success and r.message == "opened" else f"FAIL open: {r.message!r}")
def sh(c):
    r = subprocess.run(c, shell=True, capture_output=True, text=True)
    return r.stdout + r.stderr
import time
for _ in range(5):   # retry: the CLI's graph cache can still list a node from an earlier run
    ok = "successful" in sh("ros2 param set /gripper max_force 35.0").lower()
    if ok:
        break
    time.sleep(1.0)
r = call(True)
print("PASS param change" if ok and r.message == "closed with 35.0 N" else f"FAIL after setting 35.0: {r.message!r}")
out = sh("ros2 param set /gripper max_force 80.0").lower()
val = sh("ros2 param get /gripper max_force")
print("PASS rejects 80" if "fail" in out and "35.0" in val else f"FAIL 80.0 must be rejected (got {out.strip()!r}, value {val.strip()!r})")
'''


def check_server(node_cmd="python gripper_server.py"):
    try:
        ros.start(node_cmd, log="gripper_check.log")
        ros.expect(ros.run_script(SERVER_CHECK, timeout=60), 4)
    finally:
        ros.stop_all()


def check_client(node_cmd="python client.py"):
    try:
        ros.start("python gripper_server.py", log="gripper_check.log")
        time.sleep(1.5)
        out = ros.ros(f"{node_cmd} close", timeout=30, show=False).strip().splitlines()
        assert out and out[-1] == "closed with 20.0 N", f"client printed {out[-1:] if out else 'nothing'}"
        out = ros.ros(f"{node_cmd} open", timeout=30, show=False).strip().splitlines()
        assert out and out[-1] == "opened", f"client printed {out[-1:] if out else 'nothing'}"
    finally:
        ros.stop_all()
