import json
import os
from roboprep import ros

ANSWERS = {"M1": (60, {"rel": 0.1}), "M2": 1.5}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "--clock publishes the recorded time on /clock; use_sim_time makes nodes use it for now(), timers, stamps, TF",
    "Without it, replayed stamps are old while node time is now: TF extrapolation errors, synchronizers drop data",
    "Timeouts and timers run at the wrong speed relative to the data (especially with --rate)",
]}
HINTS = {
    "record": "ros.start('ros2 bag record -o run1 /joint1/temperature', log='record.log').",
    "analyze": "topic, data, t_ns = reader.read_next(); deserialize_message(data, get_message(types[topic])).",
}


ROS_CPP = {}   # check name -> (executable, dependencies) for C++ nodes
ROS_CPP["analyze"] = ("analyze_bag", ['rclcpp', 'rosbag2_cpp', 'std_msgs'])


def setup(lab):
    ros.ensure_ros()


REF = r'''
import json, sys, rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
r = rosbag2_py.SequentialReader()
r.open(rosbag2_py.StorageOptions(uri=sys.argv[1], storage_id=""), rosbag2_py.ConverterOptions("", ""))
types = {t.name: t.type for t in r.get_all_topics_and_types()}
s, v = [], []
while r.has_next():
    topic, data, t = r.read_next()
    if topic == "/joint1/temperature":
        s.append(t * 1e-9); v.append(deserialize_message(data, get_message(types[topic])).data)
print(json.dumps({"count": len(v), "rate_hz": (len(v) - 1) / (s[-1] - s[0]), "mean": sum(v) / len(v), "min": min(v), "max": max(v)}))
'''


def check_record():
    assert os.path.isdir("run1"), "no run1 folder: was ros2 bag record started with -o run1?"
    info = ros.ros("ros2 bag info run1", show=False)
    assert "/joint1/temperature" in info, "the bag has no /joint1/temperature topic:\n" + info[-600:]
    import re
    m = re.search(r"Messages:\s+(\d+)", info)
    assert m and int(m.group(1)) >= 40, f"too few messages recorded: {m.group(1) if m else '?'}"


def check_analyze(node_cmd="python analyze_bag.py"):
    ref = json.loads(ros.run_script(REF.replace("sys.argv[1]", "'run1'"), "_ref_bag.py", timeout=60).strip().splitlines()[-1])
    out = ros.ros(f"{node_cmd} {os.path.abspath('run1')}", timeout=60, show=False).strip().splitlines()
    assert out, "analyze_bag.py printed nothing"
    got = json.loads(out[-1])
    for k in ("count", "rate_hz", "mean", "min", "max"):
        assert k in got, f"missing key {k}"
        assert abs(float(got[k]) - float(ref[k])) <= 1e-6 * max(1.0, abs(ref[k])), f"{k}: {got[k]} vs {ref[k]}"
