#!/usr/bin/env python3
"""CPU-only final-runner contract checks; no Docker, GPU or real final results."""

import contextlib
import copy
from datetime import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "night2_final_runner", ROOT / "reproduction/run-stair-night2-final-comparison.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class FinalRunnerCPUContracts(unittest.TestCase):
    def setUp(self):
        # Read only already-collected development metadata, never final output.
        archive = ROOT / "reproduction/stair-night2-round1-development"
        self.selected = runner.read(archive / "faithful-training-identity.json")["identity"]
        self.summary = archive / "faithful-development-summary.json"
        self.baseline = {"label": "baseline-control660", "checkpoint": runner.BASELINE_PATH,
                         "checkpoint_sha256": runner.backend.EXPECTED_ORIGIN_SHA256,
                         "training_reward_profile": "contact"}
        self.source = {"git_commit": "a" * 40, "code_files_clean": True,
                       "runtime_sha256": {n: runner.digest(ROOT / n) for n in runner.SOURCE_FILES},
                       "workflow_sha256": {n: runner.digest(ROOT / n) for n in runner.WORKFLOW_FILES}}
        self.freeze = {"schema_version": 1, "status": "frozen_before_final",
                       "created_local": datetime.now(runner.ZONE).isoformat(),
                       "selection_basis": "development_only", "no_final_evidence_used": True,
                       "selection_reason": "CPU fixture only; not a model selection or real final freeze",
                       "selected": self.selected, "baseline": self.baseline,
                       "source": self.source, "protocol": runner.protocol_identity(),
                       "development_evidence": {"summary_file": str(self.summary), "sha256": runner.digest(self.summary)},
                       "automatic_candidate_selection": False, "retuning_from_final_allowed": False}

    def test_fixed_four_scenes_have_exact_matrix_and_one_candidate(self):
        jobs = runner.planned_jobs(self.baseline, self.selected, "night2-cpu-fixture")
        self.assertEqual(len(jobs), 4)
        self.assertEqual({(j["speed_m_s"], j["heading_control_enabled"]) for j in jobs},
                         {(s, h) for s in [.3, .5] for h in [True, False]})
        self.assertEqual(len({j["name"] for j in jobs}), 4)
        for job in jobs:
            argv = job["wrapper_argv"]
            def v(flag): return argv[argv.index(flag) + 1]
            self.assertEqual(v("--num_envs"), "512")
            self.assertEqual(v("--stair_batch"), runner.PROTOCOL_FILES["final_geometry"][0])
            self.assertEqual(v("--eval_seconds"), "40")
            self.assertEqual(v("--eval_trace_stride"), "1")
            self.assertEqual(v("--seed"), "1")
            self.assertEqual([argv[i + 1] for i, a in enumerate(argv) if a == "--eval_seed"], ["907", "911", "919"])
            self.assertEqual(argv.count("--candidate_checkpoint"), 1)
            self.assertEqual(v("--candidate_checkpoint"), self.selected["checkpoint"])
            self.assertEqual("--open_loop_heading" in argv, not job["heading_control_enabled"])
            self.assertNotIn("--eval_dynamics", argv)
            self.assertNotIn("train", argv)

    def test_preregistered_protocol_files_pass(self):
        runner.validate_protocol(runner.protocol_identity())

    def test_protocol_hash_change_is_rejected(self):
        value = runner.protocol_identity()
        value["final_geometry"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "preregistered protocol"):
            runner.validate_protocol(value)

    def test_real_development_matrix_is_accepted_without_claiming_pass(self):
        value = runner.validate_development_evidence(self.freeze["development_evidence"], self.selected)
        self.assertEqual(value["heading_numeric_verdict"], "FAIL")
        self.assertTrue(value["no_pass_or_smoothness_inferred_by_freeze"])

    def test_development_evidence_wrong_checkpoint_is_rejected(self):
        selected = {**self.selected, "checkpoint_sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "another checkpoint"):
            runner.validate_development_evidence(self.freeze["development_evidence"], selected)

    def test_final_labeled_evidence_is_rejected_with_synthetic_file(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "synthetic-not-a-real-final-result.json"
            p.write_text(json.dumps({"split": "final"}))
            evidence = {"summary_file": str(p), "sha256": runner.digest(p)}
            with self.assertRaisesRegex(ValueError, "never final"):
                runner.validate_development_evidence(evidence, self.selected)

    def test_incomplete_development_matrix_is_rejected(self):
        value = runner.read(self.summary)
        value["cases"] = value["cases"][:-1]
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "synthetic-truncated-development.json"
            p.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "18 cases"):
                runner.validate_development_evidence({"summary_file": str(p), "sha256": runner.digest(p)}, self.selected)

    def test_freeze_requires_development_only_and_no_retuning(self):
        for field, bad in [("no_final_evidence_used", False), ("selection_basis", "final"),
                           ("retuning_from_final_allowed", True), ("automatic_candidate_selection", True)]:
            value = copy.deepcopy(self.freeze)
            value[field] = bad
            with self.subTest(field=field), self.assertRaises(ValueError):
                runner.validate_selection_value(value)

    def test_model_identity_change_is_rejected(self):
        value = copy.deepcopy(self.freeze)
        value["selected"]["checkpoint_sha256"] = "0" * 64
        with mock.patch.object(runner.backend, "archive_identity", return_value=self.selected):
            with self.assertRaisesRegex(ValueError, "Frozen selected identity"):
                runner.validate_selection_value(value)

    def test_candidate_label_cannot_overwrite_baseline_summary(self):
        value = copy.deepcopy(self.freeze)
        value["selected"]["label"] = "baseline-control660"
        with mock.patch.object(runner.backend, "archive_identity", return_value=value["selected"]):
            with self.assertRaisesRegex(ValueError, "summary label"):
                runner.validate_selection_value(value)

    def test_frozen_code_content_change_is_rejected(self):
        value = copy.deepcopy(self.source)
        value["runtime_sha256"][runner.SOURCE_FILES[0]] = "0" * 64
        with mock.patch.object(runner, "git_output", return_value=""):
            with self.assertRaisesRegex(ValueError, "Code changed after freeze"):
                runner.validate_source(value)

    def test_unchanged_code_can_have_a_later_data_only_commit(self):
        def git_fake(args, binary=False):
            if args[0] == "show":
                return (ROOT / args[1].split(":", 1)[1]).read_bytes()
            return ""
        with mock.patch.object(runner, "git_output", side_effect=git_fake):
            runner.validate_source(self.source)

    def test_dry_cli_writes_immutable_plan_but_never_contacts_docker(self):
        with tempfile.TemporaryDirectory() as temp:
            p, out = Path(temp) / "synthetic-freeze.json", Path(temp) / "dry-output"
            p.write_text(json.dumps(self.freeze))
            identities = {"selected": self.selected, "baseline": self.baseline}
            with mock.patch.object(runner, "validate_selection_value", return_value=identities), \
                 mock.patch.object(runner.backend, "container_idle") as idle, \
                 mock.patch.object(runner.backend, "execute_job") as execute, \
                 mock.patch.object(sys, "argv", ["fixture", "--selection-file", str(p), "--output-dir", str(out)]), \
                 contextlib.redirect_stdout(io.StringIO()):
                runner.main()
            idle.assert_not_called()
            execute.assert_not_called()
            value = runner.read(out / "immutable-manifest.json")
            self.assertEqual(value["stage"], "final")
            self.assertEqual(len(value["jobs"]), 4)
            self.assertEqual((out / "immutable-manifest.json").stat().st_mode & 0o777, 0o444)
            self.assertEqual((out / "selection-freeze.json").stat().st_mode & 0o777, 0o444)
            self.assertEqual(runner.digest(p), runner.digest(out / "selection-freeze.json"))
            self.assertFalse((out / "comparison-completion.json").exists())

    def test_execute_refuses_busy_container_before_any_scene_or_output(self):
        with tempfile.TemporaryDirectory() as temp:
            p, out = Path(temp) / "synthetic-freeze.json", Path(temp) / "must-not-exist"
            p.write_text(json.dumps(self.freeze))
            with mock.patch.object(runner, "validate_selection_value", return_value={"selected": self.selected, "baseline": self.baseline}), \
                 mock.patch.object(runner, "DEADLINE", datetime.max.replace(tzinfo=runner.ZONE)), \
                 mock.patch.object(runner.backend, "container_idle", side_effect=ValueError("Container has live run.py")), \
                 mock.patch.object(runner.backend, "execute_job") as execute, \
                 mock.patch.object(sys, "argv", ["fixture", "--selection-file", str(p), "--output-dir", str(out), "--execute"]), \
                 contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    runner.main()
                self.assertEqual(caught.exception.code, 2)
            execute.assert_not_called()
            self.assertFalse(out.exists())

    def test_synthetic_summary_keeps_fail_and_requires_complete_controllers(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            records = []
            for index in range(4):
                sim = out / ("synthetic-scene-" + str(index))
                result = sim / ("candidates/0_" + Path(self.selected["checkpoint"]).stem) / "result.json"
                result.parent.mkdir(parents=True)
                result.write_text('{"fixture": true}\n')
                records.append({"simulator_directory": str(sim)})
            summary = {"checkpoint_sha256": self.selected["checkpoint_sha256"],
                       "complete_declared_numeric_protocol": True,
                       "controllers": [{"heading_control_enabled": h, "matrix_complete": True,
                                        "numeric_verdict": "FAIL"} for h in [True, False]]}
            def process_fake(argv, **kwargs):
                self.assertIn("--stage", argv)
                self.assertEqual(argv[argv.index("--stage") + 1], "final")
                self.assertEqual(sum(arg.endswith("result.json") for arg in argv), 4)
                prefix = Path(argv[argv.index("--output") + 1])
                prefix.with_suffix(".json").write_text(json.dumps(summary))
                return subprocess.CompletedProcess(argv, 0, "synthetic CPU summary", "")
            with mock.patch.object(runner.subprocess, "run", side_effect=process_fake), \
                 contextlib.redirect_stdout(io.StringIO()):
                result = runner.summarize_policy(self.selected, True, records, out)
            self.assertTrue(all(c["numeric_verdict"] == "FAIL" for c in result["controller_numeric_verdicts"]))
            summary["controllers"][1]["matrix_complete"] = False
            with mock.patch.object(runner.subprocess, "run", side_effect=process_fake):
                with self.assertRaisesRegex(ValueError, "incomplete"):
                    runner.summarize_policy(self.selected, True, records, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
