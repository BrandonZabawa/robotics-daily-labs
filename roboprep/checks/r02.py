ANSWERS = {"M1": 9, "M2": 3, "M3": 4}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Each task holds one mutex and waits for the other: circular wait",
    "All four conditions hold: mutual exclusion, hold and wait, no preemption, circular wait",
    "Fix 1: a global lock order",
    "Fix 2: timeout and back off (or one owner task per bus with a request queue)",
]}
HINTS = {
    "inheritance": "Look at every other task whose next op is ('lock', m) with owner[m] == task; take the max recursively.",
    "deadlock": "Follow waits_for from each task until you hit None or a task already on the path.",
}

PATHFINDER = [
    ("L", 1, 0, [("run", 1), ("lock", "M"), ("run", 4), ("unlock", "M"), ("run", 1)]),
    ("H", 3, 2, [("run", 1), ("lock", "M"), ("run", 2), ("unlock", "M")]),
    ("M", 2, 3, [("run", 6)]),
]
CHAIN = [
    ("L", 1, 0, [("lock", "A"), ("run", 5), ("unlock", "A")]),
    ("M", 2, 1, [("lock", "B"), ("lock", "A"), ("run", 1), ("unlock", "A"), ("unlock", "B")]),
    ("X", 3, 2, [("run", 8)]),
    ("H", 4, 3, [("lock", "B"), ("run", 1), ("unlock", "B")]),
]


def check_inheritance(eff, sim):
    fin, _ = sim(PATHFINDER, False)
    assert fin == {"L": 15, "H": 14, "M": 9}, f"without inheritance: {fin}"
    fin, tl = sim(PATHFINDER, True)
    assert fin == {"L": 15, "H": 8, "M": 14}, f"with inheritance: {fin} ({tl})"
    fin, tl = sim(CHAIN, True)
    assert fin["H"] < fin["X"], f"chained inheritance (H waits on M, which waits on L) must outrank X: {fin} ({tl})"


def check_deadlock(fn):
    got = fn({"A": "B", "B": "C", "C": "A", "D": "A"})
    assert got == {"A", "B", "C"}, f"cycle A->B->C->A: got {got}"
    assert fn({"A": "B", "B": None, "C": "B"}) is None, "no cycle"
    assert fn({"T1": "T2", "T2": "T1"}) == {"T1", "T2"}


def c_inheritance(lib):
    import ctypes as C
    from roboprep.cbind import Functions, out

    class T(C.Structure):
        _fields_ = [("prio", C.c_int), ("waiting_for", C.c_int)]
    f = Functions(lib, "r02", {"RtTask": T})

    def simulate(spec, inheritance, t_max=100):
        """The notebook's simulator, asking your C effective_priority for every scheduling decision."""
        tasks = [dict(name=n, prio=p, release=r, script=list(s), pc=0, left=None, finish=None) for n, p, r, s in spec]
        mutexes = sorted({op[1] for _, _, _, s in spec for op in s if op[0] in ("lock", "unlock")})
        owner, t, timeline = {}, 0, []

        def eff(task):
            arr_t = (T * len(tasks))()
            for k, x in enumerate(tasks):
                op = x["script"][x["pc"]] if x["pc"] < len(x["script"]) else None
                arr_t[k] = T(x["prio"], mutexes.index(op[1]) if op and op[0] == "lock" else -1)
            own = out(C.c_int, len(mutexes))
            for m, name in enumerate(mutexes):
                own[m] = tasks.index(owner[name]) if owner.get(name) is not None else -1
            return f.effective_priority(arr_t, len(tasks), tasks.index(task), own, bool(inheritance))

        def blocked(task):
            op = task["script"][task["pc"]]
            return op[0] == "lock" and owner.get(op[1]) not in (None, task)
        while t < t_max and any(x["finish"] is None for x in tasks):
            for x in tasks:
                while x["release"] <= t and x["finish"] is None and not blocked(x) and x["script"][x["pc"]][0] in ("lock", "unlock"):
                    op = x["script"][x["pc"]]
                    owner[op[1]] = x if op[0] == "lock" else None
                    x["pc"] += 1
                    if x["pc"] == len(x["script"]):
                        x["finish"] = t
            ready = [x for x in tasks if x["release"] <= t and x["finish"] is None and not blocked(x)]
            if not ready:
                timeline.append(".")
                t += 1
                continue
            cur = max(ready, key=lambda x: (eff(x), -x["release"]))
            if cur["left"] is None:
                cur["left"] = cur["script"][cur["pc"]][1]
            cur["left"] -= 1
            timeline.append(cur["name"])
            t += 1
            if cur["left"] == 0:
                cur["left"] = None
                cur["pc"] += 1
                if cur["pc"] == len(cur["script"]):
                    cur["finish"] = t
        return {x["name"]: x["finish"] for x in tasks}, "".join(timeline)
    return (None, simulate)


def c_deadlock(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr, out
    f = Functions(lib, "r02")

    def find_cycle(waits_for):
        names = sorted(set(waits_for) | {v for v in waits_for.values() if v is not None})
        w = arr(C.c_int, [names.index(waits_for[n]) if waits_for.get(n) is not None else -1 for n in names])
        cyc = out(C.c_int, len(names))
        k = f.find_cycle(w, len(names), cyc)
        return {names[i] for i in cyc[:k]} if k else None
    return (find_cycle,)
