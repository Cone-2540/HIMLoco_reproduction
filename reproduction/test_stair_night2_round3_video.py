"""CPU-only coverage and first-episode material fixtures, never physical evidence."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("video", ROOT / "reproduction/run-stair-night2-round3-video-review.py")
video = importlib.util.module_from_spec(spec)
spec.loader.exec_module(video)
fixture_spec = importlib.util.spec_from_file_location("old_cpu_video_fixture", ROOT / "reproduction/test-stair-night2-video-review.py")
fixtures = importlib.util.module_from_spec(fixture_spec)
fixture_spec.loader.exec_module(fixtures)


class Round3VideoGuards(unittest.TestCase):
    def test_fourteen_reserved_jobs_and_explicit_missing_coverage(self):
        jobs = video.selected_jobs()
        self.assertEqual(len(jobs), 14)
        self.assertTrue(all(j["reset_seed"] == 1301 and j["num_envs"] == 32 and j["camera_environment_id"] == 0 for j in jobs))
        reserved = video.read_json(video.GEOMETRIES)
        self.assertTrue(all(j["geometry"] == reserved[j["final_case_index"]] for j in jobs))
        chosen = video.selected_jobs(["long12-desc-speed03"])
        self.assertEqual(sum(j["selected"] for j in chosen), 1)
        self.assertEqual(len(chosen), 14)
        with self.assertRaisesRegex(ValueError, "Unknown"):
            video.selected_jobs(["replace_failed_camera"])

    def test_coverage_includes_both_directions_and_speeds_on_core_dimensions(self):
        jobs = video.selected_jobs()
        for index in (2, 3, 4, 5):
            self.assertEqual({j["speed_m_s"] for j in jobs if j["final_case_index"] == index}, {.3, .5})
        self.assertEqual({j["final_case_index"] for j in jobs}, {0, 1, 2, 3, 4, 5, 8, 9, 12, 13})

    def test_light_training_never_mislabeled_as_scene_reward(self):
        for job in video.selected_jobs():
            command = video.wrapper_command(ROOT / "artifacts/go2-stairs-control660/model_660.pt", "contact_light", job,
                                            ROOT / "isaaclab/logs/fixture.json", "fixture", 900)
            self.assertEqual(command[command.index("--reward_profile") + 1], "faithful")
            self.assertEqual(command[command.index("--eval_seed") + 1], "1301")
            self.assertEqual(command.count("--eval_seed"), 1)
            self.assertEqual(command[command.index("--video_env_index") + 1], "0")
            self.assertIn("--video_policy_only", command)
            self.assertNotIn("--viz", command)

    def test_busy_refusal_uses_existing_readonly_guard(self):
        probe = subprocess.CompletedProcess([], 0, '[{"pid":123,"run_name":"active_training"}]', '')
        with mock.patch.object(video.subprocess, "run", return_value=probe):
            with self.assertRaisesRegex(ValueError, "active_training"):
                video.assert_idle()

    def test_full_freeze_validation_and_hash_not_flattened_identity(self):
        checkpoint = (ROOT / "artifacts/go2-stairs-night2-faithful-seed1213-760/model_760.pt").resolve()
        with self.assertRaises((ValueError, KeyError)):
            video.validate_selection(ROOT / "reproduction/stair-night2-selected-final-freeze.json", checkpoint, "faithful")

    def fixture(self, directory, failed=False):
        run = fixtures.VideoReviewTests().fixture(directory, failed)
        result = video.read_json(run / "result.json")
        result["policy"]["trials"][0]["seed"] = 1301
        video.write_json(run / "result.json", result)
        return run

    def test_clean_seed1301_all_frames_pipeline_with_unchanged_clipguards(self):
        with tempfile.TemporaryDirectory(prefix="round3-clean-CPU-fixture-") as temp:
            directory = Path(temp)
            run = self.fixture(directory)
            output = directory / "materials"
            output.mkdir()
            record = video.materialize(run, output)
            self.assertEqual(record["materials_status"], "complete_clean_first_episode_materials", record)
            self.assertEqual(record["preview"]["low_resolution_video_info"]["decoded_frame_count"], 6)
            self.assertTrue(record["preview"]["all_source_frames_retained"])
            self.assertFalse(record["continuous_video_reviewed"])
            self.assertEqual(record["selected_reset_seed"], 1301)

    def test_failed_camera_is_preserved_and_never_reselected(self):
        with tempfile.TemporaryDirectory(prefix="round3-failure-CPU-fixture-") as temp:
            directory = Path(temp)
            run = self.fixture(directory, True)
            output = directory / "materials"
            output.mkdir()
            record = video.materialize(run, output)
            self.assertEqual(record["materials_status"], "incomplete_prefailure_materials", record)
            self.assertFalse(record["selected_environment_completed"])
            self.assertEqual(record["selected_environment_id"], 0)
            self.assertEqual(record["preview"]["low_resolution_video_info"]["decoded_frame_count"], 4)
            self.assertTrue(Path(record["source_videos"][0]["path"]).exists())
            summary = video.read_json(output / "selected-prefailure-frame-telemetry-summary.json")
            self.assertFalse(summary["full_failed_episode_shown"])

    def test_old_reset_cannot_be_reused_for_new_video_materials(self):
        with tempfile.TemporaryDirectory(prefix="round3-oldseed-CPU-fixture-") as temp:
            directory = Path(temp)
            run = fixtures.VideoReviewTests().fixture(directory)
            output = directory / "materials"
            output.mkdir()
            with self.assertRaisesRegex(ValueError, "seed/environment"):
                video.materialize(run, output)

    def test_default_dry_cli_never_contacts_docker(self):
        import io
        import sys
        from contextlib import redirect_stdout
        with mock.patch.object(sys, "argv", [str(Path(video.__file__)), "--checkpoint",
                               "artifacts/go2-stairs-night2-faithful-seed1213-760/model_760.pt", "--profile", "faithful"]), \
             mock.patch.object(video, "assert_idle", side_effect=AssertionError("Docker forbidden in dry run")), \
             mock.patch.object(video.subprocess, "run", side_effect=AssertionError("No process work in dry run")), \
             mock.patch.object(video.subprocess, "check_output", return_value="0" * 40 + "\n"), \
             redirect_stdout(io.StringIO()) as stream:
            video.main()
        import json
        manifest = json.loads(stream.getvalue())
        self.assertEqual(manifest["status"], "dry_run_no_GPU_or_container_calls")
        self.assertEqual(manifest["declared_case_count"], 14)
        self.assertEqual(manifest["scene_construction_reward_profile"], "faithful")

    def encoding_fixture(self, directory):
        run = self.fixture(directory)
        wrapper = directory / "wrapper"
        wrapper.mkdir()
        sources = video.source_hashes()
        proof = video.validate_encoding_proof(sources)
        active = {"schema_version": 1, "method": "integer_index_rgb_v1", "patched": True}
        active.update(proof["writer_dependencies"])
        active.update(proof["environment"])
        for key, relative in (("overlay", "isaaclab/video_compat/sitecustomize.py"),
                              ("launcher", "isaaclab/video_compat/launch_exact_video.py")):
            active[key] = {"path": "/workspace/himloco/" + relative, "sha256": sources[relative]}
            active[key + "_sha256"] = sources[relative]
        emitted = {"schema_version": 1, "method": "integer_index_rgb_v1", "cache_frame_count": 6,
                   "frames_yielded": 6, "fps": 50, "overlay_sha256": sources["isaaclab/video_compat/sitecustomize.py"]}
        wrote = "[INFO]: [VideoRecorder] Wrote 6 frames to " + str(run / "videos/fixture.mp4")
        def save(a=active, e=emitted, w=wrote):
            (wrapper / "stdout.log").write_text("HIM_VIDEO_COMPAT_ACTIVE " + json.dumps(a) + "\n" +
                 "HIM_VIDEO_COMPAT_EMITTED " + json.dumps(e) + "\n" + w + "\n")
        save()
        return run, wrapper, sources, active, emitted, wrote, save

    def test_actual_markers_bind_frozen_sources_and_decode_every_source_frame(self):
        with tempfile.TemporaryDirectory(prefix="round3-exact-encoder-CPU-fixture-") as temp:
            run, wrapper, sources, *_ = self.encoding_fixture(Path(temp))
            record = video.verify_exact_encoding(run, wrapper, sources, video.validate_encoding_proof(sources))
            self.assertEqual(record["expected_source_frames"], 6)
            self.assertEqual(record["source_video_info"]["decoded_frame_count"], 6)
            self.assertEqual(record["cache_indices_inclusive"], [0, 5])

    def test_expected_total_alone_cannot_certify_legacy_float_writer(self):
        with tempfile.TemporaryDirectory(prefix="round3-no-encoder-CPU-fixture-") as temp:
            run, wrapper, sources, active, emitted, wrote, save = self.encoding_fixture(Path(temp))
            (wrapper / "stdout.log").write_text(wrote + "\n")
            with self.assertRaisesRegex(ValueError, "ACTIVE, EMITTED"):
                video.verify_exact_encoding(run, wrapper, sources, video.validate_encoding_proof(sources))
            active["patched"] = False
            save()
            with self.assertRaisesRegex(ValueError, "activation"):
                video.verify_exact_encoding(run, wrapper, sources, video.validate_encoding_proof(sources))

    def test_overlay_hash_and_yield_count_tampering_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="round3-tampered-encoder-CPU-fixture-") as temp:
            run, wrapper, sources, active, emitted, wrote, save = self.encoding_fixture(Path(temp))
            active["overlay_sha256"] = "0" * 64
            save()
            with self.assertRaisesRegex(ValueError, "frozen overlay"):
                video.verify_exact_encoding(run, wrapper, sources, video.validate_encoding_proof(sources))
            active["overlay_sha256"] = sources["isaaclab/video_compat/sitecustomize.py"]
            emitted["frames_yielded"] = 5
            save()
            with self.assertRaisesRegex(ValueError, "count differs"):
                video.verify_exact_encoding(run, wrapper, sources, video.validate_encoding_proof(sources))

    def test_decode_mismatch_wrong_path_and_duplicate_markers_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="round3-phase-encoder-CPU-fixture-") as temp:
            run, wrapper, sources, active, emitted, wrote, save = self.encoding_fixture(Path(temp))
            save(w=wrote.replace("fixture.mp4", "other.mp4"))
            with self.assertRaisesRegex(ValueError, "Wrote path"):
                video.verify_exact_encoding(run, wrapper, sources, video.validate_encoding_proof(sources))
            save()
            with (wrapper / "stdout.log").open("a") as stream:
                stream.write("HIM_VIDEO_COMPAT_EMITTED " + json.dumps(emitted) + "\n")
            with self.assertRaisesRegex(ValueError, "exactly one"):
                video.verify_exact_encoding(run, wrapper, sources, video.validate_encoding_proof(sources))
            config = video.read_json(run / "config.json")
            result = video.read_json(run / "result.json")
            result["policy"]["trials"][0]["executed_steps"] = 5
            video.write_json(run / "result.json", result)
            emitted["cache_frame_count"] = emitted["frames_yielded"] = 5
            save(w=wrote.replace("Wrote 6", "Wrote 5"))
            with self.assertRaisesRegex(ValueError, "CPU decoded"):
                video.verify_exact_encoding(run, wrapper, sources, video.validate_encoding_proof(sources))

    def test_writer_dependency_and_real_cpu_frame_id_proof_are_bound(self):
        with tempfile.TemporaryDirectory(prefix="round3-writer-proof-CPU-fixture-") as temp:
            directory = Path(temp)
            run, wrapper, sources, active, emitted, wrote, save = self.encoding_fixture(directory)
            active["ffmpeg"] = {**active["ffmpeg"], "sha256": "0" * 64}
            save()
            with self.assertRaisesRegex(ValueError, "CPU ffmpeg"):
                video.verify_exact_encoding(run, wrapper, sources, video.validate_encoding_proof(sources))
            fake = video.read_json(video.ENCODING_PROOF)
            fake["cases"][3]["decoded_frame_ids"][243] = 244
            path = directory / "tampered-encoding-proof.json"
            video.write_json(path, fake)
            modified_sources = {**sources, "reproduction/stair-night2-exact-video-cache-cpu.json": video.digest(path)}
            with mock.patch.object(video, "ENCODING_PROOF", path):
                with self.assertRaisesRegex(ValueError, "lost, duplicated or reordered"):
                    video.validate_encoding_proof(modified_sources)


if __name__ == "__main__":
    unittest.main()
