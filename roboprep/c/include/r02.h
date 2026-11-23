/* r02.h: C/C++ versions of R02. */
#ifndef RDL_R02_H
#define RDL_R02_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: waiting_for = index of the mutex the task's current operation tries to lock, or -1.
 * mutex_owner[m] = index of the task holding mutex m, or -1. With inheritance, a task runs at the highest
 * priority of every task waiting (directly or through a chain) on a mutex it holds. */
typedef struct { int prio; int waiting_for; } RtTask;
int effective_priority(const RtTask *tasks, size_t n, size_t task, const int *mutex_owner, bool inheritance);
/* Task 2: waits_for[i] = index of the task i waits for, or -1. Writes the members of one cycle, returns its
 * length (0 if there is no cycle). */
size_t find_cycle(const int *waits_for, size_t n, int *cycle_out);
RDL_END
#endif
