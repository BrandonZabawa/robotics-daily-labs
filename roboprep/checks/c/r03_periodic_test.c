#define _GNU_SOURCE
#include <time.h>
#include "ctest.h"
int64_t run_periodic(int64_t period_ns, int iters, int64_t *lat);

int main(void) {
    enum { N = 500 };
    static int64_t lat[N];
    for (int i = 0; i < N; i++) lat[i] = -1;
    struct timespec a, b;
    clock_gettime(CLOCK_MONOTONIC, &a);
    int64_t span = run_periodic(2000000, N, lat);
    clock_gettime(CLOCK_MONOTONIC, &b);
    double wall = (b.tv_sec - a.tv_sec) + (b.tv_nsec - a.tv_nsec) / 1e9;
    CHECK_EQ("span is exactly (iters - 1) periods", span, (int64_t)(N - 1) * 2000000);
    int early = 0, unset = 0;
    for (int i = 0; i < N; i++) { if (lat[i] < 0) early++; if (lat[i] == -1) unset++; }
    CHECK("every latency recorded and never early", early == 0 && unset == 0);
    CHECK("no drift: 500 x 2 ms finishes within 1.0 to 1.05 s", wall >= 0.999 && wall < 1.05);
    CT_DONE();
}
