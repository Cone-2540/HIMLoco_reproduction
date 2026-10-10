"""CPU command sampling checks against the actual Isaac Lab parent sampler."""

import unittest
from types import SimpleNamespace
from unittest import mock

import torch
from isaaclab.envs.mdp.commands import UniformVelocityCommand

from commands import HIMVelocityCommand, HIMVelocityCommandCfg


def make_command(fraction=0.25, n=7, *, replay=False, flat_mask=None):
    # Resampling and command post-processing only require these buffers. Avoid
    # constructing a scene, physics backend, visualization or simulator app.
    command = object.__new__(HIMVelocityCommand)
    command._env = SimpleNamespace(num_envs=n, device="cpu")
    command.cfg = HIMVelocityCommandCfg(
        asset_name="robot", turn_fraction=fraction, replay_enabled=replay, heading_command=True,
        rel_heading_envs=1.0, rel_standing_envs=1.0,
        ranges=HIMVelocityCommandCfg.Ranges(
            lin_vel_x=(-1.0, 1.0), lin_vel_y=(-0.7, 0.7),
            ang_vel_z=(-1.0, 1.0), heading=(-3.14, 3.14),
        ),
    )
    command.vel_command_b = torch.full((n, 3), 7.0)
    command.heading_target = torch.full((n,), 8.0)
    command.is_heading_env = torch.ones(n, dtype=torch.bool)
    command.is_standing_env = torch.ones(n, dtype=torch.bool)
    command.robot = SimpleNamespace(data=SimpleNamespace(heading_w=SimpleNamespace(torch=torch.zeros(n))))
    command.replay_category = torch.full((n,), -1, dtype=torch.long)
    if flat_mask is not None:
        command._replay_flat_mask = torch.as_tensor(flat_mask, dtype=torch.bool)
    return command


