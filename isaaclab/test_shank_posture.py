"""CPU physics-geometry tests for the support-aware Go2 reward adaptation."""
import math
import unittest
from types import SimpleNamespace as NS
from unittest import mock

import torch

from stair_rewards import configure_stair_rewards, shank_horizontal_l2, slow_mirror_bias_l2


def env_for_angles(angles):
    theta = torch.deg2rad(torch.tensor([angles], dtype=torch.float32))
    knees = torch.zeros(1, 4, 3)
    feet = torch.stack((.213 * theta.sin(), torch.zeros_like(theta), -.213 * theta.cos()), -1)
    sensor = NS(data=NS(net_normal_forces_w_history=torch.zeros(1, 4, 8, 3),
                       net_normal_forces_w=torch.zeros(1, 8, 3)))
    return NS(scene={"robot": NS(data=NS(body_link_pos_w=torch.cat((knees, feet), 1))),
                     "contact_forces": sensor})


KNEES = NS(name="robot", body_ids=[0, 1, 2, 3])
FEET = NS(name="robot", body_ids=[4, 5, 6, 7])
CALF_SENSOR = NS(name="contact_forces", body_ids=[0, 1, 2, 3])
FOOT_SENSOR = NS(name="contact_forces", body_ids=[4, 5, 6, 7])


def reward(env):
    return shank_horizontal_l2(env, KNEES, FEET, FOOT_SENSOR, CALF_SENSOR)


