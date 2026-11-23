#include <stddef.h>
#include <string.h>
#include "ctest.h"
#include "gpio.h"

int main(void) {
    CHECK_EQ("offset MODER", offsetof(GPIO_TypeDef, MODER), 0x00);
    CHECK_EQ("offset IDR", offsetof(GPIO_TypeDef, IDR), 0x10);
    CHECK_EQ("offset ODR", offsetof(GPIO_TypeDef, ODR), 0x14);
    CHECK_EQ("offset BSRR", offsetof(GPIO_TypeDef, BSRR), 0x18);
    CHECK_EQ("offset AFR", offsetof(GPIO_TypeDef, AFR), 0x20);
    CHECK_EQ("offset BRR", offsetof(GPIO_TypeDef, BRR), 0x28);

    CHECK_EQ("field_read nibble", field_read(0xABCD1234u, 8, 4), 0x2);
    CHECK_EQ("field_read width 32", field_read(0xDEADBEEFu, 0, 32), 0xDEADBEEFu);
    CHECK_EQ("field_write middle", field_write(0xFFFFFFFFu, 4, 4, 0x5), 0xFFFFFF5Fu);
    CHECK_EQ("field_write masks val", field_write(0, 0, 2, 0x7), 0x3);
    CHECK_EQ("field_write width 32", field_write(0x12345678u, 0, 32, 0xCAFEF00Du), 0xCAFEF00Du);
    CHECK_EQ("field_write top bits", field_write(0, 30, 2, 0x2), 0x80000000u);

    GPIO_TypeDef g;
    memset(&g, 0, sizeof g);
    g.MODER = 0xABFFFFFFu;
    g.ODR = 0x00F0u;
    gpio_set_mode(&g, 5, 1);
    CHECK_EQ("gpio_set_mode PA5 output", g.MODER, 0xABFFF7FFu);
    gpio_set_mode(&g, 15, 0);
    CHECK_EQ("gpio_set_mode pin 15 input", g.MODER, 0x2BFFF7FFu);
    gpio_write(&g, 3, 1);
    CHECK_EQ("gpio_write set uses BSRR low half", g.BSRR, 1u << 3);
    gpio_write(&g, 9, 0);
    CHECK_EQ("gpio_write reset uses BSRR high half", g.BSRR, 1u << 25);
    CHECK_EQ("gpio_write leaves ODR alone", g.ODR, 0x00F0u);
    CT_DONE();
}
