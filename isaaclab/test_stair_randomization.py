"""CPU configuration checks against the pinned Lab 3 public manager APIs."""

import copy
import unittest
from types import SimpleNamespace as NS

from isaaclab.actuators import DCMotorCfg

from stair_randomization import configure_conservative_calf_limits, configure_stair_randomization


def config():
    robot = NS(actuators={"base_legs": DCMotorCfg(
        joint_names_expr=[".*_hip_joint", ".*_thigh_joint", ".*_calf_joint"],
        actuator_effort_limit={".*_hip_joint": 23.7, ".*_thigh_joint": 23.7, ".*_calf_joint": 45.43},
        saturation_effort={".*_hip_joint": 23.7, ".*_thigh_joint": 23.7, ".*_calf_joint": 45.43},
        actuator_velocity_limit={".*_hip_joint": 30.1, ".*_thigh_joint": 30.1, ".*_calf_joint": 15.70},
        stiffness=25., damping=.5,
    )})
    return NS(scene=NS(robot=robot, terrain=NS(physics_material=NS(
        static_friction=1., dynamic_friction=1., friction_combine_mode="multiply"))),
        sim=NS(use_newton_actuators=False), events=NS(
            physics_material=NS(params={}), base_com=NS(params={}),
            add_base_mass=NS(mode="startup", params={
                "mass_distribution_params": (.8, 1.25), "operation": "scale",
                "distribution": "log_uniform", "recompute_inertia": True})))


class StairRandomizationTest(unittest.TestCase):
    def test_basic_changes_only_feet_material_and_small_com_and_retains_mass(self):
        cfg = config()
        mass, motor = cfg.events.add_base_mass, cfg.scene.robot.actuators["base_legs"]
        report = configure_stair_randomization(cfg, "basic")
        material = cfg.events.physics_material
        self.assertEqual(material.mode, "startup")
        self.assertEqual(material.params["asset_cfg"].body_names, ".*_foot")
        self.assertTrue(material.params["make_consistent"])
        self.assertEqual(material.params["dynamic_friction_range"], (.5, 1.))
        self.assertEqual(cfg.events.base_com.params["com_range"]["x"], (-.01, .01))
        self.assertIs(cfg.events.add_base_mass, mass)
        self.assertIs(cfg.scene.robot.actuators["base_legs"], motor)
        self.assertIsNone(cfg.events.him_actuator_gains)
        self.assertTrue(report["base_mass"]["preserved"])
        self.assertFalse(report["action_delay_randomization"])
        self.assertFalse(report["motor_strength_randomization"])

    def test_robust_uses_supported_reset_gain_randomizer_and_larger_com(self):
        cfg = config()
        report = configure_stair_randomization(cfg, "robust")
        gain = cfg.events.him_actuator_gains
        self.assertEqual(gain.func, "isaaclab.envs.mdp:randomize_actuator_gains")
        self.assertEqual(gain.mode, "reset")
        self.assertEqual(gain.params["operation"], "scale")
        self.assertEqual(gain.params["stiffness_distribution_params"], (.9, 1.1))
        self.assertEqual(cfg.events.base_com.params["com_range"], {
            "x": (-.03, .03), "y": (-.02, .02), "z": (-.01, .01)})
        self.assertEqual(report["pd_gain_scale"], [.9, 1.1])

    def test_none_and_invalid_profile_do_not_mutate_events(self):
        cfg = config()
        before = copy.copy(vars(cfg.events))
        self.assertTrue(configure_stair_randomization(cfg, "none")["events_unchanged"])
        self.assertEqual(vars(cfg.events), before)
        with self.assertRaisesRegex(ValueError, "domain profile"):
            configure_stair_randomization(cfg, "unrecognized")
        self.assertEqual(vars(cfg.events), before)

    def test_native_backend_rejected_before_any_configuration_changes(self):
        cfg = config()
        cfg.sim.use_newton_actuators = True
        material = cfg.events.physics_material
        with self.assertRaisesRegex(ValueError, "native Newton"):
            configure_stair_randomization(cfg, "robust")
        self.assertIs(cfg.events.physics_material, material)

    def test_conservative_knee_limits_copy_motor_and_preserve_other_joints(self):
        cfg = config()
        original = cfg.scene.robot.actuators["base_legs"]
        report = configure_conservative_calf_limits(cfg)
        actual = cfg.scene.robot.actuators["base_legs"]
        self.assertIsNot(actual, original)
        self.assertEqual(original.actuator_effort_limit[".*_calf_joint"], 45.43)
        self.assertEqual(actual.actuator_effort_limit[".*_calf_joint"], 35.55)
        self.assertEqual(actual.saturation_effort[".*_calf_joint"], 35.55)
        self.assertEqual(actual.actuator_velocity_limit[".*_calf_joint"], 20.07)
        self.assertEqual(actual.joint_velocity_limit, actual.actuator_velocity_limit)
        self.assertEqual(actual.joint_effort_limit, actual.actuator_effort_limit)
        self.assertEqual(actual.actuator_effort_limit[".*_hip_joint"], 23.7)
        self.assertEqual(actual.actuator_velocity_limit[".*_thigh_joint"], 30.1)
        self.assertEqual(actual.stiffness, 25.)
        self.assertLess(abs(report["motor_power_product_W"] / report["previous_motor_power_product_W"] - 1), .001)

    def test_conservative_knee_test_rejects_training(self):
        cfg = config()
        motor = cfg.scene.robot.actuators["base_legs"]
        with self.assertRaisesRegex(ValueError, "evaluation/play only"):
            configure_conservative_calf_limits(cfg, "train")
        self.assertIs(cfg.scene.robot.actuators["base_legs"], motor)


if __name__ == "__main__":
    unittest.main()
