ANSWERS = {"M1": 20000, "M2": 85, "M3": 500}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Complementary switches: slow turn-off means both conduct briefly and short the bus (shoot-through)",
    "Dead time delays each turn-on so both switches are off for a short gap",
    "During the gap the diode sets the voltage by current direction: error about Vdc * t_dead / T_pwm",
    "Compensation: feed-forward voltage with the sign of the phase current",
]}
HINTS = {
    "pwm": "Build the up-down counter list, the reference, then delay each 0->1 edge by `dead` samples.",
    "capture": "Use (b - a) % (arr + 1) for every difference.",
}


def check_pwm(fn):
    for arr, ccr, dead in [(100, 40, 5), (200, 150, 12), (50, 25, 0)]:
        hi, lo = fn(arr, ccr, dead, periods=2)
        n = 2 * arr * 2
        assert len(hi) == len(lo) == n, f"length {len(hi)}, expected {n}"
        assert not any(h and l for h, l in zip(hi, lo)), "high and low on at the same time: shoot-through"
        ref = [1 if c < ccr else 0 for c in (list(range(0, arr + 1)) + list(range(arr - 1, 0, -1))) * 2]
        assert sum(hi) == sum(ref) - dead * sum(1 for i in range(1, n) if ref[i] and not ref[i - 1]) - (dead if ref[0] else 0), \
            f"arr={arr}, ccr={ccr}, dead={dead}: high-side on-time wrong"
        gaps = [i for i in range(n) if not hi[i] and not lo[i]]
        assert len(gaps) >= dead * 3 if dead else len(gaps) == 0, "dead-time gaps missing or present when dead = 0"


def check_capture(fn):
    f, d = fn(65000, 65500, 1464, 65535, 1e6)
    assert abs(f - 500) < 1e-9 and abs(d - 0.25) < 1e-9, f"wrapped capture: {f}, {d}"
    f, d = fn(100, 600, 1100, 65535, 170e6)
    assert abs(f - 170e3) < 1e-6 and abs(d - 0.5) < 1e-9, f"plain capture: {f}, {d}"


def c_pwm(lib):
    import ctypes as C
    from roboprep.cbind import Functions, out
    f = Functions(lib, "m01")

    def complementary_pwm(arr, ccr, dead, periods=2):
        cap = 2 * arr * periods
        hi, lo = out(C.c_uint8, cap), out(C.c_uint8, cap)
        n = f.complementary_pwm(arr, ccr, dead, periods, hi, lo, cap)
        return list(hi[:n]), list(lo[:n])
    return (complementary_pwm,)


def c_capture(lib):
    import ctypes as C
    from roboprep.cbind import Functions
    f = Functions(lib, "m01")

    def capture_measure(r1, fa, r2, arr, f_tim):
        fr, d = C.c_double(), C.c_double()
        f.capture_measure(r1, fa, r2, arr, f_tim, C.byref(fr), C.byref(d))
        return fr.value, d.value
    return (capture_measure,)
