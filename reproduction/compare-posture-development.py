#!/usr/bin/env python3
"""Archive and compare recorded development evidence, without running policies."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LOG = Path.home() / "robotics/logs"
OUT = ROOT / "reproduction"


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(matrix_path, posture_path):
    matrix, posture = read(matrix_path), read(posture_path)
    flat_all = [t for t in posture["trials"] if t.get("terrain") == "flat"]
    flat = [t for t in flat_all if t.get("samples", 0) > 0]
    result = {
        "matrix_source": str(matrix_path.resolve()),
        "matrix_sha256": digest(matrix_path),
        "posture_source": str(posture_path.resolve()),
        "posture_sha256": digest(posture_path),
        "passed": matrix["passed"], "total": matrix["total"],
        "seed_start": matrix["seed_start"],
        "seeds_per_case": matrix["seeds_per_case"],
        "failed_trials": [{k: t[k] for k in ("case", "seed", "reason")}
                          for t in matrix["trials"] if not t["success"]],
        "cases": matrix["summary"],
        "flat_posture": {},
        "flat_trials_without_post_warmup_posture": len(flat_all) - len(flat),
        "scope": "development only; equal trial weighting; 20 ms contact intervals, not contact impulse",
    }
    for key in ("mean_shank_angle_deg", "fraction_shank_angle_gt70",
                "mean_knee_clearance_cm", "p5_knee_clearance_cm", "mean_root_world_z_m"):
        result["flat_posture"][key] = np.mean([t[key] for t in flat], axis=0).tolist() if flat else None
    for name, rows in (
        ("flat", [s for s in matrix["summary"] if s["case"].startswith("flat")]),
        ("ascending", [s for s in matrix["summary"] if s["case"].startswith("asc")]),
        ("descending", [s for s in matrix["summary"] if s["case"].startswith("desc")]),
    ):
        result[name] = {
            "passed": sum(s["passed"] for s in rows), "total": sum(s["total"] for s in rows),
            "mean_loaded_calf_interval_fraction": float(np.mean([s["mean_calf_loaded_contact_fraction"] for s in rows])),
            "maximum_calf_normal_force_n": max(s["maximum_calf_normal_force_n"] for s in rows),
            "mean_xy_velocity_mae_m_s": float(np.mean([s["mean_xy_velocity_mae_m_s"] for s in rows])),
        }
    return result


def add_diagnostics(row, suite, matrix_path, archive_name=None):
    directory = matrix_path.parent.parent
    # Baseline/weak-arm telemetry predates optional exact-input/per-leg data.
    stem = matrix_path.parent.name
    result = row["suites"][suite]
    for analyzer in ("symmetry_metrics", "gait_metrics"):
        path = directory / f"{stem}-{analyzer}.json"
        if not path.exists():
            continue
        document = read(path)
        flat = [t for t in document["trials"] if t.get("terrain") == "flat"]
        if analyzer == "symmetry_metrics":
            missing = sum(t.get("samples_after_2s", 0) == 0 for t in flat)
            result["flat_trials_without_post_warmup_symmetry"] = missing
            flat = [t for t in flat if t.get("samples_after_2s", 0) > 0]
        if analyzer == "symmetry_metrics" and flat:
            result["flat_symmetry"] = {
                "mean_front_thigh_signed_mirror_bias_rad": float(np.mean([
                    t["mirror_bias"]["thigh"]["mean_signed_mirror_difference_rad"][0] for t in flat])),
                "mean_front_calf_signed_mirror_bias_rad": float(np.mean([
                    t["mirror_bias"]["calf"]["mean_signed_mirror_difference_rad"][0] for t in flat])),
                "mean_front_foot_signed_longitudinal_mirror_difference_m": float(np.mean([
                    t["mean_mirrored_foot_difference_m"][0][0] for t in flat])),
                "mean_body_roll_deg": float(np.mean([t["body_roll_mean_deg"] for t in flat])),
            }
        elif analyzer == "gait_metrics" and flat and all(t.get("available") for t in flat):
            result["flat_gait"] = {
                "mean_foot_center_world_z_span_p95_p5_cm": np.mean([
                    t["foot_center_world_z_p95_minus_p5_cm"] for t in flat], axis=0).tolist(),
                "mean_loaded_30n_foot_center_xy_speed_m_s": np.mean([
                    t["force_gates_n"]["30"]["mean_foot_center_xy_speed_m_s"] for t in flat], axis=0).tolist(),
                "scope": "trial-weighted means of saved-pose force-gated proxies",
            }
        result[analyzer + "_source"] = str(path)
        result[analyzer + "_sha256"] = digest(path)
        if archive_name:
            shutil.copyfile(path, OUT / f"posture-20261014-{archive_name}-{suite}-{analyzer}.json")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tags", nargs="+", default=["weak", "contact", "medium", "symmetric1b"])
    p.add_argument("--archive", action="store_true", help="Copy completed matrices/configs, without raw rollouts")
    a = p.parse_args()
    comparison = {"recorded_local": datetime.now().astimezone().isoformat(),
                  "development_seed_start": 2000, "leg_order": ["FL", "FR", "RL", "RR"],
                  "original_frozen_policy_unchanged": True, "candidates": []}
    base = {"name": "baseline", "suites": {}}
    for suite in ("nominal", "deployment"):
        base["suites"][suite] = summarize(
            OUT / f"posture-20261014-baseline-{suite}-dev.json",
            OUT / f"posture-20261014-baseline-{suite}-posture.json")
    comparison["candidates"].append(base)
    for tag in a.tags:
        pipeline_path = LOG / f"posture-20261014-{tag}-pipeline/pipeline.json"
        if not pipeline_path.exists():
            continue
        pipeline = read(pipeline_path)
        directory = pipeline_path.parent
        if a.archive:
            shutil.copyfile(pipeline_path, OUT / f"posture-20261014-{tag}-pipeline.json")
        for candidate in pipeline.get("candidates", []):
            iteration = candidate["iteration"]
            row = {"name": f"{tag}{iteration}", "policy": candidate["policy"],
                   "policy_sha256": digest(Path(candidate["policy"])), "suites": {}}
            for suite in ("nominal", "deployment"):
                matrix_path = directory / f"iter{iteration}-{suite}/matrix.json"
                posture_path = directory / f"iter{iteration}-{suite}-posture.json"
                row["suites"][suite] = summarize(matrix_path, posture_path)
                add_diagnostics(row, suite, matrix_path, f"{tag}{iteration}" if a.archive else None)
                if a.archive:
                    for source, suffix in ((matrix_path, ""), (posture_path, "-posture")):
                        shutil.copyfile(source, OUT / f"posture-20261014-{tag}{iteration}-{suite}{suffix}.json")
            comparison["candidates"].append(row)
    for row in comparison["candidates"]:
        path = LOG / f"posture-20261014-{row['name']}-flat-development/matrix.json"
        if path.exists() and "passed" in read(path):
            matrix = read(path)
            row["all_direction_flat"] = {"passed": matrix["passed"], "total": matrix["total"],
                                         "summary": matrix["summary"], "source": str(path),
                                         "sha256": digest(path)}
            if a.archive:
                shutil.copyfile(path, OUT / f"posture-20261014-{row['name']}-flat-development.json")
    path = OUT / "posture-20261014-development-comparison.json"
    path.write_text(json.dumps(comparison, indent=2) + "\n")
    for row in comparison["candidates"]:
        suite = row["suites"]["deployment"]
        print(row["name"], f"{suite['passed']}/{suite['total']}",
              "flat shank:", np.round(suite["flat_posture"]["mean_shank_angle_deg"][:2], 1).tolist(),
              "asc/desc loaded calf:", round(suite["ascending"]["mean_loaded_calf_interval_fraction"], 3),
              round(suite["descending"]["mean_loaded_calf_interval_fraction"], 3))
    print(path)


if __name__ == "__main__":
    main()
