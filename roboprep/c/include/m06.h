/* m06.h: C/C++ versions of M06. */
#ifndef RDL_M06_H
#define RDL_M06_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: axis supervisor. Faults latch until axis_reset. */
enum { FAULT_NONE = 0, FAULT_COLLISION = 1, FAULT_FOLLOWING_ERROR = 2 };
typedef struct {
    double ferr_max, i_limit;
    int i_cycles;
    double v_max, dt;
    int fault;
    double cmd;
    int over;
} AxisSupervisor;
void axis_init(AxisSupervisor *s, double ferr_max, double i_limit, int i_cycles, double v_max, double dt);
bool axis_update(AxisSupervisor *s, double target, double actual, double current, bool deadman, double *command);  /* returns enable */
void axis_reset(AxisSupervisor *s, double actual);

/* Task 2: homing state machine */
enum { HOME_SEEK = 0, HOME_BACKOFF, HOME_APPROACH, HOME_DONE, HOME_FAILED };
typedef struct { double v_fast, v_slow, timeout, dt; int state; double t; double zero; } Homing;
void homing_init(Homing *h, double v_fast, double v_slow, double timeout_s, double dt);
double homing_step(Homing *h, bool switch_active, double position);   /* returns the velocity command */
RDL_END
#endif
