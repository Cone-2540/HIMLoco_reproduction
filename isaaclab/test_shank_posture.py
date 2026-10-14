"""CPU physics-geometry tests for the support-aware Go2 reward adaptation."""
import math
import unittest
from types import SimpleNamespace as NS
from unittest import mock

import torch

from stair_rewards import configure_stair_rewards, shank_horizontal_l2


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


if __name__ == "__main__":
    unittest.main()
