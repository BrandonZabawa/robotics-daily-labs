/* m04.h: C/C++ versions of M04. */
#ifndef RDL_M04_H
#define RDL_M04_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: two-point (28.3 % and 63.2 %) first-order-plus-dead-time fit of a step response of size du. */
void fit_fopdt(const double *t, const double *y, size_t n, double du, double *K, double *tau, double *theta);
/* Task 2: SIMC PI tuning; pass tau_c <= 0 to use tau_c = theta. */
void simc_pi(double K, double tau, double theta, double tau_c, double *kc, double *ti);
/* Task 3: position P loop feeding a velocity PI loop (anti-windup), velocity and current limits. */
typedef struct { double kp_pos, kp_vel, ki_vel, v_max, i_max, dt, integ; } Cascade;
void cascade_init(Cascade *c, double kp_pos, double kp_vel, double ki_vel, double v_max, double i_max, double dt);
double cascade_update(Cascade *c, double pos_sp, double pos, double vel);   /* returns the current command */
RDL_END
#endif
