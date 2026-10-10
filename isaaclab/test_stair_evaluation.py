"""Regression tests for full traversal, pre-reset telemetry and motion reporting."""

import unittest
from types import SimpleNamespace as NS

import torch

from stair_evaluation import (StairStateCapture, assess_final, completion_mask,
                              configure_stair_evaluation, evaluate_stair_suite, evaluate_stairs)


GEOMETRY = {"direction": "asc", "num_steps": 6, "step_height": 0.05, "step_depth": 0.25,
            "width": 1.2, "start_x": 0., "first_riser_x": 1., "last_riser_x": 2.25,
            "goal_platform_start_x": 2.5, "goal_x": 3.15, "goal_platform_z": 0.3,
            "goal_dwell_s": 0.5}


def proxy(tensor):
    return NS(torch=tensor)


class Manager:
    def compute(self):
        return torch.zeros(32, dtype=torch.bool)


class FakeWrapped:
    def __init__(self, behavior="walk", geometry=GEOMETRY):
        self.behavior, self.geometry = behavior, geometry
        self.num_envs, self.num_actions, self.device = 32, 12, "cpu"
        n = self.num_envs
        self.names = ["base", "FL_foot", "FR_foot", "RL_foot", "RR_foot", "FL_calf"]
        data = NS(root_pos_w=proxy(torch.zeros(n, 3)), root_quat_w=proxy(torch.tensor([[0., 0., 0., 1.]]).repeat(n, 1)),
                  root_lin_vel_w=proxy(torch.zeros(n, 3)), root_lin_vel_b=proxy(torch.zeros(n, 3)),
                  root_ang_vel_b=proxy(torch.zeros(n, 3)), projected_gravity_b=proxy(torch.tensor([[0., 0., -1.]]).repeat(n, 1)),
                  body_link_pos_w=proxy(torch.zeros(n, 6, 3)), body_link_lin_vel_w=proxy(torch.zeros(n, 6, 3)),
                  joint_effort_limits=proxy(torch.full((n, 12), 20.)))
        self.robot = NS(data=data, body_names=self.names,
                        actuators=NS(applied_effort=proxy(torch.ones(n, 12)), computed_effort=proxy(torch.ones(n, 12))))
        sensor_data = NS(net_normal_forces_w=proxy(torch.zeros(n, 6, 3)),
                         net_normal_forces_w_history=proxy(torch.zeros(n, 3, 6, 3)))
        self.sensor = NS(data=sensor_data, body_names=self.names)
        self.term = NS(cfg=NS(ranges=NS()), is_standing_env=torch.zeros(n, dtype=torch.bool),
                       is_heading_env=torch.zeros(n, dtype=torch.bool), vel_command_b=torch.zeros(n, 3))
        scene = {"robot": self.robot}
        class Scene(dict):
            pass
        scene = Scene(scene)
        scene.env_origins = torch.tensor([[10., 20., 1.2]]).repeat(n, 1)
        scene.sensors = {"contact_forces": self.sensor}
        self.env = NS(scene=scene, device="cpu", num_envs=n, step_dt=0.5, termination_manager=Manager(),
                      command_manager=NS(get_term=lambda _: self.term), seed=lambda seed: None,
                      reset_terminated=torch.zeros(n, dtype=torch.bool))
        self.obs_buf = torch.zeros(n, 270)
        self.privileged_obs_buf = torch.zeros(n, 235)

    def place(self, x, final=False):
        data = self.robot.data
        z = self.geometry["goal_platform_z"] if final else 0.
        origin = self.env.scene.env_origins
        data.root_pos_w.torch[:] = origin + torch.tensor([x, 0., z + 0.3])
        for j, offset in enumerate((0.2, 0.2, -0.2, -0.2), start=1):
            data.body_link_pos_w.torch[:, j] = origin + torch.tensor([x + offset, (-1 if j % 2 else 1) * 0.15, z])
        self.sensor.data.net_normal_forces_w.torch[:, 1:5, 2] = 10.
        self.sensor.data.net_normal_forces_w_history.torch[:, :, 1:5, 2] = 10.

    def reset(self):
        self.number = 0
        self.obs_buf.zero_()
        self.privileged_obs_buf.zero_()
        self.robot.data.projected_gravity_b.torch[:, 2] = -1.
        self.sensor.data.net_normal_forces_w_history.torch[:, :, 0, :] = 0
        self.place(0.)

    def get_observations(self):
        return self.obs_buf

    def step(self, actions):
        self.number += 1
        moving = bool(actions.abs().sum() > 0)
        if self.behavior == "walk" and moving:
            x = min(self.number * 0.4, 3.6)
            self.place(x, final=x >= 3.1)
        elif self.behavior == "fall":
            self.place(1.1)
            self.sensor.data.net_normal_forces_w_history.torch[:, :, 0, 2] = 5.
        else:
            self.place(0.)
        self.env.reset_terminated[:] = self.behavior == "fall"
        timeout = torch.zeros(32, dtype=torch.bool)
        if self.behavior == "timeout_reset_goal":
            timeout[:] = True
        self.env.termination_manager.compute()
        done = self.env.reset_terminated | timeout
        if bool(done.any()):
            # Deliberately make autoreset look like a perfect final pose.
            self.place(3.6, final=True)
        self.obs_buf = torch.cat((self.obs_buf[:, :45], self.obs_buf[:, :-45]), dim=-1)
        return self.obs_buf, self.privileged_obs_buf, torch.ones(32), done, {
            "terminated": self.env.reset_terminated, "time_outs": timeout}, done.nonzero().flatten(), torch.zeros(int(done.sum()), 235)


