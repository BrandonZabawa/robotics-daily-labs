/* rs07.h: C/C++ version of RS07 Task 1 (behavior tree control nodes). In C++, a node class hierarchy with a
 * virtual tick() behind these factory functions is the natural design (as in BehaviorTree.CPP). */
#ifndef RDL_RS07_H
#define RDL_RS07_H
#include "rdl.h"
RDL_BEGIN
enum { BT_SUCCESS = 0, BT_FAILURE = 1, BT_RUNNING = 2 };
typedef struct BtNode BtNode;              /* you define it */
typedef int (*BtLeafFn)(void *ctx);         /* returns BT_SUCCESS, BT_FAILURE or BT_RUNNING */
BtNode *bt_leaf(BtLeafFn fn, void *ctx);
BtNode *bt_sequence(BtNode **children, size_t n);   /* copy the child pointers: the array is temporary */
BtNode *bt_fallback(BtNode **children, size_t n);
BtNode *bt_retry(BtNode *child, int n);
int bt_tick(BtNode *node);
RDL_END
#endif
