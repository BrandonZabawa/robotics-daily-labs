#include <string.h>
#include <stddef.h>
#include "ctest.h"

typedef struct { uint8_t id; uint16_t current_mA; int32_t position; float temp_c; } Telemetry;
void put_u16_be(uint8_t *p, uint16_t v);
void put_u32_be(uint8_t *p, uint32_t v);
uint32_t get_u32_le(const uint8_t *p);
uint32_t float_bits(float f);
size_t pack_telemetry(uint8_t *out, const Telemetry *t);

int main(void) {
    uint8_t b[16];
    memset(b, 0xAA, sizeof b);
    put_u16_be(b, 0x1234);
    CHECK("put_u16_be", b[0] == 0x12 && b[1] == 0x34 && b[2] == 0xAA);
    put_u32_be(b, 0xCAFEF00Du);
    CHECK("put_u32_be", b[0] == 0xCA && b[1] == 0xFE && b[2] == 0xF0 && b[3] == 0x0D && b[4] == 0xAA);
    const uint8_t le[4] = {0x0D, 0xF0, 0xFE, 0xCA};
    CHECK_EQ("get_u32_le", get_u32_le(le), 0xCAFEF00Du);
    CHECK_EQ("float_bits(1.0f)", float_bits(1.0f), 0x3F800000u);
    Telemetry t = {7, 1500, -2, 25.5f};
    memset(b, 0xAA, sizeof b);
    size_t n = pack_telemetry(b, &t);
    CHECK_EQ("pack length", n, 11);
    const uint8_t exp[11] = {7, 0x05, 0xDC, 0xFF, 0xFF, 0xFF, 0xFE, 0x41, 0xCC, 0x00, 0x00};
    CHECK("pack bytes", memcmp(b, exp, 11) == 0 && b[11] == 0xAA);
    CT_DONE();
}
