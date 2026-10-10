"""CPU command sampling checks against the actual Isaac Lab parent sampler."""

import unittest
from types import SimpleNamespace
from unittest import mock

import torch
from isaaclab.envs.mdp.commands import UniformVelocityCommand

from commands import HIMVelocityCommand, HIMVelocityCommandCfg


def make_command(fraction=0.25, n=7):
    # Resampling and command post-processing only require these buffers. Avoid
    # constructing a scene, physics backend, visualization or simulator app.
    command = object.__new__(HIMVelocityCommand)
    command._env = SimpleNamespace(num_envs=n, device="cpu")
    command.cfg = HIMVelocityCommandCfg(
        asset_name="robot", turn_fraction=fraction, heading_command=True,
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


if __name__ == "__main__":
    unittest.main()
