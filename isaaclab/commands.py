"""Mix pure turning commands into Isaac Lab's existing velocity sampler.

The original sampler remains responsible for all velocity ranges and heading
targets. The selected fraction receives zero XY velocity and its sampled yaw
rate, so heading control and standing selection cannot erase pure turning.
"""

import math

import torch
from isaaclab.envs.mdp.commands import UniformVelocityCommand, UniformVelocityCommandCfg
from isaaclab.utils import configclass


class HIMVelocityCommand(UniformVelocityCommand):
    """Stock velocity sampling plus a configurable probability of pure turning."""

    def _resample_command(self, env_ids):
        fraction = float(getattr(self.cfg, "turn_fraction", 0.25))
        if not math.isfinite(fraction) or not 0.0 <= fraction <= 1.0:
            raise ValueError("turn_fraction must be finite and between 0 and 1")
        if len(env_ids) == 0:
            return
        super()._resample_command(env_ids)
        if fraction == 0.0:
            return
        selected = torch.rand(len(env_ids), device=self.device) < fraction
        turn_ids = torch.as_tensor(env_ids, dtype=torch.long, device=self.device)[selected]
        self.vel_command_b[turn_ids, :2] = 0.0
        self.is_heading_env[turn_ids] = False
        self.is_standing_env[turn_ids] = False


@configclass
class HIMVelocityCommandCfg(UniformVelocityCommandCfg):
    """Preserve stock command fields and add a pure-turn sampling fraction."""

    class_type: type = HIMVelocityCommand
    turn_fraction: float = 0.25
