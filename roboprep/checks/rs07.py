ANSWERS = {"M1": 6, "M2": 100}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Per-move task logic with retries and recovery fits a behavior tree",
    "Re-checked conditions make the tree react to board changes",
    "Modes and safety (homing, idle, operational, fault, e-stop) fit a state machine with latched transitions",
    "The state machine gates when the tree may run",
]}
HINTS = {
    "nodes": "Sequence returns the first child status that is not SUCCESS; Fallback the first that is not FAILURE.",
    "tree": "Fallback([Condition(in_gripper), Sequence([Condition(visible), Action(approach), Retry(Action(grasp), 3)])]).",
}
S, F, R = "SUCCESS", "FAILURE", "RUNNING"


class _Leaf:
    def __init__(self, seq):
        self.seq, self.calls = list(seq), 0

    def tick(self):
        self.calls += 1
        return self.seq.pop(0) if len(self.seq) > 1 else self.seq[0]


def check_nodes(Seq, Fb, Retry):
    a, b = _Leaf([S]), _Leaf([R])
    assert Seq([a, b]).tick() == R and a.calls == 1 and b.calls == 1
    a, b = _Leaf([F]), _Leaf([S])
    assert Seq([a, b]).tick() == F and b.calls == 0, "sequence stops at the first failure"
    a, b = _Leaf([F]), _Leaf([S])
    assert Fb([a, b]).tick() == S and a.calls == 1 and b.calls == 1
    a, b = _Leaf([S]), _Leaf([F])
    assert Fb([a, b]).tick() == S and b.calls == 0, "fallback stops at the first success"
    assert Fb([_Leaf([F]), _Leaf([F])]).tick() == F
    leaf = _Leaf([F, F, S])
    r = Retry(leaf, 3)
    assert [r.tick(), r.tick(), r.tick()] == [R, R, S], "two failures then success within 3 tries"
    r = Retry(_Leaf([F]), 2)
    assert [r.tick(), r.tick()] == [R, F], "second failure of 2 allowed gives FAILURE"


def check_tree(build, World):
    w = World(grasp_fail_first=1)
    t = build(w)
    statuses = [t.tick() for _ in range(7)]
    assert statuses[:3] == [R, R, R] and w.distance == 0, f"approach phase {statuses}"
    assert S in statuses and w.in_gripper and w.grasp_attempts == 2, f"grasp with one retry: {statuses}"
    assert t.tick() == S and w.grasp_attempts == 2, "once holding, the first Fallback child short-circuits"
    w = World()
    t = build(w)
    t.tick()
    w.visible = False
    d = w.distance
    assert t.tick() == F and w.distance == d, "object lost: fail immediately without approaching further"
    w = World(grasp_fail_first=5)
    t = build(w)
    out = [t.tick() for _ in range(6)]
    assert out[-1] == F and w.grasp_attempts == 3, f"give up after 3 grasp failures: {out}, attempts {w.grasp_attempts}"


def c_nodes(lib):
    import ctypes as C
    from roboprep.cbind import Functions
    LEAF = C.CFUNCTYPE(C.c_int, C.c_void_p)
    f = Functions(lib, "rs07", {"BtNode": None, "BtLeafFn": LEAF})
    names = ["SUCCESS", "FAILURE", "RUNNING"]

    class _Node:
        def tick(self):
            return names[f.bt_tick(self._p)]

    def ptr(child):
        """C node pointer for a wrapped node, or a new leaf that calls a Python node's tick()."""
        if isinstance(child, _Node):
            return child._p, child
        cb = LEAF(lambda _: names.index(child.tick()))
        return f.bt_leaf(cb, None), cb

    def composite(make):
        class Composite(_Node):
            def __init__(self, children):
                pairs = [ptr(c) for c in children]
                self._keep = [k for _, k in pairs]
                self._p = make((C.c_void_p * max(1, len(pairs)))(*[p for p, _ in pairs]), len(pairs))
        return Composite

    class Retry(_Node):
        def __init__(self, child, n):
            p, self._keep = ptr(child)
            self._p = f.bt_retry(p, n)
    return composite(f.bt_sequence), composite(f.bt_fallback), Retry
