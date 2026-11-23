ANSWERS = {"M1": (0.7798, {"abs": 1e-4}), "M2": 10, "M3": 0.9}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Rate-monotonic order: current loop, then CAN, then telemetry",
    "U = 0.6, under the bound (or RTA confirms all deadlines)",
    "Add interrupts, blocking from shared resources, RTOS and context-switch overhead, jitter",
    "Use measured worst-case execution times and keep a margin",
]}
HINTS = {
    "utilization": "U = sum(C / T); compare with n (2^(1/n) - 1) and with 1.",
    "rta": "Start at R = C; R_next = C + sum(ceil(R / Tj) * Cj) over higher-priority tasks; stop when stable or > T.",
    "partition": "Reuse response_times() on core + [task] to test a placement.",
}


def check_utilization(bound, test):
    assert abs(bound(1) - 1.0) < 1e-12 and abs(bound(2) - 0.8284271) < 1e-6, "bound values"
    assert test([(1, 4), (1, 5)]) == "schedulable"
    assert test([(1, 4), (2, 6), (3, 12)]) == "unknown"
    assert test([(3, 4), (2, 5)]) == "unschedulable"


def check_rta(fn):
    assert fn([(3, 12), (1, 4), (2, 6)]) == [1, 3, 10], f"got {fn([(3, 12), (1, 4), (2, 6)])}"
    assert fn([(2, 5), (4, 7)]) == [2, None], "second task misses its 7 ms deadline"
    assert fn([(1, 3), (1, 5), (1, 15)]) == [1, 2, 3]


def check_partition(fn):
    tasks = [(5, 10), (4, 10), (3, 10), (3, 10)]
    cores = fn(tasks, 2)
    assert cores is not None and sorted(map(len, cores)) == [2, 2], f"placement {cores}"
    assert max(sum(c / t for c, t in core) for core in cores) == 0.9
    assert fn([(6, 10), (6, 10), (6, 10)], 2) is None, "three 60% tasks cannot fit on two cores"


def c_utilization(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr
    f = Functions(lib, "r01")

    def rm_test(tasks):
        code = f.rm_test(arr(C.c_double, [c for c, _ in tasks]), arr(C.c_double, [t for _, t in tasks]), len(tasks))
        return ["schedulable", "unknown", "unschedulable"][code]
    return f.ll_bound, rm_test


def _c_rta(f):
    import ctypes as C
    from roboprep.cbind import arr, out

    def response_times(tasks):
        r = out(C.c_int32, len(tasks))
        f.response_times(arr(C.c_uint32, [c for c, _ in tasks]), arr(C.c_uint32, [t for _, t in tasks]), len(tasks), r)
        return [None if v < 0 else v for v in r[:len(tasks)]]
    return response_times


def c_rta(lib):
    from roboprep.cbind import Functions
    return (_c_rta(Functions(lib, "r01")),)


def c_partition(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr, out
    f = Functions(lib, "r01")

    def partition_ffd(tasks, n_cores):
        core_of = out(C.c_int, len(tasks))
        if not f.partition_ffd(arr(C.c_uint32, [c for c, _ in tasks]), arr(C.c_uint32, [t for _, t in tasks]), len(tasks), n_cores, core_of):
            return None
        return [[tasks[i] for i in range(len(tasks)) if core_of[i] == k] for k in range(n_cores)]
    return (partition_ffd,)
