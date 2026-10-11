"""Host CPU guard checks; fixtures never establish physical evaluation success."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("round3", Path(__file__).with_name("run-stair-night2-round3-comparison.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class Round3Guards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = (runner.ROOT / runner.BASELINE).parent
        cls.manifest = runner.read(directory / "manifest.json")
        config = runner.read(directory / "config.json")
        cls.proof_fixture = {"faithful_reward_manifest": config["stair_reward"],
                             "baseline_archived_runtime_sha256": cls.manifest["source_provenance"]["verified_runtime_source_sha256"]}

    def baseline(self, proof=None):
        return runner.archive_identity("baseline-faithful1213", "faithful", runner.BASELINE,
                                       proof if proof is not None else self.proof_fixture)

    def test_actual_baseline_nineteen_members_and_saved_budget(self):
        with mock.patch.object(runner.backend, "container_idle", side_effect=AssertionError("Docker forbidden")):
            value = self.baseline()
        self.assertEqual(len(value["archive_member_sha256"]), 19)
        self.assertEqual(value["training_budget"]["environment_steps_this_run"], 76800000)

    def test_hash_tampering_rejected(self):
        original = runner.digest
        def changed(path):
            return "0" * 64 if Path(path).name == "policy.pt" else original(path)
        with mock.patch.object(runner, "digest", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "Archive member size/hash mismatch"):
                self.baseline()

    def test_missing_archive_member_declaration_rejected(self):
        original = runner.read
        changed = copy.deepcopy(self.manifest)
        changed["files"].pop("policy.pt")
        def read(path):
            return changed if Path(path).name == "manifest.json" else original(path)
        with mock.patch.object(runner, "read", side_effect=read):
            with self.assertRaisesRegex(ValueError, "nineteen"):
                self.baseline()

    def test_saved_budget_mismatch_rejected(self):
        original = runner.read
        changed = copy.deepcopy(self.manifest)
        changed["saved_additional_updates"] = 99
        def read(path):
            return changed if Path(path).name == "manifest.json" else original(path)
        with mock.patch.object(runner, "read", side_effect=read):
            with self.assertRaisesRegex(ValueError, "saved training budget"):
                self.baseline()

    def test_old_proposal_cannot_be_actual_applied_source_proof(self):
        with self.assertRaisesRegex(ValueError, "Actual applied CPU proof required"):
            runner.validate_proof({"status": "CPU_proposal_verified_not_applied"})

    def test_unproven_legacy_source_rejected(self):
        changed = copy.deepcopy(self.proof_fixture)
        changed["baseline_archived_runtime_sha256"]["isaaclab/run.py"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Legacy source differs"):
            self.baseline(changed)

    def test_declared_matrices_and_scene_reward_identity(self):
        baseline = {"checkpoint": runner.BASELINE, "checkpoint_sha256": runner.BASELINE_HASH}
        candidate = {"checkpoint": "artifacts/new_light/model_760.pt", "checkpoint_sha256": "1" * 64}
        with mock.patch.object(runner.backend, "container_idle", side_effect=AssertionError("Docker forbidden")):
            dev = runner.planned_jobs("development", baseline, candidate, "fixture")
            final = runner.planned_jobs("final", baseline, candidate, "fixture")
        self.assertEqual(len(dev), 2)
        self.assertEqual(len(final), 4)
        for stage, jobs, seeds, count in (("dev", dev, [11, 29, 47], 576), ("final", final, [1301, 1303, 1307], 512)):
            for job in jobs:
                argv = job["wrapper_argv"]
                self.assertEqual(argv[argv.index("--reward_profile") + 1], "faithful")
                self.assertEqual(argv[argv.index("--num_envs") + 1], str(count))
                observed = [int(argv[i + 1]) for i, value in enumerate(argv) if value == "--eval_seed"]
                self.assertEqual(observed, seeds)
                self.assertEqual(job["heading_control_enabled"], "--open_loop_heading" not in argv)
        self.assertEqual({job["heading_control_enabled"] for job in final}, {True, False})

    def test_same_selected_baseline_needs_no_duplicate_policy(self):
        baseline = {"checkpoint": runner.BASELINE, "checkpoint_sha256": runner.BASELINE_HASH}
        jobs = runner.planned_jobs("final", baseline, baseline, "fixture")
        self.assertTrue(all("--candidate_checkpoint" not in j["wrapper_argv"] for j in jobs))

    def test_preregistered_protocol_bound(self):
        self.assertEqual(runner.protocol_identity(), runner.PREREGISTERED_PROTOCOL_SHA256)


if __name__ == "__main__":
    unittest.main()
