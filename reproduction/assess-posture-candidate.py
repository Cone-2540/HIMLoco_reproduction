#!/usr/bin/env python3
"""Assess predeclared research targets from a completed development pipeline.

No policy is promoted or overwritten. Missing evidence is reported as unknown,
and visual review and independent-seed verification remain separate tasks.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pipeline", type=Path)
    p.add_argument("--iteration", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    pipeline = read(a.pipeline)
    gates = read(ROOT / "reproduction/posture-20261014-symmetry-gates.json")
    candidates = pipeline["candidates"]
    matched = [(i, c) for i, c in enumerate(candidates) if c["iteration"] == a.iteration]
    if len(matched) != 1:
        raise SystemExit("Need exactly one fully evaluated candidate in pipeline")
    index, candidate = matched[0]
    expected_sha = hashlib.sha256(Path(candidate["policy"]).read_bytes()).hexdigest()
    directory = a.pipeline.parent
    checks = []

    def check(name, measured, target, direction, scope):
        if measured is None:
            status = "unknown_missing_evidence"
        elif direction == "max":
            status = "met" if np.all(np.asarray(measured) <= target) else "not_met"
        else:
            status = "met" if np.all(np.asarray(measured) >= target) else "not_met"
        checks.append({"name": name, "measured": measured, "target": target,
                       "direction": direction, "status": status, "scope": scope})

    matrices = {suite: read(candidate["matrices"][suite]["source"]) for suite in ("nominal", "deployment")}
    nominal_posture = read(directory / f"iter{a.iteration}-nominal-posture.json")["trials"]
    for suite, matrix in matrices.items():
        if (matrix["seed_start"] != 2000 or matrix["seeds_per_case"] != 4
                or any(t["policy_sha256"] != expected_sha for t in matrix["trials"])):
            raise ValueError(f"{suite} matrix policy or development protocol identity mismatch")
    if any(t["policy_sha256"] != expected_sha for t in nominal_posture):
        raise ValueError("Posture evidence policy identity mismatch")
    flat = [r for r in nominal_posture if r.get("terrain") == "flat"]
    desired = gates["desired_flat_posture"]
    for key, target_name, direction in (
        ("mean_shank_angle_deg", "front_leg_mean_shank_angle_deg_each_max", "max"),
        ("p5_knee_clearance_cm", "front_knee_origin_p5_height_cm_each_min", "min"),
    ):
        measured = np.mean([r[key] for r in flat], axis=0)[:2].tolist()
        check(target_name, measured, desired[target_name], direction,
              "nominal .3/.5 m/s, equal trial means; knee origin, not collision-surface clearance")
    loaded = [r["per_leg_contacts"] for r in flat if r.get("per_leg_contacts")]
    measured = None
    if len(loaded) == len(flat):
        measured = np.mean([r["supported_fraction_shank_angle_gt70"] for r in loaded], axis=0)[:2].tolist()
    key = "front_leg_supported_fraction_angle_gt70_each_max"
    check(key, measured, desired[key], "max", "sparse saved-pose supported-angle fractions, each front leg")

    symmetry_path = directory / f"iter{a.iteration}-nominal-symmetry_metrics.json"
    flat_symmetry = []
    if symmetry_path.exists():
        symmetry = read(symmetry_path)["trials"]
        if any(t["policy_sha256"] != expected_sha for t in symmetry):
            raise ValueError("Symmetry evidence policy identity mismatch")
        flat_symmetry = [r for r in symmetry if r["terrain"] == "flat"]
    for part in ("thigh", "calf"):
        measured = float(np.mean([abs(r["mirror_bias"][part]["mean_signed_mirror_difference_rad"][0])
                                  for r in flat_symmetry])) if flat_symmetry else None
        key = f"mean_front_{part}_mirror_difference_abs_rad_max"
        check(key, measured, desired[key], "max", "mean of absolute per-trial front L/R mean biases; preserves gait phase")
    key = "mean_front_mirrored_foot_longitudinal_difference_abs_m_max"
    measured = float(np.mean([abs(r["mean_mirrored_foot_difference_m"][0][0]) for r in flat_symmetry])) if flat_symmetry else None
    check(key, measured, desired[key], "max", "mean absolute per-trial body-frame front foot longitudinal bias")

    performance = gates["performance"]
    for suite in ("nominal", "deployment"):
        key = "mujoco_" + suite + "_first_episode_completion_fraction_" + ("min" if suite == "nominal" else "target_min")
        matrix = matrices[suite]
        check(key, matrix["passed"] / matrix["total"], performance[key], "min",
              f"paired development first episodes, {matrix['passed']}/{matrix['total']}; smoothness assessed separately")
        baseline = read(ROOT / f"reproduction/posture-20261014-baseline-{suite}-dev.json")
        current_flat = {s["case"]: s for s in matrix["summary"] if s["case"].startswith("flat")}
        changes = [current_flat[s["case"]]["mean_xy_velocity_mae_m_s"] - s["mean_xy_velocity_mae_m_s"]
                   for s in baseline["summary"] if s["case"].startswith("flat")]
        check(suite+"_forward_tracking_regression", max(changes),
              performance["mean_forward_xy_velocity_mae_regression_m_s_max"], "max",
              "largest paired forward-command case mean XY tracking increase vs frozen original")
        standard = [s for s in matrix["summary"] if s["case"].startswith(("asc-16x27", "desc-16x27"))]
        check(suite+"_standard_stair_calf_contact", [s["mean_calf_loaded_contact_fraction"] for s in standard],
              performance["standard_stair_loaded_calf_interval_fraction_target_max"], "max",
              "each standard .3/.5 m/s ascending/descending case; any calf >1N in 20 ms policy interval")
    for label, evidence_key in (("nominal", "isaac_nominal_result"), ("deployment", "isaac_domain_result")):
        measured, counts = None, None
        if pipeline.get(evidence_key):
            path = Path(pipeline[evidence_key]).parent / "candidates" / f"{index}_model_{a.iteration}" / "result.json"
            report = read(path)
            counts = (sum(t["completions"] for t in report["policy"]["trials"]),
                      sum(t["num_envs"] for t in report["policy"]["trials"]))
            measured = counts[0] / counts[1]
        key = f"isaac_{label}_first_episode_completion_fraction_target_min"
        check(key, measured, performance[key], "min", "paired first-episode environment completions " + str(counts))
    frozen = ROOT / "artifacts/go2-night3-selected/model.pt"
    check("frozen_original_identity", int(hashlib.sha256(frozen.read_bytes()).hexdigest() ==
        "4e0c046734eda739fbea83ee7177ac7f3a6dbd35ef5fd0dae0a83e48f92cd83b"), 1, "min", "read-only checkpoint SHA256")
    result = {"candidate_iteration": a.iteration, "policy": candidate["policy"],
              "policy_sha256": expected_sha,
              "pipeline": str(a.pipeline.resolve()), "checks": checks,
              "all_quantitative_development_targets_met": all(c["status"] == "met" for c in checks),
              "visual_review_verified_by_this_script": False,
              "independent_validation_verified_by_this_script": False,
              "automatic_promotion": False,
              "scope": "predeclared research targets, development evidence only; unknown is not a pass; no deployment certification"}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"met": sum(c["status"] == "met" for c in checks),
                      "not_met": [c["name"] for c in checks if c["status"] == "not_met"],
                      "unknown": [c["name"] for c in checks if c["status"].startswith("unknown")],
                      "output": str(a.output)}, indent=2))


if __name__ == "__main__":
    main()
