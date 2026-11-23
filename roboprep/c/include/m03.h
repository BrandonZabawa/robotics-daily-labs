/* m03.h: C/C++ versions of M03. */
#ifndef RDL_M03_H
#define RDL_M03_H
#include "rdl.h"
RDL_BEGIN
/* Task 1 */
double lowpass_alpha(double fc, double dt);
/* Task 2: PID with derivative on measurement (filtered), conditional-integration anti-windup, output clamp. */
typedef struct {
    double kp, ki, kd, dt, u_min, u_max, alpha;
    double integ, d_f, prev_y;
    bool has_prev;
} Pid;
void pid_init(Pid *p, double kp, double ki, double kd, double dt, double u_min, double u_max, double d_cutoff_hz);
double pid_update(Pid *p, double setpoint, double y);
/* Task 3 */
void step_metrics(const double *t, const double *y, size_t n, double final_value, double *rise_time, double *overshoot_percent, double *settling_time);
RDL_END
#endif