def policy(obs):
    return torch.ones(obs.shape[0], 12)


class StairEvaluationTest(unittest.TestCase):
    def test_success_requires_complete_flight_and_zero_action_does_not_pass(self):
        result = evaluate_stair_suite(FakeWrapped(), policy, GEOMETRY, seconds=8., seeds=(1, 2), record_envs=0)
        self.assertTrue(result["passed"])
        self.assertEqual(result["policy"]["trials"][0]["completions"], 32)
        self.assertEqual(result["zero_action"]["trials"][0]["completions"], 0)
        self.assertEqual(result["zero_action"]["trials"][0]["stalls"], 32)
        self.assertEqual(result["completion_improvement_fraction"], 1.)

    def test_fall_or_timeout_reset_cannot_forge_completion(self):
        for behavior in ("fall", "timeout_reset_goal"):
            result = evaluate_stairs(FakeWrapped(behavior), policy, GEOMETRY, seconds=8., record_envs=0)
            self.assertFalse(result["passed"])
            self.assertEqual(result["trials"][0]["completions"], 0)
            if behavior == "fall":
                self.assertEqual(result["trials"][0]["falls"], 32)
            else:
                self.assertEqual(result["trials"][0]["timeouts_before_completion"], 32)

    def test_descent_uses_relative_platform_height_and_nonzero_world_origin(self):
        geometry = {**GEOMETRY, "direction": "desc", "goal_platform_z": -0.3}
        result = evaluate_stairs(FakeWrapped(geometry=geometry), policy, geometry, seconds=8., record_envs=0)
        self.assertTrue(result["passed"])

    def test_airborne_foot_and_bypass_do_not_pass(self):
        wrapped = FakeWrapped()
        wrapped.reset()
        wrapped.place(3.6, final=True)
        capture = StairStateCapture(wrapped.env)
        state = capture.snapshot()
        state["foot_contacts"].zero_()
        self.assertFalse(bool(completion_mask(state, wrapped.env.scene.env_origins, GEOMETRY).any()))
        state = capture.snapshot()
        state["feet_pos_w"][:, 0, 1] += 1.0
        self.assertFalse(bool(completion_mask(state, wrapped.env.scene.env_origins, GEOMETRY).any()))

    def test_hook_restores_original_method_even_when_policy_raises(self):
        wrapped = FakeWrapped()
        original = wrapped.env.termination_manager.compute
        def bad_policy(obs):
            raise RuntimeError("intentional")
        with self.assertRaisesRegex(RuntimeError, "intentional"):
            evaluate_stairs(wrapped, bad_policy, GEOMETRY, seconds=8.)
        self.assertEqual(wrapped.env.termination_manager.compute, original)
        self.assertNotIn("compute", vars(wrapped.env.termination_manager))

    def test_metrics_detect_dynamic_torque_clipping(self):
        wrapped = FakeWrapped()
        wrapped.robot.actuators.computed_effort.torch[:] = 2
        result = evaluate_stairs(wrapped, policy, GEOMETRY, seconds=8., record_envs=0)
        metrics = result["trials"][0]["metrics"]
        self.assertEqual(metrics["torque_saturation_fraction"], 1.)
        self.assertEqual(metrics["applied_torque_rms_nm"], 1.)

    def test_randomized_configuration_only_changes_reset_ranges(self):
        cfg = NS(compute_final_obs=False, observations=NS(policy=NS(), critic=NS()), curriculum=NS(terrain_levels=object()),
                 terminations=NS(stair_goal_reached=object()), events=NS(push_robot=object(), add_base_mass=object(), base_com=object(),
                 reset_base=NS(params={}), reset_robot_joints=NS(params={}), base_external_force_torque=NS(params={})),
                 commands=NS(base_velocity=NS(ranges=NS())))
        configure_stair_evaluation(cfg, GEOMETRY, randomized=True)
        self.assertEqual(cfg.events.reset_base.params["pose_range"]["yaw"], (-0.08, 0.08))
        self.assertEqual(cfg.events.reset_robot_joints.params["position_range"], (0.95, 1.05))
        self.assertIsNone(cfg.terminations.stair_goal_reached)
        self.assertIsNone(cfg.curriculum.terrain_levels)

    def test_batch_keeps_failed_column_from_hiding_in_average(self):
        wrapped = FakeWrapped()
        wrapped.env.scene.terrain = NS(terrain_types=torch.tensor([0] * 16 + [1] * 16))
        too_high = {**GEOMETRY, "goal_platform_z": 1.0}
        result = evaluate_stairs(wrapped, policy, [GEOMETRY, too_high], seconds=8.,
                                thresholds={"minimum_num_envs": 16}, record_envs=0)
        self.assertFalse(result["passed"])
        cases = result["trials"][0]["cases"]
        self.assertTrue(cases[0]["passed"])
        self.assertFalse(cases[1]["passed"])
        self.assertEqual(cases[0]["completion_fraction"], 1.0)
        self.assertEqual(cases[1]["completion_fraction"], 0.0)

    def test_batch_trace_covers_each_geometry(self):
        wrapped = FakeWrapped()
        wrapped.env.scene.terrain = NS(terrain_types=torch.tensor([0] * 16 + [1] * 16))
        result = evaluate_stairs(wrapped, policy, [GEOMETRY, GEOMETRY], seconds=8.,
                                thresholds={"minimum_num_envs": 16}, record_envs=1)
        trace = result["trials"][0]["trace"]
        self.assertEqual(trace[0]["case_ids"], [0, 1])
        self.assertEqual(trace[0]["env_ids"], [0, 16])
        self.assertIn("actions", trace[0])
        self.assertIn("linear_jerk_rms_m_s3", result["trials"][0]["cases"][1]["metrics"])

    def test_nominal_duplicate_poses_are_not_independent_validation(self):
        result = evaluate_stairs(FakeWrapped(), policy, GEOMETRY, seconds=8.,
                                 seeds=(1, 2, 3), randomized=True, record_envs=0)
        self.assertTrue(result["passed"])
        self.assertFalse(result["independent_reset_validation_eligible"])
        self.assertEqual(result["trials"][0]["initial_reset_distribution"]["yaw_std_rad"], 0.0)

    def test_inactive_finished_environment_nonfinite_does_not_fail_active_trial(self):
        class DifferentTimes(FakeWrapped):
            def place(self, x, final=False):
                super().place(x, final)
                # First row finishes at step8, other rows only at step10.
                if 8 <= self.number < 10:
                    self.robot.data.root_pos_w.torch[1:, 0] = self.env.scene.env_origins[1:, 0] + 2.7
                    self.robot.data.body_link_pos_w.torch[1:, 1:5, 0] = self.env.scene.env_origins[1:, None, 0] + 2.7
                if self.number == 9:
                    self.robot.data.root_pos_w.torch[0, 0] = float("nan")
                    self.robot.data.body_link_pos_w.torch[0, :, 0] = float("nan")

        result = evaluate_stairs(DifferentTimes(), policy, GEOMETRY, seconds=8., record_envs=0)
        self.assertTrue(result["passed"])
        self.assertEqual(result["trials"][0]["nonfinite_envs"], 0)
        self.assertGreaterEqual(result["trials"][0]["executed_steps"], 10)

    def test_final_gate_does_not_change_existing_passed_and_flags_long_pause(self):
        report = {"passed": True, "thresholds": {"minimum_num_envs": 32}, "trials": [
            {"seed": 1, "failure_reason": None, "cases": [{"num_envs": 32,
             "completion_fraction": 0.92, "falls": 0, "stalls": 0, "lateral_escapes": 0,
             "base_contact_envs": 0, "metrics": {"longest_flight_pause_s": 1.3}}]}]}
        assessment = assess_final(report)
        self.assertFalse(assessment["traversal_passed"])
        self.assertTrue(assessment["motion_improvement_needed"])
        self.assertTrue(report["passed"])


if __name__ == "__main__":
    unittest.main()
