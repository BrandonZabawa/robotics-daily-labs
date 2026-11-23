from roboprep import clab

ANSWERS = {"M1": 0xABFFF7FF, "M2": 0x02000008, "M3": 0x48000818}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Every volatile read or write in the source becomes a real access, in program order (no caching in a register, no deletion)",
    "So a polled status register is re-read on every loop pass",
    "It does not make read-modify-write (|=, ^=, ++) atomic; an interrupt can land between load and store",
    "It is not a memory barrier: no ordering guarantee for non-volatile data and nothing across cores",
    "Shared ISR flag: volatile plus a naturally atomic access size (aligned 32-bit), or mask interrupts or use C11 atomics for more",
]}
HINTS = {
    "regs": "mask(32) must not shift by 32; field_write = (reg & ~(m << pos)) | ((val & m) << pos).",
    "volatile": "Read the status through a pointer to volatile uint32_t.",
}


def check_regs():
    clab.run_ctest(["regs.c"], "c01_regs_test.c").require(10)


def check_volatile():
    r = clab.run_ctest(["wait.c"], "c01_wait_test.c", flags="-O2", sanitize=False, timeout=5)
    if r.stage == "timeout":
        raise AssertionError("wait_ready never returned at -O2: the load was hoisted out of the loop")
    r.require(1)
