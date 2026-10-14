#!/usr/bin/env python3
"""Plot archived paired development metrics; never infer or simulate policies."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=Path(__file__).with_name("posture-20261014-development-comparison.json"))
    p.add_argument("--output", type=Path, default=Path(__file__).with_name("posture-20261014-development-progress.png"))
    a = p.parse_args()
    report = json.loads(a.input.read_text())
    candidates = report["candidates"]
    names = [c["name"] for c in candidates]
    x = np.arange(len(names))
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout="constrained")
    for leg, label, color in ((0, "Front left", "#0072B2"), (1, "Front right", "#D55E00")):
        angles = [c["suites"]["deployment"]["flat_posture"]["mean_shank_angle_deg"][leg] for c in candidates]
        clearance = [c["suites"]["deployment"]["flat_posture"]["p5_knee_clearance_cm"][leg] for c in candidates]
        axes[0, 0].plot(x, angles, "o-", label=label, color=color)
        axes[0, 1].plot(x, clearance, "o-", label=label, color=color)
    axes[0, 0].axhline(65, ls=":", color="0.5", label="Soft reward threshold")
    axes[0, 0].set(title="Flat: shank angle to world down", ylabel="Mean angle (degrees); 90 = horizontal")
    axes[0, 1].set(title="Flat: low knee-origin height", ylabel="Mean per-trial 5th percentile (cm)")
    for phase, label, color in (("ascending", "Ascending", "#009E73"), ("descending", "Descending", "#CC79A7")):
        values = [100*c["suites"]["deployment"][phase]["mean_loaded_calf_interval_fraction"] for c in candidates]
        axes[1, 0].plot(x, values, "o-", label=label, color=color)
    axes[1, 0].set(title="Stairs: any calf loaded contact", ylabel="Mean policy intervals (%)")
    for suite, offset, color in (("nominal", -.18, "#56B4E9"), ("deployment", .18, "#E69F00")):
        values = [100*c["suites"][suite]["passed"]/c["suites"][suite]["total"] for c in candidates]
        axes[1, 1].bar(x+offset, values, width=.35, label=suite, color=color)
        for i, candidate in enumerate(candidates):
            s = candidate["suites"][suite]
            axes[1, 1].text(i+offset, values[i]+.5, f"{s['passed']}/{s['total']}", ha="center", fontsize=7)
    axes[1, 1].set(title="First-episode completion", ylabel="Trials completed (%)", ylim=(0, 112))
    for ax in axes.flat:
        ax.set_xticks(x, names, rotation=30, ha="right")
        ax.grid(axis="y", alpha=.2)
        ax.legend(fontsize=8)
    fig.suptitle("Go2 posture reward development — paired seeds 2000–2003\n"
                 "Deployment domains; one training seed per arm; completion does not establish smoothness", fontsize=13)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.output, dpi=170)
    print(a.output)


if __name__ == "__main__":
    main()
