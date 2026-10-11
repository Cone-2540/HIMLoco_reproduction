#!/usr/bin/env python3
"""Inspect explicit night2 log directories without importing Torch or a simulator.

Example:
  python3 reproduction/inspect-stair-night2-training.py \
    --wrapper-dir /home/cone/robotics/logs/20261012-005016_night2-faithful-seed1201-plus100

Repeat --wrapper-dir to compare actually launched arms. --log-dir accepts a
simulator directory directly; --stdout-log may supply its separate console log.
Only --output writes a file. Training metrics and a clean training exit do not
establish stair traversal, reward causality or smoothness.
"""

import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import struct


ROOT = Path(__file__).resolve().parents[1]
LOCAL_ZONE = timezone(timedelta(hours=8))
ANSI = re.compile(r"\x1b\[[0-9;]*m")
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
UPDATE = re.compile(r"Learning iteration (\d+)/(\d+)")
SIGNIFICANT_WARNING = re.compile(
    r"Traceback|(?:RuntimeError|ValueError|AssertionError):|Non-finite|"
    r"CUDA out of memory|(?:nan|inf)\b.*(?:loss|gradient|parameter)|"
    r"(?:loss|gradient|parameter).*\b(?:nan|inf)\b|"
    r"GPU.*(?:capacity|overflow)|out of.*(?:buffer|memory)", re.I
)
EXPECTED_FAITHFUL = {
    "track_lin_vel_xy_exp": 1.0, "track_ang_vel_z_exp": 0.5,
    "lin_vel_z_l2": -2.0, "ang_vel_xy_l2": -0.05,
    "flat_orientation_l2": -0.2, "dof_acc_l2": -2.5e-7,
    "joint_power": -2e-5, "base_height": -1.0,
    "foot_clearance": -0.01, "action_rate_l2": -0.01,
    "action_smoothness": -0.01,
}


def local_path(path):
    path = str(path)
    if path.startswith("/workspace/himloco/"):
        return ROOT / path[len("/workspace/himloco/"):]
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else ROOT / candidate


def read_small_json(path, issues):
    if not path.exists():
        return None
    if path.stat().st_size > 2 * 1024 * 1024:
        issues.append(f"Skipped {path}: exceeds 2 MiB; this tool inspects training metadata only")
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as error:
        issues.append(f"Could not read complete metadata {path}: {error}")
        return None


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def console_summary(path, last_updates):
    summaries, warnings, current, run_directory, dimensions = [], [], None, None, None
    if path is None or not path.exists():
        return {"path": str(path) if path else None, "exists": False,
                "updates": [], "significant_warnings": []}
    with path.open(errors="replace") as stream:
        for number, original in enumerate(stream, 1):
            line = ANSI.sub("", original).strip()
            if line.startswith("RUN: "):
                run_directory = str(local_path(line[5:]))
            if line.startswith("HIM dimensions:"):
                dimensions = {key: int(value) for key, value in
                              re.findall(r"(actor|frame|critic|actions)=(\d+)", line)}
            if SIGNIFICANT_WARNING.search(line):
                warnings.append({"line": number, "text": line[:600]})
            match = UPDATE.search(line)
            if match:
                if current:
                    summaries.append(current)
                    summaries = summaries[-last_updates:]
                current = {"completed_update_label": int(match[1]),
                           "target_update_label": int(match[2]), "metrics": {}}
            if current:
                speed = re.search(r"Computation:\s*(\d+) steps/s \(collection:\s*(" + NUMBER +
                                  r")s, learning\s*(" + NUMBER + r")s\)", line)
                if speed:
                    current.update(steps_per_second=int(speed[1]),
                                   collection_seconds=float(speed[2]), learning_seconds=float(speed[3]))
                else:
                    scalar = re.match(r"(.+?):\s*(" + NUMBER + r")\s*(?:s)?$", line)
                    if scalar:
                        key, value = scalar[1], float(scalar[2])
                        current["metrics"][key] = value
                        if key == "Iteration time":
                            current["iteration_seconds"] = value
                        if key == "ETA":
                            current["console_block_complete"] = True
    if current:
        summaries.append(current)
    return {"path": str(path), "exists": True, "bytes": path.stat().st_size,
            "simulator_log_dir": run_directory, "dimensions": dimensions,
            "updates": summaries[-last_updates:], "significant_warnings": warnings[-20:]}


