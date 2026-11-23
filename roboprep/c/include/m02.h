/* m02.h: C/C++ versions of M02. */
#ifndef RDL_M02_H
#define RDL_M02_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: state = (A << 1) | B; valid steps 0->1->3->2->0 count +1, the reverse -1; a two-state jump is an error. */
typedef struct { uint8_t prev; int32_t position; uint32_t errors; } QuadDecoder;
void qd_init(QuadDecoder *d);
int32_t qd_update(QuadDecoder *d, int a, int b);
/* Task 2 */
int64_t signed_delta(uint64_t now, uint64_t prev, int bits);
double rpm(int64_t delta_counts, double dt, uint32_t lines);
RDL_END
#endif
