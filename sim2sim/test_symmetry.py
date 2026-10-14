"""Check reflection signs against actual Go2 kinematics and angular vectors."""
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace as NS

import mujoco
import numpy as np

from run import ASSETS, DEFAULT_POLICY, make_model, observation
from symmetry_metrics import mirror_frame, mirror_joints


class MirrorGeometryTests(unittest.TestCase):
    def test_reflected_joints_reproduce_reflected_real_go2_foot_positions(self):
        args = NS(assets=ASSETS, dt=.005, stock_joint_physics=False,
                  contact_profile="menagerie", terrain="flat", steps=6, depth=.27,
                  width=1.2, height=.16, nosing=0, friction=1., mass_scale=1., com_offset=[0, 0, 0])
        config = json.loads((DEFAULT_POLICY.parent / "config.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            model, _, _, _ = make_model(args, Path(directory))
            data = mujoco.MjData(model)
            joints = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name) for name in config["joint_names"]]
            qids = model.jnt_qposadr[joints]
            feet = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, leg) for leg in ("FL", "FR", "RL", "RR")]
            rng = np.random.default_rng(20261014)
            for _ in range(12):
                q = np.asarray(config["default_joint_positions"]) + rng.uniform(-.25, .25, 12)
                data.qpos[:3] = [0, 0, .4]
                data.qpos[3:7] = [1, 0, 0, 0]
                data.qpos[qids] = q
                mujoco.mj_forward(model, data)
                original = data.geom_xpos[feet].copy()
                data.qpos[qids] = mirror_joints(q)
                mujoco.mj_forward(model, data)
                np.testing.assert_allclose(data.geom_xpos[feet],
                    original[[1, 0, 3, 2]] * [1, -1, 1], atol=1e-7)

    def test_polar_and_axial_vector_reflection_matches_observation_contract(self):
        rng = np.random.default_rng(20261015)
        default = np.asarray(json.loads((DEFAULT_POLICY.parent / "config.json").read_text())["default_joint_positions"])
        command, omega, gravity = rng.normal(size=(3, 3))
        q, dq, action = rng.normal(size=(3, 12))
        frame = observation(command, omega, gravity, q, dq, default, action)
        expected = observation(command*[1, -1, -1], omega*[-1, 1, -1], gravity*[1, -1, 1],
                               mirror_joints(q), mirror_joints(dq), default, mirror_joints(action))
        np.testing.assert_allclose(mirror_frame(frame), expected, atol=1e-7)
        # Reflection of angular velocity is axial, unlike linear velocity or gravity.
        a, b = rng.normal(size=(2, 3))
        np.testing.assert_allclose(np.cross(a*[1, -1, 1], b*[1, -1, 1]),
                                   np.cross(a, b)*[-1, 1, -1], atol=1e-12)
        np.testing.assert_allclose(mirror_frame(mirror_frame(np.tile(frame, (6, 1)))),
                                   np.tile(frame, (6, 1)), atol=1e-7)


if __name__ == "__main__":
    unittest.main()
