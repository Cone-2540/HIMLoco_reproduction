#!/usr/bin/env python3
"""Summarize recorded staircase evaluations using only the Python standard library.

Example (no simulator, CUDA, checkpoint loading, or model selection):
  python3 reproduction/summarize-stair-evaluations.py \
    isaaclab/logs/<evaluation-run> isaaclab/logs/<another-run> \
    --output /tmp/stair-comparison

Writes PREFIX.json, PREFIX.csv and PREFIX.md. Each CSV row is one case and
reset seed. JSON/Markdown also show pooled case completion AND the minimum
seed completion, including failed cases. Existing evaluation/final-acceptance
thresholds and decisions are copied, never changed or recomputed.

result.json supersedes an identical primary-result.json. Candidate references
are followed and candidate directories are scanned, with deduplication by
resolved result-file path. Container candidate paths are resolved against the
local run's candidates/ directory. Different runs are never merged merely
because they evaluate the same checkpoint. Missing referenced results or
conflicting primary reports are errors, not silently omitted experiments.
"""

import argparse
import csv
import json
import math
from pathlib import Path


COUNT_FIELDS = ("completions", "falls", "stalls", "lateral_escapes", "base_contact_envs")
GEOMETRY_FIELDS = ("direction", "step_height", "step_depth", "num_steps", "width", "nosing",
                   "landing_length", "first_riser_x", "last_riser_x", "goal_platform_start_x",
                   "goal_x", "goal_platform_z", "goal_dwell_s")
METRIC_FIELDS = ("flight_pause_fraction", "longest_flight_pause_s", "measured_vx_m_s",
                 "action_second_delta_rms", "pitch_rms_rad", "roll_rms_rad",
                 "torque_saturation_fraction", "base_contact_step_fraction")


def read_json(path):
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object: " + str(path))
    return value


def canonical_result(path):
    """Choose one primary result, but refuse to hide conflicting measurements."""
    path = path.resolve()
    if not path.exists():
        raise ValueError("Evaluation input does not exist: " + str(path))
    directory = path if path.is_dir() else path.parent
    result, primary = directory / "result.json", directory / "primary-result.json"
    if path.is_file() and path.name not in ("result.json", "primary-result.json"):
        return path, []
    aliases = []
    if result.exists() and primary.exists():
        left, right = read_json(result), read_json(primary)
        for key in set(left) | set(right):
            if key in ("additional_candidates", "export_max_abs_error"):
                continue
            if key not in left or key not in right or left[key] != right[key]:
                raise ValueError("Conflicting result.json/primary-result.json field %r in %s" % (key, directory))
        aliases.append(str(primary.resolve()))
    chosen = result if result.exists() else primary
    if not chosen.is_file():
        raise ValueError("No result.json or primary-result.json in " + str(directory))
    return chosen.resolve(), aliases


def config_for(directory):
    """Candidate exports share their parent evaluation config unless overridden."""
    direct = directory / "config.json"
    if direct.exists():
        return read_json(direct), direct, False
    for parent in directory.parents:
        if parent.name == "candidates":
            inherited = parent.parent / "config.json"
            if inherited.exists():
                return read_json(inherited), inherited, True
            break
    return {}, None, False


def candidate_result(run_directory, reference):
    location = reference.get("result_directory")
    if not location:
        raise ValueError("Candidate reference lacks result_directory in " + str(run_directory))
    candidate = Path(location)
    options = []
    # /workspace/himloco/.../candidates/X is an exported container path.
    if "candidates" in candidate.parts:
        index = candidate.parts.index("candidates")
        options.append(run_directory.joinpath(*candidate.parts[index:]))
    if not candidate.is_absolute():
        options.append(run_directory / candidate)
    options.append(candidate)
    for option in options:
        if option.is_dir() and ((option / "result.json").exists() or (option / "primary-result.json").exists()):
            return option
        if option.is_file():
            return option
    raise ValueError("Referenced candidate result is missing: %s (run %s)" % (location, run_directory))


