#include <pthread.h>
#include <string.h>
#include "ctest.h"
#include "spsc.h"

static spsc_t q;
#define COUNT 1000000u
static int bad_order = 0;

static void *producer(void *a) {
    for (uint32_t i = 0; i < COUNT; i++)
        while (!spsc_push(&q, i)) { }
    return a;
}
static void *consumer(void *a) {
    uint32_t v, expect = 0;
    while (expect < COUNT) {
        if (spsc_pop(&q, &v)) {
            if (v != expect) { bad_order = 1; return a; }
            expect++;
        }
    }
    return a;
}

int main(void) {
    uint32_t v = 0;
    memset(&q, 0, sizeof q);
    CHECK("pop on empty fails", !spsc_pop(&q, &v));
    int ok = 1;
    for (uint32_t i = 0; i < QCAP; i++) ok &= spsc_push(&q, i * 3u);
    CHECK("holds QCAP items", ok);
    CHECK("push on full fails", !spsc_push(&q, 99));
    ok = 1;
    for (uint32_t i = 0; i < QCAP; i++) ok &= spsc_pop(&q, &v) && v == i * 3u;
    CHECK("FIFO order", ok && !spsc_pop(&q, &v));
    if (ct_fails) { CHECK("stress test skipped until the basics pass", 0); CT_DONE(); }
    memset(&q, 0, sizeof q);
    pthread_t p, c;
    pthread_create(&c, 0, consumer, 0);
    pthread_create(&p, 0, producer, 0);
    pthread_join(p, 0);
    pthread_join(c, 0);
    CHECK("two threads, 1e6 items, in order, none lost", !bad_order);
    CT_DONE();
}
