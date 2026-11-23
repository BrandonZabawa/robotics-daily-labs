#!/usr/bin/env python3
"""Execute notebooks headless and report problems.

  python tools/run_all.py                         # blank labs: must run without crashing (TODOs fail politely)
  python tools/run_all.py C01 D03                 # only these labs
  python tools/run_all.py --keys ../robotics-daily-labs-solutions/answer_key
                                                  # answer keys against this repo's graders: every check passes, 10/10
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent


def outputs_text(nb):
    chunks = []
    for c in nb.cells:
        for o in c.get("outputs", []):
            if o.get("output_type") == "stream":
                chunks.append(o.get("text", ""))
            elif o.get("output_type") == "error":
                chunks.append(f"ERROR {o.get('ename')}: {o.get('evalue')}")
            elif "data" in o and "text/plain" in o["data"]:
                chunks.append(o["data"]["text/plain"])
    return "\n".join(chunks)


def run(path: Path, student: bool, timeout: int):
    nb = nbformat.read(path, as_version=4)
    os.environ["RDL_ROOT"] = str(ROOT)
    client = NotebookClient(nb, timeout=timeout, kernel_name="python3", allow_errors=student,
                            resources={"metadata": {"path": str(ROOT)}})
    t0 = time.time()
    try:
        client.execute()
        err = None
    except Exception as e:  # a cell raised in an answer key
        err = f"{type(e).__name__}: {str(e)[-1500:]}"
    text = outputs_text(nb)
    problems = []
    if err:
        problems.append(err)
    if student:
        for c in nb.cells:
            for o in c.get("outputs", []):
                if o.get("output_type") == "error" and o.get("ename") != "NotImplementedError":
                    problems.append(f"{o.get('ename')}: {o.get('evalue')}")
    else:
        bad = [l for l in text.splitlines() if l.startswith("❌")]
        problems += bad
        if "score 10.0/10" not in text:
            problems.append("score line is not 10.0/10")
    return problems, time.time() - t0, nb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--keys", help="folder of answer-key notebooks (from the private solutions repo)")
    ap.add_argument("--student", action="store_true", help="(default) run the blank labs")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--save", action="store_true", help="write executed notebooks to work/executed/")
    a = ap.parse_args()
    student = not a.keys
    folder = Path(a.keys).resolve() if a.keys else ROOT / "labs"
    paths = sorted(folder.rglob("*.ipynb"))
    if a.ids:
        want = {i.upper() for i in a.ids}
        paths = [p for p in paths if p.name.split("_")[0].upper() in want]
    failed = 0
    for p in paths:
        problems, dt, nb = run(p, student, a.timeout)
        status = "ok  " if not problems else "FAIL"
        print(f"{status} {p.name} ({dt:.0f} s)")
        for pr in problems[:8]:
            print("     ", pr)
        failed += bool(problems)
        if a.save:
            out = ROOT / "work" / "executed" / p.name
            out.parent.mkdir(parents=True, exist_ok=True)
            nbformat.write(nb, out)
    print(f"{len(paths) - failed}/{len(paths)} notebooks clean")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
