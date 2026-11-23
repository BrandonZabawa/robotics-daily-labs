import numpy as np

ANSWERS = {"M1": (0.75, {"abs": 1e-4}), "M2": (0.9375, {"abs": 1e-4}), "M3": (1.5, {"abs": 1e-4})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Path = where (collision-free); timing = how fast under velocity, acceleration, torque, jerk limits",
    "Separation keeps problems small; retime for payload or speed override without replanning",
    "Cubic: acceleration jumps at the ends (infinite jerk), exciting backlash and resonance",
    "Quintic: zero acceleration at the ends, smooth current, slightly higher peak velocity",
]}
HINTS = {
    "rrt": "Closest point on a segment: t = clip(dot(c - p, d) / dot(d, d), 0, 1).",
    "scaling": "Differentiate s(tau) by t: divide by T once for velocity and T^2 for acceleration.",
}
CIRCLES = [(0.5, 0.5, 0.2), (0.25, 0.8, 0.12), (0.75, 0.2, 0.15)]


def check_rrt(free, rrt):
    c = [(0.5, 0.5, 0.2)]
    assert not free((0.0, 0.5), (1.0, 0.5), c), "segment through the circle"
    assert free((0.0, 0.0), (1.0, 0.0), c), "segment far from the circle"
    assert not free((0.25, 0.3), (0.75, 0.3), [(0.5, 0.5, 0.21)]), "segment grazing inside the radius"
    assert free((0.2, 0.2), (0.25, 0.25), c) and not free((0.5, 0.5), (0.5, 0.5), c), "degenerate segments"
    for seed in range(5):
        path = rrt((0.05, 0.05), (0.95, 0.95), CIRCLES, rng=np.random.default_rng(seed))
        assert path is not None, f"seed {seed}: no path"
        path = [np.asarray(p, float) for p in path]
        assert np.allclose(path[0], (0.05, 0.05)) and np.allclose(path[-1], (0.95, 0.95)), "path endpoints"
        for a, b in zip(path, path[1:]):
            assert np.linalg.norm(b - a) <= 0.05 + 1e-9, "each edge at most one step long"
            assert free(a, b, CIRCLES), "edge collides"


def check_scaling(cubic, quintic, tmin):
    T, t = 2.0, np.linspace(0, 2.0, 2001)
    s, sd = cubic(T, t)
    assert np.isclose(s[0], 0) and np.isclose(s[-1], 1) and np.isclose(sd[0], 0) and np.isclose(sd[-1], 0)
    assert np.isclose(sd.max(), 0.75) and np.allclose(np.gradient(s, t)[1:-1], sd[1:-1], atol=1e-3), "cubic velocity"
    s, sd, sdd = quintic(T, t)
    assert np.isclose(s[-1], 1) and np.isclose(sdd[0], 0) and np.isclose(sdd[-1], 0), "quintic boundary conditions"
    assert np.isclose(sd.max(), 0.9375) and np.allclose(np.gradient(sd, t)[1:-1], sdd[1:-1], atol=1e-3), "quintic derivatives"
    assert np.isclose(tmin(1.0, 1.0, 6.0), 1.5) and np.isclose(tmin(1.0, 10.0, 1.0), np.sqrt(6)), "duration limits"
