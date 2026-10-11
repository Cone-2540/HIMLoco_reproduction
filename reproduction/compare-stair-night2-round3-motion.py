#!/usr/bin/env python3
"""Compare saved round-three motion without importing Torch or the simulator.

The unit of comparison is one case, reset seed, speed and controller. Failed
traversal never wins through a lower contact or motion magnitude. Per-body
forces are from representative trace environments, not the full population.
"""

import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
METRICS = (
    "current_sample_shank_contact_step_fraction", "shank_contact_step_fraction",
    "action_delta_rms", "action_second_delta_rms", "linear_jerk_rms_m_s3",
    "linear_acceleration_rms_m_s2", "xy_tracking_mae_m_s", "xy_tracking_rmse_m_s",
    "yaw_tracking_mae_rad_s", "heading_abs_error_rad", "lateral_abs_error_m",
    "roll_rms_rad", "roll_peak_rad", "pitch_rms_rad", "flight_pause_fraction",
    "longest_flight_pause_s", "current_sample_foot_slip_fraction",
)


def module(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "reproduction" / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


SUMMARY = module("summarize-stair-night2.py", "night2_summary_cpu")
MOTION = module("analyze-stair-motion.py", "night2_motion_cpu")


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return SUMMARY.sha256(path)


def json_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def resolve(path):
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def delta(a, b):
    if not finite(a) or not finite(b):
        return {"baseline": a, "candidate": b, "delta": None, "relative_change_pct": None,
                "status": "unavailable"}
    return {"baseline": a, "candidate": b, "delta": b - a,
            "relative_change_pct": (b - a) / abs(a) * 100 if a != 0 else None,
            "status": "observed"}


def archive_identity(identity):
    errors = []
    path = resolve(identity["checkpoint"])
    archive = read(resolve(identity["training_manifest"]))
    checks = [(path, identity["checkpoint_sha256"]),
              (resolve(identity["training_manifest"]), identity["training_manifest_sha256"]),
              (path.parent / "config.json", identity["training_config_sha256"]),
              (path.parent / "result.json", identity["training_result_sha256"])]
    for filename, expected in checks:
        if not filename.is_file() or sha(filename) != expected:
            errors.append("archive_file_identity_differs:" + str(filename))
    if archive.get("training_seed") != identity.get("training_seed"):
        errors.append("training_seed_differs")
    if archive.get("reward_profile") != identity.get("training_reward_profile"):
        errors.append("training_reward_profile_differs")
    if archive.get("files", {}).get(path.name, {}).get("sha256") != identity["checkpoint_sha256"]:
        errors.append("archive_checkpoint_hash_differs")
    cfg = read(path.parent / "config.json")
    if (cfg.get("stair_reward") or {}).get("profile") != archive.get("reward_profile"):
        errors.append("archived_training_config_reward_profile_differs")
    if cfg.get("seed") != archive.get("training_seed"):
        errors.append("archived_training_config_seed_differs")
    return {"label": identity["label"], "checkpoint": str(path), "checkpoint_sha256": sha(path),
            "training_manifest": str(resolve(identity["training_manifest"])),
            "training_reward_profile": archive.get("reward_profile"),
            "training_reward_weights": cfg.get("reward_weights"),
            "training_seed": archive.get("training_seed"),
            "origin_checkpoint_sha256": archive.get("origin_checkpoint_sha256"),
            "saved_additional_updates": archive.get("saved_additional_updates"),
            "environment_steps_this_run": archive.get("environment_steps_this_run"),
            "identity_verified": not errors, "errors": errors}


def physical_readback(source):
    path = Path(source["domain_readback_path"]) if source.get("domain_readback_path") else None
    data = read(path) if path and path.is_file() else {}
    selected = {key: data.get(key) for key in
                ("base_mass_kg", "base_inertia_kg_m2", "base_com", "actuator_pd", "foot_material")}
    errors = []
    if data.get("status") != "captured":
        errors.append("domain_readback_not_captured")
    for key, value in selected.items():
        if not isinstance(value, dict) or value.get("status") != "available":
            errors.append("physical_readback_missing:" + key)
    terrain = data.get("terrain_material")
    if not isinstance(terrain, dict) or terrain.get("status") != "available":
        errors.append("terrain_material_readback_missing")
    else:
        selected["terrain_material"] = terrain
    return {"path": str(path) if path else None, "sha256": sha(path) if path else None,
            "values_sha256": json_sha(selected), "available": not errors,
            "errors": errors, "values": selected}


def trace_legs(source, trial, case_index):
    cache = source.setdefault("_trace_environment_cache", {})
    if trial["seed"] not in cache:
        cache[trial["seed"]] = MOTION.extract_environments(trial)
    environments = cache[trial["seed"]]
    names = source.get("leg_body_names")
    dt = source.get("policy_dt_s")
    output = []
    for (index, env_id), records in environments.items():
        if index != case_index:
            continue
        mask, first_time = MOTION.sample_mask(records, dt)
        selected = [record for record, keep in zip(records, mask) if keep]
        forces = MOTION.field(selected, "leg_current_normal_force_norm_n") if selected else None
        cadence = MOTION.cadence(records, dt)
        if (not forces or not names or any(len(values) != len(names) for values in forces)):
            output.append({"env_id": env_id, "status": "missing_leg_force_or_names", "cadence": cadence})
            continue
        bodies = []
        for column, name in enumerate(names):
            values = [value[column] for value in forces]
            indices = [i for i, value in enumerate(values) if value > 1.0]
            segments, segment = [], []
            for i in indices:
                if segment and (i != segment[-1] + 1 or
                                abs(selected[i]["time_s"] - selected[segment[-1]]["time_s"] - dt) > 1e-6):
                    segments.append(segment)
                    segment = []
                segment.append(i)
            if segment:
                segments.append(segment)
            longest = max(segments, key=len, default=[])
            bodies.append({"body_name": name, "eligible_samples": len(values),
                           "current_contact_samples_gt_1n": len(indices),
                           "current_contact_fraction_gt_1n": len(indices) / len(values),
                           "sampled_force_peak_n": max(values),
                           "sample_exposure_s": len(indices) * dt,
                           "segments": len(segments),
                           "longest_segment_samples": len(longest),
                           "longest_segment_sample_exposure_s": len(longest) * dt,
                           "longest_segment_endpoint_span_s":
                               selected[longest[-1]]["time_s"] - selected[longest[0]]["time_s"] if longest else 0.0})
        output.append({"env_id": env_id, "status": "observed", "cadence": cadence,
                       "metrics_first_eligible_time_s": first_time, "body_metrics": bodies})
    return {"scope": "representative active first-episode trace environments only; not all32 case environments",
            "contact_force_threshold_n": 1.0,
            "time_semantics": "sample exposure=n*20ms and endpoint span=(n-1)*20ms; neither proves substep continuous contact",
            "environments": output}


def source_check(path, source, expected_identity, manifest, plan, geometries):
    declaration, rows = SUMMARY.source_rows(path, plan, "development", geometries)
    errors = list(declaration["source_protocol_errors"])
    cfg = source["config"]
    if declaration["checkpoint_sha256"] != expected_identity["checkpoint_sha256"]:
        errors.append("evaluated_checkpoint_differs_from_frozen_training_identity")
    if cfg.get("source_commit") != manifest["source"]["git_commit"]:
        errors.append("source_commit_differs_from_immutable_launch_manifest")
    if cfg.get("source_tracked_files_dirty") is not False:
        errors.append("source_clean_flag_not_verified")
    if (cfg.get("stair_reward") or {}).get("profile") != manifest["common_evaluation_reward_profile"]:
        errors.append("construction_reward_profile_differs")
    cfg_path, unused = SUMMARY.nearby_config(path)
    physical = physical_readback(source)
    errors.extend(physical["errors"])
    return {**declaration, "config_sha256": sha(cfg_path) if cfg_path else None,
            "common_evaluation_reward_profile": (cfg.get("stair_reward") or {}).get("profile"),
            "source_binding_verified": not errors, "source_binding_errors": errors,
            "physical_readback": {k: v for k, v in physical.items() if k != "values"}}, rows, physical


def pair_sources(paths, identities, manifest, plan, geometries):
    a, b = [MOTION.load_source(path, "policy") for path in paths]
    declarations = [source_check(path, source, identity, manifest, plan, geometries)
                    for path, source, identity in zip(paths, (a, b), identities)]
    da, ra, pa = declarations[0]
    db, rb, pb = declarations[1]
    pair_errors = []
    for label, source in (("baseline", da), ("candidate", db)):
        pair_errors.extend(label + ":" + term for term in source["source_binding_errors"])
    # These candidate subdirectories inherit the single scene's construction
    # config/readback. Missing values never match through None equality.
    if not pa["available"] or not pb["available"] or pa["values"] != pb["values"]:
        pair_errors.append("physical_readbacks_unavailable_or_different")
    for field in ("contact_sampling", "heading_control", "command_forward_speed_m_s",
                  "dynamics_randomized", "randomized_reset", "metrics_scope", "leg_body_names"):
        if a["report"].get(field) is None or a["report"].get(field) != b["report"].get(field):
            pair_errors.append("policy_protocol_differs:" + field)
    if a["config"] != b["config"]:
        pair_errors.append("construction_configuration_differs")
    trials_a = {trial["seed"]: trial for trial in a["report"]["trials"]}
    trials_b = {trial["seed"]: trial for trial in b["report"]["trials"]}
    map_a = {(row["reset_seed"], row["case_index"]): row for row in ra}
    map_b = {(row["reset_seed"], row["case_index"]): row for row in rb}
    if trials_a.keys() != trials_b.keys() or map_a.keys() != map_b.keys():
        raise ValueError("Missing or extra candidate trial/case rows")
    output = []
    for key, row_a in map_a.items():
        row_b = map_b[key]
        seed, index = key
        ta, tb = trials_a[seed], trials_b[seed]
        ca, cb = ta["cases"][index], tb["cases"][index]
        errors = list(pair_errors)
        initial_a = ta.get("per_env", {}).get("initial_root_relative_xyz_m")
        initial_b = tb.get("per_env", {}).get("initial_root_relative_xyz_m")
        xyz_match = (isinstance(initial_a, list) and len(initial_a) == plan["geometry_sets"]["development"]["num_envs"]
                     and initial_a == initial_b)
        distributions_match = (isinstance(ta.get("initial_reset_distribution"), dict) and
                               ta["initial_reset_distribution"] == tb.get("initial_reset_distribution"))
        if not xyz_match or not distributions_match:
            errors.append("recorded_initial_reset_evidence_differs_or_missing")
        if MOTION.geometry_key(ca["geometry"]) != MOTION.geometry_key(cb["geometry"]):
            errors.append("physical_case_geometry_differs")
        errors.extend("baseline_protocol:" + item for item in row_a["source_protocol_errors"])
        errors.extend("candidate_protocol:" + item for item in row_b["source_protocol_errors"])
        competent_a = row_a["numeric_acceptance_passed"]
        competent_b = row_b["numeric_acceptance_passed"]
        comparable = competent_a and competent_b and not errors
        output.append({"speed_m_s": row_a["speed_m_s"], "heading_control_enabled": row_a["heading_control_enabled"],
                       "reset_seed": seed, "case_index": index, "case_name": row_a["case_name"],
                       "group": row_a["group"], "geometry": ca["geometry"],
                       "baseline_gate": {key: row_a[key] for key in SUMMARY.COUNT_FIELDS +
                         ("traversal_failed_terms", "motion_failed_terms", "numeric_acceptance_passed")},
                       "candidate_gate": {key: row_b[key] for key in SUMMARY.COUNT_FIELDS +
                         ("traversal_failed_terms", "motion_failed_terms", "numeric_acceptance_passed")},
                       "matched_source_and_physics": not errors, "matching_errors": errors,
                       "recorded_initial_root_xyz_all_environments_equal": xyz_match,
                       "initial_reset_distribution_equal": distributions_match,
                       "initial_quaternion_full_per_environment_recorded": False,
                       "comparable_competent_case_seed": comparable,
                       "comparison_status": "competent_numeric_diagnostics" if comparable else "diagnostic_only_failed_gate_or_unmatched",
                       "metrics": {field: delta(ca["metrics"].get(field), cb["metrics"].get(field)) for field in METRICS},
                       "baseline_representative_leg_trace": trace_legs(a, ta, index),
                       "candidate_representative_leg_trace": trace_legs(b, tb, index)})
    return {"baseline": da, "candidate": db}, output


def fmt(value):
    return "NA" if value is None else f"{value:.5g}"


def write_markdown(report, path):
    counts = report["counts"]
    lines = ["# Round3 development：同 seed / 同预算 motion 比较", "",
             "这是 CPU 对既有 result.json 的独立分析，不是 smoothness 或论文效果认证。",
             f"共 {counts['case_speed_seed_rows']} 条 case×speed×reset seed；"
             f"两方均过本轮 95% 数值门槛且匹配的条目 {counts['competent_matched_rows']}。",
             "每 case32env 至少31完成、core0fall、所有 case0base，并保留 roll/pause gate。"
             "失败或短 episode 的低接触不能计作改善。", "",
             "两方从同一660 checkpoint，以训练 seed1213各继续100updates/76800000env steps。"
             "训练 reward 分别 faithful / contact_light；共同 evaluation 构造仍 faithful。", "",
             "物理 readback 和全部 env 初始 root xyz 核对；yaw/quaternion 只有 reset 分布摘要，"
             "没有逐 env 初始 quaternion 数组，因此不宣称全部初始状态逐项完全相同。", "",
             "全32env当前 shank 接触率来自 case metrics；该历史命名聚合 thigh+calf，并非仅小腿。"
             "逐 leg 数据仅每 case 一个代表 env 的"
             "20ms trace，不能当群体改善。接触 exposure 不代表步内连续接触时长；"
             "foot link速度也不等于真实接触点滑移。", "",
             "|speed|seed|case|baseline完成|light完成|两方数值合格且匹配|当前shank B→L|action2 B→L|jerk B→L|xy RMSE B→L|",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for row in report["cases"]:
        def values(field):
            data = row["metrics"][field]
            return fmt(data["baseline"]) + "→" + fmt(data["candidate"])
        lines.append(f"|{row['speed_m_s']}|{row['reset_seed']}|{row['case_name']}|"
                     f"{row['baseline_gate']['completions']}/32|{row['candidate_gate']['completions']}/32|"
                     f"{'是' if row['comparable_competent_case_seed'] else '否'}|"
                     f"{values(METRICS[0])}|{values('action_second_delta_rms')}|"
                     f"{values('linear_jerk_rms_m_s3')}|{values('xy_tracking_rmse_m_s')}|")
    lines += ["", "只对合格 case 的方向计数（降低/升高/相等）如下；这不构成 pooled contact 验收：", ""]
    for field, values in report["eligible_case_direction_counts"].items():
        lines.append(f"- `{field}`：{values['lower']}/{values['higher']}/{values['equal']}。")
    failures = [row for row in report["cases"] if not row["comparable_competent_case_seed"]]
    lines += ["", "不合格项保留如下：", ""]
    for row in failures:
        lines.append(f"- speed{row['speed_m_s']}, seed{row['reset_seed']}, {row['case_name']}："
                     f"baseline={row['baseline_gate']['traversal_failed_terms'] + row['baseline_gate']['motion_failed_terms']}；"
                     f"light={row['candidate_gate']['traversal_failed_terms'] + row['candidate_gate']['motion_failed_terms']}；"
                     f"matching={row['matching_errors']}。")
    lines += ["", "本报告仅 development 默认外部 yaw反馈两速度。不能替代 zero-yaw 或 reserved final；"
              "原冻结 final 和旧视频对齐限制不变。详细的 roll/pause、逐 leg 样本统计、hash 与源文件"
              "绑定见同名 JSON。"]
    path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", action="append", nargs=2, required=True, metavar=("BASELINE", "CANDIDATE"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = read(args.manifest)
    plan_path = ROOT / "reproduction/stair-night2-evaluation-plan.json"
    geometry_path = ROOT / "reproduction/stair-night2-development-geometries.json"
    plan, geometries = read(plan_path), read(geometry_path)
    if isinstance(geometries, dict):
        geometries = geometries["cases"]
    source_errors = []
    if manifest.get("stage") != "development" or manifest.get("round") != 3:
        source_errors.append("manifest_stage_is_not_round3_development")
    for filename, expected in manifest["source"]["file_sha256"].items():
        if not resolve(filename).is_file() or sha(resolve(filename)) != expected:
            source_errors.append("frozen_source_file_hash_differs:" + filename)
    proof = resolve(manifest["source_proof_file"])
    if sha(proof) != manifest["source_proof_sha256"] or read(proof) != manifest["source_proof"]:
        source_errors.append("frozen_source_compatibility_proof_differs")
    if manifest["protocol"].get(str(geometry_path.relative_to(ROOT))) != sha(geometry_path):
        source_errors.append("frozen_development_geometry_hash_differs")
    identities = [archive_identity(manifest[label]) for label in ("baseline", "candidate")]
    for key in ("training_seed", "origin_checkpoint_sha256", "saved_additional_updates", "environment_steps_this_run"):
        if identities[0].get(key) is None or identities[0].get(key) != identities[1].get(key):
            source_errors.append("training_comparison_not_matched:" + key)
    sources, cases = [], []
    for pair in args.pair:
        declarations, rows = pair_sources([resolve(path) for path in pair], identities, manifest, plan, geometries)
        sources.append(declarations)
        for row in rows:
            row["matching_errors"].extend(source_errors)
            row["matching_errors"].extend(error for identity in identities for error in identity["errors"])
            if row["matching_errors"]:
                row["matched_source_and_physics"] = False
                row["comparable_competent_case_seed"] = False
                row["comparison_status"] = "diagnostic_only_failed_gate_or_unmatched"
        cases.extend(rows)
    keys = [(row["speed_m_s"], row["heading_control_enabled"], row["reset_seed"], row["case_index"]) for row in cases]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate case/speed/seed/controller comparisons")
    eligible = [row for row in cases if row["comparable_competent_case_seed"]]
    directions = {field: {"lower": sum(row["metrics"][field]["delta"] < 0 for row in eligible
                                      if row["metrics"][field]["delta"] is not None),
                          "higher": sum(row["metrics"][field]["delta"] > 0 for row in eligible
                                       if row["metrics"][field]["delta"] is not None),
                          "equal": sum(row["metrics"][field]["delta"] == 0 for row in eligible),
                          "unavailable": sum(row["metrics"][field]["delta"] is None for row in eligible)}
                  for field in METRICS}
    report = {"schema_version": 1, "stage": "round3_development_cpu_motion_comparison",
              "created_local": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
              "manifest": str(args.manifest), "manifest_sha256": sha(args.manifest),
              "plan_sha256": sha(plan_path), "geometry_sha256": sha(geometry_path),
              "analysis_script_sha256": sha(Path(__file__)),
              "helper_script_sha256": {"summarize": sha(ROOT / "reproduction/summarize-stair-night2.py"),
                                       "motion": sha(ROOT / "reproduction/analyze-stair-motion.py")},
              "training_identities": identities, "sources": sources, "cases": cases,
              "counts": {"case_speed_seed_rows": len(cases), "competent_matched_rows": len(eligible),
                         "diagnostic_only_rows": len(cases) - len(eligible),
                         "baseline_numerically_failed_rows": sum(not row["baseline_gate"]["numeric_acceptance_passed"] for row in cases),
                         "candidate_numerically_failed_rows": sum(not row["candidate_gate"]["numeric_acceptance_passed"] for row in cases)},
              "eligible_case_direction_counts": directions,
              "pooled_contact_automatic_acceptance": False, "smoothness_certified": False,
              "paper_superiority_certified": False, "reserved_final_replaced": False,
              "limitations": ["Default external yaw feedback development cases only, not zero-yaw or reserved final.",
                              "Initial xyz arrays match; only initial yaw/quaternion distribution summaries saved, not full per-environment initial quaternions.",
                              "Per-body forces are one representative environment per case, whereas case metrics include all32 environments.",
                              "Legacy shank metric includes thigh and calf bodies, not calf-only contacts.",
                              "Current force at20ms boundary does not measure all substeps or continuous contact duration.",
                              "One training seed, deterministic nominal physics construction; no multi-seed reward-effect significance claim.",
                              "No videos are reviewed or certified by this CPU summary."]}
    args.output.with_suffix(".json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    write_markdown(report, args.output.with_suffix(".md"))
    print(json.dumps({"counts": report["counts"], "source_errors": source_errors,
                      "motion_directions": {field: directions[field] for field in METRICS[:8]}}))


if __name__ == "__main__":
    main()
