import numpy as np

PIP = ["opencv-python-headless"]
ANSWERS = {"M1": 380, "M2": (3.536, {"abs": 1e-3}), "M3": (56.1, {"abs": 0.05})}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Calibration errors (focal length, principal point, distortion)",
    "Corner noise, occlusion, few or poorly spread points, near-degenerate geometry",
    "Use many corners or tags with sub-pixel refinement, good calibration, undistortion",
    "Check reprojection error, reject outliers (RANSAC), filter the static board pose over time",
]}
HINTS = {
    "projection": "Xc = R X + t, then K Xc, then divide by the third coordinate.",
    "pnp": "ok, rvec, tvec = cv2.solvePnP(board, uv, K, None); R = cv2.Rodrigues(rvec)[0].",
}
K = np.array([[600.0, 0, 320], [0, 600.0, 240], [0, 0, 1]])


def _rot(rx, ry, rz):
    cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
    return (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
            @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]))


def check_projection(project, rms):
    uv = project(K, np.eye(3), np.zeros(3), np.array([[0.1, 0.0, 1.0], [0.0, -0.2, 2.0]]))
    assert np.allclose(uv, [[380, 240], [320, 180]]), f"projection {uv}"
    X = np.array([[0.0, 0, 1], [0.1, 0, 1]])
    meas = project(K, np.eye(3), np.zeros(3), X) + np.array([[3.0, 0], [0, 4.0]])
    assert abs(rms(K, np.eye(3), np.zeros(3), X, meas) - np.sqrt(12.5)) < 1e-9


def check_pnp(pose, project):
    g = np.mgrid[0:7, 0:7].reshape(2, -1).T * 0.05
    board = np.c_[g, np.zeros(len(g))]
    R_true, t_true = _rot(0.4, -0.3, 0.2), np.array([-0.15, -0.1, 0.6])
    rng = np.random.default_rng(0)
    uv = project(K, R_true, t_true, board) + rng.normal(0, 0.2, (len(board), 2))
    R, t = pose(K, board, uv)
    assert np.allclose(R, R_true, atol=5e-3) and np.allclose(t, t_true, atol=5e-3), f"t = {np.round(t, 4)} vs {t_true}"
