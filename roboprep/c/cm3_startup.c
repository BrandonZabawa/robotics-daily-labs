/* Reference Cortex-M3 startup (the C05 answer), reused by later bare-metal labs. */
#include <stdint.h>
extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss, _estack;
int main(void);
void Reset_Handler(void) {
    uint32_t *src = &_sidata, *dst = &_sdata;
    while (dst < &_edata) *dst++ = *src++;
    for (dst = &_sbss; dst < &_ebss;) *dst++ = 0;
    main();
    for (;;) {}
}
void Default_Handler(void) { for (;;) {} }
void HardFault_Handler(void) __attribute__((weak, alias("Default_Handler")));
typedef void (*vec_t)(void);
__attribute__((section(".isr_vector"), used))
const vec_t vector_table[16] = { (vec_t)(uintptr_t)&_estack, Reset_Handler, Default_Handler, HardFault_Handler,
  Default_Handler, Default_Handler, Default_Handler, 0, 0, 0, 0, Default_Handler, Default_Handler, 0, Default_Handler, Default_Handler };
