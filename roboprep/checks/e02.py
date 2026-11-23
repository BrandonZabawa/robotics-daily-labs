import numpy as np

ANSWERS = {"M1": 6, "M2": 2.5}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Gauss-Newton can overshoot or diverge far from the solution or when J^T J is ill-conditioned",
    "Levenberg-Marquardt adds damping (lambda I), moving between gradient descent and Gauss-Newton",
    "Validate: residual RMS near sensor noise, well-conditioned J^T J, plausible parameters",
    "Test on held-out orientations that the corrected magnitude is g",
]}
HINTS = {
    "solver": "J[:, j] = (r(x + h e_j) - r(x)) / h; step = solve(J^T J, -J^T r).",
    "accel": "Residual: norm of (raw - b) * s along axis 1, minus g.",
}


def check_solver(jac, gn):
    f = lambda x: np.array([x[0] ** 2 + x[1] - 3, x[0] - x[1] ** 2 + 1])
    J = jac(f, np.array([1.0, 2.0]))
    assert np.allclose(J, [[2, 1], [1, -4]], atol=1e-4), f"numerical Jacobian {J}"
    x = gn(lambda x: np.array([x[0] ** 2 - 4]), [1.0], iters=1)
    assert abs(x[0] - 2.5) < 1e-4, f"one step from 1 -> {x}"
    x = gn(f, [1.0, 1.0])
    assert np.allclose(f(x), 0, atol=1e-8), f"did not converge: {x}, residual {f(x)}"


def check_accel(fn):
    rng = np.random.default_rng(7)
    s_true, b_true = np.array([1.02, 0.97, 1.01]), np.array([0.15, -0.20, 0.30])
    dirs = rng.normal(size=(30, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    raw = dirs * 9.80665 / s_true + b_true + rng.normal(0, 0.005, (30, 3))
    s, b = fn(raw)
    assert np.allclose(s, s_true, atol=3e-3) and np.allclose(b, b_true, atol=1e-2), f"scale {np.round(s, 4)}, bias {np.round(b, 3)}"
