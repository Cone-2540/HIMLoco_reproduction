#!/usr/bin/env python3
"""Plot first-episode staircase traces without launching Isaac Sim.

Example:
  python3 reproduction/plot-stair-eval.py isaaclab/logs/<evaluation>/result.json \
    --output reproduction/stair-evaluation

Writes one PNG/PDF per recorded case and reset seed. Old trace schemas are
accepted with explicit unavailable panels; velocity/slip/action samples are
never guessed from missing telemetry. Source metrics use the policy cadence,
while plots use the recorded trace cadence and retain the original units.
"""

import argparse
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load_policy(path, controller="policy"):
    source = json.loads(path.read_text())
    if controller in source:
        report = source[controller]
    elif "trials" in source and controller == "policy":
        report = source
    else:
        raise ValueError("Requested stair evaluation controller is unavailable")
    if not isinstance(report, dict) or not report.get("trials"):
        raise ValueError("Expected staircase first-episode trials, not a flat evaluation JSON")
    return report


def ground_profile(geometry):
    """Use explicit tread metadata, retaining descent-relative negative heights."""
    treads = geometry.get("treads")
    if not treads:
        first, depth, height, count = (geometry[key] for key in
            ("first_riser_x", "step_depth", "step_height", "num_steps"))
        sign = 1 if geometry["direction"] == "asc" else -1
        treads = [{"x_min": first + index * depth, "x_max": first + (index + 1) * depth,
                   "top_z": sign * (index + 1) * height} for index in range(count)]
    start = geometry.get("start_x", 0) - geometry.get("landing_length", 2) / 2
    x, z = [start, treads[0]["x_min"]], [0.0, 0.0]
    previous_z = 0.0
    for tread in treads:
        x.extend((tread["x_min"], tread["x_min"], tread["x_max"]))
        z.extend((previous_z, tread["top_z"], tread["top_z"]))
        previous_z = tread["top_z"]
    x.append(geometry.get("flight_end_x", geometry["goal_x"] + 1))
    z.append(geometry["goal_platform_z"])
    return np.asarray(x), np.asarray(z)


def case_geometry(report, case_index):
    geometries = report["geometry"]
    if isinstance(geometries, list):
        return geometries[case_index]
    if case_index != 0:
        raise ValueError("Single-geometry report only has case zero")
    return geometries


def recorded_cases(trial):
    cases = set()
    for frame in trial.get("trace", []):
        if "case_ids" in frame:
            cases.update(int(case) for case in frame["case_ids"])
        elif frame.get("active"):
            # Legacy traces recorded the first few envs of a single case only.
            cases.add(0)
    return sorted(cases)


def extract_trace(trial, case_index):
    trace = trial.get("trace", [])
    if not trace:
        raise ValueError("No recorded trajectory in this trial")
    chosen_env = None
    frames, columns = [], []
    for frame in trace:
        ids = frame.get("env_ids", list(range(len(frame.get("active", [])))))
        case_ids = frame.get("case_ids", [0] * len(ids))
        if chosen_env is None:
            matches = [env for env, case in zip(ids, case_ids) if case == case_index]
            if not matches:
                continue
            chosen_env = matches[0]
        if chosen_env not in ids:
            continue
        column = ids.index(chosen_env)
        if case_ids[column] != case_index or not frame["active"][column]:
            continue
        frames.append(frame)
        columns.append(column)
    if not frames:
        raise ValueError("No active first-episode trace for case %d" % case_index)

    def field(name):
        if not all(name in frame for frame in frames):
            return None
        array = np.asarray([frame[name][column] for frame, column in zip(frames, columns)], dtype=float)
        if not np.isfinite(array).all():
            raise ValueError("Non-finite active trace telemetry: " + name)
        return array

    time = np.asarray([frame["time_s"] for frame in frames], dtype=float)
    if len(time) > 1 and not np.all(np.diff(time) > 0):
        raise ValueError("Trace timestamps must strictly increase")
    values = {name: field(name) for name in (
        "root_relative_xyz", "yaw_roll_pitch", "feet_relative_xyz", "contacts",
        "command_vx_vy_yaw", "root_linear_velocity_w", "foot_horizontal_speed_m_s",
        "actions", "action_delta_rms", "action_second_delta_rms", "flight_paused",
        "base_force_n", "shank_force_n",
    )}
    return chosen_env, time, values


def unavailable(axis, text):
    axis.text(0.5, 0.5, text, transform=axis.transAxes, ha="center", va="center", color="#666666", fontsize=10)


