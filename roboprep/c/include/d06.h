/* d06.h: C/C++ versions of D06. Bit arrays hold 0 or 1. */
#ifndef RDL_D06_H
#define RDL_D06_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: 11-bit identifiers; returns the winner; lost_at[i] = arbitration bit index (0 = MSB) where ids[i]
 * lost, or -1 for the winner. */
uint16_t can_arbitrate(const uint16_t *ids, size_t n, int *lost_at);
/* Task 2: return the number of bits written to out. */
size_t can_stuff(const uint8_t *bits, size_t n, uint8_t *out, size_t out_cap);
size_t can_unstuff(const uint8_t *bits, size_t n, uint8_t *out, size_t out_cap);
/* Task 3 */
void can_bit_timing(uint32_t f_clk, uint32_t bitrate, double sample_point, uint32_t *brp, uint32_t *tseg1, uint32_t *tseg2);
uint32_t can_frame_bits_worst(uint32_t n_bytes);
double can_bus_load(const uint32_t *n_bytes, const double *rate_hz, size_t n_messages, uint32_t bitrate);
RDL_END
#endif
