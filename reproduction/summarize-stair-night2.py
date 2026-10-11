#!/usr/bin/env python3
"""Read existing night-two results; recompute declared gates without simulation.

This deliberately cannot certify continuous visual quality or paper replication.
It checks each source against the predeclared geometry/seed/controller scope and
keeps missing mandatory runs distinct from passing observed runs.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
COUNT_FIELDS = ("completions", "falls", "stalls", "lateral_escapes", "base_contact_envs",
                "current_sample_base_contact_envs")
ANOMALY_FIELDS = ("nonfinite_envs", "invalid_physics_envs", "invalid_start_envs")
METRIC_FIELDS = ("roll_rms_rad", "roll_peak_rad", "longest_flight_pause_s", "action_second_delta_rms",
                 "linear_jerk_rms_m_s3", "xy_tracking_rmse_m_s", "current_sample_shank_contact_step_fraction",
                 "current_sample_foot_slip_fraction")
RUNTIME_SIGNATURE_CACHE = {}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def runtime_signature(commit):
    """Allow documentary commits only when their recorded runtime trees match."""
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        return None
    if commit not in RUNTIME_SIGNATURE_CACHE:
        probe = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "-r", "--full-tree", commit,
                                "--", "isaaclab"], text=True, capture_output=True, timeout=10)
        items = []
        if probe.returncode == 0:
            for line in probe.stdout.splitlines():
                fields = line.split("\t", 1)
                if len(fields) != 2:
                    continue
                metadata, filename = fields
                path = Path(filename)
                if (path.suffix == ".py" and not path.name.startswith("test_")) or path.name in ("run.sh", "compose.override.yaml"):
                    items.append((filename, metadata.split()[-1]))
        RUNTIME_SIGNATURE_CACHE[commit] = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest() if items else None
    return RUNTIME_SIGNATURE_CACHE[commit]


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def geometry_key(spec):
    if not isinstance(spec, dict):
        return (None,) * 8
    return (spec.get("direction"), spec.get("step_height", spec.get("height")),
            spec.get("step_depth", spec.get("depth")), spec.get("num_steps", 6),
            spec.get("nosing", 0.0), spec.get("width", 1.2), spec.get("landing_length", 2.0),
            spec.get("nosing_thickness", 0.02))


def case_gate(case, trial, is_core, plan):
    """Pure independent gate; missing telemetry never becomes an implicit pass."""
    failures = []
    n = case.get("num_envs")
    minimum = plan["acceptance"]["all_cases_each_reset_seed"]["minimum_environments"]
    if not integer(n) or n < minimum:
        failures.append("missing_or_insufficient_num_envs")
    for key in COUNT_FIELDS:
        value = case.get(key)
        if not integer(value) or not integer(n) or value > n:
            failures.append("invalid_count:" + key)
    valid_counts = integer(n) and n > 0 and all(integer(case.get(key)) and case[key] <= n for key in COUNT_FIELDS)
    if valid_counts:
        fraction = case["completions"] / n
        reported = case.get("completion_fraction")
        if not finite_number(reported) or abs(reported - fraction) > 1e-6:
            failures.append("reported_completion_fraction_disagrees")
        if fraction < plan["acceptance"]["all_cases_each_reset_seed"]["minimum_completion_fraction"]:
            failures.append("completion_below_95pct")
        if case["base_contact_envs"] or case["current_sample_base_contact_envs"]:
            failures.append("base_contact")
        limits = plan["acceptance"]["core" if is_core else "moderate_and_long"]
        if is_core:
            if case["falls"] > limits["maximum_falls"]:
                failures.append("core_fall")
        elif case["falls"] / n > limits["maximum_fall_fraction"]:
            failures.append("fall_fraction_above_5pct")
        for count, threshold in (("stalls", "maximum_stall_fraction"),
                                 ("lateral_escapes", "maximum_lateral_escape_fraction")):
            if case[count] / n > limits[threshold]:
                failures.append(count + "_fraction_above_5pct")
    else:
        fraction = None
    for key in ANOMALY_FIELDS:
        if trial.get(key) != 0 or isinstance(trial.get(key), bool):
            failures.append("trial_anomaly_or_missing:" + key)
    if "failure_reason" not in trial or trial["failure_reason"] is not None:
        failures.append("trial_failure_reason_or_missing")
    metrics = case.get("metrics", {})
    motion_failures = []
    for field, limit in (("roll_rms_rad", "maximum_roll_rms_rad"),
                         ("roll_peak_rad", "maximum_roll_peak_rad"),
                         ("longest_flight_pause_s", "maximum_longest_flight_pause_s")):
        value = metrics.get(field)
        if not finite_number(value) or value < 0:
            motion_failures.append("missing_or_invalid:" + field)
        elif value > plan["acceptance"]["motion_screen_each_case_seed"][limit]:
            motion_failures.append("exceeds_reference:" + field)
    traversal_assessable = (valid_counts and finite_number(case.get("completion_fraction"))
        and abs(case["completion_fraction"] - fraction) <= 1e-6
        and all(integer(trial.get(key)) for key in ANOMALY_FIELDS) and "failure_reason" in trial)
    motion_assessable = all(finite_number(metrics.get(field)) and metrics[field] >= 0
                           for field in ("roll_rms_rad", "roll_peak_rad", "longest_flight_pause_s"))
    return {"completion_fraction_recomputed": fraction,
            "traversal_assessable": traversal_assessable, "motion_assessable": motion_assessable,
            "traversal_gate_passed": not failures, "traversal_failed_terms": failures,
            "motion_screen_passed": not motion_failures, "motion_failed_terms": motion_failures,
            "numeric_screens_passed": not failures and not motion_failures}


def local_checkpoint(value):
    if not isinstance(value, str):
        return None
    prefix = "/workspace/himloco/"
    return ROOT / value[len(prefix):] if value.startswith(prefix) else Path(value)


def nearby_config(path):
    for directory in (path.parent, *list(path.parent.parents)[:5]):
        candidate = directory / "config.json"
        if candidate.is_file():
            return candidate, read(candidate)
    return None, {}


def source_rows(path, plan, split, geometries):
    document = read(path)
    policy = document.get("policy", document)
    specification = plan["geometry_sets"][split]
    cfg_path, cfg = nearby_config(path)
    errors = []
    source_geometries = policy.get("geometry")
    if not isinstance(source_geometries, list) or [geometry_key(g) for g in source_geometries] != [geometry_key(g) for g in geometries]:
        errors.append("source_geometry_does_not_match_declared_ordered_matrix")
    speed = policy.get("command_forward_speed_m_s")
    if speed not in plan["evaluation"]["speeds_m_s"]:
        errors.append("unexpected_or_missing_speed")
    heading = policy.get("heading_control", {}).get("enabled")
    if not isinstance(heading, bool):
        errors.append("missing_heading_controller_identity")
    if policy.get("randomized_reset") is not True:
        errors.append("randomized_reset_not_verified")
    if policy.get("dynamics_randomized") is not False:
        errors.append("unexpected_or_missing_dynamics_mode")
    if not cfg_path:
        errors.append("missing_construction_config")
    if cfg.get("mode") != "evaluate" or cfg.get("terrain") != "stairs":
        errors.append("config_is_not_stair_evaluation")
    if cfg.get("num_envs") != specification["num_envs"]:
        errors.append("config_num_envs_differs_from_matrix")
    if cfg.get("seed") != plan["evaluation"]["construction_seed"]:
        errors.append("construction_seed_differs")
    if cfg.get("evaluation_trace_stride_policy_steps") != 1:
        errors.append("dense_20ms_trace_not_verified")
    if cfg.get("evaluation_seconds") != plan["evaluation"]["seconds"]:
        errors.append("episode_duration_differs")
    if cfg.get("physics_dt") != plan["evaluation"]["physics_dt_s"] or cfg.get("policy_decimation") != 4:
        errors.append("physics_or_policy_cadence_differs")
    if cfg.get("domain_randomization") is not None or cfg.get("friction_override") is not None:
        errors.append("unexpected_domain_or_friction_configuration")
    if cfg.get("evaluation_dynamics_randomized") is not False:
        errors.append("construction_config_dynamics_mode_not_verified")
    identity = document.get("checkpoint") or cfg.get("checkpoint")
    checkpoint = local_checkpoint(identity)
    checkpoint_hash = sha256(checkpoint) if checkpoint and checkpoint.is_file() else None
    if checkpoint_hash is None:
        errors.append("checkpoint_identity_or_local_hash_unavailable")
    trials = policy.get("trials", [])
    if not isinstance(trials, list) or not trials:
        raise ValueError(f"No staircase trials: {path}")
    seeds = [trial.get("seed") for trial in trials]
    if len(seeds) != len(set(seeds)):
        errors.append("duplicate_reset_seeds")
    if not set(seeds).issubset(set(specification["reset_seeds"])):
        errors.append("undeclared_reset_seeds")
    rows = []
    for trial in trials:
        trial_errors = list(errors)
        if trial.get("num_envs") != specification["num_envs"]:
            trial_errors.append("trial_num_envs_differs")
        if not finite_number(trial.get("initial_reset_distribution", {}).get("yaw_std_rad")) or trial["initial_reset_distribution"]["yaw_std_rad"] <= 1e-6:
            trial_errors.append("randomized_yaw_variability_not_verified")
        cases = trial.get("cases", [])
        if not isinstance(cases, list) or len(cases) != len(geometries):
            trial_errors.append("missing_or_extra_cases")
        if not isinstance(cases, list) or not cases:
            cases = [{"case_index": index} for index in range(len(geometries))]
        indices = [case.get("case_index") for case in cases]
        if indices != list(range(len(geometries))):
            trial_errors.append("case_indices_differ_or_duplicate")
        for key in COUNT_FIELDS:
            if not integer(trial.get(key)) or any(not integer(case.get(key)) for case in cases) or sum(case.get(key, 0) for case in cases) != trial.get(key):
                trial_errors.append("case_totals_disagree_with_trial:" + key)
        per_env = trial.get("per_env", {})
        for array, count in (("completed", "completions"), ("fall", "falls"), ("stall", "stalls"), ("lateral_escape", "lateral_escapes")):
            values = per_env.get(array)
            if not isinstance(values, list) or len(values) != specification["num_envs"] or not all(isinstance(v, bool) for v in values) or sum(values) != trial.get(count):
                trial_errors.append("per_env_counts_unverified:" + array)
        for case in cases:
            index = case.get("case_index")
            valid_index = integer(index) and index < len(geometries)
            case_errors = list(trial_errors)
            if not valid_index or geometry_key(case.get("geometry", {})) != geometry_key(geometries[index]):
                case_errors.append("case_geometry_differs")
            if case.get("num_envs") != plan["evaluation"]["envs_each_case_each_reset_seed"]:
                case_errors.append("case_environment_count_differs")
            group = next((label for label in ("core", "moderate", "long") if valid_index and index in specification[label + "_case_indices"]), "unrecognized")
            gate = case_gate(case, trial, group == "core", plan)
            assessable = gate["traversal_assessable"] and gate["motion_assessable"] and not case_errors
            assessment = "PASS" if assessable and gate["numeric_screens_passed"] else "FAIL" if assessable else "NOT_ASSESSED"
            rows.append({"source": str(path), "checkpoint": identity, "checkpoint_sha256": checkpoint_hash,
                         "source_commit": cfg.get("source_commit"), "source_tracked_files_dirty": cfg.get("source_tracked_files_dirty"),
                         "reward_profile": (cfg.get("stair_reward") or {}).get("profile"),
                         "speed_m_s": speed, "heading_control_enabled": heading, "reset_seed": trial.get("seed"),
                         "case_index": index, "case_name": geometries[index]["name"] if valid_index else None,
                         "group": group, "geometry": case.get("geometry"), "num_envs": case.get("num_envs"),
                         **{key: case.get(key) for key in COUNT_FIELDS},
                         **{key: case.get("metrics", {}).get(key) for key in METRIC_FIELDS}, **gate,
                         "source_protocol_verified": not case_errors, "source_protocol_errors": case_errors,
                         "numeric_assessment_status": assessment,
                         "numeric_acceptance_passed": gate["numeric_screens_passed"] and not case_errors,
                         "continuous_video_review_status": "not_reviewed_by_this_numeric_tool"})
    source = {"result": str(path), "result_sha256": sha256(path), "config": str(cfg_path) if cfg_path else None,
              "checkpoint": identity, "checkpoint_sha256": checkpoint_hash, "source_commit": cfg.get("source_commit"),
              "source_tracked_files_dirty": cfg.get("source_tracked_files_dirty"), "reward_weights": cfg.get("reward_weights"),
              "committed_runtime_tree_signature": runtime_signature(cfg.get("source_commit")),
              "evaluation_num_envs_from_config": cfg.get("num_envs"),
              "reset_seeds_observed": seeds, "source_protocol_errors": errors,
              "source_original_passed": document.get("passed"), "source_final_acceptance": document.get("final_acceptance")}
    return source, rows


def summarize(paths, plan, split, geometries):
    sources, rows = [], []
    for path in paths:
        source, additions = source_rows(path, plan, split, geometries)
        sources.append(source)
        rows.extend(additions)
    hashes = {source["checkpoint_sha256"] for source in sources}
    if len(hashes) != 1 or None in hashes:
        raise ValueError("Every input in one summary must identify the same available checkpoint; summarize different candidates separately")
    commits = {source["source_commit"] for source in sources}
    signatures = {source["committed_runtime_tree_signature"] for source in sources}
    if None in commits or (len(commits) != 1 and (None in signatures or len(signatures) != 1
                       or any(source["source_tracked_files_dirty"] is not False for source in sources))):
        raise ValueError("Different source commits require identical recorded runtime trees and clean source flags; otherwise summarize separately")
    weights = {json.dumps(source["reward_weights"], sort_keys=True) for source in sources}
    if len(weights) != 1 or "null" in weights:
        raise ValueError("Do not pool different or unknown construction reward weights")
    specification = plan["geometry_sets"][split]
    expected = {(speed, heading, seed, index) for speed in plan["evaluation"]["speeds_m_s"]
                for heading in (True, False) for seed in specification["reset_seeds"]
                for index in range(len(geometries))}
    observed = [(row["speed_m_s"], row["heading_control_enabled"], row["reset_seed"], row["case_index"]) for row in rows]
    duplicates = sorted([repr(key) for key in set(observed) if observed.count(key) > 1])
    missing = sorted(expected - set(observed))
    controller_reports = []
    for heading in (True, False):
        selected = [row for row in rows if row["heading_control_enabled"] is heading]
        controller_missing = [key for key in missing if key[1] is heading]
        groups = {}
        for group in ("core", "moderate", "long"):
            group_rows = [row for row in selected if row["group"] == group]
            groups[group] = {"observed_case_seed_speed_rows": len(group_rows),
                "completions": sum(row["completions"] for row in group_rows if integer(row["completions"])),
                "num_envs": sum(row["num_envs"] for row in group_rows if integer(row["num_envs"])),
                "all_observed_numeric_acceptance_passed": bool(group_rows) and all(row["numeric_acceptance_passed"] for row in group_rows),
                "failed_rows": [{key: row[key] for key in ("case_name", "reset_seed", "speed_m_s", "traversal_failed_terms", "motion_failed_terms", "source_protocol_errors")} for row in group_rows if not row["numeric_acceptance_passed"]]}
        complete = bool(selected) and not controller_missing and not duplicates
        passing = bool(selected) and all(row["numeric_acceptance_passed"] for row in selected)
        failed = any(row["numeric_assessment_status"] == "FAIL" for row in selected)
        unassessed = any(row["numeric_assessment_status"] == "NOT_ASSESSED" for row in selected)
        controller_reports.append({"heading_control_enabled": heading, "matrix_complete": complete,
            "numeric_verdict": "FAIL" if failed else "NOT_ASSESSED" if unassessed else "PASS" if complete and passing else "INCOMPLETE",
            "missing_case_seed_speed_rows": len(controller_missing), "groups": groups})
    return {"scope": plan["scope"], "split": split, "sources": sources, "cases": rows,
            "checkpoint_sha256": next(iter(hashes)), "duplicate_case_seed_speed_controller_rows": duplicates,
            "missing_case_seed_speed_controller_rows": [{"speed_m_s": s, "heading_control_enabled": h, "reset_seed": seed, "case_index": i} for s, h, seed, i in missing],
            "controllers": controller_reports, "complete_declared_numeric_protocol": not missing and not duplicates,
            "smoothness_verified": False, "smoothness_verified_by_this_numeric_tool": False,
            "motion_quality_review": "root may judge complete frame sequences and dense telemetry under user-authorized interpretation; never imply realtime playback occurred",
            "paper_real_world_replication_verified": False,
            "limits": ["This numeric tool does not review images or decide motion quality; root can make a separate documented judgment from full data and frame sequences",
                       "Core zero-fall gate is stricter than source assess_final; source passed booleans are retained only for provenance",
                       "Full per-environment initial quaternions/joints and per-case base-contact identities may not be in source; aggregate detector counts are not independent contact reconstruction",
                       "Default heading and zero-yaw verdicts stay separate; flat regression is a required separate report",
                       "Three reset seeds are evaluation repeats, not three training runs or dynamics-construction draws",
                       "Final candidate/source/geometry freeze must be checked against the separately saved freeze artifact before any final claim",
                       "Across different clean Git commits, only identical recorded runtime trees may be pooled; documentary files and tests are excluded from runtime signature"]}


def write_markdown(report, path):
    lines = ["# 本轮楼梯数值汇总", "", "范围：" + report["split"] + "；只读取明确指定的已有结果。",
             "", f"checkpoint SHA256：`{report['checkpoint_sha256']}`。",
             "", f"已观测 {len(report['cases'])} 项／seed／速度／控制方式记录；缺少 {len(report['missing_case_seed_speed_controller_rows'])} 项预声明记录。",
             "完整声明数值协议：" + ("已采集完整" if report["complete_declared_numeric_protocol"] else "未采集完整；不能据本表声称全范围 PASS") + "。",
             "", "| 控制方式 | 已观测数值判决 | 矩阵完整 | 未采集项数 |", "|---|---|---|---:|"]
    for controller in report["controllers"]:
        mode = "默认外部航向反馈" if controller["heading_control_enabled"] else "零 yaw 指令"
        lines.append(f"| {mode} | {controller['numeric_verdict']} | {controller['matrix_complete']} | {controller['missing_case_seed_speed_rows']} |")
    lines.extend(["", "逐项记录的 PASS／FAIL 只判断已经采集的证据；缺少计数或关键证据为 NOT_ASSESSED，尚未运行的速度／控制方式保留在缺项清单。",
                  "", "| Case | Seed | Speed | Completed | Fall / base | Roll RMS / peak | Pause(s) | 已观测数值判决 |",
                  "|---|---:|---:|---:|---:|---:|---:|---|"])
    def number(value):
        return f"{value:.4f}" if finite_number(value) else "缺失"
    for row in report["cases"]:
        lines.append(f"| {row['case_name']} | {row['reset_seed']} | {row['speed_m_s']} | {row['completions']}/{row['num_envs']} | "
                     f"{row['falls']} / {row['base_contact_envs']} | {number(row['roll_rms_rad'])} / {number(row['roll_peak_rad'])} | "
                     f"{number(row['longest_flight_pause_s'])} | {row['numeric_assessment_status']} |")
    lines.extend(["", "本工具没有审查图像；数值通过不是最终流畅判断。主任务可依据用户授权，结合完整帧序列、20 ms 遥测和基线作条件性判断，必须明确未实时播放的审查方式。",
                  "最终候选冻结、默认航向／零 yaw 的差异、平地回归及论文真机比较限制仍需独立报告。",
                  "", "来源和失败项完整保存在同名前缀 JSON／CSV；原始 passed 布尔值保留作溯源，未用于替代本轮门槛。", ""])
    path.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--stage", "--split", dest="stage", choices=("development", "final"), default="development",
                        help="Default development; only explicitly supplied result files are read, never directory globs")
    parser.add_argument("--plan", type=Path, default=Path(__file__).with_name("stair-night2-evaluation-plan.json"))
    parser.add_argument("--output", type=Path, default=Path("reproduction/stair-night2-numeric-summary"))
    args = parser.parse_args()
    try:
        plan = read(args.plan)
        geometries = read(ROOT / plan["geometry_sets"][args.stage]["file"])
        report = summarize(args.results, plan, args.stage, geometries)
        report.update(plan_file=str(args.plan), plan_sha256=sha256(args.plan),
                      geometry_file=plan["geometry_sets"][args.stage]["file"],
                      geometry_sha256=sha256(ROOT / plan["geometry_sets"][args.stage]["file"]))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.with_suffix(".json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        write_markdown(report, args.output.with_suffix(".md"))
        columns = [key for key in report["cases"][0] if key != "geometry"]
        with args.output.with_suffix(".csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for row in report["cases"]:
                writer.writerow({key: json.dumps(row[key]) if isinstance(row[key], (list, dict)) else row[key] for key in columns})
    except (KeyError, TypeError, ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({"output": str(args.output), "checkpoint_sha256": report["checkpoint_sha256"],
                      "observed_rows": len(report["cases"]), "complete_declared_numeric_protocol": report["complete_declared_numeric_protocol"],
                      "controllers": [{key: controller[key] for key in ("heading_control_enabled", "numeric_verdict", "matrix_complete")} for controller in report["controllers"]],
                      "smoothness_verified": False}))


if __name__ == "__main__":
    main()
