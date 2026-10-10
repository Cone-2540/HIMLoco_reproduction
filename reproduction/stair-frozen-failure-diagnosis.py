#!/usr/bin/env python3
"""CPU-only readback of fixed-policy, matched-scene long12 descent failures.

Does not run simulation, load CUDA, change evaluation criteria, or select policies.
Run from any directory; raw logs remain local and their hashes enter the output.
"""
import csv
import hashlib
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reproduction"
CASE = 13
ENV_IDS = list(range(416, 448))
RUNS = {
    0.3: "2026-10-11_05-48-09_frozen-final-speed03",
    0.5: "2026-10-11_05-52-29_frozen-final-speed05",
}
POLICIES = {
    "control660": "primary-result.json",
    "slide680": "candidates/0_model_680/result.json",
}
METRICS = [
    "xy_tracking_rmse_m_s", "measured_vx_m_s", "measured_vy_m_s",
    "yaw_tracking_mae_rad_s", "heading_abs_error_rad", "lateral_abs_error_m",
    "roll_rms_rad", "pitch_rms_rad", "linear_jerk_rms_m_s3",
    "action_delta_rms", "action_second_delta_rms",
    "current_sample_contact_foot_horizontal_speed_m_s",
    "current_sample_foot_slip_fraction", "current_sample_shank_contact_step_fraction",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    groups = []
    data = {}
    endpoints = []
    representative_traces = []
    initial_matches = []
    for speed, run in RUNS.items():
        for name, relative in POLICIES.items():
            path = ROOT / "isaaclab/logs" / run / relative
            result = json.loads(path.read_text())
            policy = result["policy"]
            trials = policy["trials"]
            assert [t["seed"] for t in trials] == [101, 211, 307]
            data[(speed, name)] = trials
            cases = [t["cases"][CASE] for t in trials]
            geometry = cases[0]["geometry"]
            assert all(c["geometry"] == geometry and c["num_envs"] == 32 for c in cases)
            assert policy["foot_body_names"] == ["FL_foot", "FR_foot", "RL_foot", "RR_foot"]
            assert policy["heading_control"]["enabled"]
            assert not policy["dynamics_randomized"]
            limit_y = geometry["width"] / 2 + 0.05
            seeds = []
            group_endpoints = []
            for t, c in zip(trials, cases):
                per = t["per_env"]
                seed = t["seed"]
                assert sum(per["completed"][e] for e in ENV_IDS) == c["completions"]
                for e in ENV_IDS:
                    feet = per["last_measured_feet_relative_xyz_m"][e]
                    root = per["last_measured_root_relative_xyz_m"][e]
                    outside = [
                        policy["foot_body_names"][i] for i, foot in enumerate(feet)
                        if geometry["first_riser_x"] <= foot[0] <= geometry["goal_platform_start_x"]
                        and abs(foot[1] - geometry["lateral_center_y"]) > limit_y
                    ]
                    root_outside = abs(root[1] - geometry["lateral_center_y"]) > limit_y
                    row = {
                        "policy": name, "speed_m_s": speed, "seed": seed, "env_id": e,
                        "completed": per["completed"][e], "fall": per["fall"][e],
                        "stall": per["stall"][e], "lateral_escape": per["lateral_escape"][e],
                        "initial_root_xyz_m": per["initial_root_relative_xyz_m"][e],
                        "terminal_root_xyz_m": root, "terminal_feet_xyz_m": feet,
                        "duration_s": per["first_episode_measured_duration_s"][e],
                        "root_outside": root_outside, "flight_feet_outside": outside,
                    }
                    if row["lateral_escape"]:
                        assert root_outside or outside, "Recomputed terminal escape criterion disagrees"
                    group_endpoints.append(row)
                    endpoints.append(row)
                seeds.append({
                    "seed": seed,
                    **{k: c[k] for k in ("completions", "falls", "stalls", "lateral_escapes", "base_contact_envs")},
                    "final_traversal_passed": next(x["traversal_passed"] for x in result["final_acceptance"]["cases"]
                                                    if x["seed"] == seed and x["case_index"] == CASE),
                    "metrics": {k: c["metrics"][k] for k in METRICS},
                    "environment_samples_after_warmup": c["contact_sample_counts"]["environment_samples"],
                })
                trace_rows = []
                for r in t["trace"]:
                    i = r["env_ids"].index(416)
                    if not r["active"][i]:
                        continue
                    trace_rows.append({
                        "time_s": r["time_s"], "root_xyz_m": r["root_relative_xyz"][i],
                        "velocity_world_m_s": r["root_linear_velocity_w"][i],
                        "yaw_roll_pitch_rad": r["yaw_roll_pitch"][i],
                        "command_vx_vy_yaw": r["command_vx_vy_yaw"][i],
                        "feet_xyz_m": r["feet_relative_xyz"][i],
                        "action_delta_rms": r["action_delta_rms"][i],
                        "action_second_delta_rms": r["action_second_delta_rms"][i],
                        "current_base_force_n": r["current_sample_base_force_n"][i],
                    })
                end = next(x for x in group_endpoints if x["seed"] == seed and x["env_id"] == 416)
                representative_traces.append({
                    "policy": name, "speed_m_s": speed, "seed": seed, "env_id": 416,
                    "completed": end["completed"], "fall": end["fall"], "lateral_escape": end["lateral_escape"],
                    "terminal_time_s": end["duration_s"], "last_trace_time_s": trace_rows[-1]["time_s"],
                    "terminal_root_xyz_m": end["terminal_root_xyz_m"], "rows": trace_rows,
                })
            escaped = [x for x in group_endpoints if x["lateral_escape"]]
            groups.append({
                "policy": name, "speed_m_s": speed, "case_index": CASE, "num_episodes": 96,
                "raw_file": str(path.relative_to(ROOT)), "raw_sha256": sha(path), "geometry": geometry,
                "seeds": seeds, "contact_sampling": policy["contact_sampling"],
                "totals": {k: sum(c[k] for c in cases) for k in
                           ("completions", "falls", "stalls", "lateral_escapes", "base_contact_envs")},
                "seed_arithmetic_mean_metrics": {k: statistics.mean(c["metrics"][k] for c in cases) for k in METRICS},
                "escapes": {
                    "count": len(escaped), "root_outside_count": sum(x["root_outside"] for x in escaped),
                    "foot_only_count": sum(not x["root_outside"] and bool(x["flight_feet_outside"]) for x in escaped),
                    "trigger_feet_counts": {foot: sum(foot in x["flight_feet_outside"] for x in escaped)
                                            for foot in policy["foot_body_names"]},
                    "terminal_root_x_range_m": [min(x["terminal_root_xyz_m"][0] for x in escaped),
                                                max(x["terminal_root_xyz_m"][0] for x in escaped)] if escaped else None,
                    "terminal_root_y_range_m": [min(x["terminal_root_xyz_m"][1] for x in escaped),
                                                max(x["terminal_root_xyz_m"][1] for x in escaped)] if escaped else None,
                },
            })
        a = data[(speed, "control660")]
        b = data[(speed, "slide680")]
        equal = all(x["per_env"]["initial_root_relative_xyz_m"][416:448]
                    == y["per_env"]["initial_root_relative_xyz_m"][416:448] for x, y in zip(a, b))
        assert equal
        initial_matches.append({"speed_m_s": speed, "initial_root_xyz_bit_exact_match": equal,
                                "episodes_compared": 96, "scope": "stored root XYZ only; not all hidden state"})
    report = {
        "schema_version": 1, "cpu_only": True, "runtime_modified": False,
        "checkpoint_selection_changed": False, "continuous_video_reviewed": False,
        "source_script_sha256": sha(Path(__file__)), "case_index": CASE,
        "metric_scope": "Arithmetic mean of three seed/case reports; within each seed, all active first-episode samples after 1 s. Different termination durations change weighting; not pooled means.",
        "trace_scope": "One env (416) per condition and seed, every 0.1 s; all 96 endpoints per condition are available. Do not extend representative traces to unrecorded failures.",
        "escape_definition": "|root y| > width/2 + 0.05 OR any foot with x in [first_riser_x, goal_platform_start_x] has |foot y| > width/2 + 0.05; here 0.65 m. No y-position correction in yaw-only external controller.",
        "action_units": "Unscaled policy-action differences per 0.02 s step; delta and second-delta RMS are dimensionless, not derivatives divided by dt.",
        "jerk_definition": "World-frame root velocity second finite difference / dt^2, 3D norm RMS, dt=0.02 s; sparse trace is not used to reconstruct it.",
        "paired_initial_root_checks": initial_matches, "groups": groups,
        "endpoints": endpoints, "representative_traces": representative_traces,
        "stretch_diagnosis_reference": "reproduction/stair-stretch-association-review.json",
    }
    (OUT / "stair-frozen-failure-diagnosis.json").write_text(json.dumps(report, indent=2) + "\n")
    csv_path = OUT / "stair-frozen-failure-diagnosis.csv"
    with csv_path.open("w", newline="") as f:
        fieldnames = ["policy", "speed_m_s", "seed", "env_id", "completed", "fall", "stall",
                      "lateral_escape", "duration_s", "root_x_m", "root_y_m", "root_z_m",
                      "root_outside", "flight_feet_outside"]
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in endpoints:
            writer.writerow({**{k: row[k] for k in fieldnames if k in row},
                             **dict(zip(["root_x_m", "root_y_m", "root_z_m"], row["terminal_root_xyz_m"])),
                             "flight_feet_outside": ";".join(row["flight_feet_outside"])})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=True, constrained_layout=True)
    colors = {"complete": "#307db3", "escape": "#d44b36", "fall": "#662d91"}
    for ax, group in zip(axes.flat, groups):
        rows = [x for x in endpoints if x["policy"] == group["policy"] and x["speed_m_s"] == group["speed_m_s"]]
        for category in ("complete", "escape", "fall"):
            key = {"complete": "completed", "escape": "lateral_escape", "fall": "fall"}[category]
            subset = [x for x in rows if x[key]]
            if subset:
                ax.scatter([x["terminal_root_xyz_m"][0] for x in subset],
                           [x["terminal_root_xyz_m"][1] for x in subset], s=24,
                           alpha=0.65, c=colors[category], label=f"{category} ({len(subset)})")
        for y in [-0.65, 0.65]:
            ax.axhline(y, c="0.3", ls=":", lw=1)
        ax.axvline(4.0, c="0.4", ls="--", lw=1)
        ax.set_title(f"{group['policy']} / {group['speed_m_s']} m/s")
        ax.set_xlim(2.8, 5.05)
        ax.set_ylim(-0.7, 0.7)
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(alpha=0.2)
        ax.set_xlabel("Terminal root x (m)")
        ax.set_ylabel("Terminal root y (m)")
    fig.suptitle("Frozen long12 descent: 96 first-episode endpoints per condition\nEscape may be triggered by a foot while root stays within the boundary")
    fig.savefig(OUT / "stair-frozen-failure-diagnosis.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True)
    for col, speed in enumerate(RUNS):
        for trace in representative_traces:
            if trace["speed_m_s"] != speed:
                continue
            rows = trace["rows"]
            color = "#307db3" if trace["policy"] == "control660" else "#d07b24"
            ls = {101: "-", 211: "--", 307: ":"}[trace["seed"]]
            status = "C" if trace["completed"] else "E" if trace["lateral_escape"] else "F"
            label = f"{trace['policy']}, seed {trace['seed']} ({status})"
            for row, field in enumerate([("root_xyz_m", 1), ("yaw_roll_pitch_rad", 0), ("yaw_roll_pitch_rad", 1)]):
                ax = axes[row, col]
                ax.plot([r["root_xyz_m"][0] for r in rows], [r[field[0]][field[1]] for r in rows],
                        color=color, ls=ls, lw=1, label=label)
                ax.set_xlabel("Root x (m)")
                ax.set_ylabel(["Root y (m)", "Yaw (rad)", "Roll (rad)"][row])
                ax.grid(alpha=0.2)
                ax.set_title(f"{speed} m/s")
        axes[0, col].legend(fontsize=7, loc="upper left")
    fig.suptitle("Representative env 416 only; 0.1 s trace\nC: completed / E: escape / F: fall; other failed envs have endpoints but no detailed trace")
    fig.savefig(OUT / "stair-frozen-failure-diagnosis-traces.png", dpi=160)
    plt.close(fig)
    print(json.dumps({"groups": [{"policy": g["policy"], "speed_m_s": g["speed_m_s"],
                                  "totals": g["totals"], "escapes": g["escapes"]} for g in groups],
                      "endpoints": len(endpoints), "representative_traces": len(representative_traces)}, indent=2))


if __name__ == "__main__":
    main()
