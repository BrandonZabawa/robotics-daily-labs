import numpy as np

ANSWERS = {"M1": [2, 1, 0], "M2": 0.5, "M3": 1}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "At pitch 90 degrees the first and third Euler axes align: yaw and roll describe the same motion",
    "Near the singularity derivatives blow up and filters/controllers misbehave",
    "Quaternions and matrices have no singularity, compose by multiplication, interpolate smoothly",
    "So computation uses them; Euler angles only for display",
]}
HINTS = {
    "transforms": "inverse: [R^T, -R^T p; 0 1].",
    "quaternions": "q = (u sin(t/2), cos(t/2)); Hamilton product formula in the map.",
    "euler": "pitch = asin(-R[2,0]), yaw = atan2(R[1,0], R[0,0]), roll = atan2(R[2,1], R[2,2]).",
}


def _rz(t):
    c, s = np.cos(t), np.sin(t)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def check_transforms(make_T, inv_T, apply):
    T = make_T(_rz(np.pi / 2), [2, 0, 0])
    assert np.allclose(apply(T, [1, 0, 0]), [2, 1, 0]), "point mapping"
    rng = np.random.default_rng(0)
    for _ in range(5):
        A = make_T(_rz(rng.uniform(-3, 3)), rng.normal(size=3))
        assert np.allclose(inv_T(A) @ A, np.eye(4)), "inv_T(T) @ T must be identity"


def check_quaternions(qaa, qmul, q2R):
    q = qaa([0, 0, 1], np.pi / 2)
    assert np.allclose(q, [0, 0, np.sqrt(0.5), np.sqrt(0.5)]), f"90 deg about z: {q}"
    assert np.allclose(q2R(q), _rz(np.pi / 2)), "quat_to_R vs rot_z"
    rng = np.random.default_rng(1)
    for _ in range(5):
        a, b = qaa(rng.normal(size=3), rng.uniform(-3, 3)), qaa(rng.normal(size=3), rng.uniform(-3, 3))
        assert np.allclose(q2R(qmul(a, b)), q2R(a) @ q2R(b)), "R(a*b) must equal R(a) R(b)"
    assert np.allclose(q2R(-q), q2R(q)), "q and -q are the same rotation"


def check_euler(eul, q2R):
    rng = np.random.default_rng(2)
    for _ in range(10):
        y, p, r = rng.uniform(-3, 3), rng.uniform(-1.4, 1.4), rng.uniform(-3, 3)
        Ry = np.array([[np.cos(p), 0, np.sin(p)], [0, 1, 0], [-np.sin(p), 0, np.cos(p)]])
        Rx = np.array([[1, 0, 0], [0, np.cos(r), -np.sin(r)], [0, np.sin(r), np.cos(r)]])
        got = eul(_rz(y) @ Ry @ Rx)
        assert np.allclose(got, (y, p, r)), f"round trip ({y:.2f}, {p:.2f}, {r:.2f}) -> {np.round(got, 2)}"
