import math
import numpy as np

ANSWERS = {"M1": (0.0609, {"abs": 1e-4}), "M2": (1.0986, {"abs": 1e-3}), "M3": (16.667, {"abs": 0.01})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Saturation at 120 rad/s means the error persists, so an always-on integrator keeps growing",
    "After the setpoint drops, the integral must unwind: long saturation and overshoot",
    "Conditional integration stops integrating while saturated in the error's direction: fast recovery",
    "Back-calculation feeds (saturated - unsaturated) back into the integrator with a tracking gain",
]}
HINTS = {
    "alpha": "alpha = 1 - exp(-2 pi fc dt).",
    "pid": "Compute the candidate integral; keep it unless the unsaturated output exceeds a limit with the error pushing further.",
    "metrics": "np.argmax(y >= level) gives the first index reaching a level.",
}


def _sim(pid, profile, dt=1e-3, tau=0.5, K=10.0):
    a, w, ws = math.exp(-dt / tau), 0.0, []
    for sp in profile:
        u = pid.update(sp, w)
        assert -12 - 1e-9 <= u <= 12 + 1e-9, f"output {u} outside the clamp"
        w = a * w + (1 - a) * K * u
        ws.append(w)
    return np.array(ws)


class _Naive:
    def __init__(self, kp, ki, dt):
        self.kp, self.ki, self.dt, self.i = kp, ki, dt, 0.0

    def update(self, sp, y):
        e = sp - y
        self.i += self.ki * e * self.dt
        return min(12.0, max(-12.0, self.kp * e + self.i))


def check_alpha(fn):
    assert abs(fn(10, 1e-3) - (1 - math.exp(-2 * math.pi * 0.01))) < 1e-12
    assert abs(fn(1000, 1e-3) - (1 - math.exp(-2 * math.pi))) < 1e-12


def _recovery(ws):
    after = ws[6000:]   # the 50 rad/s segment starts at 6 s
    outside = np.nonzero(np.abs(after - 50.0) > 2.5)[0]
    return (outside[-1] + 1) * 1e-3 if len(outside) else 0.0


def check_pid(cls):
    w = _sim(cls(0.2, 2.0, 0.0, 1e-3, -12, 12), [100.0] * 2000)
    assert abs(w[-1] - 100.0) < 1.0, f"step to 100 ends at {w[-1]:.2f}"
    prof = [100.0] * 2000 + [150.0] * 4000 + [50.0] * 3000
    rec = _recovery(_sim(cls(0.2, 2.0, 0.0, 1e-3, -12, 12), prof))
    naive = _recovery(_sim(_Naive(0.2, 2.0, 1e-3), prof))
    assert rec < 1.5 and rec < 0.6 * naive, f"recovery after saturation {rec:.2f} s (always-integrating PID: {naive:.2f} s)"
    p = cls(0.05, 0.5, 0.01, 1e-3, -12, 12, d_cutoff_hz=50)
    u0 = p.update(100.0, 0.0)
    assert abs(u0 - (0.05 * 100 + 0.5 * 100 * 1e-3)) < 1e-6, f"first output {u0}: derivative kick or wrong P/I"
    p.update(100.0, 1.0)
    assert p.d_f < 0, "derivative of a rising measurement must be negative"




def check_metrics(fn):
    t = np.arange(0, 5, 1e-3)
    y = 1 - np.exp(-t / 0.5)
    r, o, s = fn(t, y, 1.0)
    assert abs(r - 0.5 * math.log(9)) < 2e-3 and o == 0 and abs(s - 0.5 * math.log(50)) < 2e-3, f"first order: {r}, {o}, {s}"
    wn, z = 10.0, 0.3
    wd = wn * math.sqrt(1 - z * z)
    y2 = 1 - np.exp(-z * wn * t) * (np.cos(wd * t) + z / math.sqrt(1 - z * z) * np.sin(wd * t))
    got, ref = fn(t, y2, 1.0), (0.132, 37.232409597569216, 1.124)   # precomputed on this exact sample grid
    assert all(abs(a - b) < 1e-9 for a, b in zip(got, ref)), f"second order: {got} vs {ref}"
    assert abs(got[1] - 100 * math.exp(-z * math.pi / math.sqrt(1 - z * z))) < 0.1, "overshoot vs theory"


def c_alpha(lib):
    from roboprep.cbind import Functions
    return (Functions(lib, "m03").lowpass_alpha,)


def c_pid(lib):
    import ctypes as C
    from roboprep.cbind import Functions

    class S(C.Structure):
        _fields_ = [(n, C.c_double) for n in ("kp", "ki", "kd", "dt", "u_min", "u_max", "alpha", "integ", "d_f", "prev_y")] + [("has_prev", C.c_bool)]
    f = Functions(lib, "m03", {"Pid": S})

    class PID:
        def __init__(self, kp, ki, kd, dt, u_min, u_max, d_cutoff_hz=50.0):
            self._s = S()
            f.pid_init(C.byref(self._s), kp, ki, kd, dt, u_min, u_max, d_cutoff_hz)
        d_f = property(lambda self: self._s.d_f)
        integ = property(lambda self: self._s.integ)

        def update(self, setpoint, y):
            return f.pid_update(C.byref(self._s), setpoint, y)
    return (PID,)


def c_metrics(lib):
    import ctypes as C
    import numpy as _np
    from roboprep.cbind import Functions, arr
    f = Functions(lib, "m03")

    def step_metrics(t, y, final):
        r, o, s = C.c_double(), C.c_double(), C.c_double()
        t, y = _np.asarray(t, float), _np.asarray(y, float)
        f.step_metrics(arr(C.c_double, t), arr(C.c_double, y), len(t), final, C.byref(r), C.byref(o), C.byref(s))
        return r.value, o.value, s.value
    return (step_metrics,)
