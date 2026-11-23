import re
from roboprep import clab

ANSWERS = {"M1": 90, "M2": 9}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Start with high-value required rules (17.7, 16.4, 13.4, 10.x, 15.1)",
    "Automate in CI (cppcheck MISRA addon, clang-tidy); block only new findings",
    "Exclude or blanket-deviate generated vendor code; document each intentional deviation",
    "Burn down the backlog by module, safety-relevant code first",
]}
HINTS = {
    "misra": "Separate the assignment from the comparison, add default:, replace goto with if/else, cast unused results to (void).",
    "trace": "Find 'test_name(' lines, then read @verifies IDs from the line above.",
}
GRADED = {"13.4", "15.1", "15.7", "16.4", "17.7"}

SRC = r"""
/* @verifies REQ-1 */
static void test_soft_start(void) { }
/* @verifies REQ-2, REQ-3 */
static void test_overcurrent_stops(void) { }
static void test_helper_untraced(void) { }
/* @verifies REQ-3 */
static void test_stays_faulted(void) { }
"""


def check_misra():
    out = clab.sh("cppcheck -q --addon=misra --enable=style filter.c 2>&1").stdout
    found = set(re.findall(r"misra-c2012-([0-9.]+)", out)) & GRADED
    assert not found, "still violates MISRA rules: " + ", ".join(sorted(found))
    clab.run_ctest(["filter.c"], "rs02_filter_test.c").require(5)


def check_trace(fn):
    got = fn(["REQ-1", "REQ-2", "REQ-3", "REQ-4"], SRC)
    want = {"REQ-1": ["test_soft_start"], "REQ-2": ["test_overcurrent_stops"],
            "REQ-3": ["test_overcurrent_stops", "test_stays_faulted"], "REQ-4": []}
    assert got == want, f"matrix: {got}"
