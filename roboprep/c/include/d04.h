/* d04.h: C/C++ versions of D04. */
#ifndef RDL_D04_H
#define RDL_D04_H
#include "rdl.h"
RDL_BEGIN
/* kind: 'S' start, 'R' repeated start, 'P' stop, 'B' byte (with byte and ack filled) */
typedef struct { char kind; uint8_t byte; bool ack; } I2cEvent;
size_t i2c_decode(const uint8_t *scl, const uint8_t *sda, size_t n, I2cEvent *out, size_t out_cap);

enum { I2C_STANDARD = 0, I2C_FAST = 1, I2C_FASTPLUS = 2 };
void pullup_range(double vdd, double cb_pF, int mode, double *r_min_ohm, double *r_max_ohm);

/* Task 3: bus access through function pointers, the way a hardware abstraction layer would provide it. */
typedef struct {
    int (*sda)(void *ctx);         /* read SDA: 0 or 1 */
    void (*pulse_scl)(void *ctx);  /* one clock pulse */
    void (*stop)(void *ctx);       /* generate a STOP */
    void *ctx;
} I2cBusOps;
int i2c_recover(const I2cBusOps *bus);   /* returns the number of SCL pulses sent */
RDL_END
#endif
