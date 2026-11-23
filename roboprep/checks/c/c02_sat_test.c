#include "ctest.h"
int16_t sat_add_i16(int16_t a, int16_t b);
uint8_t sat_add_u8(uint8_t a, uint8_t b);
int32_t sat_add_i32(int32_t a, int32_t b);

int main(void) {
    CHECK_EQ("i16 normal", sat_add_i16(100, -50), 50);
    CHECK_EQ("i16 high clamp", sat_add_i16(30000, 10000), 32767);
    CHECK_EQ("i16 low clamp", sat_add_i16(-30000, -10000), -32768);
    CHECK_EQ("u8 normal", sat_add_u8(100, 55), 155);
    CHECK_EQ("u8 clamp", sat_add_u8(200, 100), 255);
    CHECK_EQ("i32 normal", sat_add_i32(-5, 7), 2);
    CHECK_EQ("i32 high clamp", sat_add_i32(INT32_MAX - 1, 5), INT32_MAX);
    CHECK_EQ("i32 low clamp", sat_add_i32(INT32_MIN + 1, -5), INT32_MIN);
    CHECK_EQ("i32 max plus max", sat_add_i32(INT32_MAX, INT32_MAX), INT32_MAX);
    CHECK_EQ("i32 min plus max", sat_add_i32(INT32_MIN, INT32_MAX), -1);
    CT_DONE();
}
