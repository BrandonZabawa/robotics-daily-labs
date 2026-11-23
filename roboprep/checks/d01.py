import binascii
import os
from roboprep import clab

ANSWERS = {"M1": (-0.08, {"abs": 0.01}), "M2": 0x07, "M3": (1 / 65536, {"rel": 0.01})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Five parameters: width and polynomial, init, reflect in/out, final XOR",
    "Also byte order of the CRC on the wire and which bytes are covered",
    "Compute the check value of '123456789' on both sides and compare with the catalogue",
    "Matching check values point the bug at framing or byte order instead of the algorithm",
]}
HINTS = {
    "crc16": "CCITT-FALSE: MSB first, init 0xFFFF, poly 0x1021. MODBUS: LSB first, init 0xFFFF, poly 0xA001.",
    "crc32": "Reflected: table[i] from 8 shifts with 0xEDB88320; crc = table[(crc ^ b) & 0xFF] ^ (crc >> 8).",
    "baud": "BRR = round(f_clk / baud).",
}




MODBUS_VECTORS = [("", 0xFFFF), ("00", 0x40BF), ("00010203040506", 0xC6A1),
                  (bytes(range(64)).hex(), 0x08D9),
                  ("0b30557a9fc4e90e33587da2c7ec11365b80a5caef14395e83a8cdf2173c6186ab", 0x8E74)]


def check_crc16(ccitt, modbus):
    assert ccitt(b"123456789") == 0x29B1, f"CCITT-FALSE check value: got 0x{ccitt(b'123456789'):04X}, want 0x29B1"
    assert modbus(b"123456789") == 0x4B37, f"MODBUS check value: got 0x{modbus(b'123456789'):04X}, want 0x4B37"
    for n in (0, 1, 7, 64):
        d = os.urandom(n)
        assert ccitt(d) == binascii.crc_hqx(d, 0xFFFF), f"CCITT-FALSE wrong for a {n}-byte message"
    for hexmsg, crc in MODBUS_VECTORS:
        d = bytes.fromhex(hexmsg)
        assert modbus(d) == crc, f"MODBUS wrong for a {len(d)}-byte message"


def check_crc32():
    clab.run_ctest(["crc32.c"], "d01_crc32_test.c").require(3)


def check_baud(fn):
    for f, b in [(16e6, 115200), (170e6, 1_000_000), (8e6, 9600), (48e6, 921600)]:
        brr, actual, err = fn(f, b)
        e_brr = round(f / b)
        assert brr == e_brr, f"{f/1e6:g} MHz, {b}: BRR {brr}, want {e_brr}"
        assert abs(actual - f / e_brr) < 1e-6, "actual baud wrong"
        assert abs(err - 100 * (f / e_brr - b) / b) < 1e-6, "error percent wrong (sign: actual minus target)"


def c_crc16(lib):
    from roboprep.cbind import Functions, u8
    f = Functions(lib, "d01")
    return (lambda d: f.crc16_ccitt_false(*u8(d)), lambda d: f.crc16_modbus(*u8(d)))


def c_baud(lib):
    import ctypes as C
    from roboprep.cbind import Functions
    f = Functions(lib, "d01")

    def uart_brr(f_clk, baud):
        a, e = C.c_double(), C.c_double()
        brr = f.uart_brr(f_clk, baud, C.byref(a), C.byref(e))
        return brr, a.value, e.value
    return (uart_brr,)
