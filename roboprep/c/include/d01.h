/* d01.h: C/C++ versions of D01 Tasks 1 and 3 (Task 2 is already C). */
#ifndef RDL_D01_H
#define RDL_D01_H
#include "rdl.h"
RDL_BEGIN
/* Task 1 */
uint16_t crc16_ccitt_false(const uint8_t *data, size_t len);
uint16_t crc16_modbus(const uint8_t *data, size_t len);
/* Task 3: 16x oversampling. Writes the actual baud and the error in percent (actual minus target). */
uint32_t uart_brr(double f_clk, double baud, double *actual, double *error_percent);
RDL_END
#endif
