#!/usr/bin/env python3
"""Audit an explicitly supplied frozen-model seven-command flat evaluation.

Standard library only. Recomputes the existing flat gates from saved aggregate
metrics, preserves failures/zero-action controls, and never selects or retunes.
"""

import argparse
import csv
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMANDS = [[.3, 0., 0.], [.5, 0., 0.], [-.5, 0., 0.],
            [0., .3, 0.], [0., -.3, 0.], [0., 0., .5], [0., 0., -.5]]
THRESHOLDS = {"xy_mae_m_s": .2, "yaw_mae_rad_s": .3,
              "first_episode_survival_fraction": .95,
              "minimum_duration_s": 20., "minimum_num_envs": 64}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_path(value):
    text = str(value)
    for prefix in ("/workspace/himloco/", "/home/cone/Research/HIMLoco/"):
        if text.startswith(prefix):
            return ROOT / text[len(prefix):]
    path = Path(text).expanduser()
    return path.resolve() if path.is_absolute() else ROOT / path


def gate(case, thresholds=THRESHOLDS):
    """Recompute the evaluator's strict gates without an added posture gate."""
    eligible = (case["num_envs"] >= thresholds["minimum_num_envs"]
                and case["requested_duration_s"] + 1e-6 >= thresholds["minimum_duration_s"]
                and case["executed_steps"] == 1000)
    failures = []
    if not eligible:
        failures.append("sample_eligibility")
    if case["failure_reasons"]:
        failures.append("source_failure_reasons")
    for key, name in (("xy_mae_m_s", "XY_MAE"), ("yaw_mae_rad_s", "yaw_MAE")):
        value = case[key]
        if value is None or not math.isfinite(value) or value >= thresholds[key]:
            failures.append(name)
    if case["first_episode_survival_fraction"] < thresholds["first_episode_survival_fraction"]:
        failures.append("first_episode_survival")
    if eligible != case["sample_eligible"] or bool(case["passed"]) != (not failures):
        raise ValueError("Saved case gates differ from independent recomputation")
    return {"independent_passed": not failures, "failed_gate_terms": failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--wrapper-dir", type=Path, required=True)
    parser.add_argument("--selection-file", type=Path, required=True)
    parser.add_argument("--transfer-audit", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    run, wrapper, selection_path, transfer_path, prefix = map(
        local_path, (args.run, args.wrapper_dir, args.selection_file, args.transfer_audit, args.output_prefix))
    destinations = [Path(str(prefix) + suffix) for suffix in (".json", ".csv", ".md")]
    if any(path.exists() for path in destinations):
        raise ValueError("Refusing to overwrite an existing flat audit output")
    selection = json.loads(selection_path.read_text())
    selected = selection["selected"]
    if selection["status"] != "frozen_before_final" or selection["selection_basis"] != "development_only":
        raise ValueError("Expected the frozen development-selected checkpoint")
    checkpoint = local_path(selected["checkpoint"])
    if digest(checkpoint) != selected["checkpoint_sha256"]:
        raise ValueError("Frozen checkpoint changed")
    config, result, launch, transfer = [json.loads(path.read_text()) for path in
                                       (run/"config.json", run/"result.json", wrapper/"launch-record.json", transfer_path)]
    if launch["status"] != "exited" or launch["exit_code"] != 0 or local_path(launch["simulator_log_dir"]).resolve() != run.resolve():
        raise ValueError("Explicit successful wrapper does not identify this result run")
    if transfer["status"] != "CPU_transfer_verified" or transfer["checkpoint_sha256"] != selected["checkpoint_sha256"]:
        raise ValueError("Transfer audit identifies a different or unverified model")
    if transfer["selection_file_sha256"] != digest(selection_path) or not transfer["actual_flat_run"]:
        raise ValueError("Actual flat export has not been audited against this freeze")
    actual = transfer["actual_flat_run"]
    if local_path(actual["run"]).resolve() != run.resolve() or actual["config_sha256"] != digest(run/"config.json") or actual["export_sha256"] != digest(run/"policy.pt"):
        raise ValueError("Actual flat export/config differs from transfer audit")
    if config["mode"] != "evaluate" or config["terrain"] != "flat" or config["num_envs"] != 64 or config["seed"] != 907:
        raise ValueError("Flat evaluation does not match declared mode/envs/seed")
    if local_path(config["checkpoint"]).resolve() != checkpoint.resolve() or config["evaluation_seconds"] != 20:
        raise ValueError("Flat checkpoint or duration differs from protocol")
    if config["requested_additional_training_updates"] is not None or config["physics_dt"] != .005 or config["policy_decimation"] != 4:
        raise ValueError("Unexpected training or flat policy timestep")
    if config["transfer"] != transfer["transfer_record"] or config["command_override"] != COMMANDS:
        raise ValueError("Flat transfer or fixed command list differs")
    for filename, value in selection["source"]["runtime_sha256"].items():
        if digest(ROOT/filename) != value:
            raise ValueError("Frozen runtime changed: " + filename)
    for filename, value in launch["source_sha256"].items():
        if digest(ROOT/filename) != value:
            raise ValueError("Current source differs from launch: " + filename)
    if result["thresholds"] != THRESHOLDS:
        raise ValueError("Flat acceptance thresholds were changed")
    if len(result["cases"]) != 7 or len(result["zero_action_cases"]) != 7 or len(result["baseline_comparison"]) != 7:
        raise ValueError("Seven policy/zero-action commands are required")
    if [case["command_m_s_m_s_rad_s"] for case in result["cases"]] != COMMANDS or [case["command_m_s_m_s_rad_s"] for case in result["zero_action_cases"]] != COMMANDS:
        raise ValueError("Saved command coverage differs from the seven-command protocol")
    rows = []
    for role, cases in (("policy", result["cases"]), ("zero_action", result["zero_action_cases"])):
        for case in cases:
            audited = gate(case)
            if case["num_envs"] != 64 or case["requested_duration_s"] != 20 or case["warmup_steps"] != 100:
                raise ValueError("Case duration/sample/warmup differs from protocol")
            survivors = round(case["first_episode_survival_fraction"] * 64)
            if abs(survivors/64-case["first_episode_survival_fraction"]) > 1e-7:
                raise ValueError("Survival fraction does not correspond to integer environments")
            rows.append({"controller": role, "command": case["command_m_s_m_s_rad_s"],
                         "survivors": survivors, "first_episode_falls": case["first_episode_falls"],
                         "xy_mae_m_s": case["xy_mae_m_s"], "xy_rmse_m_s": case["xy_rmse_m_s"],
                         "yaw_mae_rad_s": case["yaw_mae_rad_s"], "yaw_rmse_rad_s": case["yaw_rmse_rad_s"],
                         "mean_measured_vx_vy_yaw": case["mean_measured_vx_vy_yaw"],
                         "upright_fraction": case["upright_fraction"],
                         "mean_root_height_m": case["mean_root_height_m"],
                         "nominal_height_fraction": case["nominal_height_fraction"],
                         "tracking_samples": case["tracking_samples"],
                         "height_tracking_samples": case["height_tracking_samples"],
                         "mean_first_episode_duration_s": case["mean_first_episode_duration_s"],
                         "finite_physics": case["finite_physics"],
                         "all_episode_falls": case["all_episode_falls"],
                         "first_episode_timeouts": case["first_episode_timeouts"],
                         "all_episode_timeouts": case["all_episode_timeouts"], **audited})
    for compared, policy, control in zip(result["baseline_comparison"], result["cases"], result["zero_action_cases"]):
        if compared["command_m_s_m_s_rad_s"] != policy["command_m_s_m_s_rad_s"]:
            raise ValueError("Zero-action comparison command mismatch")
        for metric, field in (("xy_mae_m_s", "xy_mae_improvement_m_s"), ("yaw_mae_rad_s", "yaw_mae_improvement_rad_s")):
            delta = control[metric]-policy[metric] if control[metric] is not None and policy[metric] is not None else None
            if compared[field] != delta:
                raise ValueError("Zero-action improvement calculation differs")
    passed = all(row["independent_passed"] for row in rows[:7])
    if result["passed"] != passed or result["status"] != ("passed" if passed else "failed") or result["moving_command_tested"] is not True:
        raise ValueError("Aggregate gate differs from case recomputation")
    document = {"schema_version": 1, "recorded_local": datetime.now().astimezone().isoformat(),
                "status": "passed" if passed else "failed", "gradient_updates": 0,
                "checkpoint": selected["checkpoint"], "checkpoint_sha256": selected["checkpoint_sha256"],
                "selection_sha256": digest(selection_path), "run": str(run), "wrapper": str(wrapper),
                "source_hashes": {"result": digest(run/"result.json"), "config": digest(run/"config.json"),
                                  "launch": digest(wrapper/"launch-record.json"), "transfer_audit": digest(transfer_path)},
                "thresholds": THRESHOLDS, "policy_passed_commands": sum(row["independent_passed"] for row in rows[:7]),
                "policy_commands": 7, "zero_action_commands": 7, "independent_case_audits": rows,
                "raw_result": result, "actual_config": config,
                "limits": ["One nominal flat reset seed907; no dynamics/material robustness claim.",
                           "Only first episodes count; tracking excludes first2s, survival includes startup and terminal step.",
                           "Aggregate gates recomputed from saved values; source has no per-environment flat trajectory for independent velocity reconstruction.",
                           "Upright fraction combines roll/pitch; per-axis roll RMS/peak and flat jerk are not recorded.",
                           "Height metrics omit done rows; all-episode counters include later reset episodes and do not replace first-episode survival.",
                           "Critic235→48 reset preserves frozen actor/HIM and performs no learning; successful tensor transfer does not imply flat motion passes.",
                           "Flat omnidirectional results remain separate from staircase geometry acceptance and real-robot deployment."]}
    serialized = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    table = io.StringIO()
    writer = csv.DictWriter(table, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    md = [f"Selected faithful seed1213 checkpoint: flat seven-command {'PASS' if passed else 'FAIL'} ({document['policy_passed_commands']}/7).", "",
          "Each command uses64 environments for20s; original strict gates:XY MAE<0.2m/s, yaw MAE<0.3rad/s, first-episode survival≥95%. Zero learning updates.", "",
          "| Command [vx,vy,yaw] | Survival | Falls | XY MAE | Yaw MAE | Gate |",
          "| --- | ---: | ---: | ---: | ---: | --- |"]
    for row in rows[:7]:
        xy = "unavailable" if row["xy_mae_m_s"] is None else f"{row['xy_mae_m_s']:.5f}"
        yaw = "unavailable" if row["yaw_mae_rad_s"] is None else f"{row['yaw_mae_rad_s']:.5f}"
        result_text = "PASS" if row["independent_passed"] else "FAIL: " + ", ".join(row["failed_gate_terms"])
        md.append(f"| {row['command']} | {row['survivors']}/64 | {row['first_episode_falls']} | {xy} | {yaw} | {result_text} |")
    md += ["", "All matching zero-action controls and complete raw result/config are retained in JSON and CSV.", ""]
    md.extend(document["limits"])
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for path, text in zip(destinations, (serialized, table.getvalue(), "\n".join(md) + "\n")):
        with path.open("x") as stream:
            stream.write(text)
    print(json.dumps({"status": document["status"], "passed_commands": document["policy_passed_commands"],
                      "total_commands": 7, "output_prefix": str(prefix), "gradient_updates": 0}))


if __name__ == "__main__":
    main()
