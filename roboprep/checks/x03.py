import numpy as np

ANSWERS = {"M1": 3907, "M2": 8, "M3": 10}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Memory is served in aligned 128-byte transactions",
    "Stride 1: 32 floats in one segment, one transaction per warp",
    "Stride 32: 32 segments, 32 transactions for the same useful bytes",
    "Fix: coalesced tile loads into shared memory (padded), change the layout, or remap threads along rows",
]}
HINTS = {
    "launch": "Ceiling division: (n + d - 1) // d.",
    "saxpy": "i = cuda.grid(1); stride = cuda.gridsize(1); while i < x.size: ...; i += stride",
    "coalescing": "A set of address // 128 counts distinct segments.",
    "systolic": "Shift with slices and .copy(), feed the edges with the skewed indices, then acc += a_reg * b_reg.",
}


def setup(lab):
    import os, shutil
    if shutil.which("nvidia-smi") is None:
        os.environ.setdefault("NUMBA_ENABLE_CUDASIM", "1")


def check_launch(blocks, warps):
    assert blocks(1_000_000, 256) == 3907 and blocks(1024, 256) == 4 and blocks(1, 256) == 1
    assert warps(256) == 8 and warps(33) == 2 and warps(32) == 1


def check_saxpy(kernel):
    n = 3000
    x = np.arange(n, dtype=np.float32)
    y = np.ones(n, np.float32)
    for grid, block in [(4, 64), (47, 64), (1, 32)]:
        out = np.zeros_like(x)
        kernel[grid, block](np.float32(2.0), x, y, out)
        assert np.allclose(out, 2 * x + 1), f"launch [{grid}, {block}] left wrong or missing elements"


def check_coalescing(segments, addresses):
    a = addresses(0, 1)
    assert len(a) == 32 and a[1] - a[0] == 4, "thread t reads base + t * stride * 4"
    assert segments(addresses(0, 1)) == 1 and segments(addresses(0, 2)) == 2 and segments(addresses(0, 32)) == 32
    assert segments(addresses(4, 1)) == 2, "a misaligned base splits the warp across two segments"


def check_systolic(sa):
    rng = np.random.default_rng(0)
    for M, K, N in [(4, 4, 4), (3, 5, 2), (1, 1, 1), (6, 2, 7)]:
        A, B = rng.integers(-5, 5, (M, K)), rng.integers(-5, 5, (K, N))
        C, cycles = sa(A, B)
        assert np.allclose(C, A @ B), f"{M}x{K} by {K}x{N}: wrong product"
        assert cycles == K + M + N - 2, f"{M}x{K} by {K}x{N}: {cycles} cycles, expected {K + M + N - 2}"
