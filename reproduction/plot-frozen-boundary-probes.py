#!/usr/bin/env python3
"""Plot separately prescribed frozen-model geometry and speed diagnostics.

Read saved CSV only. Preserve each original case/reset-seed gate; pooled
completion and single-scene passes do not certify a safe envelope or smoothness.
"""
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load(path, seeds):
    rows = list(csv.DictReader(path.open(newline="")))
    groups = defaultdict(list)
    for row in rows:
        groups[row["evaluation_id"], int(row["case_index"])].append(row)
    values = {}
    for key, group in groups.items():
        if len(group) != 3 or {int(r["reset_seed"]) for r in group} != seeds:
            raise ValueError(f"Unexpected case/reset-seed coverage: {path}/{key}")
        if any(int(r["num_envs"]) != 32 for r in group):
            raise ValueError("Expected 32 first episodes per case/reset seed")
        row = group[0]
        count = sum(int(r["completions"]) for r in group)
        gate = all(r["final_traversal_passed"] == "True" for r in group)
        counts = {k: sum(int(r[k]) for r in group) for k in
                  ("falls", "stalls", "lateral_escapes", "base_contact_envs")}
        values[key] = {"completed": count, "total": 96, "gate": gate,
                       "counts": counts, "case": row["case_name"],
                       "height": float(row["step_height_m"]),
                       "depth": float(row["step_depth_m"]),
                       "direction": row["direction"], "speed": float(row["speed_m_s"])}
    return values, {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "seed_rows": len(rows), "reset_seeds": sorted(seeds)}


def annotate(ax, matrix, records, small=False):
    for (y, x), value in records.items():
        flags = value["counts"]
        label = f'{value["completed"]}/96'
        if not small:
            label += f'\nF{flags["falls"]} S{flags["stalls"]} E{flags["lateral_escapes"]}'
        ax.text(x, y, label, ha="center", va="center",
                fontsize=9 if small else 11,
                color="white" if matrix[y, x] > .7 else "#172d1d")
        if not value["gate"]:
            ax.add_patch(plt.Rectangle((x-.46, y-.46), .92, .92, fill=False,
                                      edgecolor="#cf252b", linewidth=3))
        elif value["completed"] != value["total"] or any(flags.values()):
            ax.text(x+.32, y-.32, "!", ha="center", va="center", color="#ffca45",
                    fontsize=16, fontweight="bold")


def main():
    repo = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=repo)
    args = parser.parse_args()
    root = args.repo_root.resolve()/"reproduction"
    geometry, gsource = load(root/"stair-frozen-height-depth-probe.csv", {601, 607, 613})
    speed, ssource = load(root/"stair-frozen-speed-probe.csv", {503, 509, 521})
    if len(geometry) != 36 or len(speed) != 30:
        raise ValueError("Require complete 18-case/two-speed and six-case/five-speed diagnostics")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "pdf.fonttype": 42})
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 9.2))
    heights, depths = [0.18, 0.20, 0.23], [0.20, 0.27, 0.33]
    for ax, (velocity, direction) in zip(axes.flat, [(0.3,"asc"),(0.3,"desc"),
                                                   (0.5,"asc"),(0.5,"desc")]):
        matrix = np.full((3,3), np.nan)
        records = {}
        for value in geometry.values():
            if value["speed"] == velocity and value["direction"] == direction:
                y, x = heights.index(value["height"]), depths.index(value["depth"])
                if (y,x) in records:
                    raise ValueError("Duplicate height/depth cell")
                matrix[y,x] = value["completed"]/96
                records[y,x] = value
        if len(records) != 9:
            raise ValueError("Incomplete geometry plot")
        ax.imshow(matrix, cmap="YlGn", vmin=0, vmax=1)
        annotate(ax, matrix, records)
        ax.set_xticks(range(3), ["20", "27", "33"])
        ax.set_yticks(range(3), ["18", "20", "23"])
        ax.set_xlabel("Tread depth (cm)")
        ax.set_ylabel("Rise (cm)")
        ax.set_title(f'{velocity:.1f} m/s | {"Ascent" if direction=="asc" else "Descent"}')
    fig.suptitle("Frozen control660: six-step rise/tread diagnostic\n"
                 "Three reset seeds; 32 environments per case/seed", y=.99)
    fig.text(.5,.025,"F = fall, S = stall, E = lateral escape (nonexclusive). Red outline = any original seed gate fails.\n"
             "Amber ! = gate passes with a failure; PASS does not mean zero failure or smoothness.\n"
             "Adaptive diagnostic; no nosing or 12-step long stairs. Original final acceptance remains FAIL.",
             ha="center", va="bottom", fontsize=9)
    fig.tight_layout(rect=(0,.12,1,.94))
    for ext in ("png", "pdf"):
        fig.savefig(root/f"stair-frozen-rise-tread-matrix.{ext}", dpi=160)
    plt.close(fig)

    matrix = np.full((6,5), np.nan)
    records = {}
    velocities = [.2,.3,.4,.5,.6]
    labels = ["6 steps 16/27 ascent", "6 steps 16/27 descent", "12 steps 17/25 ascent",
              "12 steps 17/25 descent", "6 steps 23/20 ascent", "6 steps 23/20 descent"]
    for (_, case), value in speed.items():
        x = velocities.index(value["speed"])
        if not 0 <= case < 6 or (case,x) in records:
            raise ValueError("Unexpected speed/case identity")
        matrix[case,x] = value["completed"]/96
        records[case,x] = value
    fig, ax = plt.subplots(figsize=(10,6.8))
    color = ax.imshow(matrix, cmap="YlGn", vmin=0, vmax=1, aspect="auto")
    annotate(ax, matrix, records, small=True)
    ax.set_xticks(range(5), [f"{v:.1f}" for v in velocities])
    ax.set_yticks(range(6), labels)
    ax.set_xlabel("Commanded forward speed (m/s)")
    ax.set_title("Frozen control660 speed diagnostic\nThree reset seeds; 96 first episodes per cell", pad=18)
    fig.colorbar(color, ax=ax, shrink=.7, label="Pooled completion fraction (display only)")
    fig.text(.5,.025,"Red outline = any original case/reset-seed gate fails; amber ! = passing gate with a failure.\n"
             "All five whole six-case matrices FAIL. These adapted diagnostic subsets establish no safe speed.\n"
             "The unchanged 0.6 m/s retry follows a collection OOM; its complete result is shown.",
             ha="center", va="bottom", fontsize=9)
    fig.tight_layout(rect=(0,.12,1,1))
    for ext in ("png", "pdf"):
        fig.savefig(root/f"stair-frozen-speed-matrix.{ext}", dpi=160)
    plt.close(fig)
    manifest = {"sources": [gsource, ssource], "geometry_cells": list(geometry.values()),
                "speed_cells": list(speed.values()),
                "interpretation": "Diagnostic only; gates from CSV retained; no model selection or retuning."}
    (root/"stair-frozen-boundary-plot-data.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("Saved rise/tread and speed diagnostic PNG/PDF plus source hash manifest")


if __name__ == "__main__":
    main()
