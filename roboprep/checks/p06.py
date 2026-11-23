import numpy as np

ANSWERS = {"M1": (1.4, {"abs": 1e-6}), "M2": (2.71, {"abs": 1e-6}), "M3": 100}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Nominal tuning picks the most aggressive gain stable at mass 1.0; latency plus a lighter robot makes it diverge",
    "Randomized tuning picks a gentler gain: slightly worse at nominal, stable and good across the range",
    "Trade: nominal performance for robustness",
    "Too wide a range: overly conservative or no good policy; bound ranges with system identification",
]}
HINTS = {
    "qlearn": "target = r if done else r + gamma * max(Q[s2]); Q[s, a] += alpha * (target - Q[s, a]).",
    "randomize": "buf.append(command); applied = buf.pop(0); semi-implicit Euler: v first, then x.",
}
N, START, GOAL, PITS = 5, (0, 0), (4, 4), {(1, 1), (2, 3), (3, 1)}
MOVES = [(-1, 0), (1, 0), (0, -1), (0, 1)]
# reference costs for episode_cost(k, m) with delay 3
COSTS = {(54.0, 1.0): 0.170213, (19.0, 0.4): 0.172942, (19.0, 1.0): 0.236254, (54.0, 0.4): 1e6}


def _step(cell, a):
    r, c = cell[0] + MOVES[a][0], cell[1] + MOVES[a][1]
    nxt = (r, c) if 0 <= r < N and 0 <= c < N else cell
    if nxt == GOAL:
        return nxt, 1.0, True
    if nxt in PITS:
        return nxt, -1.0, True
    return nxt, -0.01, False


def check_qlearn(upd, eg):
    Q = np.zeros((3, 2))
    Q[1] = [2.0, -1.0]
    td = upd(Q, 0, 1, 1.0, 1, False, 0.5, 0.9)
    assert np.isclose(Q[0, 1], 1.4) and np.isclose(td, 2.8), f"Q = {Q[0, 1]}, td = {td}"
    upd(Q, 2, 0, -1.0, 1, True, 0.5, 0.9)
    assert np.isclose(Q[2, 0], -0.5), "terminal transitions must not bootstrap"
    rng = np.random.default_rng(0)
    Qg = np.array([[0.0, 3.0, 1.0, 2.0]])
    assert all(eg(Qg, 0, 0.0, rng) == 1 for _ in range(20)), "eps = 0 must be greedy"
    counts = np.bincount([eg(Qg, 0, 1.0, rng) for _ in range(4000)], minlength=4) / 4000
    assert np.all(np.abs(counts - 0.25) < 0.04), f"eps = 1 should be uniform, got {counts}"
    rng, Q = np.random.default_rng(0), np.zeros((N * N, 4))
    for _ in range(3000):
        cell, done, steps = START, False, 0
        while not done and steps < 100:
            a = eg(Q, cell[0] * N + cell[1], 0.2, rng)
            nxt, r, done = _step(cell, a)
            upd(Q, cell[0] * N + cell[1], a, r, nxt[0] * N + nxt[1], done, 0.5, 0.95)
            cell, steps = nxt, steps + 1
    cell, n = START, 0
    while cell != GOAL and n < 30:
        cell, _, _ = _step(cell, int(np.argmax(Q[cell[0] * N + cell[1]])))
        assert cell not in PITS, "greedy policy walks into a pit"
        n += 1
    assert cell == GOAL and n == 8, f"greedy policy should reach the goal in 8 steps, took {n}"


def check_randomize(cost, pick):
    for (k, m), c in COSTS.items():
        got = cost(k, m)
        assert np.isclose(got, c, rtol=1e-3), f"episode_cost({k}, {m}) = {got:.5g}, expected {c:.5g}"
    gains = np.linspace(1, 150, 150)
    assert np.isclose(pick(gains, [1.0]), 54.0), "nominal-only tuning should pick k = 54"
    assert np.isclose(pick(gains, np.random.default_rng(0).uniform(0.3, 2.0, 20)), 19.0), "randomized tuning should pick k = 19"
