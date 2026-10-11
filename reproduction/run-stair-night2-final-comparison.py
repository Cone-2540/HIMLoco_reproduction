#!/usr/bin/env python3
"""Collect the fixed final matrix for one explicitly frozen night-two policy.

Default dry-run validates identities and prints four commands without Docker.
Only --execute starts simulation. No candidate selection, threshold changes,
training, final-result globbing, or automatic retry is implemented here.
"""

import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import secrets
import shlex
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "night2_development_backend", ROOT / "reproduction/run-stair-night2-development-comparison.py")
backend = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backend)
ZONE, DEADLINE = backend.ZONE, backend.DEADLINE
SOURCE_FILES = (*backend.SOURCE_FILES, "isaaclab/stair_randomization.py")
WORKFLOW_FILES = (
    "isaaclab/run.sh", "isaaclab/compose.override.yaml", "reproduction/run-stair-night2-job.py",
    "reproduction/run-stair-night2-development-comparison.py",
    "reproduction/run-stair-night2-final-comparison.py",
    "reproduction/summarize-stair-night2.py",
)
PROTOCOL_FILES = {
    "evaluation_plan": ("reproduction/stair-night2-evaluation-plan.json",
        "03e854ebc1b9575abe99364bb8c89156fc3b40400b40ebc4bb86e0e44d31d418"),
    "development_geometry": ("reproduction/stair-night2-development-geometries.json",
        "dd98558974995a8c409491c11aef6a89be2e0953813a76412cb088279a322a98"),
    "final_geometry": ("reproduction/stair-night2-final-geometries.json",
        "51d698a9a4a18b8b7d31af68fb7b69490d80ea07c02785085544e3f818c3933b"),
}
BASELINE_PATH = "artifacts/go2-stairs-control660/model_660.pt"
SEEDS, SPEEDS = [907, 911, 919], [0.3, 0.5]
require, digest, read = backend.require, backend.digest, backend.read


def explicit_file(value):
    require(isinstance(value, str) and bool(value), "An explicit file path is required")
    path = Path(value).expanduser()
    path = path if path.is_absolute() else ROOT / path
    path = path.resolve(strict=True)
    require(path.is_file(), "Not a file: " + str(path))
    return path


def git_output(arguments, *, binary=False):
    result = subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True,
                            text=not binary, timeout=20)
    require(result.returncode == 0, "Git identity check failed")
    return result.stdout


def source_identity():
    names = (*SOURCE_FILES, *WORKFLOW_FILES)
    require(not git_output(["status", "--porcelain", "--", *names]).strip(),
            "Runtime/evaluation code must be committed and clean before freeze")
    commit = git_output(["rev-parse", "HEAD"]).strip()
    return {"git_commit": commit, "code_files_clean": True,
            "runtime_sha256": {name: digest(ROOT / name) for name in SOURCE_FILES},
            "workflow_sha256": {name: digest(ROOT / name) for name in WORKFLOW_FILES},
            "commit_scope": "Data-only later commits are allowed; every declared runtime/workflow file must match this commit and the frozen content hashes."}


def protocol_identity():
    return {key: {"file": name, "sha256": expected}
            for key, (name, expected) in PROTOCOL_FILES.items()}


def validate_source(source):
    require(isinstance(source, dict) and source.get("code_files_clean") is True,
            "Freeze must declare clean runtime/evaluation code")
    commit = source.get("git_commit", "")
    require(isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit),
            "Freeze requires a full source Git commit")
    git_output(["cat-file", "-e", commit + "^{commit}"])
    for field, names in (("runtime_sha256", SOURCE_FILES), ("workflow_sha256", WORKFLOW_FILES)):
        hashes = source.get(field)
        require(isinstance(hashes, dict) and set(hashes) == set(names),
                "Freeze has missing/unexpected source files: " + field)
        for name in names:
            require(hashes[name] == digest(ROOT / name), "Code changed after freeze: " + name)
            committed = git_output(["show", commit + ":" + name], binary=True)
            require(hashlib.sha256(committed).hexdigest() == hashes[name],
                    "Frozen source hash does not match declared commit: " + name)
    require(not git_output(["status", "--porcelain", "--", *SOURCE_FILES, *WORKFLOW_FILES]).strip(),
            "Runtime/evaluation code is dirty after freeze")


def validate_protocol(protocol):
    require(isinstance(protocol, dict) and set(protocol) == set(PROTOCOL_FILES),
            "Freeze must bind evaluation plan and both geometry files")
    for key, (name, expected) in PROTOCOL_FILES.items():
        require(protocol[key] == {"file": name, "sha256": expected},
                "Freeze differs from preregistered protocol: " + key)
        require(digest(ROOT / name) == expected, "Preregistered protocol file changed: " + name)


