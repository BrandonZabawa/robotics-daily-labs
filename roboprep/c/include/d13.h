/* d13.h: C/C++ versions of D13 (VLAN, PTP, RSTP, EtherCAT). */
#ifndef RDL_D13_H
#define RDL_D13_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: false if untagged. */
bool parse_vlan(const uint8_t *frame, size_t len, uint16_t *vid, uint8_t *pcp, uint8_t *dei, uint16_t *ethertype);
/* Task 2 */
void ptp(double t1, double t2, double t3, double t4, double *offset, double *delay);
void simulate_exchange(double true_offset, double d_forward, double d_reverse, double t1, double t3_after_t2, double *t4_out);
/* Task 3: mac strings like "00:1b:21:0a:00:09"; return the index of the root bridge. */
size_t root_bridge(const uint16_t *priority, const char **mac, size_t n);
int expected_wkc_lrw(const bool *has_inputs, const bool *has_outputs, size_t n);
RDL_END
#endif
