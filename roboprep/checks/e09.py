import numpy as np

ANSWERS = {"M1": 20, "M2": 10, "M3": (5.991, {"abs": 1e-3})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Each odometry edge adds independent noise; positions are sums of edges, so covariance grows along the chain",
    "Biases (scale, heading) make the drift grow even faster",
    "A loop closure closes a cycle: least squares must satisfy chain and closure together",
    "The mismatch is spread over every edge of the cycle, so all poses in the loop improve, not just the ends",
]}
HINTS = {
    "graph": "Edge k fills rows 2k and 2k+1: +sqrt(w) at column of p_j, -sqrt(w) at p_i, b = sqrt(w) z.",
    "gate": "r = z - (est[j] - est[i]); d2 = r.r / ((|j-i|+1) sigma^2).",
}
TRUTH = np.array([[0, 0], [1, 0], [2, 0], [3, 0], [3, 1], [3, 2], [2, 2], [1, 2], [0, 2], [0, 1]], float)


def _edges(seed=3):
    rng = np.random.default_rng(seed)
    odo = [(k, k + 1, TRUTH[k + 1] - TRUTH[k] + np.array([0.04, 0.03]) + rng.normal(0, 0.02, 2), 400.0) for k in range(9)]
    return odo, (9, 0, TRUTH[0] - TRUTH[9], 400.0)


def check_graph(build, solve):
    odo, loop = _edges()
    A, b = build(10, odo + [loop])
    assert A.shape == (22, 20) and b.shape == (22,), f"shapes {A.shape}, {b.shape}"
    assert np.allclose(A[0, :4], [-20, 0, 20, 0]) and np.isclose(b[0], 20 * odo[0][2][0]), "row 0 should weight edge 0 by sqrt(w) = 20"
    x = np.linalg.lstsq(A, b, rcond=None)[0]
    P = solve(10, odo + [loop])
    assert np.allclose(P, x.reshape(10, 2), atol=1e-6), "solve_graph should be the least-squares solution of build_system"
    assert np.allclose(P[0], 0, atol=1e-5), "p0 must be anchored at the origin"
    dead = solve(10, odo)
    e_dead, e_fix = np.linalg.norm(dead - TRUTH, axis=1).max(), np.linalg.norm(P - TRUTH, axis=1).max()
    assert e_fix < 0.6 * e_dead, f"loop closure should cut the worst error: {e_dead:.3f} -> {e_fix:.3f}"


def check_gate(gate):
    odo, loop = _edges()
    est = np.cumsum(np.vstack([[0, 0]] + [e[2] for e in odo]), axis=0)
    d2, ok = gate(est, 9, 0, loop[2], 0.08)
    expect = float(np.sum((loop[2] - (est[0] - est[9])) ** 2)) / (10 * 0.08 ** 2)
    assert np.isclose(d2, expect) and bool(ok) == (expect < 5.991), f"d2 = {d2}, expected {expect:.4f}"
    d2b, okb = gate(est, 5, 0, np.array([0.1, -0.2]), 0.08)
    assert not okb and d2b > 100, "a perceptual alias (pose 5 claimed next to pose 0) must be rejected"
