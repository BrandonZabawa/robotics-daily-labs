/* h01.h: C/C++ versions of H01. */
#ifndef RDL_H01_H
#define RDL_H01_H
#include "rdl.h"
RDL_BEGIN
/* Task 1 */
double divider(double v_in, double r_top, double r_bottom);
double ntc_ohms_from_code(uint32_t code, int bits, double r_fixed);
double ntc_temp_c(double r, double r0, double t0_c, double beta);
/* Task 2: least-squares fit of a*sin + b*cos + c at f0, then ENOB from SINAD. */
double enob(const double *samples, size_t n, double fs, double f0);
/* Task 3: sum groups of 4^extra_bits samples, round, shift right by extra_bits; returns the output count. */
size_t oversample(const int32_t *samples, size_t n, int extra_bits, int32_t *out, size_t out_cap);
RDL_END
#endif
