"""ROS 2 Jazzy inside Colab through RoboStack (conda-forge builds of ROS 2).

Why RoboStack: Colab's Python and Ubuntu versions change without notice; a micromamba
environment carries its own Python and ROS 2, so the labs keep working. You write nodes
as files (%%writefile) and run them like you would in a terminal.
"""
from __future__ import annotations

import os
import pathlib
import shlex
import shutil
import signal
import subprocess
import time

from .core import IN_COLAB, ROOT

MM_URL = "https://conda.anaconda.org/conda-forge/linux-64/micromamba-2.10.0-0.tar.bz2"
MM_FALLBACK = "https://micro.mamba.pm/api/micromamba/linux-64/latest"
BASE = ["ros-jazzy-ros-base", "ros-jazzy-tf2-ros", "ros-jazzy-robot-state-publisher",
        "ros-jazzy-rosbag2", "ros-jazzy-example-interfaces",
        "yaml=0.2.5"]   # pin: newer yaml changes the soname that librcl links against
EXTRAS = {
    "build": ["colcon-common-extensions", "compilers", "cmake", "ninja", "pkg-config"],
    "control": ["ros-jazzy-ros2-control", "ros-jazzy-ros2-controllers"],
}
CHANNELS = ["-c", "conda-forge", "-c", "robostack-jazzy"]

_procs: list[subprocess.Popen] = []


def _paths():
    mm = os.environ.get("RDL_MAMBA") or ("/content/mm/bin/micromamba" if IN_COLAB else str(ROOT / ".mm/bin/micromamba"))
    root = os.environ.get("RDL_MAMBA_ROOT") or ("/content/mm/root" if IN_COLAB else str(ROOT / ".mm/root"))
    return pathlib.Path(mm), pathlib.Path(root)


def _env_dir():
    return _paths()[1] / "envs" / "ros"


def _sh(cmd, timeout=1800):
    return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=timeout)


def ensure_ros(extras=()):
    """Create the ROS 2 Jazzy environment once per Colab session (about 3 to 5 minutes)."""
    mm, root = _paths()
    if not mm.exists():
        mm.parent.mkdir(parents=True, exist_ok=True)
        r = _sh(f"cd {mm.parent.parent} && (curl -fsSL {MM_URL} || curl -fsSL {MM_FALLBACK}) | tar -xj bin/micromamba")
        if r.returncode != 0:
            raise RuntimeError("could not download micromamba: " + r.stderr)
    env = _env_dir()
    pkgs = list(BASE)
    for e in extras:
        pkgs += EXTRAS[e]
    if not env.exists():
        print("Creating the ROS 2 Jazzy environment (first ROS lab in this session: 3 to 5 minutes) ...")
        t0 = time.time()
        r = _sh(f"MAMBA_ROOT_PREFIX={root} {mm} create -y -q -n ros {' '.join(CHANNELS)} {' '.join(pkgs)}")
        if r.returncode != 0:
            raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])
        print(f"Done in {time.time() - t0:.0f} s")
    else:
        need = [p for p in pkgs if not list((env / "conda-meta").glob(p.split("=")[0] + "-[0-9]*.json"))]
        if need:
            print("Adding:", " ".join(need))
            r = _sh(f"MAMBA_ROOT_PREFIX={root} {mm} install -y -q -n ros {' '.join(CHANNELS)} {' '.join(need)}")
            if r.returncode != 0:
                raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])
    os.environ.setdefault("ROS_DOMAIN_ID", "7")
    os.environ.setdefault("ROS_AUTOMATIC_DISCOVERY_RANGE", "LOCALHOST")
    return env


def _wrap(cmd: str) -> list[str]:
    mm, root = _paths()
    env = _env_dir()
    inner = f"source {env}/setup.bash 2>/dev/null; {cmd}"
    return ["env", f"MAMBA_ROOT_PREFIX={root}", str(mm), "run", "-n", "ros", "bash", "-c", inner]


def ros(cmd: str, timeout: int = 60, show: bool = True, check: bool = False) -> str:
    """Run a shell command inside the ROS 2 environment and return its output."""
    try:
        r = subprocess.run(_wrap(cmd), capture_output=True, text=True, timeout=timeout)
        out = r.stdout + r.stderr
        if check and r.returncode != 0:
            raise RuntimeError(out[-2000:])
    except subprocess.TimeoutExpired as e:
        so = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        out = so + f"\n[stopped after {timeout} s]"
    if show:
        print(out.rstrip())
    return out


