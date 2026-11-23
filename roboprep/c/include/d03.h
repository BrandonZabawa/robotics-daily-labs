/* d03.h: C/C++ versions of D03. Arrays of samples hold 0 or 1. */
#ifndef RDL_D03_H
#define RDL_D03_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: decode bytes (MSB first) from sampled SCLK and data lines; return the number of bytes written to out. */
size_t spi_decode(const uint8_t *sclk, const uint8_t *data, size_t n, int cpol, int cpha, uint8_t *out, size_t out_cap);
/* Task 1: idle clock level and whether data is sampled on the rising edge, for SPI mode 0..3. */
void spi_mode(int mode, int *idle_level, bool *sample_rising);
/* Task 2: daisy chain of n devices with 40-bit datagrams (datagram 0 = nearest device). The chain shifts
 * 5*n bytes; out[0] is the first byte shifted out (most significant, farthest device). */
void chain_tx(const uint64_t *datagrams, size_t n, uint8_t *out);
void chain_rx(const uint8_t *in, size_t n, uint64_t *datagrams);
RDL_END
#endif
