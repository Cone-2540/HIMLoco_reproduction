"""Exercise real Lab DC motors and delay buffers on CPU, including partial resets."""
import copy
import unittest
import torch
from isaaclab.actuators import DCMotor
from isaaclab.utils.types import ArticulationActions
from deployment_motor import DeploymentMotor, DeploymentMotorCfg


def motor(kind=DeploymentMotor, max_delay=2):
    cfg=DeploymentMotorCfg(joint_names_expr=['.*'],stiffness=25.,damping=.5,
                          actuator_effort_limit=23.7,saturation_effort=23.7,
                          actuator_velocity_limit=30.1,max_delay=max_delay)
    return kind(cfg,joint_names=['FL_hip_joint','FR_hip_joint'],joint_ids=slice(None),num_envs=4,device='cpu')


def command(target):
    return ArticulationActions(joint_positions=torch.ones(4,2)*target,
                               joint_velocities=torch.zeros(4,2),joint_efforts=torch.zeros(4,2))


class DeploymentMotorTests(unittest.TestCase):
    def test_nominal_exactly_matches_original_dc_with_overspeed(self):
        original,extended=motor(DCMotor),motor()
        extended.drive_strength.fill_(1)
        extended.positions_delay_buffer.set_time_lag(0)
        dq=torch.tensor([[-90.,90.],[-30.1,30.1],[0.,0.],[10.,-10.]])
        for target in [-10.,.05,10.]:
            before=command(target)
            expected=original.compute(copy.deepcopy(before),torch.zeros(4,2),dq).joint_efforts
            actual=extended.compute(before,torch.zeros(4,2),dq).joint_efforts
            torch.testing.assert_close(actual,expected,atol=0,rtol=0)
            self.assertIsNotNone(before.joint_positions)

    def test_two_physics_steps_delay_and_reset_does_not_leak(self):
        m=motor()
        m.drive_strength.fill_(1)
        m.positions_delay_buffer.set_time_lag(2)
        results=[]
        for value in [0.,.1,.2,.3]:
            results.append(m.compute(command(value),torch.zeros(4,2),torch.zeros(4,2)).joint_efforts[0,0].item())
        self.assertEqual(results,[0.,0.,0.,2.5])
        m.cfg.strength_range=(1.,1.)
        m.cfg.min_delay=m.cfg.max_delay=2
        m.reset(torch.tensor([0]))
        out=m.compute(command(.4),torch.zeros(4,2),torch.zeros(4,2)).joint_efforts
        self.assertEqual(out[0,0].item(),10.)
        self.assertEqual(out[1,0].item(),5.)

    def test_strength_scales_applied_torque_and_respects_hard_cap(self):
        m=motor(max_delay=0)
        m.drive_strength.fill_(.9)
        out=m.compute(command(.2),torch.zeros(4,2),torch.zeros(4,2)).joint_efforts
        torch.testing.assert_close(out,torch.ones(4,2)*4.5)
        m.drive_strength.fill_(1.1)
        out=m.compute(command(10.),torch.zeros(4,2),torch.zeros(4,2)).joint_efforts
        torch.testing.assert_close(out,torch.ones(4,2)*23.7)


if __name__=='__main__':unittest.main()