def draw_trial(report, trial, case_index, output, source, controller):
    geometry = case_geometry(report, case_index)
    env_id, time, values = extract_trace(trial, case_index)
    case = next((item for item in trial.get("cases", []) if item["case_index"] == case_index), trial)
    metrics = case.get("metrics", trial.get("metrics", {}))
    fig, axes = plt.subplots(3, 2, figsize=(12.4, 10.5))
    profile, progress, velocity, posture, contact, action = axes.flatten()
    colors = ["#1768ac", "#b35422", "#14967f", "#7745ad"]
    root, feet = values["root_relative_xyz"], values["feet_relative_xyz"]
    gx, gz = ground_profile(geometry)
    profile.step(gx, gz, where="post", color="#555555", linewidth=1.6, label="Stair top surface")
    profile.fill_between(gx, gz, min(-0.15, float(gz.min()) - 0.1), step="post", color="#dddddd", alpha=0.65)
    if root is not None:
        profile.plot(root[:, 0], root[:, 2], color="#1768ac", linewidth=1.8, label="Root path")
    if feet is not None:
        for foot in range(4):
            profile.plot(feet[:, foot, 0], feet[:, foot, 2], color=colors[foot], linewidth=0.9, alpha=0.65,
                         label="Foot %d" % (foot + 1))
    if geometry.get("nosing", 0):
        sign = -1 if geometry["direction"] == "asc" else 1
        for tread in geometry.get("treads", []):
            edge = tread["x_min"] if sign < 0 else tread["x_max"]
            profile.plot([edge, edge + sign * geometry["nosing"]], [tread["top_z"]] * 2,
                         color="#aa4444", linewidth=3)
    profile.axvline(geometry["goal_x"], color="#14967f", linestyle="--", linewidth=1, label="Body goal")
    profile.set(xlabel="Forward position relative to spawn origin (m)", ylabel="Relative height (m)",
                title="Full-flight geometry and trajectory", xlim=(gx.min(), gx.max()))
    profile.legend(loc="best", fontsize=7, ncol=2, frameon=False)

    if root is not None:
        progress.plot(time, root[:, 0], color="#1768ac", label="Directed position")
        progress.axhline(geometry["goal_x"], color="#14967f", linestyle="--", label="Goal")
        lateral = progress.twinx()
        lateral.plot(time, root[:, 1] - geometry.get("lateral_center_y", 0), color="#b35422", label="Lateral displacement")
        lateral.set_ylabel("Lateral displacement (m)", color="#b35422")
        lateral.set_ylim(-geometry["width"] / 2 - 0.1, geometry["width"] / 2 + 0.1)
        lateral.axhline(geometry["width"] / 2, color="#b35422", linewidth=0.6, alpha=.35)
        lateral.axhline(-geometry["width"] / 2, color="#b35422", linewidth=0.6, alpha=.35)
    progress.set(title="Progress and corridor tracking", ylabel="Directed position (m)")

    measured = values["root_linear_velocity_w"]
    command = values["command_vx_vy_yaw"]
    if measured is None:
        unavailable(velocity, "World velocity was not recorded in this trace schema")
    else:
        velocity.plot(time, measured[:, 0], color="#1768ac", label="Measured world vx")
        if command is not None:
            velocity.plot(time, command[:, 0], color="#777777", linestyle="--", label="Forward body command")
        if root is not None:
            flight = ((root[:, 0] >= geometry["first_riser_x"] - .25)
                      & (root[:, 0] <= geometry["goal_platform_start_x"] + .25) & (time >= 1.0))
            paused = flight & (measured[:, 0] < .05)
            velocity.fill_between(time, 0, 1, where=paused, transform=velocity.get_xaxis_transform(),
                                  color="#df9b40", alpha=.25, label="Flight vx < 0.05 m/s")
        velocity.legend(fontsize=8, frameon=False)
    pause = metrics.get("longest_flight_pause_s")
    velocity.set(title="Velocity and pauses" + (" | longest %.2f s" % pause if pause is not None else ""),
                 ylabel="Velocity (m/s)")

    orientation = values["yaw_roll_pitch"]
    if orientation is not None:
        for index, label in enumerate(("Yaw", "Roll", "Pitch")):
            posture.plot(time, orientation[:, index], label=label, color=colors[index], linewidth=1.2)
        posture.legend(fontsize=8, frameon=False)
    else:
        unavailable(posture, "Orientation was not recorded")
    posture.set(title="Body orientation", ylabel="Angle (rad)")

    contacts, slip = values["contacts"], values["foot_horizontal_speed_m_s"]
    if contacts is not None:
        for foot in range(4):
            contact.plot(time, foot + .25 * contacts[:, foot], color=colors[foot], linewidth=.8,
                         label="Foot %d contact" % (foot + 1))
        contact.set_yticks(range(4), labels=["F1", "F2", "F3", "F4"])
        contact.set_ylim(-.2, 3.6)
        if slip is not None:
            sliding = contact.twinx()
            contacting = contacts > 0
            count = contacting.sum(axis=1)
            speed = np.where(contacting, slip, 0).sum(axis=1) / np.maximum(count, 1)
            speed[count == 0] = np.nan
            sliding.plot(time, speed, color="#111111", alpha=.7, label="Contact-foot speed proxy")
            sliding.axhline(.1, color="#666666", linestyle=":", linewidth=.8)
            sliding.set_ylabel("Contact-foot horizontal speed (m/s)")
        else:
            contact.text(.98, .96, "Slip velocity unavailable in source trace", ha="right", va="top",
                         transform=contact.transAxes, fontsize=8, color="#666666")
    else:
        unavailable(contact, "Contact telemetry was not recorded")
    contact.set(title="Foot contact and slip proxy", ylabel="Contact (raised = active)")

    delta, second = values["action_delta_rms"], values["action_second_delta_rms"]
    if second is not None:
        if delta is not None:
            action.plot(time, delta, color="#1768ac", label="Action first difference RMS")
        action.plot(time, second, color="#7745ad", label="Action second difference RMS")
        action.legend(fontsize=8, frameon=False)
    else:
        unavailable(action, "Action-difference samples were not recorded\nNo differences inferred from subsampled actions")
    summary_second = metrics.get("action_second_delta_rms")
    action.set(title="Action changes at policy cadence" + (" | aggregate second RMS %.3f" % summary_second
               if summary_second is not None else ""), ylabel="Action difference (normalized)")
    for axis in axes.flatten()[1:]:
        axis.set_xlabel("First-episode time (s)")
        axis.set_xlim(time[0], max(time[-1], time[0] + .1))
    for axis in axes.flatten():
        axis.grid(alpha=.18, linewidth=.7)
    status = "PASS" if case.get("passed", trial.get("passed")) else "FAIL"
    title = ("%s | %s | %.0f cm rise, %.0f cm tread, %.0f mm nosing | %d steps | seed %d, env %d"
             % (controller, geometry["direction"], geometry["step_height"]*100, geometry["step_depth"]*100,
                geometry.get("nosing", 0)*1000, geometry["num_steps"], trial["seed"], env_id))
    fig.suptitle(title, fontsize=12, y=.987)
    footnote = ("%s | case completion %.1f%% | falls %d, stalls %d, lateral escapes %d\n"
                "Representative first-episode trace; source: %s\n"
                "Missing panels mean telemetry was not recorded. Contact-foot speed is a slip proxy; plots alone do not certify smoothness."
                % (status, case.get("completion_fraction", 0)*100, case.get("falls", 0), case.get("stalls", 0),
                   case.get("lateral_escapes", 0), source))
    fig.text(.5, .015, footnote, ha="center", va="bottom", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, .09, 1, .966), h_pad=2, w_pad=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output.with_suffix(".png"), dpi=170, bbox_inches="tight")
    fig.savefig(output.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    return {"case": case_index, "seed": trial["seed"], "env_id": env_id,
            "png": str(output.with_suffix(".png")), "pdf": str(output.with_suffix(".pdf")),
            "trace_samples": len(time), "velocity_recorded": measured is not None,
            "action_differences_recorded": second is not None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reproduction/stair-evaluation"))
    parser.add_argument("--controller", choices=["policy", "zero_action"], default="policy")
    parser.add_argument("--seed", type=int, help="Plot one seed instead of all recorded trials")
    parser.add_argument("--case", type=int, help="Plot one geometry column instead of all recorded cases")
    args = parser.parse_args()
    report = load_policy(args.result, args.controller)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "axes.spines.top": False, "pdf.fonttype": 42})
    files = []
    for trial in report["trials"]:
        if args.seed is not None and trial["seed"] != args.seed:
            continue
        for case in recorded_cases(trial):
            if args.case is not None and case != args.case:
                continue
            geometry = case_geometry(report, case)
            label = re.sub(r"[^a-zA-Z0-9_.-]+", "-", geometry.get("name", geometry["direction"]))
            name = "%s-case%d-%s-seed%d" % (args.output.stem, case, label, trial["seed"])
            files.append(draw_trial(report, trial, case, args.output.parent / name, str(args.result), args.controller))
    if not files:
        parser.error("No trace matched the selected seed/case")
    print(json.dumps({"source": str(args.result), "outputs": files}, indent=2))


if __name__ == "__main__":
    main()
