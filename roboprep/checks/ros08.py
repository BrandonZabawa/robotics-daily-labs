import time
from roboprep import ros

ANSWERS = {"M1": 2, "M2": 18}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Hardware interface reads states and writes commands; controllers implement control laws on named interfaces",
    "Resource manager connects them by name and arbitrates command interfaces; controllers swap at runtime",
    "Real hardware: a SystemInterface plugin (configure/activate open the bus, read/write convert counts and commands)",
    "Only the <plugin> line and hardware parameters change; controllers and YAML stay the same",
]}
HINTS = {
    "loop": "step = max_vel * dt; command += clamp(target - command, -step, step). Loop: read, update, write.",
    "controllers": "type: joint_state_broadcaster/JointStateBroadcaster and forward_command_controller/ForwardCommandController.",
}


def setup(lab):
    ros.ensure_ros(extras=("control",))


class _Hw:
    def __init__(self, joints):
        self.state = {j: 0.0 for j in joints}
        self.command = {j: 0.0 for j in joints}
        self.calls = []

    def read(self):
        self.calls.append("read")
        self.state.update(self.command)

    def write(self):
        self.calls.append("write")


def check_loop(ctrl_cls, run):
    hw = _Hw(["a", "b"])
    c = ctrl_cls(["a", "b"], max_vel=1.0)
    c.target = {"a": 0.5, "b": -2.0}
    seen = []
    orig = c.update

    def spy(state, command, dt):
        hw.calls.append("update")
        before = dict(command)
        orig(state, command, dt)
        seen.append(max(abs(command[j] - before[j]) for j in command) / dt)
    c.update = spy
    run(hw, c, 100, 1.0)
    assert hw.calls[:3] == ["read", "update", "write"] and len(hw.calls) == 300, f"call order {hw.calls[:6]}..., {len(hw.calls)} calls"
    assert max(seen) <= 1.0 + 1e-9, f"velocity limit exceeded: {max(seen):.3f} rad/s"
    assert abs(hw.command["a"] - 0.5) < 1e-9, f"joint a should reach 0.5, is {hw.command['a']:.3f}"
    assert abs(hw.command["b"] + 1.0) < 1e-6, f"joint b moves at 1 rad/s for 1 s: expected -1.0, got {hw.command['b']:.3f}"


CTRL = r'''
import subprocess, time, rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray
rclpy.init()
n = Node("checker")
js = {}
n.create_subscription(JointState, "/joint_states", lambda m: js.update(dict(zip(m.name, m.position))), 10)
pub = n.create_publisher(Float64MultiArray, "/forward_position_controller/commands", 10)
out = subprocess.run("ros2 control list_controllers", shell=True, capture_output=True, text=True).stdout
ok = all(any(c in l and "active" in l for l in out.splitlines()) for c in ("joint_state_broadcaster", "forward_position_controller"))
print("PASS both controllers active" if ok else "FAIL controllers:\n" + out)
t0 = time.time()
while time.time() - t0 < 3:
    pub.publish(Float64MultiArray(data=[0.7, -0.4]))
    rclpy.spin_once(n, timeout_sec=0.1)
good = abs(js.get("shoulder", 9) - 0.7) < 1e-3 and abs(js.get("elbow", 9) + 0.4) < 1e-3
print("PASS joints follow commands" if good else f"FAIL joint_states {js}")
'''


def check_controllers():
    try:
        ros.start('ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:="$(cat arm_control.urdf)"',
                  log="rsp_check.log")
        ros.start("ros2 run controller_manager ros2_control_node --ros-args --params-file controllers.yaml "
                  "-r /controller_manager/robot_description:=/robot_description", log="cm_check.log")
        time.sleep(3)
        sp = ros.ros("timeout 30 ros2 run controller_manager spawner joint_state_broadcaster forward_position_controller",
                     timeout=40, show=False)
        assert "activated forward_position_controller" in sp, "spawner could not activate the controllers:\n" + sp[-800:]
        ros.expect(ros.run_script(CTRL, "_ctrl.py", timeout=40), 2)
    finally:
        ros.stop_all()


def c_loop(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr, out
    V = C.CFUNCTYPE(None, C.c_void_p)
    U = C.CFUNCTYPE(None, C.c_void_p, C.c_double)

    class S(C.Structure):
        _fields_ = [("n", C.c_size_t), ("max_vel", C.c_double), ("target", C.c_double * 8)]

    class Ops(C.Structure):
        _fields_ = [("read", V), ("update", U), ("write", V), ("ctx", C.c_void_p)]
    f = Functions(lib, "ros08", {"RateLimitedPosition": S, "LoopOps": Ops})

    class RateLimitedPosition:
        def __init__(self, joints, max_vel):
            self.joints, self.max_vel, self.target = list(joints), max_vel, {j: 0.0 for j in joints}
            self._s = S()
            f.rlp_init(C.byref(self._s), len(self.joints), max_vel)

        def update(self, state, command, dt):
            for k, j in enumerate(self.joints):
                self._s.target[k] = self.target[j]
            cmd = arr(C.c_double, [command[j] for j in self.joints])
            f.rlp_update(C.byref(self._s), arr(C.c_double, [state[j] for j in self.joints]), cmd, dt)
            for k, j in enumerate(self.joints):
                command[j] = cmd[k]

    def run_loop(hw, controller, rate_hz, seconds):
        cbs = (V(lambda _: hw.read()), U(lambda _, dt: controller.update(hw.state, hw.command, dt)), V(lambda _: hw.write()))
        f.run_loop(C.byref(Ops(*cbs, None)), rate_hz, seconds)
    return RateLimitedPosition, run_loop
