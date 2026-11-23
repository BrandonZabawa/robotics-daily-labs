"""Lab session object: graders, checkpoint answers, scoring.

Scoring (out of 10), matching the sheet's rule that tests decide the code points:
  Code checks       4 points x (checks passed / checks in the lab)
  Math checkpoint   3 points x (correct answers / math questions)
  Concept checkpoint 3 points x (choice questions right + rubric points hit) / total
Hints are allowed but logged, because a hinted attempt is not a cold attempt.
"""
from __future__ import annotations

import datetime as _dt
import importlib
import importlib.util
import math
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
IN_COLAB = bool(os.environ.get("COLAB_RELEASE_TAG")) or importlib.util.find_spec("google.colab") is not None

# pip name -> import name, for lab dependencies installed on first use
_IMPORT_NAME = {
    "python-can": "can",
    "opencv-python-headless": "cv2",
    "py_trees": "py_trees",
    "onnxruntime": "onnxruntime",
    "pyyaml": "yaml",
}


def _ctypes_load(path):
    import ctypes
    return ctypes.CDLL(path)


def _ensure_pip(packages):
    missing = []
    for pkg in packages:
        mod = _IMPORT_NAME.get(pkg, pkg.replace("-", "_"))
        if importlib.util.find_spec(mod) is None:
            missing.append(pkg)
    if missing:
        print("Installing:", " ".join(missing))
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", *missing], check=True)


def _close(got, expected, tol):
    if isinstance(expected, str):
        return str(got).strip().lower() == expected.strip().lower()
    if isinstance(expected, bool):
        return bool(got) is expected
    if isinstance(expected, (list, tuple)):
        return len(got) == len(expected) and all(_close(g, e, tol) for g, e in zip(got, expected))
    rel = tol.get("rel", 1e-3)
    ab = tol.get("abs", 1e-9)
    return math.isclose(float(got), float(expected), rel_tol=rel, abs_tol=ab)


