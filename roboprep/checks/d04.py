import random

ANSWERS = {"M1": (966.7, {"rel": 2e-3}), "M2": (1770, {"rel": 2e-3}), "M3": 0xD1}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Reset interrupted a read; the slave is still driving a 0 bit and waits for clocks",
    "STOP needs SDA to rise while SCL is high, impossible while the slave holds SDA low",
    "Recovery: drive SCL as GPIO, pulse up to 9 times until SDA reads high",
    "Then send a STOP manually and give the pins back to the I2C peripheral",
]}
HINTS = {
    "decode": "SCL high on both samples and SDA changes -> START or STOP; SCL rising -> sample a bit; 9 bits per byte.",
    "pullup": "R_max = t_r / (0.8473 * C_b); remember pF = 1e-12 F.",
    "recover": "Loop while SDA is low and pulses < 9, then stop().",
}


def wave(events, S=2, stretch=False):
    scl, sda = [1] * S, [1] * S

    def push(c, d, n=S):
        scl.extend([c] * n)
        sda.extend([d] * n)

    for ev in events:
        if ev[0] in ("S", "Sr"):
            if ev[0] == "Sr":
                push(0, 1)
                push(1, 1)
            push(1, 0)
            push(0, 0)
        elif ev[0] == "B":
            for b in [int(x) for x in f"{ev[1]:08b}"] + [0 if ev[2] else 1]:
                push(0, b, S * (4 if stretch and b else 1))
                push(1, b)
                push(0, b)
        elif ev[0] == "P":
            push(0, 0)
            push(1, 0)
            push(1, 1)
    return scl, sda


def check_decode(fn):
    tx = [("S",), ("B", 0xD0, True), ("B", 0x3B, True), ("Sr",), ("B", 0xD1, True), ("B", 0x12, True),
          ("B", 0x34, False), ("P",)]
    got = fn(*wave(tx))
    assert got == tx, f"register read decoded as {got}"
    tx2 = [("S",), ("B", 0x90, False), ("P",), ("S",), ("B", 0xA0, True), ("B", 0xFF, True), ("P",)]
    got = fn(*wave(tx2, stretch=True))
    assert got == tx2, f"NACKed address then a write (with clock stretching) decoded as {got}"


def check_pullup(fn):
    lo, hi = fn(3.3, 200, "fast")
    assert abs(lo - 2.9 / 3e-3) < 0.5 and abs(hi - 300e-9 / (0.8473 * 200e-12)) < 0.5, f"fast 200 pF: {lo:.1f}, {hi:.1f}"
    lo, hi = fn(5.0, 100, "standard")
    assert abs(lo - 4.6 / 3e-3) < 0.5 and abs(hi - 1000e-9 / (0.8473 * 100e-12)) < 0.5, "standard 100 pF wrong"
    lo, hi = fn(3.3, 100, "fastplus")
    assert abs(lo - 2.9 / 20e-3) < 0.5 and abs(hi - 120e-9 / (0.8473 * 100e-12)) < 0.5, "fast-mode plus wrong"


class StuckBus:
    def __init__(self, remaining_bits):
        self.bits = list(remaining_bits)   # bits the slave still wants to drive (0 = pull low)
        self.pulses = 0
        self.stopped = False
        self.bad_stop = False

    def sda(self):
        return self.bits[0] if self.bits else 1

    def pulse_scl(self):
        self.pulses += 1
        if self.bits:
            self.bits.pop(0)

    def stop(self):
        if self.sda() == 0:
            self.bad_stop = True
        else:
            self.stopped = True
            self.bits = []


def check_recover(fn):
    rnd = random.Random(3)
    for k in range(20):
        start = rnd.randrange(8)
        byte = [int(x) for x in f"{rnd.randrange(256):08b}"][start:]
        bits = [0] + byte[1:] + [1] if byte else [0, 1]
        bus = StuckBus(bits)
        n = fn(bus)
        assert not bus.bad_stop, "sent STOP while SDA was still held low"
        assert bus.stopped, "never sent a valid STOP"
        assert bus.pulses <= 9 and n == bus.pulses, f"pulse count {n} (bus saw {bus.pulses}), max 9"


def c_decode(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr

    class Ev(C.Structure):
        _fields_ = [("kind", C.c_char), ("byte", C.c_uint8), ("ack", C.c_bool)]
    f = Functions(lib, "d04", {"I2cEvent": Ev})

    def i2c_decode(scl, sda):
        buf = (Ev * len(scl))()
        n = f.i2c_decode(arr(C.c_uint8, scl), arr(C.c_uint8, sda), len(scl), buf, len(scl))
        kinds = {b"S": ("S",), b"R": ("Sr",), b"P": ("P",)}
        return [kinds[e.kind] if e.kind in kinds else ("B", e.byte, bool(e.ack)) for e in buf[:n]]
    return (i2c_decode,)


def c_pullup(lib):
    import ctypes as C
    from roboprep.cbind import Functions
    f = Functions(lib, "d04")

    def pullup_range(vdd, cb_pF, mode):
        lo, hi = C.c_double(), C.c_double()
        f.pullup_range(vdd, cb_pF, {"standard": 0, "fast": 1, "fastplus": 2}[mode], C.byref(lo), C.byref(hi))
        return lo.value, hi.value
    return (pullup_range,)


def c_recover(lib):
    import ctypes as C
    SDA = C.CFUNCTYPE(C.c_int, C.c_void_p)
    ACT = C.CFUNCTYPE(None, C.c_void_p)

    class Ops(C.Structure):
        _fields_ = [("sda", SDA), ("pulse_scl", ACT), ("stop", ACT), ("ctx", C.c_void_p)]
    from roboprep.cbind import Functions
    f = Functions(lib, "d04", {"I2cBusOps": Ops})

    def recover(bus):
        cbs = (SDA(lambda _: int(bus.sda())), ACT(lambda _: bus.pulse_scl()), ACT(lambda _: bus.stop()))
        ops = Ops(*cbs, None)
        return f.i2c_recover(C.byref(ops))
    return (recover,)
