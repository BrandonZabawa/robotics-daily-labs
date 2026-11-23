import numpy as np

ANSWERS = {"M1": 1.2, "M2": 0.375, "M3": 1.2}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "During the dead time the output does not react, so the controller acts blind and overcorrects",
    "Dead time adds phase lag growing with frequency, limiting stable bandwidth",
    "SIMC ties tau_c to theta (Kc = tau / (2 K theta)): larger theta forces lower gain; reducing delay is often worth more",
]}
HINTS = {
    "fit": "Normalize to 0..1, find the 0.283 and 0.632 crossings with linear interpolation.",
    "simc": "Kc = tau / (K (tau_c + theta)), Ti = min(tau, 4 (tau_c + theta)).",
    "cascade": "v_sp = clamp(kp_pos * error); inner PI like M03 with i_max as the clamp.",
}


def check_fit(fn):
    for K, tau, theta in [(2.0, 1.2, 0.8), (0.5, 3.0, 0.2), (10.0, 0.4, 0.05)]:
        t = np.arange(0, theta + 8 * tau, 1e-3)
        y = 5.0 + np.where(t >= theta, K * 3.0 * (1 - np.exp(-(t - theta) / tau)), 0.0)
        k, ta, th = fn(t, y, 3.0)
        assert abs(k - K) / K < 0.01 and abs(ta - tau) / tau < 0.02 and abs(th - theta) < 0.02 * tau + 2e-3, \
            f"true (K, tau, theta) = {(K, tau, theta)}, fitted {(round(k, 3), round(ta, 3), round(th, 3))}"


def check_simc(fn):
    kc, ti = fn(2.0, 1.2, 0.8)
    assert abs(kc - 0.375) < 1e-9 and abs(ti - 1.2) < 1e-9, f"{kc}, {ti}"
    kc, ti = fn(1.0, 10.0, 0.5, tau_c=0.5)
    assert abs(kc - 10.0) < 1e-9 and abs(ti - 4.0) < 1e-9, f"slow plant: {kc}, {ti}"


def check_cascade(cls):
    c = cls(6.0, 1.5, 8.0, 4.0, 2.0, 1e-3)
    pos = vel = 0.0
    vmax_seen = imax_seen = 0.0
    for k in range(4000):
        i = c.update(3.0, pos, vel)
        imax_seen = max(imax_seen, abs(i))
        vel += (10 * i - vel - (5.0 if k > 3000 else 0.0)) * 1e-3
        pos += vel * 1e-3
        vmax_seen = max(vmax_seen, abs(vel))
        if k == 2500:
            at_25 = pos
    assert imax_seen <= 2.0 + 1e-9, f"current {imax_seen:.2f} A exceeds i_max"
    assert vmax_seen <= 4.0 * 1.05, f"velocity {vmax_seen:.2f} rad/s exceeds v_max"
    assert abs(at_25 - 3.0) < 0.01, f"position at 2.5 s is {at_25:.4f}, want 3.0 +- 0.01"
    assert abs(pos - 3.0) < 0.02, f"with the load disturbance the final position is {pos:.4f}"


def c_fit(lib):
    import ctypes as C
    import numpy as _np
    from roboprep.cbind import Functions, arr
    f = Functions(lib, "m04")

    def fit_fopdt(t, y, du):
        k, ta, th = C.c_double(), C.c_double(), C.c_double()
        t, y = _np.asarray(t, float), _np.asarray(y, float)
        f.fit_fopdt(arr(C.c_double, t), arr(C.c_double, y), len(t), du, C.byref(k), C.byref(ta), C.byref(th))
        return k.value, ta.value, th.value
    return (fit_fopdt,)


def c_simc(lib):
    import ctypes as C
    from roboprep.cbind import Functions
    f = Functions(lib, "m04")

    def simc_pi(K, tau, theta, tau_c=None):
        kc, ti = C.c_double(), C.c_double()
        f.simc_pi(K, tau, theta, -1.0 if tau_c is None else tau_c, C.byref(kc), C.byref(ti))
        return kc.value, ti.value
    return (simc_pi,)


def c_cascade(lib):
    import ctypes as C
    from roboprep.cbind import Functions

    class S(C.Structure):
        _fields_ = [(n, C.c_double) for n in ("kp_pos", "kp_vel", "ki_vel", "v_max", "i_max", "dt", "integ")]
    f = Functions(lib, "m04", {"Cascade": S})

    class Cascade:
        def __init__(self, *args):
            self._s = S()
            f.cascade_init(C.byref(self._s), *args)

        def update(self, pos_sp, pos, vel):
            return f.cascade_update(C.byref(self._s), pos_sp, pos, vel)
    return (Cascade,)
