from roboprep import clab

ANSWERS = {"M1": 1000, "M2": -4096, "M3": 0.25}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "170 MHz / 20 kHz = 8500 counts per period",
    "PSC = 0, ARR = 8499: maximum duty resolution (8500 steps, about 13 bits)",
    "+1 because the prescaler divides by PSC+1 and the counter has ARR+1 states (0..ARR)",
    "Mentions a trade-off: larger PSC only needed for longer periods; center-aligned halves the frequency",
]}
HINTS = {
    "q15": "Multiply in int32_t, add 1 << 14, shift right 15, clamp the top to 32767.",
    "timer": "For each PSC, ARR = round(f_clk / f / (PSC+1)) - 1; keep the best error.",
}


def check_q15():
    clab.run_ctest(["q15.c"], "c03_q15_test.c").require(8)




# smallest achievable error and the PSC that keeps the most resolution, precomputed
BEST = {(170e6, 1000): (0.0, 3), (170e6, 20000): (0.0, 0), (16e6, 1): (0.0, 249), (170e6, 7): (3.705882551940931e-07, 3868),
        (72e6, 50): (0.0, 23)}


def check_timer(fn):
    for f_clk, f in [(170e6, 1000), (170e6, 20000), (16e6, 1), (170e6, 7), (72e6, 50)]:
        psc, arr = fn(f_clk, f)
        assert 0 <= psc <= 65535 and 0 <= arr <= 65535, f"out of range for {f} Hz: {psc}, {arr}"
        err = abs(f_clk / ((psc + 1) * (arr + 1)) - f)
        best = BEST[(f_clk, f)]
        assert err <= best[0] + 1e-9, f"{f_clk/1e6:g} MHz -> {f} Hz: error {err:.4g} Hz, best possible {best[0]:.4g}"
        assert psc <= best[1], f"{f} Hz: PSC {psc} works but {best[1]} keeps more resolution"


def c_timer(lib):
    import ctypes as C
    from roboprep.cbind import Functions
    f = Functions(lib, "c03")

    def timer_config(f_clk, f_target):
        p, a = C.c_uint16(), C.c_uint16()
        f.timer_config(f_clk, f_target, C.byref(p), C.byref(a))
        return p.value, a.value
    return (timer_config,)
