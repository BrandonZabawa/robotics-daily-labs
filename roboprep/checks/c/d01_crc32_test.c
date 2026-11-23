#include <string.h>
#include <stddef.h>
#include "ctest.h"
uint32_t crc32_update(uint32_t crc, const uint8_t *p, size_t n);
uint32_t crc32_final(uint32_t crc);

int main(void) {
    const uint8_t *m = (const uint8_t *)"123456789";
    CHECK_EQ("check value 0xCBF43926", crc32_final(crc32_update(0xFFFFFFFFu, m, 9)), 0xCBF43926u);
    uint32_t c = crc32_update(0xFFFFFFFFu, m, 4);
    c = crc32_update(c, m + 4, 5);
    CHECK_EQ("streaming in two chunks", crc32_final(c), 0xCBF43926u);
    CHECK_EQ("empty message", crc32_final(crc32_update(0xFFFFFFFFu, m, 0)), 0x00000000u);
    const uint8_t q[] = "The quick brown fox jumps over the lazy dog";
    CHECK_EQ("pangram", crc32_final(crc32_update(0xFFFFFFFFu, q, 43)), 0x414FA339u);
    CT_DONE();
}
