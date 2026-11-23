import math

ANSWERS = {"M1": 2.5, "M2": (0.3162, {"abs": 1e-4}), "M3": 3200}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Trapezoid has infinite jerk at the corners, exciting vibration",
    "S-curve when vibration, compliance or settling matter; costs a longer move and more computation",
    "DDA keeps an exact step ratio from one tick, so the path is straight and axes finish together",
    "Independent timers drift through rounding and jitter",
]}
HINTS = {
    "trapezoid": "Compare d with v_max^2 / a_max to pick trapezoid or triangle.",
    "ramp": "c_i = c_{i-1} - 2 c_{i-1} / (4 i + 1) for i = 1..n-1.",
    "dda": "err += minor each tick; when 2*err >= major step the minor axis and subtract major.",
}


def check_trapezoid(tr, pos):
    assert all(abs(a - b) < 1e-9 for a, b in zip(tr(1.0, 0.5, 1.0), (0.5, 1.5, 2.5, 0.5))), f"trapezoid: {tr(1.0, 0.5, 1.0)}"
    t_a, t_c, t_f, vp = tr(0.1, 1.0, 1.0)
    assert t_c == 0 and abs(vp - math.sqrt(0.1)) < 1e-9 and abs(t_f - 2 * math.sqrt(0.1)) < 1e-9, "triangle case"
    for d, v, a in [(1.0, 0.5, 1.0), (0.1, 1.0, 1.0)]:
        tf = tr(d, v, a)[2]
        ts = [k * tf / 400 for k in range(401)]
        p = [pos(t, d, v, a) for t in ts]
        assert abs(p[0]) < 1e-9 and abs(p[-1] - d) < 1e-9, "starts at 0, ends at d"
        vel = [(p[k + 1] - p[k]) / (ts[1]) for k in range(400)]
        assert max(vel) <= v * 1.001 + 1e-9 and all(x >= -1e-9 for x in vel), "velocity exceeds v_max or goes negative"
        acc = [(vel[k + 1] - vel[k]) / ts[1] for k in range(399)]
        assert max(abs(x) for x in acc) <= a * 1.05 + 1e-6, "acceleration exceeds a_max"


def check_ramp(fn):
    f, alpha, acc = 1e6, 2 * math.pi / 3200, 50.0
    c = fn(200, f, alpha, acc)
    assert len(c) == 200 and abs(c[0] - 0.676 * f * math.sqrt(2 * alpha / acc)) < 1e-6, "c0 wrong"
    k = f * math.sqrt(2 * alpha / acc)
    worst = max(abs(c[i] / (k * (math.sqrt(i + 1) - math.sqrt(i))) - 1) for i in range(10, 200))
    assert worst < 0.01, f"recurrence drifts {worst * 100:.2f}% from the exact delays"
    assert all(c[i + 1] < c[i] for i in range(199)), "delays must shrink while accelerating"


def check_dda(fn):
    for dx, dy in [(10, 3), (3, 10), (7, 7), (100, 37), (5, 0)]:
        s = fn(dx, dy)
        assert sum(a for a, _ in s) == dx and sum(b for _, b in s) == dy, f"({dx}, {dy}): totals wrong"
        x = y = 0
        worst = 0.0
        for a, b in s:
            x, y = x + a, y + b
            if dx >= dy:
                worst = max(worst, abs(y - x * dy / dx))
            else:
                worst = max(worst, abs(x - y * dx / dy))
        assert worst <= 0.5 + 1e-9, f"({dx}, {dy}): strays {worst:.2f} steps from the line"


def c_trapezoid(lib):
    import ctypes as C
    from roboprep.cbind import Functions
    f = Functions(lib, "m05")

    def trapezoid(d, v_max, a_max):
        r = [C.c_double() for _ in range(4)]
        f.trapezoid(d, v_max, a_max, *[C.byref(x) for x in r])
        return tuple(x.value for x in r)
    return trapezoid, f.trap_position


def c_ramp(lib):
    import ctypes as C
    from roboprep.cbind import Functions, out
    f = Functions(lib, "m05")

    def austin_delays(n, f_timer, alpha, accel):
        buf = out(C.c_double, n)
        f.austin_delays(n, f_timer, alpha, accel, buf)
        return list(buf[:n])
    return (austin_delays,)


def c_dda(lib):
    import ctypes as C
    from roboprep.cbind import Functions, out
    f = Functions(lib, "m05")

    def dda(dx, dy):
        cap = max(dx, dy)
        sx, sy = out(C.c_uint8, cap), out(C.c_uint8, cap)
        n = f.dda(dx, dy, sx, sy, cap)
        return [(sx[k], sy[k]) for k in range(n)]
    return (dda,)
