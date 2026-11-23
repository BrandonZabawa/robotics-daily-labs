#include "ctest.h"
static int calls = 0;
int32_t read_sensor(void) { calls++; return 42; }
int32_t filter(int32_t x);

int main(void) {
    CHECK_EQ("x = 3: no change, sensor read", filter(3), 0);
    CHECK_EQ("sensor was called once", calls, 1);
    CHECK_EQ("x = 30: last = 15, early return", filter(30), 15);
    CHECK_EQ("early return skips the sensor", calls, 1);
    CHECK_EQ("x = 1: last = 1", filter(1), 1);
    CHECK_EQ("x = 24: last = 12", filter(24), 12);
    CHECK_EQ("x = 0: last = 0, sensor read", filter(0), 0);
    CHECK_EQ("sensor calls total", calls, 3);
    CT_DONE();
}
