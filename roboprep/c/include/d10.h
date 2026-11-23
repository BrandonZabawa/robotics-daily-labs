/* d10.h: C/C++ versions of D10 (J1939, ISO-TP, UDS). */
#ifndef RDL_D10_H
#define RDL_D10_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: da = -1 for PDU2 (broadcast) */
typedef struct { uint8_t priority; uint32_t pgn; uint8_t sa; int da; } J1939Id;
void parse_j1939(uint32_t can_id, J1939Id *out);
uint64_t claim_winner(const uint64_t *names, size_t n);

/* Task 2: frames are stored back to back, 8 bytes each. */
size_t isotp_segment(const uint8_t *payload, size_t n, uint8_t *frames, size_t max_frames);  /* returns frame count */
int isotp_reassemble(const uint8_t *frames, size_t n_frames, uint8_t *out, size_t out_cap);   /* length, or -1 on a sequence error */

/* Task 3: UDS server with a fixed data-identifier table. uds_init loads 0xF190 = "BZ-STORM-0000001"
 * and 0xF187 = "STM32G474" and the default session 0x01. */
#define UDS_MAX_DIDS 8
#define UDS_MAX_DATA 32
typedef struct { uint16_t did; uint8_t len; uint8_t data[UDS_MAX_DATA]; } UdsDid;
typedef struct { uint8_t session; size_t n_dids; UdsDid dids[UDS_MAX_DIDS]; } UdsServer;
void uds_init(UdsServer *s);
size_t uds_handle(UdsServer *s, const uint8_t *req, size_t len, uint8_t *resp, size_t resp_cap);  /* response length */
RDL_END
#endif
