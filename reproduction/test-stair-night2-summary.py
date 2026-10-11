"""CPU tests for decision boundaries and missing/inconsistent source evidence."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("night2_summary", HERE / "summarize-stair-night2.py")
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)
PLAN = json.loads((HERE / "stair-night2-evaluation-plan.json").read_text())
GEOMETRIES = json.loads((HERE / "stair-night2-development-geometries.json").read_text())


def trial_fixture(seed=11):
    cases = []
    for index, geometry in enumerate(GEOMETRIES):
        cases.append({"case_index": index, "geometry": copy.deepcopy(geometry), "num_envs": 32,
            "completions": 32, "completion_fraction": 1.0, "falls": 0, "stalls": 0,
            "lateral_escapes": 0, "base_contact_envs": 0, "current_sample_base_contact_envs": 0,
            "metrics": {"roll_rms_rad": 0.10, "roll_peak_rad": 0.25, "longest_flight_pause_s": 0.20}})
    n = 32 * len(GEOMETRIES)
    return {"seed": seed, "num_envs": n, "cases": cases, "completions": n, "falls": 0,
        "stalls": 0, "lateral_escapes": 0, "base_contact_envs": 0,
        "current_sample_base_contact_envs": 0, "nonfinite_envs": 0, "invalid_physics_envs": 0,
        "invalid_start_envs": 0, "failure_reason": None,
        "initial_reset_distribution": {"yaw_std_rad": 0.1},
        "per_env": {"completed": [True] * n, "fall": [False] * n,
                    "stall": [False] * n, "lateral_escape": [False] * n}}


class GateTests(unittest.TestCase):
    def setUp(self):
        self.trial = trial_fixture()
        self.case = self.trial["cases"][0]

    def gate(self, core=True):
        return summary.case_gate(self.case, self.trial, core, PLAN)

    def test_31_completions_pass_30_fail_despite_old_boolean(self):
        self.case.update(completions=31, completion_fraction=31 / 32, passed=True)
        self.assertTrue(self.gate()["numeric_screens_passed"])
        self.case.update(completions=30, completion_fraction=30 / 32, passed=True)
        self.assertFalse(self.gate()["traversal_gate_passed"])

    def test_core_zero_fall_is_stricter_than_moderate(self):
        self.case["falls"] = 1
        self.assertIn("core_fall", self.gate()["traversal_failed_terms"])
        self.assertTrue(self.gate(core=False)["traversal_gate_passed"])
        self.case["falls"] = 2
        self.assertFalse(self.gate(core=False)["traversal_gate_passed"])

    def test_either_base_contact_detector_fails(self):
        for field in ("base_contact_envs", "current_sample_base_contact_envs"):
            case = copy.deepcopy(self.case)
            case[field] = 1
            self.assertFalse(summary.case_gate(case, self.trial, True, PLAN)["traversal_gate_passed"])

    def test_motion_boundary_inclusive_and_missing_never_pass(self):
        self.case["metrics"].update(roll_rms_rad=0.15, roll_peak_rad=0.35, longest_flight_pause_s=1.0)
        self.assertTrue(self.gate()["motion_screen_passed"])
        for field in ("roll_rms_rad", "roll_peak_rad", "longest_flight_pause_s"):
            case = copy.deepcopy(self.case)
            case["metrics"].pop(field)
            self.assertFalse(summary.case_gate(case, self.trial, True, PLAN)["motion_screen_passed"])
        self.case["metrics"]["roll_peak_rad"] = 0.350001
        self.assertFalse(self.gate()["motion_screen_passed"])

    def test_trial_anomaly_absence_and_nonfinite_motion_fail(self):
        self.trial.pop("invalid_physics_envs")
        self.assertFalse(self.gate()["traversal_gate_passed"])
        self.case["metrics"]["roll_rms_rad"] = float("nan")
        self.assertFalse(self.gate()["motion_screen_passed"])

    def test_counts_cannot_be_fraction_boolean_or_disagree(self):
        for invalid in (True, 31.0, -1, 33, None):
            self.case["completions"] = invalid
            self.assertFalse(self.gate()["traversal_gate_passed"])
        self.case.update(completions=31, completion_fraction=1.0)
        self.assertIn("reported_completion_fraction_disagrees", self.gate()["traversal_failed_terms"])


class MatrixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="himloco-night2-cpu-")
        self.directory = Path(self.temp.name)
        self.checkpoint = self.directory / "fixture-model.pt"
        self.checkpoint.write_bytes(b"identity-only-cpu-test-no-model-execution")
        self.paths = []

    def tearDown(self):
        self.temp.cleanup()

    def write_source(self, speed=0.3, heading=True, seeds=(11,), change=None):
        directory = self.directory / str(len(self.paths))
        directory.mkdir()
        cfg = {"mode": "evaluate", "terrain": "stairs", "num_envs": 576, "seed": 1,
               "evaluation_trace_stride_policy_steps": 1, "evaluation_seconds": 40,
               "physics_dt": 0.005, "policy_decimation": 4, "domain_randomization": None,
               "friction_override": None, "evaluation_dynamics_randomized": False,
               "checkpoint": str(self.checkpoint), "source_commit": "same-frozen-fixture-source",
               "source_tracked_files_dirty": False, "reward_weights": {"fixture": 1.0},
               "stair_reward": {"profile": "fixture"}}
        document = {"passed": True, "policy": {"geometry": GEOMETRIES,
               "command_forward_speed_m_s": speed, "heading_control": {"enabled": heading},
               "randomized_reset": True, "dynamics_randomized": False,
               "trials": [trial_fixture(seed) for seed in seeds]}}
        if change:
            change(document, cfg)
        path = directory / "result.json"
        path.write_text(json.dumps(document))
        (directory / "config.json").write_text(json.dumps(cfg))
        self.paths.append(path)
        return path

    def test_single_observed_pass_does_not_mean_complete(self):
        self.write_source()
        report = summary.summarize(self.paths, PLAN, "development", GEOMETRIES)
        self.assertFalse(report["complete_declared_numeric_protocol"])
        self.assertEqual(report["controllers"][0]["numeric_verdict"], "INCOMPLETE")
        self.assertTrue(report["controllers"][0]["groups"]["core"]["all_observed_numeric_acceptance_passed"])
        self.assertFalse(report["smoothness_verified"])

    def test_full_matrix_and_separate_controller_verdict(self):
        for speed in (0.3, 0.5):
            for heading in (True, False):
                self.write_source(speed, heading, seeds=(11, 29, 47))
        report = summary.summarize(self.paths, PLAN, "development", GEOMETRIES)
        self.assertTrue(report["complete_declared_numeric_protocol"])
        self.assertEqual([x["numeric_verdict"] for x in report["controllers"]], ["PASS", "PASS"])
        self.assertFalse(report["smoothness_verified"])

    def test_geometry_seed_and_count_errors_are_visible(self):
        def change(document, cfg):
            trial = document["policy"]["trials"][0]
            trial["seed"] = 101
            trial["cases"][0]["geometry"]["num_steps"] = 6
            trial["falls"] = 1
        self.write_source(change=change)
        report = summary.summarize(self.paths, PLAN, "development", GEOMETRIES)
        self.assertEqual(report["controllers"][0]["numeric_verdict"], "NOT_ASSESSED")
        errors = report["cases"][0]["source_protocol_errors"]
        self.assertIn("undeclared_reset_seeds", errors)
        self.assertIn("case_geometry_differs", errors)
        self.assertIn("case_totals_disagree_with_trial:falls", errors)

    def test_duplicate_matrix_cannot_pass(self):
        self.write_source()
        self.write_source()
        report = summary.summarize(self.paths, PLAN, "development", GEOMETRIES)
        self.assertTrue(report["duplicate_case_seed_speed_controller_rows"])
        self.assertFalse(report["complete_declared_numeric_protocol"])

    def test_source_commits_cannot_be_pooled(self):
        self.write_source()
        self.write_source(change=lambda document, cfg: cfg.update(source_commit="other-source"))
        with self.assertRaisesRegex(ValueError, "source commits"):
            summary.summarize(self.paths, PLAN, "development", GEOMETRIES)

    def test_documentary_commits_need_runtime_equality_and_clean_flags(self):
        self.write_source()
        self.write_source(change=lambda document, cfg: cfg.update(source_commit="other-source"))
        with mock.patch.object(summary, "runtime_signature", return_value="identical-recorded-runtime"):
            report = summary.summarize(self.paths, PLAN, "development", GEOMETRIES)
            self.assertTrue(report["duplicate_case_seed_speed_controller_rows"])
            path = self.paths[-1].parent / "config.json"
            cfg = json.loads(path.read_text())
            cfg["source_tracked_files_dirty"] = True
            path.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError, "clean source flags"):
                summary.summarize(self.paths, PLAN, "development", GEOMETRIES)

    def test_empty_case_list_is_not_assessed(self):
        def change(document, cfg):
            document["policy"]["trials"][0]["cases"] = []
        self.write_source(change=change)
        report = summary.summarize(self.paths, PLAN, "development", GEOMETRIES)
        self.assertEqual(report["controllers"][0]["numeric_verdict"], "NOT_ASSESSED")
        self.assertTrue(all(row["numeric_assessment_status"] == "NOT_ASSESSED" for row in report["cases"]))

    def test_missing_case_count_and_metric_are_not_assessed(self):
        def change(document, cfg):
            document["policy"]["trials"][0]["cases"][0].pop("falls")
            document["policy"]["trials"][0]["cases"][1]["metrics"].pop("roll_rms_rad")
        self.write_source(change=change)
        report = summary.summarize(self.paths, PLAN, "development", GEOMETRIES)
        self.assertEqual(report["controllers"][0]["numeric_verdict"], "NOT_ASSESSED")
        self.assertEqual(report["cases"][0]["numeric_assessment_status"], "NOT_ASSESSED")
        self.assertEqual(report["cases"][1]["numeric_assessment_status"], "NOT_ASSESSED")


if __name__ == "__main__":
    unittest.main()
