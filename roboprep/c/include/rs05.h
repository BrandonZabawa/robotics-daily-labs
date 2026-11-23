/* rs05.h: C/C++ versions of RS05. */
#ifndef RDL_RS05_H
#define RDL_RS05_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: memory under test, accessed through callbacks so the grader can inject faults. Cells hold 0 or 1. */
typedef struct {
    uint8_t (*read)(void *ctx, size_t addr);
    void (*write)(void *ctx, size_t addr, uint8_t value);
    size_t n;
    void *ctx;
} RamOps;
bool march_c_minus(const RamOps *ram);   /* true = no fault found; exactly 10n operations */
/* Task 2 */
double reliability(double t, double mtbf);
double series(const double *rs, size_t n);
double parallel(const double *rs, size_t n);
double series_mtbf(const double *mtbfs, size_t n);
RDL_END
#endif
