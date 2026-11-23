import numpy as np

ANSWERS = {"M1": 0.8, "M2": 0.8, "M3": 0.8}
CHOICES = {"K1": "a"}
RUBRIC = {"K2": [
    "R from recorded still data (and quantization), not guesses",
    "Q from expected unmodeled acceleration, then adjusted",
    "Check innovations are zero-mean and white, NIS near the measurement dimension",
    "Trade smoothness vs lag for the consuming controller; tune offline with recorded bags",
]}
HINTS = {"kalman": "predict: x = F x, P = F P F^T + Q. update: y, S, K = P H^T S^-1, x += K y, P = (I - K H) P."}


def _sim(seed, n=2000, dt=0.01, q=4.0, r=0.05 ** 2):
    rng = np.random.default_rng(seed)
    p = v = 0.0
    t, z = [], []
    for _ in range(n):
        v += rng.normal(0, np.sqrt(q * dt))
        p += v * dt
        t.append(p)
        z.append(p + rng.normal(0, np.sqrt(r)))
    return np.array(t), np.array(z)


def check_kalman(cls):
    k = cls(0.1, 1.0, 1.0, p0=4.0)
    k.P = np.diag([4.0, 0.0])
    k.update(5.0)
    assert np.allclose(k.x[0], 4.0) and np.allclose(k.P[0, 0], 0.8), "scalar check: P=4, R=1, z=5 -> x=4, P=0.8"
    truth, z = _sim(3)
    kf = cls(0.01, 4.0, 0.05 ** 2)
    est, nis = [], []
    for zk in z:
        kf.predict()
        kf.update(zk)
        est.append(kf.x[0])
        nis.append(float(kf.y @ np.linalg.inv(kf.S) @ kf.y))
    est = np.array(est)
    raw_rms = np.sqrt(np.mean((z - truth) ** 2))
    kf_rms = np.sqrt(np.mean((est[200:] - truth[200:]) ** 2))
    assert kf_rms < 0.6 * raw_rms, f"filter RMS {kf_rms:.4f} vs raw {raw_rms:.4f}"
    m = np.mean(nis[200:])
    assert 0.8 < m < 1.25, f"average NIS {m:.2f} should be near 1 for a correctly tuned filter"
