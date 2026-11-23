import numpy as np

ANSWERS = {"M1": (1.618, {"abs": 1e-3}), "M2": (0.382, {"abs": 1e-3}), "M3": 20}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Every sample: measure, solve the N-step constrained problem, apply only the first input, repeat",
    "Re-solving gives feedback against model error and disturbances; the horizon anticipates limits",
    "Higher Q versus R: faster, more aggressive, larger inputs, more saturation and noise",
    "Higher R: gentler, slower, more efficient motion",
]}
HINTS = {
    "lqr": "P = solve_discrete_are(A, B, Q, R); K = solve(R + B'PB, B'PA).",
    "mpc": "Block (i, j) of Su is A^(i-j) B for j <= i; whiten with Cholesky factors and call lsq_linear with bounds.",
}
DT = 0.1
A = np.array([[1.0, DT], [0.0, 1.0]])
B = np.array([[0.5 * DT ** 2], [DT]])


def check_lqr(dlqr):
    Q, R = np.diag([10.0, 1.0]), np.array([[0.1]])
    K, P = dlqr(A, B, Q, R)
    K, P = np.atleast_2d(K), np.atleast_2d(P)
    ric = Q + A.T @ P @ A - A.T @ P @ B @ np.linalg.solve(R + B.T @ P @ B, B.T @ P @ A)
    assert np.allclose(P, ric, atol=1e-8), "P does not satisfy the DARE"
    assert np.allclose(K, np.linalg.solve(R + B.T @ P @ B, B.T @ P @ A)), "K does not match P"
    assert np.max(np.abs(np.linalg.eigvals(A - B @ K))) < 1, "closed loop must be stable"
    k1, p1 = dlqr(np.eye(1), np.eye(1), np.eye(1), np.eye(1))
    assert np.isclose(np.ravel(p1)[0], (1 + 5 ** 0.5) / 2), "scalar case: P is the golden ratio"


def _cost(U, x0, Q, R):
    x, J = np.asarray(x0, float), 0.0
    for u in U:
        x = A @ x + B[:, 0] * u
        J += x @ Q @ x + R[0, 0] * u * u
    return J


def check_mpc(prediction, solve):
    Sx, Su = prediction(A, B, 5)
    rng = np.random.default_rng(0)
    x0, U = rng.normal(size=2), rng.normal(size=5)
    x, X = x0.copy(), []
    for u in U:
        x = A @ x + B[:, 0] * u
        X.append(x)
    assert np.allclose(Sx @ x0 + Su @ U, np.concatenate(X)), "prediction matrices disagree with simulation"
    Q, R = np.diag([10.0, 1.0]), np.array([[0.1]])
    x0 = np.array([2.0, 0.0])
    Ustar = np.asarray(solve(x0, A, B, Q, R, 20, 1.0), float).ravel()
    assert Ustar.shape == (20,) and np.all(np.abs(Ustar) <= 1 + 1e-6), "20 inputs within the bound"
    J = _cost(Ustar, x0, Q, R)
    for _ in range(300):
        Up = np.clip(Ustar + rng.normal(0, 0.05, 20), -1, 1)
        assert _cost(Up, x0, Q, R) >= J - 1e-7, "a feasible perturbation lowered the cost: not optimal"
    x = x0.copy()
    for _ in range(80):
        u = np.asarray(solve(x, A, B, Q, R, 20, 1.0)).ravel()[0]
        x = A @ x + B[:, 0] * u
    assert np.linalg.norm(x) < 0.02, f"closed loop should settle at the origin, ended at {x}"
