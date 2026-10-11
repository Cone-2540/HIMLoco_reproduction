#!/usr/bin/env python3
"""CPU-only video-runner fixtures; synthetic footage is not locomotion evidence."""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("night2_video_runner", ROOT / "reproduction/run-stair-night2-video-review.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class VideoReviewTests(unittest.TestCase):
    def test_predeclared_cases_and_subsets_preserve_missing_coverage(self):
        jobs = runner.selected_jobs()
        self.assertEqual(len(jobs), 14)
        self.assertEqual(len({item["label"] for item in jobs}), 14)
        self.assertTrue(all(item["camera_environment_id"] == 0 and item["reset_seed"] == 907
                            and item["num_envs"] == 32 for item in jobs))
        selected = runner.selected_jobs(["long12-desc-speed03"])
        self.assertEqual([item["label"] for item in selected if item["selected"]], ["long12-desc-speed03"])
        self.assertEqual(len([item for item in selected if not item["selected"]]), 13)
        with self.assertRaisesRegex(ValueError, "Unknown"):
            runner.selected_jobs(["pretty-env"])

    def test_video_commands_keep_one_seed_and_no_disabled_visualizer(self):
        for job in runner.selected_jobs():
            command = runner.wrapper_command(ROOT / "artifacts/go2-stairs-control660/model_660.pt",
                                             "contact", job, ROOT / "isaaclab/logs/fixture.json", "fixture", 900)
            self.assertIn("--video_policy_only", command)
            self.assertNotIn("--viz", command)
            self.assertEqual(command.count("--eval_seed"), 1)
            self.assertEqual(command[command.index("--video_env_index") + 1], "0")
            self.assertEqual(command[command.index("--num_envs") + 1], "32")

    def test_busy_guard_rejects_a_specific_live_job_without_gpu(self):
        completed = subprocess.CompletedProcess([], 0, '[{"pid":123,"run_name":"night2-live-training"}]', '')
        with mock.patch.object(runner.subprocess, "run", return_value=completed) as call:
            with self.assertRaisesRegex(ValueError, "night2-live-training"):
                runner.assert_idle()
            self.assertIn("CUDA_VISIBLE_DEVICES=", call.call_args.args[0])
        with mock.patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, '[]', '')):
            self.assertEqual(runner.assert_idle()["status"], "no_live_run_py_process")

    def test_selection_hash_and_profile_guard(self):
        with tempfile.TemporaryDirectory(prefix="night2-selection-cpu-") as temp:
            directory = Path(temp)
            checkpoint = directory / "checkpoint.pt"
            checkpoint.write_bytes(b"CPU fixture; not a trained checkpoint")
            selection = directory / "selection.json"
            runner.write_json(selection, {"checkpoint": str(checkpoint), "checkpoint_sha256": runner.digest(checkpoint),
                                          "reward_profile": "contact"})
            accepted = runner.validate_selection(selection, checkpoint, "contact")
            self.assertEqual(accepted["sha256"], runner.digest(selection))
            with self.assertRaisesRegex(ValueError, "does not match"):
                runner.validate_selection(selection, checkpoint, "contact_vertical")
            checkpoint.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "does not match"):
                runner.validate_selection(selection, checkpoint, "contact")

    def fixture(self, directory, failed=False):
        helper_spec = importlib.util.spec_from_file_location("video_fixture_helpers", ROOT / "reproduction/clip-first-episode-video.py")
        helper = importlib.util.module_from_spec(helper_spec)
        helper_spec.loader.exec_module(helper)
        run = directory / "synthetic-run"
        videos = run / "videos"
        videos.mkdir(parents=True)
        video = videos / "fixture.mp4"
        command = [str(helper.find_ffmpeg()), "-hide_banner", "-loglevel", "error", "-nostdin",
                   "-f", "lavfi", "-i", "color=c=blue:s=1280x720:r=50", "-frames:v", "6", "-an",
                   "-c:v", "libx264", "-preset", "ultrafast", "-threads", "2", "-pix_fmt", "yuv420p", str(video)]
        subprocess.run(command, check=True, capture_output=True)
        config = {"mode": "evaluate", "terrain": "stairs", "video": True, "video_policy_only": True,
                  "video_environment_index": 0, "physics_dt": .005, "policy_decimation": 4,
                  "episode_length_s": 40, "video_fps": 50, "video_length": 2000,
                  "evaluation_trace_stride_policy_steps": 1, "checkpoint": "CPU_SYNTHETIC_NOT_A_MODEL",
                  "joint_names": ["fixture_joint_" + str(i) for i in range(12)],
                  "source_commit": "CPU_SYNTHETIC_NOT_A_SOURCE_VERSION", "source_tracked_files_dirty": False}
        trace = []
        for index in range(6):
            row = {"time_s": (index + 1) * .02, "env_ids": [0], "case_ids": [0], "active": [True],
                   "root_relative_xyz": [[(index + 1) * .01, 0., .3]], "root_linear_velocity_w": [[.5, 0., 0.]],
                   "yaw_roll_pitch": [[0., 0., 0.]], "command_vx_vy_yaw": [[.3, 0., 0.]],
                   "feet_relative_xyz": [[[.1, 0., 0.]] * 4], "foot_horizontal_speed_m_s": [[0.] * 4],
                   "contacts": [[True] * 4], "current_sample_contacts": [[True] * 4], "actions": [[0.] * 12],
                   "leg_current_normal_force_norm_n": [[0.] * 8], "leg_history_peak_normal_force_norm_n": [[0.] * 8],
                   "leg_current_normal_force_w_n": [[[0., 0., 0.]] * 8],
                   "leg_link_pos_w_m": [[[0., 0., 0.]] * 8], "leg_link_quat_w_xyzw": [[[0., 0., 0., 1.]] * 8],
                   "flight_paused": [False]}
            for key in ("action_delta_rms", "action_second_delta_rms", "base_force_n", "shank_force_n",
                        "current_sample_base_force_n", "current_sample_shank_force_n"):
                row[key] = [0.]
            trace.append(row)
        pe = {"completed": [not failed] + [True] * 31, "fall": [False] * 32, "stall": [failed] + [False] * 31,
              "lateral_escape": [False] * 32, "first_episode_measured_duration_s": [.12] * 32,
              "completion_time_s": [None if failed else .12] + [.12] * 31}
        trial = {"seed": 907, "num_envs": 32, "executed_steps": 6, "per_env": pe, "trace": trace,
                 "completions": 31 if failed else 32, "falls": 0, "stalls": int(failed), "lateral_escapes": 0,
                 "base_contact_envs": 0, "current_sample_base_contact_envs": 0, "failure_reason": None}
        result = {"zero_action": None, "additional_candidates": None, "policy": {"trials": [trial],
                  "foot_body_names": [name + "_foot" for name in ("FL", "FR", "RL", "RR")],
                  "leg_body_names": [name + "_" + part for part in ("thigh", "calf") for name in ("FL", "FR", "RL", "RR")]}}
        runner.write_json(run / "config.json", config)
        runner.write_json(run / "result.json", result)
        return run

    def test_clean_complete_frame_telemetry_pipeline_on_synthetic_cpu_video(self):
        with tempfile.TemporaryDirectory(prefix="night2-clean-cpu-video-") as temp:
            directory = Path(temp)
            run = self.fixture(directory)
            material = directory / "materials"
            material.mkdir()
            record = runner.materialize(run, material)
            self.assertEqual(record["materials_status"], "complete_clean_first_episode_materials", record)
            self.assertEqual(record["preview"]["low_resolution_video_info"]["decoded_frame_count"], 6)
            self.assertFalse(record["continuous_video_reviewed"])
            self.assertTrue(record["preview"]["all_source_frames_retained"])
            summary = runner.read_json(material / "selected-frame-telemetry-summary.json")
            self.assertEqual(summary["csv_rows"], 6)
            self.assertEqual(summary["environment_id"], 0)

    def test_failed_env_is_kept_without_reselection_and_terminal_frames_excluded(self):
        with tempfile.TemporaryDirectory(prefix="night2-failure-cpu-video-") as temp:
            directory = Path(temp)
            run = self.fixture(directory, failed=True)
            material = directory / "materials"
            material.mkdir()
            record = runner.materialize(run, material)
            self.assertEqual(record["materials_status"], "incomplete_prefailure_materials", record)
            self.assertFalse(record["selected_environment_completed"])
            self.assertEqual(record["selected_environment_id"], 0)
            self.assertEqual(record["preview"]["low_resolution_video_info"]["decoded_frame_count"], 4)
            self.assertTrue(Path(record["source_videos"][0]["path"]).exists())
            summary = runner.read_json(material / "selected-prefailure-frame-telemetry-summary.json")
            self.assertFalse(summary["full_failed_episode_shown"])
            self.assertEqual(summary["csv_rows"], 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
