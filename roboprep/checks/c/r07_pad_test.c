#include <stddef.h>
#include "ctest.h"
#include "counters.h"

int main(void) {
    CHECK("a and b at least 64 bytes apart", offsetof(struct counters_good, b) - offsetof(struct counters_good, a) >= 64);
    CHECK("struct aligned to 64", _Alignof(struct counters_good) >= 64);
    CT_DONE();
}
