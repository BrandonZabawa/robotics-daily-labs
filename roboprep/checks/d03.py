import random

ANSWERS = {"M1": 80, "M2": 40, "M3": (512820, {"rel": 1e-3})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Modes 0 and 3 both sample rising and shift falling, so mid-frame bits are right",
    "They differ in idle clock level when CS falls",
    "First bit (or the first MISO bit) can be lost or shifted",
    "Prove it: decode the capture both ways, check SCLK level at CS falling edge, compare first bit and status",
]}
HINTS = {
    "decode": "Rising-edge sampling when CPOL == CPHA; falling otherwise.",
    "chain": "Device i occupies bits [40*i, 40*i+40).",
}


def wave(data_bytes, cpol, cpha, S=4):
    """Samples of SCLK and data; data changes one sample after the shifting edge (propagation delay)."""
    bits = [int(b) for x in data_bytes for b in f"{x:08b}"]
    lead = 1 - cpol
    sclk, mosi, prev = [cpol] * S, [bits[0] if cpha == 0 else 0] * S, 0
    for k, b in enumerate(bits):
        if cpha == 0:      # shift on trailing edge (start of this window), sample on leading edge (middle)
            first = [b] * S if k == 0 else [prev] + [b] * (S - 1)
            sclk += [cpol] * S + [lead] * S
            mosi += first + [b] * S
        else:              # shift on leading edge (middle), sample on trailing edge (end)
            sclk += [cpol] * S + [lead] * S
            mosi += [prev] * S + [prev] + [b] * (S - 1)
        prev = b
    sclk += [cpol] * S
    mosi += [prev] * S
    return sclk, mosi


def check_decode(decode, mode_table):
    rnd = random.Random(5)
    for mode in range(4):
        payload = [rnd.randrange(256) for _ in range(5)]
        s, d = wave(payload, mode >> 1, mode & 1)
        got = decode(s, d, mode >> 1, mode & 1)
        assert got == payload, f"mode {mode}: decoded {got}, sent {payload}"
    t = mode_table()
    want = {0: (0, "rising"), 1: (0, "falling"), 2: (1, "falling"), 3: (1, "rising")}
    bad = [m for m in range(4) if tuple(t.get(m, ())) != want[m]]
    assert not bad, f"mode_table wrong for modes {bad}"


def check_chain(tx, rx):
    d = [0x8000000001, 0x00AABBCCDD, 0x1234567890]
    v = tx(d)
    assert v >> 80 == 0x1234567890, "the farthest device's datagram must be shifted out first (most significant)"
    assert v & (2**40 - 1) == 0x8000000001, "the nearest device's datagram must be shifted out last"
    assert rx(v, 3) == d, "chain_rx must undo chain_tx"
    assert rx(0xFF << 40, 2) == [0, 0xFF], "reply index 1 is the farther device"


def c_decode(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr, out
    f = Functions(lib, "d03")

    def spi_decode(sclk, data, cpol, cpha):
        buf = out(C.c_uint8, len(sclk) // 8 + 1)
        n = f.spi_decode(arr(C.c_uint8, sclk), arr(C.c_uint8, data), len(sclk), cpol, cpha, buf, len(sclk) // 8 + 1)
        return list(buf[:n])

    def mode_table():
        res = {}
        for m in range(4):
            idle, rising = C.c_int(), C.c_bool()
            f.spi_mode(m, C.byref(idle), C.byref(rising))
            res[m] = (idle.value, "rising" if rising.value else "falling")
        return res
    return spi_decode, mode_table


def c_chain(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr, out
    f = Functions(lib, "d03")

    def chain_tx(datagrams):
        buf = out(C.c_uint8, 5 * len(datagrams))
        f.chain_tx(arr(C.c_uint64, datagrams), len(datagrams), buf)
        return int.from_bytes(bytes(buf[:5 * len(datagrams)]), "big")

    def chain_rx(value, n):
        res = out(C.c_uint64, n)
        f.chain_rx(arr(C.c_uint8, value.to_bytes(5 * n, "big")), n, res)
        return list(res[:n])
    return chain_tx, chain_rx