def validate_development_evidence(evidence, selected):
    require(isinstance(evidence, dict), "Explicit development summary evidence is required")
    path = explicit_file(evidence.get("summary_file"))
    require(evidence.get("sha256") == digest(path), "Development summary hash mismatch")
    summary = read(path)
    require(summary.get("split") == "development", "Selection evidence must be development, never final")
    require(summary.get("checkpoint_sha256") == selected["checkpoint_sha256"],
            "Selection evidence belongs to another checkpoint")
    require(summary.get("plan_sha256") == PROTOCOL_FILES["evaluation_plan"][1]
            and summary.get("geometry_sha256") == PROTOCOL_FILES["development_geometry"][1],
            "Development evidence belongs to a different protocol")
    require(not summary.get("duplicate_case_seed_speed_controller_rows"), "Duplicate development evidence rows")
    controllers = [row for row in summary.get("controllers", [])
                   if row.get("heading_control_enabled") is True]
    require(len(controllers) == 1 and controllers[0].get("matrix_complete") is True,
            "Selection requires the complete default-heading development matrix")
    rows = [row for row in summary.get("cases", []) if row.get("heading_control_enabled") is True]
    expected = {(i, seed, speed) for i in range(18) for seed in [11, 29, 47] for speed in SPEEDS}
    observed = {(row.get("case_index"), row.get("reset_seed"), row.get("speed_m_s")) for row in rows}
    require(len(rows) == 108 and observed == expected,
            "Development evidence must include all 18 cases, three seeds and both speeds")
    require(all(row.get("source_protocol_verified") is True for row in rows),
            "Development evidence has unverified source/protocol rows")
    # A root may freeze a limited claim even if long development stairs failed.
    # This runner preserves that failure and never promotes/selects on its own.
    return {"summary_file": str(path), "sha256": digest(path),
            "heading_numeric_verdict": controllers[0].get("numeric_verdict"),
            "no_pass_or_smoothness_inferred_by_freeze": True}


def selection_payload(checkpoint, profile, development_summary, reason, label="selected"):
    """Pure CPU helper for a root-selected policy; returns JSON, writes nothing."""
    selected = backend.archive_identity(label, profile, checkpoint)
    summary_path = explicit_file(development_summary)
    value = {"schema_version": 1, "status": "frozen_before_final",
             "created_local": datetime.now(ZONE).isoformat(),
             "selection_basis": "development_only", "no_final_evidence_used": True,
             "selection_reason": reason, "selected": selected,
             "baseline": {"label": "baseline-control660", "checkpoint": BASELINE_PATH,
                          "checkpoint_sha256": backend.EXPECTED_ORIGIN_SHA256,
                          "training_reward_profile": "contact"},
             "source": source_identity(), "protocol": protocol_identity(),
             "development_evidence": {"summary_file": str(summary_path), "sha256": digest(summary_path)},
             "automatic_candidate_selection": False, "retuning_from_final_allowed": False}
    validate_selection_value(value)
    return value


def validate_selection_value(value):
    require(isinstance(value, dict) and value.get("schema_version") == 1
            and value.get("status") == "frozen_before_final", "Selection is not a completed pre-final freeze")
    require(value.get("selection_basis") == "development_only" and value.get("no_final_evidence_used") is True,
            "Freeze must declare selection from development only")
    require(value.get("automatic_candidate_selection") is False and value.get("retuning_from_final_allowed") is False,
            "Freeze must prohibit automatic selection and retuning from final")
    require(isinstance(value.get("selection_reason"), str) and value["selection_reason"].strip(),
            "Root's explicit development selection reason is required")
    created = datetime.fromisoformat(value.get("created_local", ""))
    require(created.tzinfo is not None and created <= datetime.now(ZONE), "Invalid/future freeze time")
    selected = value.get("selected")
    require(isinstance(selected, dict), "Exactly one selected archive identity is required")
    current = backend.archive_identity(selected.get("label"), selected.get("training_reward_profile"),
                                       selected.get("checkpoint"))
    require(selected == current, "Frozen selected identity differs from actual archived model/config/audit")
    baseline = {"label": "baseline-control660", "checkpoint": BASELINE_PATH,
                "checkpoint_sha256": backend.EXPECTED_ORIGIN_SHA256, "training_reward_profile": "contact"}
    require(selected["label"] != baseline["label"], "Selected label must differ from baseline summary label")
    require(value.get("baseline") == baseline, "Freeze must retain the fixed control660 baseline")
    require(digest(ROOT / BASELINE_PATH) == baseline["checkpoint_sha256"], "Baseline checkpoint changed")
    require(selected["checkpoint_sha256"] != baseline["checkpoint_sha256"], "Selected model equals baseline")
    validate_source(value.get("source"))
    validate_protocol(value.get("protocol"))
    evidence = validate_development_evidence(value.get("development_evidence"), selected)
    return {"selected": current, "baseline": baseline, "development_evidence": evidence}


