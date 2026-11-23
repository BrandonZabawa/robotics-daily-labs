import os
import random
import tempfile

PIP = ["cantools"]
DBC = '''VERSION ""
NS_ :
BS_:
BU_: ESC HOST
BO_ 291 MotorStatus: 8 ESC
 SG_ Speed : 0|16@1- (0.1,0) [-3276.8|3276.7] "rpm" HOST
 SG_ Current : 16|16@1- (0.01,0) [-327.68|327.67] "A" HOST
 SG_ Temperature : 32|8@1+ (1,-40) [-40|215] "degC" HOST
 SG_ Fault : 40|1@1+ (1,0) [0|1] "" HOST
'''
LOG = """(1700000000.000000) can0 123#E803F4013C000000
(1700000000.010000) can0 123#EE03F0013C000000
(1700000000.010500) can0 701#05
(1700000000.020000) can0 123#F403EC013D010000
(1700000000.030000) can0 123#FA03E8013D010000
(1700000001.010500) can0 701#05"""
ANSWERS = {"M1": 16, "M2": 0x98FF50E5, "M3": (1650.0, {"rel": 1e-4})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Sysfs: one-shot reads, a system call per channel, fine for slow values",
    "Buffer: enable channels in scan_elements and read packed samples from /dev/iio:deviceN",
    "Trigger (data-ready interrupt or hrtimer) decides when a scan is captured",
    "Buffered scans are time-aligned, timestamped and not lost while user space sleeps",
]}
HINTS = {
    "candump": "Each line: '(ts) channel ID#HEX'. cantools.database.load_string(text, 'dbc').decode_message(id, data).",
    "frames": "struct format '=IB3x8s'. Filter: (rx & mask) == (id & mask), flipped when CAN_INV_FILTER is set.",
    "iio": "Per-channel scale file wins over the shared one; processed = (raw + offset) * scale.",
}


def check_candump(parse, decode):
    fr = parse(LOG)
    assert len(fr) == 6 and fr[2] == (1700000000.0105, "can0", 0x701, b"\x05"), f"third frame: {fr[2] if fr else None}"
    m = decode(fr, DBC)
    assert len(m) == 4, "four MotorStatus frames"
    assert abs(m[0]["Speed"] - 100.0) < 1e-9 and abs(m[0]["Current"] - 5.0) < 1e-9 and m[0]["Temperature"] == 20
    assert m[2]["Fault"] == 1 and abs(m[3]["Speed"] - 101.8) < 1e-9


def check_frames(pack, filt):
    b = pack(0x123, b"\x01\x02")
    assert len(b) == 16 and b[:4] == bytes.fromhex("23010000") and b[4] == 2 and b[8:10] == b"\x01\x02", b.hex()
    e = pack(0x18FF50E5, b"", extended=True)
    assert e[:4] == (0x98FF50E5).to_bytes(4, "little"), "EFF flag in bit 31"
    assert pack(0x7FF, b"", rtr=True)[:4] == (0x400007FF).to_bytes(4, "little"), "RTR flag in bit 30"
    f = [(0x120, 0x7F0)]
    assert filt(0x12A, f) and not filt(0x130, f), "plain id/mask filter"
    inv = [(0x701 | 0x20000000, 0x7FF)]
    assert not filt(0x701, inv) and filt(0x123, inv), "CAN_INV_FILTER passes everything except 0x701"


def check_iio(fn):
    d = tempfile.mkdtemp()
    dev = os.path.join(d, "iio:device0")
    os.makedirs(dev)
    rnd = random.Random(4)
    raw0, raw1, traw = rnd.randrange(4096), rnd.randrange(4096), rnd.randrange(2000)
    files = {"name": "ads1015", "in_voltage0_raw": raw0, "in_voltage1_raw": raw1, "in_voltage_scale": 0.805664062,
             "in_voltage1_scale": 3.0, "in_temp_raw": traw, "in_temp_offset": -500, "in_temp_scale": 50,
             "sampling_frequency": 1600}
    for k, v in files.items():
        open(os.path.join(dev, k), "w").write(f"{v}\n")
    got = fn(dev)
    want = {"voltage0": raw0 * 0.805664062, "voltage1": raw1 * 3.0, "temp": (traw - 500) * 50}
    assert set(got) == set(want), f"channels {sorted(got)}"
    for k in want:
        assert abs(got[k] - want[k]) < 1e-6, f"{k}: {got[k]} vs {want[k]}"




def _cframe_type():
    import ctypes as C

    class F(C.Structure):
        _fields_ = [("ts", C.c_double), ("channel", C.c_char * 16), ("can_id", C.c_uint32), ("len", C.c_uint8),
                    ("data", C.c_uint8 * 64)]
    return F


def c_candump(lib):
    import ctypes as C
    from roboprep.cbind import Functions
    F = _cframe_type()

    class M(C.Structure):
        _fields_ = [("speed", C.c_double), ("current", C.c_double), ("temperature", C.c_double), ("fault", C.c_int)]
    f = Functions(lib, "d12", {"CandumpFrame": F, "MotorStatus": M})

    def parse_candump(text):
        buf = (F * 256)()
        n = f.parse_candump(text.encode(), buf, 256)
        return [(x.ts, x.channel.decode(), x.can_id, bytes(x.data[:x.len])) for x in buf[:n]]

    def decode_motor(frames, dbc_text):
        fr = (F * max(1, len(frames)))()
        for k, (ts, ch, cid, data) in enumerate(frames):
            fr[k].ts, fr[k].channel, fr[k].can_id, fr[k].len = ts, ch.encode(), cid, len(data)
            fr[k].data[:len(data)] = list(data)
        res = (M * max(1, len(frames)))()
        n = f.decode_motor(fr, len(frames), res, len(frames))
        return [{"Speed": m.speed, "Current": m.current, "Temperature": m.temperature, "Fault": m.fault} for m in res[:n]]
    return parse_candump, decode_motor


def c_frames(lib):
    import ctypes as C
    from roboprep.cbind import Functions, u8, out

    class CF(C.Structure):
        _fields_ = [("can_id", C.c_uint32), ("can_mask", C.c_uint32)]
    f = Functions(lib, "d12", {"CanFilter": CF})

    def pack_can_frame(can_id, data, extended=False, rtr=False):
        buf = out(C.c_uint8, 16)
        f.pack_can_frame(can_id, *u8(data), extended, rtr, buf)
        return bytes(buf[:16])

    def filter_pass(rx, filters):
        arr = (CF * max(1, len(filters)))(*[CF(i, m) for i, m in filters])
        return bool(f.filter_pass(rx, arr, len(filters)))
    return pack_can_frame, filter_pass


def c_iio(lib):
    import ctypes as C
    from roboprep.cbind import Functions

    class Ch(C.Structure):
        _fields_ = [("name", C.c_char * 32), ("value", C.c_double)]
    f = Functions(lib, "d12", {"IioChannel": Ch})

    def read_iio(dev):
        buf = (Ch * 64)()
        n = f.read_iio(str(dev).encode(), buf, 64)
        return {c.name.decode(): c.value for c in buf[:n]}
    return (read_iio,)