class ShankPostureTest(unittest.TestCase):
    def test_default_stance_and_threshold_are_unpenalized(self):
        torch.testing.assert_close(reward(env_for_angles([40., 40., 29., 65.])), torch.zeros(1))

    def test_calf_support_cannot_bypass_full_penalty_and_history_is_used(self):
        env = env_for_angles([90., 90., 40., 40.])
        torch.testing.assert_close(reward(env), torch.tensor([.125]))
        force = env.scene["contact_forces"].data.net_normal_forces_w_history
        force[0, 1, 4, 2] = 20.  # FL foot supported in a previous substep.
        force[0, 2, 1, 2] = 20.  # FR calf supported, with its foot unloaded.
        torch.testing.assert_close(reward(env), torch.tensor([.5]))

    def test_world_geometry_ignores_translation_and_heading_rotation(self):
        env = env_for_angles([80., 90., 35., 60.])
        expected = reward(env)
        positions = env.scene["robot"].data.body_link_pos_w
        yaw = torch.tensor([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
        env.scene["robot"].data.body_link_pos_w = positions @ yaw.T + torch.tensor([50., -40., 2.])
        torch.testing.assert_close(reward(env), expected, atol=1e-5, rtol=1e-5)

    def test_leg_order_and_current_only_sensor_fallback(self):
        env = env_for_angles([90., 40., 40., 40.])
        data = env.scene["contact_forces"].data
        data.net_normal_forces_w_history = torch.zeros(1, 0, 8, 3)
        data.net_normal_forces_w[0, 4, 2] = 3.
        torch.testing.assert_close(reward(env), torch.tensor([.25]))
        data.net_normal_forces_w[0, 4, 2] = 0.
        data.net_normal_forces_w[0, 5, 2] = 3.  # FR support cannot gate FL.
        torch.testing.assert_close(reward(env), torch.tensor([.0625]))

    def test_upward_and_degenerate_shanks_remain_finite_and_bounded(self):
        env = env_for_angles([180., 150., 90., 0.])
        force = env.scene["contact_forces"].data.net_normal_forces_w_history
        force[:, :, :, 2] = 10.
        value = reward(env)
        self.assertTrue(torch.isfinite(value).all())
        self.assertLessEqual(float(value), 4.)
        env.scene["robot"].data.body_link_pos_w.zero_()
        self.assertTrue(torch.isfinite(reward(env)).all())

    def test_posture_adds_only_one_term_and_preserves_leg_order(self):
        managers = NS(RewardTermCfg=lambda **kw: NS(**kw),
                      SceneEntityCfg=lambda name, **kw: NS(name=name, **kw))
        def config():
            return NS(scene=NS(base_height_scanner=object(), contact_forces=object()), rewards=NS())
        with mock.patch.dict("sys.modules", {"isaaclab.managers": managers}):
            faithful, posture = config(), config()
            original = configure_stair_rewards(faithful)
            adapted = configure_stair_rewards(posture, "posture")
            self.assertEqual(adapted["weights"], {**original["weights"], "shank_horizontal": -.08})
            for name in original["weights"]:
                self.assertEqual(vars(getattr(faithful.rewards, name)), vars(getattr(posture.rewards, name)))
            for key, part in (("knee_cfg", "calf"), ("foot_cfg", "foot"),
                              ("foot_sensor_cfg", "foot"), ("calf_sensor_cfg", "calf")):
                selected = posture.rewards.shank_horizontal.params[key]
                self.assertTrue(selected.preserve_order)
                self.assertEqual(selected.body_names, [leg + "_" + part for leg in ("FL", "FR", "RL", "RR")])

    def test_bad_parameters_and_missing_contact_sensor_fail_before_mutation(self):
        for kwargs in ({"posture_weight": .1}, {"posture_angle_deg": 90.},
                       {"posture_swing_weight": 0.}, {"posture_weight": math.nan}):
            with self.assertRaises(ValueError):
                configure_stair_rewards(NS(), "posture", **kwargs)
        old = NS(weight=-.01)
        cfg = NS(scene=NS(base_height_scanner=object()), rewards=NS(old=old))
        with self.assertRaisesRegex(ValueError, "contact_forces"):
            configure_stair_rewards(cfg, "posture")
        self.assertIs(cfg.rewards.old, old)

    def test_user_contact_profile_keeps_posture_and_excludes_feet(self):
        managers = NS(RewardTermCfg=lambda **kw: NS(**kw),
                      SceneEntityCfg=lambda name, **kw: NS(name=name, **kw))
        def config():
            return NS(scene=NS(base_height_scanner=object(), contact_forces=object()), rewards=NS())
        with mock.patch.dict("sys.modules", {"isaaclab.managers": managers}):
            baseline, modified = config(), config()
            original = configure_stair_rewards(baseline, "posture")
            combined = configure_stair_rewards(modified, "posture_contact")
            self.assertEqual(combined["weights"], {**original["weights"],
                             "head_undesired_contacts": -1., "other_undesired_contacts": -.01})
            for name in original["weights"]:
                self.assertEqual(vars(getattr(baseline.rewards, name)), vars(getattr(modified.rewards, name)))
            self.assertEqual(modified.rewards.head_undesired_contacts.params["sensor_cfg"].body_names, ["Head_.*"])
            self.assertEqual(modified.rewards.other_undesired_contacts.params["sensor_cfg"].body_names,
                             [".*_hip", ".*_thigh", ".*_calf"])
            self.assertEqual(modified.rewards.other_undesired_contacts.params["threshold"], .3)
            self.assertEqual(modified.rewards.head_undesired_contacts.params["threshold"], .3)
            self.assertEqual(len(combined["adaptation_changes"]), 2)


class SlowMirrorBiasTest(unittest.TestCase):
    def test_optional_loaded_calf_term_keeps_original_objective_and_excludes_feet(self):
        managers = NS(RewardTermCfg=lambda **kw: NS(**kw),
                      SceneEntityCfg=lambda name, **kw: NS(name=name, **kw))
        def config():
            return NS(scene=NS(base_height_scanner=object(), contact_forces=object()), rewards=NS())
        with mock.patch.dict("sys.modules", {"isaaclab.managers": managers}):
            before, after = config(), config()
            original = configure_stair_rewards(before, "posture_symmetric", symmetry_stair_scale=.5)
            added = configure_stair_rewards(after, "posture_symmetric", symmetry_stair_scale=.5,
                                            calf_contact_weight=-.05)
            self.assertEqual(added["weights"], {**original["weights"], "calf_loaded_contacts": -.05})
            for name in original["weights"]:
                self.assertEqual(vars(getattr(before.rewards, name)), vars(getattr(after.rewards, name)))
            term = after.rewards.calf_loaded_contacts
            self.assertEqual(term.func, "isaaclab.envs.mdp:undesired_contacts")
            self.assertEqual(term.params["threshold"], 1.)
            self.assertEqual(term.params["sensor_cfg"].body_names,
                             [leg + "_calf" for leg in ("FL", "FR", "RL", "RR")])

    def test_invalid_calf_weight_or_duplicate_profile_fails_before_mutation(self):
        for value in (.1, math.nan, math.inf):
            with self.assertRaisesRegex(ValueError, "calf_contact_weight"):
                configure_stair_rewards(NS(), "posture_symmetric", calf_contact_weight=value)
        for profile in ("faithful", "stock", "posture_contact", "contact"):
            with self.assertRaisesRegex(ValueError, "calf_contact_weight"):
                configure_stair_rewards(NS(), profile, calf_contact_weight=-.05)

    def test_profile_adds_only_slow_bias_and_validates_joint_order(self):
        managers = NS(RewardTermCfg=lambda **kw: NS(**kw),
                      SceneEntityCfg=lambda name, **kw: NS(name=name, **kw))
        def config():
            return NS(scene=NS(base_height_scanner=object(), contact_forces=object()), rewards=NS())
        with mock.patch.dict("sys.modules", {"isaaclab.managers": managers}):
            base, symmetric = config(), config()
            baseline = configure_stair_rewards(base, "posture", posture_weight=-.24)
            adapted = configure_stair_rewards(symmetric, "posture_symmetric", posture_weight=-.24)
            self.assertEqual(adapted["weights"], {**baseline["weights"], "slow_mirror_bias": -.08})
            cfg = symmetric.rewards.slow_mirror_bias.params["asset_cfg"]
            self.assertEqual(cfg.joint_names, [leg + "_" + part + "_joint"
                for part in ("hip", "thigh", "calf") for leg in ("FL", "FR", "RL", "RR")])
            self.assertTrue(cfg.preserve_order)
            self.assertFalse(adapted["symmetry_penalty"]["actor_inputs_added"])

    def make_env(self):
        q = torch.tensor([[.1, -.1, .1, -.1, .8, .8, 1., 1., -1.5, -1.5, -1.5, -1.5]])
        command = torch.tensor([[.3, 0., 0.]])
        return NS(scene={"robot": NS(data=NS(joint_pos=q))},
                  command_manager=NS(get_command=lambda _: command), command=command,
                  episode_length_buf=torch.ones(1, dtype=torch.long), common_step_counter=1, step_dt=.02)

    def advance(self, env, n=200, alternating=False):
        result = None
        for i in range(n):
            env.common_step_counter += 1
            env.episode_length_buf += 1
            if alternating:
                phase = math.sin(i * .02 * 2 * math.pi * 3)
                env.scene["robot"].data.joint_pos[0, 4:6] = torch.tensor([.8 + .3*phase, .8 - .3*phase])
            result = slow_mirror_bias_l2(env, NS(name="robot", joint_ids=list(range(12))))
        return result

    @mock.patch.dict("sys.modules", {"stair_terrain": NS(flat_env_mask=lambda e: torch.ones(1, dtype=torch.bool))})
    def test_persistent_bias_is_detected_but_alternation_is_not(self):
        env = self.make_env()
        env.scene["robot"].data.joint_pos[0, 4] += .6
        self.assertGreater(float(self.advance(env)), .1)
        env = self.make_env()
        self.assertLess(float(self.advance(env, alternating=True)), .001)

    @mock.patch.dict("sys.modules", {"stair_terrain": NS(flat_env_mask=lambda e: torch.ones(1, dtype=torch.bool))})
    def test_reset_turn_and_repeated_evaluation_have_no_stale_bias(self):
        env = self.make_env()
        env.scene["robot"].data.joint_pos[0, 4] += .6
        before = self.advance(env)
        state = env._him_slow_mirror_bias["mean"].clone()
        torch.testing.assert_close(slow_mirror_bias_l2(env, NS(name="robot", joint_ids=list(range(12)))), before)
        torch.testing.assert_close(env._him_slow_mirror_bias["mean"], state)
        env.episode_length_buf[:] = 0
        self.assertEqual(float(self.advance(env, 1)), 0.)
        self.advance(env)
        env.command[:, 2] = .5
        self.assertEqual(float(self.advance(env, 1)), 0.)
        self.assertEqual(float(env._him_slow_mirror_bias["mean"].abs().max()), 0.)

    @mock.patch.dict("sys.modules", {"stair_terrain": NS(flat_env_mask=lambda e: torch.zeros(1, dtype=torch.bool))})
    def test_stair_environments_are_excluded(self):
        env = self.make_env()
        env.scene["robot"].data.joint_pos[0, 4] += .6
        self.assertEqual(float(self.advance(env)), 0.)

    def test_explicit_stair_exposure_scales_same_bias_and_preserves_default(self):
        def simulate(flat, scale):
            env = self.make_env()
            env.scene["robot"].data.joint_pos[0, 4] += .6
            with mock.patch.dict("sys.modules", {"stair_terrain": NS(
                    flat_env_mask=lambda e: torch.full((1,), flat, dtype=torch.bool))}):
                for _ in range(200):
                    env.common_step_counter += 1
                    env.episode_length_buf += 1
                    value = slow_mirror_bias_l2(env, NS(name="robot", joint_ids=list(range(12))), stair_scale=scale)
            return value
        flat = simulate(True, 0.5)
        stair = simulate(False, 0.5)
        torch.testing.assert_close(stair, flat * .5)
        self.assertEqual(float(simulate(False, 0)), 0.)

    def test_invalid_stair_scale_fails_before_config_mutation(self):
        for value in (-.1, 1.1, math.nan):
            with self.assertRaisesRegex(ValueError, "symmetry_stair_scale"):
                configure_stair_rewards(NS(), "posture_symmetric", symmetry_stair_scale=value)


if __name__ == "__main__":
    unittest.main()
