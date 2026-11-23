import re
from roboprep import clab

ANSWERS = {"M1": 44, "M2": 11, "M3": 32767}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Undefined: no requirements, compiler may assume it never happens",
    "Unspecified: one of several allowed results, not documented; implementation-defined: chosen and documented",
    "Signed overflow is undefined, so x + 1 < x is folded to false (return 0) for int but kept for unsigned",
    "Fix: check against the limit before the operation, use unsigned or __builtin_add_overflow",
]}
HINTS = {
    "predict": "Promotion turns every uint8_t and uint16_t operand into int before any arithmetic.",
    "saturate": "For int32_t, compare a against INT32_MAX - b (b > 0) before adding.",
    "categories": "If the standard lists it under 'undefined behavior', the optimizer may exploit it.",
}

PROG = r"""#include <stdio.h>
#include <stdint.h>
int main(void) {
    uint8_t a = 200, b = 100; uint32_t u = 1; unsigned short s = 0xFFFF;
    (void)a; (void)b; (void)u; (void)s;
%s
    return 0;
}
"""
CAT = {
    "signed int overflow": "undefined",
    "order in which f(g(), h()) evaluates g and h": "unspecified",
    "right shift of a negative int": "implementation-defined",
    "x << 32 where x is uint32_t": "undefined",
    "whether plain char is signed": "implementation-defined",
    "modifying a string literal": "undefined",
    "values of padding bytes in a struct": "unspecified",
    "converting 300 to int8_t": "implementation-defined",
}


def check_predict(pred):
    keys = list(pred)
    body = "\n".join(f'    printf("%d\\n", (int)({k}));' for k in keys)
    open("predict.c", "w").write(PROG % body)
    out = clab.compile_run("predict.c", flags="-O0 -w").split()
    wrong = []
    for k, actual in zip(keys, out):
        if pred[k] is None:
            raise NotImplementedError
        if int(pred[k]) != int(actual):
            wrong.append(f"{k}: you said {pred[k]}, compiler says {actual}")
    assert not wrong, "; ".join(wrong)


def check_saturate():
    clab.run_ctest(["sat.c"], "c02_sat_test.c").require(9)


def check_categories(cats):
    if any(v is None for v in cats.values()):
        raise NotImplementedError
    wrong = [k for k, v in CAT.items() if str(cats.get(k, "")).strip().lower() != v]
    assert not wrong, f"{len(wrong)} wrong: " + "; ".join(wrong)
