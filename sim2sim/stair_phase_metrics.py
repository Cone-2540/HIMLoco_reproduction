#!/usr/bin/env python3
"""Locate calf contacts and persistent joint bias in existing stair traces.

Use the generated XML and saved goal to define the staircase, not a hardcoded
start. Failed/short episodes stay in the output; empty phases are unavailable.
No policy or simulator rollout is executed by this analysis.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


def geometry(directory, result):
    if result["arguments"]["terrain"] == "flat":
        return None
    world = ET.parse(directory / "model.xml").getroot().find("worldbody")
    terrain = result["arguments"]["terrain"]
    first = next(g for g in world.findall("geom") if g.get("name") == (
        "step_0" if terrain == "asc" else "start_platform"))
    center = float(first.get("pos").split()[0])
    half = float(first.get("size").split()[0])
    start = center - half if terrain == "asc" else center + half
    end = float(result["goal_x"]) - .08
    if not np.isclose(end - start, result["arguments"]["steps"] * result["arguments"]["depth"]):
        raise ValueError("Saved staircase XML and goal disagree")
    return start, end


def phase_rows(rows, bounds):
    selected = {name: [] for name in ("startup", "approach", "flight", "landing")}
    for row in rows:
        if row["time"] < 2:
            selected["startup"].append(row)
            continue
        if bounds is None:
            selected["approach"].append(row)
        elif row["position"][0] < bounds[0] - .25:
            selected["approach"].append(row)
        elif row["position"][0] <= bounds[1] + .25:
            selected["flight"].append(row)
        else:
            selected["landing"].append(row)
    return selected


def phase_summary(rows):
    if not rows:
        return {"available": False, "samples": 0}
    q = np.asarray([r["joint_position"] for r in rows])
    quaternion = np.asarray([r["quaternion_wxyz"] for r in rows])
    w, x, y, z = quaternion.T
    roll = np.rad2deg(np.arctan2(2 * (w*x + y*z), 1 - 2 * (x*x + y*y)))
    peak = np.asarray([r["calf_peak_normal_force_n"] for r in rows])
    calf = np.asarray([r["calf_loaded_contact"] for r in rows])
    result = {"available": True, "samples": len(rows),
              "first_time_s": rows[0]["time"], "last_time_s": rows[-1]["time"],
              "first_root_x_m": rows[0]["position"][0], "last_root_x_m": rows[-1]["position"][0],
              "mean_roll_deg": float(roll.mean()), "max_abs_roll_deg": float(np.abs(roll).max()),
              "front_thigh_signed_mean_bias_rad": float((q[:, 4] - q[:, 5]).mean()),
              "front_calf_signed_mean_bias_rad": float((q[:, 8] - q[:, 9]).mean()),
              "any_calf_loaded_fraction": float(calf.mean()),
              "any_calf_max_peak_normal_force_n": float(peak.max())}
    if all("calf_peak_normal_force_by_leg_n" in r for r in rows):
        force = np.asarray([r["calf_peak_normal_force_by_leg_n"] for r in rows])
        result.update(calf_loaded_fraction_by_leg=(force > 1).mean(0).tolist(),
                      calf_max_peak_normal_force_n_by_leg=force.max(0).tolist())
    return result


def summarize(directory):
    result = json.loads((directory / "result.json").read_text())
    rows = json.loads((directory / "trace.json").read_text())
    expected = [leg + "_" + part + "_joint" for part in ("hip", "thigh", "calf")
                for leg in ("FL", "FR", "RL", "RR")]
    if result["policy_joint_order"] != expected:
        raise ValueError("Unsupported joint order")
    bounds = geometry(directory, result)
    return {"source": str(directory.resolve()), "success": result["success"], "reason": result["reason"],
            "policy_sha256": result["policy_sha256"], "seed": result["arguments"]["seed"],
            "terrain": result["arguments"]["terrain"], "command": result["arguments"]["command"],
            "trace_sha256": hashlib.sha256((directory / "trace.json").read_bytes()).hexdigest(),
            "stair_flight_x_bounds_m": list(bounds) if bounds else None,
            "phases": {name: phase_summary(group) for name, group in phase_rows(rows, bounds).items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.matrix:
        matrix = json.loads((args.directory / "matrix.json").read_text())
        directories = [Path(t["result_file"]).parent for t in matrix["trials"]]
    else:
        directories = [args.directory]
    report = {"scope": "Saved post-step root/joint poses and preceding 20ms contact maxima; no new physics.",
              "phase_definition": "startup t<2s; thereafter approach/flight/landing by saved XML root X with 0.25m margin",
              "joint_bias_scope": "phase mean, allows alternating steps; flight bias can reflect different treads",
              "contact_scope": "interval force >1N; peak normal force is not impact impulse or measured damage",
              "leg_order": ["FL", "FR", "RL", "RR"], "trials": [summarize(d) for d in directories]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
