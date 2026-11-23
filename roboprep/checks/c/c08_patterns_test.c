#include <stdbool.h>
#include <stddef.h>
#include "ctest.h"

uint32_t elapsed(uint32_t now, uint32_t start);
bool time_after(uint32_t a, uint32_t b);
typedef struct { bool out; uint8_t count; uint8_t need; } Debounce;
bool debounce_update(Debounce *d, bool raw);
typedef struct { void *free; size_t block; } Pool;
void pool_init(Pool *p, void *buf, size_t block, size_t count);
void *pool_alloc(Pool *p);
void pool_free(Pool *p, void *blk);
void stack_paint(uint32_t *stack, size_t words);
size_t stack_high_water(const uint32_t *stack, size_t words);

int main(void) {
    CHECK_EQ("elapsed across wrap", elapsed(0x00000005u, 0xFFFFFFFBu), 10);
    CHECK("time_after across wrap", time_after(0x00000010u, 0xFFFFFFF0u));
    CHECK("time_after false when earlier", !time_after(0xFFFFFFF0u, 0x00000010u));
    CHECK("time_after equal is false", !time_after(1000u, 1000u));

    Debounce d = {false, 0, 4};
    const bool bouncy[] = {1, 0, 1, 1, 0, 1, 1, 1, 1, 1};
    int changed_at = -1;
    for (int i = 0; i < 10; i++)
        if (debounce_update(&d, bouncy[i]) && changed_at < 0) changed_at = i;
    CHECK_EQ("debounce ignores bounce, changes on 4th steady sample", changed_at, 8);
    for (int i = 0; i < 3; i++) debounce_update(&d, 0);
    CHECK("debounce holds through 3 low samples", d.out == true);

    static _Alignas(8) unsigned char buf[4 * 32];
    Pool p;
    pool_init(&p, buf, 32, 4);
    void *a = pool_alloc(&p), *b = pool_alloc(&p), *c = pool_alloc(&p), *e = pool_alloc(&p);
    CHECK("pool hands out 4 distinct blocks inside the buffer",
          a && b && c && e && a != b && b != c && c != e &&
          (unsigned char *)a >= buf && (unsigned char *)e < buf + sizeof buf);
    CHECK("pool exhausted returns NULL", pool_alloc(&p) == NULL);
    pool_free(&p, b);
    CHECK("freed block is reused", pool_alloc(&p) == b);
    CHECK("blocks are block-aligned offsets", (((unsigned char *)a - buf) % 32) == 0);

    uint32_t stack[64];
    stack_paint(stack, 64);
    for (int i = 40; i < 64; i++) stack[i] = (uint32_t)i;   /* top 24 words used */
    CHECK_EQ("high-water mark", stack_high_water(stack, 64), 24);
    stack[0] = 1;
    CHECK_EQ("full overflow", stack_high_water(stack, 64), 64);
    CT_DONE();
}
