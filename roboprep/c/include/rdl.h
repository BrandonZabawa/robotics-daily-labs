/* rdl.h: shared prelude for the C/C++ versions of the labs.
 * Every lab header includes this. Functions get C linkage so C++ files can implement them too. */
#ifndef RDL_H
#define RDL_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#ifdef __cplusplus
#define RDL_BEGIN extern "C" {
#define RDL_END }
#else
#define RDL_BEGIN
#define RDL_END
#endif
#endif