class CommandTest(unittest.TestCase):
    def test_selected_subset_preserves_parent_yaw_and_nonturn_samples(self):
        ids = torch.tensor([5, 1, 4])
        stock, mixed = make_command(), make_command()
        torch.manual_seed(31)
        UniformVelocityCommand._resample_command(stock, ids)
        torch.manual_seed(31)
        with mock.patch("commands.torch.rand", return_value=torch.tensor([0.1, 0.7, 0.2])):
            mixed._resample_command(ids)
        turns = torch.tensor([5, 4])
        torch.testing.assert_close(mixed.vel_command_b[turns, :2], torch.zeros(2, 2))
        torch.testing.assert_close(mixed.vel_command_b[:, 2], stock.vel_command_b[:, 2])
        torch.testing.assert_close(mixed.heading_target, stock.heading_target)
        self.assertFalse(mixed.is_heading_env[turns].any())
        self.assertFalse(mixed.is_standing_env[turns].any())
        untouched = torch.tensor([0, 1, 2, 3, 6])
        torch.testing.assert_close(mixed.vel_command_b[untouched], stock.vel_command_b[untouched])
        torch.testing.assert_close(mixed.is_heading_env[untouched], stock.is_heading_env[untouched])
        torch.testing.assert_close(mixed.is_standing_env[untouched], stock.is_standing_env[untouched])
        mixed._update_command()
        # Heading processing and standing processing must preserve sampled turns.
        torch.testing.assert_close(mixed.vel_command_b[turns, 2], stock.vel_command_b[turns, 2])
        torch.testing.assert_close(mixed.vel_command_b[turns, :2], torch.zeros(2, 2))

    def test_zero_fraction_is_exactly_stock_sampling_without_extra_rng(self):
        stock, mixed = make_command(0.0), make_command(0.0)
        ids = [6, 2, 0]
        torch.manual_seed(13)
        UniformVelocityCommand._resample_command(stock, ids)
        expected_rng = torch.random.get_rng_state()
        torch.manual_seed(13)
        with mock.patch.object(mixed, "_flat_replay_mask", side_effect=AssertionError("replay is disabled")):
            mixed._resample_command(ids)
        torch.testing.assert_close(torch.random.get_rng_state(), expected_rng)
        for name in ("vel_command_b", "heading_target", "is_heading_env", "is_standing_env"):
            torch.testing.assert_close(getattr(mixed, name), getattr(stock, name))

    def test_probability_and_yaw_ranges_are_preserved(self):
        n = 4096
        mixed = make_command(n=n)
        torch.manual_seed(5)
        mixed._resample_command(torch.arange(n))
        turns = ~mixed.is_heading_env
        fraction = turns.float().mean().item()
        self.assertGreater(fraction, 0.20)
        self.assertLess(fraction, 0.30)
        torch.testing.assert_close(mixed.vel_command_b[turns, :2], torch.zeros(int(turns.sum()), 2))
        self.assertTrue((mixed.vel_command_b[:, 2].abs() <= 1.0).all())
        self.assertTrue((mixed.vel_command_b[turns, 2] > 0.8).any())
        self.assertTrue((mixed.vel_command_b[turns, 2] < -0.8).any())

    def test_invalid_fractions_and_empty_subset_do_not_mutate_buffers(self):
        command = make_command()
        before = command.vel_command_b.clone()
        command._resample_command(torch.empty(0, dtype=torch.long))
        torch.testing.assert_close(command.vel_command_b, before)
        for fraction in (-0.1, 1.1, float("nan"), float("inf")):
            command.cfg.turn_fraction = fraction
            with self.assertRaisesRegex(ValueError, "turn_fraction"):
                command._resample_command([0, 2])
            torch.testing.assert_close(command.vel_command_b, before)

    def test_real_parent_initialization_does_not_sample_or_resolve_disabled_replay(self):
        template = make_command(0.0)
        registry = SimpleNamespace(clear_debug_vis_callback=mock.Mock())
        env = SimpleNamespace(num_envs=7, device="cpu", scene={"robot": template.robot},
                              sim=SimpleNamespace(vis_marker_registry=registry))
        before = torch.random.get_rng_state()
        with mock.patch.object(HIMVelocityCommand, "_flat_replay_mask",
                               side_effect=AssertionError("replay is disabled")):
            command = HIMVelocityCommand(template.cfg, env)
        torch.testing.assert_close(torch.random.get_rng_state(), before)
        torch.testing.assert_close(command.vel_command_b, torch.zeros(7, 3))
        torch.testing.assert_close(command.replay_category, torch.full((7,), -1, dtype=torch.long))

    def test_real_initialization_resolves_flat_identity_from_terrain_metadata(self):
        from stair_terrain import build_stair_generator, flat_env_mask

        class Scene(dict):
            pass

        template = make_command(0.0, replay=True)
        generator = build_stair_generator("standard", flat_fraction=.25)
        scene = Scene(robot=template.robot)
        # Deliberately shuffle columns; category selection must follow terrain
        # metadata rather than assuming the first quarter of environment IDs.
        scene.terrain = SimpleNamespace(cfg=SimpleNamespace(terrain_generator=generator),
                                        terrain_types=torch.tensor([31, 0, 8, 7, 15, 4, 23]))
        registry = SimpleNamespace(clear_debug_vis_callback=mock.Mock())
        env = SimpleNamespace(num_envs=7, device="cpu", scene=scene,
                              sim=SimpleNamespace(vis_marker_registry=registry))
        before = torch.random.get_rng_state()
        command = HIMVelocityCommand(template.cfg, env)
        torch.testing.assert_close(torch.random.get_rng_state(), before)
        expected = torch.tensor([False, True, False, True, False, True, False])
        torch.testing.assert_close(command._flat_replay_mask(), expected)
        torch.testing.assert_close(command._flat_replay_mask(), flat_env_mask(env))
        command._resample_command(torch.arange(7))
        self.assertTrue((command.replay_category[expected] >= 0).all())
        self.assertTrue((command.replay_category[~expected] == -1).all())

    def test_no_flat_columns_add_no_rng_to_parent_sampling(self):
        stock = make_command(0.0)
        mixed = make_command(0.0, replay=True, flat_mask=[False] * 7)
        ids = [4, 0, 6]
        torch.manual_seed(89)
        UniformVelocityCommand._resample_command(stock, ids)
        expected_rng = torch.random.get_rng_state()
        torch.manual_seed(89)
        mixed._resample_command(ids)
        torch.testing.assert_close(torch.random.get_rng_state(), expected_rng)
        for name in ("vel_command_b", "heading_target", "is_heading_env", "is_standing_env"):
            torch.testing.assert_close(getattr(mixed, name), getattr(stock, name))

    def test_flat_subset_cannot_change_stair_parent_samples_or_unsampled_environments(self):
        mask = [True, False, True, False, False, True, False, False]
        stock = make_command(0.0, n=8)
        mixed = make_command(0.0, n=8, replay=True, flat_mask=mask)
        ids = torch.tensor([7, 2, 5, 0])
        torch.manual_seed(17)
        UniformVelocityCommand._resample_command(stock, ids)
        torch.manual_seed(17)
        mixed._resample_command(ids)
        stair_ids = torch.tensor([7])
        untouched = torch.tensor([1, 3, 4, 6])
        for name in ("vel_command_b", "heading_target", "is_heading_env", "is_standing_env"):
            torch.testing.assert_close(getattr(mixed, name)[stair_ids], getattr(stock, name)[stair_ids])
            torch.testing.assert_close(getattr(mixed, name)[untouched], getattr(stock, name)[untouched])
        self.assertTrue((mixed.replay_category[stair_ids] == -1).all())
        self.assertTrue((mixed.replay_category[untouched] == -1).all())
        sampled_flat = torch.tensor([2, 5, 0])
        before_update = mixed.vel_command_b[sampled_flat].clone()
        self.assertFalse(mixed.is_heading_env[sampled_flat].any())
        self.assertFalse(mixed.is_standing_env[sampled_flat].any())
        stock._update_command()
        mixed._update_command()
        torch.testing.assert_close(mixed.vel_command_b[sampled_flat], before_update)
        torch.testing.assert_close(mixed.vel_command_b[stair_ids], stock.vel_command_b[stair_ids])

    def test_replay_category_distribution_signed_axes_and_continuous_ranges(self):
        n = 32768
        mixed = make_command(0.0, n=n, replay=True, flat_mask=torch.ones(n, dtype=torch.bool))
        torch.manual_seed(211)
        mixed._resample_command(torch.arange(n))
        category = mixed.replay_category
        counts = torch.bincount(category, minlength=7).float() / n
        self.assertLess(abs(counts[0].item() - 0.1), 0.008)
        self.assertTrue(((counts[1:] - 0.15).abs() < 0.008).all())
        commands = mixed.vel_command_b
        torch.testing.assert_close(commands[category == 0], torch.zeros(int((category == 0).sum()), 3))
        self.assertTrue(((commands[category != 0] != 0).sum(dim=1) == 1).all())
        for index, (axis, sign, low, high) in enumerate(
                ((0, 1, .2, .65), (0, -1, .2, .65), (1, 1, .15, .35),
                 (1, -1, .15, .35), (2, 1, .2, .6), (2, -1, .2, .6)), 1):
            values = commands[category == index, axis] * sign
            self.assertTrue(((values >= low) & (values <= high)).all())
            # Each category reaches both ends of its continuous distribution.
            self.assertLess(values.min().item(), low + (high - low) * .03)
            self.assertGreater(values.max().item(), high - (high - low) * .03)
            self.assertGreater(torch.unique(values).numel(), 1000)
        before_update = commands.clone()
        mixed._update_command()
        torch.testing.assert_close(commands, before_update)

    def test_turn_fraction_applies_only_to_stairs_during_replay(self):
        n = 1024
        mask = torch.arange(n) % 2 == 0
        mixed = make_command(1.0, n=n, replay=True, flat_mask=mask)
        mixed.cfg.replay_standing_fraction = 0.0
        torch.manual_seed(53)
        mixed._resample_command(torch.arange(n))
        stair_ids = (~mask).nonzero().flatten()
        flat_ids = mask.nonzero().flatten()
        torch.testing.assert_close(mixed.vel_command_b[stair_ids, :2], torch.zeros(len(stair_ids), 2))
        self.assertTrue((mixed.replay_category[stair_ids] == -1).all())
        self.assertTrue((mixed.replay_category[flat_ids] > 0).all())
        self.assertTrue((mixed.vel_command_b[flat_ids, :2].abs().sum(dim=1) > 0).any())
        self.assertFalse(mixed.is_heading_env.any())
        self.assertFalse(mixed.is_standing_env.any())

    def test_all_standing_and_subset_resampling_preserve_other_categories(self):
        mixed = make_command(0.0, n=7, replay=True, flat_mask=[True] * 7)
        mixed.cfg.replay_standing_fraction = 1.0
        mixed.replay_category[:] = 6
        ids = torch.tensor([6, 1, 3])
        mixed._resample_command(ids)
        torch.testing.assert_close(mixed.vel_command_b[ids], torch.zeros(3, 3))
        self.assertTrue((mixed.replay_category[ids] == 0).all())
        self.assertTrue((mixed.replay_category[[0, 2, 4, 5]] == 6).all())
        mixed._update_command()
        torch.testing.assert_close(mixed.vel_command_b[ids], torch.zeros(3, 3))

    def test_bad_replay_settings_fail_before_parent_sampling_or_rng_draws(self):
        command = make_command(0.0, replay=True, flat_mask=[True] * 7)
        cases = [("replay_standing_fraction", value)
                 for value in (None, "bad", -.1, 1.1, float("nan"), float("inf"))]
        cases += [(name, value) for name in ("replay_vx_range", "replay_vy_range", "replay_yaw_range")
                  for value in (None, (.2,), (.2, .3, .4), (0., .3), (-.1, .3), (.4, .3),
                                (.2, float("nan")), (.2, float("inf")), ("bad", .3))]
        for name, value in cases:
            original = getattr(command.cfg, name)
            setattr(command.cfg, name, value)
            before = command.vel_command_b.clone()
            before_rng = torch.random.get_rng_state()
            with self.assertRaisesRegex(ValueError, name):
                command._resample_command([0, 2])
            torch.testing.assert_close(command.vel_command_b, before)
            torch.testing.assert_close(torch.random.get_rng_state(), before_rng)
            setattr(command.cfg, name, original)

    def test_replay_empty_subset_draws_nothing(self):
        command = make_command(0.0, replay=True, flat_mask=[True] * 7)
        before = command.vel_command_b.clone()
        before_rng = torch.random.get_rng_state()
        command._resample_command(torch.empty(0, dtype=torch.long))
        torch.testing.assert_close(command.vel_command_b, before)
        torch.testing.assert_close(torch.random.get_rng_state(), before_rng)

    def test_malformed_terrain_masks_fail_before_parent_sampling(self):
        command = make_command(0.0, replay=True)
        for value in (torch.zeros(7), torch.zeros(6, dtype=torch.bool), torch.zeros(7, 1, dtype=torch.bool)):
            with mock.patch("stair_terrain.flat_env_mask", return_value=value):
                before = command.vel_command_b.clone()
                before_rng = torch.random.get_rng_state()
                with self.assertRaisesRegex(ValueError, "flat_env_mask"):
                    command._resample_command([0, 2])
                torch.testing.assert_close(command.vel_command_b, before)
                torch.testing.assert_close(torch.random.get_rng_state(), before_rng)


if __name__ == "__main__":
    unittest.main()