def discover(inputs):
    queue = [(path, None) for path in inputs]
    seen, documents = set(), []
    while queue:
        requested, checkpoint_hint = queue.pop(0)
        path, aliases = canonical_result(requested)
        if path in seen:
            continue
        seen.add(path)
        source = read_json(path)
        config, config_path, inherited = config_for(path.parent)
        checkpoint = source.get("checkpoint") or checkpoint_hint or config.get("checkpoint")
        if checkpoint_hint and source.get("checkpoint") and checkpoint_hint != source["checkpoint"]:
            raise ValueError("Candidate checkpoint reference disagrees with " + str(path))
        documents.append({"path": path, "aliases": aliases, "source": source,
                          "config": config, "config_path": config_path, "inherited_config": inherited,
                          "checkpoint": checkpoint,
                          "checkpoint_source": "result" if source.get("checkpoint") else
                          "candidate_reference" if checkpoint_hint else "config" if checkpoint else "unavailable"})
        for reference in source.get("additional_candidates", []):
            queue.append((candidate_result(path.parent, reference), reference.get("checkpoint")))
        candidates = path.parent / "candidates"
        if candidates.is_dir():
            directories = {file.parent for name in ("result.json", "primary-result.json")
                           for file in candidates.rglob(name)}
            queue.extend((directory, None) for directory in sorted(directories))
    return documents


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def minimum(values):
    # Unknown/missing observations must not yield an optimistic minimum.
    return min(values) if values and all(number(value) for value in values) else None


def maximum(values):
    return max(values) if values and all(number(value) for value in values) else None


def totals(rows):
    result = {}
    for key in ("num_envs",) + COUNT_FIELDS:
        values = [row.get(key) for row in rows]
        result[key] = sum(values) if values and all(number(value) for value in values) else None
    result["completion_fraction"] = (result["completions"] / result["num_envs"]
                                      if result["num_envs"] and result["completions"] is not None else None)
    return result


def summarize_rows(rows):
    result = totals(rows)
    fractions = [row.get("completion_fraction") for row in rows]
    worst = minimum(fractions)
    result.update({"minimum_seed_completion_fraction": worst,
                   "worst_completion_seeds": [row["seed"] for row in rows
                                              if worst is not None and row.get("completion_fraction") == worst],
                   "maximum_seed_failure_fractions": {
                       key: maximum([row[key] / row["num_envs"] if row.get(key) is not None
                                     and row.get("num_envs") else None for row in rows])
                       for key in COUNT_FIELDS[1:]},
                   "maximum_flight_pause_s": maximum([row.get("longest_flight_pause_s") for row in rows]),
                   "observations_complete": all(row["observation_available"] for row in rows)})
    return result


def material_scope(report, config):
    domain = config.get("domain_randomization")
    domain = domain if isinstance(domain, dict) else {}
    foot, terrain = domain.get("foot_material"), domain.get("terrain_material")
    return {"domain_randomization_profile": domain.get("profile"),
            "foot_material": foot, "terrain_material": terrain,
            "friction_override": config.get("friction_override"),
            "parameter_scope": ("Recorded material configuration; see foot/terrain/override fields"
                                if foot or terrain or config.get("friction_override") is not None else
                                "Material parameter ranges not recorded; inherited environment materials are unknown"),
            "seed_scope": report.get("seed_scope", "Startup material resampling scope not recorded")}


