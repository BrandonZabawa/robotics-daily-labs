from roboprep import clab

ANSWERS = {"M1": 57, "M2": 120, "M3": (70.6, {"abs": 0.1})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "PREEMPT_RT kernel for bounded latency (threaded interrupts, preemptible kernel)",
    "SCHED_FIFO high priority for the loop thread",
    "mlockall and prefaulting to avoid page faults",
    "Absolute-time sleeps (TIMER_ABSTIME) so errors do not accumulate",
    "Isolated, pinned CPU; no allocation, logging or blocking in the loop; measure with cyclictest",
]}
HINTS = {"periodic": "next.tv_nsec += period; normalize; clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next, NULL)."}


def check_periodic():
    clab.run_ctest(["periodic.c"], "r03_periodic_test.c", sanitize=False, flags="-O2", timeout=30).require(3)
