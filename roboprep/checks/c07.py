from roboprep import clab

ANSWERS = {"M1": 15, "M2": 2, "M3": 768}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "volatile orders only volatile accesses; the slot write is a plain store the compiler may move",
    "The CPU can make the head update visible before the data (no hardware ordering from volatile)",
    "Release on head: all earlier writes are visible to whoever acquires that value",
    "Acquire stops the consumer's slot read from being hoisted before the head read; atomics also remove the data race",
]}
HINTS = {"spsc": "push: load head relaxed, tail acquire; full if head - tail == QCAP; write slot; store head + 1 release."}


def _parse(out):
    lines = out.splitlines()
    return clab.CResult(not any(l.startswith("FAIL") for l in lines), out,
                        [l for l in lines if l.startswith("PASS")], [l for l in lines if l.startswith("FAIL")], "run")


def check_spsc():
    r = clab.run_ctest(["spsc.c"], "c07_spsc_test.c", flags="-O2 -fsanitize=thread", sanitize=False, timeout=60)
    if "FATAL: ThreadSanitizer" in r.output:          # some kernels need address randomization off
        p = clab.sh("setarch $(uname -m) -R ./ctest_bin", timeout=60)
        r = _parse(p.stdout + p.stderr)
        if "FATAL: ThreadSanitizer" in r.output:
            print("(ThreadSanitizer cannot run here; stress test only)")
            r = clab.run_ctest(["spsc.c"], "c07_spsc_test.c", flags="-O2", sanitize=False, timeout=60)
    if "ThreadSanitizer: data race" in r.output:
        raise AssertionError("ThreadSanitizer found a data race: an index or slot is accessed without the right atomics")
    r.require(5)