def summarize(document, controller):
    source, config = document["source"], document["config"]
    report = source.get(controller)
    if report is None and controller == "policy" and "trials" in source:
        report = source
    if not isinstance(report, dict) or not isinstance(report.get("trials"), list) or not report["trials"]:
        raise ValueError("No staircase %s trials in %s" % (controller, document["path"]))
    geometry = report.get("geometry", source.get("geometry", {}))
    geometries = geometry if isinstance(geometry, list) else [geometry]
    if not geometries or not all(isinstance(g, dict) and g.get("direction") in ("asc", "desc") for g in geometries):
        raise ValueError("Expected staircase geometry, not flat/training results: " + str(document["path"]))
    acceptance = source.get("final_acceptance", {}) if controller == "policy" else {}
    acceptance_cases = {(case.get("seed"), case.get("case_index", 0)): case
                        for case in acceptance.get("cases", [])}
    rows, trial_diagnostics, seeds = [], [], []
    for trial in report["trials"]:
        seed = trial.get("seed")
        if seed in seeds:
            raise ValueError("Duplicate reset seed %r in %s" % (seed, document["path"]))
        seeds.append(seed)
        cases = trial.get("cases")
        if cases is None:
            cases = [dict(trial, case_index=0)] if len(geometries) == 1 else []
        by_index = {}
        for ordinal, case in enumerate(cases):
            index = case.get("case_index", ordinal)
            if index in by_index or index not in range(len(geometries)):
                raise ValueError("Duplicate/out-of-range case_index %r in %s" % (index, document["path"]))
            by_index[index] = case
        for index, expected_geometry in enumerate(geometries):
            case = by_index.get(index)
            metrics = case.get("metrics", {}) if case else {}
            row = {"case_index": index, "seed": seed, "observation_available": case is not None,
                   "geometry": {key: expected_geometry.get(key) for key in GEOMETRY_FIELDS},
                   "requested_duration_s": trial.get("requested_duration_s"),
                   "num_envs": case.get("num_envs") if case else None,
                   "reported_passed": case.get("passed") if case else None,
                   "failure_reason": trial.get("failure_reason") if case else "Case observations missing",
                   "final_acceptance": acceptance_cases.get((seed, index)),
                   **{key: case.get(key) if case else None for key in COUNT_FIELDS},
                   **{key: metrics.get(key) for key in METRIC_FIELDS},
                   "mean_max_progress_m": case.get("mean_max_progress_m",
                       case.get("mean_max_directed_progress_m")) if case else None}
            row["completion_fraction"] = (row["completions"] / row["num_envs"]
                                           if row["num_envs"] and row["completions"] is not None else None)
            if case and case.get("completion_fraction") is not None:
                recorded = case["completion_fraction"]
                if row["completion_fraction"] is not None and abs(recorded - row["completion_fraction"]) > 1e-6:
                    raise ValueError("Completion count/fraction disagreement in " + str(document["path"]))
                row["completion_fraction"] = row["completion_fraction"] if row["completion_fraction"] is not None else recorded
            rows.append(row)
        trial_diagnostics.append({"seed": seed, **{key: trial.get(key) for key in (
            "nonfinite_envs", "invalid_physics_envs", "invalid_start_envs", "timeouts_before_completion", "failure_reason")}})
    configured_seeds = config.get("evaluation_seeds") or []
    missing_seeds = [seed for seed in configured_seeds if seed not in seeds]
    # Keep absent configured trials visible in every export. Their unknown
    # observations must not produce an optimistic case or direction minimum.
    for seed in missing_seeds:
        for index, expected_geometry in enumerate(geometries):
            rows.append({"case_index": index, "seed": seed, "observation_available": False,
                         "geometry": {key: expected_geometry.get(key) for key in GEOMETRY_FIELDS},
                         "requested_duration_s": None, "num_envs": None,
                         "reported_passed": None, "failure_reason": "Configured reset seed observations missing",
                         "final_acceptance": None, "completion_fraction": None, "mean_max_progress_m": None,
                         **{key: None for key in COUNT_FIELDS + METRIC_FIELDS}})
    case_summaries = []
    for index in range(len(geometries)):
        selected = [row for row in rows if row["case_index"] == index]
        case_summaries.append({"case_index": index, "geometry": selected[0]["geometry"],
                               **summarize_rows(selected)})
    directions = []
    for direction in sorted({g["direction"] for g in geometries}):
        selected_rows = [row for row in rows if row["geometry"]["direction"] == direction]
        selected_cases = [case for case in case_summaries if case["geometry"]["direction"] == direction]
        directions.append({"direction": direction, **totals(selected_rows),
                           "minimum_case_completion_fraction": minimum([case["completion_fraction"] for case in selected_cases]),
                           "minimum_case_seed_completion_fraction": minimum([row["completion_fraction"] for row in selected_rows])})
    return {"evaluation_id": str(document["path"].parent) + ":" + controller,
            "run_directory": str(document["path"].parent), "result_file": str(document["path"]),
            "alternate_result_files": document["aliases"], "checkpoint": document["checkpoint"],
            "checkpoint_source": document["checkpoint_source"], "controller": controller,
            "config_file": str(document["config_path"]) if document["config_path"] else None,
            "config_inherited_from_parent_run": document["inherited_config"],
            "status": report.get("status", source.get("status")), "reported_passed": report.get("passed"),
            "reported_final_traversal_passed": acceptance.get("traversal_passed"),
            "thresholds": {"evaluation": report.get("thresholds"), "final_acceptance": acceptance.get("thresholds")},
            "scope": {"command_forward_speed_m_s": report.get("command_forward_speed_m_s"),
                      "randomized_reset": report.get("randomized_reset", config.get("evaluation_randomized")),
                      "dynamics_randomized": report.get("dynamics_randomized", config.get("evaluation_dynamics_randomized")),
                      "independent_reset_validation_eligible": report.get("independent_reset_validation_eligible"),
                      "heading_control": report.get("heading_control"),
                      "validation_scope": report.get("validation_scope"), "metrics_scope": report.get("metrics_scope"),
                      "seed_scope": report.get("seed_scope"), "recorded_reset_seeds": seeds,
                      "configured_reset_seeds": configured_seeds, "missing_configured_reset_seeds": missing_seeds,
                      "material": material_scope(report, config)},
            "observations_complete": not missing_seeds and all(row["observation_available"] for row in rows),
            "minimum_case_completion_fraction": minimum([case["completion_fraction"] for case in case_summaries]),
            "minimum_case_seed_completion_fraction": minimum([row["completion_fraction"] for row in rows]),
            "case_summaries": case_summaries, "direction_summaries": directions,
            "trial_diagnostics": trial_diagnostics, "case_seed_results": rows}


