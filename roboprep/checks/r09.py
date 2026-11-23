ANSWERS = {"M1": 0.32, "M2": 0.64}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Static partitioning gives the safety RTOS its own core, memory and devices, enforced in hardware",
    "A Linux crash or overload cannot affect it; it can be certified separately",
    "Costs: configuration, residual interference through shared caches and memory, device splitting, debugging",
    "All-Linux is simpler but not certifiable and a kernel fault takes the monitor down",
]}
HINTS = {
    "dvfs": "E = (P_static + C V^2 f) * (N / f) + P_idle * (T - N / f); skip OPPs that miss the window.",
    "idle": "Filter by residency <= predicted and exit latency <= limit, then take the lowest power.",
}

OPPS = [(400e6, 0.70, 0.02), (800e6, 0.80, 0.03), (1.2e9, 0.95, 0.05), (1.8e9, 1.10, 0.08)]


def check_dvfs(energy, best):
    e = energy((1e9, 1.0, 0.1), 5e8, 1.0, 1e-9, 0.01)
    assert abs(e - ((0.1 + 1.0) * 0.5 + 0.01 * 0.5)) < 1e-12, f"energy formula: {e}"
    assert best(OPPS, 2e8, 1.0, 1e-9, 0.005) == OPPS[0], "light job: the lowest voltage point wins"
    assert best(OPPS, 1.0e9, 1.0, 1e-9, 0.005) == OPPS[2], "heavy job: the slowest point that meets the deadline"
    assert best(OPPS, 1e10, 1.0, 1e-9, 0.005) is None, "nothing can finish 1e10 cycles in 1 s"
    hot = [(400e6, 0.9, 0.5), (1.8e9, 1.0, 0.5)]
    assert best(hot, 3e8, 1.0, 1e-10, 0.001) == hot[1], "with high leakage, race to idle wins"


STATES = [
    {"name": "WFI", "exit_us": 1, "residency_us": 1, "power_mw": 120},
    {"name": "C2", "exit_us": 50, "residency_us": 200, "power_mw": 40},
    {"name": "C3", "exit_us": 300, "residency_us": 2000, "power_mw": 5},
]


def check_idle(fn):
    assert fn(STATES, 5000, 1000) == "C3"
    assert fn(STATES, 5000, 100) == "C2", "latency limit rules out C3"
    assert fn(STATES, 150, 1000) == "WFI", "too short an idle for C2"
    assert fn(STATES, 500, 1000) == "C2"


def c_dvfs(lib):
    import ctypes as C
    from roboprep.cbind import Functions

    class O(C.Structure):
        _fields_ = [("f", C.c_double), ("v", C.c_double), ("p_static", C.c_double)]
    f = Functions(lib, "r09", {"Opp": O})

    def job_energy(opp, cycles, window, c_eff, p_idle):
        return f.job_energy(C.byref(O(*opp)), cycles, window, c_eff, p_idle)

    def best_opp(opps, cycles, window, c_eff, p_idle):
        i = f.best_opp((O * len(opps))(*[O(*o) for o in opps]), len(opps), cycles, window, c_eff, p_idle)
        return None if i < 0 else opps[i]
    return job_energy, best_opp


def c_idle(lib):
    import ctypes as C
    from roboprep.cbind import Functions

    class S(C.Structure):
        _fields_ = [("name", C.c_char_p), ("exit_us", C.c_double), ("residency_us", C.c_double), ("power_mw", C.c_double)]
    f = Functions(lib, "r09", {"IdleState": S})

    def pick_idle(states, predicted, limit):
        names = [s["name"].encode() for s in states]
        arr = (S * len(states))(*[S(n, s["exit_us"], s["residency_us"], s["power_mw"]) for n, s in zip(names, states)])
        return states[f.pick_idle(arr, len(states), predicted, limit)]["name"]
    return (pick_idle,)
