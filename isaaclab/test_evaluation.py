"""Metric regression checks without launching the simulator."""

import unittest
from types import SimpleNamespace as NS

import torch

from evaluation import configure_evaluation, evaluate


class FakeWrapped:
    def __init__(self, n=64, episode_steps=4, fall_at=None, terminal_vx=0.5):
        self.num_envs, self.num_actions, self.device = n, 12, "cpu"
        self.fall_at, self.terminal_vx, self.episode_steps = fall_at, terminal_vx, episode_steps
        self.term = NS(cfg=NS(ranges=NS()), vel_command_b=torch.zeros(n, 3),
                       is_standing_env=torch.zeros(n, dtype=torch.bool),
                       is_heading_env=torch.zeros(n, dtype=torch.bool))
        data = NS(root_pos_w=NS(torch=torch.tensor([[0., 0., 0.35]]).repeat(n, 1)),
                  root_lin_vel_b=NS(torch=torch.zeros(n, 3)), root_ang_vel_b=NS(torch=torch.zeros(n, 3)),
                  projected_gravity_b=NS(torch=torch.tensor([[0., 0., -1.]]).repeat(n, 1)),
                  joint_pos=NS(torch=torch.zeros(n, 12)), joint_vel=NS(torch=torch.zeros(n, 12)))
        self.env = NS(step_dt=5.0, scene={"robot": NS(data=data)},
                      command_manager=NS(get_term=lambda _: self.term),
                      reset_terminated=torch.zeros(n, dtype=torch.bool))
        self.obs_buf = torch.zeros(n, 270)
        self.privileged_obs_buf = torch.zeros(n, 48)

    def reset(self):
        self.step_number = 0
        self.obs_buf.zero_()
        self.privileged_obs_buf.zero_()

    def get_observations(self):
        return self.obs_buf

    def step(self, actions):
        self.step_number += 1
        # Match HIMVecEnv: a step replaces history with a newly allocated tensor.
        # During evaluation this becomes an inference tensor, and next-case reset
        # must also happen in inference mode to safely clear it in place.
        self.obs_buf = torch.cat((self.obs_buf[:, :45], self.obs_buf[:, :-45]), dim=-1)
        moving = bool(actions.abs().sum() > 0)
        critic = torch.zeros(self.num_envs, 48)
        critic[:, 8] = -1.0
        critic[:, 45] = (0.5 if moving else 0.0) * 2.0
        timeout = torch.full((self.num_envs,), self.step_number % self.episode_steps == 0)
        terminated = torch.zeros(self.num_envs, dtype=torch.bool)
        if self.fall_at == self.step_number:
            terminated[:self.num_envs // 2] = True
        done = timeout | terminated
        ids = done.nonzero().flatten()
        terminal = critic[ids].clone()
        terminal[:, 45] = self.terminal_vx * 2.0 if moving else 0.0
        critic[ids, 45] = 0.0  # Autoreset state must not enter the metric.
        self.env.reset_terminated = terminated
        return self.obs_buf, critic, torch.ones(self.num_envs), done, {"time_outs": timeout}, ids, terminal


def policy(obs):
    return torch.ones(obs.shape[0], 12)


class EvaluationTest(unittest.TestCase):
    def test_timeout_velocity_is_pre_reset_and_zero_actions_fail_tracking(self):
        result = evaluate(FakeWrapped(), policy, num_steps=4, warmup_steps=0)
        self.assertTrue(result["passed"])
        learned, control = result["cases"][0], result["zero_action_cases"][0]
        self.assertEqual(learned["xy_mae_m_s"], 0.0)
        self.assertEqual(learned["first_episode_timeouts"], 64)
        self.assertEqual(learned["first_episode_survival_fraction"], 1.0)
        self.assertEqual(control["xy_mae_m_s"], 0.5)
        self.assertFalse(control["passed"])

    def test_consecutive_evaluations_reset_inference_history_safely(self):
        wrapped = FakeWrapped()
        evaluate(wrapped, policy, num_steps=4, warmup_steps=0)
        result = evaluate(wrapped, policy, num_steps=4, warmup_steps=0)
        self.assertTrue(result["passed"])

    def test_posture_ignores_reset_height_and_uses_terminal_gravity(self):
        class ResetPostureWrapped(FakeWrapped):
            def step(self, actions):
                outputs = super().step(actions)
                ids, terminal = outputs[-2:]
                # State after autoreset has a different height and gravity.
                self.env.scene["robot"].data.root_pos_w.torch[ids, 2] = 0.9
                outputs[1][ids, 8] = -1.0
                terminal[:, 8] = 0.0
                return outputs

        result = evaluate(ResetPostureWrapped(), policy, num_steps=4,
                          warmup_steps=0, include_zero_action=False)
        case = result["cases"][0]
        self.assertAlmostEqual(case["mean_root_height_m"], 0.35, places=6)
        self.assertEqual(case["height_tracking_samples"], 64 * 3)
        self.assertEqual(case["nominal_height_fraction"], 1.0)
        self.assertEqual(case["upright_fraction"], 0.75)

    def test_early_falls_exclude_reset_episodes_from_tracking(self):
        result = evaluate(FakeWrapped(fall_at=2, terminal_vx=1.5), policy,
                          num_steps=4, warmup_steps=0, include_zero_action=False)
        case = result["cases"][0]
        self.assertFalse(result["passed"])
        self.assertEqual(case["first_episode_survival_fraction"], 0.5)
        self.assertEqual(case["tracking_samples"], 32 * 2 + 32 * 4)
        # Half fall at step 2 with error1; the other half timeout at step4 with error1.
        self.assertAlmostEqual(case["xy_mae_m_s"], 64 / 192)
        self.assertEqual(case["first_episode_falls"], 32)

    def test_fall_on_timeout_step_is_not_counted_as_survival(self):
        result = evaluate(FakeWrapped(fall_at=4), policy, num_steps=4,
                          warmup_steps=0, include_zero_action=False)
        case = result["cases"][0]
        self.assertEqual(case["first_episode_falls"], 32)
        self.assertEqual(case["first_episode_timeouts"], 64)
        self.assertEqual(case["first_episode_survival_fraction"], 0.5)

    def test_small_sample_and_standing_do_not_pass_locomotion(self):
        result = evaluate(FakeWrapped(n=2), policy, num_steps=4,
                          warmup_steps=0, include_zero_action=False)
        self.assertFalse(result["passed"])
        self.assertFalse(result["cases"][0]["sample_eligible"])
        standing = evaluate(FakeWrapped(), lambda obs: torch.zeros(obs.shape[0], 12),
                            num_steps=4, warmup_steps=0, commands=((0., 0., 0.),))
        self.assertFalse(standing["passed"])
        self.assertFalse(standing["moving_command_tested"])

    def test_non_finite_actions_fail_before_physics_step(self):
        wrapped = FakeWrapped()
        result = evaluate(wrapped, lambda obs: torch.full((64, 12), float("nan")),
                          num_steps=4, warmup_steps=0, include_zero_action=False)
        self.assertFalse(result["passed"])
        self.assertEqual(wrapped.step_number, 0)
        self.assertEqual(result["cases"][0]["failure_reasons"], ["non_finite_actions"])

    def test_config_removes_disturbance_and_sets_nominal_reset(self):
        cfg = NS(scene=NS(terrain=NS(terrain_type="plane")),
                 observations=NS(policy=NS(), critic=NS()),
                 events=NS(push_robot=object(), add_base_mass=object(), base_com=object(),
                           reset_base=NS(params={}), reset_robot_joints=NS(params={}),
                           base_external_force_torque=NS(params={})),
                 commands=NS(base_velocity=NS(ranges=NS())))
        configure_evaluation(cfg)
        self.assertIsNone(cfg.events.push_robot)
        self.assertIsNone(cfg.events.add_base_mass)
        self.assertEqual(cfg.events.reset_robot_joints.params["position_range"], (1., 1.))
        self.assertEqual(cfg.commands.base_velocity.ranges.lin_vel_x, (0.5, 0.5))
        self.assertFalse(cfg.commands.base_velocity.heading_command)
        self.assertFalse(cfg.observations.policy.enable_corruption)
        self.assertEqual(cfg.events.reset_base.params["velocity_range"]["yaw"], (0., 0.))


if __name__ == "__main__":
    unittest.main()
