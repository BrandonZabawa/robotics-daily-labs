/* ros08.h: C/C++ version of ROS08 Task 1: the shape of a ros2_control controller and of the controller
 * manager's loop, without ROS. In C++ this is where you would write a controller_interface::ControllerInterface. */
#ifndef RDL_ROS08_H
#define RDL_ROS08_H
#include "rdl.h"
RDL_BEGIN
#define RLP_MAX_JOINTS 8
typedef struct { size_t n; double max_vel; double target[RLP_MAX_JOINTS]; } RateLimitedPosition;
void rlp_init(RateLimitedPosition *c, size_t n_joints, double max_vel);
/* move each command toward its target by at most max_vel * dt */
void rlp_update(RateLimitedPosition *c, const double *state, double *command, double dt);
/* the controller manager loop: read hardware, update the controller, write hardware, rate_hz * seconds times */
typedef struct {
    void (*read)(void *ctx);
    void (*update)(void *ctx, double dt);
    void (*write)(void *ctx);
    void *ctx;
} LoopOps;
void run_loop(const LoopOps *ops, double rate_hz, double seconds);
RDL_END
#endif
