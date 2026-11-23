import numpy as np

ANSWERS = {"M1": (0.9804, {"abs": 1e-4}), "M2": 1, "M3": 0.6}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Linearization breaks with strong nonlinearity relative to the uncertainty (large errors, angles)",
    "Wrong Jacobians or mistuned Q/R make it overconfident and diverge",
    "Remedies: check Jacobians numerically, wrap angles, good initialization, inflate Q, gate outliers",
    "Use iterated EKF, UKF or particle filter for strong nonlinearity or multimodality",
]}
HINTS = {
    "observability": "Stack H, HF, HF^2, ... (n blocks) and take np.linalg.matrix_rank.",
    "complementary": "alpha = tau / (tau + dt); start from the first accelerometer angle.",
    "ekf": "Predict P += Q; innovation with wrapped bearing; standard update with H from H_jac.",
}


def check_observability(fn):
    F = np.array([[1, 0.1], [0, 1.0]])
    assert fn(F, np.array([[1.0, 0]])) == 2, "position measured: observable"
    assert fn(F, np.array([[0, 1.0]])) == 1, "velocity only: position unobservable"
    F3 = np.array([[1, 0.1, 0.005], [0, 1, 0.1], [0, 0, 1.0]])
    assert fn(F3, np.array([[1.0, 0, 0]])) == 3


def check_complementary(fn):
    rng = np.random.default_rng(5)
    dt, n = 0.01, 3000
    t = np.arange(n) * dt
    true = 0.3 * np.sin(0.5 * t)
    gyro = np.gradient(true, dt) + 0.05 + rng.normal(0, 0.01, n)       # bias 0.05 rad/s
    acc = true + rng.normal(0, 0.05, n)
    est = np.array(fn(gyro, acc, dt, 0.5))
    err = np.sqrt(np.mean((est[500:] - true[500:]) ** 2))
    gyro_only = np.cumsum(gyro) * dt + acc[0]
    assert err < 0.035, f"RMS error {err:.4f} rad"
    assert err < np.sqrt(np.mean((acc - true) ** 2)) and abs(gyro_only[-1] - true[-1]) > 1.0, "should beat both sensors"


def check_ekf(Hj, step):
    x, lm = np.array([1.0, -2.0]), np.array([4.0, 2.0])
    num = np.zeros((2, 2))
    hm = lambda p: np.array([np.hypot(lm[0] - p[0], lm[1] - p[1]), np.arctan2(lm[1] - p[1], lm[0] - p[0])])
    for j in range(2):
        e = np.zeros(2)
        e[j] = 1e-6
        num[:, j] = (hm(x + e) - hm(x)) / 1e-6
    assert np.allclose(Hj(x, lm), num, atol=1e-4), f"Jacobian {Hj(x, lm)} vs numerical {num}"
    rng = np.random.default_rng(1)
    true = np.array([2.0, 1.0])
    lms = [np.array([5.0, 5.0]), np.array([-3.0, 4.0]), np.array([0.0, -4.0])]
    xe, P = np.array([0.0, 0.0]), np.eye(2) * 4.0
    Q, R = np.eye(2) * 1e-4, np.diag([0.05 ** 2, 0.02 ** 2])
    for k in range(60):
        lmk = lms[k % 3]
        dx, dy = lmk - true
        z = np.array([np.hypot(dx, dy) + rng.normal(0, 0.05), np.arctan2(dy, dx) + rng.normal(0, 0.02)])
        xe, P = step(xe, P, z, lmk, Q, R)
    assert np.linalg.norm(xe - true) < 0.1, f"EKF ended at {np.round(xe, 3)}, truth {true}"
    assert np.all(np.linalg.eigvalsh(P) > 0), "P must stay positive definite"
