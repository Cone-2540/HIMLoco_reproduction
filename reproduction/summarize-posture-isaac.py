#!/usr/bin/env python3
"""Analyze existing sparse Isaac telemetry without changing acceptance metrics."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def summarize(path):
    report = json.loads(path.read_text())
    policy = report["policy"]
    names = policy["leg_body_names"]
    indices = [names.index(leg + "_calf") for leg in ("FL", "FR", "RL", "RR")]
    phases = {name: [] for name in ("approach", "flight", "landing")}
    for trial in policy["trials"]:
        for row in trial["trace"]:
            for i, case in enumerate(row["case_ids"]):
                if row["time_s"] < 1.0 or not row["active"][i]:
                    continue
                geom = policy["geometry"][case]
                x = row["root_relative_xyz"][i][0]
                phase = "approach" if x < geom["first_riser_x"] - .25 else (
                    "landing" if x > geom["goal_platform_start_x"] + .25 else "flight")
                quaternions = np.asarray(row["leg_link_quat_w_xyzw"][i])[indices]
                cosine = 1 - 2 * (quaternions[:, 0] ** 2 + quaternions[:, 1] ** 2)
                phases[phase].append(np.rad2deg(np.arccos(np.clip(cosine, -1, 1))))
    summaries = {}
    for phase, values in phases.items():
        if values:
            data = np.asarray(values)
            summaries[phase] = {"sparse_environment_samples": len(values),
                                "mean_shank_axis_angle_deg": data.mean(0).tolist(),
                                "p95_shank_axis_angle_deg": np.percentile(data, 95, axis=0).tolist(),
                                "fraction_angle_gt70": (data > 70).mean(0).tolist()}
    return {"source": str(path.resolve()), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "checkpoint": report.get("checkpoint"), "leg_order": ["FL", "FR", "RL", "RR"],
            "phases": summaries,
            "completion": [{"seed": t["seed"], "completions": t["completions"], "num_envs": t["num_envs"],
                            "cases": [{"case_index": c["case_index"], "completions": c["completions"],
                                       "num_envs": c["num_envs"], "metrics": c["metrics"]} for c in t["cases"]]}
                           for t in policy["trials"]],
            "scope": "active sparse trace after 1 s; world down vs calf-link local -Z; not continuous contact exposure or geometric clearance"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summarize(args.result), indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
