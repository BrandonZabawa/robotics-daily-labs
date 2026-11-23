import os

ANSWERS = {"M1": 61444, "M2": 15, "M3": 0x62}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Both send Address Claimed (PGN 0xEE00) with their NAME for 0x80",
    "Lower NAME keeps the address",
    "Loser claims another address (if arbitrary-address capable) or sends Cannot Claim from 0xFE",
    "NAME fields are unique per device, so the result is deterministic; identical units need different identity/instance",
]}
HINTS = {
    "j1939": "PF = bits 23..16; PDU1 if PF < 240 (PS is the destination and not in the PGN).",
    "isotp": "First frame 0x10 | len>>8, len & 0xFF, 6 bytes; then 0x21, 0x22 ... with 7 bytes each.",
    "uds": "Check the service, then the length, then session or DID; NRC frame is 7F SID code.",
}


def check_j1939(parse, claim):
    assert parse(0x0CF00400) == {"priority": 3, "pgn": 0xF004, "sa": 0x00, "da": None}, f"EEC1: {parse(0x0CF00400)}"
    assert parse(0x18EAFF00) == {"priority": 6, "pgn": 0xEA00, "sa": 0x00, "da": 0xFF}, f"request: {parse(0x18EAFF00)}"
    assert parse(0x18EEFF80) == {"priority": 6, "pgn": 0xEE00, "sa": 0x80, "da": 0xFF}, "address claim"
    assert claim([0xA00C81045A20021B, 0x800C81045A20021B, 0xA00C81045A20021C]) == 0x800C81045A20021B


def check_isotp(seg, reasm):
    f = seg(b"\x22\xF1\x90")
    assert f == [bytes([0x03, 0x22, 0xF1, 0x90, 0xCC, 0xCC, 0xCC, 0xCC])], f"single frame: {f}"
    msg = bytes(range(20))
    f = seg(msg)
    assert f[0] == bytes([0x10, 20, 0, 1, 2, 3, 4, 5]) and f[1][0] == 0x21 and f[2][0] == 0x22, "first/consecutive headers"
    assert f[2] == bytes([0x22, 13, 14, 15, 16, 17, 18, 19]), "last frame"
    big = os.urandom(300)
    f = seg(big)
    assert all(len(x) == 8 for x in f) and len(f) == 1 + -(-294 // 7), "frame count for 300 bytes"
    assert f[16][0] == 0x20, "sequence number wraps from 15 to 0"
    for n in (0, 7, 8, 100, 300):
        p = os.urandom(n)
        assert reasm(seg(p)) == p, f"round trip of {n} bytes"


def check_uds(cls):
    s = cls()
    assert s.handle(bytes([0x22, 0xF1, 0x90])) == b"\x62\xF1\x90BZ-STORM-0000001", "read VIN"
    assert s.handle(bytes([0x22, 0x12, 0x34])) == bytes([0x7F, 0x22, 0x31]), "unknown DID"
    assert s.handle(bytes([0x22, 0xF1])) == bytes([0x7F, 0x22, 0x13]), "short request"
    assert s.handle(bytes([0x2E, 0xF1, 0x90]) + b"X") == bytes([0x7F, 0x2E, 0x7F]), "write needs extended session"
    assert s.handle(bytes([0x10, 0x03])) == bytes([0x50, 0x03]), "enter extended session"
    assert s.handle(bytes([0x2E, 0xF1, 0x87]) + b"G431") == bytes([0x6E, 0xF1, 0x87]), "write in extended session"
    assert s.handle(bytes([0x22, 0xF1, 0x87])) == b"\x62\xF1\x87G431", "read back"
    assert s.handle(bytes([0x85, 0x01])) == bytes([0x7F, 0x85, 0x11]), "unknown service"


def c_j1939(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr

    class J(C.Structure):
        _fields_ = [("priority", C.c_uint8), ("pgn", C.c_uint32), ("sa", C.c_uint8), ("da", C.c_int)]
    f = Functions(lib, "d10", {"J1939Id": J})

    def parse_j1939(can_id):
        j = J()
        f.parse_j1939(can_id, C.byref(j))
        return {"priority": j.priority, "pgn": j.pgn, "sa": j.sa, "da": None if j.da < 0 else j.da}
    return parse_j1939, lambda names: f.claim_winner(arr(C.c_uint64, names), len(names))


def c_isotp(lib):
    import ctypes as C
    from roboprep.cbind import Functions, u8, out
    f = Functions(lib, "d10")

    def isotp_segment(payload):
        cap = len(payload) // 7 + 2
        buf = out(C.c_uint8, 8 * cap)
        n = f.isotp_segment(*u8(payload), buf, cap)
        return [bytes(buf[8 * k:8 * k + 8]) for k in range(n)]

    def isotp_reassemble(frames):
        res = out(C.c_uint8, 4096)
        n = f.isotp_reassemble(u8(b"".join(frames))[0], len(frames), res, 4096)
        if n < 0:
            raise ValueError("sequence error")
        return bytes(res[:n])
    return isotp_segment, isotp_reassemble


def c_uds(lib):
    import ctypes as C
    from roboprep.cbind import Functions, u8, out

    class Did(C.Structure):
        _fields_ = [("did", C.c_uint16), ("len", C.c_uint8), ("data", C.c_uint8 * 32)]

    class S(C.Structure):
        _fields_ = [("session", C.c_uint8), ("n_dids", C.c_size_t), ("dids", Did * 8)]
    f = Functions(lib, "d10", {"UdsServer": S})

    class UdsServer:
        def __init__(self):
            self._s = S()
            f.uds_init(C.byref(self._s))

        def handle(self, req):
            buf = out(C.c_uint8, 64)
            n = f.uds_handle(C.byref(self._s), *u8(req), buf, 64)
            return bytes(buf[:n])
    return (UdsServer,)
