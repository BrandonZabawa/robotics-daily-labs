import random

ANSWERS = {"M1": 2.0, "M2": 128}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Reset cause flags logged with a timestamp at every boot",
    "Crash record (PC, LR, CFSR, HFSR, fault address, task) saved in no-init RAM, copied to a committed flash log",
    "Watchdog supervisor records which task missed its check-in",
    "Power evidence (brown-out counts, supply voltage) to tell power problems from code",
]}
HINTS = {
    "log": "Program magic+len+payload+crc in one call, then the commit byte alone; the scanner trusts only crc-ok and commit==0x00.",
    "supervisor": "Every task must have checked in, and no longer ago than its limit.",
    "resets": "Bits 31..25; three IWDG resets in a row means safe mode.",
}


class PowerCut(Exception):
    pass


class LogFlash:
    """Same model as the notebook's: program() only clears bits and may lose power after `budget` bytes."""
    def __init__(self, size=4096, budget=None):
        self.mem, self.budget = bytearray(b"\xff" * size), budget

    def program(self, addr, data):
        for i, b in enumerate(data):
            if self.budget is not None:
                if self.budget == 0:
                    raise PowerCut()
                self.budget -= 1
            self.mem[addr + i] &= b


def check_log(append, recover):
    f = LogFlash()
    off = 0
    msgs = [b"boot", b"IWDG reset", b"pc=0x08001234", b""]
    for m in msgs:
        off = append(f, off, m)
    got, nxt = recover(f)
    assert got == msgs and nxt == off, f"recover -> {got}, next {nxt} (expected {off})"
    rnd = random.Random(9)
    for trial in range(60):
        cut = rnd.randrange(0, 40)
        f = LogFlash()
        off = append(f, 0, b"first record")
        f.budget = cut
        try:
            append(f, off, b"second record!")
            done = True
        except PowerCut:
            done = False
        f.budget = None
        got, nxt = recover(f)
        want = [b"first record", b"second record!"] if done else [b"first record"]
        assert got == want, f"power cut after {cut} bytes: recovered {got}"
        off2 = append(f, nxt, b"after reboot")
        got2, _ = recover(f)
        assert got2 == want + [b"after reboot"], f"cannot keep logging after a cut at byte {cut}: {got2}"


def check_supervisor(cls):
    s = cls({"control": 0.01, "can": 0.1})
    assert not s.kick(0.0), "no check-ins yet"
    s.checkin("control", 0.0)
    s.checkin("can", 0.0)
    assert s.kick(0.005)
    s.checkin("control", 0.02)
    assert s.kick(0.025)
    assert not s.kick(0.15), "can task silent for 150 ms (limit 100 ms)"
    s.checkin("can", 0.15)
    assert not s.kick(0.15), "control silent for 130 ms (limit 10 ms)"


def check_resets(decode, mode):
    assert decode(0x24000000) == {"IWDG", "PIN"} or decode(0x24000000) == {"PIN", "IWDG"}, f"{decode(0x24000000)}"
    assert decode(0x0C000000) == {"BOR", "PIN"}, "power-on: BOR + PIN"
    assert decode(0x10000000) == {"SFT"}
    assert mode([{"PIN"}, {"BOR", "PIN"}]) == "normal"
    assert mode([{"PIN"}, {"IWDG"}]) == "degraded"
    assert mode([{"IWDG"}, {"IWDG"}, {"IWDG", "PIN"}]) == "safe"
    assert mode([{"IWDG"}, {"PIN"}, {"IWDG"}]) == "degraded", "only consecutive watchdog resets count toward safe mode"


def c_log(lib):
    import ctypes as C
    from roboprep.cbind import Functions, u8, out
    PR = C.CFUNCTYPE(C.c_bool, C.c_void_p, C.c_uint32, C.POINTER(C.c_uint8), C.c_size_t)

    class Ops(C.Structure):
        _fields_ = [("program", PR), ("ctx", C.c_void_p)]
    f = Functions(lib, "rs04", {"LogFlashOps": Ops})

    def append(flash, offset, payload):
        cut = []

        def program(_, addr, data, n):
            try:
                flash.program(addr, bytes(data[:n]))
                return True
            except PowerCut:
                cut.append(1)
                return False
        cb = PR(program)
        r = f.log_append(C.byref(Ops(cb, None)), offset, *u8(payload))
        if cut:
            raise PowerCut()
        return r

    def recover(flash):
        buf, lens, nxt = out(C.c_uint8, len(flash.mem)), out(C.c_size_t, 256), C.c_uint32()
        n = f.log_recover(*u8(flash.mem), buf, len(flash.mem), lens, 256, C.byref(nxt))
        res, k = [], 0
        for i in range(n):
            res.append(bytes(buf[k:k + lens[i]]))
            k += lens[i]
        return res, nxt.value
    return append, recover


def c_supervisor(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr

    class S(C.Structure):
        _fields_ = [("n", C.c_size_t), ("max_interval", C.c_double * 8), ("last", C.c_double * 8), ("seen", C.c_bool * 8)]
    f = Functions(lib, "rs04", {"Supervisor": S})

    class Supervisor:
        def __init__(self, max_interval):
            self.names, self._s = list(max_interval), S()
            f.sup_init(C.byref(self._s), arr(C.c_double, [max_interval[n] for n in self.names]), len(self.names))

        def checkin(self, task, now):
            f.sup_checkin(C.byref(self._s), self.names.index(task), now)

        def kick(self, now):
            return bool(f.sup_kick(C.byref(self._s), now))
    return (Supervisor,)


def c_resets(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr
    f = Functions(lib, "rs04")
    bits = {"LPWR": 31, "WWDG": 30, "IWDG": 29, "SFT": 28, "BOR": 27, "PIN": 26, "OBL": 25}

    def decode_csr(csr):
        names = (C.c_char_p * 8)()
        n = f.decode_csr(csr, names, 8)
        return {names[i].decode() for i in range(n)}

    def boot_mode(history):
        csrs = [sum(1 << bits[x] for x in h) for h in history]
        return ["normal", "degraded", "safe"][f.boot_mode(arr(C.c_uint32, csrs), len(csrs))]
    return decode_csr, boot_mode