def csv_rows(evaluations):
    for evaluation in evaluations:
        scope = evaluation["scope"]
        for row in evaluation["case_seed_results"]:
            flat = {key: evaluation[key] for key in ("evaluation_id", "result_file", "checkpoint", "controller",
                    "observations_complete", "minimum_case_completion_fraction", "minimum_case_seed_completion_fraction")}
            flat.update({key: scope[key] for key in ("command_forward_speed_m_s", "randomized_reset", "dynamics_randomized",
                         "independent_reset_validation_eligible", "validation_scope", "seed_scope")})
            flat["material_scope_json"] = json.dumps(scope["material"], separators=(",", ":"), sort_keys=True)
            flat["missing_configured_reset_seeds_json"] = json.dumps(scope["missing_configured_reset_seeds"])
            flat.update({key: value for key, value in row.items() if key not in ("geometry", "final_acceptance")})
            flat.update(row["geometry"])
            final = row["final_acceptance"] or {}
            flat["reported_final_traversal_passed"] = final.get("traversal_passed")
            flat["reported_motion_improvement_needed"] = final.get("motion_improvement_needed")
            flat["evaluation_thresholds_json"] = json.dumps(evaluation["thresholds"], separators=(",", ":"), sort_keys=True)
            yield flat


def cell(value):
    return "—" if value is None else str(value).replace("|", "\\|").replace("\n", " ")


def percent(value):
    return "—" if value is None else "%.2f%%" % (100 * value)


