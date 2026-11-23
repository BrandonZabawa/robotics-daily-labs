import numpy as np

ANSWERS = {"M1": (0.2, {"abs": 1e-6}), "M2": (0.4551, {"abs": 1e-3}), "M3": 100}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Demos never leave the lane, so the data has no examples of what to do with lateral or heading error",
    "A disturbance leads to unseen states, wrong actions, growing error (compounding)",
    "DAgger labels the states the learner actually visits, so one round reaches expert-level error",
    "Chunking makes fewer decisions per horizon; temporal ensembling smooths overlapping chunks",
]}
HINTS = {
    "bc": "Sequential(Linear(3,32), Tanh(), Linear(32,32), Tanh(), Linear(32,1)); Adam; loop zero_grad, loss, backward, step.",
    "dagger": "new = vstack of rollout(policy, ph, noise, rng=rng); labels = expert(new).",
    "ensemble": "w = exp(-m * arange(n)); w /= w.sum(); weighted sum over the first axis.",
}
DT, V = 0.05, 1.0


def _kappa(t, ph):
    return 0.5 * np.sin(0.5 * t + ph)


def _expert(o):
    o = np.atleast_2d(o)
    return np.clip(V * o[:, 2] - 2.0 * o[:, 0] - 2.5 * o[:, 1], -2, 2)[:, None]


def _rollout(policy, ph, noise=0.0, steps=200, rng=None):
    e, psi, obs = 0.0, 0.0, []
    for k in range(steps):
        o = np.array([e, psi, _kappa(k * DT, ph)])
        obs.append(o)
        u = float(np.clip(np.ravel(policy(o))[0], -2, 2))
        e += V * np.sin(psi) * DT
        psi += (u - V * o[2]) * DT + (rng.normal(0, noise) if noise else 0.0)
    return np.array(obs)


def _policy(model):
    import torch
    return lambda o: model(torch.tensor(o, dtype=torch.float32)[None])[0].detach().numpy()


def _lane_error(policy, n=8, seed=1):
    r = np.random.default_rng(seed)
    return np.mean([np.mean(np.abs(_rollout(policy, ph, 0.03, rng=r)[:, 0])) for ph in r.uniform(0, 2 * np.pi, n)])


def _demos():
    rng = np.random.default_rng(0)
    X = np.vstack([_rollout(lambda o: _expert(o)[0], ph) for ph in rng.uniform(0, 2 * np.pi, 5)])
    return X, _expert(X)


def check_bc(train):
    import torch
    X, Y = _demos()
    model = train(X, Y, 400, 0)
    with torch.no_grad():
        out = model(torch.tensor(X, dtype=torch.float32)).numpy()
    assert out.shape == (len(X), 1), f"model output shape {out.shape}, expected ({len(X)}, 1)"
    mse = float(np.mean((out - Y) ** 2))
    assert mse < 1e-3, f"training mean squared error {mse:.2e} is too high"


def check_dagger(dagger_round, train):
    X, Y = _demos()
    rng = np.random.default_rng(5)
    model = train(X, Y, 400, 0)
    phases = rng.uniform(0, 2 * np.pi, 4)
    X2, Y2 = dagger_round(_policy(model), X, Y, phases, np.random.default_rng(7), 0.03)
    assert X2.shape == (len(X) + 800, 3) and Y2.shape == (len(X) + 800, 1), f"shapes {X2.shape}, {Y2.shape}"
    assert np.allclose(X2[:len(X)], X), "keep the old rows first"
    assert np.allclose(Y2[len(X):], _expert(X2[len(X):])), "new rows must be labeled by the expert"
    for k, ph in enumerate(phases):
        assert np.allclose(X2[len(X) + 200 * k], [0, 0, _kappa(0, ph)]), "each rollout starts on the lane at its phase"
    for _ in range(2):
        model = train(X2, Y2, 400, 0)
        X2, Y2 = dagger_round(_policy(model), X2, Y2, rng.uniform(0, 2 * np.pi, 4), rng, 0.03)
    model = train(X2, Y2, 400, 0)
    err = _lane_error(_policy(model))
    assert err < 0.1, f"after DAgger the lane error is {err:.3f} m (expert is about 0.034)"


def check_ensemble(te):
    p = [np.array([1.0, 0.0]), np.array([0.0, 1.0]), np.array([2.0, 2.0]), np.array([-1.0, 4.0])]
    w = np.exp(-0.5 * np.arange(4))
    w /= w.sum()
    assert np.allclose(te(p, 0.5), w @ np.array(p)), "weights exp(-m i), i = 0 oldest, normalized"
    assert np.allclose(te([np.array([3.0])], 0.5), [3.0]) and np.allclose(te(p, 0.0), np.mean(p, axis=0))
