#!/usr/bin/env python3
"""Analyze saved first-episode stair motion without Isaac Sim or GPU access.

The standard-library analysis accepts sparse and policy-step traces. It keeps
their cadence distinct, records missing telemetry explicitly, and never assigns
an aggregate shank force to an individual leg. Optional plots need matplotlib.

Example:
  python3 reproduction/analyze-stair-motion.py RUN/result.json \
    RUN/candidates/0_model_370/result.json --output reproduction/motion
  python3 reproduction/analyze-stair-motion.py --self-test

Writes JSON, Markdown and a body/event CSV. Multiple inputs are compared only
at equal case index, geometry, reset seed and commanded speed. Existing source
metrics and acceptance thresholds are preserved; this tool certifies no motion.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path


GO2_LEGS = tuple(f"{leg}_{body}" for leg in ("FL", "FR", "RL", "RR") for body in ("thigh", "calf"))
GEOMETRY_FIELDS = (
    "direction", "travel_sign", "num_steps", "step_height", "step_depth", "width",
    "nosing", "nosing_thickness", "landing_length", "start_x", "first_riser_x",
    "last_riser_x", "goal_platform_start_x", "goal_x", "goal_platform_z",
    "lateral_center_y", "goal_dwell_s", "treads", "collision_representation",
)
MOTION_METRICS = (
    "action_delta_rms", "action_second_delta_rms", "linear_jerk_rms_m_s3",
    "linear_acceleration_rms_m_s2", "xy_tracking_mae_m_s", "xy_tracking_rmse_m_s",
    "measured_vx_m_s", "current_sample_shank_contact_step_fraction",
    "shank_contact_step_fraction", "current_sample_foot_slip_fraction", "foot_slip_fraction",
)
TRACE_FIELDS = (
    "root_relative_xyz", "root_linear_velocity_w", "yaw_roll_pitch", "feet_relative_xyz",
    "foot_horizontal_speed_m_s", "contacts", "current_sample_contacts", "command_vx_vy_yaw",
    "actions", "action_delta_rms", "action_second_delta_rms", "flight_paused",
    "base_force_n", "shank_force_n", "current_sample_base_force_n", "current_sample_shank_force_n",
    "leg_current_normal_force_norm_n", "leg_history_peak_normal_force_norm_n",
)


def finite(value):
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(finite(item) for item in value)
    return value is None


def mean(values):
    return statistics.fmean(values) if values else None


def rms(values):
    return math.sqrt(statistics.fmean(value * value for value in values)) if values else None


def quantile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    coordinate = (len(ordered) - 1) * fraction
    low = math.floor(coordinate)
    high = math.ceil(coordinate)
    return ordered[low] + (ordered[high] - ordered[low]) * (coordinate - low)


def stats(values):
    return {"samples": len(values), "mean": mean(values), "rms": rms(values),
            "min": min(values) if values else None, "max": max(values) if values else None,
            "p95": quantile(values, 0.95)}


def read_json(path):
    return json.loads(path.read_text()) if path.is_file() else None


def sidecar_directory(path):
    # Candidate subdirectories share their parent run's construction config.
    for directory in (path.parent, *path.parent.parents):
        if (directory / "config.json").is_file():
            return directory
        if directory.name in ("logs", "reproduction"):
            break
    return path.parent


def load_source(path, controller):
    document = read_json(path)
    if not isinstance(document, dict):
        raise ValueError(f"Not a JSON report: {path}")
    report = document.get(controller)
    if report is None and controller == "policy" and "trials" in document:
        report = document
    if not isinstance(report, dict) or not report.get("trials"):
        raise ValueError(f"No {controller} staircase trials in {path}")
    directory = sidecar_directory(path)
    config = read_json(directory / "config.json") or {}
    domain = read_json(directory / "domain-parameters-initial.json") or {}
    sampling = report.get("contact_sampling") or {}
    physics_dt = sampling.get("physics_dt_s", config.get("physics_dt"))
    policy_dt = sampling.get("policy_sample_dt_s")
    if policy_dt is None and physics_dt is not None and config.get("policy_decimation") is not None:
        policy_dt = physics_dt * config["policy_decimation"]
    foot_names = report.get("foot_body_names")
    foot_name_source = "report.foot_body_names" if foot_names else None
    if not foot_names:
        materials = domain.get("foot_material", {})
        if materials.get("status") == "available" and materials.get("body_names"):
            foot_names = materials["body_names"]
            foot_name_source = str(directory / "domain-parameters-initial.json") + ":foot_material.body_names"
    leg_names = report.get("leg_body_names")
    checkpoint = document.get("checkpoint", config.get("checkpoint"))
    # Domain values are useful matching evidence. Never treat missing reads as equal.
    material = domain.get("foot_material", {})
    physical_evidence = {key: domain.get(key) for key in
                         ("base_mass_kg", "base_inertia_kg_m2", "base_com", "actuator_pd")}
    material_evidence = {key: material.get(key) for key in
                         ("status", "body_names", "static_friction", "dynamic_friction", "restitution", "configured_ranges")}
    return {"path": str(path), "checkpoint": checkpoint, "controller": controller,
            "report": report, "config": config, "policy_dt_s": policy_dt,
            "physics_dt_s": physics_dt, "foot_body_names": foot_names,
            "foot_name_source": foot_name_source, "leg_body_names": leg_names,
            "material_evidence": material_evidence, "physical_evidence": physical_evidence,
            "domain_readback_path": str(directory / "domain-parameters-initial.json") if domain else None}


def geometry_for(report, case_index):
    geometry = report["geometry"]
    if isinstance(geometry, list):
        return geometry[case_index]
    if case_index != 0:
        raise ValueError("Single geometry has nonzero trace case index")
    return geometry


def geometry_key(geometry):
    # Ignore spawn translations and arbitrary labels, retaining physical geometry.
    return json.dumps({key: geometry.get(key) for key in GEOMETRY_FIELDS}, sort_keys=True)


def extract_environments(trial):
    groups, ended = {}, set()
    for frame in trial.get("trace", []):
        active = frame.get("active", [])
        env_ids = frame.get("env_ids", list(range(len(active))))
        case_ids = frame.get("case_ids", [0] * len(env_ids))
        if len(active) != len(env_ids) or len(case_ids) != len(env_ids) or len(set(env_ids)) != len(env_ids):
            raise ValueError("Inconsistent or duplicate trace environment IDs")
        for column, (env_id, case_index, is_active) in enumerate(zip(env_ids, case_ids, active)):
            key = (int(case_index), int(env_id))
            if not is_active:
                ended.add(key)
                continue
            if key in ended:
                # Keep the first episode even if a foreign schema reactivates it.
                continue
            record = {"time_s": float(frame["time_s"])}
            if not finite(record["time_s"]):
                raise ValueError("Active trace time must be finite")
            for name in TRACE_FIELDS:
                if name in frame:
                    if len(frame[name]) != len(env_ids):
                        raise ValueError(f"Trace field {name} does not match environment columns")
                    record[name] = frame[name][column]
                    if not finite(record[name]):
                        raise ValueError(f"Non-finite active trace field {name}")
            groups.setdefault(key, []).append(record)
    for records in groups.values():
        if any(right["time_s"] <= left["time_s"] for left, right in zip(records, records[1:])):
            raise ValueError("Active trace time must strictly increase")
    return groups


def field(records, name):
    return [row[name] for row in records] if all(name in row and row[name] is not None for row in records) else None


def checked_names(names, width, label):
    if names is None:
        return [f"unnamed_{label}_column_{index}" for index in range(width)]
    if len(names) != width or len(set(names)) != len(names):
        raise ValueError(f"{label} body-name manifest disagrees with trace columns")
    return names


def event_at(records, index, value, field_name, body=None):
    row = records[index]
    event = {"field": field_name, "body_name": body, "value": value,
             "time_s": row["time_s"], "root_relative_xyz_m": row.get("root_relative_xyz"),
             "world_vx_m_s": row.get("root_linear_velocity_w", [None])[0],
             "action_second_delta_rms": row.get("action_second_delta_rms"),
             "aggregate_leg_history_peak_n": row.get("shank_force_n"),
             "aggregate_leg_current_n": row.get("current_sample_shank_force_n")}
    return event


def ranked_events(records, values, mask, field_name, limit, body=None):
    indices = [index for index, keep in enumerate(mask) if keep]
    ordered = sorted(indices, key=lambda index: (-values[index], records[index]["time_s"]))[:limit]
    return [event_at(records, index, values[index], field_name, body) for index in ordered]


def cadence(records, policy_dt):
    intervals = [right["time_s"] - left["time_s"] for left, right in zip(records, records[1:])]
    nominal = statistics.median(intervals) if intervals else None
    complete = bool(intervals and policy_dt is not None and
                    all(abs(interval - policy_dt) < max(1e-7, policy_dt * 1e-5) for interval in intervals))
    return {"samples": len(records), "first_time_s": records[0]["time_s"],
            "last_time_s": records[-1]["time_s"], "interval_s": stats(intervals),
            "median_interval_s": nominal, "policy_dt_s": policy_dt,
            "every_policy_boundary_recorded_in_observed_span": complete,
            "classification": "policy_step_trace" if complete else "sparse_or_unknown_trace",
            "limit": "Camera frame rate is independent of trace cadence; sampled peaks are lower bounds."}


def sample_mask(records, policy_dt):
    # Match evaluate_stairs: step >= ceil(1 / dt), with time=(step+1)*dt.
    first_time = (math.ceil(1.0 / policy_dt) + 1) * policy_dt if policy_dt else 1.0 + 1e-9
    return [row["time_s"] + 1e-8 >= first_time for row in records], first_time


def source_outcome(trial, case_index, env_id):
    per_env = trial.get("per_env", {})
    def read(name):
        values = per_env.get(name)
        return values[env_id] if isinstance(values, list) and env_id < len(values) else None
    case = next((item for item in trial.get("cases", []) if item.get("case_index", 0) == case_index), trial)
    return {"completed": read("completed"), "fall": read("fall"), "stall": read("stall"),
            "lateral_escape": read("lateral_escape"), "completion_time_s": read("completion_time_s"),
            "first_episode_measured_duration_s": read("first_episode_measured_duration_s"),
            "initial_root_relative_xyz_m": read("initial_root_relative_xyz_m"),
            "last_measured_root_relative_xyz_m": read("last_measured_root_relative_xyz_m"),
            "case_num_envs": case.get("num_envs"), "case_completion_fraction": case.get("completion_fraction"),
            "case_falls": case.get("falls"), "case_stalls": case.get("stalls"),
            "case_lateral_escapes": case.get("lateral_escapes"), "case_base_contact_envs": case.get("base_contact_envs"),
            "case_metrics": case.get("metrics", {}), "case_contact_sample_counts": case.get("contact_sample_counts"),
            "limit": "Failure labels come from evaluator; falls also include non-escape termination."}


def norm(vector):
    return math.sqrt(sum(component * component for component in vector))


def retractions(records, feet, names, mask, limit):
    outputs = []
    eligible_intervals = sum(mask[index - 1] and mask[index] for index in range(1, len(records)))
    for foot, name in enumerate(names):
        events = []
        for index in range(1, len(records)):
            if not (mask[index - 1] and mask[index]):
                continue
            delta = feet[index][foot][0] - feet[index - 1][foot][0]
            if delta >= 0:
                continue
            event = event_at(records, index, -delta, "sampled_foot_course_x_retraction_m", name)
            event.update({"start_time_s": records[index - 1]["time_s"],
                          "interval_s": records[index]["time_s"] - records[index - 1]["time_s"],
                          "foot_start_relative_xyz_m": feet[index - 1][foot],
                          "foot_end_relative_xyz_m": feet[index][foot],
                          "current_contact_at_end": records[index].get("current_sample_contacts", [None] * len(names))[foot],
                          "history_contact_at_end": records[index].get("contacts", [None] * len(names))[foot]})
            events.append(event)
        outputs.append({"body_name": name, "negative_interval_count": len(events),
                        "eligible_adjacent_intervals": eligible_intervals,
                        "maximum_sampled_retraction_m": max((event["value"] for event in events), default=0.0)
                            if eligible_intervals else None,
                        "largest_events": sorted(events, key=lambda event: -event["value"])[:limit]})
    return {"scope": "Course/world-x foot-center decrease between adjacent recorded root-flight samples; normal gait corrections also qualify.",
            "contact_mechanism_inferred": False, "feet": outputs}


def contact_summary(records, names, speed, mask):
    result = {}
    if speed is not None and any(len(row) != len(names) for row in speed):
        raise ValueError("Foot-speed width disagrees with foot-body manifest")
    for label, key in (("history", "contacts"), ("current", "current_sample_contacts")):
        contact = field(records, key)
        if contact is None:
            result[label] = {"status": "unavailable", "reason": f"{key} was not recorded"}
            continue
        if any(len(row) != len(names) for row in contact):
            raise ValueError(f"{key} width disagrees with foot-body manifest")
        body_rows = []
        for body, name in enumerate(names):
            selected = [index for index, keep in enumerate(mask) if keep]
            touching = [index for index in selected if bool(contact[index][body])]
            transitions = sum(bool(contact[index][body]) != bool(contact[index - 1][body])
                              for index in selected if index and mask[index - 1])
            speeds = [speed[index][body] for index in touching] if speed is not None else []
            body_rows.append({"body_name": name, "eligible_trace_samples": len(selected),
                              "contact_trace_samples": len(touching),
                              "sample_fraction": len(touching) / len(selected) if selected else None,
                              "observed_flag_transitions": transitions,
                              "contact_foot_horizontal_speed_m_s": stats(speeds) if speed is not None else None})
        result[label] = {"status": "available", "bodies": body_rows}
    result["scope"] = "Trace-sample contact flags after evaluator warmup; neither exact contact duration nor exact touchdown timing."
    return result


def pause_runs(records, paused, mask, trace_cadence):
    # Report observed endpoint spans. Never multiply sparse hits into exact durations.
    runs, indices = [], []
    for index in range(len(records) + 1):
        keep = index < len(records) and mask[index] and bool(paused[index])
        contiguous = not indices or index == indices[-1] + 1
        if indices and (not keep or not contiguous):
            start, end = indices[0], indices[-1]
            runs.append({"start_time_s": records[start]["time_s"], "end_time_s": records[end]["time_s"],
                         "observed_endpoint_span_s": records[end]["time_s"] - records[start]["time_s"],
                         "trace_hits": len(indices), "root_start_relative_xyz_m": records[start].get("root_relative_xyz"),
                         "root_end_relative_xyz_m": records[end].get("root_relative_xyz"),
                         "duration_s_if_all_policy_boundaries_recorded": len(indices) * trace_cadence["policy_dt_s"]
                         if trace_cadence["every_policy_boundary_recorded_in_observed_span"] else None})
            indices = []
        if keep:
            indices.append(index)
    return {"runs": runs, "paused_trace_hits": sum(row["trace_hits"] for row in runs),
            "longest_observed_endpoint_span_s": max((row["observed_endpoint_span_s"] for row in runs), default=0.0),
            "limit": "Sparse low-vx hits cannot establish continuous pause duration; use source policy-cadence longest_flight_pause_s."}


def analyze_trace(source, trial, case_index, env_id, records, limit):
    report = source["report"]
    geometry = geometry_for(report, case_index)
    policy_dt = source["policy_dt_s"]
    timing = cadence(records, policy_dt)
    mask, first_time = sample_mask(records, policy_dt)
    root = field(records, "root_relative_xyz")
    feet = field(records, "feet_relative_xyz")
    foot_names = checked_names(source["foot_body_names"], len(feet[0]) if feet else 4, "foot")
    if feet and any(len(row) != len(foot_names) or any(len(position) != 3 for position in row) for row in feet):
        raise ValueError("Foot-position dimensions disagree with foot-body manifest or XYZ coordinates")
    if root and any(len(row) != 3 for row in root):
        raise ValueError("Root-position columns must contain XYZ coordinates")
    first_riser = geometry.get("first_riser_x", geometry["start_x"])
    platform = geometry.get("goal_platform_start_x", geometry["last_riser_x"])
    flight = [keep and row[0] >= first_riser and row[0] < platform for keep, row in zip(mask, root)] if root else [False] * len(records)
    pause_region = [keep and row[0] >= first_riser - 0.25 and row[0] <= platform + 0.25
                    for keep, row in zip(mask, root)] if root else [False] * len(records)
    outcome = source_outcome(trial, case_index, env_id)
    result = {"source": source["path"], "seed": trial["seed"], "case_index": case_index,
              "env_id": env_id, "geometry": geometry, "command_speed_m_s": report.get("command_forward_speed_m_s"),
              "trace_cadence": timing, "first_evaluator_motion_sample_time_s": first_time,
              "post_warmup_trace_samples": sum(mask), "root_flight_trace_samples": sum(flight),
              "foot_body_names": foot_names, "foot_name_source": source["foot_name_source"],
              "outcome": outcome,
              "telemetry_availability": {name: field(records, name) is not None for name in TRACE_FIELDS}}
    selected = [index for index, keep in enumerate(mask) if keep]
    result["progress"] = {"initial_trace_root_relative_xyz_m": root[0] if root else None,
                          "last_trace_root_relative_xyz_m": root[-1] if root else None,
                          "root_trace_displacement_x_m": root[-1][0] - root[0][0] if root else None,
                          "maximum_trace_root_x_m": max(row[0] for row in root) if root else None,
                          "minimum_adjacent_root_flight_delta_x_m": min((root[i][0] - root[i - 1][0]
                              for i in range(1, len(root)) if flight[i] and flight[i - 1]), default=None) if root else None,
                          "limit": "Trace endpoints can precede true terminal state; source outcome retains actual pre-reset endpoint."}
    velocity = field(records, "root_linear_velocity_w")
    posture = field(records, "yaw_roll_pitch")
    commands = field(records, "command_vx_vy_yaw")
    for label, values in (("root velocity", velocity), ("yaw/roll/pitch", posture), ("command", commands)):
        if values is not None and any(len(row) != 3 for row in values):
            raise ValueError(f"{label} columns must have width three")
    tracking = {"world_vx_m_s": stats([velocity[i][0] for i in selected]) if velocity else None,
                "root_flight_world_vx_m_s": stats([velocity[i][0] for i, keep in enumerate(flight) if keep]) if velocity else None,
                "yaw_rotated_xy_command_error_proxy_m_s": None,
                "note": "World vx is reported separately; body-frame XY command error rotates measured world XY using recorded yaw."}
    if velocity and posture and commands:
        errors = []
        for index in selected:
            yaw = posture[index][0]
            world_x, world_y = velocity[index][:2]
            body_x = math.cos(yaw) * world_x + math.sin(yaw) * world_y
            body_y = -math.sin(yaw) * world_x + math.cos(yaw) * world_y
            errors.append(math.hypot(body_x - commands[index][0], body_y - commands[index][1]))
        tracking["yaw_rotated_xy_command_error_proxy_m_s"] = stats(errors)
        tracking["note"] = "Yaw-only projection is a tracking proxy on pitched stairs; authoritative full-body-frame errors are source case metrics."
    result["tracking"] = tracking
    recorded_pause = field(records, "flight_paused")
    if recorded_pause is not None:
        result["pauses"] = pause_runs(records, recorded_pause, mask, timing)
        result["pauses"]["flag_source"] = "recorded flight_paused"
    elif velocity:
        inferred = [velocity[index][0] < 0.05 and pause_region[index] for index in range(len(records))]
        result["pauses"] = pause_runs(records, inferred, mask, timing)
        result["pauses"]["flag_source"] = "inferred evaluator flight region and world vx < 0.05 m/s"
    else:
        result["pauses"] = {"status": "unavailable", "reason": "No pause flag or root velocity"}
    result["pauses"]["source_case_longest_flight_pause_s"] = outcome["case_metrics"].get("longest_flight_pause_s")
    result["action_changes"] = {}
    for name in ("action_delta_rms", "action_second_delta_rms"):
        values = field(records, name)
        result["action_changes"][name] = {"status": "available", "sampled_post_warmup": stats([values[i] for i in selected]),
            "largest_post_warmup_events": ranked_events(records, values, mask, name, limit),
            "largest_root_flight_events": ranked_events(records, values, flight, name, limit),
            "scope": "Recorded one-policy-step differences sampled at trace timestamps; never differences across sparse action snapshots."} if values else {
            "status": "unavailable", "reason": "No recorded policy-step difference telemetry"}
    # Derived action differences are only valid when *all* observed policy boundaries exist.
    actions = field(records, "actions")
    if actions and (not actions[0] or any(len(row) != len(actions[0]) for row in actions)):
        raise ValueError("Action width must be positive and constant within a trace")
    if timing["every_policy_boundary_recorded_in_observed_span"] and actions and len(actions) >= 3:
        second = [math.sqrt(mean([(actions[i][j] - 2 * actions[i - 1][j] + actions[i - 2][j]) ** 2
                                  for j in range(len(actions[i]))])) for i in range(2, len(actions))]
        result["action_changes"]["derived_dense_action_second_delta_rms"] = stats([
            value for i, value in enumerate(second, start=2) if mask[i] and mask[i - 1] and mask[i - 2]])
    else:
        result["action_changes"]["derived_dense_action_second_delta_rms"] = None
    speed = field(records, "foot_horizontal_speed_m_s")
    result["foot_contacts"] = contact_summary(records, foot_names, speed, mask)
    result["foot_retractions"] = retractions(records, feet, foot_names, flight, limit) if feet else {
        "status": "unavailable", "reason": "No foot positions"}
    leg_names = source["leg_body_names"]
    force_current = field(records, "leg_current_normal_force_norm_n")
    force_history = field(records, "leg_history_peak_normal_force_norm_n")
    if leg_names:
        for forces in (force_current, force_history):
            if forces is not None:
                checked_names(leg_names, len(forces[0]), "leg")
                if any(len(row) != len(leg_names) for row in forces):
                    raise ValueError("Leg-force width changed within a trace")
    force_rows = []
    leg_threshold = report.get("thresholds", {}).get("contact_force_n")
    # Always expose eight expected Go2 reward body entries; absent measurements remain null.
    for name in dict.fromkeys((*GO2_LEGS, *(leg_names or []))):
        row = {"body_name": name, "recorded_column": leg_names.index(name) if leg_names and name in leg_names else None}
        for label, values, key in (("current", force_current, "leg_current_normal_force_norm_n"),
                                   ("history_peak", force_history, "leg_history_peak_normal_force_norm_n")):
            if values is not None and row["recorded_column"] is not None:
                norms = [value[row["recorded_column"]] for value in values]
                events = ranked_events(records, norms, mask, key, limit, name)
                row[label] = {"status": "available", "stats_post_warmup_n": stats([norms[i] for i in selected]),
                              "peak_post_warmup": events[0] if events else None, "largest_events": events,
                              "contact_trace_samples": sum(norms[i] > leg_threshold for i in selected) if leg_threshold is not None else None,
                              "eligible_trace_samples": len(selected),
                              "contact_sample_fraction": sum(norms[i] > leg_threshold for i in selected) / len(selected)
                                  if selected and leg_threshold is not None else None}
            else:
                row[label] = {"status": "unavailable", "peak_post_warmup": None,
                              "reason": "Named per-body force was not recorded; aggregate shank force cannot identify this body"}
        force_rows.append(row)
    result["selected_leg_forces"] = {"expected_go2_body_count": 8, "recorded_body_names": leg_names,
        "body_order_source": "report.leg_body_names" if leg_names else None,
        "contact_threshold_n": leg_threshold,
        "measurement": "Per-body world-frame net normal-force vector norm; tangential friction excluded",
        "bodies": force_rows}
    result["aggregate_contacts"] = {}
    for key in ("base_force_n", "shank_force_n", "current_sample_base_force_n", "current_sample_shank_force_n"):
        values = field(records, key)
        result["aggregate_contacts"][key] = {"status": "available", "stats_post_warmup_n": stats([values[i] for i in selected]),
            "peak_post_warmup": (ranked_events(records, values, mask, key, 1) or [None])[0],
            "largest_root_flight_events": ranked_events(records, values, flight, key, limit)} if values else {
            "status": "unavailable", "reason": "Not recorded"}
    return result


def case_records(source, acceptance):
    rows = []
    report = source["report"]
    for trial in report["trials"]:
        for case in trial.get("cases", [trial]):
            index = case.get("case_index", 0)
            row = {"source": source["path"], "seed": trial["seed"], "case_index": index,
                   "geometry": case.get("geometry", geometry_for(report, index)),
                   "command_speed_m_s": report.get("command_forward_speed_m_s"),
                   "num_envs": case.get("num_envs"), "completion_fraction": case.get("completion_fraction"),
                   "falls": case.get("falls"), "stalls": case.get("stalls"), "lateral_escapes": case.get("lateral_escapes"),
                   "base_contact_envs": case.get("base_contact_envs"), "metrics": case.get("metrics", {}),
                   "source_trial_failure_reason": trial.get("failure_reason"),
                   "source_contact_sample_counts": case.get("contact_sample_counts"),
                   "mean_max_progress_m": case.get("mean_max_progress_m", trial.get("mean_max_directed_progress_m"))}
            n = row["num_envs"] or 0
            required = acceptance["minimum_environments_per_case_per_seed"]
            completion = row["completion_fraction"]
            failures_ok = n > 0 and all(row.get(name) is not None and row[name] / n <= acceptance[f"maximum_{label}_fraction_each_case_each_seed"]
                                        for name, label in (("falls", "fall"), ("stalls", "stall"), ("lateral_escapes", "lateral_escape")))
            row["declared_per_case_traversal_gate_passed"] = bool(n >= required and completion is not None and
                completion >= acceptance["core_completion_fraction_each_case_each_seed"] and failures_ok and
                row["base_contact_envs"] is not None and row["base_contact_envs"] <= acceptance["maximum_base_contact_envs"] and
                trial.get("failure_reason") is None)
            rows.append(row)
    return rows


def protocol_signature(source):
    report, config = source["report"], source["config"]
    return {"controller": source["controller"], "heading_control": report.get("heading_control"),
            "randomized_reset": report.get("randomized_reset"), "dynamics_randomized": report.get("dynamics_randomized"),
            "source_thresholds": report.get("thresholds"), "robot_usd": config.get("robot_usd"),
            "physics_dt_s": source["physics_dt_s"], "policy_dt_s": source["policy_dt_s"],
            "friction_override": config.get("friction_override"), "domain_profile": config.get("domain_randomization"),
            "contact_sampling": report.get("contact_sampling")}


def compare_sources(sources, case_rows):
    comparisons = []
    for right_index in range(1, len(sources)):
        for left_index in range(right_index):
            left, right = sources[left_index], sources[right_index]
            lookup = {(row["seed"], row["case_index"], geometry_key(row["geometry"]), row["command_speed_m_s"]): row
                      for row in case_rows if row["source"] == left["path"]}
            left_protocol, right_protocol = protocol_signature(left), protocol_signature(right)
            differences = [key for key in left_protocol if left_protocol[key] != right_protocol[key]]
            left_trials = {trial["seed"]: trial for trial in left["report"]["trials"]}
            right_trials = {trial["seed"]: trial for trial in right["report"]["trials"]}
            for row in case_rows:
                if row["source"] != right["path"]:
                    continue
                key = (row["seed"], row["case_index"], geometry_key(row["geometry"]), row["command_speed_m_s"])
                if row["command_speed_m_s"] is None or row["seed"] is None:
                    continue
                baseline = lookup.get(key)
                if baseline is None:
                    continue
                left_initial = left_trials[row["seed"]].get("per_env", {}).get("initial_root_relative_xyz_m")
                right_initial = right_trials[row["seed"]].get("per_env", {}).get("initial_root_relative_xyz_m")
                reset_match = left_initial == right_initial if left_initial is not None and right_initial is not None else None
                material_available = all(source["material_evidence"].get("status") == "available" and
                    all(source["material_evidence"].get(key) is not None for key in
                        ("static_friction", "dynamic_friction", "restitution")) for source in (left, right))
                material_match = left["material_evidence"] == right["material_evidence"] if material_available else None
                physical_available = all(isinstance(source["physical_evidence"].get(key), dict) and
                    source["physical_evidence"][key].get("status") == "available"
                    for source in (left, right) for key in
                    ("base_mass_kg", "base_inertia_kg_m2", "base_com", "actuator_pd"))
                physical_match = left["physical_evidence"] == right["physical_evidence"] if physical_available else None
                both_competent = baseline["declared_per_case_traversal_gate_passed"] and row["declared_per_case_traversal_gate_passed"]
                evidence_matches = not differences and reset_match is True and material_match is True and physical_match is True
                deltas = {name: row["metrics"][name] - baseline["metrics"][name] for name in MOTION_METRICS
                          if isinstance(row["metrics"].get(name), (int, float)) and isinstance(baseline["metrics"].get(name), (int, float))}
                comparisons.append({"left_source": left["path"], "right_source": right["path"],
                    "direction": row["geometry"]["direction"], "geometry": row["geometry"], "seed": row["seed"], "case_index": row["case_index"],
                    "command_speed_m_s": row["command_speed_m_s"], "protocol_difference_fields": differences,
                    "initial_root_arrays_exactly_match": reset_match, "foot_material_readback_matches": material_match,
                    "initial_domain_readback_matches": physical_match,
                    "matching_evidence_limit": "Only saved fields checked; per-environment full initial state, terrain material readback and per-trial reset-gain readback may be absent.",
                    "left_outcomes": {key: baseline[key] for key in ("completion_fraction", "falls", "stalls", "lateral_escapes", "mean_max_progress_m")},
                    "right_outcomes": {key: row[key] for key in ("completion_fraction", "falls", "stalls", "lateral_escapes", "mean_max_progress_m")},
                    "right_minus_left_source_metric_deltas": deltas,
                    "both_cases_pass_declared_traversal_gate": both_competent,
                    "controlled_motion_comparison_eligible_from_saved_evidence": bool(evidence_matches and both_competent),
                    "interpretation": "Report action/jerk changes together with tracking and contact; no smoothness certificate." if evidence_matches and both_competent else
                        "Descriptive only: a failing/stalled comparator or incomplete matching evidence cannot establish smoother competent traversal."})
    return comparisons


def analyze(sources, acceptance, limit=5, selected_seed=None, selected_case=None):
    traces, cases = [], []
    source_metadata = []
    for source in sources:
        cases.extend(case_records(source, acceptance))
        for trial in source["report"]["trials"]:
            if selected_seed is not None and trial["seed"] != selected_seed:
                continue
            for (case_index, env_id), records in sorted(extract_environments(trial).items()):
                if selected_case is not None and selected_case != case_index:
                    continue
                traces.append(analyze_trace(source, trial, case_index, env_id, records, limit))
        source_metadata.append({key: source[key] for key in ("path", "checkpoint", "controller", "policy_dt_s", "physics_dt_s",
            "foot_body_names", "foot_name_source", "leg_body_names", "domain_readback_path")})
    comparisons = compare_sources(sources, cases)
    if selected_seed is not None:
        cases = [row for row in cases if row["seed"] == selected_seed]
        comparisons = [row for row in comparisons if row["seed"] == selected_seed]
    if selected_case is not None:
        cases = [row for row in cases if row["case_index"] == selected_case]
        comparisons = [row for row in comparisons if row["case_index"] == selected_case]
    return {"schema_version": 1, "scope": "CPU-only saved first-episode trace analysis; no acceptance thresholds changed",
            "acceptance_reference": acceptance, "sources": source_metadata,
            "source_case_metrics": cases, "traces": traces, "matched_comparisons": comparisons,
            "limits": ["Source case statistics cover all measured policy steps; trace statistics cover only recorded active samples.",
                "Current/history contact and foot-link horizontal speed are proxies, not exact scraping/slip duration.",
                "Sparse action snapshots are never differentiated; recorded policy-step action differences are retained.",
                "Named leg force is never reconstructed from aggregate shank force.",
                "Low action variation in a stalled policy does not establish smooth traversal.",
                "This analysis does not replace continuous video review, unseen-case validation or material/dynamics tests."]}


def fmt(value, digits=3):
    return "unavailable" if value is None else f"{value:.{digits}f}" if isinstance(value, float) else str(value)


def write_markdown(report, path):
    lines = ["# Saved staircase motion analysis", "", report["scope"] + ".", "",
             "Trace peaks are sampled observations. Existing evaluator case metrics and traversal outcomes remain authoritative.", "",
             "| Source / seed / case / env | Cadence s | Completed / stall / escape | Sampled action second peak | Sampled leg aggregate peak N | Largest flight foot retraction m |", "|---|---:|---|---:|---:|---:|"]
    for trace in report["traces"]:
        outcome = trace["outcome"]
        action = trace["action_changes"]["action_second_delta_rms"].get("sampled_post_warmup", {}).get("max")
        force = trace["aggregate_contacts"]["shank_force_n"].get("stats_post_warmup_n", {}).get("max")
        retractions = trace["foot_retractions"].get("feet", [])
        largest = max((foot["maximum_sampled_retraction_m"] for foot in retractions
                       if foot["maximum_sampled_retraction_m"] is not None), default=None)
        label = f"{Path(trace['source']).parent.name} / {trace['seed']} / {trace['case_index']} / {trace['env_id']}"
        lines.append(f"| {label} | {fmt(trace['trace_cadence']['median_interval_s'])} | {outcome['completed']} / {outcome['stall']} / {outcome['lateral_escape']} | {fmt(action)} | {fmt(force)} | {fmt(largest)} |")
    lines.extend(("", "Named current/history body peaks and their times/positions are in JSON and CSV. Unrecorded per-leg values are unavailable.", "",
                  "| Matched seed / case | Left completion | Right completion | Right − left action second RMS | Right − left jerk RMS | Eligible controlled motion comparison |", "|---|---:|---:|---:|---:|---|"))
    for row in report["matched_comparisons"]:
        delta = row["right_minus_left_source_metric_deltas"]
        lines.append(f"| {row['seed']} / {row['case_index']} | {fmt(row['left_outcomes']['completion_fraction'])} | {fmt(row['right_outcomes']['completion_fraction'])} | {fmt(delta.get('action_second_delta_rms'))} | {fmt(delta.get('linear_jerk_rms_m_s3'))} | {row['controlled_motion_comparison_eligible_from_saved_evidence']} |")
    lines.extend(("", "Comparison direction follows input order. Failing/stalled comparators and mismatched construction evidence are labeled descriptive only.", ""))
    lines.extend("- " + note for note in report["limits"])
    path.write_text("\n".join(lines) + "\n")


def write_csv(report, path):
    columns = ("source", "seed", "case_index", "env_id", "body_name", "measure", "status", "value",
               "time_s", "start_time_s", "root_x_m", "root_y_m", "root_z_m", "foot_start_x_m", "foot_end_x_m")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for trace in report["traces"]:
            common = {key: trace[key] for key in ("source", "seed", "case_index", "env_id")}
            for body in trace["selected_leg_forces"]["bodies"]:
                for measure in ("current", "history_peak"):
                    event = body[measure].get("peak_post_warmup") or {}
                    root = event.get("root_relative_xyz_m") or [None] * 3
                    writer.writerow({**common, "body_name": body["body_name"], "measure": measure,
                        "status": body[measure]["status"], "value": event.get("value"), "time_s": event.get("time_s"),
                        **dict(zip(("root_x_m", "root_y_m", "root_z_m"), root))})
            for foot in trace["foot_retractions"].get("feet", []):
                for event in foot["largest_events"][:1]:
                    root = event.get("root_relative_xyz_m") or [None] * 3
                    writer.writerow({**common, "body_name": foot["body_name"], "measure": event["field"],
                        "status": "sampled", "value": event["value"], "time_s": event["time_s"], "start_time_s": event["start_time_s"],
                        **dict(zip(("root_x_m", "root_y_m", "root_z_m"), root)),
                        "foot_start_x_m": event["foot_start_relative_xyz_m"][0], "foot_end_x_m": event["foot_end_relative_xyz_m"][0]})


def plot_events(report, output):
    # Event-oriented overview complements plot-stair-eval's trajectory panels.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    traces = report["traces"]
    figure, axes = plt.subplots(2, 1, figsize=(max(8, min(24, len(traces) * 0.45)), 7), constrained_layout=True)
    source_indices = {source["path"]: index + 1 for index, source in enumerate(report["sources"])}
    labels, action, force = [], [], []
    for trace in traces:
        labels.append(f"S{source_indices[trace['source']]} {trace['geometry']['direction']}\ns{trace['seed']} c{trace['case_index']} e{trace['env_id']}")
        action.append(trace["action_changes"]["action_second_delta_rms"].get("sampled_post_warmup", {}).get("max"))
        force.append(trace["aggregate_contacts"]["shank_force_n"].get("stats_post_warmup_n", {}).get("max"))
    for axis, values, label in zip(axes, (action, force), ("Action second-difference\nsampled peak", "Aggregate leg-history force\nsampled peak (N)")):
        points = [(index, value) for index, value in enumerate(values) if value is not None]
        axis.scatter([p[0] for p in points], [p[1] for p in points], color="#1768ac", s=20)
        axis.set_ylabel(label)
        axis.grid(alpha=0.2)
        ticks = list(range(0, len(labels), max(1, math.ceil(len(labels) / 24))))
        axis.set_xticks(ticks, labels=[labels[index] for index in ticks], rotation=45, ha="right", fontsize=8)
        axis.margins(x=0.08)
    figure.suptitle("Sampled event peaks; source numbers follow the accompanying JSON\nInspect completion, tracking and cadence alongside motion", fontsize=12)
    figure.savefig(output.with_suffix(".png"), dpi=150)
    figure.savefig(output.with_suffix(".pdf"))
    plt.close(figure)


def self_test():
    import unittest

    class AnalysisTests(unittest.TestCase):
        def source(self):
            geometry = {"direction": "asc", "start_x": 0.0, "first_riser_x": 1.0, "last_riser_x": 2.0,
                        "goal_platform_start_x": 2.5, "goal_x": 3.0, "num_steps": 6, "step_height": 0.16}
            names = list(reversed(GO2_LEGS))
            rows = []
            for index in range(8):
                root = [1.1 + index * .005, 0.0, 0.5]
                rows.append({"time_s": 1.02 + index * .02, "root_relative_xyz": root,
                    "root_linear_velocity_w": [.3, 0., 0.], "yaw_roll_pitch": [0., 0., 0.],
                    "command_vx_vy_yaw": [.3, 0., 0.], "feet_relative_xyz": [[1.2 - index * .01, 0., .1]] * 4,
                    "contacts": [True] * 4, "current_sample_contacts": [False] * 4,
                    "foot_horizontal_speed_m_s": [.2] * 4, "flight_paused": False,
                    "action_second_delta_rms": .1 * index, "actions": [float(index * index)] * 12,
                    "leg_current_normal_force_norm_n": [float(i + index) for i in range(8)],
                    "leg_history_peak_normal_force_norm_n": [float(20 + i + index) for i in range(8)]})
            source = {"path": "synthetic/result.json", "report": {"geometry": geometry, "command_forward_speed_m_s": .3,
                      "thresholds": {"contact_force_n": 1.0}},
                      "policy_dt_s": .02, "foot_body_names": ["FL_foot", "FR_foot", "RL_foot", "RR_foot"],
                      "foot_name_source": "synthetic", "leg_body_names": names}
            trial = {"seed": 29, "num_envs": 32, "per_env": {"completed": [False], "stall": [True]}}
            return source, trial, rows

        def test_dense_named_force_peaks_keep_body_identity_and_position(self):
            source, trial, rows = self.source()
            result = analyze_trace(source, trial, 0, 0, rows, 2)
            self.assertTrue(result["trace_cadence"]["every_policy_boundary_recorded_in_observed_span"])
            body = result["selected_leg_forces"]["bodies"][0]
            self.assertEqual(body["body_name"], "FL_thigh")
            self.assertEqual(body["recorded_column"], 7)
            self.assertEqual(body["current"]["peak_post_warmup"]["value"], 14.)
            self.assertEqual(body["history_peak"]["peak_post_warmup"]["value"], 34.)
            self.assertAlmostEqual(body["current"]["peak_post_warmup"]["time_s"], 1.16)
            self.assertEqual(body["current"]["peak_post_warmup"]["root_relative_xyz_m"], rows[-1]["root_relative_xyz"])
            self.assertEqual(body["current"]["contact_trace_samples"], 8)
            self.assertEqual(body["current"]["contact_sample_fraction"], 1.)
            self.assertAlmostEqual(result["action_changes"]["derived_dense_action_second_delta_rms"]["rms"], 2.)

        def test_sparse_actions_are_not_differentiated_or_pause_duration_invented(self):
            source, trial, rows = self.source()
            rows = rows[::2]
            for row in rows:
                row["flight_paused"] = True
            result = analyze_trace(source, trial, 0, 0, rows, 2)
            self.assertFalse(result["trace_cadence"]["every_policy_boundary_recorded_in_observed_span"])
            self.assertIsNone(result["action_changes"]["derived_dense_action_second_delta_rms"])
            self.assertIsNone(result["pauses"]["runs"][0]["duration_s_if_all_policy_boundaries_recorded"])

        def test_missing_named_force_stays_unavailable_and_current_contact_separate(self):
            source, trial, rows = self.source()
            source["leg_body_names"] = None
            result = analyze_trace(source, trial, 0, 0, rows, 2)
            self.assertEqual(len(result["selected_leg_forces"]["bodies"]), 8)
            self.assertTrue(all(body["current"]["status"] == "unavailable" for body in result["selected_leg_forces"]["bodies"]))
            self.assertEqual(result["foot_contacts"]["current"]["bodies"][0]["contact_trace_samples"], 0)
            self.assertEqual(result["foot_contacts"]["history"]["bodies"][0]["contact_trace_samples"], 8)

        def test_first_episode_does_not_reactivate(self):
            frames = [{"time_s": t, "env_ids": [0], "case_ids": [0], "active": [active]} for t, active in
                      ((.02, True), (.04, False), (.06, True))]
            result = extract_environments({"trace": frames})
            self.assertEqual(len(result[(0, 0)]), 1)

        def test_manifest_and_timestamp_inconsistency_rejected(self):
            with self.assertRaises(ValueError):
                checked_names(["FL_calf", "FL_calf"], 2, "leg")
            with self.assertRaises(ValueError):
                extract_environments({"trace": [{"time_s": .02, "active": [True]}, {"time_s": .02, "active": [True]}]})
            with self.assertRaises(ValueError):
                extract_environments({"trace": [{"time_s": float("inf"), "active": [True]}]})
            source, trial, rows = self.source()
            rows[0]["current_sample_contacts"] = [False]
            with self.assertRaises(ValueError):
                analyze_trace(source, trial, 0, 0, rows, 2)

        def test_no_root_flight_interval_is_not_zero_retraction_evidence(self):
            source, trial, rows = self.source()
            for row in rows:
                row["root_relative_xyz"][0] = .5
            result = analyze_trace(source, trial, 0, 0, rows, 2)
            self.assertEqual(result["root_flight_trace_samples"], 0)
            self.assertTrue(all(foot["maximum_sampled_retraction_m"] is None for foot in result["foot_retractions"]["feet"]))

        def test_comparisons_require_matching_speed_seed_case_geometry_and_competence(self):
            import copy
            source, _, _ = self.source()
            source.update({"controller": "policy", "config": {}, "physics_dt_s": .005,
                           "material_evidence": {}, "physical_evidence": {}, "domain_readback_path": None})
            source["report"]["trials"] = [{"seed": 29}]
            right = copy.deepcopy(source)
            right["path"] = "candidate/result.json"
            row = {"source": source["path"], "seed": 29, "case_index": 0,
                   "geometry": source["report"]["geometry"], "command_speed_m_s": .3,
                   "completion_fraction": 0., "falls": 0, "stalls": 32, "lateral_escapes": 0,
                   "mean_max_progress_m": .5, "metrics": {"action_second_delta_rms": .001},
                   "declared_per_case_traversal_gate_passed": False}
            candidate = {**copy.deepcopy(row), "source": right["path"], "completion_fraction": 1., "stalls": 0,
                         "declared_per_case_traversal_gate_passed": True}
            comparisons = compare_sources([source, right], [row, candidate])
            self.assertEqual(len(comparisons), 1)
            self.assertIsNone(comparisons[0]["initial_domain_readback_matches"])
            self.assertIsNone(comparisons[0]["foot_material_readback_matches"])
            self.assertFalse(comparisons[0]["controlled_motion_comparison_eligible_from_saved_evidence"])
            self.assertIn("stalled", comparisons[0]["interpretation"])
            for key, value in (("command_speed_m_s", .5), ("seed", 47), ("case_index", 1), ("command_speed_m_s", None)):
                with self.subTest(key=key, value=value):
                    self.assertEqual(compare_sources([source, right], [row, {**candidate, key: value}]), [])
            altered = {**candidate, "geometry": {**candidate["geometry"], "step_height": .2}}
            self.assertEqual(compare_sources([source, right], [row, altered]), [])

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AnalysisTests)
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="*", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reproduction/stair-motion-analysis"))
    parser.add_argument("--controller", choices=("policy", "zero_action"), default="policy")
    parser.add_argument("--acceptance", type=Path, default=Path(__file__).with_name("stair-acceptance.json"))
    parser.add_argument("--seed", type=int)
    parser.add_argument("--case", type=int)
    parser.add_argument("--top-events", type=int, default=5)
    parser.add_argument("--plot", action="store_true", help="Optional event-peak overview; requires matplotlib")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(0 if self_test() else 1)
    if not args.results or args.top_events < 1:
        parser.error("Provide result paths and a positive --top-events count")
    try:
        acceptance = read_json(args.acceptance)
        if not acceptance:
            raise ValueError("The declared acceptance JSON is required")
        sources = [load_source(path, args.controller) for path in args.results]
        report = analyze(sources, acceptance, args.top_events, args.seed, args.case)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.with_suffix(".json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        write_markdown(report, args.output.with_suffix(".md"))
        write_csv(report, args.output.with_suffix(".csv"))
        if args.plot:
            plot_events(report, args.output)
    except (KeyError, ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({"output": str(args.output), "sources": len(sources), "active_environment_traces": len(report["traces"]),
                      "source_cases": len(report["source_case_metrics"]), "matched_case_seed_comparisons": len(report["matched_comparisons"])}))


if __name__ == "__main__":
    main()
