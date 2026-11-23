/* d12.h: C/C++ versions of D12 (SocketCAN, candump logs, IIO). */
#ifndef RDL_D12_H
#define RDL_D12_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: one line per frame, "(1700000000.010500) can0 701#05"; returns the number of frames parsed. */
typedef struct { double ts; char channel[16]; uint32_t can_id; uint8_t len; uint8_t data[64]; } CandumpFrame;
size_t parse_candump(const char *text, CandumpFrame *out, size_t out_cap);
/* Task 1: decode every 0x123 MotorStatus frame using the lab's DBC layout, the way code generated from a DBC
 * (for example by `cantools generate_c_source`) would. Returns the number of frames decoded. */
typedef struct { double speed; double current; double temperature; int fault; } MotorStatus;
size_t decode_motor(const CandumpFrame *frames, size_t n, MotorStatus *out, size_t out_cap);

/* Task 2: the 16 bytes of a Linux struct can_frame (you may include <linux/can.h> and use it). */
void pack_can_frame(uint32_t can_id, const uint8_t *data, size_t len, bool extended, bool rtr, uint8_t *out16);
typedef struct { uint32_t can_id; uint32_t can_mask; } CanFilter;   /* same layout as struct can_filter */
bool filter_pass(uint32_t rx_can_id, const CanFilter *filters, size_t n);

/* Task 3: read every in_<kind><index>_raw channel of an IIO device directory. */
typedef struct { char name[32]; double value; } IioChannel;   /* name like "voltage0" or "temp" */
size_t read_iio(const char *dev_dir, IioChannel *out, size_t out_cap);
RDL_END
#endif
