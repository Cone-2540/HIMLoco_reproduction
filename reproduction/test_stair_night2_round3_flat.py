"""CPU protocol/gate regression checks; old physical results remain old evidence."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("flat", Path(__file__).with_name("summarize-stair-night2-round3-flat.py"))
flat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flat)
old_run = flat.ROOT / "isaaclab/logs/2026-10-12_05-22-23_night2-flat7-faithful1213-760"


class Round3FlatGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json
        cls.config = json.loads((old_run / "config.json").read_text())
        cls.result = json.loads((old_run / "result.json").read_text())
        cls.checkpoint = flat.local_path(cls.config["checkpoint"])

    def protocol_fixture(self):
        fixture = copy.deepcopy(self.config)
        fixture["seed"] = 1301
        return fixture

    def test_same_gates_on_all_fourteen_actual_historical_cases(self):
        result = [flat.gate(c) for c in self.result["cases"] + self.result["zero_action_cases"]]
        self.assertEqual(sum(c["independent_passed"] for c in result[:7]), 2)
        self.assertEqual(flat.THRESHOLDS, self.result["thresholds"])

    def test_historical_seed907_cannot_be_fresh_round3_result(self):
        with self.assertRaisesRegex(ValueError, "freshseed1301"):
            flat.validate_flat_configuration(self.config, self.checkpoint, self.config["transfer"])

    def test_fresh_protocol_fixture_is_valid_not_physical_evidence(self):
        fixture = self.protocol_fixture()
        flat.validate_flat_configuration(fixture, self.checkpoint, fixture["transfer"])

    def test_any_learning_request_rejected(self):
        fixture = self.protocol_fixture()
        fixture["requested_additional_training_updates"] = 1
        with self.assertRaisesRegex(ValueError, "Unexpected training"):
            flat.validate_flat_configuration(fixture, self.checkpoint, fixture["transfer"])

    def test_omitted_sideways_command_rejected(self):
        fixture = self.protocol_fixture()
        fixture["command_override"].pop(3)
        with self.assertRaisesRegex(ValueError, "fixed command list"):
            flat.validate_flat_configuration(fixture, self.checkpoint, fixture["transfer"])

    def test_critic_transfer_change_rejected(self):
        fixture = self.protocol_fixture()
        fixture["transfer"]["critic_mode"] = "expand"
        with self.assertRaisesRegex(ValueError, "Flat transfer"):
            flat.validate_flat_configuration(fixture, self.checkpoint, self.config["transfer"])

    def test_changed_checkpoint_rejected(self):
        fixture = self.protocol_fixture()
        fixture["checkpoint"] = "artifacts/go2-stairs-control660/model_660.pt"
        with self.assertRaisesRegex(ValueError, "Flat checkpoint"):
            flat.validate_flat_configuration(fixture, self.checkpoint, fixture["transfer"])

    def test_tracking_exact_boundary_fails(self):
        fixture = copy.deepcopy(self.result["cases"][0])
        fixture["xy_mae_m_s"] = .2
        fixture["passed"] = False
        self.assertIn("XY_MAE", flat.gate(fixture)["failed_gate_terms"])
        fixture["xy_mae_m_s"] = .1
        fixture["yaw_mae_rad_s"] = .3
        self.assertIn("yaw_MAE", flat.gate(fixture)["failed_gate_terms"])

    def test_false_saved_pass_rejected(self):
        fixture = copy.deepcopy(self.result["cases"][3])
        fixture["passed"] = True
        with self.assertRaisesRegex(ValueError, "Saved case gates differ"):
            flat.gate(fixture)


if __name__ == "__main__":
    unittest.main()
