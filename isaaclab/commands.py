"""Mix turning and optional flat rehearsal into Lab's velocity sampler.

The original sampler remains responsible for all velocity ranges and heading
targets. The selected fraction receives zero XY velocity and its sampled yaw
rate, so heading control and standing selection cannot erase pure turning.
Optional flat rehearsal samples signed single-axis commands only on columns
identified as flat by the terrain configuration. Stair columns retain the
parent sampler and their existing heading control.
"""

import math

import torch
from isaaclab.envs.mdp.commands import UniformVelocityCommand, UniformVelocityCommandCfg
from isaaclab.utils import configclass


class HIMVelocityCommand(UniformVelocityCommand):
    """Stock sampling, optional pure turns, and terrain-masked flat rehearsal."""

    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        # Categories describe the current command, not per-step success:
        # -1: stair/stock; 0: stand; 1..6: +vx, -vx, +vy, -vy, +yaw, -yaw.
        self.replay_category = torch.full((self.num_envs,), -1, dtype=torch.long, device=self.device)
        if getattr(self.cfg, "replay_enabled", False):
            self._validate_replay_config()
            self._flat_replay_mask()

    def _validate_replay_config(self):
        try:
            fraction = float(getattr(self.cfg, "replay_standing_fraction", 0.1))
        except (ValueError, TypeError):
            raise ValueError("replay_standing_fraction must be finite and between 0 and 1") from None
        if not math.isfinite(fraction) or not 0.0 <= fraction <= 1.0:
            raise ValueError("replay_standing_fraction must be finite and between 0 and 1")
        ranges = []
        for name, default in (("replay_vx_range", (0.2, 0.65)),
                              ("replay_vy_range", (0.15, 0.35)),
                              ("replay_yaw_range", (0.2, 0.6))):
            values = getattr(self.cfg, name, default)
            if not isinstance(values, (tuple, list)) or len(values) != 2:
                raise ValueError(f"{name} must contain two positive finite magnitude bounds")
            try:
                bounds = tuple(float(value) for value in values)
            except (ValueError, TypeError):
                raise ValueError(f"{name} must contain two positive finite magnitude bounds") from None
            if not all(math.isfinite(value) for value in bounds) or not 0.0 < bounds[0] <= bounds[1]:
                raise ValueError(f"{name} requires finite 0 < minimum <= maximum")
            ranges.append(bounds)
        return fraction, ranges

    def _flat_replay_mask(self):
        # Terrain types are fixed during Lab's level curriculum. The terrain
        # helper resolves the generator's column metadata, never an ID cutoff.
        mask = getattr(self, "_replay_flat_mask", None)
        if mask is None:
            from stair_terrain import flat_env_mask

            mask = torch.as_tensor(flat_env_mask(self._env), device=self.device)
            if mask.dtype != torch.bool or mask.shape != (self.num_envs,):
                raise ValueError("flat_env_mask must return one boolean per environment")
            self._replay_flat_mask = mask
        return mask

    def _sample_flat_replay(self, env_ids, standing_fraction, ranges):
        count = len(env_ids)
        if count == 0:
            return
        if not hasattr(self, "replay_category"):
            self.replay_category = torch.full((self.num_envs,), -1, dtype=torch.long, device=self.device)
        category = torch.randint(1, 7, (count,), device=self.device)
        standing = torch.rand(count, device=self.device) < standing_fraction
        category[standing] = 0
        # Sample continuous magnitudes for every selected category. Each
        # nonstanding vector has exactly one nonzero component.
        axis = ((category - 1).clamp_min(0) // 2).long()
        lower = torch.tensor([bounds[0] for bounds in ranges], device=self.device)
        upper = torch.tensor([bounds[1] for bounds in ranges], device=self.device)
        magnitude = lower[axis] + torch.rand(count, device=self.device) * (upper[axis] - lower[axis])
        sign = torch.where(category % 2 == 1, 1.0, -1.0)
        magnitude *= sign * (~standing)
        commands = torch.zeros(count, 3, device=self.device)
        commands[torch.arange(count, device=self.device), axis] = magnitude
        self.vel_command_b[env_ids] = commands
        self.replay_category[env_ids] = category
        # Standing is the explicit zero vector. Clearing both stock flags
        # keeps heading/standing post-processing from erasing moving samples.
        self.is_heading_env[env_ids] = False
        self.is_standing_env[env_ids] = False

    def _resample_command(self, env_ids):
        fraction = float(getattr(self.cfg, "turn_fraction", 0.25))
        if not math.isfinite(fraction) or not 0.0 <= fraction <= 1.0:
            raise ValueError("turn_fraction must be finite and between 0 and 1")
        replay = bool(getattr(self.cfg, "replay_enabled", False))
        if replay:
            standing_fraction, ranges = self._validate_replay_config()
        if len(env_ids) == 0:
            return
        if replay:
            ids = torch.as_tensor(env_ids, dtype=torch.long, device=self.device)
            is_flat = self._flat_replay_mask()[ids]
            stair_ids = ids[~is_flat]
            flat_ids = ids[is_flat]
        super()._resample_command(env_ids)
        turn_candidates = stair_ids if replay else env_ids
        if fraction > 0.0 and len(turn_candidates) > 0:
            selected = torch.rand(len(turn_candidates), device=self.device) < fraction
            turn_ids = torch.as_tensor(turn_candidates, dtype=torch.long, device=self.device)[selected]
            self.vel_command_b[turn_ids, :2] = 0.0
            self.is_heading_env[turn_ids] = False
            self.is_standing_env[turn_ids] = False
        if replay:
            self._sample_flat_replay(flat_ids, standing_fraction, ranges)


@configclass
class HIMVelocityCommandCfg(UniformVelocityCommandCfg):
    """Preserve stock fields; flat rehearsal is opt-in and terrain-masked."""

    class_type: type = HIMVelocityCommand
    turn_fraction: float = 0.25
    replay_enabled: bool = False
    replay_standing_fraction: float = 0.1
    replay_vx_range: tuple[float, float] = (0.2, 0.65)
    replay_vy_range: tuple[float, float] = (0.15, 0.35)
    replay_yaw_range: tuple[float, float] = (0.2, 0.6)
