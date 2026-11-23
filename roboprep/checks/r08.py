import multiprocessing as mp
import os
from roboprep import clab

ANSWERS = {"M1": 131072, "M2": 3}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Firmware name written to remoteproc sysfs, then start: segments loaded into the M core's memory",
    "Resource table parsed: carveouts, virtio device with vrings; shared memory allocated; core released from reset",
    "OpenAMP on the M side announces an endpoint (name service); Linux creates the rpmsg channel",
    "rpmsg_char / rpmsg_tty exposes /dev/rpmsg0 or /dev/ttyRPMSG0; writes go into the vring and kick the mailbox",
]}
HINTS = {
    "ticket": "fetch_add on next (relaxed), spin on load_acquire(serving) != me; unlock stores serving + 1 with release.",
    "ring": "Full when head - tail == N; write the slot, then set_head, then os.eventfd_write(doorbell, 1).",
}


def check_ticket():
    r = clab.run_ctest(["ticket.c"], "r08_ticket_test.c", flags="-O2 -fsanitize=thread", sanitize=False, timeout=90)
    if "FATAL: ThreadSanitizer" in r.output:
        r = clab.run_ctest(["ticket.c"], "r08_ticket_test.c", flags="-O2", sanitize=False, timeout=90)
    if "ThreadSanitizer: data race" in r.output:
        raise AssertionError("data race on the protected counter: check acquire on lock and release on unlock")
    r.require(2)


def _consumer(name, efd, n, q, cls, recv_all):
    ring = cls(name)
    got = []
    while len(got) < n:
        os.eventfd_read(efd)          # sleep until the doorbell rings
        got += recv_all(ring)
    q.put(got)
    ring.shm.close()


def check_ring(cls, send, recv_all):
    ctx = mp.get_context("fork")
    ring = cls()
    ring.doorbell = os.eventfd(0)
    q = ctx.Queue()
    msgs = [f"setpoint {k} {k * 0.001:.3f}".encode() for k in range(300)]
    p = ctx.Process(target=_consumer, args=(ring.shm.name, ring.doorbell, len(msgs), q, cls, recv_all))
    p.start()
    try:
        for m in msgs:
            send(ring, m)
        got = q.get(timeout=20)
    finally:
        p.join(5)
        if p.is_alive():
            p.kill()
        ring.shm.close()
        ring.shm.unlink()
    assert got == msgs, f"received {len(got)} messages; first mismatch at {next((i for i, (a, b) in enumerate(zip(got, msgs)) if a != b), None)}"


def c_ring(lib):
    import ctypes as C
    import struct
    from multiprocessing import shared_memory
    from roboprep.cbind import Functions, u8, out
    f = Functions(lib, "r08")
    N, SLOT = 16, 64

    class Ring:
        def __init__(self, name=None):
            self.shm = shared_memory.SharedMemory(name=name, create=name is None, size=8 + N * SLOT)
            if name is None:
                self.shm.buf[:8] = bytes(8)
            self.doorbell = None

        def head(self): return struct.unpack_from("<I", self.shm.buf, 0)[0]
        def tail(self): return struct.unpack_from("<I", self.shm.buf, 4)[0]

    def _ptr(ring):
        return (C.c_uint8 * (8 + N * SLOT)).from_buffer(ring.shm.buf)

    def send(ring, data):
        p = _ptr(ring)
        f.ring_send(p, ring.doorbell, *u8(data))
        del p

    def recv_all(ring):
        p, buf, lens = _ptr(ring), out(C.c_uint8, N * SLOT), out(C.c_size_t, N)
        n = f.ring_recv_all(p, buf, N * SLOT, lens, N)
        del p
        res, k = [], 0
        for i in range(n):
            res.append(bytes(buf[k:k + lens[i]]))
            k += lens[i]
        return res
    return Ring, send, recv_all
