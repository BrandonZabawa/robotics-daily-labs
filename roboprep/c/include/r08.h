/* r08.h: C/C++ version of R08 Task 2 (Task 1 is already C).
 * Shared memory layout (little-endian): bytes 0..3 head (u32, producer writes), bytes 4..7 tail (u32, consumer
 * writes), then RING_N slots of RING_SLOT bytes: slot[0] = length, slot[1..] = payload. Indices run freely and
 * wrap modulo 2^32; slot index = counter % RING_N. Use acquire loads and release stores on head and tail. */
#ifndef RDL_R08_H
#define RDL_R08_H
#include "rdl.h"
RDL_BEGIN
#define RING_N 16
#define RING_SLOT 64
/* blocks while full; after publishing, writes 1 to the eventfd `doorbell` */
void ring_send(uint8_t *shm, int doorbell, const uint8_t *data, size_t len);
/* copies every available message: payloads back to back in out, lengths in lens; returns the message count */
size_t ring_recv_all(uint8_t *shm, uint8_t *out, size_t out_cap, size_t *lens, size_t max_msgs);
RDL_END
#endif
