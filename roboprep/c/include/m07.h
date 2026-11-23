/* m07.h: C/C++ versions of M07 (field-oriented control). */
#ifndef RDL_M07_H
#define RDL_M07_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: amplitude-invariant transforms */
void clarke(double ia, double ib, double ic, double *alpha, double *beta);
void park(double alpha, double beta, double theta, double *d, double *q);
void inv_park(double d, double q, double theta, double *alpha, double *beta);
/* Task 2: min-max zero-sequence injection; duty[3] in [0, 1] */
void svm(double v_alpha, double v_beta, double vdc, double *duty);
/* Task 3: d and q PI current loops with decoupling and voltage-vector limiting (anti-windup by not integrating). */
typedef struct { double kp, ki, L, lam, dt, v_max, id_int, iq_int; } FocCurrentController;
void foc_init(FocCurrentController *c, double kp, double ki, double L, double lam, double dt, double v_max);
void foc_update(FocCurrentController *c, double id_ref, double iq_ref, double i_d, double i_q, double w_e, double *vd, double *vq);
RDL_END
#endif
