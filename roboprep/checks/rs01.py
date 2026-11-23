import re
from roboprep import clab

ANSWERS = {"M1": 95, "M2": 10}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Function pointers: runtime flexibility per test, swappable variants",
    "Function pointers cost an indirect call, no inlining, some memory, harder to follow",
    "Link-time substitution: zero overhead and direct calls, one fake per test binary",
    "A sensible mix or criterion for choosing",
]}
HINTS = {
    "module": "Check the fault flag first, then the current, then clamp the step to +-100.",
    "tests": "Cover soft start, ramp down, the fault and the stays-off path; EXPECT each return value.",
}


def check_module():
    clab.run_ctest(["motor.c"], "rs01_motor_test.c").require(6)


def check_tests():
    r = clab.sh("rm -f *.gcda *.gcno; gcc --coverage -O0 -c motor.c test_motor.c && gcc --coverage motor.o test_motor.o -o t_motor "
                "&& ./t_motor; echo EXIT=$?; gcov -n motor.c")
    out = r.stdout + r.stderr
    assert "ALL TESTS PASSED" in out and "EXIT=0" in out, "your tests fail or did not run:\n" + out[-600:]
    m = re.search(r"File 'motor\.c'\s*\nLines executed:([\d.]+)% of (\d+)", out)
    assert m, "no coverage report for motor.c"
    cov = float(m.group(1))
    assert cov >= 90.0, f"line coverage of motor.c is {cov}%, need 90%"
    n_expect = open("test_motor.c").read().count("EXPECT(") - 1
    assert n_expect >= 5, f"only {n_expect} EXPECT checks; write at least 5"
