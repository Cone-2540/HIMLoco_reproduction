#!/usr/bin/env python3
"""Plot completion and unchanged gates from the saved final-validation CSV.

Run from any directory; no simulator is started. A red cell outline means at
least one reset seed failed the original gate, including zero base contact.
Pooled completion alone is deliberately not used to assign the outline.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    repo = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=repo / "reproduction/stair-frozen-final-validation.csv")
    parser.add_argument("--output", type=Path, default=repo / "reproduction/stair-frozen-final-matrix")
    args = parser.parse_args()
    with args.csv.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    grouped = defaultdict(list)
    for row in rows:
        if row["evaluation_id"].startswith("nominal_"):
            grouped[(row["evaluation_id"], int(row["case_index"]))].append(row)
    evaluations = [
        ("nominal_primary_speed0.3", "Primary control660 | 0.3 m/s"),
        ("nominal_primary_speed0.5", "Primary control660 | 0.5 m/s"),
        ("nominal_secondary_speed0.3", "Secondary slide680 | 0.3 m/s"),
        ("nominal_secondary_speed0.5", "Secondary slide680 | 0.5 m/s"),
    ]
    labels = [
        "16/27 asc", "16/27 desc", "17/25 asc", "17/25 desc",
        "11/33 asc", "11/33 desc", "16.5/29 asc", "16.5/29 desc",
        "17/29 + 1.5 cm lip asc", "17/29 + 1.5 cm lip desc",
        "16/33 + 2.5 cm lip asc", "16/33 + 2.5 cm lip desc",
        "12 steps 17/25 asc", "12 steps 17/25 desc",
        "23/20 asc", "23/20 desc",
    ]
    values = np.full((4, 16), np.nan)
    counts = {}
    gates = {}
    for r, (evaluation, _) in enumerate(evaluations):
        for c in range(16):
            items = grouped[(evaluation, c)]
            if len(items) != 3 or {int(item["reset_seed"]) for item in items} != {101, 211, 307}:
                raise ValueError(f"Incomplete or unexpected independent reset seeds: {evaluation}/{c}")
            total = sum(int(item["num_envs"]) for item in items)
            completed = sum(int(item["completions"]) for item in items)
            if total != 96:
                raise ValueError(f"Expected 96 environments: {evaluation}/{c}")
            values[r, c] = completed / total
            counts[r, c] = (completed, total)
            gates[r, c] = all(item["final_traversal_passed"] == "True" for item in items)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "pdf.fonttype": 42})
    fig, axis = plt.subplots(figsize=(18, 6.4))
    color = axis.imshow(values, cmap="YlGn", vmin=0, vmax=1, aspect="auto")
    axis.set_xticks(range(16), labels=labels, rotation=40, ha="right")
    axis.set_yticks(range(4), labels=[label for _, label in evaluations])
    for r in range(4):
        for c in range(16):
            n, d = counts[r, c]
            axis.text(c, r, f"{n}/{d}", ha="center", va="center", fontsize=10,
                      color="white" if values[r, c] > .75 else "#102615")
            if not gates[r, c]:
                axis.add_patch(plt.Rectangle((c - .47, r - .46), .94, .92,
                                             fill=False, edgecolor="#cf252b", linewidth=3))
    for boundary in (3.5, 11.5, 13.5):
        axis.axvline(boundary, color="white", linewidth=3)
    axis.set_title("Frozen Go2 staircase policies: independent first-episode completion\n"
                   "Three fresh reset seeds; 32 environments per case/seed; 40 s maximum", pad=24)
    fig.colorbar(color, ax=axis, shrink=.7, label="Pooled completion fraction (display only)")
    fig.text(.5, .025,
             "Red outline = any case/reset seed fails unchanged >=95% completion, <=5% each fall/stall/escape, or zero-base-contact gate.\n"
             "All four whole matrices FAIL. Geometry strata are descriptive; success does not certify smoothness or real-robot transfer.",
             ha="center", va="bottom", fontsize=10)
    fig.tight_layout(rect=(0, .10, 1, 1))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output.with_suffix(".png"), dpi=150)
    fig.savefig(args.output.with_suffix(".pdf"))
    plt.close(fig)
    print(args.output.with_suffix(".png"))


if __name__ == "__main__":
    main()
