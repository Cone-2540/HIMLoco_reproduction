#!/usr/bin/env python3
"""Independent round3 reward comparison with a narrowly bound source proof.

Default dry run never contacts Docker. --execute requires complete archives,
the actual CPU source proof, clean committed source, an exclusive launch plan,
the unchanged deadline job wrapper and idle checks before/after every scene.
No candidate selection, training, automatic retry or smoothness judgment.
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
spec = importlib.util.spec_from_file_location("night2_backend", ROOT / "reproduction/run-stair-night2-development-comparison.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)
require, digest, read = backend.require, backend.digest, backend.read
ZONE, DEADLINE = backend.ZONE, backend.DEADLINE
BASELINE = "artifacts/go2-stairs-night2-faithful-seed1213-760/model_760.pt"
BASELINE_HASH = "039dfefe4798751b378342b792c1442d9025bfe76749572fa1a70eabae7b2472"
PLAN = "reproduction/stair-night2-round3-evaluation-proposal.json"
TRAINING_PLAN = "reproduction/stair-night2-round3-training-proposal.json"
PREREGISTERED_PROTOCOL_SHA256 = {
    PLAN: "24f646160c5e3aeeddd7fe193582132f07b32490eb2f5056da1cfb62a15b53f3",
    TRAINING_PLAN: "45d0190ff0e931331ad0d128390e5cca6e4d2c0812030d38a6af3f37e579cc6f",
    "reproduction/stair-night2-development-geometries.json": "dd98558974995a8c409491c11aef6a89be2e0953813a76412cb088279a322a98",
    "reproduction/stair-night2-round3-reserved-geometries.json": "d7132ecd85f0ca9ab6fc37cb312fafc612d9c8513efecbba7ab7007c76f763e1",
}
RUNTIME_FILES = (*backend.SOURCE_FILES, "isaaclab/stair_randomization.py", "isaaclab/checkpoint_transfer.py",
                 "isaaclab/vendor/him_rsl_rl/modules/him_actor_critic.py",
                 "isaaclab/vendor/him_rsl_rl/modules/him_estimator.py",
                 "isaaclab/vendor/him_rsl_rl/algorithms/him_ppo.py",
                 "isaaclab/vendor/him_rsl_rl/runners/him_on_policy_runner.py")
STATIC_FILES = tuple(n for n in RUNTIME_FILES if n not in ("isaaclab/run.py", "isaaclab/stair_rewards.py"))
WORKFLOW_FILES = ("isaaclab/run.sh", "isaaclab/compose.override.yaml", "reproduction/run-stair-night2-job.py",
                  "reproduction/run-stair-night2-development-comparison.py",
                  "reproduction/run-stair-night2-final-comparison.py", "reproduction/summarize-stair-night2.py",
                  "reproduction/run-stair-night2-round3-comparison.py",
                  "reproduction/audit-stair-night2-round3-source.py",
                  "reproduction/run-stair-night2-round.py", "reproduction/inspect-stair-night2-training.py")


def explicit_file(value):
    path = Path(value).expanduser()
    path = path if path.is_absolute() else ROOT / path
    path = path.resolve(strict=True)
    require(path.is_file(), "Input must be an explicit file: " + str(path))
    return path


def git(arguments, binary=False):
    done = subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True, text=not binary, timeout=20)
    require(done.returncode == 0, "Git provenance check failed")
    return done.stdout


def source_identity():
    names = (*RUNTIME_FILES, *WORKFLOW_FILES)
    require(not git(["status", "--porcelain", "--", *names]).strip(), "Commit runtime/workflow before declaring source")
    commit = git(["rev-parse", "HEAD"]).strip()
    hashes = {name: digest(ROOT / name) for name in names}
    for name, actual in hashes.items():
        require(hashlib.sha256(git(["show", commit + ":" + name], binary=True)).hexdigest() == actual,
                "Declared source differs from Git commit: " + name)
    return {"git_commit": commit, "code_files_clean": True, "file_sha256": hashes}


def validate_source_identity(value):
    require(value.get("code_files_clean") is True, "Source must be committed and clean")
    commit = value.get("git_commit", "")
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "Full source commit required")
    hashes = value.get("file_sha256", {})
    require(set(hashes) == set((*RUNTIME_FILES, *WORKFLOW_FILES)), "Source file set differs")
    require(not git(["status", "--porcelain", "--", *hashes]).strip(), "Runtime/workflow dirty after declaration")
    for name, expected in hashes.items():
        require(digest(ROOT / name) == expected, "Source changed after declaration: " + name)
        require(hashlib.sha256(git(["show", commit + ":" + name], binary=True)).hexdigest() == expected,
                "Source hash differs from frozen commit: " + name)


def protocol_identity():
    plan = read(ROOT / PLAN)
    names = (PLAN, TRAINING_PLAN, plan["geometry_sets"]["development"]["file"], plan["geometry_sets"]["final"]["file"])
    require(plan["geometry_sets"]["development"]["reset_seeds"] == [11, 29, 47], "Development seeds changed")
    require(plan["geometry_sets"]["final"]["reset_seeds"] == [1301, 1303, 1307], "Round3 reserved seeds changed")
    require(plan["evaluation"]["speeds_m_s"] == [0.3, 0.5], "Speeds changed")
    require(plan["geometry_sets"]["development"]["num_envs"] == 576 and plan["geometry_sets"]["final"]["num_envs"] == 512,
            "Matrix environment counts changed")
    actual = {name: digest(ROOT / name) for name in names}
    require(actual == PREREGISTERED_PROTOCOL_SHA256, "Round3 preregistered protocol bytes changed")
    return actual


def validate_proof(value):
    require(value.get("status") == "actual_applied_contact_light_source_compatibility_CPU_verified", "Actual applied CPU proof required")
    require(value.get("cuda_initialized") is False and value.get("simulation_started") is False,
            "Compatibility proof must be CPU-only")
    require(value.get("baseline_checkpoint") == BASELINE and value.get("baseline_checkpoint_sha256") == BASELINE_HASH,
            "Proof must bind fixed faithful1213 baseline")
    require(digest(ROOT / BASELINE) == BASELINE_HASH, "Baseline checkpoint hash changed")
    require(value.get("baseline_manifest_sha256") == digest((ROOT / BASELINE).parent / "manifest.json"),
            "Proof baseline archive changed")
    require(value.get("proposal_sha256") == digest(ROOT / TRAINING_PLAN), "Predeclared training proposal changed")
    expected_patch = read(ROOT / TRAINING_PLAN)["patch_proposal"]["proposed_source_sha256"]
    require(value.get("applied_patch_file_sha256") == expected_patch, "Proof uses unregistered patch")
    require(all(digest(ROOT / name) == expected for name, expected in expected_patch.items()), "Applied patch changed after proof")
    require(value.get("current_runtime_sha256") == {n: digest(ROOT / n) for n in backend.SOURCE_FILES},
            "Current runtime differs from actual source proof")
    static = value.get("unchanged_nonreward_files", {})
    require(set(static) == set(STATIC_FILES), "Proof requires all nine unchanged non-reward files")
    for name, row in static.items():
        require(row.get("equal") is True and row.get("current_sha256") == row.get("archived_training_commit_sha256") == digest(ROOT / name),
                "Non-reward compatibility failed: " + name)
        committed = git(["show", value["baseline_training_commit"] + ":" + name], binary=True)
        require(hashlib.sha256(committed).hexdigest() == row["current_sha256"], "Baseline source provenance differs: " + name)
    expected_profiles = {"stock", "faithful", "faithful_tracking", "tuned", "contact", "contact_force", "contact_slide", "contact_vertical", "contact_clearance"}
    profiles = value.get("old_profiles", {})
    require(set(profiles) == expected_profiles and all(r.get("full_actual_go2_configuration_equal") is True and r.get("manifest_equal") is True for r in profiles.values()),
            "All nine old actual configurations/manifests must remain equal")
    require(len(value.get("preserved_reward_helper_AST_sha256", {})) == 11, "Eleven reward helpers must be unchanged")
    require(value.get("light_only_difference") == {"term": "leg_contacts", "weight": -0.02,
            "function_and_parameters_equal_existing_contact": True, "all_other_actual_configuration_equal": True},
            "New reward must be sole existing contact-count weight addition")
    require(value.get("audit_script_sha256") == digest(ROOT / "reproduction/audit-stair-night2-round3-source.py"),
            "Actual proof script changed")


def archive_identity(label, profile, checkpoint, proof):
    require(profile in ("faithful", "contact_light"), "Round3 only admits faithful or contact_light")
    model = explicit_file(checkpoint)
    relative = str(model.relative_to(ROOT))
    directory = model.parent
    manifest_path, config_path, result_path = [directory / n for n in ("manifest.json", "config.json", "result.json")]
    manifest, config, result = map(read, (manifest_path, config_path, result_path))
    require(manifest.get("training_status") == "completed_and_CPU_checkpoint_verified", "Archive is not completed and CPU verified")
    members = manifest.get("files", {})
    require(len(members) == 19, "Every training archive must have the expected nineteen members")
    member_hashes = {}
    for name, entry in members.items():
        path = directory / name
        require(path.resolve().is_relative_to(directory.resolve()) and path.is_file(), "Invalid/missing archive member: " + name)
        require(path.stat().st_size == entry.get("bytes") and digest(path) == entry.get("sha256"), "Archive member size/hash mismatch: " + name)
        member_hashes[name] = entry["sha256"]
    require(manifest.get("reward_profile") == profile == config.get("stair_reward", {}).get("profile"), "Actual reward profile differs")
    budget = {"saved_additional_updates": 100, "num_envs": 7680, "steps_per_env": 100, "environment_steps_this_run": 76800000}
    require(all(manifest.get(k) == v for k, v in budget.items()), "Unmatched saved training budget")
    require(config.get("mode") == "train" and config.get("terrain") == "stairs" and config.get("num_envs") == 7680
            and config["train"]["runner"]["num_steps_per_env"] == 100 and config.get("requested_additional_training_updates") == 100, "Actual training config budget differs")
    require(result.get("status") == "smoke_passed" and result.get("parameters_finite") is True and result.get("iterations") == 100
            and result.get("num_envs") == 7680 and result.get("environment_steps_this_run") == 76800000 and result.get("checkpoint") == model.name,
            "Actual training result incomplete")
    require(manifest.get("origin_checkpoint_sha256") == backend.EXPECTED_ORIGIN_SHA256
            and manifest.get("origin_checkpoint_completed_updates") == 660 and manifest.get("checkpoint_completed_updates") == result.get("completed_iterations") == 760,
            "Candidate must be common control660 plus exactly100updates")
    require(manifest.get("training_seed") == config.get("seed") == 1213, "Matched training seed1213 required")
    require(config.get("runtime_training_state_before_learning", {}).get("optimizer_state") == "checkpoint Adam retained"
            and config.get("exploration_std_override") is None, "Adam/std continuation differs")
    audit_path = directory / manifest["cpu_checkpoint_audit"]
    require(audit_path.name in members, "Checkpoint audit must be an archived member")
    audit = read(audit_path)
    require(audit.get("cuda_initialized") is False and audit.get("all_model_tensors_finite") is True
            and audit.get("network_shapes_preserved") is True and audit.get("model_state_tensor_count") == 30
            and audit.get("origin_iteration") == 660 and audit.get("final_iteration") == 760 and audit.get("saved_additional_updates") == 100
            and audit["final_tot_timesteps"] - audit["origin_tot_timesteps"] == 76800000, "CPU checkpoint proof incomplete")
    optimizers = audit.get("optimizers", {})
    require(set(optimizers) == {"optimizer_state_dict", "estimator_optimizer_state_dict"}, "Both Adam states required")
    for optimizer in optimizers.values():
        require(optimizer.get("all_state_tensors_finite") is True and optimizer.get("per_state_step_continuation")
                and all(r.get("delta") == 2000 for r in optimizer["per_state_step_continuation"]), "Adam steps must advance exactly2000")
    provenance = manifest["source_provenance"]
    actual_hash = digest(model)
    if profile == "faithful":
        require(relative == BASELINE and actual_hash == BASELINE_HASH, "Only narrowly proven fixed faithful1213 archive may use older source")
        require(provenance["verified_runtime_source_sha256"] == proof["baseline_archived_runtime_sha256"], "Legacy source differs from proven baseline")
        expected_manifest = proof["faithful_reward_manifest"]
        compatibility = "fixed_old_faithful_exact_configuration_and_nine_file_compatibility_proof"
    else:
        require(provenance["verified_runtime_source_sha256"] == proof["current_runtime_sha256"], "New light training source differs from current runtime")
        expected_manifest = proof["light_reward_manifest"]
        compatibility = "new_light_exact_current_runtime_source"
    require(config["stair_reward"] == expected_manifest and config["reward_weights"] == expected_manifest["weights"], "Archived actual reward config differs from CPU proof")
    if profile == "contact_light":
        bodies = sorted(f"{leg}_{part}" for leg in ("FL", "FR", "RL", "RR") for part in ("thigh", "calf"))
        require(sorted(config.get("resolved_contact_reward_bodies", [])) == bodies
                and sorted(config.get("resolved_leg_reward_body_selections", {}).get("leg_contacts", [])) == bodies,
                "Actual light training must resolve exactly eight thigh/calf bodies")
    signature_keys = ("task", "seed", "num_envs", "train", "physics", "torch", "cuda", "gpu_capability",
                      "robot_usd", "physics_dt", "policy_decimation", "episode_length_s", "observation",
                      "command_override", "training_turn_fraction", "exploration_std_override", "resume_learning_rate_override",
                      "requested_additional_training_updates", "terrain_start_level", "stair_training_speed_range_m_s",
                      "terrain", "stairs", "domain_randomization", "calf_limit_sensitivity", "friction_override",
                      "stair_pushes", "flat_replay", "joint_names", "default_joint_positions", "action_scale",
                      "runtime_training_state_before_learning", "reward_frame_validation")
    physical = read(directory / "domain-parameters-initial.json")
    require(physical.get("status") == "captured", "Actual initial physical readback required")
    physical = {k: v for k, v in physical.items() if k != "terrain_material"} | {
        "terrain_material": {k: v for k, v in read(directory / "domain-parameters-initial.json")["terrain_material"].items()
                             if k != "stage_root_layer_identifier"}}
    physical_hash = hashlib.sha256(json.dumps(physical, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return {"label": label, "training_reward_profile": profile, "checkpoint": relative, "checkpoint_sha256": actual_hash,
            "training_manifest": str(manifest_path.relative_to(ROOT)), "training_manifest_sha256": digest(manifest_path),
            "training_config_sha256": digest(config_path), "training_result_sha256": digest(result_path),
            "archive_member_sha256": member_hashes, "training_budget": budget, "training_seed": 1213,
            "training_reward_weights": config["reward_weights"], "training_source_provenance": provenance,
            "source_compatibility": compatibility, "training_hyperparameters": config["train"],
            "training_state_before_learning": config["runtime_training_state_before_learning"],
            "training_common_parameter_configuration": {k: config.get(k) for k in signature_keys},
            "training_initial_physical_readback_sha256_normalized": physical_hash,
            "physical_comparison_scope": "Saved readback values/statistics with only anonymous USD layer identifier removed; not all initial tensors or deterministic CUDA trajectories.",
            "training_sampling_configuration": {k: config.get(k) for k in ("terrain", "stairs", "robot_usd", "domain_randomization", "friction_override", "terrain_start_level", "stair_training_speed_range_m_s", "training_turn_fraction", "stair_pushes", "flat_replay")},
            "origin_checkpoint_sha256": backend.EXPECTED_ORIGIN_SHA256}


def validate_pair(baseline, selected):
    for key in ("training_budget", "training_seed", "training_hyperparameters", "training_state_before_learning", "training_sampling_configuration", "origin_checkpoint_sha256",
                "training_common_parameter_configuration", "training_initial_physical_readback_sha256_normalized"):
        require(baseline[key] == selected[key], "Matched training identity differs beyond reward: " + key)
    if selected["training_reward_profile"] == "contact_light":
        weights = dict(selected["training_reward_weights"])
        require(weights.pop("leg_contacts", None) == -0.02 and weights == baseline["training_reward_weights"], "Sole light weight addition differs")


def development_evidence(path, selected):
    path = explicit_file(path)
    summary = read(path)
    plan = read(ROOT / PLAN)
    require(summary.get("split") == "development" and summary.get("checkpoint_sha256") == selected["checkpoint_sha256"], "Only own development evidence may select")
    require(summary.get("plan_sha256") == digest(ROOT / PLAN) and summary.get("geometry_sha256") == digest(ROOT / plan["geometry_sets"]["development"]["file"]), "Development protocol differs")
    rows = summary.get("cases", [])
    expected = {(i, s, v) for i in range(18) for s in [11, 29, 47] for v in [0.3, 0.5]}
    require(len(rows) == 108 and {(r.get("case_index"), r.get("reset_seed"), r.get("speed_m_s")) for r in rows} == expected
            and all(r.get("heading_control_enabled") is True and r.get("source_protocol_verified") is True for r in rows)
            and not summary.get("duplicate_case_seed_speed_controller_rows"), "Complete108row default-heading development matrix required")
    # Training identity comes from archive, never the shared construction reward label.
    sidecar_path = path.parent / (selected["label"] + "-training-identity.json")
    sidecar = read(sidecar_path)
    require(sidecar.get("identity") == selected and sidecar.get("summary_sha256") == digest(path), "Actual training identity sidecar required")
    return {"summary_file": str(path), "sha256": digest(path), "training_identity_file": str(sidecar_path),
            "training_identity_sha256": digest(sidecar_path), "numeric_verdicts": summary["controllers"]}


def selection_payload(checkpoint, development_summary, reason, source_proof):
    proof_path = explicit_file(source_proof)
    proof = read(proof_path)
    validate_proof(proof)
    profile = read(explicit_file(checkpoint).parent / "manifest.json")["reward_profile"]
    baseline = archive_identity("baseline-faithful1213", "faithful", BASELINE, proof)
    selected = archive_identity("contact-light1213" if profile == "contact_light" else "baseline-faithful1213", profile, checkpoint, proof)
    validate_pair(baseline, selected)
    require(isinstance(reason, str) and reason.strip(), "Root's explicit development selection reason required")
    value = {"schema_version": 1, "round": 3, "status": "frozen_before_final", "created_local": datetime.now(ZONE).isoformat(),
             "selection_basis": "development_only", "no_final_evidence_used": True, "selection_reason": reason,
             "selected": selected, "baseline": baseline, "source": source_identity(), "protocol": protocol_identity(),
             "source_proof_file": str(proof_path), "source_proof_sha256": digest(proof_path),
             "development_evidence": development_evidence(development_summary, selected),
             "automatic_candidate_selection": False, "retuning_from_final_allowed": False}
    return value


def validate_selection(value, proof_path, proof):
    require(value.get("schema_version") == 1 and value.get("round") == 3 and value.get("status") == "frozen_before_final", "Explicit round3 freeze required")
    require(value.get("selection_basis") == "development_only" and value.get("no_final_evidence_used") is True
            and value.get("automatic_candidate_selection") is False and value.get("retuning_from_final_allowed") is False, "Final selection/retuning forbidden")
    require(value.get("selection_reason", "").strip(), "Explicit root reason required")
    created = datetime.fromisoformat(value["created_local"])
    require(created.tzinfo is not None and created <= datetime.now(ZONE), "Invalid freeze time")
    require(value.get("source_proof_sha256") == digest(proof_path) and explicit_file(value["source_proof_file"]) == proof_path, "Freeze source proof differs")
    require(value.get("protocol") == protocol_identity(), "Protocol changed since freeze")
    validate_source_identity(value["source"])
    selected = value["selected"]
    current = archive_identity(selected["label"], selected["training_reward_profile"], selected["checkpoint"], proof)
    baseline = archive_identity("baseline-faithful1213", "faithful", BASELINE, proof)
    require(current == selected and baseline == value["baseline"], "Frozen archive identities changed")
    validate_pair(baseline, current)
    require(development_evidence(value["development_evidence"]["summary_file"], selected) == value["development_evidence"], "Selection evidence changed")
    return baseline, current


def planned_jobs(stage, baseline, candidate, prefix):
    plan = read(ROOT / PLAN)
    matrix = plan["geometry_sets"][stage]
    jobs = []
    for speed in [0.3, 0.5]:
        for heading in ([True] if stage == "development" else [True, False]):
            name = prefix + ("-speed03" if speed == 0.3 else "-speed05") + ("-heading" if heading else "-zero-yaw")
            forwarded = ["evaluate", "--terrain", "stairs", "--checkpoint", baseline["checkpoint"], "--reward_profile", "faithful",
                         "--stair_batch", matrix["file"], "--num_envs", str(matrix["num_envs"]), "--speed", str(speed),
                         "--eval_seconds", "40", "--eval_randomized", "--seed", "1", "--domain_profile", "none", "--eval_trace_stride", "1"]
            for seed in matrix["reset_seeds"]:
                forwarded += ["--eval_seed", str(seed)]
            if candidate["checkpoint_sha256"] != baseline["checkpoint_sha256"]:
                forwarded += ["--candidate_checkpoint", candidate["checkpoint"]]
            if not heading:
                forwarded.append("--open_loop_heading")
            argv = [sys.executable, str(ROOT / "reproduction/run-stair-night2-job.py"), "--name", name, "--max-seconds", "3000", "--", *forwarded]
            jobs.append({"name": name, "speed_m_s": speed, "heading_control_enabled": heading,
                         "wrapper_argv": argv, "shell_command": shlex.join(argv)})
    return jobs


def summarize_policy(identity, candidate, records, output, stage):
    paths = []
    for record in records:
        directory = Path(record["simulator_directory"])
        if candidate:
            directory /= "candidates/0_" + Path(identity["checkpoint"]).stem
        result = directory / "result.json"
        require(result.is_file(), "Declared explicit result missing: " + str(result))
        paths.append(result)
    prefix = output / (identity["label"] + "-" + stage + "-summary")
    require(not any(prefix.with_suffix(s).exists() for s in (".json", ".md", ".csv")), "Summary overwrite refused")
    done = subprocess.run([sys.executable, str(ROOT / "reproduction/summarize-stair-night2.py"), *map(str, paths),
                           "--stage", stage, "--plan", str(ROOT / PLAN), "--output", str(prefix)], cwd=ROOT,
                          capture_output=True, text=True, timeout=240)
    require(done.returncode == 0, "Independent CPU summary failed: " + done.stderr)
    summary_path = prefix.with_suffix(".json")
    summary = read(summary_path)
    require(summary["checkpoint_sha256"] == identity["checkpoint_sha256"], "Summary model identity differs")
    expected_controllers = {True} if stage == "development" else {True, False}
    require({r["heading_control_enabled"] for r in summary["controllers"]} == expected_controllers
            and all(r["matrix_complete"] is True for r in summary["controllers"]), "Collection matrix incomplete; preserve failures")
    sidecar = {"status": stage + "_collection_completed_actual_training_identity_attached", "identity": identity,
               "shared_evaluation_reward_profile": "faithful", "source_result_paths": list(map(str, paths)),
               "raw_result_sha256": {str(p): digest(p) for p in paths}, "summary": str(summary_path), "summary_sha256": digest(summary_path),
               "training_profile_scope": "Scene construction faithful is not candidate training identity; use actual archive identity above.",
               "automatic_selection_performed": False, "smoothness_visual_judgment_performed": False}
    sidecar_path = output / (identity["label"] + "-training-identity.json")
    backend.save_json_exclusive(sidecar_path, sidecar)
    print(done.stdout.strip(), flush=True)
    return {"label": identity["label"], "summary": str(summary_path), "training_identity": str(sidecar_path), "controller_numeric_verdicts": summary["controllers"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("development", "final"), required=True)
    parser.add_argument("--candidate", help="New contact_light archive; development only")
    parser.add_argument("--selection-file", help="Explicit new round3 freeze; final only")
    parser.add_argument("--source-proof", required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--container", default="isaaclab-local-lab-1")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    output, records, active_job = None, [], None
    try:
        require(args.container == "isaaclab-local-lab-1", "Use existing fixed container")
        proof_path = explicit_file(args.source_proof)
        proof_hash, proof = digest(proof_path), read(proof_path)
        validate_proof(proof)
        protocol = protocol_identity()
        source = source_identity()
        selection_path, selection_hash, selection = None, None, None
        if args.stage == "development":
            require(args.candidate is not None and args.selection_file is None, "Development requires candidate, no selection")
            baseline = archive_identity("baseline-faithful1213", "faithful", BASELINE, proof)
            candidate = archive_identity("contact-light1213", "contact_light", args.candidate, proof)
            validate_pair(baseline, candidate)
        else:
            require(args.selection_file is not None and args.candidate is None, "Final requires explicit freeze, no candidate option")
            selection_path = explicit_file(args.selection_file)
            selection_hash, selection = digest(selection_path), read(selection_path)
            baseline, candidate = validate_selection(selection, proof_path, proof)
        unique = datetime.now(ZONE).strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
        prefix = "night2-round3-" + args.stage + "-" + unique
        jobs = planned_jobs(args.stage, baseline, candidate, prefix)
        idle = {"status": "not_checked_in_dry_run", "docker_contacted": False}
        if args.execute:
            require(datetime.now(ZONE) < DEADLINE, "Authorized deadline passed")
            idle = backend.container_idle(args.container)
        destination = args.output_dir.expanduser().resolve() if args.output_dir else Path.home() / "robotics/logs" / prefix
        manifest = {"schema_version": 1, "round": 3, "created_local": datetime.now(ZONE).isoformat(), "stage": args.stage,
                    "status": "immutable_launch_plan" if args.execute else "dry_run_not_executed", "baseline": baseline,
                    "candidate": candidate, "source": source, "protocol": protocol, "source_proof": proof,
                    "source_proof_file": str(proof_path), "source_proof_sha256": proof_hash,
                    "selection_file": str(selection_path) if selection_path else None, "selection_sha256": selection_hash,
                    "selection": selection, "jobs": jobs, "common_evaluation_reward_profile": "faithful",
                    "deadline_local": DEADLINE.isoformat(), "per_scene_max_seconds": 3000, "initial_container_idle_check": idle,
                    "automatic_candidate_selection": False, "retuning_from_final_allowed": False,
                    "scientific_acceptance": "Collection completion is not numerical PASS, smoothness, or original-paper superiority."}
        if args.execute or args.output_dir:
            destination.mkdir(parents=True, exist_ok=False)
            output = destination
            backend.save_json_exclusive(output / "immutable-manifest.json", manifest)
            (output / "immutable-manifest.json").chmod(0o444)
            if selection_path:
                shutil.copyfile(selection_path, output / "selection-freeze.json")
                require(digest(output / "selection-freeze.json") == selection_hash, "Freeze copy changed")
                (output / "selection-freeze.json").chmod(0o444)
        print("COMPARISON_DIR: " + str(destination), flush=True)
        if not args.execute:
            for job in jobs:
                print(job["shell_command"])
            print(json.dumps({"status": "dry_run_not_executed", "jobs": len(jobs), "docker_contacted": False}))
            return
        for job in jobs:
            active_job = job["name"]
            require(datetime.now(ZONE) < DEADLINE, "Deadline reached before next scene")
            require(digest(proof_path) == proof_hash and protocol_identity() == protocol, "Source proof or protocol changed")
            validate_source_identity(source)
            validate_proof(proof)
            require(archive_identity(baseline["label"], "faithful", BASELINE, proof) == baseline, "Baseline archive changed")
            require(archive_identity(candidate["label"], candidate["training_reward_profile"], candidate["checkpoint"], proof) == candidate, "Candidate archive changed")
            if selection_path:
                require(digest(selection_path) == selection_hash, "Selection changed after freeze")
                validate_selection(selection, proof_path, proof)
            pre_idle = backend.container_idle(args.container)
            record = backend.execute_job(job, output)
            record.update(pre_scene_idle_check=pre_idle, source_proof_sha256=proof_hash, selection_sha256=selection_hash)
            records.append(record)
            backend.save_json_exclusive(output / (job["name"] + "-completion.json"), record)
            backend.container_idle(args.container)
        active_job = "cpu_summaries"
        validate_source_identity(source)
        validate_proof(proof)
        policies = [summarize_policy(baseline, False, records, output, args.stage)]
        if candidate["checkpoint_sha256"] != baseline["checkpoint_sha256"]:
            policies.append(summarize_policy(candidate, True, records, output, args.stage))
        backend.save_json_exclusive(output / "comparison-completion.json", {
            "status": args.stage + "_collection_and_separate_cpu_summaries_completed", "records": records,
            "policies": policies, "source_proof_sha256": proof_hash, "selection_sha256": selection_hash,
            "immutable_manifest_sha256": digest(output / "immutable-manifest.json"),
            "automatic_candidate_selection": False, "retuning_from_final_allowed": False})
        print(json.dumps({"status": "collection_and_CPU_summaries_completed", "directory": str(output)}), flush=True)
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        if args.execute and output is not None:
            backend.save_json_exclusive(output / "comparison-failure.json", {"status": "stopped_preserve_evidence_no_automatic_retry",
                "failed_stage": active_job, "error": str(error), "completed_records": records, "scientific_acceptance": "INCOMPLETE or FAIL, never automatic promotion"})
        parser.error(str(error))


if __name__ == "__main__":
    main()
