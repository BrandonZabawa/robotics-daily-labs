/* h02.h: C/C++ versions of H02. */
#ifndef RDL_H02_H
#define RDL_H02_H
#include "rdl.h"
RDL_BEGIN
/* Task 1 */
double half_deadline_s(double fs, size_t n);
int half_to_process(size_t dma_index, size_t n);
/* Task 2: phases i of current_mA[i] for duration_s[i], sleeping the rest of the period. */
double average_current_mA(const double *current_mA, const double *duration_s, size_t n_phases, double sleep_mA, double period_s);
double battery_life_hours(double capacity_mAh, double avg_mA, double derating);
/* Task 3 */
double alias(double f, double fs);
RDL_END
#endif
