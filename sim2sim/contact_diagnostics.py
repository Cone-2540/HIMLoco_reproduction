#!/usr/bin/env python3
"""Record loaded calf collision locations without changing the rollout runner.

This opt-in diagnostic wraps the existing mj_contactForce read. The returned
forces, control, RNG and physics calls stay identical. A separate sidecar records
the wrapper source; these runs are diagnostic and do not replace matrix results.
All usual sim2sim/run.py arguments apply.
"""
import hashlib
import json

import mujoco
import numpy as np

from run import parse, run


def main():
    args = parse()
    original = mujoco.mj_contactForce
    contacts = []

    def record(model, data, contact_index, force):
        original(model, data, contact_index, force)
        normal = abs(float(force[0]))
        if normal <= 1:
            return
        contact = data.contact[contact_index]
        for geom, other in ((contact.geom1, contact.geom2), (contact.geom2, contact.geom1)):
            body = model.geom_bodyid[geom]
            name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body) or ""
            geom_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom) or ""
            if not name.endswith("_calf") or geom_name in ("FL", "FR", "RL", "RR"):
                continue
            point = np.asarray(contact.pos).copy()
            knee = data.xpos[body].copy()
            local = data.xmat[body].reshape(3, 3).T @ (point - knee)
            normal_w = np.asarray(contact.frame).reshape(3, 3)[0].copy()
            leg = name.removesuffix("_calf")
            foot_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, leg)
            foot = data.geom_xpos[foot_id].copy()
            shank = foot - knee
            angle = float(np.rad2deg(np.arccos(np.clip(-shank[2] / np.linalg.norm(shank), -1, 1))))
            contacts.append({"call_time_s": float(data.time),
                             "solver_state_time_s": float(data.time - model.opt.timestep),
                             "leg": leg, "normal_force_n": normal,
                             "world_point_m": point.tolist(), "calf_local_point_m": local.tolist(),
                             "knee_origin_world_m": knee.tolist(),
                             "foot_center_world_m": foot.tolist(), "shank_angle_deg": angle,
                             "normal_world": normal_w.tolist(), "contact_distance_m": float(contact.dist),
                             "robot_geom_id": int(geom), "robot_geom_name": geom_name,
                             "terrain_geom_name": mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, other)})

    mujoco.mj_contactForce = record
    try:
        result = run(args)
    finally:
        mujoco.mj_contactForce = original
    summary = {}
    for leg in ("FL", "FR", "RL", "RR"):
        rows = [r for r in contacts if r["leg"] == leg]
        summary[leg] = {"loaded_contact_samples": len(rows)}
        if rows:
            local_z = np.array([r["calf_local_point_m"][2] for r in rows])
            vertical = np.array([abs(r["normal_world"][2]) for r in rows])
            angle = np.array([r["shank_angle_deg"] for r in rows])
            summary[leg].update(local_z_p5_p50_p95_m=np.percentile(local_z, [5, 50, 95]).tolist(),
                                shank_angle_p5_p50_p95_deg=np.percentile(angle, [5, 50, 95]).tolist(),
                                fraction_loaded_contacts_angle_le65=float((angle <= 65).mean()),
                                fraction_normal_near_vertical=float((vertical > .7).mean()),
                                fraction_normal_near_horizontal=float((vertical < .3).mean()),
                                peak_normal_force_n=max(r["normal_force_n"] for r in rows),
                                terrain_geoms=sorted({r["terrain_geom_name"] for r in rows}))
    path = args.output / "calf-contact-locations.json"
    path.write_text(json.dumps({"policy_sha256": result["policy_sha256"],
                               "success": result["success"], "reason": result["reason"],
                               "diagnostic_source_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
                               "summary": summary, "contacts": contacts,
                               "scope": ">1N calf geometric contacts in original 5ms physics samples; local point Z is along the calf link, not world height; force is not impulse.",
                               "timestamp_scope": "mj_step integrates qpos after deriving contacts; positions belong to solver state at call time minus one physics dt."}, indent=2) + "\n")
    print(path)


if __name__ == "__main__":
    main()
