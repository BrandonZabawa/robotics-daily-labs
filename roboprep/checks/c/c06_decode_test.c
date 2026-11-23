#include <string.h>
#include "ctest.h"
const char *stack_used(uint32_t exc_return);
const char *cfsr_cause(uint32_t cfsr);

int main(void) {
    CHECK("MSP for 0xFFFFFFF9", strcmp(stack_used(0xFFFFFFF9u), "MSP") == 0);
    CHECK("PSP for 0xFFFFFFFD", strcmp(stack_used(0xFFFFFFFDu), "PSP") == 0);
    CHECK("PSP for 0xFFFFFFED (FPU frame)", strcmp(stack_used(0xFFFFFFEDu), "PSP") == 0);
    CHECK("DIVBYZERO", strcmp(cfsr_cause(0x02000000u), "DIVBYZERO") == 0);
    CHECK("UNDEFINSTR", strcmp(cfsr_cause(0x00010000u), "UNDEFINSTR") == 0);
    CHECK("DACCVIOL beats MMARVALID", strcmp(cfsr_cause(0x00000082u), "DACCVIOL") == 0);
    CHECK("PRECISERR", strcmp(cfsr_cause(0x00008200u), "PRECISERR") == 0);
    CHECK("NONE", strcmp(cfsr_cause(0x00000080u), "NONE") == 0);
    CT_DONE();
}
