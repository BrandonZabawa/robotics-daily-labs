#include <stdlib.h>
#include <string.h>
#include "ctest.h"
#include "proto.h"

static int enc_eq(const uint8_t *in, size_t n, const uint8_t *exp, size_t m) {
    uint8_t out[600];
    size_t k = cobs_encode(in, n, out);
    return k == m && memcmp(out, exp, m) == 0;
}

static int roundtrip(const uint8_t *in, size_t n) {
    uint8_t enc[600], dec[600];
    size_t k = cobs_encode(in, n, enc);
    if (k == 0 || k > n + 1 + n / 254) return 0;
    for (size_t i = 0; i < k; i++) if (enc[i] == 0) return 0;
    size_t m = cobs_decode(enc, k, dec);
    return m == n && memcmp(dec, in, n) == 0;
}

static void test_cobs(void) {
    CHECK("00", enc_eq((uint8_t[]){0x00}, 1, (uint8_t[]){1, 1}, 2));
    CHECK("00 00", enc_eq((uint8_t[]){0, 0}, 2, (uint8_t[]){1, 1, 1}, 3));
    CHECK("00 11 00", enc_eq((uint8_t[]){0, 0x11, 0}, 3, (uint8_t[]){1, 2, 0x11, 1}, 4));
    CHECK("11 22 00 33", enc_eq((uint8_t[]){0x11, 0x22, 0, 0x33}, 4, (uint8_t[]){3, 0x11, 0x22, 2, 0x33}, 5));
    CHECK("11 22 33 44", enc_eq((uint8_t[]){0x11, 0x22, 0x33, 0x44}, 4, (uint8_t[]){5, 0x11, 0x22, 0x33, 0x44}, 5));
    CHECK("11 00 00 00", enc_eq((uint8_t[]){0x11, 0, 0, 0}, 4, (uint8_t[]){2, 0x11, 1, 1, 1}, 5));
    uint8_t big[300];
    for (int i = 0; i < 300; i++) big[i] = (uint8_t)(i % 255 + 1);
    CHECK("254 non-zero bytes round trip", roundtrip(big, 254));
    CHECK("300 non-zero bytes round trip", roundtrip(big, 300));
    srand(7);
    int ok = 1;
    for (int t = 0; t < 200; t++) {
        size_t n = (size_t)(rand() % 120);
        for (size_t i = 0; i < n; i++) big[i] = (uint8_t)(rand() % 4 == 0 ? 0 : rand());
        ok &= roundtrip(big, n);
    }
    CHECK("200 random messages round trip", ok);
    CHECK("decode rejects embedded zero", cobs_decode((uint8_t[]){3, 0x11, 0x00}, 3, big) == 0);
}

static size_t make_frame(const uint8_t *pl, size_t n, uint8_t *wire) {
    uint8_t tmp[300];
    memcpy(tmp, pl, n);
    uint16_t c = crc16_ccitt(pl, n);
    tmp[n] = (uint8_t)(c >> 8);
    tmp[n + 1] = (uint8_t)c;
    size_t k = cobs_encode(tmp, n + 2, wire);
    wire[k] = 0;
    return k + 1;
}

static size_t feed(Parser *p, const uint8_t *w, size_t n, uint8_t *out, int *frames) {
    size_t last = 0;
    for (size_t i = 0; i < n; i++) { size_t r = parser_feed(p, w[i], out); if (r) { last = r; (*frames)++; } }
    return last;
}

static void test_parser(void) {
    Parser p; memset(&p, 0, sizeof p);
    uint8_t w[400], out[80]; int frames = 0;
    const uint8_t a[] = {0x01, 0x05, 0xE8, 0x03, 0x00, 0x00};
    size_t n = make_frame(a, sizeof a, w);
    size_t got = feed(&p, w, n, out, &frames);
    CHECK("one valid frame", frames == 1 && got == sizeof a && memcmp(out, a, sizeof a) == 0);
    const uint8_t junk[] = {0x55, 0x13, 0x77, 0x00};   /* line noise, then the sender's leading 0x00 */
    frames = 0; feed(&p, junk, 4, out, &frames); got = feed(&p, w, n, out, &frames);
    CHECK("garbage flushed by a delimiter, next frame accepted", frames == 1 && got == sizeof a);
    uint8_t bad[400]; memcpy(bad, w, n); bad[2] ^= 0x01;
    frames = 0; feed(&p, bad, n, out, &frames);
    CHECK("bad CRC rejected", frames == 0);
    frames = 0; feed(&p, w, n, out, &frames);
    CHECK("next frame after a bad one accepted", frames == 1);
    uint8_t longp[200]; memset(longp, 0x42, sizeof longp);
    size_t ln = make_frame(longp, 120, bad);
    frames = 0; feed(&p, bad, ln, out, &frames); feed(&p, w, n, out, &frames);
    CHECK("oversized frame dropped, then resync", frames == 1);
}

static void test_dispatch(void) {
    Device d; memset(&d, 0, sizeof d);
    const uint8_t set[] = {0x01, 1, 0xE8, 0x03, 0, 0};          /* SET_POS 1000 */
    CHECK_EQ("SET_POS ok", handle_payload(&d, set, sizeof set), RESP_OK);
    CHECK_EQ("position 1000", d.position, 1000);
    const uint8_t mv[] = {0x02, 2, 0x0A, 0, 0, 0};               /* MOVE_BY 10 */
    handle_payload(&d, mv, sizeof mv);
    CHECK_EQ("duplicate MOVE_BY detected", handle_payload(&d, mv, sizeof mv), RESP_DUP);
    CHECK_EQ("moved only once", d.position, 1010);
    CHECK_EQ("unknown command", handle_payload(&d, (uint8_t[]){0x7F, 3}, 2), RESP_UNKNOWN);
    CHECK_EQ("wrong length", handle_payload(&d, (uint8_t[]){0x01, 4, 1, 2}, 4), RESP_BADLEN);
    const uint8_t neg[] = {0x02, 5, 0xF6, 0xFF, 0xFF, 0xFF};      /* MOVE_BY -10 */
    handle_payload(&d, neg, sizeof neg);
    CHECK("negative move and executed count", d.position == 1000 && d.executed == 3);
}

int main(int argc, char **argv) {
    const char *t = argc > 1 ? argv[1] : "";
    if (!strcmp(t, "cobs")) test_cobs();
    if (!strcmp(t, "parser")) test_parser();
    if (!strcmp(t, "dispatch")) test_dispatch();
    CT_DONE();
}
