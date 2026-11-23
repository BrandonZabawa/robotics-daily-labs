#include <pthread.h>
#include <stdatomic.h>
#include "ctest.h"
typedef struct { atomic_uint next; atomic_uint serving; } ticket_lock_t;
void tl_lock(ticket_lock_t *l);
void tl_unlock(ticket_lock_t *l);

static ticket_lock_t lock;
static long counter = 0;            /* plain variable: only the lock protects it */
#define ITERS 100000

static void *work(void *a) {
    for (int i = 0; i < ITERS; i++) { tl_lock(&lock); counter++; tl_unlock(&lock); }
    return a;
}

int main(void) {
    tl_lock(&lock);
    tl_unlock(&lock);
    CHECK_EQ("lock then unlock advances serving", atomic_load(&lock.serving), 1);
    pthread_t t[3];
    for (int i = 0; i < 3; i++) pthread_create(&t[i], 0, work, 0);
    for (int i = 0; i < 3; i++) pthread_join(t[i], 0);
    CHECK_EQ("3 threads x 100000 increments under the lock", counter, 3L * ITERS);
    CT_DONE();
}
