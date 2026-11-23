/* rs06.h: C/C++ version of RS06 Task 1 (hierarchical state machine). Task 2 is a classification quiz. */
#ifndef RDL_RS06_H
#define RDL_RS06_H
#include "rdl.h"
RDL_BEGIN
enum { ST_ROOT = 0, ST_INIT, ST_READY, ST_FAULT, ST_IDLE, ST_OPERATIONAL, ST_MANUAL, ST_AUTO, ST_COUNT };
enum { EV_INIT_DONE = 0, EV_ENABLE, EV_AUTO, EV_MANUAL, EV_DISABLE, EV_FAULT, EV_RESET };
typedef struct {
    int state;
    bool estop_released;
    void (*log)(void *ctx, bool entry, int state);   /* call for every exit (entry = false) and entry action */
    void *ctx;
} Hsm;
/* given: the state tree (ST_ROOT has no parent: -1) */
static inline int hsm_parent(int s) {
    switch (s) {
        case ST_INIT: case ST_READY: case ST_FAULT: return ST_ROOT;
        case ST_IDLE: case ST_OPERATIONAL: return ST_READY;
        case ST_MANUAL: case ST_AUTO: return ST_OPERATIONAL;
        default: return -1;
    }
}
/* given: the handler table. Returns the target state, or -1 if `state` does not handle `event`. */
static inline int hsm_handler(const Hsm *h, int state, int event) {
    if (state == ST_INIT && event == EV_INIT_DONE) return ST_IDLE;
    if (state == ST_IDLE && event == EV_ENABLE) return ST_MANUAL;
    if (state == ST_MANUAL && event == EV_AUTO) return ST_AUTO;
    if (state == ST_AUTO && event == EV_MANUAL) return ST_MANUAL;
    if (state == ST_OPERATIONAL && event == EV_DISABLE) return ST_IDLE;
    if (state == ST_ROOT && event == EV_FAULT) return ST_FAULT;
    if (state == ST_FAULT && event == EV_FAULT) return ST_FAULT;
    if (state == ST_FAULT && event == EV_RESET) return h->estop_released ? ST_IDLE : ST_FAULT;
    return -1;
}
void hsm_transition(Hsm *h, int target);   /* exits up to the least common ancestor, entries down to target */
bool hsm_dispatch(Hsm *h, int event);      /* innermost state first, then its ancestors; true if handled */
RDL_END
#endif
