import numpy as np

ANSWERS = {"M1": (0.075, {"abs": 1e-4}), "M2": (0.55, {"abs": 1e-4}), "M3": 2}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Lambda trades accuracy for bounded joint speed",
    "Too small: pseudo-inverse behavior, huge joint velocities near singularities",
    "Too large: slow convergence and steady tracking error",
    "Real controllers adapt lambda to the smallest singular value or manipulability and clamp joint speed",
]}
HINTS = {
    "fk": "Sum of two rotated links; differentiate x and y by q1 and q2 for J.",
    "ik": "c2 from the law of cosines; q2 = -arccos(c2) for elbow up; q1 = atan2(y, x) - atan2(l2 s2, l1 + l2 c2).",
    "dls": "dq = J.T @ solve(J @ J.T + lam^2 I, e).",
}


def check_fk(fk, jac):
    assert np.allclose(fk([0, 0]), [0.55, 0]) and np.allclose(fk([np.pi / 2, -np.pi / 2]), [0.25, 0.30])
    rng = np.random.default_rng(0)
    for _ in range(20):
        q = rng.uniform(-np.pi, np.pi, 2)
        Jn = np.column_stack([(np.asarray(fk(q + d)) - np.asarray(fk(q - d))) / 2e-6 for d in np.eye(2) * 1e-6])
        assert np.allclose(jac(q), Jn, atol=1e-6), "analytic Jacobian differs from finite differences"
        assert np.isclose(np.linalg.det(jac(q)), 0.3 * 0.25 * np.sin(q[1])), "det J should be l1 l2 sin q2"


def check_ik(ik, fk):
    rng = np.random.default_rng(1)
    for _ in range(30):
        r, a = rng.uniform(0.07, 0.54), rng.uniform(-np.pi, np.pi)
        p = np.array([r * np.cos(a), r * np.sin(a)])
        up, down = ik(*p, elbow_up=True), ik(*p, elbow_up=False)
        assert np.allclose(fk(up), p, atol=1e-9) and np.allclose(fk(down), p, atol=1e-9), f"ik misses {p}"
        assert up[1] < 0 < down[1], "elbow up: q2 < 0, elbow down: q2 > 0"
    assert ik(0.6, 0.0) is None and ik(0.01, 0.0) is None, "unreachable points return None"


def check_dls(step, fk, jac):
    q = np.array([0.3, 1.2])
    target = np.array([0.1, 0.4])
    for _ in range(200):
        q = step(q, target, 0.05)
    assert np.linalg.norm(fk(q) - target) < 1e-4, f"did not converge: error {np.linalg.norm(fk(q) - target):.2e}"
    for q0 in ([0.0, 1e-3], [0.5, -1.0]):
        q = np.array(q0)
        for _ in range(200):
            e = np.linalg.norm(np.array([0.7, 0.0]) - np.asarray(fk(q)))
            q2 = np.asarray(step(q, [0.7, 0.0], 0.1), float)
            assert np.linalg.norm(q2 - q) <= e / (2 * 0.1) + 1e-9, "a damped step can never exceed |e| / (2 lambda)"
            q = q2
        assert np.linalg.norm(np.asarray(fk(q)) - [0.55, 0]) < 1e-3, "for an unreachable target the arm should stretch toward it"
