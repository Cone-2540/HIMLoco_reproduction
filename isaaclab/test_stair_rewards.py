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
    leg_contact_force_proxy,
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

    def test_faithful_weights_match_full_released_go1_objective(self):
        cfg = NS(scene=NS(base_height_scanner=object()), rewards=NS())
        manifest = configure_stair_rewards(cfg, "faithful")
        self.assertEqual(manifest["weights"], {
            "track_lin_vel_xy_exp": 1., "track_ang_vel_z_exp": .5,
            "lin_vel_z_l2": -2., "ang_vel_xy_l2": -.05,
            "flat_orientation_l2": -.2, "dof_acc_l2": -2.5e-7,
            "joint_power": -2e-5, "base_height": -1.,
            "foot_clearance": -.01, "action_rate_l2": -.01,
            "action_smoothness": -.01,
        })
        self.assertEqual(cfg.rewards.track_lin_vel_xy_exp.params["std"], .5)
        self.assertEqual(cfg.rewards.track_ang_vel_z_exp.params["std"], .5)
        self.assertEqual(cfg.rewards.base_height.params["target_height"], .30)
        self.assertEqual(cfg.rewards.foot_clearance.params["target_height"], -.20)

    def test_new_weight_ablations_change_exactly_one_contact_term(self):
        def config():
            return NS(scene=NS(base_height_scanner=object(), contact_forces=object()),
                      rewards=NS(feet_air_time=NS(weight=.01)))
        baseline = config()
        original = configure_stair_rewards(baseline, "contact")
        for profile, changed_term, old_weight, new_weight in (
            ("contact_vertical", "lin_vel_z_l2", -2., -1.),
            ("contact_clearance", "foot_clearance", -.01, -.02),
        ):
            with self.subTest(profile=profile):
                modified = config()
                manifest = configure_stair_rewards(modified, profile)
                self.assertEqual(set(manifest["weights"]), set(original["weights"]))
                self.assertEqual(manifest["weights"], {
                    **original["weights"], changed_term: new_weight,
                })
                for name in original["weights"]:
                    expected = getattr(baseline.rewards, name).to_dict()
                    actual = getattr(modified.rewards, name).to_dict()
                    if name == changed_term:
                        expected["weight"] = new_weight
                    self.assertEqual(actual, expected, name)
                self.assertIsNone(modified.rewards.feet_air_time)
                self.assertFalse(hasattr(modified.rewards, "feet_slide"))
                self.assertFalse(hasattr(modified.rewards, "leg_contact_force_proxy"))
                self.assertEqual(manifest["contact_penalty"], original["contact_penalty"])
                self.assertIsNone(manifest["force_proxy_penalty"])
                self.assertIsNone(manifest["slide_proxy_penalty"])
                self.assertEqual(manifest["tuned_changes"], [])
                self.assertEqual(len(manifest["adaptation_changes"]), 2)
                ablation = manifest["reward_weight_ablation"]
                self.assertEqual(ablation["baseline_profile"], "contact")
                self.assertEqual(ablation["term"], changed_term)
                self.assertEqual(ablation["original_weight"], old_weight)
                self.assertEqual(ablation["weight"], new_weight)

    def test_new_ablations_require_contact_sensor_before_mutating_rewards(self):
        for profile in ("contact_vertical", "contact_clearance"):
            with self.subTest(profile=profile):
                old = NS(weight=-.0002)
                cfg = NS(scene=NS(base_height_scanner=object()), rewards=NS(old=old))
                with self.assertRaisesRegex(ValueError, "contact_forces sensor"):
                    configure_stair_rewards(cfg, profile)
                self.assertIs(cfg.rewards.old, old)

    def test_new_ablations_keep_finite_signed_velocity_and_height_penalties(self):
        from isaaclab.envs.mdp import lin_vel_z_l2
        env = make_env()
        velocity = torch.tensor([[0., 0., .3], [0., 0., -.4]])
        env.scene["robot"].data.root_lin_vel_b = NS(torch=velocity)
        velocity_before = velocity.clone()
        raw_vertical = lin_vel_z_l2(env)
        raw_clearance = foot_clearance_body_l2(env, ASSET)
        torch.testing.assert_close(raw_vertical, torch.tensor([.09, .16]))
        torch.testing.assert_close(raw_clearance, torch.tensor([.01, .01]))
        results = {}
        for profile in ("contact", "contact_vertical", "contact_clearance"):
            cfg = NS(scene=NS(base_height_scanner=object(), contact_forces=object()), rewards=NS())
            weights = configure_stair_rewards(cfg, profile)["weights"]
            weighted = torch.stack((raw_vertical * weights["lin_vel_z_l2"],
                                    raw_clearance * weights["foot_clearance"]))
            self.assertTrue(torch.isfinite(weighted).all())
            self.assertTrue((weighted <= 0).all())
            results[profile] = weighted
        torch.testing.assert_close(results["contact_vertical"][0], results["contact"][0] * .5)
        torch.testing.assert_close(results["contact_vertical"][1], results["contact"][1])
        torch.testing.assert_close(results["contact_clearance"][0], results["contact"][0])
        torch.testing.assert_close(results["contact_clearance"][1], results["contact"][1] * 2.)
        torch.testing.assert_close(velocity, velocity_before)

    def test_contact_profile_changes_exactly_one_term_from_faithful(self):
        def config():
            return NS(scene=NS(base_height_scanner=object(), contact_forces=object()),
                      rewards=NS(dof_torques_l2=NS(weight=-.0002), feet_air_time=NS(weight=.01)))
        faithful, contact = config(), config()
        original = configure_stair_rewards(faithful, "faithful")
        manifest = configure_stair_rewards(contact, "contact")
        self.assertEqual(manifest["profile"], "contact")
        self.assertEqual(manifest["weights"], {**original["weights"], "leg_contacts": -.1})
        for name in original["weights"]:
            self.assertEqual(getattr(contact.rewards, name).to_dict(),
                             getattr(faithful.rewards, name).to_dict(), name)
        self.assertIsNone(contact.rewards.dof_torques_l2)
        self.assertIsNone(contact.rewards.feet_air_time)
        self.assertFalse(hasattr(contact.rewards, "feet_slide"))
        self.assertEqual(manifest["tuned_changes"], [])
        self.assertEqual(len(manifest["adaptation_changes"]), 1)
        term = contact.rewards.leg_contacts
        self.assertEqual(term.func, "isaaclab.envs.mdp:undesired_contacts")
        self.assertEqual(term.weight, -.1)
        self.assertEqual(term.params["threshold"], 1.)
        self.assertEqual(manifest["contact_penalty"]["baseline_profile"], "faithful")
        self.assertEqual(manifest["contact_penalty"]["expected_selected_go2_bodies"], 8)

    def test_contact_selector_and_installed_mdp_exclude_feet_base_and_hips(self):
        from isaaclab.envs.mdp import undesired_contacts
        from isaaclab.utils.string import resolve_matching_names

        names = ["base", "Head_upper", "Head_lower"] + [f"{leg}_{body}" for leg in ("FL", "FR", "RL", "RR")
                            for body in ("hip", "thigh", "calf", "foot")]
        class ContactSensor:
            body_names = names
            num_sensors = len(names)

            def find_sensors(self, keys, preserve_order=False):
                return resolve_matching_names(keys, self.body_names, preserve_order=preserve_order)

        sensor = ContactSensor()
        history = torch.zeros(5, 3, len(names), 3)
        history[0, 0, names.index("FL_thigh"), 0] = 2.  # Horizontal riser normal.
        history[1, 2, names.index("FR_calf"), 1] = 2.  # Retained contact, current zero.
        history[2, 0, names.index("RL_calf"), 2] = 1.  # Strict threshold.
        for body in ("base", "FL_foot", "FR_hip", "Head_upper"):
            history[3, :, names.index(body), 2] = 100.
        history[4, 0, names.index("RR_thigh"), 2] = 2.
        history[4, 1, names.index("RL_calf"), 0] = 2.  # Count both bodies.
        sensor.data = NS(net_normal_forces_w_history=NS(torch=history))
        class Scene(dict):
            pass
        scene = Scene(contact_forces=sensor)
        scene.sensors = {"contact_forces": sensor}
        cfg = NS(scene=NS(base_height_scanner=object(), contact_forces=object()), rewards=NS())
        configure_stair_rewards(cfg, "contact")
        term = cfg.rewards.leg_contacts
        selection = term.params["sensor_cfg"]
        selection.resolve(scene)
        expected = {f"{leg}_{body}" for leg in ("FL", "FR", "RL", "RR")
                    for body in ("thigh", "calf")}
        self.assertEqual({names[index] for index in selection.body_ids}, expected)
        self.assertEqual(len(selection.body_ids), 8)
        value = undesired_contacts(NS(scene=scene), **term.params)
        torch.testing.assert_close(value, torch.tensor([1, 1, 0, 0, 2]))

    def test_contact_profile_requires_sensor_before_mutating_rewards(self):
        old = NS(weight=-.0002)
        cfg = NS(scene=NS(base_height_scanner=object()), rewards=NS(dof_torques_l2=old))
        with self.assertRaisesRegex(ValueError, "contact_forces sensor"):
            configure_stair_rewards(cfg, "contact")
        self.assertIs(cfg.rewards.dof_torques_l2, old)

    def test_slide_profile_preserves_full_contact_config_and_reuses_only_tuned_slide(self):
        def config():
            return NS(scene=NS(base_height_scanner=object(), contact_forces=object()),
                      rewards=NS(feet_air_time=NS(weight=.01)))
        baseline, modified, tuned_cfg = config(), config(), config()
        original = configure_stair_rewards(baseline, "contact")
        manifest = configure_stair_rewards(modified, "contact_slide")
        configure_stair_rewards(tuned_cfg, "tuned")
        self.assertEqual(manifest["weights"], {**original["weights"], "feet_slide": -.05})
        for name in original["weights"]:
            self.assertEqual(getattr(baseline.rewards, name).to_dict(),
                             getattr(modified.rewards, name).to_dict(), name)
        self.assertEqual(modified.rewards.feet_slide.to_dict(), tuned_cfg.rewards.feet_slide.to_dict())
        self.assertEqual(modified.rewards.lin_vel_z_l2.weight, -2.)
        self.assertEqual(modified.rewards.flat_orientation_l2.weight, -.2)
        self.assertEqual(manifest["contact_penalty"], original["contact_penalty"])
        self.assertIsNone(manifest["force_proxy_penalty"])
        self.assertEqual(manifest["tuned_changes"], [])
        self.assertEqual(len(manifest["adaptation_changes"]), 2)
        self.assertEqual(manifest["slide_proxy_penalty"]["expected_selected_go2_bodies"], 4)
        self.assertEqual(manifest["slide_proxy_penalty"]["threshold_n"], 1.)
        self.assertIn("not exact contact-point slip", manifest["slide_proxy_penalty"]["interpretation_limit"])
        cfg = NS(scene=NS(base_height_scanner=object()), rewards=NS(old=NS(weight=1.)))
        with self.assertRaisesRegex(ValueError, "contact_forces sensor"):
            configure_stair_rewards(cfg, "contact_slide")
        self.assertEqual(cfg.rewards.old.weight, 1.)

    def test_slide_profile_four_named_feet_strict_history_gate_xy_sum_and_exclusions(self):
        from isaaclab.utils.string import resolve_matching_names
        names = ["base", "Head_lower"] + [f"{leg}_{part}" for leg in ("FL", "FR", "RL", "RR")
                                          for part in ("hip", "foot", "calf", "thigh")]
        class ContactSensor:
            body_names = names
            num_sensors = len(names)

            def find_sensors(self, keys, preserve_order=False):
                return resolve_matching_names(keys, self.body_names, preserve_order=preserve_order)

        class Robot:
            body_names = names
            num_bodies = len(names)

            def find_bodies(self, keys, preserve_order=False):
                return resolve_matching_names(keys, self.body_names, preserve_order=preserve_order)

        sensor, robot = ContactSensor(), Robot()
        force = torch.zeros(3, 3, len(names), 3)
        velocity = torch.zeros(3, len(names), 3)
        # Retained horizontal normal, with current contact absent, still gates XY speed.
        force[0, 2, names.index("FR_foot"), 0] = 2.
        velocity[0, names.index("FR_foot")] = torch.tensor([3., 4., 100.])
        # A vector norm exactly1N is excluded by the strict gate.
        force[1, 0, names.index("FL_foot"), :2] = torch.tensor([.6, .8])
        velocity[1, names.index("FL_foot"), 0] = 10.
        # Two independently contacted feet sum; Z speed is irrelevant.
        force[2, 1, names.index("FL_foot"), 0] = 2.
        force[2, 2, names.index("RR_foot"), 2] = 2.
        velocity[2, names.index("FL_foot")] = torch.tensor([1., 2., 50.])
        velocity[2, names.index("RR_foot")] = torch.tensor([2., 0., 70.])
        # Unselected body impacts/motion and uncontacted foot speed do not contribute.
        force[:, :, names.index("RL_calf"), 2] = 500.
        velocity[:, names.index("RL_calf"), :2] = 100.
        velocity[:, names.index("RL_foot"), :2] = 100.
        sensor.data = NS(net_normal_forces_w_history=NS(torch=force))
        robot.data = NS(body_lin_vel_w=NS(torch=velocity))
        class Scene(dict):
            pass
        scene = Scene(contact_forces=sensor, robot=robot)
        scene.sensors = {"contact_forces": sensor}
        cfg = NS(scene=NS(base_height_scanner=object(), contact_forces=object()), rewards=NS())
        configure_stair_rewards(cfg, "contact_slide")
        term = cfg.rewards.feet_slide
        sensor_cfg, asset_cfg = term.params["sensor_cfg"], term.params["asset_cfg"]
        sensor_cfg.resolve(scene)
        asset_cfg.resolve(scene)
        expected = [f"{leg}_foot" for leg in ("FL", "FR", "RL", "RR")]
        self.assertEqual([names[i] for i in sensor_cfg.body_ids], expected)
        self.assertEqual([names[i] for i in asset_cfg.body_ids], expected)
        leg_cfg = cfg.rewards.leg_contacts.params["sensor_cfg"]
        leg_cfg.resolve(scene)
        self.assertEqual({names[i] for i in leg_cfg.body_ids},
                         {f"{leg}_{part}" for leg in ("FL", "FR", "RL", "RR") for part in ("thigh", "calf")})
        env = NS(scene=scene, step_dt=.02)
        force_before, velocity_before = force.clone(), velocity.clone()
        torch.testing.assert_close(feet_slide_l2(env, **term.params), torch.tensor([25., 0., 9.]))
        env.step_dt = .1
        torch.testing.assert_close(feet_slide_l2(env, **term.params), torch.tensor([25., 0., 9.]))
        torch.testing.assert_close(force, force_before)
        torch.testing.assert_close(velocity, velocity_before)

    def test_force_profile_preserves_every_contact_term_and_adds_only_bounded_proxy(self):
        def config():
            return NS(scene=NS(base_height_scanner=object(), contact_forces=object()), rewards=NS())
        baseline, modified = config(), config()
        original = configure_stair_rewards(baseline, "contact")
        manifest = configure_stair_rewards(modified, "contact_force")
        self.assertEqual(manifest["weights"], {**original["weights"], "leg_contact_force_proxy": -.02})
        for name in original["weights"]:
            self.assertEqual(getattr(baseline.rewards, name).to_dict(),
                             getattr(modified.rewards, name).to_dict(), name)
        self.assertEqual(manifest["contact_penalty"], original["contact_penalty"])
        self.assertEqual(manifest["tuned_changes"], [])
        self.assertEqual(len(manifest["adaptation_changes"]), 2)
        term = modified.rewards.leg_contact_force_proxy
        self.assertEqual(term.func, "stair_rewards:leg_contact_force_proxy")
        self.assertEqual(term.weight, -.02)
        self.assertEqual({k: v for k, v in term.params.items() if k != "sensor_cfg"},
                         {"threshold_n": 50., "force_scale_n": 50., "cap_per_body": 4.})
        self.assertEqual(manifest["force_proxy_penalty"]["baseline_profile"], "contact")
        self.assertIn("not impact impulse", manifest["force_proxy_penalty"]["interpretation_limit"])
        cfg = NS(scene=NS(base_height_scanner=object()), rewards=NS(old=NS(weight=1.)))
        with self.assertRaisesRegex(ValueError, "contact_forces sensor"):
            configure_stair_rewards(cfg, "contact_force")
        self.assertEqual(cfg.rewards.old.weight, 1.)

    def test_force_proxy_vector_norm_history_peak_per_body_cap_and_multiple_bodies(self):
        # Named columns deliberately interleave feet/base with the selected legs.
        names = ["FR_foot", "FR_calf", "base", "FL_thigh", "FL_foot", "RL_calf"]
        history = torch.zeros(6, 3, len(names), 3)
        history[0, 1, 1, 0] = 50.  # Boundary; current is zero.
        history[1, 2, 1, :2] = torch.tensor([60., 80.])  # Norm100, not z or component max.
        history[2, 0, 1, 0] = 150.
        history[3, 0, 1, 0] = 1000.  # Bounded, no linear force spill.
        history[4, 0, 1, 0] = 1000.
        history[4, 2, 3, 1] = 100.  # Different body's peak in a different history slot.
        history[4, 1, 5, 2] = 75.  # sum independent caps:4+1+.25.
        history[5, :, [0, 2, 4], 2] = 10000.  # Unselected feet/base don't contribute.
        current = torch.zeros(6, len(names), 3)
        sensor = NS(data=NS(net_normal_forces_w_history=NS(torch=history),
                            net_normal_forces_w=NS(torch=current)))
        env = NS(scene={"contact": sensor}, step_dt=.02)
        selection = NS(name="contact", body_ids=[1, 3, 5])
        before = history.clone()
        rng_before = torch.random.get_rng_state().clone()
        torch.testing.assert_close(leg_contact_force_proxy(env, selection),
                                   torch.tensor([0., 1., 4., 4., 5.25, 0.]))
        torch.testing.assert_close(leg_contact_force_proxy(env, selection),
                                   torch.tensor([0., 1., 4., 4., 5.25, 0.]))
        self.assertTrue(torch.equal(history, before))
        self.assertTrue(torch.equal(torch.random.get_rng_state(), rng_before))
        env.step_dt = .1  # The reward manager, not this function, applies dt.
        torch.testing.assert_close(leg_contact_force_proxy(env, selection),
                                   torch.tensor([0., 1., 4., 4., 5.25, 0.]))

    def test_force_proxy_disabled_and_zero_length_history_use_current_sample(self):
        current = torch.zeros(2, 2, 3)
        current[0, 0, 1] = 100.
        current[1, 0, 0] = 75.
        current[:, 1, 2] = 5000.  # Excluded body.
        data = NS(net_normal_forces_w=NS(torch=current))
        env = NS(scene={"contact": NS(data=data)})
        cfg = NS(name="contact", body_ids=[0])
        for history in (None, torch.empty(2, 0, 2, 3)):
            with self.subTest(history_disabled=history is None):
                data.net_normal_forces_w_history = None if history is None else NS(torch=history)
                torch.testing.assert_close(leg_contact_force_proxy(env, cfg), torch.tensor([1., .25]))
        del data.net_normal_forces_w_history
        torch.testing.assert_close(leg_contact_force_proxy(env, cfg), torch.tensor([1., .25]))

    def test_force_proxy_runtime_selector_resolves_same_eight_leg_bodies(self):
        from isaaclab.utils.string import resolve_matching_names
        names = ["base", "Head_lower"] + [f"{leg}_{body}" for leg in ("FL", "FR", "RL", "RR")
                        for body in ("foot", "calf", "hip", "thigh")]
        class ContactSensor:
            body_names = names
            num_sensors = len(names)

            def find_sensors(self, keys, preserve_order=False):
                return resolve_matching_names(keys, self.body_names, preserve_order=preserve_order)
        sensor = ContactSensor()
        force = torch.zeros(2, 3, len(names), 3)
        force[0, 1, names.index("FR_calf"), 1] = 100.
        force[1, :, names.index("FR_foot"), 0] = 1000.
        sensor.data = NS(net_normal_forces_w_history=NS(torch=force))
        class Scene(dict):
            pass
        scene = Scene(contact_forces=sensor)
        scene.sensors = {"contact_forces": sensor}
        cfg = NS(scene=NS(base_height_scanner=object(), contact_forces=object()), rewards=NS())
        configure_stair_rewards(cfg, "contact_force")
        count = cfg.rewards.leg_contacts.params["sensor_cfg"]
        term = cfg.rewards.leg_contact_force_proxy
        selection = term.params["sensor_cfg"]
        count.resolve(scene)
        selection.resolve(scene)
        self.assertEqual(selection.body_ids, count.body_ids)
        self.assertEqual({names[i] for i in selection.body_ids},
                         {f"{leg}_{body}" for leg in ("FL", "FR", "RL", "RR") for body in ("thigh", "calf")})
        torch.testing.assert_close(leg_contact_force_proxy(NS(scene=scene), **term.params), torch.tensor([1., 0.]))

    def test_force_proxy_rejects_invalid_scaling_parameters_before_sensor_access(self):
        for parameter, values in (("threshold_n", [-1., math.nan, math.inf]),
                                  ("force_scale_n", [0., -1., math.nan, math.inf]),
                                  ("cap_per_body", [0., -1., math.nan, math.inf])):
            for value in values:
                with self.subTest(parameter=parameter, value=value):
                    with self.assertRaisesRegex(ValueError, parameter):
                        leg_contact_force_proxy(NS(scene={}), NS(name="missing"), **{parameter: value})


if __name__ == "__main__":
    unittest.main()
