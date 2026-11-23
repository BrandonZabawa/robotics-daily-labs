import math

ANSWERS = {"M1": 0.3, "M2": (12.57, {"abs": 0.01}), "M3": (13.86, {"abs": 0.01})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Back-EMF is proportional to speed and meets the available SVM voltage near 3300 rpm",
    "With R and L drops there is no voltage margin left to drive q current, so torque collapses",
    "Option 1: raise the bus voltage",
    "Option 2: flux weakening with negative i_d, costing current and torque per amp",
]}
HINTS = {
    "transforms": "beta = (ib - ic) / sqrt(3); Park rotates by -theta, inverse Park by +theta.",
    "svm": "Phase voltages from inverse Clarke, offset = -(max + min) / 2, duty = 0.5 + v / vdc.",
    "current_loop": "PI on each axis, add -w_e L i_q to vd and w_e (L i_d + lambda) to vq, scale if too long.",
}


def check_transforms(clarke, park, inv_park):
    th = 0.7
    ia, ib, ic = [3.0 * math.cos(th - k * 2 * math.pi / 3) for k in range(3)]
    a, b = clarke(ia, ib, ic)
    assert abs(a - 3 * math.cos(th)) < 1e-9 and abs(b - 3 * math.sin(th)) < 1e-9, "amplitude-invariant Clarke"
    d, q = park(a, b, th)
    assert abs(d - 3.0) < 1e-9 and abs(q) < 1e-9, f"aligned rotor: (d, q) = ({d:.3f}, {q:.3f}), want (3, 0)"
    d, q = park(a, b, th - math.pi / 2)
    assert abs(d) < 1e-9 and abs(q - 3.0) < 1e-9, "current leading the rotor by 90 degrees is pure q"
    x, y = inv_park(1.2, -0.4, 2.1)
    assert all(abs(u - v) < 1e-12 for u, v in zip(park(x, y, 2.1), (1.2, -0.4))), "inverse Park must undo Park"


def check_svm(svm):
    vdc = 24.0
    for th in [0.0, 0.3, 1.0, 2.5, 4.0]:
        amp = vdc / math.sqrt(3) * 0.999
        da, db, dc = svm(amp * math.cos(th), amp * math.sin(th), vdc)
        assert all(0 <= x <= 1 for x in (da, db, dc)), "duties outside [0, 1]"
        va, vb, vc = (da - 0.5) * vdc, (db - 0.5) * vdc, (dc - 0.5) * vdc
        line_ab = va - vb
        want_ab = amp * math.cos(th) - (-0.5 * amp * math.cos(th) + math.sqrt(3) / 2 * amp * math.sin(th))
        assert abs(line_ab - want_ab) < 1e-6, f"line voltage wrong at angle {th}: full Vdc/sqrt(3) must be linear"
    assert all(abs(x - 0.5) < 1e-12 for x in svm(0, 0, vdc)), "zero voltage = 50% duty on all phases"


def _simulate(ctrl_cls):
    R, L, lam, p, J, B, dt = 0.5, 0.5e-3, 0.01, 4, 1e-5, 1e-5, 50e-6
    wc = 2 * math.pi * 1000
    c = ctrl_cls(L * wc, R * wc, L, lam, dt, 24 / math.sqrt(3))
    i_d = i_q = w_m = 0.0
    log = []
    for k in range(int(0.02 / dt)):
        w_e = p * w_m
        vd, vq = c.update(0.0, 2.0, i_d, i_q, w_e)
        assert math.hypot(vd, vq) <= 24 / math.sqrt(3) + 1e-9, "voltage vector exceeds the limit"
        for _ in range(10):  # integrate the plant finer than the control period
            h = dt / 10
            did = (vd - R * i_d + w_e * L * i_q) / L
            diq = (vq - R * i_q - w_e * L * i_d - w_e * lam) / L
            i_d, i_q = i_d + did * h, i_q + diq * h
            w_m += (1.5 * p * lam * i_q - B * w_m) / J * h
            w_e = p * w_m
        log.append((k * dt, i_d, i_q, w_m))
    return log


def check_current_loop(cls):
    log = _simulate(cls)
    after = [r for r in log if r[0] >= 0.002 and r[3] * 4 * 0.01 < 0.8 * 24 / math.sqrt(3)]
    assert after, "motor never ran"
    assert all(abs(r[2] - 2.0) < 0.1 for r in after), f"iq should hold 2 A after 2 ms; min {min(r[2] for r in after):.2f}"
    assert max(abs(r[1]) for r in log) < 0.15, f"id should stay near 0 (decoupling); peak {max(abs(r[1]) for r in log):.2f} A"


def c_transforms(lib):
    import ctypes as C
    from roboprep.cbind import Functions
    f = Functions(lib, "m07")

    def two(fn, *args):
        a, b = C.c_double(), C.c_double()
        fn(*args, C.byref(a), C.byref(b))
        return a.value, b.value
    return (lambda ia, ib, ic: two(f.clarke, ia, ib, ic), lambda a, b, th: two(f.park, a, b, th),
            lambda d, q, th: two(f.inv_park, d, q, th))


def c_svm(lib):
    import ctypes as C
    from roboprep.cbind import Functions, out
    f = Functions(lib, "m07")

    def svm(va, vb, vdc):
        d = out(C.c_double, 3)
        f.svm(va, vb, vdc, d)
        return tuple(d[:3])
    return (svm,)


def c_current_loop(lib):
    import ctypes as C
    from roboprep.cbind import Functions

    class S(C.Structure):
        _fields_ = [(n, C.c_double) for n in ("kp", "ki", "L", "lam", "dt", "v_max", "id_int", "iq_int")]
    f = Functions(lib, "m07", {"FocCurrentController": S})

    class FocCurrentController:
        def __init__(self, kp, ki, L, lam, dt, v_max):
            self._s = S()
            f.foc_init(C.byref(self._s), kp, ki, L, lam, dt, v_max)

        def update(self, id_ref, iq_ref, i_d, i_q, w_e):
            vd, vq = C.c_double(), C.c_double()
            f.foc_update(C.byref(self._s), id_ref, iq_ref, i_d, i_q, w_e, C.byref(vd), C.byref(vq))
            return vd.value, vq.value
    return (FocCurrentController,)
