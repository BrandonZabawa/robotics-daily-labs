/* m01.h: C/C++ versions of M01. */
#ifndef RDL_M01_H
#define RDL_M01_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: center-aligned counter 0..arr..1 repeated `periods` times; reference high while count < ccr;
 * each output turns on only after `dead` counts. Writes 2*arr*periods samples (0/1); returns that length. */
size_t complementary_pwm(uint32_t arr, uint32_t ccr, uint32_t dead, int periods, uint8_t *hi, uint8_t *lo, size_t cap);
/* Task 2: counter wraps after arr (arr + 1 counts per wrap) */
void capture_measure(uint32_t rise1, uint32_t fall, uint32_t rise2, uint32_t arr, double f_tim, double *freq_hz, double *duty);
RDL_END
#endif
