import math

ANSWERS = {"M1": (0.8393, {"abs": 1e-4}), "M2": (16667, {"abs": 1}), "M3": 10240}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Test points on rails and buses, SWD header, boundary scan where available",
    "Factory test firmware: self-tests, talk to every chip on SPI/CAN, spin and measure the motor",
    "Fixture checks idle current before powering fully (catches shorts)",
    "Calibrate and log results per serial number",
]}
HINTS = {
    "march": "Write 0 everywhere; then (up, r0 w1), (up, r1 w0), (down, r0 w1), (down, r1 w0); finally read 0 everywhere.",
    "reliability": "exp(-t/MTBF); product; 1 - product of (1 - R); 1 / sum(1/MTBF).",
}


class Ram:
    def __init__(self, n, fault=None):
        self.n, self.m, self.fault, self.ops = n, [0] * n, fault, 0

    def write(self, a, v):
        self.ops += 1
        f = self.fault
        if f and f[0] == "transition" and f[1] == a and self.m[a] == 0 and v == 1:
            return
        if f and f[0] == "coupling" and f[1] == a and self.m[a] == 0 and v == 1:
            self.m[f[2]] = 1
        self.m[a] = v

    def read(self, a):
        self.ops += 1
        f = self.fault
        if f and f[0] == "stuck" and f[1] == a:
            return f[2]
        return self.m[a]


def check_march(fn):
    r = Ram(64)
    assert fn(r) is True, "fault-free RAM must pass"
    assert r.ops == 640, f"March C- is 10n operations; you used {r.ops} for n = 64"
    for fault in [("stuck", 10, 0), ("stuck", 63, 1), ("transition", 5), ("coupling", 3, 40), ("coupling", 40, 3)]:
        assert fn(Ram(64, fault)) is False, f"missed fault {fault}"


def check_reliability(rel, ser, par, smtbf):
    assert abs(rel(8760, 50000) - math.exp(-0.1752)) < 1e-12
    assert abs(ser([0.9, 0.9]) - 0.81) < 1e-12 and abs(par([0.9, 0.9]) - 0.99) < 1e-12
    assert abs(smtbf([100000] * 6) - 100000 / 6) < 1e-6


def c_march(lib):
    import ctypes as C
    from roboprep.cbind import Functions
    RD = C.CFUNCTYPE(C.c_uint8, C.c_void_p, C.c_size_t)
    WR = C.CFUNCTYPE(None, C.c_void_p, C.c_size_t, C.c_uint8)

    class Ops(C.Structure):
        _fields_ = [("read", RD), ("write", WR), ("n", C.c_size_t), ("ctx", C.c_void_p)]
    f = Functions(lib, "rs05", {"RamOps": Ops})

    def march_c_minus(ram):
        cbs = (RD(lambda _, a: ram.read(a)), WR(lambda _, a, v: ram.write(a, v)))
        return bool(f.march_c_minus(C.byref(Ops(*cbs, ram.n, None))))
    return (march_c_minus,)


def c_reliability(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr
    f = Functions(lib, "rs05")
    return (f.reliability, lambda rs: f.series(arr(C.c_double, rs), len(rs)),
            lambda rs: f.parallel(arr(C.c_double, rs), len(rs)), lambda ms: f.series_mtbf(arr(C.c_double, ms), len(ms)))
