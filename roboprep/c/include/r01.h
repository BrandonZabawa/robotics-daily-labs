/* r01.h: C/C++ versions of R01. Task i has worst-case execution time c[i] and period (= deadline) t[i]. */
#ifndef RDL_R01_H
#define RDL_R01_H
#include "rdl.h"
RDL_BEGIN
/* Task 1 */
double ll_bound(int n);
enum { RM_SCHEDULABLE = 0, RM_UNKNOWN = 1, RM_UNSCHEDULABLE = 2 };
int rm_test(const double *c, const double *t, size_t n);
/* Task 2: r_out in rate-monotonic order (shortest period first); -1 where the deadline is missed. */
void response_times(const uint32_t *c, const uint32_t *t, size_t n, int32_t *r_out);
/* Task 3: first-fit decreasing by utilization with the response-time test per core; core_of[i] gets task i's core. */
bool partition_ffd(const uint32_t *c, const uint32_t *t, size_t n, int n_cores, int *core_of);
RDL_END
#endif
