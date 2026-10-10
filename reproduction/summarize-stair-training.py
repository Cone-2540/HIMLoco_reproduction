"""Small JSON summaries and standalone curves from actual TensorBoard data."""

import argparse
import json
from pathlib import Path

from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

parser = argparse.ArgumentParser()
parser.add_argument("run", type=Path)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--plot", type=Path)
args = parser.parse_args()
accumulator = EventAccumulator(str(args.run), size_guidance={"scalars": 0})
accumulator.Reload()
tags = accumulator.Tags()["scalars"]
selected = [tag for tag in tags if tag.startswith(("Loss/", "Perf/", "Policy/", "Train/"))
            or any(key in tag for key in ("terrain_levels", "stair_goal_reached", "base_contact", "stair_corridor_exit", "error_vel"))]
series = {tag: [{"update": event.step + 1, "value": event.value} for event in accumulator.Scalars(tag)]
          for tag in selected}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps({"run": str(args.run), "series": series,
                                 "scope": "Training diagnostics; successful goal term is not independent traversal validation"}, indent=2))
print(json.dumps({tag: points[-1] for tag, points in series.items() if points}, indent=2))
if args.plot:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    groups = [
        ("Full flight training term", [tag for tag in selected if "stair_goal_reached" in tag]),
        ("Failures", [tag for tag in selected if "base_contact" in tag or "stair_corridor_exit" in tag]),
        ("Curriculum", [tag for tag in selected if "terrain_levels" in tag]),
        ("Velocity errors", [tag for tag in selected if "error_vel" in tag]),
        ("HIM estimation", ["Loss/Estimation Loss", "Loss/Swap Loss"]),
        ("Actual learning rate", ["Loss/learning_rate"]),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
    for ax, (title, keys) in zip(axes.flat, groups):
        for tag in keys:
            points = series.get(tag, [])
            if points:
                ax.plot([p["update"] for p in points], [p["value"] for p in points], label=tag.split("/")[-1])
        ax.set(title=title, xlabel="Completed PPO updates")
        ax.grid(alpha=0.25)
        if ax.lines:
            ax.legend(fontsize=8)
    fig.suptitle(args.run.name + " — training diagnostics")
    args.plot.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.plot, dpi=150)
    fig.savefig(args.plot.with_suffix(".pdf"))
    plt.close(fig)
