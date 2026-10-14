#!/usr/bin/env python3
"""Read recorded MuJoCo poses; quantify posture without another policy rollout."""
import argparse
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np


def summarize(directory, warmup=2.0, stride=1):
    directory = Path(directory)
    result = json.loads((directory / "result.json").read_text())
    rows = json.loads((directory / "trace.json").read_text())
    model = mujoco.MjModel.from_xml_path(str(directory / "model.xml"))
    data = mujoco.MjData(model)
    legs = ("FL", "FR", "RL", "RR")
    knee_ids = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, n + "_calf") for n in legs]
    feet_ids = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, n) for n in legs]
    joint_ids = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, n) for n in result["policy_joint_order"]]
    qids = model.jnt_qposadr[joint_ids]
    # Terrain-only vertical rays; robot visual/collision shapes cannot be hits.
    for gid in range(model.ngeom):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gid) or ""
        model.geom_group[gid] = 5 if name == "floor" or name == "start_platform" or name.startswith(("step_", "nosing_", "platform_nosing")) else 0
    groups = np.array([0, 0, 0, 0, 0, 1], dtype=np.uint8)
    angles, clearance, root, forces = [], [], [], []
    calf_by_leg, foot_by_leg = [], []
    for row in rows[::stride]:
        if row["time"] < warmup:
            continue
        data.qpos[:3] = row["position"]
        data.qpos[3:7] = row["quaternion_wxyz"]
        data.qpos[qids] = row["joint_position"]
        mujoco.mj_forward(model, data)
        knee, foot = data.xpos[knee_ids].copy(), data.geom_xpos[feet_ids].copy()
        vector = foot - knee
        angles.append(np.rad2deg(np.arccos(np.clip(-vector[:, 2] / np.linalg.norm(vector, axis=1), -1, 1))))
        leg_clearance = []
        for point in knee:
            start = point + [0, 0, 5.0]
            gid = np.array([-1], dtype=np.int32)
            distance = mujoco.mj_ray(model, data, start, np.array([0., 0., -1.]), groups, 1, -1, gid)
            if distance < 0:
                raise ValueError("Missing terrain ray in recorded trial")
            leg_clearance.append(distance - 5.0)
        clearance.append(leg_clearance)
        root.append(row["position"][2])
        forces.append(bool(row["calf_loaded_contact"]))
        if "calf_peak_normal_force_by_leg_n" in row:
            calf_by_leg.append(row["calf_peak_normal_force_by_leg_n"])
            foot_by_leg.append(row["foot_peak_normal_force_by_leg_n"])
    if not angles:
        return {"source": str(directory), "samples": 0, "scope": "no frames after warmup"}
    angles, clearance = np.asarray(angles), np.asarray(clearance)
    per_leg = None
    if calf_by_leg:
        if len(calf_by_leg) != len(angles):
            raise ValueError("Incomplete per-leg contact telemetry")
        calf_by_leg, foot_by_leg = np.asarray(calf_by_leg), np.asarray(foot_by_leg)
        supported = (calf_by_leg > 1) | (foot_by_leg > 1)
        count = supported.sum(0)
        per_leg = {
            "loaded_calf_interval_fraction_by_leg": (calf_by_leg > 1).mean(0).tolist(),
            "loaded_foot_interval_fraction_by_leg": (foot_by_leg > 1).mean(0).tolist(),
            "max_calf_normal_force_by_leg_n": calf_by_leg.max(0).tolist(),
            "support_samples_by_leg": count.tolist(),
            "supported_mean_shank_angle_deg": [float(angles[supported[:, i], i].mean()) if count[i] else None for i in range(4)],
            "supported_fraction_shank_angle_gt70": [float((angles[supported[:, i], i] > 70).mean()) if count[i] else None for i in range(4)],
            "scope": "post-step sampled angle gated by any >1 N contact during preceding 20 ms; not instantaneous phase/force correlation",
        }
    return {"source": str(directory.resolve()), "policy_sha256": result["policy_sha256"],
            "trace_sha256": hashlib.sha256((directory / "trace.json").read_bytes()).hexdigest(),
            "success": result["success"], "terrain": result["arguments"]["terrain"],
            "command": result["arguments"]["command"], "samples": len(angles),
            "leg_order": list(legs), "warmup_s": warmup, "stride": stride,
            "angle_definition": "world down to knee-to-foot-center vector; 90 deg is horizontal",
            "mean_shank_angle_deg": angles.mean(0).tolist(),
            "p95_shank_angle_deg": np.percentile(angles, 95, axis=0).tolist(),
            "fraction_shank_angle_gt70": (angles > 70).mean(0).tolist(),
            "mean_knee_clearance_cm": (100 * clearance.mean(0)).tolist(),
            "p5_knee_clearance_cm": (100 * np.percentile(clearance, 5, axis=0)).tolist(),
            "mean_root_world_z_m": float(np.mean(root)),
            "loaded_calf_policy_interval_fraction": float(np.mean(forces)),
            "clearance_scope": "knee joint origin above highest terrain vertically below; not collision-surface clearance or side-riser distance",
            "contact_scope": result["contact_scope"],
            "per_leg_contacts": per_leg,
            "scope": "post-warmup saved policy-boundary poses, all terrain phases; sparse stride if requested"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.stride < 1:
        parser.error("stride must be positive")
    if args.matrix:
        matrix = json.loads((args.directory / "matrix.json").read_text())
        metrics = [summarize(Path(t["result_file"]).parent, stride=args.stride) for t in matrix["trials"]]
    else:
        metrics = [summarize(args.directory, stride=args.stride)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"trials": metrics}, indent=2) + "\n")
    print(json.dumps({"trials": len(metrics), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
