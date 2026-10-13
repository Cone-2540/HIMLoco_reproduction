"""Reset-randomized command latency and drive strength, retaining Lab's DC curve.

Latency is measured in physics substeps (5 ms), never policy frames (20 ms).
The buffered signal is the requested joint position, not the state measurement.
"""
import copy
import torch
from isaaclab.actuators import DCMotor, DCMotorCfg
from isaaclab.utils import configclass
from isaaclab.utils.buffers import DelayBuffer


class DeploymentMotor(DCMotor):
    def __init__(self, cfg, *args, **kwargs):
        super().__init__(cfg, *args, **kwargs)
        self.positions_delay_buffer = DelayBuffer(cfg.max_delay, self._num_envs, self._device)
        self.drive_strength = torch.ones(self._num_envs, self.num_joints, device=self._device)
        self._ALL_INDICES = torch.arange(self._num_envs, device=self._device)

    def reset(self, env_ids=None):
        super().reset(env_ids)
        ids = self._ALL_INDICES if env_ids is None or isinstance(env_ids, slice) else env_ids
        if isinstance(env_ids, slice):
            ids = self._ALL_INDICES[env_ids]
        low, high = self.cfg.strength_range
        self.drive_strength[ids] = torch.empty(len(ids), self.num_joints, device=self._device).uniform_(low, high)
        lag = torch.randint(self.cfg.min_delay, self.cfg.max_delay+1, (len(ids),), dtype=torch.int, device=self._device)
        self.positions_delay_buffer.set_time_lag(lag, ids)
        self.positions_delay_buffer.reset(ids)

    def compute(self, control_action, joint_pos, joint_vel):
        delayed = copy.copy(control_action)
        delayed.joint_positions = self.positions_delay_buffer.compute(control_action.joint_positions)
        return super().compute(delayed, joint_pos, joint_vel)

    def _clip_effort(self, effort):
        # The whole DC envelope scales with physical drive strength. Keep the
        # final result within the original robot effort limit in both directions.
        envelope = super()._clip_effort(effort)
        return torch.clamp(envelope*self.drive_strength,
                           min=-self.actuator_effort_limit, max=self.actuator_effort_limit)


@configclass
class DeploymentMotorCfg(DCMotorCfg):
    class_type = DeploymentMotor
    min_delay: int = 0
    max_delay: int = 2
    strength_range: tuple[float,float] = (.9,1.1)


def deployment_config(original):
    cfg = DeploymentMotorCfg()
    for key, value in vars(original).items():
        if key != 'class_type':
            setattr(cfg, key, copy.deepcopy(value))
    return cfg
