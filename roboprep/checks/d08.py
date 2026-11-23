PIP = ["python-can"]
ANSWERS = {"M1": 32, "M2": 256, "M3": 24}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Heartbeat: one small frame per node per period, detection time = consumer timeout, low load",
    "Node guarding: request plus reply per node, needs remote frames (gone in CAN FD), centralized",
    "Time-triggered: fixed windows, missing message seen within one cycle, no arbitration jitter",
    "Time-triggered costs schedule design and synchronization on every node",
]}
HINTS = {
    "fd": "Walk the length table and return the first entry >= n.",
    "heartbeat": "Heartbeat COB-ID is 0x700 + node with exactly one data byte.",
    "tails": "Byte = start<<7 | end<<6 | toggle<<5 | tid; toggle flips each frame.",
}


def check_fd(fn):
    for n, want in [(0, (0, 0)), (8, (8, 8)), (9, (9, 12)), (20, (11, 20)), (33, (14, 48)), (64, (15, 64))]:
        assert tuple(fn(n)) == want, f"{n} bytes -> {fn(n)}, want {want}"


def check_heartbeat(cls):
    m = cls([5, 6, 7], timeout_s=0.25)
    for k in range(5):
        m.on_frame(0x705, bytes([0x05]), k * 0.1)
    m.on_frame(0x706, bytes([0x7F]), 0.0)
    m.on_frame(0x185, bytes([1, 2, 3, 4]), 0.2)         # a PDO from node 5: not a heartbeat
    m.on_frame(0x707, bytes([0x05, 0x00]), 0.2)          # wrong length: ignore
    s = m.status(0.45)
    assert s[5] == ("OK", "operational"), f"node 5: {s[5]}"
    assert s[6] == ("LOST", "pre-operational"), f"node 6: {s[6]}"
    assert s[7] == ("UNKNOWN", None), f"node 7: {s[7]}"
    m.on_frame(0x706, bytes([0x00]), 0.5)
    assert m.status(0.55)[6] == ("OK", "boot-up"), "node 6 rebooted"


def check_tails(fn):
    assert fn(1, 3, "cyphal") == [0xE3], "single-frame Cyphal transfer: start, end, toggle 1"
    assert fn(1, 3, "dronecan") == [0xC3], "single-frame DroneCAN transfer: toggle 0"
    assert fn(3, 31, "cyphal") == [0xBF, 0x1F, 0x7F], f"3-frame Cyphal: {[hex(x) for x in fn(3, 31, 'cyphal')]}"
    assert fn(2, 0, "dronecan") == [0x80, 0x60], "2-frame DroneCAN"


def c_fd(lib):
    import ctypes as C
    from roboprep.cbind import Functions
    f = Functions(lib, "d08")

    def dlc_for(n):
        p = C.c_size_t()
        d = f.can_fd_dlc_for(n, C.byref(p))
        if d < 0:
            raise ValueError("more than 64 bytes")
        return d, p.value
    return (dlc_for,)


def c_heartbeat(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr, u8

    class S(C.Structure):
        _fields_ = [("nodes", C.c_uint8 * 16), ("n_nodes", C.c_size_t), ("timeout_s", C.c_double),
                    ("last_t", C.c_double * 16), ("last_state", C.c_int * 16)]
    f = Functions(lib, "d08", {"HeartbeatMonitor": S})
    NMT = {0x00: "boot-up", 0x04: "stopped", 0x05: "operational", 0x7F: "pre-operational"}

    class HeartbeatMonitor:
        def __init__(self, nodes, timeout_s):
            self.nodes, self._s = list(nodes), S()
            f.hb_init(C.byref(self._s), arr(C.c_uint8, self.nodes), len(self.nodes), timeout_s)

        def on_frame(self, can_id, data, t):
            f.hb_on_frame(C.byref(self._s), can_id, *u8(data), t)

        def status(self, t):
            res = {}
            for n in self.nodes:
                st = C.c_int()
                code = f.hb_status(C.byref(self._s), n, t, C.byref(st))
                res[n] = (["UNKNOWN", "OK", "LOST"][code], None if st.value < 0 else NMT.get(st.value))
            return res
    return (HeartbeatMonitor,)


def c_tails(lib):
    import ctypes as C
    from roboprep.cbind import Functions, out
    f = Functions(lib, "d08")

    def tail_bytes(n_frames, transfer_id, protocol):
        buf = out(C.c_uint8, n_frames)
        f.tail_bytes(n_frames, transfer_id, {"cyphal": 0, "dronecan": 1}[protocol], buf)
        return list(buf[:n_frames])
    return (tail_bytes,)