def start(cmd: str, log: str | None = None) -> subprocess.Popen:
    """Start a long-running ROS 2 command in the background (a node, a launch file, a bag)."""
    fh = open(log, "w") if log else subprocess.DEVNULL
    p = subprocess.Popen(_wrap(cmd), stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
    _procs.append(p)
    return p


def stop_all():
    """Stop every background process started with start()."""
    for p in _procs:
        if p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGINT)
            except ProcessLookupError:
                pass
    t0 = time.time()
    for p in _procs:
        try:
            p.wait(timeout=max(0.1, 5 - (time.time() - t0)))
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
    _procs.clear()


def py(script: str, args: str = "", timeout: int = 60, show: bool = True) -> str:
    """Run a Python file with the ROS 2 environment's interpreter."""
    return ros(f"python {shlex.quote(str(script))} {args}", timeout=timeout, show=show)


def run_script(code: str, name: str = "_check.py", timeout: int = 60) -> str:
    """Write a Python script to the work folder and run it inside the ROS 2 environment (used by graders)."""
    path = pathlib.Path(name).resolve()
    path.write_text(code)
    return ros(f"python {path}", timeout=timeout, show=False)


def expect(out: str, at_least: int = 1):
    """Raise AssertionError unless the output has at least `at_least` PASS lines and no FAIL lines."""
    passes = [l for l in out.splitlines() if l.startswith("PASS")]
    fails = [l[5:] for l in out.splitlines() if l.startswith("FAIL")]
    if fails:
        raise AssertionError("; ".join(fails[:5]))
    if len(passes) < at_least:
        raise AssertionError("checker did not finish:\n" + out[-800:])


WS = "ros_ws"


def cpp_prefix() -> str:
    """Shell prefix that sources the workspace your C++ nodes are built into."""
    return f"source {pathlib.Path(WS).resolve()}/install/setup.bash && "


def build_cpp_node(sources, exe: str, deps) -> str:
    """Wrap your .cpp file(s) in a colcon package named rdl_<exe>, build it, and return the command that runs it.

    Used by lab.check("<name>", "your_node.cpp"): the grader then runs your C++ node instead of the Python one.
    """
    ensure_ros(extras=("build",))
    pkg = f"rdl_{exe}"
    root = pathlib.Path(WS).resolve()
    src = root / "src" / pkg
    (src / "src").mkdir(parents=True, exist_ok=True)
    names = []
    for s in sources:
        s = pathlib.Path(s)
        if not s.exists():
            raise AssertionError(f"{s} not found: run its %%writefile cell first")
        shutil.copy(s, src / "src" / s.name)
        if s.suffix in (".cpp", ".cc", ".cxx"):
            names.append(f"src/{s.name}")
    deps = list(deps)
    (src / "package.xml").write_text(
        '<?xml version="1.0"?>\n<package format="3">\n'
        f"  <name>{pkg}</name>\n  <version>0.0.1</version>\n  <description>Student node {exe}</description>\n"
        "  <maintainer email=\"student@example.com\">student</maintainer>\n  <license>GPL-3.0-only</license>\n"
        "  <buildtool_depend>ament_cmake</buildtool_depend>\n"
        + "".join(f"  <depend>{d}</depend>\n" for d in deps)
        + "  <export><build_type>ament_cmake</build_type></export>\n</package>\n")
    (src / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.8)\n"
        f"project({pkg})\nset(CMAKE_CXX_STANDARD 17)\n"
        "add_compile_options(-Wall -Wextra)\nfind_package(ament_cmake REQUIRED)\n"
        + "".join(f"find_package({d} REQUIRED)\n" for d in deps)
        + f"add_executable({exe} {' '.join(names)})\n"
        f"ament_target_dependencies({exe} {' '.join(deps)})\n"
        f"install(TARGETS {exe} DESTINATION lib/${{PROJECT_NAME}})\nament_package()\n")
    out = ros(f"cd {root} && colcon build --packages-select {pkg} --cmake-args -DCMAKE_BUILD_TYPE=Release 2>&1",
              timeout=900, show=False)
    if "Failed" in out or "failed" in out.lower().split("summary")[-1] or "finished" not in out:
        tail = "\n".join(l for l in out.splitlines() if "error" in l.lower() or "Failed" in l)[-2500:] or out[-2500:]
        raise AssertionError(f"colcon build of {pkg} failed:\n{tail}")
    return f"{cpp_prefix()}exec ros2 run {pkg} {exe}"
