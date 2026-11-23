import re
from roboprep import clab
from roboprep.clab import CDIR

ANSWERS = {"M1": 0x20003FF8, "M2": 25, "M3": 1}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "HFSR.FORCED: a configurable fault escalated to HardFault",
    "CFSR 0x82 = MemManage DACCVIOL (bit 1) plus MMARVALID (bit 7)",
    "MMFAR = 0 means the faulting data address was 0: a null pointer dereference",
    "Stacked PC locates the instruction (map file or addr2line)",
    "Use the stacked registers to find which pointer was null and trace its initialisation",
]}
HINTS = {
    "decode": "Walk a table of {bit, name} in increasing bit order and return the first set bit.",
    "handler": "The stacked PC is frame[6]; print with sh_puthex and sh_puts.",
}


def check_decode():
    clab.run_ctest(["decode.c"], "c06_decode_test.c").require(7)


def check_handler():
    clab.arm_build([str(CDIR / "cm3_startup.c"), "fault.c", "decode.c", "main.c"], str(CDIR / "cm3.ld"), out="fw.elf")
    out = clab.qemu_run("fw.elf")
    assert "no fault" not in out, "the divide did not trap"
    nm = clab.arm_tool("arm-none-eabi-nm -S fw.elf")
    m = re.search(r"^([0-9a-f]+) ([0-9a-f]+) T do_div$", nm, re.M)
    start, size = int(m.group(1), 16), int(m.group(2), 16)
    pc = re.search(r"pc=0x([0-9A-F]+)", out)
    assert pc, "no pc= line printed:\n" + out[-300:]
    pcv = int(pc.group(1), 16)
    assert start <= pcv < start + size, f"pc=0x{pcv:08X} is not inside do_div (0x{start:08X}..)"
    assert re.search(r"exc_return=0xFFFFFFF9", out), "exc_return line missing or wrong"
    assert re.search(r"cfsr=0x02000000", out), "cfsr line missing or wrong"
    assert "cause=DIVBYZERO" in out, "cause line missing or wrong"
    assert "stack=MSP" in out, "stack line missing or wrong"
