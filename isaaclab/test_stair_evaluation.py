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
        self.sensor = NS(data=sensor_data, body_names=self.names,
                         cfg=NS(update_period=0.125, history_length=3))
        self.term = NS(cfg=NS(ranges=NS()), is_standing_env=torch.zeros(n, dtype=torch.bool),
                       is_heading_env=torch.zeros(n, dtype=torch.bool), vel_command_b=torch.zeros(n, 3))
        scene = {"robot": self.robot}
        class Scene(dict):
            pass
        scene = Scene(scene)
        scene.env_origins = torch.tensor([[10., 20., 1.2]]).repeat(n, 1)
        scene.sensors = {"contact_forces": self.sensor}
        scene.cfg = NS(lazy_sensor_update=False)
        self.env = NS(scene=scene, device="cpu", num_envs=n, step_dt=0.5, physics_dt=0.125,
                      _physics_handles_decimation=False, termination_manager=Manager(),
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
    def test_report_separates_reset_displacement_from_course_position(self):
        class OffsetWrapped(FakeWrapped):
            def reset(self):
                super().reset()
                self.place(0.15)

        wrapped = OffsetWrapped()
        result = evaluate_stairs(wrapped, lambda obs: torch.ones(32, 12), GEOMETRY, seconds=10., seeds=(7,))
        trial = result["trials"][0]
        per_env = trial["per_env"]
        self.assertAlmostEqual(per_env["initial_root_relative_xyz_m"][0][0], 0.15, places=5)
        initial_x = torch.tensor(per_env["initial_root_relative_xyz_m"])[:, 0]
        course_max_x = torch.tensor(per_env["maximum_root_relative_x_m"])
        displacement = torch.tensor(per_env["max_progress_m"])
        torch.testing.assert_close(course_max_x, initial_x + displacement)
        final_x = torch.tensor(per_env["last_measured_root_relative_xyz_m"])[:, 0]
        torch.testing.assert_close(final_x, course_max_x)
        self.assertEqual(torch.tensor(per_env["last_measured_feet_relative_xyz_m"]).shape, (32, 4, 3))
        self.assertTrue(all(trial["per_env"]["completed"]))
        self.assertGreater(per_env["first_episode_measured_duration_s"][0], 0.)

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

    def test_evaluation_configures_reset_ranges_and_eager_physics_sensor_refresh(self):
        cfg = NS(compute_final_obs=False, observations=NS(policy=NS(), critic=NS()), curriculum=NS(terrain_levels=object()),
                 sim=NS(dt=0.005), scene=NS(lazy_sensor_update=True, contact_forces=NS(update_period=0.02, history_length=3)),
                 terminations=NS(stair_goal_reached=object()), events=NS(push_robot=object(), add_base_mass=object(), base_com=object(),
                 reset_base=NS(params={}), reset_robot_joints=NS(params={}), base_external_force_torque=NS(params={})),
                 commands=NS(base_velocity=NS(ranges=NS())))
        configure_stair_evaluation(cfg, GEOMETRY, randomized=True)
        self.assertEqual(cfg.events.reset_base.params["pose_range"]["yaw"], (-0.08, 0.08))
        self.assertEqual(cfg.events.reset_robot_joints.params["position_range"], (0.95, 1.05))
        self.assertIsNone(cfg.terminations.stair_goal_reached)
        self.assertIsNone(cfg.curriculum.terrain_levels)
        self.assertFalse(cfg.scene.lazy_sensor_update)
        self.assertEqual(cfg.scene.contact_forces.update_period, 0.005)
        self.assertEqual(cfg.scene.contact_forces.history_length, 3)

    def test_default_removes_gain_randomization_and_explicit_dynamics_keeps_events(self):
        def cfg_factory():
            return NS(observations=NS(policy=NS(), critic=NS()), curriculum=NS(), terminations=NS(),
                      sim=NS(dt=0.005), scene=NS(lazy_sensor_update=True, contact_forces=NS(update_period=0.02)),
                      events=NS(push_robot=object(), add_base_mass=object(), base_com=object(), him_actuator_gains=object(),
                                reset_base=NS(params={}), reset_robot_joints=NS(params={})),
                      commands=NS(base_velocity=NS(ranges=NS())))
        nominal = cfg_factory()
        configure_stair_evaluation(nominal, GEOMETRY)
        self.assertIsNone(nominal.events.him_actuator_gains)
        dynamics = cfg_factory()
        original_mass, original_gains = dynamics.events.add_base_mass, dynamics.events.him_actuator_gains
        configure_stair_evaluation(dynamics, GEOMETRY, dynamics_randomized=True)
        self.assertIs(dynamics.events.add_base_mass, original_mass)
        self.assertIs(dynamics.events.him_actuator_gains, original_gains)
        self.assertIsNone(dynamics.events.push_robot)

    def test_history_only_contacts_do_not_contaminate_current_sample_metrics_or_gate(self):
        class HistoryOnly(FakeWrapped):
            def place(self, x, final=False):
                super().place(x, final)
                self.sensor.data.net_normal_forces_w.torch[:, 1:6] = 0
                self.sensor.data.net_normal_forces_w_history.torch[:, 1:, 5, 0] = 5.
                self.robot.data.body_link_lin_vel_w.torch[:, 1:5, 0] = 0.2

        result = evaluate_stairs(HistoryOnly(), policy, GEOMETRY, seconds=8., record_envs=1)
        self.assertTrue(result["passed"])
        trial = result["trials"][0]
        metrics = trial["metrics"]
        self.assertEqual(metrics["shank_contact_step_fraction"], 1.)
        self.assertEqual(metrics["current_sample_shank_contact_step_fraction"], 0.)
        self.assertEqual(metrics["foot_slip_fraction"], 1.)
        self.assertIsNone(metrics["current_sample_foot_slip_fraction"])
        self.assertIsNone(metrics["current_sample_contact_foot_horizontal_speed_m_s"])
        self.assertEqual(trial["shank_contact_envs"], 32)
        self.assertEqual(trial["current_sample_shank_contact_envs"], 0)
        self.assertEqual(trial["contact_sample_counts"]["current_contact_foot_samples"], 0)
        self.assertGreater(trial["contact_sample_counts"]["history_contact_foot_samples"], 0)
        self.assertTrue(all(trial["trace"][0]["contacts"][0]))
        self.assertFalse(any(trial["trace"][0]["current_sample_contacts"][0]))

    def test_matching_history_and_current_contacts_have_matching_metrics_and_denominators(self):
        class CurrentContact(FakeWrapped):
            def place(self, x, final=False):
                super().place(x, final)
                self.sensor.data.net_normal_forces_w.torch[:, 5, 0] = 5.
                self.sensor.data.net_normal_forces_w_history.torch[:, :, 5, 0] = 5.
                self.robot.data.body_link_lin_vel_w.torch[:, 1:5, 0] = 0.2

        result = evaluate_stairs(CurrentContact(), policy, GEOMETRY, seconds=8., record_envs=0)
        trial = result["trials"][0]
        for scope in (trial, trial["cases"][0]):
            metrics = scope["metrics"]
            for name in ("base_contact_step_fraction", "shank_contact_step_fraction",
                         "contact_foot_horizontal_speed_m_s", "foot_slip_fraction"):
                self.assertEqual(metrics[name], metrics["current_sample_" + name])
            counts = scope["contact_sample_counts"]
            self.assertEqual(counts["current_contact_foot_samples"], counts["history_contact_foot_samples"])
            self.assertEqual(counts["current_contact_foot_samples"], 4 * counts["environment_samples"])
        self.assertEqual(trial["current_sample_shank_contact_envs"], 32)

    def test_current_forces_match_body_names_and_include_horizontal_riser_normals(self):
        wrapped = FakeWrapped()
        wrapped.reset()
        wrapped.sensor.body_names = ["FL_calf", "RR_foot", "base", "RL_foot", "FR_foot", "FL_foot"]
        current = wrapped.sensor.data.net_normal_forces_w.torch
        history = wrapped.sensor.data.net_normal_forces_w_history.torch
        current.zero_()
        history.zero_()
        current[:, 0, 1] = 3.
        current[:, 1, 0] = 2.
        current[:, 2, 0] = 4.
        current[:, 3, 2] = 1.  # Exact threshold does not count as contact.
        history[:, 0] = current
        history[:, 1, 0, 0] = 9.
        state = StairStateCapture(wrapped.env).snapshot()
        self.assertEqual(state["current_foot_contacts"][0].tolist(), [False, False, False, True])
        self.assertEqual(float(state["current_base_force_n"][0]), 4.)
        self.assertEqual(float(state["current_shank_force_n"][0]), 3.)
        self.assertEqual(float(state["shank_force_n"][0]), 9.)
        self.assertEqual(state["leg_current_normal_force_norm_n"][0].tolist(), [3.])
        self.assertEqual(state["leg_history_peak_normal_force_norm_n"][0].tolist(), [9.])

    def test_report_names_and_per_leg_trace_match_reordered_sensor_bodies(self):
        class PerLegWrapped(FakeWrapped):
            def __init__(self):
                super().__init__()
                # Both feet and legs deliberately use noncanonical robot order.
                self.robot.body_names = ["base", "RR_foot", "FL_foot", "RL_foot", "FR_foot",
                                         "FR_calf", "RL_thigh", "FL_calf", "RR_thigh",
                                         "FL_thigh", "RR_calf", "FR_thigh", "RL_calf", "FL_hip"]
                self.sensor.body_names = list(reversed(self.robot.body_names))
                count = len(self.robot.body_names)
                self.robot.data.body_link_pos_w = proxy(torch.zeros(32, count, 3))
                self.robot.data.body_link_lin_vel_w = proxy(torch.zeros(32, count, 3))
                self.sensor.data.net_normal_forces_w = proxy(torch.zeros(32, count, 3))
                self.sensor.data.net_normal_forces_w_history = proxy(torch.zeros(32, 3, count, 3))

            def place(self, x, final=False):
                super().place(x, final)
                force = self.sensor.data.net_normal_forces_w.torch
                history = self.sensor.data.net_normal_forces_w_history.torch
                force.zero_()
                history.zero_()
                for name in self.robot.body_names:
                    index = self.sensor.body_names.index(name)
                    if name.endswith("_foot"):
                        force[:, index, 2] = 10.
                        history[:, :, index, 2] = 10.
                legs = [name for name in self.robot.body_names if name.endswith(("_thigh", "_calf"))]
                for number, name in enumerate(legs, start=1):
                    index = self.sensor.body_names.index(name)
                    force[:, index, 0] = float(number)  # Includes horizontal normal forces.
                    history[:, 0, index] = force[:, index]
                    history[:, 1, index, 1] = 10. + number
                # Hip impacts must not enter these reward-body arrays.
                hip_index = self.sensor.body_names.index("FL_hip")
                force[:, hip_index, 2] = 100.
                history[:, :, hip_index, 2] = 100.

        wrapped = PerLegWrapped()
        result = evaluate_stairs(wrapped, policy, GEOMETRY, seconds=8., record_envs=4, record_stride=1)
        self.assertTrue(result["passed"])
        self.assertEqual(result["foot_body_names"], ["RR_foot", "FL_foot", "RL_foot", "FR_foot"])
        expected_names = ["FR_calf", "RL_thigh", "FL_calf", "RR_thigh",
                          "FL_thigh", "RR_calf", "FR_thigh", "RL_calf"]
        self.assertEqual(result["leg_body_names"], expected_names)
        trace = result["trials"][0]["trace"]
        self.assertGreater(len(trace), 0)
        for row in trace:
            self.assertLessEqual(len(row["env_ids"]), 4)
            self.assertEqual(row["leg_current_normal_force_norm_n"], [list(range(1, 9))] * 4)
            self.assertEqual(row["leg_history_peak_normal_force_norm_n"], [list(range(11, 19))] * 4)
            self.assertTrue(all(all(flags) for flags in row["current_sample_contacts"]))
        self.assertIn("sparse traces do not measure contact duration", result["leg_force_trace_scope"])

    def test_cadence_metadata_distinguishes_sample_age_from_count_window(self):
        result = evaluate_stairs(FakeWrapped(), policy, GEOMETRY, seconds=8., record_envs=0)
        sampling = result["contact_sampling"]
        self.assertEqual(sampling["semantics_version"], 2)
        self.assertEqual(sampling["physics_dt_s"], 0.125)
        self.assertEqual(sampling["policy_sample_dt_s"], 0.5)
        self.assertEqual(sampling["history_sampling"], "eager_physics_step_history")
        self.assertEqual(sampling["history_oldest_sample_age_s_after_warmup"], 0.25)
        self.assertEqual(sampling["history_nominal_count_window_s"], 0.375)
        self.assertFalse(sampling["history_covers_entire_policy_step"])

    def test_lazy_or_unknown_scene_cadence_is_not_reported_as_physics_step_history(self):
        for lazy, handles_decimation, expected in (
            (True, False, "lazy_read_driven_history"),
            (False, None, "unknown"),
            (False, True, "eager_policy_step_history"),
        ):
            with self.subTest(lazy=lazy, handles_decimation=handles_decimation):
                wrapped = FakeWrapped()
                wrapped.env.scene.cfg.lazy_sensor_update = lazy
                wrapped.env._physics_handles_decimation = handles_decimation
                sampling = evaluate_stairs(wrapped, policy, GEOMETRY, seconds=8., record_envs=0)["contact_sampling"]
                self.assertEqual(sampling["history_sampling"], expected)
                if lazy or handles_decimation is None:
                    self.assertIsNone(sampling["inferred_history_sample_dt_s"])
                    self.assertIsNone(sampling["history_oldest_sample_age_s_after_warmup"])

    def test_installed_contact_history_override_is_eager_even_with_lazy_scene(self):
        def history_update():
            pass
        # Stand in for the inherited method identity, without importing Kit.
        history_update.__module__ = "isaaclab.sensors.contact_sensor.base_contact_sensor"
        history_update.__qualname__ = "BaseContactSensor.update"
        wrapped = FakeWrapped()
        wrapped.env.scene.cfg.lazy_sensor_update = True
        wrapped.sensor.update = history_update
        sampling = evaluate_stairs(wrapped, policy, GEOMETRY, seconds=8., record_envs=0)["contact_sampling"]
        self.assertTrue(sampling["installed_sensor_updates_nonempty_history_with_lazy_scene"])
        self.assertEqual(sampling["history_sampling"], "eager_physics_step_history")
        self.assertEqual(sampling["inferred_history_sample_dt_s"], 0.125)

    def test_zero_configured_history_does_not_infer_eager_history_from_allocated_slot(self):
        def history_update():
            pass
        history_update.__module__ = "isaaclab.sensors.contact_sensor.base_contact_sensor"
        history_update.__qualname__ = "BaseContactSensor.update"
        wrapped = FakeWrapped()
        wrapped.env.scene.cfg.lazy_sensor_update = True
        wrapped.sensor.cfg.history_length = 0
        wrapped.sensor.update = history_update
        wrapped.sensor.data.net_normal_forces_w_history = proxy(torch.zeros(32, 1, 6, 3))
        sampling = evaluate_stairs(wrapped, policy, GEOMETRY, seconds=8., record_envs=0)["contact_sampling"]
        self.assertEqual(sampling["history_length"], 0)
        self.assertEqual(sampling["history_buffer_length"], 1)
        self.assertFalse(sampling["installed_sensor_updates_nonempty_history_with_lazy_scene"])
        self.assertEqual(sampling["history_sampling"], "current_force_fallback_without_history")
        self.assertIsNone(sampling["history_covers_entire_policy_step"])

    def test_eager_scene_with_slow_sensor_period_does_not_claim_physics_cadence(self):
        wrapped = FakeWrapped()
        wrapped.sensor.cfg.update_period = 0.5
        sampling = evaluate_stairs(wrapped, policy, GEOMETRY, seconds=8., record_envs=0)["contact_sampling"]
        self.assertEqual(sampling["history_sampling"], "unknown")
        self.assertIsNone(sampling["inferred_history_sample_dt_s"])
        self.assertIsNone(sampling["history_covers_entire_policy_step"])

    def test_backend_decimation_does_not_claim_all_substeps_were_sampled(self):
        wrapped = FakeWrapped()
        wrapped.env._physics_handles_decimation = True
        wrapped.sensor.cfg.history_length = 1
        sampling = evaluate_stairs(wrapped, policy, GEOMETRY, seconds=8., record_envs=0)["contact_sampling"]
        self.assertEqual(sampling["history_sampling"], "eager_policy_step_history")
        self.assertEqual(sampling["history_nominal_count_window_s"], 0.5)
        self.assertIsNone(sampling["history_covers_entire_policy_step"])

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

    def test_seed_scope_distinguishes_startup_parameters_from_reset_dynamics(self):
        nominal = evaluate_stairs(FakeWrapped(), policy, GEOMETRY, seconds=8., record_envs=0)
        self.assertIn("mass/COM/gain evaluation randomization is disabled", nominal["seed_scope"])
        randomized = evaluate_stairs(FakeWrapped(), policy, GEOMETRY, seconds=8., record_envs=0,
                                     dynamics_randomized=True)
        self.assertIn("startup terrain/material/dynamics", randomized["seed_scope"])
        self.assertIn("enabled reset-mode dynamics events", randomized["seed_scope"])
        self.assertIn("resample on resets", randomized["seed_scope"])
        self.assertNotIn("evaluation randomization is disabled", randomized["seed_scope"])

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
