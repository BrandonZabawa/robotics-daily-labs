/* r09.h: C/C++ versions of R09. */
#ifndef RDL_R09_H
#define RDL_R09_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: operating performance point: frequency (Hz), voltage (V), static power (W) */
typedef struct { double f; double v; double p_static; } Opp;
double job_energy(const Opp *opp, double cycles, double window, double c_eff, double p_idle);
int best_opp(const Opp *opps, size_t n, double cycles, double window, double c_eff, double p_idle);   /* index or -1 */
/* Task 2: index of the chosen idle state (fallback: states[0]) */
typedef struct { const char *name; double exit_us; double residency_us; double power_mw; } IdleState;
size_t pick_idle(const IdleState *states, size_t n, double predicted_idle_us, double latency_limit_us);
RDL_END
#endif
