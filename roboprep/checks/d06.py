import random

ANSWERS = {"M1": 135, "M2": 4, "M3": (0.27, {"abs": 1e-3})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "No clock line; nodes resync on recessive-to-dominant edges",
    "Stuffing guarantees an edge at least every 6 bits",
    "Every node must see each bit within one bit time during arbitration: round-trip delay limits length vs rate",
    "Late sample point leaves time for propagation and settling; phase segments and SJW absorb drift",
]}
HINTS = {
    "arbitrate": "Line level = min of the bits still competing; anyone who sent 1 while the line is 0 drops out.",
    "stuffing": "Count equal bits; after the 5th insert the complement, which also starts the next run.",
    "timing_load": "Try 25 down to 8 quanta; BRP must divide exactly; tseg2 = round(ntq * (1 - sp)).",
}




def check_arbitrate(fn):
    w, lost = fn([0x123, 0x122, 0x7FF, 0x120])
    assert w == 0x120, f"winner 0x{w:03X}, want 0x120"
    assert lost == {0x7FF: 0, 0x123: 9, 0x122: 9}, f"loss positions {lost}"


def check_stuffing(stuff, unstuff):
    assert stuff([0] * 5) == [0] * 5 + [1], "five zeros need one stuff bit"
    assert stuff([1] * 10) == [1] * 5 + [0] + [1] * 5 + [0], "ten ones need two stuff bits"
    assert stuff([0, 0, 0, 0, 0, 1, 1, 1, 1]) == [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0], "the stuff bit starts the next run"
    import json
    import pathlib
    vectors = json.loads((pathlib.Path(__file__).parent / "data" / "d06_stuff.json").read_text())
    for raw, stuffed in vectors:
        bits, sbits = [int(c) for c in raw], [int(c) for c in stuffed]
        assert stuff(bits) == sbits, "stuff() wrong on a random frame"
        assert unstuff(sbits) == bits, "unstuff(stuff(x)) != x"


def check_timing_load(bit_timing, frame_bits_worst, bus_load):
    for f, br, sp in [(170_000_000, 500_000, 0.8), (80_000_000, 1_000_000, 0.875), (16_000_000, 250_000, 0.875)]:
        brp, t1, t2 = bit_timing(f, br, sp)
        ntq = 1 + t1 + t2
        assert 8 <= ntq <= 25 and t2 >= 1, f"{br}: {ntq} quanta"
        assert f == brp * ntq * br, f"{br}: bit rate not exact"
        assert abs((1 + t1) / ntq - sp) <= 0.03, f"{br}: sample point {(1 + t1) / ntq:.3f}, target {sp}"
    assert frame_bits_worst(8) == 135 and frame_bits_worst(0) == 55, "worst-case frame length formula"
    assert abs(bus_load([(8, 100)] * 10, 500_000) - 0.27) < 1e-9, "bus load"


def c_arbitrate(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr, out
    f = Functions(lib, "d06")

    def arbitrate(ids):
        lost = out(C.c_int, len(ids))
        w = f.can_arbitrate(arr(C.c_uint16, ids), len(ids), lost)
        return w, {i: lost[k] for k, i in enumerate(ids) if lost[k] >= 0}
    return (arbitrate,)


def c_stuffing(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr, out
    f = Functions(lib, "d06")

    def call(fn, bits):
        buf = out(C.c_uint8, 2 * len(bits) + 2)
        n = fn(arr(C.c_uint8, bits), len(bits), buf, 2 * len(bits) + 2)
        return list(buf[:n])
    return (lambda b: call(f.can_stuff, b), lambda b: call(f.can_unstuff, b))


def c_timing_load(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr
    f = Functions(lib, "d06")

    def bit_timing(f_clk, bitrate, sample_point=0.8):
        b, t1, t2 = C.c_uint32(), C.c_uint32(), C.c_uint32()
        f.can_bit_timing(f_clk, bitrate, sample_point, C.byref(b), C.byref(t1), C.byref(t2))
        return b.value, t1.value, t2.value

    def bus_load(messages, bitrate):
        return f.can_bus_load(arr(C.c_uint32, [m[0] for m in messages]), arr(C.c_double, [m[1] for m in messages]),
                              len(messages), bitrate)
    return bit_timing, f.can_frame_bits_worst, bus_load
