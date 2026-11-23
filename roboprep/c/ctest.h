/* Minimal test macros used by the hidden harnesses in roboprep/checks/c. */
#ifndef CTEST_H
#define CTEST_H
#include <stdio.h>
#include <stdint.h>

static int ct_fails = 0;

#define CHECK(name, cond)                                                     \
    do {                                                                      \
        if (cond) { printf("PASS %s\n", name); }                              \
        else { printf("FAIL %s (harness line %d)\n", name, __LINE__); ct_fails++; } \
    } while (0)

#define CHECK_EQ(name, got, exp)                                              \
    do {                                                                      \
        long long g_ = (long long)(got), e_ = (long long)(exp);               \
        if (g_ == e_) { printf("PASS %s\n", name); }                          \
        else { printf("FAIL %s: got %lld (0x%llX), expected %lld (0x%llX)\n", \
                      name, g_, (unsigned long long)g_, e_, (unsigned long long)e_); ct_fails++; } \
    } while (0)

#define CT_DONE() return ct_fails ? 1 : 0

#endif
