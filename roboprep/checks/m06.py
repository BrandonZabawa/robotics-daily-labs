ANSWERS = {"M1": 0.4, "M2": 0.0625}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "The switch triggers late by an amount that grows with speed (hysteresis, sampling)",
    "The fast pass finds the switch; the slow re-approach makes the trigger point small and repeatable",
    "The index pulse is a much sharper once-per-revolution mark; zero on it after the switch",
    "Repeatability becomes one encoder count instead of the switch's",
]}
HINTS = {
    "supervisor": "Faulted: return (False, actual). Dead-man held: move cmd toward target by at most v_max*dt. Count over-current cycles.",
    "homing": "Each state returns its velocity; transitions on switch edges; check the timeout first.",
}


def check_supervisor(cls):
    dt = 1e-3
    s = cls(ferr_max=0.05, i_limit=2.0, i_cycles=5, v_max=1.0, dt=dt)
    act = 0.0
    for _ in range(100):
        en, cmd = s.update(1.0, act, 0.5, True)
        act += (cmd - act) * 0.5
    assert en and abs(cmd - 0.1) < 1e-9, f"velocity limit: after 0.1 s cmd should be 0.1, is {cmd:.4f}"
    held = cmd
    for _ in range(50):
        en, cmd = s.update(1.0, act, 0.5, False)
        act += (cmd - act) * 0.5
    assert en and abs(cmd - held) < 1e-12, "dead-man released: command must hold"
    for k in range(4):
        en, _ = s.update(1.0, act, 3.0, True)
    assert en and s.fault is None, "4 over-current cycles must not trip (needs 5)"
    s.update(1.0, act, 0.5, True)
    for k in range(5):
        en, _ = s.update(1.0, act, 3.0, True)
    assert not en and s.fault == "COLLISION", f"5 consecutive over-current cycles must trip COLLISION (fault={s.fault})"
    en, _ = s.update(1.0, act, 0.0, True)
    assert not en, "fault must latch even after the current drops"
    s.reset(act)
    en, cmd = s.update(act, act, 0.0, True)
    assert en and abs(cmd - act) < 1e-12, "reset must be bumpless (command = actual)"
    for _ in range(200):
        en, cmd = s.update(5.0, act, 0.0, True)     # actual stuck: jammed axis
        if not en:
            break
    assert s.fault == "FOLLOWING_ERROR", f"a jammed axis must trip FOLLOWING_ERROR (fault={s.fault})"


def _home(cls, switch_pos, start, v_fast=0.2, v_slow=0.01, dt=1e-3, timeout=30.0):
    h = cls(v_fast, v_slow, timeout, dt)
    pos = start
    for _ in range(int(timeout / dt) + 10):
        v = h.step(pos <= switch_pos, pos)
        pos += v * dt
        if h.state in ("DONE", "FAILED"):
            break
    return h


def check_homing(cls):
    for sw, start in [(-0.3, 0.5), (0.0, 0.25), (1.2, 2.0)]:
        h = _home(cls, sw, start)
        assert h.state == "DONE", f"switch at {sw}, start {start}: ended in {h.state}"
        assert abs(h.zero - sw) <= 0.01 * 1e-3 * 2 + 1e-12, f"zero {h.zero:.6f} vs switch {sw} (slow approach should land within one slow step)"
    h = _home(cls, -100.0, 0.0, timeout=2.0)
    assert h.state == "FAILED", "no switch within the timeout must give FAILED"


def c_supervisor(lib):
    import ctypes as C
    from roboprep.cbind import Functions

    class S(C.Structure):
        _fields_ = [("ferr_max", C.c_double), ("i_limit", C.c_double), ("i_cycles", C.c_int), ("v_max", C.c_double),
                    ("dt", C.c_double), ("fault", C.c_int), ("cmd", C.c_double), ("over", C.c_int)]
    f = Functions(lib, "m06", {"AxisSupervisor": S})

    class AxisSupervisor:
        def __init__(self, ferr_max, i_limit, i_cycles, v_max, dt):
            self._s = S()
            f.axis_init(C.byref(self._s), ferr_max, i_limit, i_cycles, v_max, dt)
        fault = property(lambda self: [None, "COLLISION", "FOLLOWING_ERROR"][self._s.fault])

        def update(self, target, actual, current, deadman):
            cmd = C.c_double()
            en = f.axis_update(C.byref(self._s), target, actual, current, bool(deadman), C.byref(cmd))
            return bool(en), cmd.value

        def reset(self, actual):
            f.axis_reset(C.byref(self._s), actual)
    return (AxisSupervisor,)


def c_homing(lib):
    import ctypes as C
    from roboprep.cbind import Functions

    class S(C.Structure):
        _fields_ = [(n, C.c_double) for n in ("v_fast", "v_slow", "timeout", "dt")] + [("state", C.c_int), ("t", C.c_double), ("zero", C.c_double)]
    f = Functions(lib, "m06", {"Homing": S})

    class Homing:
        def __init__(self, v_fast, v_slow, timeout_s, dt):
            self._s = S()
            f.homing_init(C.byref(self._s), v_fast, v_slow, timeout_s, dt)
        state = property(lambda self: ["SEEK", "BACKOFF", "APPROACH", "DONE", "FAILED"][self._s.state])
        zero = property(lambda self: self._s.zero if self._s.state == 3 else None)

        def step(self, switch, position):
            return f.homing_step(C.byref(self._s), bool(switch), position)
    return (Homing,)