def planned_jobs(baseline, selected, prefix):
    jobs = []
    for speed in SPEEDS:
        for heading in [True, False]:
            name = prefix + ("-speed03" if speed == 0.3 else "-speed05") + ("-heading" if heading else "-zero-yaw")
            forwarded = ["evaluate", "--terrain", "stairs", "--checkpoint", baseline["checkpoint"],
                         "--reward_profile", "contact", "--stair_batch", PROTOCOL_FILES["final_geometry"][0],
                         "--num_envs", "512", "--speed", str(speed), "--eval_seconds", "40", "--eval_randomized",
                         "--seed", "1", "--domain_profile", "none", "--eval_trace_stride", "1"]
            for seed in SEEDS:
                forwarded += ["--eval_seed", str(seed)]
            forwarded += ["--candidate_checkpoint", selected["checkpoint"]]
            if not heading:
                forwarded.append("--open_loop_heading")
            command = [sys.executable, str(ROOT / "reproduction/run-stair-night2-job.py"), "--name", name,
                       "--max-seconds", "3000", "--", *forwarded]
            jobs.append({"name": name, "speed_m_s": speed, "heading_control_enabled": heading,
                         "wrapper_argv": command, "shell_command": shlex.join(command)})
    return jobs


def summarize_policy(identity, candidate, records, output):
    paths = []
    for record in records:
        directory = Path(record["simulator_directory"])
        if candidate:
            directory /= "candidates/0_" + Path(identity["checkpoint"]).stem
        path = directory / "result.json"
        require(path.is_file(), "Explicit final result missing: " + str(path))
        paths.append(path)
    prefix = output / (identity["label"] + "-final-summary")
    result = subprocess.run([sys.executable, str(ROOT / "reproduction/summarize-stair-night2.py"),
                             *map(str, paths), "--stage", "final", "--output", str(prefix)],
                            cwd=ROOT, capture_output=True, text=True, timeout=240)
    require(result.returncode == 0, "Final CPU summary failed: " + result.stderr)
    summary = read(prefix.with_suffix(".json"))
    require(summary["checkpoint_sha256"] == identity["checkpoint_sha256"], "Final summary model hash mismatch")
    controllers = summary["controllers"]
    require(len(controllers) == 2 and {c["heading_control_enabled"] for c in controllers} == {True, False},
            "Both final controllers must receive separate reports")
    require(summary["complete_declared_numeric_protocol"] is True
            and all(c["matrix_complete"] is True for c in controllers),
            "Final protocol incomplete; preserve outputs without claiming complete collection")
    sidecar = {"status": "final_collection_completed_training_identity_attached", "identity": identity,
               "shared_evaluation_reward_profile": "contact", "source_result_paths": list(map(str, paths)),
               "raw_result_sha256": {str(p): digest(p) for p in paths},
               "summary": str(prefix.with_suffix(".json")), "summary_sha256": digest(prefix.with_suffix(".json")),
               "training_profile_scope": "Candidate archive identity records its actual training profile; raw shared scene reward label belongs to baseline construction.",
               "automatic_selection_performed": False, "smoothness_visual_judgment_performed": False}
    sidecar_path = output / (identity["label"] + "-training-identity.json")
    backend.save_json_exclusive(sidecar_path, sidecar)
    print(result.stdout.strip(), flush=True)
    return {"label": identity["label"], "summary": str(prefix.with_suffix(".json")),
            "training_identity": str(sidecar_path), "controller_numeric_verdicts": controllers}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-file", required=True, help="Explicit root-created pre-final freeze JSON")
    parser.add_argument("--output-dir", type=Path, help="New exclusive output directory; dry-run writes only when supplied")
    parser.add_argument("--container", default="isaaclab-local-lab-1")
    parser.add_argument("--execute", action="store_true", help="Run the four fixed scenes; default prints commands only")
    args = parser.parse_args()
    output, records, active_job = None, [], None
    try:
        require(args.container == "isaaclab-local-lab-1", "Existing wrapper uses fixed isaaclab-local-lab-1")
        selection_path = explicit_file(args.selection_file)
        selection_hash = digest(selection_path)
        selection = read(selection_path)
        identities = validate_selection_value(selection)
        unique = datetime.now(ZONE).strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
        prefix = "night2-finalcompare-" + unique
        jobs = planned_jobs(identities["baseline"], identities["selected"], prefix)
        if args.execute:
            require(datetime.now(ZONE) < DEADLINE, "Authorized deadline has passed")
            initial_idle = backend.container_idle(args.container)
        else:
            initial_idle = {"status": "not_checked_in_dry_run", "docker_contacted": False}
        planned_output = args.output_dir.expanduser().resolve() if args.output_dir else Path.home() / "robotics/logs" / prefix
        manifest = {"schema_version": 1, "created_local": datetime.now(ZONE).isoformat(), "stage": "final",
                    "status": "immutable_launch_plan" if args.execute else "dry_run_not_executed",
                    "selection_file": str(selection_path), "selection_sha256": selection_hash,
                    "selection": selection, "baseline": identities["baseline"], "selected": identities["selected"],
                    "geometry_cases": 16, "num_envs": 512, "reset_seeds": SEEDS, "speeds": SPEEDS,
                    "controllers": ["default_heading_feedback", "constant_zero_yaw_command"],
                    "construction_seed": 1, "seconds": 40, "trace_stride": 1, "eval_dynamics": False,
                    "jobs": jobs, "deadline_local": DEADLINE.isoformat(), "per_scene_max_seconds": 3000,
                    "initial_container_idle_check": initial_idle, "common_evaluation_reward_profile": "contact",
                    "automatic_candidate_selection": False, "retuning_from_final_allowed": False,
                    "scientific_acceptance": "Independent numeric and motion review required; collection exit0 is not PASS"}
        if args.execute or args.output_dir:
            planned_output.mkdir(parents=True, exist_ok=False)
            output = planned_output
            backend.save_json_exclusive(output / "immutable-manifest.json", manifest)
            (output / "immutable-manifest.json").chmod(0o444)
            shutil.copyfile(selection_path, output / "selection-freeze.json")
            require(digest(output / "selection-freeze.json") == selection_hash, "Freeze copy changed during preparation")
            (output / "selection-freeze.json").chmod(0o444)
        print("COMPARISON_DIR: " + str(planned_output), flush=True)
        if not args.execute:
            for job in jobs:
                print(job["shell_command"])
            print(json.dumps({"status": "dry_run_not_executed", "jobs": 4, "selected_models": 1,
                              "docker_contacted": False, "final_result_read": False,
                              "manifest": str(output / "immutable-manifest.json") if output else None}))
            return
        for job in jobs:
            active_job = job["name"]
            require(datetime.now(ZONE) < DEADLINE, "Authorized deadline reached before next scene")
            require(digest(selection_path) == selection_hash, "Original selection changed after freeze")
            validate_selection_value(selection)
            idle = backend.container_idle(args.container)
            record = backend.execute_job(job, output)
            record["pre_scene_idle_check"] = idle
            record["selection_sha256"] = selection_hash
            records.append(record)
            backend.save_json_exclusive(output / (job["name"] + "-completion.json"), record)
            backend.container_idle(args.container)
        active_job = "cpu_summaries"
        require(digest(selection_path) == selection_hash, "Original selection changed during collection")
        validate_selection_value(selection)
        policies = [summarize_policy(identities["baseline"], False, records, output),
                    summarize_policy(identities["selected"], True, records, output)]
        backend.save_json_exclusive(output / "comparison-completion.json", {
            "status": "final_collection_and_separate_cpu_summaries_completed", "records": records,
            "policies": policies, "selection_sha256": selection_hash,
            "immutable_manifest_sha256": digest(output / "immutable-manifest.json"),
            "automatic_candidate_selection": False, "retuning_from_final_allowed": False,
            "scientific_acceptance": "Root must report separate controller verdicts and review complete motion evidence"})
        print(json.dumps({"status": "final_collection_and_separate_cpu_summaries_completed",
                          "directory": str(output), "policy_summaries": 2}), flush=True)
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        if args.execute and output is not None:
            backend.save_json_exclusive(output / "comparison-failure.json", {
                "status": "stopped_preserve_final_evidence_no_automatic_retry", "failed_stage": active_job,
                "error": str(error), "completed_records": records,
                "scientific_acceptance": "INCOMPLETE or FAIL; never promote from an interrupted matrix"})
        parser.error(str(error))


if __name__ == "__main__":
    main()
