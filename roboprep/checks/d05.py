import random

ANSWERS = {"M1": 12.5, "M2": 64, "M3": 0x09}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "In-band interrupts remove per-sensor interrupt wires (important through arm joints)",
    "Higher throughput: 12.5 MHz push-pull SDR, HDR for bursts",
    "Dynamic addressing avoids address collisions between identical sensors",
    "Legacy I2C EEPROM needs the 50 ns spike filter; controller and driver maturity add firmware effort",
]}
HINTS = {
    "daa": "Build v = pid << 16 | bcr << 8 | dcr; for bit 63..0 the line is the AND of all bits; drop targets that sent 1 when the line is 0.",
    "ccc_ibi": "Below 0x80 is broadcast; the lowest address wins arbitration.",
}


def check_daa(fn):
    rnd = random.Random(11)
    t = [(rnd.getrandbits(48), rnd.getrandbits(8), rnd.getrandbits(8)) for _ in range(6)]
    t.append((0x0000_0000_0001, 0x20, 0x44))
    got = fn(t, 0x08)
    order = sorted(t, key=lambda x: (x[0] << 16) | (x[1] << 8) | x[2])
    want = {p: 0x08 + i for i, (p, _, _) in enumerate(order)}
    assert got == want, "addresses not handed out in arbitration order (lowest 64-bit PID|BCR|DCR first)"
    same_pid = [(0xABCDEF012345, 0x10, 0x05), (0xABCDEF012346, 0x00, 0x00)]
    assert fn(same_pid, 0x30) == {0xABCDEF012345: 0x30, 0xABCDEF012346: 0x31}, "PID decides before BCR"


def check_ccc_ibi(ccc_type, ibi_winner):
    for code, t in [(0x07, "broadcast"), (0x06, "broadcast"), (0x87, "direct"), (0x8D, "direct"), (0x00, "broadcast"), (0x81, "direct")]:
        assert ccc_type(code) == t, f"0x{code:02X} should be {t}"
    assert ibi_winner([0x0A, 0x09, 0x0C]) == 0x09, "lowest address wins the IBI header arbitration"


def c_daa(lib):
    import ctypes as C
    from roboprep.cbind import Functions, out

    class T(C.Structure):
        _fields_ = [("pid", C.c_uint64), ("bcr", C.c_uint8), ("dcr", C.c_uint8)]
    f = Functions(lib, "d05", {"I3cTarget": T})

    def entdaa(targets, first=0x08):
        ts = (T * len(targets))(*[T(p, b, d) for p, b, d in targets])
        res = out(C.c_uint8, len(targets))
        f.entdaa(ts, len(targets), first, res)
        return {p: res[i] for i, (p, _, _) in enumerate(targets)}
    return (entdaa,)


def c_ccc_ibi(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr
    f = Functions(lib, "d05")
    return (lambda code: "direct" if f.ccc_is_direct(code) else "broadcast",
            lambda addrs: f.ibi_winner(arr(C.c_uint8, addrs), len(addrs)))
