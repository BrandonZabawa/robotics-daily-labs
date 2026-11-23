/* r07.h: C/C++ versions of R07 Tasks 2 and 3 (Task 1 is already C). */
#ifndef RDL_R07_H
#define RDL_R07_H
#include "rdl.h"
RDL_BEGIN
/* Task 2 */
uint64_t cpu_mask(const int *cpus, size_t n);
uint64_t parse_mask(const char *text);              /* hex, optionally comma-separated 32-bit groups */
/* Per-CPU counts of one IRQ from /proc/interrupts text; returns the number of CPUs, or -1 if the IRQ is absent. */
int irq_counts(const char *proc_interrupts, int irq, uint64_t *counts, size_t cap);
/* Task 3 */
double amdahl(double p, double n);
RDL_END
#endif