def proto_fields(data):
    """Read the few protobuf wire types used by TensorBoard Event scalars."""
    index = 0
    def varint():
        nonlocal index
        value, shift = 0, 0
        while index < len(data) and shift < 70:
            byte = data[index]
            index += 1
            value |= (byte & 127) << shift
            if not byte & 128:
                return value
            shift += 7
        raise ValueError("Truncated or oversized protobuf varint")
    while index < len(data):
        tag = varint()
        field, wire = tag >> 3, tag & 7
        if wire == 0:
            value = varint()
        elif wire in (1, 5):
            width = 8 if wire == 1 else 4
            value = data[index:index + width]
            index += width
            if len(value) != width:
                raise ValueError("Truncated fixed-width protobuf field")
        elif wire == 2:
            width = varint()
            value = data[index:index + width]
            index += width
            if len(value) != width:
                raise ValueError("Truncated protobuf byte field")
        else:
            raise ValueError(f"Unsupported protobuf wire type {wire}")
        yield field, wire, value


def event_scalars(data):
    step, summary = 0, None
    for field, wire, value in proto_fields(data):
        if field == 2 and wire == 0:
            step = value
        elif field == 5 and wire == 2:
            summary = value
    if summary is None:
        return
    for field, wire, scalar in proto_fields(summary):
        if field != 1 or wire != 2:
            continue
        tag, simple = None, None
        for key, kind, value in proto_fields(scalar):
            if key == 1 and kind == 2:
                tag = value.decode("utf-8", errors="replace")
            elif key == 2 and kind == 5:
                simple = struct.unpack("<f", value)[0]
        if tag is not None and simple is not None:
            yield tag, step + 1, simple


def tensorboard_summary(directory, last_updates, issues):
    latest, by_update, files, nonfinite = {}, {}, [], []
    for path in sorted(directory.glob("events.out.tfevents.*")):
        if path.stat().st_size > 64 * 1024 * 1024:
            issues.append(f"Skipped event file over 64 MiB: {path}")
            continue
        records, incomplete = 0, False
        try:
            with path.open("rb") as stream:
                while header := stream.read(12):
                    if len(header) != 12:
                        incomplete = True
                        break
                    size = struct.unpack("<Q", header[:8])[0]
                    if size > 16 * 1024 * 1024:
                        raise ValueError("Event record exceeds 16 MiB")
                    data = stream.read(size)
                    crc = stream.read(4)
                    if len(data) != size or len(crc) != 4:
                        incomplete = True
                        break
                    records += 1
                    for tag, update, value in event_scalars(data):
                        if not tag.startswith(("Loss/", "Perf/", "Policy/", "PPO/", "Train/", "Episode_", "Curriculum/", "Metrics/")):
                            continue
                        if not math.isfinite(value):
                            nonfinite.append({"tag": tag, "update": update, "value": str(value)})
                            continue
                        latest[tag] = {"update": update, "value": value}
                        by_update.setdefault(update, {})[tag] = value
        except (OSError, ValueError, struct.error) as error:
            issues.append(f"Event parse failed {path}: {error}")
        files.append({"path": str(path), "bytes": path.stat().st_size,
                      "complete_records": records, "trailing_record_incomplete": incomplete})
    updates = [{"update": update, "scalars": by_update[update]}
               for update in sorted(by_update)[-last_updates:]]
    return {"files": files, "latest_scalars": latest, "updates": updates,
            "nonfinite_scalars": nonfinite[-20:],
            "read_scope": "Standard-library TFRecord/protobuf simple_value reader; incomplete trailing records skipped, CRC32C not validated. Tensor summaries are not decoded. Event step is upstream zero-based update index; reported update=step+1."}


def gpu_summary(path):
    maxima, samples, rows_invalid = {}, 0, 0
    if not path.exists():
        return {"path": str(path), "exists": False}
    fields = ("memory_used_mib", "temperature_c", "power_w", "utilization_percent")
    driver_versions = set()
    first, last = None, None
    with path.open() as stream:
        for row in csv.DictReader(stream, skipinitialspace=True):
            try:
                values = {field: float(row[field]) for field in fields}
                if not all(math.isfinite(value) for value in values.values()):
                    raise ValueError("Nonfinite resource sample")
            except (ValueError, KeyError, TypeError):
                rows_invalid += 1
                continue
            samples += 1
            first = first or row.get("local_time")
            last = row.get("local_time")
            driver_versions.add(row.get("driver_version", "unknown"))
            for field, value in values.items():
                maxima[field] = max(maxima.get(field, value), value)
    return {"path": str(path), "exists": True, "samples": samples,
            "invalid_or_partial_rows": rows_invalid, "first_sample_local": first,
            "last_sample_local": last, "maxima": maxima,
            "driver_versions": sorted(driver_versions),
            "scope": "All host GPU processes at approximately 10-second cadence; neither whole-run instantaneous peak nor training-only allocated memory."}


