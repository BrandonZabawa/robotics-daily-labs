import numpy as np

ANSWERS = {"M1": (6.243, {"abs": 1e-3}), "M2": 3, "M3": 29}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "In C-space the robot is a point: collision check is one lookup, any graph search applies",
    "Inflating once is cheaper than sweeping the outline along every edge",
    "Exact only for a translating disc robot",
    "Orientation-dependent shapes or arms need more dimensions (x, y, theta or joints); circumscribed inflation is too conservative",
]}
HINTS = {
    "inflate": "Loop over offsets with dx^2 + dy^2 <= r^2 and shift the obstacle coordinates, clipping at the borders.",
    "astar": "heapq of (f, g, cell); skip closed cells; reconstruct through a parent dict.",
}
# expected optimal costs on inflate(make_map(), 3), and the expansions Dijkstra needs for the same query
CASES = [((2, 2), (37, 37), 102.42640687119281, 1084),
         ((37, 2), (2, 37), 57.11269837220807, 862),
         ((20, 20), (2, 2), 52.04163056034262, 1053)]


def _map():
    g = np.zeros((40, 40), bool)
    g[0:28, 13] = True
    g[12:40, 27] = True
    g[14:20, 4:7] = True
    return g


def check_inflate(inflate):
    one = np.zeros((9, 9), bool)
    one[4, 4] = True
    out = inflate(one, 3)
    assert out.sum() == 29 and out[4, 7] and out[6, 6] and not out[7, 7], f"single cell, r = 3: {out.sum()} cells (expected 29)"
    corner = np.zeros((5, 5), bool)
    corner[0, 0] = True
    assert inflate(corner, 2).sum() == 6, "clip at the borders"
    cs = inflate(_map(), 3)
    assert cs.sum() == 502, f"{cs.sum()} inflated cells on the lab map (expected 502)"


def check_astar(astar, inflate, octile):
    assert np.isclose(octile((0, 0), (5, 3)), 5 + 3 * (np.sqrt(2) - 1))
    cs = inflate(_map(), 3)
    for s, t, cost, dijkstra in CASES:
        path, n = astar(cs, s, t)
        assert path is not None, f"{s}->{t}: no path found"
        path = [tuple(p) for p in path]
        assert path[0] == s and path[-1] == t, "path must start at start and end at goal"
        total = 0.0
        for a, b in zip(path, path[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            assert max(abs(dx), abs(dy)) == 1 and not cs[b], f"illegal step {a}->{b}"
            if dx and dy:
                assert not cs[a[0] + dx, a[1]] and not cs[a[0], a[1] + dy], f"corner cut at {a}->{b}"
            total += np.hypot(dx, dy)
        assert np.isclose(total, cost), f"{s}->{t}: cost {total:.4f}, optimal is {cost:.4f}"
        assert n < 0.9 * dijkstra, f"{s}->{t}: {n} expansions; Dijkstra needs {dijkstra}, the heuristic should save more"
    assert astar(cs, (2, 2), (15, 5))[0] is None, "goal inside an obstacle: None"
