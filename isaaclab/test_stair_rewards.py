"""CPU regression tests for terrain-relative and history-sensitive HIM rewards."""

import math
import unittest
from types import SimpleNamespace as NS
from unittest import mock

import torch

from stair_rewards import (
    _inverse_rotate,
    action_smoothness_l2,
    configure_stair_rewards,
    feet_slide_l2,
    foot_clearance_body_l2,
    joint_power_l1,
    policy_joint_acceleration_l2,
    terrain_relative_base_height_l2,
    validate_reward_frames,
)


def tensor(value):
    return NS(torch=torch.as_tensor(value, dtype=torch.float32))


def make_env():
    robot = NS(data=NS(
        root_pos_w=tensor([[0, 0, 0.3], [5, 3, 1.5]]),
        root_quat_w=tensor([[0, 0, 0, 1], [0, 0, 0, 1]]),
        root_lin_vel_w=tensor([[0, 0, 0], [0, 0, 0]]),
        body_pos_w=tensor([[[0, 0, 0.1], [0, 0, 0.0]], [[5, 3, 1.3], [5, 3, 1.2]]]),
        body_lin_vel_w=tensor([[[1, 0, 0], [1, 0, 0]], [[1, 0, 0], [1, 0, 0]]]),
        joint_vel=tensor([[1, 2], [-3, 4]])),
        actuators=NS(applied_effort=tensor([[2, -3], [4, -5]])))
    return NS(scene={"robot": robot}, common_step_counter=1,
              episode_length_buf=torch.ones(2, dtype=torch.long), step_dt=0.02,
              action_manager=NS(action=torch.zeros(2, 2), prev_action=torch.zeros(2, 2)))


ASSET = NS(name="robot", joint_ids=slice(None), body_ids=slice(None))


