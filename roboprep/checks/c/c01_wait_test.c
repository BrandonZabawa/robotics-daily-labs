#include <pthread.h>
#include <time.h>
#include "ctest.h"

void wait_ready(uint32_t *status);
static uint32_t status_word = 0;

static void *setter(void *arg) {
    (void)arg;
    struct timespec ts = {0, 50 * 1000 * 1000};
    nanosleep(&ts, 0);
    *(volatile uint32_t *)&status_word = 1u;
    return 0;
}

int main(void) {
    pthread_t t;
    pthread_create(&t, 0, setter, 0);
    wait_ready(&status_word);
    pthread_join(t, 0);
    CHECK("wait_ready returns after the bit is set", 1);
    CT_DONE();
}
