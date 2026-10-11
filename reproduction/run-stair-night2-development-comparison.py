#!/usr/bin/env python3
"""Prepare or serially run explicitly identified, matched night-two policies.

Default dry-run never contacts Docker or starts simulation. --execute verifies
archived identities/budgets, refuses any live container run.py, saves an
exclusive immutable manifest, and uses the existing per-job deadline wrapper.
Each candidate receives its own explicit-path CPU summary and training sidecar.
"""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import sys
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
ZONE = ZoneInfo("Asia/Shanghai")
EXPECTED_ORIGIN_SHA256 = "79fcc69b9447ecfb4df9fcfb41224cdab78632649f38fd9faf09c7b6adf69c61"
DEADLINE = datetime.fromisoformat("2026-10-12T07:20:00+08:00")
PROFILES = ("faithful", "faithful_tracking", "contact", "contact_vertical", "contact_clearance")
SOURCE_FILES = ("isaaclab/run.py", "isaaclab/stair_rewards.py", "isaaclab/stair_terrain.py",
                "isaaclab/stair_evaluation.py", "isaaclab/adapter.py")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def input_path(value):
    path = Path(value).expanduser()
    path = path if path.is_absolute() else ROOT / path
    path = path.resolve(strict=True)
    require(path.is_file(), "Input is not a file: " + str(path))
    relative = path.relative_to(ROOT)
    return path, str(relative)


def archive_identity(label, profile, value):
    require(re.fullmatch(r"[a-zA-Z0-9_-]+", label) is not None, "Use simple unique candidate labels")
    require(profile in PROFILES, "Undeclared candidate reward profile: " + profile)
    model, relative = input_path(value)
    directory = model.parent
    manifest_path = directory / "manifest.json"
    config_path = directory / "config.json"
    result_path = directory / "result.json"
    require(manifest_path.is_file() and config_path.is_file() and result_path.is_file(),
            "Candidate needs archived manifest/config/result alongside model: " + relative)
    manifest, config, result = map(read, (manifest_path, config_path, result_path))
    actual_hash = digest(model)
    require(manifest.get("training_status") == "completed_and_CPU_checkpoint_verified", "Candidate archive not CPU-verified complete")
    require(manifest.get("reward_profile") == profile == config.get("stair_reward", {}).get("profile"),
            "Training reward profile disagrees with archive/config: " + label)
    require(config.get("mode") == "train" and config.get("terrain") == "stairs", "Candidate config is not staircase training")
    expected_budget = {"saved_additional_updates": 100, "num_envs": 7680,
                       "steps_per_env": 100, "environment_steps_this_run": 76800000}
    require(all(manifest.get(key) == value for key, value in expected_budget.items()),
            "Candidate does not have matched100updates/7680envs/100steps/76.8Msteps: " + label)
    require(config.get("num_envs") == 7680 and config["train"]["runner"]["num_steps_per_env"] == 100
            and config.get("requested_additional_training_updates") == 100, "Actual config budget differs: " + label)
    require(result.get("status") == "smoke_passed" and result.get("parameters_finite") is True
            and result.get("iterations") == 100 and result.get("num_envs") == 7680
            and result.get("environment_steps_this_run") == 76800000
            and result.get("checkpoint") == model.name, "Actual result budget/finite/model identity differs: " + label)
    require(manifest.get("origin_checkpoint_sha256") == EXPECTED_ORIGIN_SHA256, "Origin is not common control660: " + label)
    require(manifest.get("origin_checkpoint_completed_updates") == 660
            and manifest.get("checkpoint_completed_updates") == result.get("completed_iterations") == 760,
            "Checkpoint saved iteration is not660+100: " + label)
    require(config.get("runtime_training_state_before_learning", {}).get("optimizer_state") == "checkpoint Adam retained",
            "Full Adam continuation not declared: " + label)
    require(config.get("exploration_std_override") is None, "Candidate reset exploration std: " + label)
    files = manifest.get("files", {})
    for path in (model, config_path, result_path):
        require(files.get(path.name, {}).get("sha256") == digest(path), "Archive member hash mismatch: " + str(path))
    audit_name = manifest.get("cpu_checkpoint_audit")
    require(isinstance(audit_name, str), "CPU checkpoint audit identity missing: " + label)
    audit_path = directory / audit_name
    require(audit_path.is_file() and files.get(audit_name, {}).get("sha256") == digest(audit_path),
            "CPU checkpoint audit missing/hash mismatch: " + label)
    audit = read(audit_path)
    require(audit.get("cuda_initialized") is False and audit.get("all_model_tensors_finite") is True
            and audit.get("network_shapes_preserved") is True and audit.get("origin_iteration") == 660
            and audit.get("final_iteration") == 760, "CPU checkpoint audit incomplete: " + label)
    require(audit.get("saved_additional_updates") == 100 and isinstance(audit.get("origin_tot_timesteps"), int)
            and isinstance(audit.get("final_tot_timesteps"), int)
            and audit["final_tot_timesteps"] - audit["origin_tot_timesteps"] == 76800000,
            "CPU checkpoint timesteps do not match actual saved budget: " + label)
    provenance = manifest.get("source_provenance", {})
    runtime_hashes = provenance.get("verified_runtime_source_sha256", {})
    require(all(runtime_hashes.get(name) == digest(ROOT / name) for name in SOURCE_FILES),
            "Current runtime source differs from archived candidate: " + label)
    return {"label": label, "training_reward_profile": profile, "checkpoint": relative,
            "checkpoint_sha256": actual_hash, "training_manifest": str(manifest_path.relative_to(ROOT)),
            "training_manifest_sha256": digest(manifest_path), "training_config": str(config_path.relative_to(ROOT)),
            "training_config_sha256": digest(config_path), "training_result": str(result_path.relative_to(ROOT)),
            "training_result_sha256": digest(result_path), "cpu_audit_sha256": digest(audit_path),
            "training_budget": expected_budget, "training_seed": manifest.get("training_seed"),
            "training_reward_weights": config.get("reward_weights"), "training_source_provenance": provenance,
            "training_hyperparameters": config.get("train"),
            "training_sampling_configuration": {key: config.get(key) for key in (
                "terrain", "stairs", "robot_usd", "domain_randomization", "friction_override", "terrain_start_level",
                "stair_training_speed_range_m_s", "training_turn_fraction", "stair_pushes", "flat_replay")},
            "origin_checkpoint_sha256": EXPECTED_ORIGIN_SHA256}


