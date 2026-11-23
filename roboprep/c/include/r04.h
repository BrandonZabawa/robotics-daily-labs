/* r04.h: C/C++ version of R04 Task 3 (character device read/write with a wait queue). Use pthreads
 * (pthread_mutex_t + pthread_cond_t) in C, or std::mutex + std::condition_variable in C++. */
#ifndef RDL_R04_H
#define RDL_R04_H
#include "rdl.h"
RDL_BEGIN
typedef struct CharDev CharDev;            /* you define the struct in your file */
CharDev *chardev_create(size_t size);
void chardev_destroy(CharDev *d);
/* producer side (think: interrupt handler): returns bytes accepted, drops what does not fit */
size_t chardev_write(CharDev *d, const uint8_t *data, size_t len);
/* returns bytes read; -11 (-EAGAIN) if nonblock and empty; 0 on timeout. timeout_s < 0 waits forever. */
long chardev_read(CharDev *d, uint8_t *out, size_t n, bool nonblock, double timeout_s);
RDL_END
#endif
