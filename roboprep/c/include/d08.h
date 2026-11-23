/* d08.h: C/C++ versions of D08. */
#ifndef RDL_D08_H
#define RDL_D08_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: smallest DLC holding n_bytes; writes the padded length; returns -1 above 64 bytes. */
int can_fd_dlc_for(size_t n_bytes, size_t *padded_length);

/* Task 2: CANopen heartbeat consumer (no dynamic memory: fixed table). */
#define HB_MAX_NODES 16
enum { HB_UNKNOWN = 0, HB_OK = 1, HB_LOST = 2 };
typedef struct {
    uint8_t nodes[HB_MAX_NODES];
    size_t n_nodes;
    double timeout_s;
    double last_t[HB_MAX_NODES];
    int last_state[HB_MAX_NODES];   /* NMT state byte, or -1 if never heard */
} HeartbeatMonitor;
void hb_init(HeartbeatMonitor *m, const uint8_t *nodes, size_t n_nodes, double timeout_s);
void hb_on_frame(HeartbeatMonitor *m, uint32_t can_id, const uint8_t *data, size_t len, double t);
/* returns HB_UNKNOWN, HB_OK or HB_LOST; *nmt_state receives the last state byte or -1 */
int hb_status(const HeartbeatMonitor *m, uint8_t node, double t, int *nmt_state);

/* Task 3 */
enum { PROTO_CYPHAL = 0, PROTO_DRONECAN = 1 };
void tail_bytes(size_t n_frames, uint8_t transfer_id, int protocol, uint8_t *out);
RDL_END
#endif
