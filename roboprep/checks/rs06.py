ANSWERS = {"M1": 0.5, "M2": 0.375}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Fault in ROOT covers every current and future state; nobody can forget it",
    "Disable in Operational is inherited by Manual and Auto and ignored elsewhere",
    "Parent entry/exit actions (enable drives on entering Operational) run automatically",
    "Flat machine duplicates transitions (states x events) and a missing fault transition is a safety bug",
]}
HINTS = {
    "hsm": "LCA = first state in the source's ancestor list that is also in the target's; exit up to it, enter down from it.",
    "categories": "0 = remove power now, 1 = stop then remove power, 2 = stop and keep power.",
}


def check_hsm(cls, transition, dispatch):
    h = cls()
    for e in ["init_done", "enable", "auto"]:
        dispatch(h, e)
    assert h.state == "Auto", f"state {h.state}"
    assert h.log == ["exit:Init", "entry:Ready", "entry:Idle", "exit:Idle", "entry:Operational", "entry:Manual",
                     "exit:Manual", "entry:Auto"], f"log {h.log}"
    h.log.clear()
    dispatch(h, "disable")
    assert h.state == "Idle" and h.log == ["exit:Auto", "exit:Operational", "entry:Idle"], f"disable from Auto: {h.log}"
    dispatch(h, "enable")
    h.log.clear()
    dispatch(h, "fault")
    assert h.state == "Fault" and h.log == ["exit:Manual", "exit:Operational", "exit:Ready", "entry:Fault"], f"fault: {h.log}"
    h.log.clear()
    assert dispatch(h, "enable") is False and h.state == "Fault", "Fault ignores enable (latched)"
    dispatch(h, "reset")
    assert h.state == "Fault" and h.log == [], "reset is refused while the e-stop is pressed"
    h.estop_released = True
    dispatch(h, "reset")
    assert h.state == "Idle" and h.log == ["exit:Fault", "entry:Ready", "entry:Idle"], f"reset: {h.log}"


def check_categories(stops):
    if any(v is None for v in stops.values()):
        raise NotImplementedError
    want = [0, 1, 2, 1]
    wrong = [k for k, w in zip(stops, want) if stops[k] != w]
    assert not wrong, "wrong: " + "; ".join(wrong)


def c_hsm(lib):
    import ctypes as C
    from roboprep.cbind import Functions
    LOG = C.CFUNCTYPE(None, C.c_void_p, C.c_bool, C.c_int)

    class S(C.Structure):
        _fields_ = [("state", C.c_int), ("estop_released", C.c_bool), ("log", LOG), ("ctx", C.c_void_p)]
    f = Functions(lib, "rs06", {"Hsm": S})
    names = ["ROOT", "Init", "Ready", "Fault", "Idle", "Operational", "Manual", "Auto"]
    events = ["init_done", "enable", "auto", "manual", "disable", "fault", "reset"]

    class Hsm:
        def __init__(self):
            self.log = []
            self._cb = LOG(lambda _, entry, s: self.log.append(f"{'entry' if entry else 'exit'}:{names[s]}"))
            self._s = S(1, False, self._cb, None)
        state = property(lambda self: names[self._s.state])
        estop_released = property(lambda self: self._s.estop_released,
                                  lambda self, v: setattr(self._s, "estop_released", bool(v)))

    def transition(h, target):
        f.hsm_transition(C.byref(h._s), names.index(target))

    def dispatch(h, event):
        return bool(f.hsm_dispatch(C.byref(h._s), events.index(event)))
    return Hsm, transition, dispatch
