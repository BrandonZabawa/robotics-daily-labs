ANSWERS = {"M1": (1.728, {"abs": 1e-3}), "M2": (22.7, {"abs": 0.05}), "M3": 340}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "At 10 MHz only half a period (50 ns) exists between launch and sample",
    "Budget: slave clock-to-out + cable delay both ways + setup, plus slower edges from capacitance",
    "Ringing and crosstalk on an unshielded ribbon reduce margin further",
    "Fixes: lower clock, shorter or twisted cable with grounds, series termination, delayed sampling, move the interface",
]}
HINTS = {
    "pll": "Loop M, then R; N = f_target * R * M / f_in must be an integer in range and the VCO in 96..344 MHz.",
    "timing": "Formulas are in the map above.",
}


def _valid(f_in, res, f_t):
    m, n, r = res
    ref, vco = f_in / m, f_in / m * n
    return 2.66e6 <= ref <= 16e6 and 96e6 <= vco <= 344e6 and r in (2, 4, 6, 8) and 8 <= n <= 127 and abs(vco / r - f_t) < 1e-3


def check_pll(fn):
    assert fn(8e6, 170e6) == (2, 85, 2), f"8 MHz -> 170 MHz: {fn(8e6, 170e6)}"
    for f_in, f_t in [(24e6, 170e6), (16e6, 150e6), (12e6, 48e6)]:
        res = fn(f_in, f_t)
        assert res and _valid(f_in, res, f_t), f"{f_in/1e6:g} -> {f_t/1e6:g} MHz: {res}"
    assert fn(8e6, 171.3e6) is None, "171.3 MHz is not reachable exactly"


def check_timing(drift, spi, setup, hold):
    assert abs(drift(20) - 1.728) < 1e-9
    assert abs(spi(15e-9, 1e-9, 5e-9) - 1 / 44e-9) < 1
    assert abs(setup(5e-9, 0.5e-9, 3.6e-9, 0.4e-9) - 0.5e-9) < 1e-15
    assert abs(setup(5e-9, 0.5e-9, 3.6e-9, 0.4e-9, skew=0.2e-9) - 0.7e-9) < 1e-15
    assert abs(hold(0.5e-9, 0.1e-9, 0.3e-9, skew=0.4e-9) + 0.1e-9) < 1e-15, "negative hold slack with large skew"


def c_pll(lib):
    import ctypes as C
    from roboprep.cbind import Functions
    f = Functions(lib, "h03")

    def pll_config(f_in, f_target):
        m, n, r = C.c_int(), C.c_int(), C.c_int()
        return (m.value, n.value, r.value) if f.pll_config(f_in, f_target, C.byref(m), C.byref(n), C.byref(r)) else None
    return (pll_config,)


def c_timing(lib):
    from roboprep.cbind import Functions
    f = Functions(lib, "h03")
    return (f.drift_s_per_day, f.spi_max_clock,
            lambda period, t_cq, t_logic, t_su, skew=0.0: f.setup_slack(period, t_cq, t_logic, t_su, skew),
            lambda t_cq, t_logic_min, t_hold, skew=0.0: f.hold_slack(t_cq, t_logic_min, t_hold, skew))
