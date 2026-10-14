#!/usr/bin/env python3
"""Render saved poses with a close side view; no controller or new physics run."""
import argparse
import hashlib
import json
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("trial", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--start", type=float, default=2.0)
    p.add_argument("--end", type=float, default=10.0)
    p.add_argument("--azimuth", type=float, default=90.0)
    p.add_argument("--distance", type=float, default=1.4)
    a = p.parse_args()
    if a.output.exists():
        p.error("Output already exists")
    result = json.loads((a.trial / "result.json").read_text())
    rows = json.loads((a.trial / "trace.json").read_text())
    m = mujoco.MjModel.from_xml_path(str(a.trial / "model.xml"))
    d = mujoco.MjData(m)
    qids = [m.jnt_qposadr[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)]
            for n in result["policy_joint_order"]]
    feet = [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, n) for n in ("FL", "FR", "RL", "RR")]
    camera = mujoco.MjvCamera()
    camera.azimuth, camera.elevation, camera.distance = a.azimuth, -10.0, a.distance
    frames, maximum_error = 0, 0.
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with mujoco.Renderer(m, height=540, width=960) as renderer:
        with imageio.get_writer(a.output, fps=50, codec="libx264", quality=7, macro_block_size=2) as writer:
            for row in rows:
                if not a.start <= row["time"] <= a.end:
                    continue
                d.qpos[:3] = row["position"]
                d.qpos[3:7] = row["quaternion_wxyz"]
                d.qpos[qids] = row["joint_position"]
                mujoco.mj_forward(m, d)
                error = np.max(np.abs(d.geom_xpos[feet] - np.asarray(row["foot_position"])))
                maximum_error = max(maximum_error, float(error))
                if error > 1e-5:
                    raise ValueError("Saved pose does not reproduce foot positions")
                camera.lookat[:] = d.qpos[:3] + [0, 0, -.07]
                renderer.update_scene(d, camera=camera)
                frame = renderer.render()
                writer.append_data(frame)
                if frames == 0:
                    imageio.imwrite(a.output.with_suffix(".jpg"), frame)
                frames += 1
    record = {"source": str(a.trial.resolve()), "video": str(a.output.resolve()), "frames": frames,
              "fps": 50, "interval_s": [a.start, a.end], "policy_sha256": result["policy_sha256"],
              "trace_sha256": hashlib.sha256((a.trial / "trace.json").read_bytes()).hexdigest(),
              "reconstructed_foot_max_error_m": maximum_error,
              "scope": "recorded policy-boundary kinematic pose playback; no policy inference or new physics",
              "camera": {"azimuth": a.azimuth, "elevation": -10, "distance": a.distance}}
    a.output.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
