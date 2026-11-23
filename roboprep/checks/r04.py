import threading
import time
from roboprep import clab

ANSWERS = {"M1": 251658243, "M2": 104, "M3": 69}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "read() enters the driver in process context; empty buffer -> sleep on the wait queue",
    "Interrupt handler fills the buffer under spin_lock_irqsave and calls wake_up",
    "Reader wakes, takes the data under the lock",
    "copy_to_user happens outside the spinlock because it may sleep",
]}
HINTS = {
    "boot": "ROM code first, the kernel needs the DTB, init is the first user-space process.",
    "dts": "I2C children use reg = <address>; SPI children reg = <chip select>; mode 1 = spi-cpha.",
    "chardev": "with self.lock: ... self.wq.wait_for(lambda: len(self.buf) > 0); notify_all() in write.",
    "locks": "Interrupt context cannot sleep, so it needs a spinlock; anything that may sleep needs a mutex.",
}


def check_boot(order):
    if order is None:
        raise NotImplementedError
    assert list(order) == ["Boot ROM", "SPL / TF-A", "U-Boot", "Linux kernel + DTB", "init (systemd)"], f"order {order}"


def _get(prop, node, typ):
    r = clab.sh(f"fdtget -t {typ} board.dtb {node} {prop}")
    return r.stdout.strip() if r.returncode == 0 else None


def check_dts():
    r = clab.sh("dtc -q -I dts -O dtb -o board.dtb board.dts")
    assert r.returncode == 0, "dtc failed:\n" + r.stderr[-800:]
    imu = "/i2c@40005400/imu@68"
    assert _get("compatible", imu, "s") == "invensense,icm42688", "imu compatible"
    assert _get("reg", imu, "u") == "104", "imu reg must be <0x68>"
    assert _get("interrupts", imu, "u") == "37 4", "imu interrupts"
    enc = "/spi@40013000/encoder@0"
    assert _get("compatible", enc, "s") == "ams,as5047p", "encoder compatible"
    assert _get("reg", enc, "u") == "0", "encoder chip select"
    assert _get("spi-max-frequency", enc, "u") == "10000000", "encoder clock"
    assert clab.sh(f"fdtget -p board.dtb {enc}").stdout.split().count("spi-cpha") == 1, "mode 1 needs spi-cpha"
    assert "spi-cpol" not in clab.sh(f"fdtget -p board.dtb {enc}").stdout.split(), "mode 1 has CPOL = 0"


def check_chardev(cls):
    d = cls(size=8)
    try:
        d.read(4, nonblock=True)
        raise AssertionError("non-blocking read on an empty device must raise BlockingIOError")
    except BlockingIOError:
        pass
    got, t_done = [], []
    def reader():
        got.append(d.read(4, timeout=5))
        t_done.append(time.time())
    th = threading.Thread(target=reader)
    th.start()
    time.sleep(0.3)
    assert not got, "read() returned before any data was written: it must block"
    t_write = time.time()
    assert d.write(b"abcdef") == 6
    th.join(2)
    assert got == [b"abcd"] and t_done[0] - t_write < 0.2, f"blocked reader got {got}"
    assert d.write(b"0123456789") == 6, "only the free space (8 - 2 bytes) is accepted"
    assert d.read(100) == b"ef012345", "remaining bytes in order"


def check_locks(locks):
    if any(v is None for v in locks.values()):
        raise NotImplementedError
    want = ["spinlock", "mutex", "mutex", "spinlock"]
    wrong = [k for k, w in zip(locks, want) if str(locks[k]).lower() != w]
    assert not wrong, "wrong: " + "; ".join(wrong)


CFLAGS = "-pthread"


def c_chardev(lib):
    import ctypes as C
    from roboprep.cbind import Functions, u8, out
    f = Functions(lib, "r04", {"CharDev": None})          # opaque: your struct stays private to your file

    class CharDev:
        def __init__(self, size=64):
            self._d = f.chardev_create(size)

        def write(self, data):
            return f.chardev_write(self._d, *u8(data))

        def read(self, n, nonblock=False, timeout=None):
            buf = out(C.c_uint8, n)
            r = f.chardev_read(self._d, buf, n, bool(nonblock), -1.0 if timeout is None else float(timeout))
            if r == -11:
                raise BlockingIOError("EAGAIN")
            return bytes(buf[:max(0, r)])
    return (CharDev,)
