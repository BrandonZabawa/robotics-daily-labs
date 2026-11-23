from roboprep import clab

ANSWERS = {"M1": (3.077, {"abs": 1e-3}), "M2": 5, "M3": 10}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Isolate a core for the control thread (isolcpus, nohz_full) and pin it with SCHED_FIFO",
    "Pin the camera pipeline to other cores",
    "Route interrupts with /proc/irq/N/smp_affinity (and irqbalance settings) away from the control core, except ones it consumes",
    "Logging and housekeeping on a remaining core; verify with /proc/interrupts, ps psr, cyclictest",
]}
HINTS = {
    "padding": "_Alignas(64) on each member puts them on separate 64-byte lines.",
    "affinity": "mask = sum(1 << cpu); /proc/interrupts: first line lists CPUs, then 'IRQ: count count ... name'.",
    "amdahl": "1 / ((1 - p) + p / n).",
}

SAMPLE = """           CPU0       CPU1       CPU2       CPU3
  0:         40          0          0          0   IO-APIC    2-edge      timer
 24:     123456          7     890123          0   PCI-MSI 1048576-edge      eth0-rx-0
 31:          0          0          0     500000   PCI-MSI 2097152-edge      can0
NMI:          0          0          0          0   Non-maskable interrupts
"""


def check_padding():
    clab.run_ctest([], "r07_pad_test.c", flags="-I.", sanitize=False).require(2)


def check_affinity(mask, parse, irq):
    assert mask({0, 2}) == "0x5" and mask({3}) == "0x8" and mask(range(4)) == "0xf", "cpu_mask"
    assert parse("0000000f") == {0, 1, 2, 3} and parse("00000000,00000100") == {8}, "parse_mask (also comma-separated groups)"
    assert irq(SAMPLE, 24) == [123456, 7, 890123, 0], f"irq 24 -> {irq(SAMPLE, 24)}"
    assert irq(SAMPLE, 31) == [0, 0, 0, 500000] and irq(SAMPLE, 99) is None


def check_amdahl(fn):
    assert abs(fn(0.9, 4) - 1 / 0.325) < 1e-9 and abs(fn(0.5, 2) - 4 / 3) < 1e-9 and fn(1.0, 8) == 8.0


def c_affinity(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr, out
    f = Functions(lib, "r07")

    def irq(text, n):
        buf = out(C.c_uint64, 64)
        k = f.irq_counts(text.encode(), n, buf, 64)
        return None if k < 0 else list(buf[:k])

    def parse_mask(text):
        v = f.parse_mask(text.encode())
        return {k for k in range(64) if v >> k & 1}
    return (lambda cpus: hex(f.cpu_mask(arr(C.c_int, list(cpus)), len(list(cpus)))), parse_mask, irq)


def c_amdahl(lib):
    from roboprep.cbind import Functions
    return (Functions(lib, "r07").amdahl,)