def markdown(evaluations):
    lines = ["# Recorded staircase evaluations", "",
             "No models are selected and no thresholds are changed. Pooled completion counts all recorded",
             "environments; minimum case/seed completion preserves the worst reset seed. A direction total",
             "does not replace individual cases. Missing metrics remain unavailable. Material settings are",
             "only reported when recorded; reset seeds do not imply fresh startup material samples.", ""]
    for ordinal, evaluation in enumerate(evaluations, 1):
        scope = evaluation["scope"]
        lines.extend(["## %d. %s (%s)" % (ordinal, Path(evaluation["run_directory"]).name, evaluation["controller"]), "",
                      "- Result: `%s`" % evaluation["result_file"],
                      "- Checkpoint: `%s` (source: %s)" % (cell(evaluation["checkpoint"]), evaluation["checkpoint_source"]),
                      "- Speed: %s m/s; reset randomized: %s; dynamics randomized: %s; independent reset validation eligible: %s." %
                      tuple(cell(scope[key]) for key in ("command_forward_speed_m_s", "randomized_reset", "dynamics_randomized", "independent_reset_validation_eligible")),
                      "- Minimum pooled case completion: %s; minimum case/seed completion: %s; observations complete: %s." %
                      (percent(evaluation["minimum_case_completion_fraction"]), percent(evaluation["minimum_case_seed_completion_fraction"]), evaluation["observations_complete"]),
                      "- Reported evaluation passed: %s; reported final traversal passed: %s." %
                      (cell(evaluation["reported_passed"]), cell(evaluation["reported_final_traversal_passed"])),
                      "- Validation scope: %s" % cell(scope["validation_scope"]),
                      "- Recorded reset seeds: %s; missing configured reset seeds: %s." %
                      (scope["recorded_reset_seeds"], scope["missing_configured_reset_seeds"]),
                      "- Seed/material sampling scope: %s" % cell(scope["material"]["seed_scope"]),
                      "- Material configuration: `%s`" % json.dumps(scope["material"], separators=(",", ":"), sort_keys=True),
                      "- Recorded thresholds: `%s`" % json.dumps(evaluation["thresholds"], separators=(",", ":"), sort_keys=True), "",
                      "| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |",
                      "|---|---|---|---|---|---|---|---|---|---|---|---|---|"])
        for row in evaluation["case_seed_results"]:
            g, final = row["geometry"], row["final_acceptance"] or {}
            values = [row["case_index"], g["direction"], "%s / %s" % (cell(g["step_height"]), cell(g["step_depth"])),
                      row["seed"], "%s / %s" % (cell(row["completions"]), cell(row["num_envs"])), percent(row["completion_fraction"]),
                      row["falls"], row["stalls"], row["lateral_escapes"], row["base_contact_envs"],
                      percent(row["flight_pause_fraction"]), "%.3f" % row["longest_flight_pause_s"] if number(row["longest_flight_pause_s"]) else None,
                      final.get("traversal_passed")]
            lines.append("| " + " | ".join(cell(value) for value in values) + " |")
        lines.extend(["", "| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |",
                      "|---|---|---|---|---|---|---|---|---|"])
        for case in evaluation["case_summaries"]:
            failure = case["maximum_seed_failure_fractions"]
            values = [case["case_index"], percent(case["completion_fraction"]), percent(case["minimum_seed_completion_fraction"]),
                      ", ".join(str(seed) for seed in case["worst_completion_seeds"]),
                      *[percent(failure[key]) for key in COUNT_FIELDS[1:]],
                      "%.3f" % case["maximum_flight_pause_s"] if number(case["maximum_flight_pause_s"]) else None]
            lines.append("| " + " | ".join(cell(value) for value in values) + " |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", type=Path, nargs="+", help="Evaluation run directories or result JSON files")
    parser.add_argument("--output", type=Path, required=True, help="Prefix for JSON/CSV/Markdown outputs")
    parser.add_argument("--include-zero-action", action="store_true", help="Also export recorded controls, separately from policy")
    args = parser.parse_args()
    try:
        evaluations = []
        for document in discover(args.runs):
            evaluations.append(summarize(document, "policy"))
            if args.include_zero_action and document["source"].get("zero_action"):
                evaluations.append(summarize(document, "zero_action"))
        summary = {"schema_version": 1, "inputs": [str(path.resolve()) for path in args.runs],
                   "aggregation_scope": "Each evaluation retains its checkpoint, command speed, controller, cases and reset seeds. Pooled counts are descriptive; minima preserve worst cases/seeds. No model selection or threshold changes.",
                   "evaluations": evaluations}
        prefix = args.output
        prefix.parent.mkdir(parents=True, exist_ok=True)
        paths = {extension: Path(str(prefix) + "." + extension) for extension in ("json", "csv", "md")}
        paths["json"].write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        rows = list(csv_rows(evaluations))
        with paths["csv"].open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        paths["md"].write_text(markdown(evaluations), encoding="utf-8")
        print(json.dumps({"evaluations": len(evaluations), "case_seed_rows": len(rows),
                          "outputs": {key: str(path) for key, path in paths.items()}}, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, "error: %s\n" % error)


if __name__ == "__main__":
    main()
