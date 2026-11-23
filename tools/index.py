#!/usr/bin/env python3
"""Rebuild SCHEDULE.md, CURRICULUM.md and curriculum/labs.csv from the notebooks' metadata.

Each lab notebook carries its metadata under metadata["rdl"]: id, title, track, axis, minutes, after (lab ids it
builds on) and concepts (names from curriculum/concepts.csv). Run this after adding or renaming a lab:

    python tools/index.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GH_USER, GH_REPO, DAYS_PER_WEEK = "BrandonZabawa", "robotics-daily-labs", 5
TRACKS = ["C and bare-metal", "Drivers and protocols", "ROS 2", "Control and motion", "Real-time and Linux",
          "Estimation and perception", "Reliability and systems", "Hardware and electronics", "Planning and learning",
          "Compute and deployment", "Maps and review"]


def load_labs():
    labs = []
    for p in sorted((ROOT / "labs").rglob("*.ipynb")):
        meta = dict(json.loads(p.read_text())["metadata"]["rdl"])
        meta["path"] = p.relative_to(ROOT).as_posix()
        labs.append(meta)
    return labs


def schedule(labs):
    """Interleave tracks so each advances at the same proportional rate; a lab never precedes its `after` labs."""
    ids = {l["id"] for l in labs}
    for l in labs:
        l["after"] = [a for a in l["after"] if a in ids]
    queues = OrderedDict((t, [l for l in labs if l["track"] == t]) for t in TRACKS)
    totals = {t: len(q) for t, q in queues.items() if q}
    done, placed, order = {t: 0 for t in totals}, set(), []
    while any(queues.values()):
        for t in sorted((t for t in totals if queues[t]), key=lambda t: ((done[t] + 1) / totals[t], TRACKS.index(t))):
            lab = queues[t][0]
            if all(a in placed for a in lab["after"]):
                order.append(lab)
                placed.add(lab["id"])
                queues[t].pop(0)
                done[t] += 1
                break
        else:
            sys.exit("schedule: dependency cycle in `after`")
    for n, lab in enumerate(order):
        lab["week"], lab["day"] = n // DAYS_PER_WEEK + 1, n % DAYS_PER_WEEK + 1
    return order


def colab(path):
    return f"https://colab.research.google.com/github/{GH_USER}/{GH_REPO}/blob/main/{path}"


def main():
    concepts = list(csv.DictReader(open(ROOT / "curriculum" / "concepts.csv")))
    known = {c["term"] for c in concepts}
    labs = load_labs()
    bad = [f"{l['id']}: unknown concept {c!r}" for l in labs for c in l["concepts"] if c not in known]
    bad += [f"{l['id']}: unknown track {l['track']!r}" for l in labs if l["track"] not in TRACKS]
    if bad:
        sys.exit("\n".join(bad))
    order = schedule(labs)
    covered = {}
    for l in labs:
        for c in l["concepts"]:
            covered.setdefault(c, []).append(l["id"])

    s = ["# Schedule", "",
         f"{len(order)} labs, {DAYS_PER_WEEK} a week. Tracks are interleaved so each one advances at the same rate; "
         "a lab never comes before the labs it builds on. Do them in order, one a day.", "",
         "| Week | Day | Lab | Title | Track | Minutes |", "|---|---|---|---|---|---|"]
    s += [f"| {l['week']} | {l['day']} | [{l['id']}]({colab(l['path'])}) | {l['title']} | {l['track']} | {l['minutes']} |" for l in order]
    (ROOT / "SCHEDULE.md").write_text("\n".join(s) + "\n")

    c = ["# Curriculum coverage", "",
         "Every concept from the Skill Hub tab of the prep sheet (plus the added ROS 2 track) and the lab that teaches it.", "",
         "| Concept | Skill Hub layer | Math or Concept | Lab |", "|---|---|---|---|"]
    c += [f"| {r['term']} | {r['layer']} | {r['tag']} | {', '.join(covered.get(r['term'], [])) or '**missing**'} |" for r in concepts]
    (ROOT / "CURRICULUM.md").write_text("\n".join(c) + "\n")

    with open(ROOT / "curriculum" / "labs.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["week", "day", "id", "title", "track", "skill_axis", "minutes", "concepts", "notebook"])
        for l in order:
            w.writerow([l["week"], l["day"], l["id"], l["title"], l["track"], l["axis"], l["minutes"], "; ".join(l["concepts"]), l["path"]])
    missing = [r["term"] for r in concepts if r["term"] not in covered]
    print(f"{len(labs)} labs; {len(covered)}/{len(concepts)} concepts covered" + (f"; missing: {missing}" if missing else ""))


if __name__ == "__main__":
    main()
