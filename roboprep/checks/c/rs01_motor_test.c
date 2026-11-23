#include "ctest.h"
#include "motor.h"

typedef struct { uint16_t last; int calls; uint16_t adc; } F;
static void pwm(void *c, uint16_t d) { ((F *)c)->last = d; ((F *)c)->calls++; }
static uint16_t adc(void *c) { return ((F *)c)->adc; }

int main(void) {
    F f = {7, 0, 0};
    MotorHal h = {pwm, adc, &f};
    Motor m;
    motor_init(&m, &h);
    CHECK_EQ("soft start step", motor_step(&m, 1000), 100);
    for (int i = 0; i < 8; i++) motor_step(&m, 1000);
    CHECK_EQ("reaches 900 after 9 steps", f.last, 900);
    CHECK_EQ("small final step", motor_step(&m, 950), 950);
    CHECK_EQ("ramp down limited", motor_step(&m, 0), 850);
    f.adc = 3001;
    CHECK("over-current faults and zeroes PWM", motor_step(&m, 950) == -1 && f.last == 0);
    f.adc = 0;
    int c = f.calls;
    CHECK("stays faulted without touching PWM", motor_step(&m, 950) == -1 && f.calls == c);
    CT_DONE();
}
