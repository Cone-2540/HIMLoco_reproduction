"""CPU integration audit of the A/B/C configuration paths, without simulation.

The real entry point, CLI parser, task resolver, terrain/reward configuration,
MDP observation functions and ray pattern are exercised. CUDA reporting is
mocked solely to pass the entry point's GPU requirement. Simulation launch is
replaced, and gym.make raises before creating an environment. Temporary JSONs
are explicitly configuration-audit evidence, never physical evaluation data.
"""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

import torch

import run as entry
from commands import HIMVelocityCommand
from isaaclab.app import AppLauncher
from isaaclab.managers import ObservationTermCfg
from isaaclab.utils.string import string_to_callable


class StopBeforeEnvironment(RuntimeError):
    pass


def observation_terms(group):
    return {name: term for name, term in vars(group).items() if isinstance(term, ObservationTermCfg)}


class ReplayConfigurationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or torch.cuda.is_available():
            raise RuntimeError("Run this configuration audit with CUDA_VISIBLE_DEVICES empty")
        cls.audit_dir = Path(tempfile.mkdtemp(prefix="him-replay-cpu-configuration-"))
        cls.previous_cwd = Path.cwd()
        root = Path(__file__).resolve().parents[1]
        plan_path = root / "reproduction/stair-generalization-phase1-plan.json"
        launcher_path = root / "reproduction/run-stair-generalization-phase1.py"
        cls.plan = json.loads(plan_path.read_text())
        spec = importlib.util.spec_from_file_location("phase1_configuration_audit_jobs", launcher_path)
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        os.chdir(cls.audit_dir)
        cls.audit_scope = {
            "scope": "CPU configuration integration only; no environment, simulation, training or policy evaluation",
            "cuda_visible_devices": os.environ["CUDA_VISIBLE_DEVICES"],
            "actual_cuda_available_before_mock": False,
            "cuda_requirement_and_gpu_reporting": "mocked only inside entry-point configuration capture",
            "actual_task_config_resolution": True,
            "actual_observation_function_shape_fixture": "CPU tensors for a 12-joint Go2; no physical sensor data",
            "simulation_launch": "replaced by no-op context manager",
            "gym_make": "raises before environment construction",
            "test_command": ["/isaac-sim/python.sh", "-m", "unittest", "-v", "test_replay_configuration"],
            "required_environment": {"CUDA_VISIBLE_DEVICES": "", "OMP_NUM_THREADS": "2"},
            "plan_path": str(plan_path),
            "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            "job_generator_path": str(launcher_path),
            "job_generator_sha256": hashlib.sha256(launcher_path.read_bytes()).hexdigest(),
            "formal_job_selection": {"arms": ["A", "B", "C"], "continuation_seed": 1001},
            "unittest_exit_code": "recorded by the external process runner after this test process exits",
            "arms": {},
        }
        cls.captures = {}
        for arm in ("A", "B", "C"):
            selected = list(launcher.jobs(cls.plan, arm=arm, seed=1001))
            if len(selected) != 1:
                raise AssertionError("Expected one prescribed formal job per arm")
            name, arguments = selected[0]
            cls.captures[arm] = cls.capture_configuration(name, arguments)
            cls.audit_scope["arms"][arm] = cls.captures[arm]["guard_evidence"]
        (cls.audit_dir / "audit-scope.json").write_text(json.dumps(cls.audit_scope, indent=2))
        print(f"CPU configuration audit evidence: {cls.audit_dir}", flush=True)

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.previous_cwd)

    @classmethod
    def capture_configuration(cls, name, arguments):
        capture = {}
        audit_source_dir = cls.audit_dir / name
        audit_source_dir.mkdir()

        @contextlib.contextmanager
        def no_simulation(cfg, args):
            capture["args"] = args
            yield None

        def reject_environment(task, *, cfg):
            capture["task"], capture["cfg"] = task, cfg
            raise StopBeforeEnvironment("CPU audit stopped before creating a simulation environment")

        argv = ["run.py", *arguments]
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(sys, "argv", argv))
            stack.enter_context(mock.patch.object(entry, "__file__", str(audit_source_dir / "cpu-audit-source.py")))
            launch = stack.enter_context(mock.patch.object(entry, "launch_simulation", side_effect=no_simulation))
            make = stack.enter_context(mock.patch.object(entry.gym, "make", side_effect=reject_environment))
            app = stack.enter_context(mock.patch.object(AppLauncher, "__init__", side_effect=AssertionError("No AppLauncher")))
            runner = stack.enter_context(mock.patch.object(entry, "HIMOnPolicyRunner", side_effect=AssertionError("No runner")))
            stack.enter_context(mock.patch.object(torch.cuda, "is_available", return_value=True))
            stack.enter_context(mock.patch.object(torch.cuda, "manual_seed_all"))
            stack.enter_context(mock.patch.object(torch.cuda, "get_device_name", return_value="CPU_CONFIGURATION_AUDIT_MOCK"))
            stack.enter_context(mock.patch.object(torch.cuda, "get_device_capability", return_value=(0, 0)))
            lazy = stack.enter_context(mock.patch.object(torch.cuda, "_lazy_init", side_effect=AssertionError("No CUDA initialization")))
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    entry.main()
                except StopBeforeEnvironment:
                    pass
                else:
                    raise AssertionError("Entry point did not stop before environment construction")
            if launch.call_count != 1 or make.call_count != 1:
                raise AssertionError("Configuration must reach the guarded environment boundary exactly once")
            app.assert_not_called()
            runner.assert_not_called()
            lazy.assert_not_called()
            capture["guard_evidence"] = {
                "argv": argv,
                "job_name": name,
                "configuration_boundary_calls": {"mock_launch_simulation": launch.call_count,
                                                 "guarded_gym_make": make.call_count},
                "forbidden_guard_calls": {"AppLauncher_init": app.call_count,
                                          "HIMOnPolicyRunner_init": runner.call_count,
                                          "torch_cuda_lazy_init": lazy.call_count},
                "environment_created": False,
                "simulation_launched": False,
                "training_started": False,
            }
        configs = list(audit_source_dir.glob("logs/*/config.json"))
        if len(configs) != 1:
            raise AssertionError("Expected exactly one temporary configuration JSON")
        capture["metadata"] = json.loads(configs[0].read_text())
        capture["metadata_path"] = configs[0]
        return capture

    def test_abc_sampler_configuration_and_initial_turn_probability(self):
        for name, capture in self.captures.items():
            with self.subTest(name=name):
                cfg, metadata = capture["cfg"], capture["metadata"]
                command = cfg.commands.base_velocity
                self.assertEqual(capture["task"], "Isaac-Velocity-Rough-UnitreeGo2")
                self.assertEqual(metadata["gpu"], "CPU_CONFIGURATION_AUDIT_MOCK")
                self.assertEqual(metadata["training_turn_fraction"], 0.0)
                self.assertEqual(command.ranges.lin_vel_x, (.25, .65))
                self.assertEqual(command.ranges.lin_vel_y, (-.03, .03))
                self.assertEqual(command.ranges.ang_vel_z, (-.5, .5))
                self.assertEqual(command.ranges.heading, (0., 0.))
                self.assertTrue(command.heading_command)
                self.assertEqual(command.rel_heading_envs, 1.)
                self.assertEqual(command.rel_standing_envs, 0.)
                signed = name == "C"
                self.assertEqual(bool(getattr(command, "replay_enabled", False)), signed)
                if signed:
                    self.assertIs(command.class_type, HIMVelocityCommand)
                    self.assertEqual(command.turn_fraction, 0.)
                    self.assertEqual(command.replay_standing_fraction, .1)
                    self.assertEqual(command.replay_vx_range, (.2, .65))
                    self.assertEqual(command.replay_vy_range, (.15, .35))
                    self.assertEqual(command.replay_yaw_range, (.2, .6))
                    self.assertEqual(metadata["flat_replay"]["moving_categories"],
                                     ["forward", "backward", "left", "right", "positive_yaw", "negative_yaw"])
                else:
                    self.assertIsNot(command.class_type, HIMVelocityCommand)
                expected_fraction = 0.0 if name == "A" else .25
                self.assertEqual(metadata["flat_replay"]["requested_terrain_fraction"], expected_fraction)
                self.assertEqual(metadata["flat_replay"]["all_direction_commands"], signed)
                self.assertNotIn("flat_replay_runtime_readback", metadata)

    def test_abc_keep_identical_contact_rewards_robot_actions_and_training_parameters(self):
        baseline = self.captures["A"]
        rewards = {name: term.to_dict() for name, term in vars(baseline["cfg"].rewards).items()
                   if term is not None and hasattr(term, "weight")}
        self.assertEqual(rewards["leg_contacts"]["weight"], -.1)
        self.assertNotIn("feet_slide", rewards)
        self.assertNotIn("leg_contact_force_proxy", rewards)
        for name, capture in self.captures.items():
            with self.subTest(name=name):
                cfg, metadata = capture["cfg"], capture["metadata"]
                actual = {key: term.to_dict() for key, term in vars(cfg.rewards).items()
                          if term is not None and hasattr(term, "weight")}
                self.assertEqual(actual, rewards)
                self.assertEqual(cfg.scene.robot.to_dict(), baseline["cfg"].scene.robot.to_dict())
                self.assertEqual(cfg.actions.to_dict(), baseline["cfg"].actions.to_dict())
                self.assertEqual(metadata["train"], baseline["metadata"]["train"])
                self.assertEqual(metadata["stair_reward"], baseline["metadata"]["stair_reward"])
                self.assertEqual(metadata["domain_randomization"], baseline["metadata"]["domain_randomization"])

    def test_formal_hard_plan_terrain_exposure_and_resume_configuration(self):
        common = self.plan["common_training"]
        for arm, capture in self.captures.items():
            with self.subTest(arm=arm):
                cfg, args, metadata = capture["cfg"], capture["args"], capture["metadata"]
                self.assertEqual(args.stair_stage, "hard")
                self.assertEqual(args.domain_profile, "none")
                self.assertEqual(args.start_level, 4)
                self.assertEqual(args.seed, 1001)
                self.assertEqual(cfg.scene.num_envs, common["num_envs"])
                self.assertEqual(cfg.scene.terrain.max_init_terrain_level, common["stair_initial_maximum_level"])
                self.assertEqual(metadata["checkpoint"], common["checkpoint"])
                self.assertIsNone(args.warm_start)
                self.assertIsNone(args.reset_noise_std)
                self.assertEqual(args.max_iterations, common["saved_updates_per_arm"])
                self.assertEqual(args.steps_per_env, common["policy_steps_per_update"])
                self.assertEqual(args.save_interval, common["save_interval"])
                self.assertEqual(args.resume_learning_rate, common["him_learning_rate"])
                self.assertEqual(metadata["train"]["algorithm"]["learning_rate"], common["ppo_learning_rate"])
                self.assertEqual(metadata["train"]["algorithm"]["schedule"], common["lr_schedule"])
                self.assertIsNone(metadata["domain_randomization"])
                stair_manifest = metadata["stairs"]
                generator = cfg.scene.terrain.terrain_generator
                expected_columns = 48 if arm == "A" else self.plan["flat_terrain"]["hard_columns"]
                self.assertEqual(generator.num_cols, expected_columns)
                self.assertEqual(stair_manifest["num_cols"], expected_columns)
                self.assertEqual(generator.num_rows, 10)
                self.assertEqual(len(stair_manifest["variants"]), expected_columns)
                if arm == "A":
                    self.assertNotIn("flat_replay", stair_manifest)
                    self.assertIsNone(cfg.terminations.flat_replay_region_exit)
                else:
                    replay = stair_manifest["flat_replay"]
                    self.assertEqual(replay["flat_columns"], list(range(16)))
                    self.assertEqual(replay["stair_columns"], list(range(16, 64)))
                    self.assertEqual(replay["actual_column_fraction"], .25)
                    columns = torch.div(torch.arange(common["num_envs"]),
                                        common["num_envs"] / generator.num_cols, rounding_mode="floor").long()
                    is_flat = torch.isin(columns, torch.tensor(replay["flat_columns"]))
                    self.assertEqual(int(is_flat.sum()), 1024)
                    self.assertEqual(int((~is_flat).sum()), 3072)
                    self.assertTrue(cfg.terminations.flat_replay_region_exit.time_out)
                    self.assertEqual(replay["boundary_timeout"]["inward_margin_m"], 1.)

    def test_abc_policy_terrain_exclusion_and_actual_cpu_observation_shapes(self):
        class Scene(dict):
            pass

        def tensor_view(value):
            return NS(torch=value)

        for name, capture in self.captures.items():
            with self.subTest(name=name):
                cfg = capture["cfg"]
                policy = observation_terms(cfg.observations.policy)
                critic = observation_terms(cfg.observations.critic)
                self.assertEqual(list(policy), ["velocity_commands", "base_ang_vel", "projected_gravity",
                                               "joint_pos", "joint_vel", "actions"])
                self.assertEqual(list(critic), [*policy, "base_lin_vel", "height_scan"])
                self.assertFalse(capture["metadata"]["flat_replay"]["actor_terrain_inputs_added"])
                pattern = cfg.scene.height_scanner.pattern_cfg
                starts, directions = pattern.func(pattern, device="cpu")
                self.assertEqual(starts.shape, (187, 3))
                self.assertEqual(directions.shape, (187, 3))
                scene = Scene(robot=NS(data=NS(
                    root_ang_vel_b=tensor_view(torch.zeros(1, 3)),
                    root_lin_vel_b=tensor_view(torch.zeros(1, 3)),
                    projected_gravity_b=tensor_view(torch.zeros(1, 3)),
                    joint_pos=tensor_view(torch.zeros(1, 12)),
                    default_joint_pos=tensor_view(torch.zeros(1, 12)),
                    joint_vel=tensor_view(torch.zeros(1, 12)),
                    default_joint_vel=tensor_view(torch.zeros(1, 12)))))
                scene.sensors = {"height_scanner": NS(data=NS(
                    pos_w=tensor_view(torch.zeros(1, 3)), ray_hits_w=tensor_view(torch.zeros(1, 187, 3))))}
                env = NS(scene=scene, command_manager=NS(get_command=lambda _: torch.zeros(1, 3)),
                         action_manager=NS(action=torch.zeros(1, 12)))
                sizes = {}
                for group_name, terms in (("policy", policy), ("critic", critic)):
                    size = 0
                    for term in terms.values():
                        func = term.func if callable(term.func) else string_to_callable(str(term.func))
                        value = func(env, **term.params)
                        self.assertIsInstance(value, torch.Tensor)
                        self.assertEqual(value.device.type, "cpu")
                        size += value.shape[1]
                    sizes[group_name] = size
                self.assertEqual(sizes, {"policy": 45, "critic": 235})
                self.assertEqual(sizes["policy"] * 6, 270)

    def test_cli_rejects_replay_outside_curriculum_training_before_config_resolution(self):
        invalid = [
            ["evaluate", "--terrain", "stairs", "--flat_replay_fraction", ".25"],
            ["play", "--terrain", "stairs", "--flat_replay_fraction", ".25"],
            ["train", "--terrain", "flat", "--flat_replay_fraction", ".25"],
            ["train", "--terrain", "rough", "--flat_replay_fraction", ".25"],
            ["train", "--terrain", "stairs", "--stair_height", ".16", "--flat_replay_fraction", ".25"],
            ["train", "--terrain", "stairs", "--stair_batch", "/nonexistent.json", "--flat_replay_fraction", ".25"],
            ["train", "--terrain", "stairs", "--flat_replay_all_directions"],
            ["train", "--terrain", "stairs", "--flat_replay_fraction", ".5"],
        ]
        for args in invalid:
            with self.subTest(args=args), contextlib.ExitStack() as stack:
                stack.enter_context(mock.patch.object(sys, "argv", ["run.py", *args]))
                resolver = stack.enter_context(mock.patch.object(entry, "resolve_task_config",
                                                                 side_effect=AssertionError("Must reject first")))
                launch = stack.enter_context(mock.patch.object(entry, "launch_simulation",
                                                               side_effect=AssertionError("No simulation")))
                stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
                with self.assertRaises(SystemExit) as raised:
                    entry.main()
                self.assertEqual(raised.exception.code, 2)
                resolver.assert_not_called()
                launch.assert_not_called()

    def test_actual_parent_command_property_returns_torch_buffer(self):
        term = object.__new__(HIMVelocityCommand)
        term.vel_command_b = torch.arange(21).reshape(7, 3).float()
        self.assertIs(term.command, term.vel_command_b)
        for value in (term.command, NS(torch=term.command)):
            readback = getattr(value, "torch", value)
            self.assertIs(readback, term.vel_command_b)
            self.assertEqual(readback[:2].tolist(), [[0., 1., 2.], [3., 4., 5.]])


if __name__ == "__main__":
    unittest.main()
