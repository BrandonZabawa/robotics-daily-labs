#include "ctest.h"
int16_t q15_mul(int16_t a, int16_t b);
int16_t q15_from_float(float x);

int main(void) {
    CHECK_EQ("0.5 * 0.5", q15_mul(16384, 16384), 8192);
    CHECK_EQ("0.5 * -0.25", q15_mul(16384, -8192), -4096);
    CHECK_EQ("-1 * -1 saturates", q15_mul(-32768, -32768), 32767);
    CHECK_EQ("-1 * 0.5", q15_mul(-32768, 16384), -16384);
    CHECK_EQ("rounds to nearest", q15_mul(3, 16384), 2);       /* 1.5 -> 2 */
    CHECK_EQ("rounds negative", q15_mul(-3, 16384), -1);       /* -1.5 -> -1 (round half up) */
    CHECK_EQ("from_float 0.5", q15_from_float(0.5f), 16384);
    CHECK_EQ("from_float 1.0 saturates", q15_from_float(1.0f), 32767);
    CHECK_EQ("from_float -1.0", q15_from_float(-1.0f), -32768);
    CHECK_EQ("from_float -0.25", q15_from_float(-0.25f), -8192);
    CT_DONE();
}