def container_idle(container):
    script = """import json, os
rows=[]
for entry in os.listdir('/proc'):
    if not entry.isdigit(): continue
    try:
        raw=open('/proc/'+entry+'/cmdline','rb').read().split(b'\\0')
        args=[arg.decode(errors='replace') for arg in raw if arg]
        if any(arg=='run.py' or arg.endswith('/run.py') for arg in args):
            rows.append({'pid':int(entry),'argv':args})
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        continue
print(json.dumps(rows))
"""
    probe = subprocess.run(["docker", "exec", container, "/isaac-sim/kit/python/bin/python3", "-c", script],
                           capture_output=True, text=True, timeout=25)
    require(probe.returncode == 0, "Container idle check failed; no evaluation launched: " + probe.stderr.strip())
    rows = json.loads(probe.stdout.strip())
    require(isinstance(rows, list), "Container process check returned unexpected schema")
    require(not rows, "Container has live run.py; refusing instead of queuing/concurrent simulation: " + json.dumps(rows))
    return {"container": container, "checked_local": datetime.now(ZONE).isoformat(), "live_run_py": []}


def planned_jobs(baseline, candidates, speeds, seeds, zero_yaw, prefix):
    jobs = []
    for speed in speeds:
        name = prefix + ("-speed03" if speed == 0.3 else "-speed05") + ("-zero-yaw" if zero_yaw else "-heading")
        forwarded = ["evaluate", "--terrain", "stairs", "--checkpoint", baseline["checkpoint"],
                     "--reward_profile", "contact", "--stair_batch", "reproduction/stair-night2-development-geometries.json",
                     "--num_envs", "576", "--speed", str(speed), "--eval_seconds", "40", "--eval_randomized",
                     "--seed", "1", "--domain_profile", "none", "--eval_trace_stride", "1"]
        for seed in seeds:
            forwarded += ["--eval_seed", str(seed)]
        for candidate in candidates:
            forwarded += ["--candidate_checkpoint", candidate["checkpoint"]]
        if zero_yaw:
            forwarded.append("--open_loop_heading")
        command = [sys.executable, str(ROOT / "reproduction/run-stair-night2-job.py"), "--name", name,
                   "--max-seconds", "3000", "--", *forwarded]
        jobs.append({"name": name, "speed_m_s": speed, "heading_control_enabled": not zero_yaw,
                     "wrapper_argv": command, "shell_command": shlex.join(command)})
    return jobs


