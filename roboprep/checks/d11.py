ANSWERS = {"M1": (4.01, {"abs": 0.01}), "M2": 25, "M3": (23.9, {"abs": 0.1})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Byte time 10 us at 1 Mbaud; per-servo exchange about 200 to 300 us including turnaround",
    "Eight servos exceed (or nearly exceed) the 2 ms period: use broadcast sync-write or lower the rate",
    "Budget eaten by turnaround, gaps, header/CRC overhead and retries",
    "Absolute (idempotent) setpoints make retries safe",
]}
HINTS = {
    "master": "Request = addr, 0x03, start hi/lo, count hi/lo, CRC low byte then high byte.",
    "slave": "Silent on bad CRC or other address; exception = addr, fn | 0x80, code.",
    "budget": "Seven extra characters: 3.5 after the request and 3.5 after the response.",
}


def _crc(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def _f(body):
    c = _crc(body)
    return bytes(body) + bytes([c & 0xFF, c >> 8])


def check_master(req, parse):
    assert req(0x11, 0x006B, 3) == bytes.fromhex("1103006B00037687"), f"classic example request: {req(0x11, 0x6B, 3).hex()}"
    assert parse(_f(bytes([0x11, 0x03, 0x06, 0x02, 0x2B, 0x00, 0x00, 0x00, 0x64])), 0x11) == [0x022B, 0, 0x64]
    try:
        parse(_f(bytes([0x11, 0x83, 0x02])), 0x11)
        raise AssertionError("exception response must raise ModbusException")
    except AssertionError:
        raise
    except Exception as e:
        assert type(e).__name__ == "ModbusException" and e.args[0] == 2, f"raised {e!r}"
    bad = bytearray(_f(bytes([0x11, 0x03, 0x02, 0x00, 0x01])))
    bad[3] ^= 1
    try:
        parse(bytes(bad), 0x11)
        raise AssertionError("bad CRC must raise ValueError")
    except ValueError:
        pass


def check_slave(fn):
    regs = {100: 0x1234, 101: 0x5678, 102: 7}
    r = fn(_f(bytes([5, 0x03, 0, 100, 0, 2])), 5, regs)
    assert r == _f(bytes([5, 0x03, 4, 0x12, 0x34, 0x56, 0x78])), "read 2 registers"
    assert fn(_f(bytes([5, 0x03, 0, 103, 0, 1])), 5, regs) == _f(bytes([5, 0x83, 2])), "illegal address"
    assert fn(_f(bytes([6, 0x03, 0, 100, 0, 1])), 5, regs) is None, "other slave: stay silent"
    w = _f(bytes([5, 0x06, 0, 102, 0x00, 0x2A]))
    assert fn(w, 5, regs) == w and regs[102] == 42, "write single register echoes the request"
    assert fn(_f(bytes([5, 0x2B, 0, 0])), 5, regs) == _f(bytes([5, 0xAB, 1])), "illegal function"
    b = bytearray(w)
    b[-1] ^= 0xFF
    assert fn(bytes(b), 5, regs) is None, "bad CRC: stay silent"


def check_budget(pt, rate):
    assert abs(pt(19200, 8, 25, 0.001) - 0.0239167) < 1e-6
    assert abs(rate(4, 115200, 8, 9, 0.0005) - 1 / (4 * ((24 * 11) / 115200 + 0.0005))) < 1e-6


def c_master(lib):
    import ctypes as C
    from roboprep.cbind import Functions, u8, out
    f = Functions(lib, "d11")

    class ModbusException(Exception):
        pass

    def read_holding_request(slave, start, count):
        buf = out(C.c_uint8, 8)
        return bytes(buf[:f.mb_read_holding_request(slave, start, count, buf)])

    def parse_read_response(frame, slave):
        regs, code = out(C.c_uint16, 128), C.c_uint8()
        n = f.mb_parse_read_response(*u8(frame), slave, regs, 128, C.byref(code))
        if n == -1:
            raise ValueError("bad frame")
        if n == -2:
            raise ModbusException(code.value)
        return list(regs[:n])
    return read_holding_request, parse_read_response


def c_slave(lib):
    import ctypes as C
    from roboprep.cbind import Functions, u8, out

    class R(C.Structure):
        _fields_ = [("addr", C.c_uint16), ("value", C.c_uint16)]
    f = Functions(lib, "d11", {"MbRegister": R})

    def slave_handle(frame, my_addr, regs):
        keys = list(regs)
        table = (R * max(1, len(keys)))(*[R(k, regs[k]) for k in keys])
        buf = out(C.c_uint8, 256)
        n = f.mb_slave_handle(*u8(frame), my_addr, table, len(keys), buf, 256)
        for i, k in enumerate(keys):
            regs[k] = table[i].value
        return bytes(buf[:n]) if n else None
    return (slave_handle,)


def c_budget(lib):
    from roboprep.cbind import Functions
    f = Functions(lib, "d11")
    return (lambda baud, rq, rs, ta, bits_per_char=11: f.mb_poll_time(baud, rq, rs, ta, bits_per_char),
            f.mb_max_poll_rate_per_node)
