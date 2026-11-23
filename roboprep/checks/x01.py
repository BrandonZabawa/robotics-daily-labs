import numpy as np

ANSWERS = {"M1": 64, "M2": 4, "M3": (0.007843, {"abs": 1e-5})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Rounding has zero or undefined derivative, so no gradient flows",
    "STE: quantized value forward, identity gradient backward (inside the range)",
    "QAT trains while experiencing the real rounding and clipping noise",
    "Weights and ranges adapt to where quantization hurts less; PTQ rounds a model that never adapted",
]}
HINTS = {
    "affine": "scale = (max - min) / (2^b - 1); zero point = round(-min / scale), clipped.",
    "granularity": "Per channel: max(abs(W), axis=1, keepdims=True) / 127.",
    "ste": "return x + (fq - x).detach()",
}


def check_affine(params, quantize, dequantize):
    s, z = params(-0.5, 1.5)
    assert np.isclose(s, 2 / 255) and z == 64, f"(scale, zero point) = ({s}, {z})"
    s2, z2 = params(0.2, 1.0)
    assert z2 == 0 and np.isclose(s2, 1 / 255), "range must be extended to include 0"
    x = np.linspace(-0.5, 1.5, 1001)
    q = quantize(x, s, z)
    assert q.min() >= 0 and q.max() <= 255 and quantize([0.0], s, z)[0] == 64, "0.0 must map exactly to the zero point"
    assert np.max(np.abs(dequantize(q, s, z) - x)) <= s / 2 + 1e-12, "round-trip error must stay within half a step"
    assert quantize([10.0], s, z)[0] == 255 and quantize([-10.0], s, z)[0] == 0, "clip out-of-range values"


def check_granularity(per_tensor, per_channel):
    rng = np.random.default_rng(0)
    W = rng.normal(size=(8, 64)) * np.logspace(-3, 0, 8)[:, None]
    et, ec = np.abs(per_tensor(W) - W), np.abs(per_channel(W) - W)
    assert et.max() <= np.abs(W).max() / 254 + 1e-12, "per-tensor error must be within half a step"
    assert np.all(ec.max(axis=1) <= np.abs(W).max(axis=1) / 254 + 1e-12), "per-channel error within each row's half step"
    assert ec[0].mean() < 0.05 * et[0].mean() + 1e-15, "the smallest row should be far better with per-channel scales"
    Z = W.copy()
    Z[3] = 0
    assert np.all(np.isfinite(per_channel(Z))) and np.allclose(per_channel(Z)[3], 0), "an all-zero row must not divide by zero"


def check_ste(fq):
    import torch
    x = torch.linspace(-0.4, 1.4, 50, requires_grad=True)
    y = fq(x, 2 / 255, 64)
    ref = (2 / 255) * (torch.clamp(torch.round(x.detach() / (2 / 255)) + 64, 0, 255) - 64)
    assert torch.allclose(y.detach(), ref, atol=1e-6), "forward must equal quantize-dequantize"
    y.sum().backward()
    assert torch.allclose(x.grad, torch.ones_like(x)), "gradient must pass straight through (1) inside the range"
