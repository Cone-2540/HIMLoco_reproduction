#!/usr/bin/env python3
"""Export honest, standalone training curves from an Isaac Lab HIM run.

Run with the existing container Python to reuse TensorBoard/matplotlib:
  docker exec -w /workspace/himloco isaaclab-local-lab-1 /isaac-sim/python.sh \
    reproduction/plot-gpu.py isaaclab/logs/<run> \
    --output reproduction/gpu-training.png
Add --resume_run isaaclab/logs/<resumed-run> to combine continuous event steps
and mark the change in pure-turn command sampling recorded in its config.json.
Both PNG and PDF are written. Reading events does not change the training run.
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator


def read_scalars(accumulator, tag):
    if tag not in accumulator.Tags().get("scalars", []):
        raise ValueError("Required TensorBoard scalar missing: %s" % tag)
    # The runner logs iteration 0 after completing its first update. A completed
    # update count is easier to compare to checkpoint names model_20/model_300.
    points = {event.step + 1: event.value for event in accumulator.Scalars(tag)}
    steps = np.array(sorted(points), dtype=np.int64)
    values = np.array([points[step] for step in steps], dtype=np.float64)
    if not len(steps) or not np.isfinite(values).all():
        raise ValueError("Empty or non-finite TensorBoard scalar: %s" % tag)
    return steps, values


def rolling_mean(values, window):
    if window <= 1:
        return values
    # Trailing average, keeping startup points rather than discarding the first
    # window. The faint raw curve remains visible for each plotted series.
    cumulative = np.concatenate(([0.0], np.cumsum(values)))
    stop = np.arange(1, len(values) + 1)
    start = np.maximum(0, stop - window)
    return (cumulative[stop] - cumulative[start]) / (stop - start)


def load_run(path):
    if not path.is_dir():
        raise ValueError("Run directory does not exist: %s" % path)
    if not list(path.glob("events.out.tfevents.*")):
        raise ValueError("No TensorBoard event file in %s" % path)
    config_path = path / "config.json"
    config = json.loads(config_path.read_text()) if config_path.is_file() else {}
    accumulator = EventAccumulator(str(path), size_guidance={"scalars": 0})
    accumulator.Reload()
    tags = {
        "reward": "Train/mean_reward",
        "length": "Train/mean_episode_length",
        "xy": "Episode/Metrics/base_velocity/error_vel_xy",
        "yaw": "Episode/Metrics/base_velocity/error_vel_yaw",
        "estimate": "Loss/Estimation Loss",
        "swap": "Loss/Swap Loss",
    }
    return config, {key: read_scalars(accumulator, tag) for key, tag in tags.items()}


def merge_resume(series, resumed_series):
    # Resume logs already carry absolute PPO iteration numbers; adding a second
    # offset would mislabel updates 301-500. Require a continuous boundary.
    boundaries = {int(steps[-1]) for steps, _ in series.values()}
    if len(boundaries) != 1:
        raise ValueError("Original run scalars end at different updates")
    boundary = boundaries.pop()
    merged = {}
    for key, (steps, values) in series.items():
        resumed_steps, resumed_values = resumed_series[key]
        if int(resumed_steps[0]) != boundary + 1:
            raise ValueError("Resume scalar %s begins at update %d; expected %d"
                             % (key, resumed_steps[0], boundary + 1))
        combined_steps = np.concatenate((steps, resumed_steps))
        if not np.all(np.diff(combined_steps) == 1):
            raise ValueError("Non-continuous logged update sequence for %s" % key)
        merged[key] = (combined_steps, np.concatenate((values, resumed_values)))
    return merged, boundary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="Training run directory containing TensorBoard events")
    parser.add_argument("--resume_run", type=Path,
                        help="Optional resumed run with continuous absolute event steps")
    parser.add_argument("--output", type=Path, default=Path("reproduction/gpu-training.png"))
    parser.add_argument("--window", type=int, default=10, help="Trailing average window in updates (default: 10)")
    args = parser.parse_args()
    if args.window < 1:
        parser.error("--window must be positive")
    config, series = load_run(args.run)
    resume_boundary = None
    change_label = None
    if args.resume_run is not None:
        resumed_config, resumed_series = load_run(args.resume_run)
        if (config.get("num_envs") is not None and
                resumed_config.get("num_envs") != config["num_envs"]):
            parser.error("Original and resumed runs have different num_envs")
        series, resume_boundary = merge_resume(series, resumed_series)
        turn_fraction = resumed_config.get("training_turn_fraction")
        if turn_fraction is not None:
            change_label = "%g%% pure-turn commands" % (100 * turn_fraction)
        else:
            change_label = "Resumed training"
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.titlesize": 11, "axes.labelsize": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })
    fig, axes = plt.subplots(2, 2, figsize=(11.6, 7.5))
    all_axes = list(axes.flat)

    def draw(axis, key, label, color):
        steps, values = series[key]
        axis.plot(steps, values, color=color, alpha=0.22, linewidth=0.8)
        axis.plot(steps, rolling_mean(values, args.window), color=color,
                  linewidth=1.7, label=label)

    draw(all_axes[0], "reward", "Episode reward", "#1768ac")
    all_axes[0].set(title="Training reward", ylabel="Mean episode reward")
    draw(all_axes[1], "length", "Episode length", "#14967f")
    all_axes[1].set(title="Episode duration", ylabel="Mean episode length (control steps)")
    draw(all_axes[2], "xy", "XY velocity error", "#1768ac")
    all_axes[2].set(title="Command tracking error", ylabel="XY velocity error (m/s)")
    yaw_axis = all_axes[2].twinx()
    draw(yaw_axis, "yaw", "Yaw rate error", "#df7a22")
    yaw_axis.set_ylabel("Yaw rate error (rad/s)")
    handles, labels = all_axes[2].get_legend_handles_labels()
    other_handles, other_labels = yaw_axis.get_legend_handles_labels()
    all_axes[2].legend(handles + other_handles, labels + other_labels,
                      loc="upper right", frameon=False)
    draw(all_axes[3], "estimate", "Velocity estimation", "#7745ad")
    draw(all_axes[3], "swap", "Swap prediction", "#c24162")
    all_axes[3].set(title="HIM estimator losses", ylabel="Loss")
    all_axes[3].legend(frameon=False)
    final_updates = min(int(steps[-1]) for steps, _ in series.values())
    for axis in all_axes:
        axis.set_xlabel("Completed PPO updates")
        axis.grid(axis="both", alpha=0.18, linewidth=0.7)
        axis.set_xlim(1, max(final_updates, 2))
        axis.tick_params(direction="out")
        if resume_boundary is not None:
            axis.axvline(resume_boundary, color="#666666", linestyle="--",
                         linewidth=1.1, alpha=0.8)
    if resume_boundary is not None:
        all_axes[0].annotate(change_label, xy=(resume_boundary, 0.98),
                             xycoords=("data", "axes fraction"),
                             xytext=(-6, -2), textcoords="offset points",
                             ha="right", va="top", fontsize=8, color="#444444",
                             bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85})
    title_details = ["Isaac Lab migration", "Go2 flat ground", "HIM + PPO"]
    if config.get("num_envs"):
        title_details.append("%s environments" % config["num_envs"])
    fig.suptitle(" | ".join(title_details), fontsize=13, y=0.98)
    run_names = args.run.name
    if args.resume_run is not None:
        run_names += " -> " + args.resume_run.name
    footnote = ("Run: %s\n%d logged updates | Raw curves + %d-update trailing mean\n"
                "Training signals describe learning progress; they do not establish paper-level reproduction or deployment readiness."
                % (run_names, final_updates, args.window))
    fig.text(0.5, 0.025, footnote, ha="center", va="bottom", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.11, 1, 0.945), w_pad=2.6, h_pad=2.6)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    png = args.output.with_suffix(".png")
    pdf = args.output.with_suffix(".pdf")
    fig.savefig(png, dpi=190, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight", metadata={"Title": "HIM migration Go2 flat-ground training curves"})
    plt.close(fig)
    print(json.dumps({"run": str(args.run), "logged_updates": final_updates,
                      "resume_run": str(args.resume_run) if args.resume_run is not None else None,
                      "resume_boundary": resume_boundary,
                      "png": str(png), "pdf": str(pdf), "smoothing_window": args.window}, indent=2))


if __name__ == "__main__":
    main()