def execute_job(job, output):
    captured = output / (job["name"] + "-wrapper.stdout.txt")
    require(not captured.exists(), "Refusing wrapper-output overwrite")
    log_paths = []
    with captured.open("x") as stream:
        process = subprocess.Popen(job["wrapper_argv"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, bufsize=1)
        for line in process.stdout:
            stream.write(line)
            stream.flush()
            if line.startswith("JOB_LOG: "):
                log_paths.append(Path(line[len("JOB_LOG: "):].strip()))
                print(line.rstrip(), flush=True)
        code = process.wait()
    require(code == 0, "Evaluation wrapper failed; preserve outputs, do not restart automatically: " + str(captured))
    require(len(log_paths) == 1, "Wrapper stdout must identify exactly one JOB_LOG")
    record_path = log_paths[0] / "launch-record.json"
    record = read(record_path)
    require(record.get("name") == job["name"] and record.get("status") == "exited" and record.get("exit_code") == 0,
            "Wrapper completion record disagrees with job")
    run_lines = []
    with (log_paths[0] / "stdout.log").open(errors="replace") as stream:
        for line in stream:
            if line.startswith("RUN: "):
                raw = line[5:].strip()
                if raw.startswith("/workspace/himloco/"):
                    run_lines.append(ROOT / raw[len("/workspace/himloco/"):])
                else:
                    run_lines.append(Path(raw))
    require(len(run_lines) == 1, "Expected exactly one simulator RUN path in wrapper stdout log")
    simdir = run_lines[0].resolve(strict=True)
    simdir.relative_to(ROOT / "isaaclab/logs")
    require(Path(record.get("simulator_log_dir", "")).resolve() == simdir,
            "Explicit RUN line disagrees with wrapper simulator_log_dir")
    require((simdir / "result.json").is_file(), "Successful wrapper did not save primary result")
    return {"name": job["name"], "wrapper_directory": str(log_paths[0]), "wrapper_stdout": str(captured),
            "launch_record_sha256": digest(record_path), "simulator_directory": str(simdir),
            "speed_m_s": job["speed_m_s"], "heading_control_enabled": job["heading_control_enabled"]}


def save_json_exclusive(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def summarize_policy(identity, index, records, output):
    paths = []
    for record in records:
        directory = Path(record["simulator_directory"])
        if index is not None:
            directory /= "candidates/" + str(index) + "_" + Path(identity["checkpoint"]).stem
        result = directory / "result.json"
        require(result.is_file(), "Declared candidate result missing: " + str(result))
        paths.append(result)
    prefix = output / (identity["label"] + "-development-summary")
    command = [sys.executable, str(ROOT / "reproduction/summarize-stair-night2.py"), *map(str, paths),
               "--stage", "development", "--output", str(prefix)]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=180)
    require(completed.returncode == 0, "CPU candidate summary failed: " + completed.stderr)
    summary = read(prefix.with_suffix(".json"))
    require(summary["checkpoint_sha256"] == identity["checkpoint_sha256"], "Summary hash disagrees with declared candidate")
    sidecar = {"status": "evaluation_completed_training_identity_attached", "identity": identity,
               "shared_evaluation_reward_profile": "contact", "source_result_paths": list(map(str, paths)),
               "raw_result_sha256": {str(p): digest(p) for p in paths},
               "summary": str(prefix.with_suffix(".json")), "summary_sha256": digest(prefix.with_suffix(".json")),
               "training_profile_correction": "Raw shared construction rewards belong to baseline scene; candidate true training profile/weights are identity fields here, not inferred from shared evaluation config",
               "automatic_selection_performed": False, "smoothness_visual_judgment_performed": False}
    sidecar_path = output / (identity["label"] + "-training-identity.json")
    save_json_exclusive(sidecar_path, sidecar)
    print(completed.stdout.strip(), flush=True)
    return {"label": identity["label"], "summary": str(prefix.with_suffix(".json")),
            "training_identity": str(sidecar_path), "controller_numeric_verdicts": summary["controllers"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="append", nargs=3, required=True, metavar=("LABEL", "PROFILE", "CHECKPOINT"))
    parser.add_argument("--baseline", default="artifacts/go2-stairs-control660/model_660.pt")
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 29, 47])
    parser.add_argument("--speeds", nargs="+", type=float, choices=(0.3, 0.5), default=[0.3, 0.5])
    parser.add_argument("--zero-yaw", action="store_true", help="Only zero-yaw scenes; default only heading-feedback scenes")
    parser.add_argument("--output-dir", type=Path, help="New exclusive manifest/output directory; dry-run writes only if supplied")
    parser.add_argument("--container", default="isaaclab-local-lab-1")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        require(2 <= len(args.candidate) <= 4, "Supply explicitly two to four candidates")
        require(len({label for label, _, _ in args.candidate}) == len(args.candidate), "Candidate labels must be unique")
        require(args.seeds == [11, 29, 47], "This comparison uses declared development seeds11/29/47 in order")
        require(len(set(args.speeds)) == len(args.speeds), "Duplicate speeds")
        baseline_path, baseline_relative = input_path(args.baseline)
        require(digest(baseline_path) == EXPECTED_ORIGIN_SHA256, "Baseline is not frozen common control660")
        baseline = {"label": "baseline-control660", "checkpoint": baseline_relative,
                    "checkpoint_sha256": EXPECTED_ORIGIN_SHA256, "training_reward_profile": "contact"}
        candidates = [archive_identity(*candidate) for candidate in args.candidate]
        require(len({candidate["training_seed"] for candidate in candidates}) == 1, "Paired candidates must use same training seed")
        require(len({json.dumps(candidate["training_hyperparameters"], sort_keys=True) for candidate in candidates}) == 1,
                "Matched candidates must have identical PPO/HIM/runner settings")
        require(len({json.dumps(candidate["training_sampling_configuration"], sort_keys=True) for candidate in candidates}) == 1,
                "Matched candidates must have identical terrain/reset/command/domain configuration")
        require(args.container == "isaaclab-local-lab-1", "Existing job wrapper uses fixed isaaclab-local-lab-1 container")
        if args.execute:
            require(datetime.now(ZONE) < DEADLINE, "Authorized deadline has passed")
            require(len({candidate["checkpoint_sha256"] for candidate in candidates}) == len(candidates),
                    "Execute requires distinct candidate models; duplicate model only useful as dry fixture")
            initial_idle = container_idle(args.container)
        else:
            initial_idle = {"status": "not_checked_in_dry_run", "docker_contacted": False}
        unique = datetime.now(ZONE).strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
        prefix = "night2-devcompare-" + unique
        jobs = planned_jobs(baseline, candidates, args.speeds, args.seeds, args.zero_yaw, prefix)
        output = args.output_dir.expanduser().resolve() if args.output_dir else Path.home() / "robotics/logs" / prefix
        manifest = {"schema_version": 1, "created_local": datetime.now(ZONE).isoformat(),
            "status": "immutable_launch_plan" if args.execute else "dry_run_not_executed", "stage": "development",
            "baseline": baseline, "candidates_in_parameter_order": candidates, "seeds": args.seeds, "speeds": args.speeds,
            "heading_control_enabled": not args.zero_yaw, "common_evaluation_reward_profile": "contact",
            "training_reward_profiles_separate_from_evaluation_label": True, "deadline_local": DEADLINE.isoformat(),
            "per_scene_max_seconds": 3000, "initial_container_idle_check": initial_idle,
            "jobs": jobs, "source_sha256": {name: digest(ROOT / name) for name in SOURCE_FILES},
            "geometry_sha256": digest(ROOT / "reproduction/stair-night2-development-geometries.json"),
            "evaluation_plan_sha256": digest(ROOT / "reproduction/stair-night2-evaluation-plan.json"),
            "automatic_candidate_selection": False}
        if args.execute or args.output_dir:
            output.mkdir(parents=True, exist_ok=False)
            save_json_exclusive(output / "immutable-manifest.json", manifest)
            (output / "immutable-manifest.json").chmod(0o444)
        print("COMPARISON_DIR: " + str(output), flush=True)
        if not args.execute:
            for job in jobs:
                print(job["shell_command"])
            print(json.dumps({"status": "dry_run_not_executed", "candidate_count": len(candidates),
                              "jobs": len(jobs), "docker_contacted": False,
                              "manifest": str(output / "immutable-manifest.json") if args.output_dir else None}))
            return
        records = []
        for job in jobs:
            idle = container_idle(args.container)
            record = execute_job(job, output)
            record["pre_scene_idle_check"] = idle
            records.append(record)
            save_json_exclusive(output / (job["name"] + "-completion.json"), record)
            container_idle(args.container)
        policies = [summarize_policy(baseline, None, records, output)]
        policies += [summarize_policy(candidate, index, records, output) for index, candidate in enumerate(candidates)]
        final = {"status": "development_collection_and_cpu_summaries_completed", "records": records,
                 "policies": policies, "automatic_candidate_selection": False,
                 "immutable_manifest_sha256": digest(output / "immutable-manifest.json"),
                 "scientific_acceptance": "independent_root_review_required"}
        save_json_exclusive(output / "comparison-completion.json", final)
        print(json.dumps({"status": final["status"], "directory": str(output), "policy_summaries": len(policies)}))
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
