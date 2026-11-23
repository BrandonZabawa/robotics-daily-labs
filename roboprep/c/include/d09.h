/* d09.h: C/C++ versions of D09 (CANopen). */
#ifndef RDL_D09_H
#define RDL_D09_H
#include "rdl.h"
RDL_BEGIN
/* Task 1: expedited SDO write of `size` bytes (1..4); fills data[8]; returns the COB-ID. */
uint16_t sdo_download(uint8_t node, uint16_t index, uint8_t sub, int32_t value, int size, uint8_t *data);
/* Task 1: returns 0 and fills index/sub/value, or -1 for an abort frame (abort_code filled). */
int sdo_upload_parse(const uint8_t *data, uint16_t *index, uint8_t *sub, uint32_t *value, uint32_t *abort_code);

/* Task 2 */
enum { CIA402_NOT_READY = 0, CIA402_SWITCH_ON_DISABLED, CIA402_READY_TO_SWITCH_ON, CIA402_SWITCHED_ON,
       CIA402_OPERATION_ENABLED, CIA402_QUICK_STOP_ACTIVE, CIA402_FAULT_REACTION_ACTIVE, CIA402_FAULT, CIA402_UNKNOWN };
int cia402_state(uint16_t statusword);
typedef struct {
    uint16_t (*statusword)(void *ctx);
    void (*write_controlword)(void *ctx, uint16_t cw);
    void *ctx;
} Cia402DriveOps;
bool enable_drive(const Cia402DriveOps *drive, int max_steps);

/* Task 3: values[i] belongs to map[i]; little-endian; returns the number of bytes written. */
typedef struct { uint16_t index; uint8_t sub; uint8_t bits; } PdoEntry;
size_t pack_pdo(const PdoEntry *map, const int64_t *values, size_t n, uint8_t *out);
RDL_END
#endif
