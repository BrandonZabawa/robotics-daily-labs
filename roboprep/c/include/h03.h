/* h03.h: C/C++ versions of H03. */
#ifndef RDL_H03_H
#define RDL_H03_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: STM32G4 PLL; false if no exact solution. Prefer the smallest M. */
bool pll_config(double f_in, double f_target, int *m, int *n, int *r);
/* Task 2 */
double drift_s_per_day(double ppm);
double spi_max_clock(double t_co, double t_pd, double t_su);
double setup_slack(double period, double t_cq, double t_logic, double t_su, double skew);
double hold_slack(double t_cq, double t_logic_min, double t_hold, double skew);
RDL_END
#endif