def command_option(command, flag):
    if flag not in command:
        return None
    index = command.index(flag)
    return command[index + 1] if index + 1 < len(command) else None


def process_handle(record):
    pid = record.get("host_wrapper_child_pid")
    if not pid:
        return {"verified_live": False, "reason": "No PID handle recorded"}
    try:
        arguments = (Path("/proc") / str(pid) / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        matches = record.get("name", "") in arguments and ("run.sh" in arguments or
                  "/workspace/himloco/isaaclab/run.py" in arguments)
        return {"pid": pid, "verified_live": matches, "matching_command": arguments[:500] if matches else None,
                "reason": None if matches else "PID exists but does not match exact task command; possible PID reuse"}
    except OSError:
        return {"pid": pid, "verified_live": False, "reason": "Recorded host process handle is absent"}


def inspect_job(wrapper_directory, log_directory, stdout_path, last_updates, expected_start_sha256):
    issues = []
    launch = read_small_json(wrapper_directory / "launch-record.json", issues) if wrapper_directory else None
    launch = launch or {}
    if stdout_path is None and wrapper_directory:
        stdout_path = wrapper_directory / "stdout.log"
    console = console_summary(stdout_path, last_updates)
    if log_directory is None:
        reported = launch.get("simulator_log_dir") or console.get("simulator_log_dir")
        log_directory = local_path(reported) if reported else None
    config = read_small_json(log_directory / "config.json", issues) if log_directory else None
    result = read_small_json(log_directory / "result.json", issues) if log_directory else None
    if config and config.get("mode") != "train":
        issues.append("Config mode is not train; training completion checks are inapplicable")
    config = config or {}
    runtime = config.get("runtime_training_state_before_learning", {})
    initial_domain = read_small_json(log_directory / "domain-parameters-initial.json", issues) if log_directory else None
    physics_diagnostic = read_small_json(log_directory / "physics-diagnostic.json", issues) if log_directory else None
    train = config.get("train", {})
    steps = train.get("runner", {}).get("num_steps_per_env")
    envs = config.get("num_envs")
    start = runtime.get("completed_updates")
    requested = config.get("requested_additional_training_updates")
    checkpoint = local_path(config["checkpoint"]) if config.get("checkpoint") else None
    checkpoint_sha = digest(checkpoint) if checkpoint and checkpoint.exists() else None
    profile = config.get("stair_reward", {}).get("profile")
    expected_rewards = dict(EXPECTED_FAITHFUL)
    if profile in ("contact", "contact_vertical", "contact_clearance"):
        expected_rewards["leg_contacts"] = -.1
    if profile == "contact_light":
        expected_rewards["leg_contacts"] = -.02
    if profile == "contact_vertical":
        expected_rewards["lin_vel_z_l2"] = -1.
    if profile == "contact_clearance":
        expected_rewards["foot_clearance"] = -.02
    if profile == "faithful_tracking":
        expected_rewards["track_lin_vel_xy_exp"] = 1.5
    checks = []
    def check(name, actual, expected):
        checks.append({"name": name, "status": "unknown" if actual is None or expected is None else
                       "pass" if actual == expected else "fail", "actual": actual, "expected": expected})
    if profile in ("faithful", "faithful_tracking", "contact", "contact_light", "contact_vertical", "contact_clearance"):
        check("exact_known_profile_weights", config.get("reward_weights"), expected_rewards)
    check("config_source_matches_launch", config.get("source_commit"), launch.get("source_commit"))
    check("starting_checkpoint_sha256", checkpoint_sha, expected_start_sha256)
    command = launch.get("command", [])
    for key, flag in (("num_envs", "--num_envs"), ("requested_additional_training_updates", "--max_iterations"), ("seed", "--seed")):
        value = command_option(command, flag)
        check("request_" + key, config.get(key), int(value) if value else None)
    check("request_steps_per_env", steps, int(command_option(command, "--steps_per_env")) if command_option(command, "--steps_per_env") else None)
    check("initial_Adam_restore_metadata", runtime.get("optimizer_state"), "checkpoint Adam retained" if checkpoint else None)
    if initial_domain:
        for name in ("base_mass_kg", "base_inertia_kg_m2"):
            check("initial_" + name + "_finite", initial_domain.get(name, {}).get("observed", {}).get("finite"), True)
        if profile in ("contact", "contact_light", "contact_vertical", "contact_clearance"):
            check("leg_reward_resolved_eight_bodies", sorted(config.get("resolved_contact_reward_bodies", [])),
                  sorted(f"{leg}_{part}" for leg in ("FL", "FR", "RL", "RR") for part in ("thigh", "calf")))
    if physics_diagnostic:
        check("critic_runtime_dimensions", physics_diagnostic.get("critic_shape"), [envs, 235] if envs is not None else None)
    if result:
        check("result_num_envs", result.get("num_envs"), envs)
        check("result_requested_updates", result.get("iterations"), requested)
        check("result_completed_updates", result.get("completed_iterations"), start + requested if start is not None and requested is not None else None)
        check("result_environment_steps", result.get("environment_steps_this_run"), envs * steps * requested if all(value is not None for value in (envs, steps, requested)) else None)
        check("final_parameters_finite", result.get("parameters_finite"), True)
        saved = log_directory / result["checkpoint"] if result.get("checkpoint") else None
        check("final_checkpoint_file_exists_nonempty", bool(saved and saved.exists() and saved.stat().st_size), True)
    source_checks = [{"path": path, "launch_sha256": value,
                      "current_sha256": digest(ROOT / path) if (ROOT / path).exists() else None}
                     for path, value in launch.get("source_sha256", {}).items()]
    for entry in source_checks:
        entry["matches_launch"] = entry["launch_sha256"] == entry["current_sha256"]
    tb = tensorboard_summary(log_directory, last_updates, issues) if log_directory else None
    if tb and tb["nonfinite_scalars"]:
        issues.append("Nonfinite training event scalars observed")
    if console["significant_warnings"]:
        issues.append("Significant runtime warnings/errors observed; inspect listed lines")
    signature_keys = ("task", "seed", "num_envs", "train", "physics", "torch", "cuda", "gpu_capability",
                      "robot_usd", "physics_dt", "policy_decimation", "episode_length_s", "observation",
                      "command_override", "training_turn_fraction", "exploration_std_override", "resume_learning_rate_override",
                      "requested_additional_training_updates", "terrain_start_level", "stair_training_speed_range_m_s",
                      "terrain", "stairs", "domain_randomization", "calf_limit_sensitivity", "friction_override",
                      "stair_pushes", "flat_replay", "joint_names", "default_joint_positions", "action_scale",
                      "runtime_training_state_before_learning", "reward_frame_validation")
    signature = {key: config.get(key) for key in signature_keys} if config else None
    if signature:
        signature["starting_checkpoint_sha256"] = checkpoint_sha
        signature["source_sha256_at_launch"] = launch.get("source_sha256")
        if initial_domain:
            physical = {key: value for key, value in initial_domain.items() if key != "terrain_material"}
            # An anonymous USD layer identifier differs across recreations and
            # is not a physical material property.
            terrain = initial_domain.get("terrain_material", {})
            physical["terrain_material"] = {key: value for key, value in terrain.items()
                                            if key != "stage_root_layer_identifier"}
            signature["initial_domain_readback_sha256_normalized"] = hashlib.sha256(
                json.dumps(physical, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return {"name": launch.get("name") or (log_directory.name if log_directory else str(wrapper_directory)),
            "wrapper_directory": str(wrapper_directory) if wrapper_directory else None,
            "simulator_log_directory": str(log_directory) if log_directory else None,
            "declared_wrapper_status": launch.get("status"), "wrapper_exit_code": launch.get("exit_code"),
            "host_process_handle": process_handle(launch), "reward_profile": profile,
            "starting_checkpoint": str(checkpoint) if checkpoint else None, "starting_checkpoint_sha256": checkpoint_sha,
            "source_commit": config.get("source_commit"), "source_checks_against_current_files": source_checks,
            "runtime_training_state_before_learning": runtime, "completion_checks": checks,
            "initial_domain_readback_scope": initial_domain.get("scope") if initial_domain else None,
            "domain_profile_interpretation": "In train mode, domain_profile=none disables the additional robust profile but retains existing startup mass/COM events. Default stair evaluation with eval_dynamics=false removes mass/COM/gain randomization. Use mode, flags and saved physical readbacks to determine the actual setup.",
            "initial_mass_kg_summary": {key: value for key, value in initial_domain.get("base_mass_kg", {}).get("observed", {}).items()
                                        if key != "samples_first_envs"} if initial_domain else None,
            "physics_diagnostic": physics_diagnostic,
            "saved_model_file_labels": sorted(int(match[1]) for path in log_directory.glob("model_*.pt")
                                               if (match := re.fullmatch(r"model_(\d+)\.pt", path.name))) if log_directory else [],
            "checkpoint_scope": "File labels/existence and simulator result metadata only; Torch checkpoint iter/Adam tensors are not independently decoded.",
            "result": result, "console": console, "tensorboard": tb,
            "gpu": gpu_summary(wrapper_directory / "gpu-resource.csv") if wrapper_directory else None,
            "common_parameter_signature": signature, "issues": issues}


def compare_jobs(jobs):
    ready = [job for job in jobs if job["common_parameter_signature"]]
    mismatches = []
    if len(ready) < 2:
        return {"status": "insufficient_started_jobs", "configured_jobs": len(ready),
                "scope": "Needs at least two actual training configurations; plans alone do not establish a matched comparison."}
    base = ready[0]
    for job in ready[1:]:
        left, right = base["common_parameter_signature"], job["common_parameter_signature"]
        for key in sorted(set(left) | set(right)):
            if left.get(key) != right.get(key):
                mismatches.append({"reference": base["name"], "other": job["name"], "parameter": key,
                                   "reference_value": left.get(key), "other_value": right.get(key)})
    return {"status": "mismatch" if mismatches else "matched_available_metadata",
            "configured_jobs": len(ready), "mismatches": mismatches,
            "profiles": [job["reward_profile"] for job in ready],
            "scope": "Configuration, exact starting checkpoint hash and selected source hashes; differing reward profiles/weights are intentional. No claim of identical GPU trajectories, all physical tensors, initial RNG state or causal effect across training seeds."}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--wrapper-dir", action="append", default=[], type=Path)
    parser.add_argument("--log-dir", action="append", default=[], type=Path)
    parser.add_argument("--stdout-log", action="append", default=[], type=Path,
                        help="Console log for each directly supplied --log-dir, in matching order")
    parser.add_argument("--last-updates", type=int, default=3)
    parser.add_argument("--output", type=Path, help="Optional explicit audit JSON destination")
    parser.add_argument("--plan", type=Path, default=ROOT / "reproduction/stair-night2-training-plan.json",
                        help="Small frozen training plan supplying expected start checkpoint hash")
    parser.add_argument("--json", action="store_true", help="Print the full compact audit instead of one summary per job")
    args = parser.parse_args()
    if not args.wrapper_dir and not args.log_dir:
        parser.error("Supply explicit --wrapper-dir or --log-dir")
    if not 1 <= args.last_updates <= 100:
        parser.error("--last-updates must be1..100")
    if args.stdout_log and len(args.stdout_log) != len(args.log_dir):
        parser.error("Supply one --stdout-log per --log-dir, or none")
    plan_issues = []
    plan = read_small_json(args.plan.expanduser().resolve(), plan_issues) or {}
    expected_start_sha256 = plan.get("checkpoint_sha256")
    jobs = [inspect_job(path.expanduser().resolve(), None, None, args.last_updates, expected_start_sha256) for path in args.wrapper_dir]
    for index, path in enumerate(args.log_dir):
        stdout = args.stdout_log[index].expanduser().resolve() if args.stdout_log else None
        jobs.append(inspect_job(None, path.expanduser().resolve(), stdout, args.last_updates, expected_start_sha256))
    report = {"schema_version": 1, "inspected_local": datetime.now(LOCAL_ZONE).isoformat(),
              "scope": "CPU read-only training evidence; no simulator/Torch import or GPU calls. Training reward, curriculum and successful exit are not stair/smoothness acceptance.",
              "plan_path": str(args.plan), "plan_read_issues": plan_issues,
              "jobs": jobs, "matched_arm_comparison": compare_jobs(jobs)}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    else:
        for job in jobs:
            blocks = job["console"]["updates"]
            latest = blocks[-1] if blocks else None
            if latest:
                latest = {**latest, "metrics": {key: value for key, value in latest["metrics"].items()
                           if key in ("Mean reward", "Mean episode length", "Mean action noise std", "Value function loss", "Surrogate loss", "Estimation loss", "Swap loss", "ETA") or "levels_mean" in key}}
            scalars = (job["tensorboard"] or {}).get("latest_scalars", {})
            selected = {key: value for key, value in scalars.items() if key.startswith("PPO/") or key == "Loss/learning_rate"}
            print(json.dumps({"name": job["name"], "declared_status": job["declared_wrapper_status"],
                              "host_handle_live": job["host_process_handle"]["verified_live"],
                              "profile": job["reward_profile"], "latest_console_update": latest,
                              "PPO_latest": selected, "saved_model_labels": job["saved_model_file_labels"],
                              "result": job["result"], "gpu_maxima": (job["gpu"] or {}).get("maxima"),
                              "failed_checks": [check for check in job["completion_checks"] if check["status"] == "fail"],
                              "issues": job["issues"]}, ensure_ascii=False, allow_nan=False))
        print(json.dumps({"matched_arm_comparison": report["matched_arm_comparison"],
                          "audit_output": str(args.output) if args.output else None}, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
