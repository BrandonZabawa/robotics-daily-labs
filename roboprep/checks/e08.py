import numpy as np

ANSWERS = {"M1": (0.847, {"abs": 1e-3}), "M2": (0.8808, {"abs": 1e-3}), "M3": 1}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Log-odds make the Bayes update an addition per cell; unknown starts at 0 (p = 0.5)",
    "Numerically stable near p = 0 and p = 1",
    "Without a clamp, repeated hits make a cell nearly certain; undoing it takes as many misses",
    "Result: ghost obstacles after people or doors move; clamping keeps the map responsive",
]}
HINTS = {
    "flow": "Iy, Ix = np.gradient(I0); solve G [u, v] = -[sum Ix It, sum Iy It].",
    "occupancy": "Step along the major axis; accumulate an error term to decide when the minor axis steps.",
}


def _blob(cx, cy, n=64, s=5.0):
    y, x = np.mgrid[0:n, 0:n]
    return np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * s * s))


def check_flow(tensor, lk):
    profile = 1 / (1 + np.exp(-(np.arange(64) - 31.5)))               # changes along rows: a horizontal edge
    edge = np.repeat(profile[:, None], 64, axis=1)
    ev = np.linalg.eigvalsh(tensor(edge))
    assert ev[0] < 1e-9 * ev[1], f"edge should be rank 1, eigenvalues {ev}"
    ev = np.linalg.eigvalsh(tensor(_blob(32, 32)))
    assert ev[0] > 0.5 * ev[1], f"blob should be rank 2 with similar eigenvalues, got {ev}"
    u, v = lk(_blob(32, 32), _blob(32.4, 31.7))
    assert abs(u - 0.4) < 0.05 and abs(v + 0.3) < 0.05, f"(u, v) = ({u:.3f}, {v:.3f}), expected (0.4, -0.3)"


def _line_ok(cells, x0, y0, x1, y1):
    cells = [tuple(int(c) for c in p) for p in cells]
    assert cells[0] == (x0, y0) and cells[-1] == (x1, y1), f"{(x0, y0)}->{(x1, y1)}: wrong endpoints {cells[0]}, {cells[-1]}"
    assert len(cells) == max(abs(x1 - x0), abs(y1 - y0)) + 1, f"{(x0, y0)}->{(x1, y1)}: {len(cells)} cells"
    for a, b in zip(cells, cells[1:]):
        assert max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1, "consecutive cells must touch (8-connected)"
    dx, dy = x1 - x0, y1 - y0
    for x, y in cells:
        if dx == 0 and dy == 0:
            continue
        if abs(dx) >= abs(dy):
            off = y - (y0 + dy * (x - x0) / dx)
        else:
            off = x - (x0 + dx * (y - y0) / dy)
        assert abs(off) <= 0.5 + 1e-9, f"cell {(x, y)} is too far from the ideal line"


def check_occupancy(bres, update):
    for a in [(0, 0, 5, 2), (0, 0, 2, 5), (3, 3, -4, 1), (2, 7, 2, -3), (0, 0, -6, -6), (5, 5, 5, 5), (1, 0, 9, -3)]:
        _line_ok(bres(*a), *a)
    L = np.zeros((40, 40))
    walls, free = set(), set()
    for _ in range(3):
        for a in np.linspace(0, 2 * np.pi, 180, endpoint=False):
            r = 0.0
            while True:
                r += 0.25
                x, y = int(round(20 + r * np.cos(a))), int(round(20 + r * np.sin(a)))
                if x in (5, 34) or y in (5, 34):
                    break
            walls.add((x, y))
            L = update(L, (20, 20), (x, y), 0.85, -0.4, 3.5)
    assert np.abs(L).max() <= 3.5 + 1e-9, "clamp to +-l_max"
    assert all(L[w] > 0 for w in walls), "every hit wall cell should end with positive log-odds"
    assert L[20, 20] < 0 and L[12, 20] < 0 and L[20, 28] < 0, "cells along the beams should be free"
    assert L[0, 0] == 0 and L[39, 39] == 0, "cells outside the room are never observed"
