import os
import struct
import zlib

ANSWERS = {"M1": 6, "M2": (6.9, {"abs": 0.05}), "M3": (444, {"abs": 1})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "CRC proves integrity, not that the firmware works on this board",
    "Bootloader grants limited trial boots; the app confirms after proving itself, otherwise rollback",
    "Crashes, hangs or watchdog resets exhaust the counter",
    "Healthy = minimum uptime, CAN up, sensors plausible, power stage self-test, no latched faults",
]}
HINTS = {
    "validate": "Check magic, unpack <III at offset 4, bound the length, compare zlib.crc32 of the payload.",
    "write": "Erase ceil(len / SECTOR) sectors from slot_addr // SECTOR, program, validate the read-back.",
    "boot": "Pending and tries left and valid: tries += 1 and boot it; otherwise drop pending and boot a valid slot.",
}


def _img(v, p):
    return b"RDL1" + struct.pack("<III", v, len(p), zlib.crc32(p)) + p


def check_validate(fn):
    p = os.urandom(5000)
    img = bytearray(_img(7, p)) + b"\xff" * 100
    assert fn(img, 65536) == (True, 7), "good image"
    bad = bytearray(img)
    bad[100] ^= 1
    assert fn(bad, 65536) == (False, None), "flipped payload bit must fail the CRC"
    assert fn(b"\xff" * 64, 65536) == (False, None), "erased slot"
    huge = bytearray(img)
    struct.pack_into("<I", huge, 8, 10**9)
    assert fn(huge, 65536) == (False, None), "absurd length must be rejected before reading"


SECTOR = 4096


class Flash:
    """Same model as the notebook's: erase sets a sector to 0xFF, program can only clear bits."""
    def __init__(self, size):
        self.mem = bytearray(b"\xff" * size)
        self.erases = [0] * (size // SECTOR)

    def erase(self, sector):
        self.mem[sector * SECTOR:(sector + 1) * SECTOR] = b"\xff" * SECTOR
        self.erases[sector] += 1

    def program(self, addr, data):
        for i, b in enumerate(data):
            old = self.mem[addr + i]
            if b & ~old & 0xFF:
                raise RuntimeError(f"program at 0x{addr + i:X} would set bits 0 -> 1 without an erase")
            self.mem[addr + i] = old & b


def check_write(fn):
    f = Flash(64 * 1024)
    f.program(0x4000, b"\x00" * 64)                  # old data in the slot
    img = _img(3, os.urandom(9000))
    assert fn(f, 0x4000, img, 32768) is True, "write + verify failed"
    assert f.erases[4:7] == [1, 1, 1] and sum(f.erases) == 3, f"erase counts {f.erases[:8]}: erase exactly the 3 sectors needed"


def check_boot(fn):
    m = {"active": "A", "pending": "B", "tries": 0}
    seq = [fn(m, {"A": True, "B": True}) for _ in range(4)]
    assert seq == ["B", "B", "B", "A"] and m["pending"] is None, f"trial boots then rollback: {seq}, {m}"
    m = {"active": "A", "pending": "B", "tries": 0}
    assert fn(m, {"A": True, "B": False}) == "A" and m["pending"] is None, "invalid pending image: roll back at once"
    m = {"active": "A", "pending": None, "tries": 0}
    assert fn(m, {"A": False, "B": True}) == "B", "corrupt active slot: fall back to the other"
    assert fn(m, {"A": False, "B": False}) is None, "nothing valid: stay in the bootloader"


def c_validate(lib):
    import ctypes as C
    from roboprep.cbind import Functions, u8
    f = Functions(lib, "rs03")

    def validate(slot_bytes, max_len):
        v = C.c_uint32()
        ok = f.validate_image(*u8(slot_bytes), max_len, C.byref(v))
        return (True, v.value) if ok else (False, None)
    return (validate,)


def c_write(lib):
    import ctypes as C
    from roboprep.cbind import Functions, u8
    ER = C.CFUNCTYPE(C.c_bool, C.c_void_p, C.c_uint32)
    PR = C.CFUNCTYPE(C.c_bool, C.c_void_p, C.c_uint32, C.POINTER(C.c_uint8), C.c_size_t)
    RD = C.CFUNCTYPE(None, C.c_void_p, C.c_uint32, C.POINTER(C.c_uint8), C.c_size_t)

    class Ops(C.Structure):
        _fields_ = [("erase", ER), ("program", PR), ("read", RD), ("ctx", C.c_void_p)]
    f = Functions(lib, "rs03", {"FlashOps": Ops})

    def write_image(flash, slot_addr, image, max_len):
        errors = []

        def erase(_, s):
            try:
                flash.erase(s)
                return True
            except Exception as e:  # noqa: BLE001
                errors.append(e)
                return False

        def program(_, addr, data, n):
            try:
                flash.program(addr, bytes(data[:n]))
                return True
            except Exception as e:  # noqa: BLE001
                errors.append(e)
                return False

        def read(_, addr, out, n):
            C.memmove(out, bytes(flash.mem[addr:addr + n]), n)
        cbs = (ER(erase), PR(program), RD(read))
        ok = f.write_image(C.byref(Ops(*cbs, None)), slot_addr, *u8(image), max_len)
        if errors:
            raise errors[0]
        return bool(ok)
    return (write_image,)


def c_boot(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr

    class M(C.Structure):
        _fields_ = [("active", C.c_int), ("pending", C.c_int), ("tries", C.c_int)]
    f = Functions(lib, "rs03", {"BootMeta": M})
    idx = {"A": 0, "B": 1, None: -1}

    def choose_slot(meta, valid, max_tries=3):
        m = M(idx[meta["active"]], idx[meta["pending"]], meta["tries"])
        r = f.choose_slot(C.byref(m), arr(C.c_bool, [bool(valid["A"]), bool(valid["B"])]), max_tries)
        names = {0: "A", 1: "B", -1: None}
        meta["active"], meta["pending"], meta["tries"] = names[m.active], names[m.pending], m.tries
        return names[r]
    return (choose_slot,)
