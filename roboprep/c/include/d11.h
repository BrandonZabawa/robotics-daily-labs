/* d11.h: C/C++ versions of D11 (Modbus RTU). */
#ifndef RDL_D11_H
#define RDL_D11_H
#include "rdl.h"
RDL_BEGIN
/* given (from D01): CRC-16/MODBUS */
static inline uint16_t mb_crc16(const uint8_t *data, size_t len) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (int b = 0; b < 8; ++b) crc = (crc & 1) ? (uint16_t)((crc >> 1) ^ 0xA001) : (uint16_t)(crc >> 1);
    }
    return crc;
}
/* Task 1: returns the frame length (8). */
size_t mb_read_holding_request(uint8_t slave, uint16_t start, uint16_t count, uint8_t *out);
/* Task 1: returns the number of registers, MB_ERR_FRAME for a bad CRC, length or slave address,
 * or MB_ERR_EXCEPTION with *exception_code filled for an exception response. */
enum { MB_ERR_FRAME = -1, MB_ERR_EXCEPTION = -2 };
int mb_parse_read_response(const uint8_t *frame, size_t len, uint8_t slave, uint16_t *regs, size_t regs_cap, uint8_t *exception_code);
/* Task 2: returns the response length, or 0 to stay silent. regs is the slave's register table. */
typedef struct { uint16_t addr; uint16_t value; } MbRegister;
size_t mb_slave_handle(const uint8_t *frame, size_t len, uint8_t my_addr, MbRegister *regs, size_t n_regs, uint8_t *resp, size_t resp_cap);
/* Task 3 */
double mb_poll_time(double baud, int req_bytes, int resp_bytes, double turnaround_s, int bits_per_char);
double mb_max_poll_rate_per_node(int n_nodes, double baud, int req_bytes, int resp_bytes, double turnaround_s);
RDL_END
#endif
