/* rs03.h: C/C++ versions of RS03 (bootloader and A/B update). */
#ifndef RDL_RS03_H
#define RDL_RS03_H
#include "rdl.h"
RDL_BEGIN
#define SECTOR 4096
/* given (Python uses zlib.crc32): CRC-32/ISO-HDLC */
static inline uint32_t crc32_ieee(const uint8_t *data, size_t len) {
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (int b = 0; b < 8; ++b) crc = (crc & 1) ? (crc >> 1) ^ 0xEDB88320u : crc >> 1;
    }
    return ~crc;
}
/* Task 1: header "RDL1", u32 version, u32 length, u32 crc32 (little-endian), then the payload. */
bool validate_image(const uint8_t *slot, size_t slot_len, uint32_t max_len, uint32_t *version);

/* Task 2: flash access. program/erase return false on a flash error (for example programming a 0 bit to 1). */
typedef struct {
    bool (*erase)(void *ctx, uint32_t sector);
    bool (*program)(void *ctx, uint32_t addr, const uint8_t *data, size_t len);
    void (*read)(void *ctx, uint32_t addr, uint8_t *out, size_t len);
    void *ctx;
} FlashOps;
bool write_image(const FlashOps *flash, uint32_t slot_addr, const uint8_t *image, size_t len, uint32_t max_len);

/* Task 3: slots 0 = A, 1 = B; pending = -1 when no trial is pending. Returns the slot to boot or -1. */
typedef struct { int active; int pending; int tries; } BootMeta;
int choose_slot(BootMeta *meta, const bool *valid, int max_tries);
RDL_END
#endif
