import numpy as np

PIP = ["opencv-python-headless"]
ANSWERS = {"M1": 2.4, "M2": 8, "M3": 60}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Exact when all points lie on one plane, or the camera only rotates about its center",
    "That is why the board can be rectified to a top-down view",
    "Off-plane points at different depths show parallax under translation: no single homography fits",
    "Then use 3D methods (depth, stereo, epipolar geometry) or restrict the homography to on-plane features",
]}
HINTS = {
    "homography": "Two rows per point; H = last row of Vt from np.linalg.svd, reshaped, divided by H[2,2].",
    "stereo": "Z = f B / d; guard d <= 0.",
    "convolution": "Flip the kernel in both axes, then sum shifted slices weighted by the kernel.",
}


def check_homography(fn):
    H_true = np.array([[1.2, 0.1, 30], [-0.05, 0.9, 12], [0.0004, -0.0002, 1]])
    rng = np.random.default_rng(1)
    src = rng.uniform(0, 400, (8, 2))
    p = np.c_[src, np.ones(8)] @ H_true.T
    dst = p[:, :2] / p[:, 2:]
    H = fn(src, dst)
    assert np.allclose(H, H_true, atol=1e-6), f"H = {np.round(H, 5)}"
    import cv2
    Hc, _ = cv2.findHomography(src, dst)
    assert np.allclose(H, Hc, atol=1e-5), "should agree with cv2.findHomography"


def check_stereo(fn):
    z = fn([35, 70, 0], 700, 0.12)
    assert abs(z[0] - 2.4) < 1e-12 and abs(z[1] - 1.2) < 1e-12 and np.isinf(z[2])


def check_convolution(fn):
    from scipy.signal import convolve2d
    rng = np.random.default_rng(2)
    img, k = rng.normal(size=(20, 17)), rng.normal(size=(3, 5))
    assert np.allclose(fn(img, k), convolve2d(img, k, mode="valid")), "differs from scipy convolve2d (did you flip the kernel?)"
    assert fn(np.ones((64, 64)), np.ones((5, 5))).shape == (60, 60)
