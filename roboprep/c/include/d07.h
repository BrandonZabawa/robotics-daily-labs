/* d07.h: C/C++ versions of D07. */
#ifndef RDL_D07_H
#define RDL_D07_H
#include "rdl.h"
RDL_BEGIN
/* Task 1 */
void can_filter_mask_for(const uint16_t *ids, size_t n, uint16_t *filt, uint16_t *mask);
size_t can_accepted(uint16_t filt, uint16_t mask, uint16_t *out, size_t out_cap);   /* ascending ids 0..0x7FF */
/* Task 2: fault confinement */
enum { CAN_ERROR_ACTIVE = 0, CAN_ERROR_PASSIVE = 1, CAN_BUS_OFF = 2 };
typedef struct { int tec; int rec; int recov; } CanErrorCounters;
void cec_init(CanErrorCounters *c);
int cec_state(const CanErrorCounters *c);
void cec_tx_error(CanErrorCounters *c);
void cec_tx_ok(CanErrorCounters *c);
void cec_rx_error(CanErrorCounters *c);
void cec_rx_ok(CanErrorCounters *c);
void cec_recessive_11(CanErrorCounters *c);   /* one run of 11 recessive bits seen while bus-off */
RDL_END
#endif
