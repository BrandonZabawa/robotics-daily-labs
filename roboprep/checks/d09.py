ANSWERS = {"M1": 0x185, "M2": 0x2B, "M3": 0x0F}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Pre-operational: SDO and heartbeat, no PDOs; Operational: PDOs flow; Stopped: only NMT and heartbeat",
    "NMT Start (0x01) moves the node to operational",
    "CiA 402 is a separate power state machine inside the drive (Shutdown, Switch on, Enable operation)",
    "Motion needs both: PDOs flowing and power stage enabled; a fault drops it out until fault reset",
]}
HINTS = {
    "sdo": "Bytes: cmd, index low, index high, sub, then value little-endian, padded to 8.",
    "cia402": "Check the 0x4F masks for not-ready/disabled/fault, the 0x6F masks for the rest.",
    "pdo": "int.to_bytes(bits // 8, 'little') for each mapped entry, concatenated.",
}

SW = {"Switch on disabled": 0x0250, "Ready to switch on": 0x0231, "Switched on": 0x0233,
      "Operation enabled": 0x0237, "Quick stop active": 0x0217, "Fault": 0x0218, "Not ready to switch on": 0x0000}


class Drive:
    def __init__(self, state):
        self.state, self.prev_cw, self.writes = state, 0, []

    def statusword(self):
        return SW[self.state] | (0x80 if self.state == "Fault" else 0)

    def write_controlword(self, cw):
        self.writes.append(cw)
        s = self.state
        if s == "Fault":
            if cw & 0x80 and not self.prev_cw & 0x80:
                self.state = "Switch on disabled"
        elif cw & 0x82 == 0x00 and s in ("Ready to switch on", "Switched on", "Operation enabled", "Quick stop active"):
            self.state = "Switch on disabled"
        elif cw & 0x87 == 0x06 and s in ("Switch on disabled", "Switched on", "Operation enabled"):
            self.state = "Ready to switch on"
        elif cw & 0x8F == 0x07 and s in ("Ready to switch on", "Operation enabled"):
            self.state = "Switched on"
        elif cw & 0x8F == 0x0F and s == "Ready to switch on":
            self.state = "Switched on"
        elif cw & 0x8F == 0x0F and s == "Switched on":
            self.state = "Operation enabled"
        elif cw & 0x86 == 0x02 and s == "Operation enabled":
            self.state = "Quick stop active"
        self.prev_cw = cw


def check_sdo(dl, up):
    assert dl(5, 0x6040, 0, 0x000F, 2) == (0x605, bytes([0x2B, 0x40, 0x60, 0x00, 0x0F, 0x00, 0, 0])), "write controlword"
    assert dl(3, 0x607A, 0, 100000, 4) == (0x603, bytes([0x23, 0x7A, 0x60, 0x00, 0xA0, 0x86, 0x01, 0x00])), "target position"
    assert dl(1, 0x6060, 0, 1, 1)[1][0] == 0x2F
    assert up(bytes([0x4B, 0x41, 0x60, 0x00, 0x37, 0x02, 0, 0])) == (0x6041, 0, 0x0237), "2-byte upload"
    assert up(bytes([0x43, 0x64, 0x60, 0x00, 0x10, 0x27, 0, 0])) == (0x6064, 0, 10000), "4-byte upload"
    try:
        up(bytes([0x80, 0x00, 0x20, 0x01, 0x00, 0x00, 0x02, 0x06]))
        raise AssertionError("an abort frame must raise RuntimeError")
    except RuntimeError:
        pass


def check_cia402(state_fn, enable):
    for name, sw in SW.items():
        assert state_fn(sw) == name, f"0x{sw:04X} decoded as {state_fn(sw)}, want {name}"
    for start in ["Switch on disabled", "Fault", "Quick stop active", "Switched on"]:
        d = Drive(start)
        ok = enable(d)
        assert ok and d.state == "Operation enabled", f"from {start}: ended in {d.state} after {[hex(c) for c in d.writes]}"
        assert len(d.writes) <= 5, f"from {start}: too many steps"


def check_pdo(fn):
    m = [(0x6041, 0, 16), (0x6064, 0, 32), (0x6061, 0, 8)]
    v = {(0x6041, 0): 0x0237, (0x6064, 0): -2, (0x6061, 0): 8}
    assert fn(m, v) == bytes([0x37, 0x02, 0xFE, 0xFF, 0xFF, 0xFF, 0x08]), "TPDO bytes"


def c_sdo(lib):
    import ctypes as C
    from roboprep.cbind import Functions, u8, out
    f = Functions(lib, "d09")

    def sdo_download(node, index, sub, value, size):
        buf = out(C.c_uint8, 8)
        cob = f.sdo_download(node, index, sub, value, size, buf)
        return cob, bytes(buf[:8])

    def sdo_upload_parse(data):
        i, s, v, a = C.c_uint16(), C.c_uint8(), C.c_uint32(), C.c_uint32()
        if f.sdo_upload_parse(u8(data)[0], C.byref(i), C.byref(s), C.byref(v), C.byref(a)) < 0:
            raise RuntimeError(f"SDO abort 0x{a.value:08X}")
        return i.value, s.value, v.value
    return sdo_download, sdo_upload_parse


def c_cia402(lib):
    import ctypes as C
    from roboprep.cbind import Functions
    SWF = C.CFUNCTYPE(C.c_uint16, C.c_void_p)
    CWF = C.CFUNCTYPE(None, C.c_void_p, C.c_uint16)

    class Ops(C.Structure):
        _fields_ = [("statusword", SWF), ("write_controlword", CWF), ("ctx", C.c_void_p)]
    f = Functions(lib, "d09", {"Cia402DriveOps": Ops})
    names = ["Not ready to switch on", "Switch on disabled", "Ready to switch on", "Switched on", "Operation enabled",
             "Quick stop active", "Fault reaction active", "Fault", "Unknown"]

    def enable_drive(drive, max_steps=10):
        cbs = (SWF(lambda _: drive.statusword()), CWF(lambda _, cw: drive.write_controlword(cw)))
        return bool(f.enable_drive(C.byref(Ops(*cbs, None)), max_steps))
    return (lambda sw: names[f.cia402_state(sw)], enable_drive)


def c_pdo(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr, out

    class E(C.Structure):
        _fields_ = [("index", C.c_uint16), ("sub", C.c_uint8), ("bits", C.c_uint8)]
    f = Functions(lib, "d09", {"PdoEntry": E})

    def pack_pdo(mapping, values):
        m = (E * len(mapping))(*[E(i, s, b) for i, s, b in mapping])
        buf = out(C.c_uint8, 64)
        n = f.pack_pdo(m, arr(C.c_int64, [values[(i, s)] for i, s, _ in mapping]), len(mapping), buf)
        return bytes(buf[:n])
    return (pack_pdo,)