class StairRewardTest(unittest.TestCase):
    def test_pinned_math_identity_yaw_and_pitch_use_xyzw(self):
        from isaaclab.utils.math import quat_apply_inverse, quat_from_euler_xyz
        angles = torch.tensor([[0., 0., 0.], [0., 0., math.pi / 2], [0., math.pi / 4, 0.]])
        quaternion = quat_from_euler_xyz(*angles.unbind(dim=1))
        torch.testing.assert_close(quaternion[0], torch.tensor([0., 0., 0., 1.]))
        vectors = torch.tensor([[[1., 0., 0.], [0., 0., 1.]]]).repeat(3, 1, 1)
        expected = quat_apply_inverse(quaternion[:, None].expand(-1, 2, -1).reshape(-1, 4),
                                     vectors.reshape(-1, 3)).reshape(3, 2, 3)
        torch.testing.assert_close(_inverse_rotate(quaternion, vectors), expected)
        torch.testing.assert_close(expected[1, 0], torch.tensor([0., -1., 0.]), atol=1e-6, rtol=0)
        env = make_env()
        env.scene["robot"].data.root_quat_w.torch = quaternion
        result = validate_reward_frames(env)
        self.assertEqual(result["quaternion_order"], "xyzw")

    def test_power_uses_actual_effort_and_absolute_product(self):
        env = make_env()
        torch.testing.assert_close(joint_power_l1(env, ASSET), torch.tensor([8., 32.]))

    def test_body_relative_foot_clearance_is_invariant_to_elevated_landing(self):
        env = make_env()
        result = foot_clearance_body_l2(env, ASSET)
        # One foot at -0.20 has zero error, the other at -0.30 contributes .01.
        torch.testing.assert_close(result, torch.tensor([0.01, 0.01]), atol=1e-6, rtol=1e-5)
        env.scene["robot"].data.root_lin_vel_w.torch[:, 0] = 1.0
        torch.testing.assert_close(foot_clearance_body_l2(env, ASSET), torch.zeros(2))

    def test_foot_clearance_uses_full_body_rotation_on_pitch(self):
        env = make_env()
        half = math.pi / 8
        env.scene["robot"].data.root_quat_w.torch[:] = torch.tensor([0, math.sin(half), 0, math.cos(half)])
        # These world vectors correspond to body [0,0,-.2] at pitch pi/4.
        delta = torch.tensor([-math.sqrt(.02), 0, -math.sqrt(.02)])
        root = env.scene["robot"].data.root_pos_w.torch
        env.scene["robot"].data.body_pos_w.torch[:] = root[:, None, :] + delta
        torch.testing.assert_close(foot_clearance_body_l2(env, ASSET), torch.zeros(2), atol=1e-10, rtol=0)

    def test_height_uses_close_terrain_not_world_z_or_distant_high_tread(self):
        env = make_env()
        env.scene["scanner"] = NS(data=NS(ray_hits_w=tensor([
            [[-.1, 0, 0], [.1, 0, 0], [.6, 0, 0.8]],
            [[4.9, 3, 1.2], [5.1, 3, 1.2], [5.6, 3, 2.0]],
        ])))
        value = terrain_relative_base_height_l2(env, ASSET, NS(name="scanner"))
        torch.testing.assert_close(value, torch.zeros(2), atol=1e-12, rtol=0)
        env.scene["robot"].data.root_pos_w.torch[:, 2] += 0.1
        value = terrain_relative_base_height_l2(env, ASSET, NS(name="scanner"))
        torch.testing.assert_close(value, torch.full((2,), .01), atol=1e-7, rtol=1e-5)

    def test_height_rotates_footprint_and_excludes_invalid_rays(self):
        env = make_env()
        env.scene["robot"].data.root_pos_w.torch[:] = torch.tensor([0, 0, .3])
        env.scene["robot"].data.root_quat_w.torch[:] = torch.tensor([0, 0, math.sqrt(.5), math.sqrt(.5)])
        env.scene["scanner"] = NS(data=NS(ray_hits_w=tensor([
            [[.19, 0, 0], [0, .19, .9], [float("inf"), 0, float("inf")]],
            [[float("nan"), 0, 0], [float("inf"), 0, 0], [0, 0, float("inf")]],
        ])))
        value = terrain_relative_base_height_l2(env, ASSET, NS(name="scanner"))
        # After 90deg yaw, world x .19 is inside body y footprint; y .19 is outside x.
        self.assertTrue(torch.isfinite(value).all())
        torch.testing.assert_close(value, torch.zeros(2))

    def test_action_second_difference_is_reset_safe_and_idempotent_per_step(self):
        env = make_env()
        env.action_manager.action[:] = 1.0
        torch.testing.assert_close(action_smoothness_l2(env), torch.full((2,), 2.))
        env.common_step_counter += 1
        env.episode_length_buf += 1
        env.action_manager.prev_action[:] = 1.0
        env.action_manager.action[:] = 2.0
        torch.testing.assert_close(action_smoothness_l2(env), torch.zeros(2))
        torch.testing.assert_close(action_smoothness_l2(env), torch.zeros(2))
        env.common_step_counter += 1
        env.episode_length_buf = torch.tensor([1, 3])  # only env0 resets
        env.action_manager.prev_action[:] = torch.tensor([[0., 0.], [2., 2.]])
        env.action_manager.action[:] = torch.tensor([[1., 1.], [3., 3.]])
        torch.testing.assert_close(action_smoothness_l2(env), torch.tensor([2., 0.]))

    def test_joint_acceleration_uses_policy_interval_and_reset_clears_velocity(self):
        env = make_env()
        first = policy_joint_acceleration_l2(env, ASSET)
        torch.testing.assert_close(first, torch.tensor([5., 25.]) / .02**2)
        env.common_step_counter += 1
        env.episode_length_buf += 1
        env.scene["robot"].data.joint_vel.torch += 1.0
        result = policy_joint_acceleration_l2(env, ASSET)
        torch.testing.assert_close(result, torch.full((2,), 2. / .02**2))
        env.common_step_counter += 1
        env.episode_length_buf[:] = torch.tensor([1, 3])
        env.scene["robot"].data.joint_vel.torch[:] = torch.tensor([[1, 0], [-2, 5]])
        result = policy_joint_acceleration_l2(env, ASSET)
        torch.testing.assert_close(result, torch.tensor([1. / .02**2, 0.]))

    def test_slip_requires_contact_and_uses_world_horizontal_motion(self):
        env = make_env()
        force = torch.zeros(2, 3, 2, 3)
        force[0, 1, 0, 2] = 20.0
        env.scene["contact"] = NS(data=NS(net_normal_forces_w_history=NS(torch=force)))
        value = feet_slide_l2(env, NS(name="contact", body_ids=slice(None)), ASSET)
        torch.testing.assert_close(value, torch.tensor([1., 0.]))

    def test_invalid_reward_profile_fails_before_importing_simulator(self):
        with self.assertRaisesRegex(ValueError, "reward profile"):
            configure_stair_rewards(NS(), "nonexistent")

    def test_configuration_restores_original_objective_and_marks_tuned_changes(self):
        managers = NS(RewardTermCfg=lambda **kwargs: NS(**kwargs),
                      SceneEntityCfg=lambda name, **kwargs: NS(name=name, **kwargs))
        def config():
            return NS(scene=NS(base_height_scanner=object()), rewards=NS(
                dof_torques_l2=NS(weight=-.0002), feet_air_time=NS(weight=.01)))
        with mock.patch.dict("sys.modules", {"isaaclab.managers": managers}):
            cfg = config()
            result = configure_stair_rewards(cfg)
            self.assertIsNone(cfg.rewards.dof_torques_l2)
            self.assertIsNone(cfg.rewards.feet_air_time)
            self.assertEqual(result["base_height_sensor"], "base_height_scanner")
            self.assertEqual(result["weights"]["lin_vel_z_l2"], -2.0)
            self.assertEqual(result["weights"]["base_height"], -1.0)
            self.assertEqual(result["weights"]["action_smoothness"], -.01)
            self.assertEqual(result["tuned_changes"], [])
            tuned = configure_stair_rewards(config(), "tuned")
            self.assertEqual(tuned["weights"]["lin_vel_z_l2"], -.5)
            self.assertIn("feet_slide", tuned["weights"])


if __name__ == "__main__":
    unittest.main()
