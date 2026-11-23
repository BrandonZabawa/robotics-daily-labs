"""C helpers: compile your files with a hidden test harness, run, and parse PASS/FAIL lines.

Also installs the Arm bare-metal toolchain and QEMU for the Cortex-M labs.
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess

from .core import ROOT, IN_COLAB

CDIR = ROOT / "roboprep" / "c"
TESTS = ROOT / "roboprep" / "checks" / "c"


def sh(cmd: str, timeout: int = 120, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=timeout, cwd=cwd)


class CResult:
    def __init__(self, ok, output, passes, fails, stage):
        self.ok, self.output, self.passes, self.fails, self.stage = ok, output, passes, fails, stage

    def require(self, expect_at_least: int = 1):
        if self.stage == "compile":
            raise AssertionError("compile error:\n" + self.output[-1500:])
        if self.stage == "timeout":
            raise AssertionError("timed out (infinite loop or deadlock?)")
        if self.fails:
            raise AssertionError("failed: " + "; ".join(self.fails[:6]))
        if len(self.passes) < expect_at_least:
            raise AssertionError("tests did not run to the end:\n" + self.output[-800:])
        return self


def run_ctest(sources, test_file: str, flags: str = "", sanitize: bool = True, timeout: int = 30,
              extra_sources=(), run_args: str = "") -> CResult:
    """Compile your sources plus roboprep/checks/c/<test_file>, run, collect PASS/FAIL lines."""
    srcs = " ".join(str(pathlib.Path(s).resolve()) for s in sources)
    extra = " ".join(str(TESTS / s) for s in extra_sources)
    san = "-fsanitize=address,undefined -fno-sanitize-recover=undefined" if sanitize else ""
    exe = pathlib.Path("ctest_bin").resolve()
    cmd = (f"gcc -std=c11 -O1 -g -Wall -Wextra {san} -I{CDIR} -I. {flags} "
           f"{srcs} {extra} {TESTS / test_file} -o {exe} -lm -lpthread")
    r = sh(cmd)
    if r.returncode != 0:
        return CResult(False, r.stdout + r.stderr, [], [], "compile")
    try:
        r = sh(f"{exe} {run_args}", timeout=timeout)
    except subprocess.TimeoutExpired:
        return CResult(False, "", [], [], "timeout")
    out = r.stdout + r.stderr
    passes = re.findall(r"^PASS (.+)$", out, re.M)
    fails = re.findall(r"^FAIL (.+)$", out, re.M)
    if r.returncode != 0 and not fails:
        fails = [f"exit code {r.returncode}: {out[-600:]}"]
    return CResult(not fails, out, passes, fails, "run")


def compile_run(source: str, flags: str = "-O2", args: str = "", timeout: int = 60) -> str:
    """Compile one file and return its stdout (for experiments, not grading)."""
    exe = pathlib.Path(source).with_suffix("").resolve()
    r = sh(f"gcc -std=c11 -Wall -Wextra {flags} -I{CDIR} {source} -o {exe} -lm -lpthread")
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return sh(f"{exe} {args}", timeout=timeout).stdout


def ensure_arm():
    """arm-none-eabi-gcc and qemu-system-arm (about 1 minute the first time in a Colab session)."""
    if shutil.which("arm-none-eabi-gcc") and shutil.which("qemu-system-arm"):
        return
    print("Installing the Arm toolchain and QEMU ...")
    r = sh("sudo -n true 2>/dev/null && S=sudo || S=; export DEBIAN_FRONTEND=noninteractive; "
           "$S apt-get update -qq && $S apt-get install -y -qq gcc-arm-none-eabi libnewlib-arm-none-eabi "
           "qemu-system-arm > /tmp/arm_apt.log 2>&1", timeout=600)
    if r.returncode != 0:
        raise RuntimeError("apt install failed; see /tmp/arm_apt.log")


ARM_FLAGS = "-mcpu=cortex-m3 -mthumb -O1 -g -ffreestanding -nostdlib -fno-tree-loop-distribute-patterns -Wall"


def arm_build(sources, linker_script: str, out: str = "fw.elf", flags: str = "") -> str:
    ensure_arm()
    r = sh(f"arm-none-eabi-gcc {ARM_FLAGS} {flags} -I{CDIR} -T {linker_script} {' '.join(sources)} "
           f"-Wl,-Map={out}.map -o {out}")
    if r.returncode != 0:
        raise AssertionError("arm build failed:\n" + r.stderr[-1500:])
    return out


def qemu_run(elf: str, timeout: int = 10, extra: str = "") -> str:
    """Run on QEMU's mps2-an385 board (Cortex-M3). Output comes from Arm semihosting."""
    ensure_arm()
    cmd = (f"qemu-system-arm -M mps2-an385 -nographic -monitor none -serial none "
           f"-semihosting-config enable=on,target=native -kernel {elf} {extra}")
    try:
        r = sh(cmd, timeout=timeout)
        return r.stdout + r.stderr
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"")
        return (out.decode() if isinstance(out, bytes) else out) + "\n[timeout]"


def arm_tool(cmd: str) -> str:
    ensure_arm()
    r = sh(cmd)
    return r.stdout + r.stderr


def ensure_apt(binary: str, package: str):
    """Install a Debian package if `binary` is missing (Colab allows apt)."""
    if shutil.which(binary):
        return
    print(f"Installing {package} ...")
    r = sh("sudo -n true 2>/dev/null && S=sudo || S=; export DEBIAN_FRONTEND=noninteractive; "
           f"$S apt-get update -qq && $S apt-get install -y -qq {package} > /tmp/apt_{package}.log 2>&1", timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"apt install {package} failed")
