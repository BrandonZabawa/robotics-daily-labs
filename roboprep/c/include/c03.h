/* c03.h: C/C++ version of C03 Task 2. */
#ifndef RDL_C03_H
#define RDL_C03_H
#include "rdl.h"
RDL_BEGIN
/* PSC and ARR in 0..65535 hitting f_target with the smallest frequency error; on a tie, the smallest PSC. */
void timer_config(double f_clk, double f_target, uint16_t *psc, uint16_t *arr);
RDL_END
#endif
