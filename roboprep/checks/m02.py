import random

ANSWERS = {"M1": 4096, "M2": 12, "M3": (1464.84, {"rel": 1e-4})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Fixed-window counting quantizes speed to one count per window (14.6 rpm here)",
    "Period measurement with input capture is precise at low speed",
    "Switch methods by speed, or use an observer / PLL / Kalman filter for smooth velocity",
    "Longer windows reduce noise but add delay",
]}
HINTS = {
    "decoder": "Only act when the state changed; unknown transitions count as errors.",
    "velocity": "Add half the range before the modulo, subtract it after.",
}

SEQ = [0, 1, 3, 2]


def check_decoder(cls):
    d = cls()
    pos = 0
    idx = 0
    rnd = random.Random(1)
    for _ in range(500):
        step = rnd.choice([1, 1, 1, -1, 0])
        idx = (idx + step) % 4
        pos += step
        s = SEQ[idx]
        got = d.update(s >> 1, s & 1)
    assert got == pos and d.errors == 0, f"position {got}, expected {pos}; errors {d.errors}"
    d.update(SEQ[(idx + 2) % 4] >> 1, SEQ[(idx + 2) % 4] & 1)
    assert d.errors == 1 and d.position == pos, "a jump of two states must count as an error and not move"


def check_velocity(sd, rpm):
    assert sd(6, 65530) == 12 and sd(65530, 6) == -12, "wrap in both directions"
    assert sd(100, 50) == 50 and sd(0, 32768) == -32768, "plain difference and the half-range edge"
    assert sd(5, 2**32 - 5, bits=32) == 10, "32-bit counter"
    assert abs(rpm(1000, 0.01, 1024) - 1464.84375) < 1e-6


def c_decoder(lib):
    import ctypes as C
    from roboprep.cbind import Functions

    class S(C.Structure):
        _fields_ = [("prev", C.c_uint8), ("position", C.c_int32), ("errors", C.c_uint32)]
    f = Functions(lib, "m02", {"QuadDecoder": S})

    class QuadDecoder:
        def __init__(self):
            self._s = S()
            f.qd_init(C.byref(self._s))
        position = property(lambda self: self._s.position)
        errors = property(lambda self: self._s.errors)

        def update(self, a, b):
            return f.qd_update(C.byref(self._s), a, b)
    return (QuadDecoder,)


def c_velocity(lib):
    from roboprep.cbind import Functions
    f = Functions(lib, "m02")
    return (lambda now, prev, bits=16: f.signed_delta(now, prev, bits), f.rpm)
