/* rs04.h: C/C++ versions of RS04 (commit log, watchdog supervisor, reset causes). */
#ifndef RDL_RS04_H
#define RDL_RS04_H
#include "rdl.h"
RDL_BEGIN
/* given: CRC-8 (polynomial 0x07, init 0) */
static inline uint8_t crc8(const uint8_t *data, size_t len) {
    uint8_t c = 0;
    for (size_t i = 0; i < len; ++i) {
        c ^= data[i];
        for (int b = 0; b < 8; ++b) c = (c & 0x80) ? (uint8_t)((c << 1) ^ 0x07) : (uint8_t)(c << 1);
    }
    return c;
}
/* Task 1: record = 0xA5, length, payload, crc8(length + payload), then a 0x00 commit byte written last.
 * program returns false when power is lost: stop immediately and return -1. */
typedef struct { bool (*program)(void *ctx, uint32_t addr, const uint8_t *data, size_t len); void *ctx; } LogFlashOps;
int32_t log_append(const LogFlashOps *flash, uint32_t offset, const uint8_t *payload, size_t len);  /* next offset, or -1 */
/* Scan a flash image; committed payloads back to back in out, lengths in lens; returns the record count. */
size_t log_recover(const uint8_t *mem, size_t size, uint8_t *out, size_t out_cap, size_t *lens, size_t max_records, uint32_t *next_offset);

/* Task 2: software watchdog supervisor (task index = position in max_interval). */
#define SUP_MAX_TASKS 8
typedef struct { size_t n; double max_interval[SUP_MAX_TASKS]; double last[SUP_MAX_TASKS]; bool seen[SUP_MAX_TASKS]; } Supervisor;
void sup_init(Supervisor *s, const double *max_interval, size_t n);
void sup_checkin(Supervisor *s, size_t task, double now);
bool sup_kick(const Supervisor *s, double now);

/* Task 3: RCC_CSR reset flags (bit: 31 LPWR, 30 WWDG, 29 IWDG, 28 SFT, 27 BOR, 26 PIN, 25 OBL). */
size_t decode_csr(uint32_t csr, const char **names, size_t cap);   /* names like "IWDG"; returns the count */
enum { BOOT_NORMAL = 0, BOOT_DEGRADED = 1, BOOT_SAFE = 2 };
int boot_mode(const uint32_t *history_csr, size_t n);              /* oldest first */
RDL_END
#endif
