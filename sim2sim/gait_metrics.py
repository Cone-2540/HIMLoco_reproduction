#!/usr/bin/env python3
"""Saved-pose foot motion diagnostics with explicit force and time alignment."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def summarize(directory, warmup=2.0):
    result = json.loads((directory / "result.json").read_text())
    all_rows = json.loads((directory / "trace.json").read_text())
    rows = [r for r in all_rows if r["time"] >= warmup]
    if len(rows) < 2 or not all("foot_peak_normal_force_by_leg_n" in r for r in rows):
        return {"source": str(directory.resolve()), "available": False,
                "reason": "Missing post-warmup per-leg force telemetry"}
    times = np.asarray([r["time"] for r in rows])
    dt = np.diff(times)
    if not np.all(dt > 0):
        raise ValueError("Trace timestamps must be strictly increasing")
    foot = np.asarray([r["foot_position"] for r in rows])
    force = np.asarray([r["foot_peak_normal_force_by_leg_n"] for r in rows])
    speed = np.linalg.norm(np.diff(foot[..., :2], axis=0) / dt[:, None, None], axis=-1)
    gates = {}
    for threshold in (1, 10, 30, 50):
        # Require contact force in BOTH neighboring policy intervals; a single
        # peak cannot make the whole position difference a loaded stance sample.
        loaded = (force[:-1] > threshold) & (force[1:] > threshold)
        gates[str(threshold)] = {
            "samples_by_leg": loaded.sum(0).tolist(),
            "mean_foot_center_xy_speed_m_s": [float(speed[loaded[:, i], i].mean())
                                              if loaded[:, i].any() else None for i in range(4)],
            "fraction_speed_gt_0_10_m_s": [float((speed[loaded[:, i], i] > .10).mean())
                                           if loaded[:, i].any() else None for i in range(4)],
        }
    return {"source": str(directory.resolve()), "available": True,
            "policy_sha256": result["policy_sha256"],
            "trace_sha256": hashlib.sha256((directory / "trace.json").read_bytes()).hexdigest(),
            "terrain": result["arguments"]["terrain"], "command": result["arguments"]["command"],
            "success": result["success"], "leg_order": ["FL", "FR", "RL", "RR"],
            "warmup_s": warmup, "samples": len(rows),
            "force_gates_n": gates,
            "foot_center_world_z_p95_minus_p5_cm": (100*(np.percentile(foot[..., 2], 95, axis=0)
                                                        - np.percentile(foot[..., 2], 5, axis=0))).tolist(),
            "loaded_foot_interval_fraction": (force > 1).mean(0).tolist(),
            "scope": "finite difference of post-step foot centers; gated by >threshold peak normal force in both adjacent 20 ms intervals; proxy, not contact-point tangential slip; world-z span is only a swing proxy on flat terrain"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    p.add_argument("--matrix", action="store_true")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.matrix:
        matrix = json.loads((a.directory / "matrix.json").read_text())
        directories = [Path(t["result_file"]).parent for t in matrix["trials"]]
    else:
        directories = [a.directory]
    trials = [summarize(directory) for directory in directories]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps({"trials": trials}, indent=2) + "\n")
    print(a.output)


if __name__ == "__main__":
    main()
