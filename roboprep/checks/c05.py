import re
from roboprep import clab

ANSWERS = {"M1": 32, "M2": 0x54, "M3": 0x101}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Core loads SP from word 0 and PC from word 1 (Thumb bit)",
    "Reset_Handler copies .data from flash (LMA) to RAM (VMA) and zeroes .bss",
    "SystemInit sets the clock tree (PLL, prescalers, flash wait states) before main",
    "Peripheral clocks start gated; enable the RCC bit before touching the peripheral",
    "Writes to a gated peripheral are ignored (reads return 0): silent failure",
]}
HINTS = {"boot": "`.data : {...} > RAM AT> FLASH` and `_sidata = LOADADDR(.data);` then copy word by word."}


def check_boot():
    clab.arm_build(["startup.c", "main.c"], "link.ld", out="fw.elf")
    hdr = clab.arm_tool("arm-none-eabi-objdump -h fw.elf")
    m = re.search(r"\.data\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)", hdr)
    assert m, "no .data section in the image"
    vma, lma = int(m.group(2), 16), int(m.group(3), 16)
    assert 0x20000000 <= vma < 0x20010000, f".data runs at 0x{vma:08X}; it must run in RAM"
    assert lma < 0x00040000, f".data loads from 0x{lma:08X}; its initial values must live in flash (AT> FLASH)"
    open("garbage.bin", "wb").write(b"\xa5" * 65536)
    out = clab.qemu_run("fw.elf", extra="-device loader,file=garbage.bin,addr=0x20000000")
    assert "booted" in out, "never reached main (check the vector table and ENTRY):\n" + out[-300:]
    assert "data_ok" in out, ".data was not copied to RAM"
    assert "bss_ok" in out, ".bss was not zeroed"
