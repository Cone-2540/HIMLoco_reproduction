#!/usr/bin/env python3
"""Measure persistent mirror bias and policy equivariance on recorded traces."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from run import observation, push_history


def mirror_frame(frame):
    """Reflect sagittal plane in the exact 45-D HIM observation convention."""
    reflected = frame.copy()
    reflected[..., [1, 2, 3, 5, 7]] *= -1  # cmd y/yaw; omega x/z; gravity y
    for start in (9, 21, 33):
        reflected[..., start:start + 12] = mirror_joints(frame[..., start:start + 12])
    return reflected


def mirror_joints(values):
    result = values[..., [1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10]].copy()
    result[..., :4] *= -1
    return result


def summarize(directory):
    result = json.loads((directory / "result.json").read_text())
    rows = json.loads((directory / "trace.json").read_text())
    config = json.loads(Path(result["arguments"]["config"]).read_text())
    expected = [leg + "_" + part + "_joint" for part in ("hip", "thigh", "calf")
                for leg in ("FL", "FR", "RL", "RR")]
    if result["policy_joint_order"] != expected:
        raise ValueError("Only explicit grouped Go2 joint order is supported")
    default = np.asarray(config["default_joint_positions"])
    if not np.allclose(default, mirror_joints(default), atol=1e-6):
        raise ValueError("Default pose is not mirror symmetric")
    q = np.asarray([r["joint_position"] for r in rows if r["time"] >= 2])
    if len(q) == 0:
        return {"source": str(directory.resolve()), "policy_sha256": result["policy_sha256"],
                "success": result["success"], "terrain": result["arguments"]["terrain"],
                "command": result["arguments"]["command"], "samples_after_2s": 0,
                "scope": "No frames after warmup; symmetry unassessed, completion retained"}
    hip = np.column_stack((q[:, 0] + q[:, 1], q[:, 2] + q[:, 3]))
    thigh = q[:, [4, 6]] - q[:, [5, 7]]
    calf = q[:, [8, 10]] - q[:, [9, 11]]
    saved = [r for r in rows if r["time"] >= 2]
    quaternion = np.asarray([r["quaternion_wxyz"] for r in saved])
    w, x, y, z = quaternion.T
    roll = np.arctan2(2*(w*x+y*z), 1-2*(x*x+y*y))
    # Inverse quaternion rotation of post-step world foot offsets into body.
    relative = np.asarray([r["foot_position"] for r in saved]) - np.asarray([r["position"] for r in saved])[:, None]
    xyz = quaternion[:, None, 1:]
    feet = relative - 2*quaternion[:, None, :1]*np.cross(xyz, relative)
    feet += 2*np.cross(xyz, np.cross(xyz, relative))
    foot_bias = feet[:, [0, 2]] - feet[:, [1, 3]] * np.array([1., -1., 1.])
    torque = np.asarray([r["torque"] for r in saved])
    stats = {}
    for name, values in (("hip", hip), ("thigh", thigh), ("calf", calf)):
        stats[name] = {"mean_signed_mirror_difference_rad": values.mean(0).tolist(),
                       "instantaneous_rms_difference_rad": np.sqrt(np.mean(values**2, 0)).tolist(),
                       "pair_order": ["front", "rear"]}
    # Old telemetry mixes pre/post-step quantities, so infer mirror behavior
    # from a neutral probe only unless exact policy_input frames were recorded.
    policy = torch.jit.load(result["arguments"]["policy"], map_location="cpu").eval()
    neutral = observation(result["arguments"]["command"], np.zeros(3), np.array([0., 0., -1.]),
                          default, np.zeros(12), default, np.zeros(12))
    history = np.tile(neutral, 6).astype(np.float32)
    mirrored = mirror_frame(history.reshape(6, 45)).reshape(270)
    with torch.inference_mode():
        action = policy(torch.from_numpy(history)[None]).numpy()[0]
        mirrored_action = mirror_joints(policy(torch.from_numpy(mirrored)[None]).numpy()[0])
    recorded_input_probe = None
    if all("policy_input" in row for row in rows):
        history = np.zeros(270, dtype=np.float32)
        maximum_error, residuals = 0., []
        with torch.inference_mode():
            for i, row in enumerate(rows):
                history = push_history(history, np.asarray(row["policy_input"], dtype=np.float32))
                if i % 10 or row["time"] < 2:
                    continue
                original = np.clip(policy(torch.from_numpy(history)[None]).numpy()[0], -100, 100)
                maximum_error = max(maximum_error, float(np.max(np.abs(original-np.asarray(row["action"])))))
                flipped = mirror_frame(history.reshape(6, 45)).reshape(270)
                mapped = mirror_joints(np.clip(policy(torch.from_numpy(flipped)[None]).numpy()[0], -100, 100))
                residuals.append(original - mapped)
        if maximum_error > 1e-5:
            raise ValueError("Reconstructed exact actor history disagrees with saved action")
        errors = np.asarray(residuals)
        recorded_input_probe = {"samples": len(errors), "saved_action_max_abs_reconstruction_error": maximum_error,
                                "mirror_action_rms": float(np.sqrt(np.mean(errors**2))),
                                "per_joint_mirror_action_rms": np.sqrt(np.mean(errors**2, 0)).tolist(),
                                "scope": "exact recorded noisy frame history; mirrored policy inputs, no second physics rollout"}
    return {"source": str(directory.resolve()), "policy_sha256": result["policy_sha256"],
            "trace_sha256": hashlib.sha256((directory / "trace.json").read_bytes()).hexdigest(),
            "success": result["success"], "terrain": result["arguments"]["terrain"],
            "command": result["arguments"]["command"], "samples_after_2s": len(q),
            "joint_names": expected, "mean_joint_position_rad": q.mean(0).tolist(),
            "joint_std_rad": q.std(0).tolist(), "mirror_bias": stats,
            "body_roll_mean_deg": float(np.rad2deg(roll.mean())),
            "body_roll_rms_deg": float(np.rad2deg(np.sqrt(np.mean(roll**2)))),
            "mean_foot_body_position_m": feet.mean(0).tolist(),
            "mean_mirrored_foot_difference_m": foot_bias.mean(0).tolist(),
            "mean_abs_joint_torque_nm": np.abs(torque).mean(0).tolist(),
            "neutral_input_mirror_action_rms": float(np.sqrt(np.mean((action - mirrored_action)**2))),
            "neutral_action": action.tolist(), "neutral_action_mirror_residual": (action-mirrored_action).tolist(),
            "recorded_input_mirror_probe": recorded_input_probe,
            "scope": "full post-warmup trial means; mean bias is phase averaged but stair sequencing can differ; neutral probe is off-trajectory and diagnostic only"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    p.add_argument("--matrix", action="store_true")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    torch.set_num_threads(1)
    if a.matrix:
        matrix = json.loads((a.directory / "matrix.json").read_text())
        directories = [Path(t["result_file"]).parent for t in matrix["trials"]]
    else:
        directories = [a.directory]
    trials = [summarize(d) for d in directories]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps({"trials": trials}, indent=2) + "\n")
    print(a.output)


if __name__ == "__main__":
    main()
