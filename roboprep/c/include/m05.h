/* m05.h: C/C++ versions of M05. */
#ifndef RDL_M05_H
#define RDL_M05_H
#include "rdl.h"
RDL_BEGIN
/* Task 1 */
void trapezoid(double d, double v_max, double a_max, double *t_acc, double *t_const, double *t_total, double *v_peak);
double trap_position(double t, double d, double v_max, double a_max);
/* Task 2: Austin's stepper ramp; writes n timer counts. */
void austin_delays(size_t n, double f_timer, double alpha, double accel, double *counts);
/* Task 3: dx, dy >= 0; writes max(dx, dy) step pairs (0 or 1 each); returns that count. */
size_t dda(uint32_t dx, uint32_t dy, uint8_t *step_x, uint8_t *step_y, size_t cap);
RDL_END
#endif
