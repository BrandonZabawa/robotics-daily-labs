/* d05.h: C/C++ versions of D05. */
#ifndef RDL_D05_H
#define RDL_D05_H
#include "rdl.h"
RDL_BEGIN
typedef struct { uint64_t pid; uint8_t bcr; uint8_t dcr; } I3cTarget;   /* pid: 48-bit provisioned ID */
/* Task 1: addr_out[i] receives the dynamic address assigned to targets[i]. */
void entdaa(const I3cTarget *targets, size_t n, uint8_t first, uint8_t *addr_out);
/* Task 2 */
bool ccc_is_direct(uint8_t code);
uint8_t ibi_winner(const uint8_t *dynamic_addresses, size_t n);
RDL_END
#endif
