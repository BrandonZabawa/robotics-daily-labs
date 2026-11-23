from roboprep import clab

ANSWERS = {"M1": 0xF0, "M2": 12, "M3": 8}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Access an object only through its own (compatible) type or a character type",
    "Exceptions: char/unsigned char, memcpy, union reads in C",
    "Compiler assumes pointers of different types do not alias, so it may cache or reorder",
    "Result: stale or reordered values at -O2; fix with memcpy (same machine code)",
]}
HINTS = {
    "layout": "Walk member by member: next offset rounded up to the member's alignment; size rounded to max alignment.",
    "wire": "Big-endian means the most significant byte goes first: p[0] = v >> 24.",
}

PROG = r"""#include <stdio.h>
#include <stdint.h>
#include <stddef.h>
struct A { char a; double b; char c; };
struct B { double b; char a; char c; };
struct C { uint8_t id; uint32_t v; uint16_t crc; };
struct D { uint16_t x; uint8_t y; uint8_t z; uint16_t w; };
int main(void) {
%s
    return 0;
}
"""


def check_layout(pred):
    if any(v is None for v in pred.values()):
        raise NotImplementedError
    keys = list(pred)
    open("layout.c", "w").write(PROG % "\n".join(f'    printf("%d\\n", (int)({k}));' for k in keys))
    out = clab.compile_run("layout.c", flags="-O0").split()
    wrong = [f"{k}: you said {pred[k]}, compiler says {a}" for k, a in zip(keys, out) if int(pred[k]) != int(a)]
    assert not wrong, "; ".join(wrong)


def check_wire():
    r = clab.sh("gcc -std=c11 -O2 -Wstrict-aliasing=2 -Werror=strict-aliasing -c wire.c -o /dev/null")
    assert r.returncode == 0, "strict aliasing violation:\n" + r.stderr[-600:]
    clab.run_ctest(["wire.c"], "c04_wire_test.c").require(6)
