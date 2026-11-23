ANSWERS = {"M1": 16, "M2": 32, "M3": 40}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Measure CANH-CANL powered off: 60 ohm good, 120 missing terminator, 40 extra terminator",
    "Same bit rate and sample point on every node; accurate clock source (crystal) for the longer bus",
    "Read TEC/REC and error type per node to locate the culprit",
    "Scope the differential signal: ringing, stubs, grounding",
]}
HINTS = {
    "filters": "mask = ~(OR of every id XOR ids[0]) & 0x7FF.",
    "confinement": "Bus-off when TEC > 255; passive when either counter > 127.",
}


def check_filters(fmf, acc):
    f, m = fmf(list(range(0x120, 0x130)))
    assert (f, m) == (0x120, 0x7F0), f"0x120..0x12F -> (0x{f:03X}, 0x{m:03X})"
    f, m = fmf([0x100, 0x101, 0x104])
    assert m == 0x7FA and f == 0x100, f"[0x100, 0x101, 0x104] -> (0x{f:03X}, 0x{m:03X})"
    assert acc(0x100, 0x7FA) == [0x100, 0x101, 0x104, 0x105], "accepted() list (note the extra 0x105)"
    assert len(acc(0x120, 0x7F0)) == 16


def check_confinement(cls):
    c = cls()
    for _ in range(16):
        c.tx_error()
    assert c.tec == 128 and c.state == "error-passive", f"after 16 tx errors: TEC {c.tec}, {c.state}"
    c.tx_ok()
    assert c.tec == 127 and c.state == "error-active", "one success brings TEC to 127: active again"
    for _ in range(17):
        c.tx_error()
    assert c.state == "bus-off", f"TEC {c.tec} should be bus-off"
    c.tx_error()
    assert c.tec == 263, "no counting while bus-off"
    for _ in range(127):
        c.recessive_11()
    assert c.state == "bus-off", "needs 128 recovery sequences"
    c.recessive_11()
    assert c.state == "error-active" and c.tec == 0 and c.rec == 0, "after 128 sequences: active, counters 0"
    d = cls()
    for _ in range(130):
        d.rx_error()
    assert d.state == "error-passive"
    d.rx_ok()
    assert d.rec == 127 and d.state == "error-active", "REC above 127 drops to 127 on a good receive"
    for _ in range(200):
        d.rx_ok()
    assert d.rec == 0


def c_filters(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr, out
    f = Functions(lib, "d07")

    def filter_mask_for(ids):
        fi, m = C.c_uint16(), C.c_uint16()
        f.can_filter_mask_for(arr(C.c_uint16, ids), len(ids), C.byref(fi), C.byref(m))
        return fi.value, m.value

    def accepted(filt, mask):
        buf = out(C.c_uint16, 0x800)
        return list(buf[:f.can_accepted(filt, mask, buf, 0x800)])
    return filter_mask_for, accepted


def c_confinement(lib):
    import ctypes as C
    from roboprep.cbind import Functions

    class S(C.Structure):
        _fields_ = [("tec", C.c_int), ("rec", C.c_int), ("recov", C.c_int)]
    f = Functions(lib, "d07", {"CanErrorCounters": S})

    class ErrorCounters:
        def __init__(self):
            self._s = S()
            f.cec_init(C.byref(self._s))
        tec = property(lambda self: self._s.tec)
        rec = property(lambda self: self._s.rec)
        state = property(lambda self: ["error-active", "error-passive", "bus-off"][f.cec_state(C.byref(self._s))])
        def tx_error(self): f.cec_tx_error(C.byref(self._s))
        def tx_ok(self): f.cec_tx_ok(C.byref(self._s))
        def rx_error(self): f.cec_rx_error(C.byref(self._s))
        def rx_ok(self): f.cec_rx_ok(C.byref(self._s))
        def recessive_11(self): f.cec_recessive_11(C.byref(self._s))
    return (ErrorCounters,)
