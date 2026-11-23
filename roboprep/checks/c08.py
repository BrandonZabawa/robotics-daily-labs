from roboprep import clab

ANSWERS = {"M1": (49.71, {"abs": 0.01}), "M2": 1, "M3": 20}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Painting gives a high-water mark for sizing, but only after the fact",
    "Canary checked at context switch catches overflow late and can be skipped over",
    "MPU guard region faults immediately on the first bad access with a precise PC",
    "Mentions a cost or trade-off (MPU regions and alignment, check overhead, detection latency)",
]}
HINTS = {"patterns": "Pool: each free block's first word stores the next free pointer. Debounce: count only samples that differ from the output."}


def check_patterns():
    clab.run_ctest(["patterns.c"], "c08_patterns_test.c").require(11)
