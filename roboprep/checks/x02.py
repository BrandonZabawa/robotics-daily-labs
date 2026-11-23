import numpy as np

ANSWERS = {"M1": 231211008, "M2": 1000, "M3": (0.1, {"abs": 1e-9})}
CHOICES = {"K1": "a"}
RUBRIC = {"K2": [
    "Batch 1: in a feedback loop latency matters, not throughput",
    "Batch 8 waits to collect frames plus long processing: image over 100 ms old, phase lag",
    "Batch 1 at about 17 ms fits a 33 ms (30 Hz) budget with margin",
    "Batching suits offline or many independent streams",
]}
HINTS = {
    "macs": "Inside the hook: out.shape[2] * out.shape[3] for convolutions; skip modules that are not Conv2d or Linear.",
    "roofline": "Bytes moved: every element of A, B and C once, times bytes per element.",
    "energy": "Joules = watts x seconds; divide by the batch for per-inference energy.",
}


def check_macs(conv, lin, model_macs):
    import torch
    assert conv(64, 64, 3, 56, 56) == 115605504 and conv(32, 32, 3, 16, 16, groups=32) == 73728
    assert lin(512, 10) == 5120
    net = torch.nn.Sequential(
        torch.nn.Conv2d(3, 16, 3, padding=1), torch.nn.ReLU(),
        torch.nn.Conv2d(16, 32, 3, stride=2, padding=1), torch.nn.ReLU(),
        torch.nn.Conv2d(32, 32, 3, padding=1, groups=32), torch.nn.Flatten(),
        torch.nn.Linear(32 * 16 * 16, 10))
    got = model_macs(net, (1, 3, 32, 32))
    assert got == 1777664, f"model_macs = {got:,}, expected 1,777,664"


def check_roofline(intensity, attainable):
    assert np.isclose(intensity(4096, 1, 4096, 2), 2 * 4096 * 4096 / (2 * (4096 * 4096 + 2 * 4096)))
    assert np.isclose(intensity(1024, 1024, 1024, 4), 2 * 1024 ** 3 / (4 * 3 * 1024 ** 2))
    assert attainable(2000, 100, 10) == 1000 and attainable(2000, 100, 50) == 2000


def check_energy(tp, energy):
    assert np.isclose(tp(8, 0.0667), 8 / 0.0667) and np.isclose(energy(5, 0.02), 0.1) and np.isclose(energy(10, 0.08, 8), 0.1)
