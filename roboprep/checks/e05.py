import numpy as np

ANSWERS = {"M1": 9, "M2": 2}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Joint velocity: nearly linear, unimodal: KF/EKF is cheapest and fits an MCU loop",
    "Global localization is multimodal: Gaussian filters lock onto one hypothesis",
    "Particle filter (AMCL) keeps several hypotheses at higher compute cost",
    "UKF handles stronger nonlinearity without Jacobians but is still unimodal",
]}
HINTS = {
    "unscented": "L = cholesky((n + lam) P); points mu, mu + rows of L^T, mu - rows of L^T.",
    "particles": "Systematic: pointers (u + arange(N)) / N into the cumulative weights with searchsorted.",
}


def check_unscented(sp, ut):
    mu, P = np.array([1.0, 2.0]), np.array([[0.5, 0.1], [0.1, 0.3]])
    X, Wm, Wc = sp(mu, P, alpha=0.5)
    assert X.shape == (5, 2) and abs(Wm.sum() - 1) < 1e-12, "5 points, mean weights sum to 1"
    A, b = np.array([[2.0, -1.0], [0.5, 3.0]]), np.array([0.3, -0.7])
    m, C = ut(lambda x: A @ x + b, mu, P, alpha=0.5)
    assert np.allclose(m, A @ mu + b) and np.allclose(C, A @ P @ A.T), "linear function must be exact"
    mu2, P2 = np.array([1.0, 0.6]), np.diag([0.01, 0.2])
    polar = lambda x: np.array([x[0] * np.cos(x[1]), x[0] * np.sin(x[1])])
    m2, _ = ut(polar, mu2, P2, alpha=1.0, beta=2.0, kappa=1.0)
    rng = np.random.default_rng(0)
    s = rng.multivariate_normal(mu2, P2, 200000)
    mc = np.mean(np.c_[s[:, 0] * np.cos(s[:, 1]), s[:, 0] * np.sin(s[:, 1])], axis=0)
    lin = polar(mu2)
    assert np.linalg.norm(m2 - mc) < 0.5 * np.linalg.norm(lin - mc), "UT mean should beat plain linearization"


def check_particles(predict, weights, resample, neff):
    assert abs(neff([0.5, 0.5, 0, 0]) - 2) < 1e-12 and abs(neff([0.25] * 4) - 4) < 1e-12
    rng = np.random.default_rng(0)
    r = resample(np.arange(4.0), np.array([0.0, 1.0, 0.0, 0.0]), rng)
    assert np.all(r == 1.0), "all weight on particle 1"
    rng = np.random.default_rng(42)
    doors = np.array([2.0, 6.0, 13.0])
    x = 0.5
    p = rng.uniform(0, 20, 2000)
    for _ in range(112):
        x += 0.125 + rng.normal(0, 0.02)
        p = predict(p, 0.125, 0.03, rng)
        near = np.min(np.abs(x - doors)) <= 0.5
        z = int(rng.random() < (0.9 if near else 0.1))
        w = weights(p, z)
        assert abs(w.sum() - 1) < 1e-9, "weights must be normalized"
        p = resample(p, w, rng)
    assert abs(np.mean(p) - x) < 0.6 and np.std(p) < 0.6, f"estimate {np.mean(p):.2f} +- {np.std(p):.2f}, truth {x:.2f}"