class Lab:
    """One lab session. Create it in the setup cell: lab = Lab("C01")."""

    def __init__(self, lab_id: str, chdir: bool = True):
        self.id = lab_id.upper()
        self.checks = importlib.import_module(f"roboprep.checks.{self.id.lower()}")
        _ensure_pip(getattr(self.checks, "PIP", []))
        base = pathlib.Path("/content/work") if IN_COLAB else ROOT / "work"
        self.work = base / self.id
        self.work.mkdir(parents=True, exist_ok=True)
        if chdir:
            os.chdir(self.work)
        self._code: dict[str, bool] = {}
        self._lang: dict[tuple, bool] = {}
        self._math: dict[str, bool] = {}
        self._choice: dict[str, bool] = {}
        self._rubric_hits: dict[str, int] = {}
        self._hints: list[str] = []
        self._started = _dt.datetime.now()
        setup = getattr(self.checks, "setup", None)
        if setup:
            setup(self)
        print(f"{self.id} ready. Work folder: {self.work}")

    # ---------- code checks ----------
    def check(self, name: str, *args, **kwargs) -> bool:
        """Run a grader. Pass your Python functions, or the path(s) of your C/C++ file(s) instead."""
        fn = getattr(self.checks, f"check_{name}")
        from . import cbind
        sources = [a for a in args if cbind.is_source(a)]
        ros_cpp = getattr(self.checks, "ROS_CPP", {}).get(name)
        if sources and ros_cpp:
            lang = "C++"
            from . import ros
            try:
                cmd = ros.build_cpp_node(sources, *ros_cpp)
                fn(node_cmd=cmd, **kwargs)
                ok, why = True, ""
            except NotImplementedError:
                ok, why = False, "not attempted yet (replace the TODO)"
            except AssertionError as e:
                ok, why = False, str(e) or "assertion failed"
            except Exception as e:  # noqa: BLE001
                ok, why = False, f"{type(e).__name__}: {e}"
        elif sources:
            lang = "C++" if any(str(s).endswith(cbind.CPP_EXT) for s in sources) else "C"
            adapter = getattr(self.checks, f"c_{name}", None)
            if adapter is None:
                ok, why = False, "this check has no C/C++ adapter yet; grade it with your Python functions"
            else:
                try:
                    so = cbind.build(sources, getattr(self.checks, "CFLAGS", ""))
                    ok, why = cbind.run_isolated(lambda: fn(*adapter(_ctypes_load(so)), **kwargs))
                except AssertionError as e:  # compile error
                    ok, why = False, str(e)
        else:
            lang = "Python"
            try:
                fn(*args, **kwargs)
                ok, why = True, ""
            except NotImplementedError:
                ok, why = False, "not attempted yet (replace the NotImplementedError / TODO)"
            except AssertionError as e:
                ok, why = False, str(e) or "assertion failed"
            except Exception as e:  # student code crashed
                ok, why = False, f"{type(e).__name__}: {e}"
        self._lang[(name, lang)] = ok
        self._code[name] = any(v for (n, _), v in self._lang.items() if n == name)
        tag = f" ({lang})" if lang != "Python" else ""
        print(("✅ " if ok else "❌ ") + name + tag + ("" if ok else f"  ->  {why}"))
        return ok

    # ---------- checkpoint ----------
    def answer(self, qid: str, value) -> bool:
        spec = self.checks.ANSWERS[qid]
        expected, tol = (spec if isinstance(spec, tuple) and len(spec) == 2 and isinstance(spec[1], dict) else (spec, {}))
        if value is None or value is Ellipsis:
            ok, why = False, "not attempted"
        else:
            try:
                ok, why = _close(value, expected, tol), "wrong value"
            except (TypeError, ValueError) as e:
                ok, why = False, f"could not compare: {e}"
        self._math[qid] = ok
        print(("✅ " if ok else "❌ ") + qid + ("" if ok else f"  ->  {why}"))
        return ok

    def choose(self, qid: str, option) -> bool:
        expected = self.checks.CHOICES[qid]
        ok = option is not None and str(option).strip().lower() == str(expected).lower()
        self._choice[qid] = ok
        print(("✅ " if ok else "❌ ") + qid + ("" if ok else "  ->  not this one" if option else "  ->  not attempted"))
        return ok

    def explain(self, qid: str, text: str):
        """Commit your explanation first, then read the rubric it prints."""
        points = self.checks.RUBRIC[qid]
        words = len(text.split()) if text else 0
        if words < 5:
            print(f"{qid}: write your explanation first (at least a few sentences), then run this cell.")
            return
        print(f"{qid} rubric ({len(points)} points). Count the points your answer actually covered:")
        for i, p in enumerate(points, 1):
            print(f"  {i}. {p}")

    def self_score(self, hits: dict):
        for qid, n in hits.items():
            total = len(self.checks.RUBRIC[qid])
            self._rubric_hits[qid] = max(0, min(int(n), total))
        print("Recorded:", {k: f"{v}/{len(self.checks.RUBRIC[k])}" for k, v in self._rubric_hits.items()})

    def hint(self, name: str):
        self._hints.append(name)
        print("Hint (logged):", self.checks.HINTS[name])

    # ---------- helpers for checks ----------
    def path(self, name: str) -> pathlib.Path:
        return self.work / name

    # ---------- score ----------
    def score(self) -> float:
        code_names = [n[6:] for n in dir(self.checks) if n.startswith("check_")]
        n_code = len(code_names)
        n_math = len(getattr(self.checks, "ANSWERS", {}))
        choices = getattr(self.checks, "CHOICES", {})
        rubric = getattr(self.checks, "RUBRIC", {})
        c_code = sum(self._code.get(n, False) for n in code_names)
        c_math = sum(self._math.get(q, False) for q in getattr(self.checks, "ANSWERS", {}))
        concept_total = len(choices) + sum(len(v) for v in rubric.values())
        concept_got = sum(self._choice.get(q, False) for q in choices) + sum(self._rubric_hits.get(q, 0) for q in rubric)
        pts = 0.0
        pts += 4.0 * (c_code / n_code if n_code else 1.0)
        pts += 3.0 * (c_math / n_math if n_math else 1.0)
        pts += 3.0 * (concept_got / concept_total if concept_total else 1.0)
        pts = round(pts, 1)
        minutes = int((_dt.datetime.now() - self._started).total_seconds() // 60)
        line = (f"{self.id} | {_dt.date.today().isoformat()} | code {c_code}/{n_code} | math {c_math}/{n_math} | "
                f"concept {concept_got}/{concept_total} | hints {len(self._hints)} | {minutes} min | score {pts}/10")
        print(line)
        if pts >= 7 and not self._hints:
            print("Passed (cold attempt). Log it as Passed with this score.")
        elif pts >= 7:
            print("Passed with hints. Log the score; schedule a cold redo in 4 weeks.")
        else:
            print("Below 7: log it as Redo and repeat the failed parts cold on another day.")
        return pts
