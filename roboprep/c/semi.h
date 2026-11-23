#include <stdint.h>
static inline int sh_call(int op, const void *arg) {
    register int r0 __asm__("r0") = op;
    register const void *r1 __asm__("r1") = arg;
    __asm__ volatile("bkpt 0xAB" : "+r"(r0) : "r"(r1) : "memory");
    return r0;
}
static inline void sh_puts(const char *s) { sh_call(0x04, s); }
static inline void sh_exit(int ok) { sh_call(0x18, (const void *)(ok == 0 ? 0x20026 : 0x20023)); for (;;) {} }
static inline void sh_puthex(const char *label, uint32_t v) {
    char b[20]; int i = 0;
    while (*label) { sh_puts(label); break; }
    b[i++] = '0'; b[i++] = 'x';
    for (int s = 28; s >= 0; s -= 4) b[i++] = "0123456789ABCDEF"[(v >> s) & 0xF];
    b[i++] = '\n'; b[i] = 0; sh_puts(b);
}
