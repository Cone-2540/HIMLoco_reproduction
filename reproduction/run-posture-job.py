#!/usr/bin/env python3
"""Bounded Isaac Lab job, exact-process cleanup and read-only GPU monitoring.

This new daytime authorization has no inherited overnight deadline. Each job
still has an explicit duration bound. Driver and system settings are never
changed. Simulator exit and locomotion acceptance are recorded separately.
"""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("previous_job_cleanup", ROOT / "reproduction/run-night3-job.py")
cleanup_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup_module)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--max-seconds", type=float, default=3600)
    parser.add_argument("--gpu-cap-mib", type=int, default=15360)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.name.startswith("posture-") or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.name):
        parser.error("Use a unique lowercase posture- job name")
    forwarded = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
    if not forwarded or forwarded[0] not in ("train", "evaluate", "play") or "--run_name" in forwarded:
        parser.error("Forward train/evaluate/play after --; wrapper supplies run_name")
    if args.max_seconds <= 0 or not 1024 <= args.gpu_cap_mib <= 15360:
        parser.error("Require positive timeout and GPU cap <= 15360 MiB")
    probe = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
    if probe.returncode:
        raise SystemExit("Docker unavailable: " + probe.stderr.strip())
    directory = Path.home() / "robotics/logs" / (datetime.now().astimezone().strftime("%Y%m%d-%H%M%S_") + args.name)
    directory.mkdir(parents=True, exist_ok=False)
    command = ["bash", str(ROOT / "isaaclab/run.sh"), *forwarded,
               "--run_name", args.name, "--shutdown_timeout", "20"]
    if "--video" not in forwarded:
        command.extend(["--viz", "none"])
    tracked = ["isaaclab/run.py", "isaaclab/stair_rewards.py", "isaaclab/stair_terrain.py",
               "isaaclab/stair_evaluation.py", "isaaclab/adapter.py", "isaaclab/stair_randomization.py",
               "isaaclab/deployment_motor.py"]
    record = {"name": args.name, "command": command, "started_local": datetime.now().astimezone().isoformat(),
              "timeout_seconds": args.max_seconds, "gpu_cap_mib": args.gpu_cap_mib,
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_tracked_files_dirty": bool(subprocess.check_output(
                  ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True).strip()),
              "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tracked},
              "status": "started", "scientific_acceptance": "NOT_ASSESSED", "gpu_peak_mib": 0}
    record_path = directory / "launch-record.json"
    def save():
        temporary = record_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, indent=2) + "\n")
        temporary.replace(record_path)
    save()
    print("JOB_LOG: " + str(directory), flush=True)
    stop, exceeded = threading.Event(), threading.Event()
    def monitor():
        successive_excess = 0
        with (directory / "gpu-resource.csv").open("x") as stream:
            stream.write("local_time,memory_used_mib,utilization_percent,temperature_c,power_w\n")
            while not stop.is_set():
                try:
                    sample = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,utilization.gpu,temperature.gpu,power.draw",
                                             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)
                    if sample.returncode == 0:
                        row = sample.stdout.strip().splitlines()[0]
                        used = int(row.split(",")[0])
                        record["gpu_peak_mib"] = max(record["gpu_peak_mib"], used)
                        stream.write(datetime.now().astimezone().isoformat() + "," + row + "\n")
                        stream.flush()
                        successive_excess = successive_excess + 1 if used > args.gpu_cap_mib else 0
                        if successive_excess >= 2:
                            exceeded.set()
                except (OSError, subprocess.TimeoutExpired, ValueError, IndexError):
                    pass
                stop.wait(2)
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    started = time.monotonic()
    process = None
    try:
        with (directory / "stdout.log").open("x") as output:
            process = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            record["host_wrapper_child_pid"] = process.pid
            save()
            while process.poll() is None:
                if exceeded.is_set() or time.monotonic() - started > args.max_seconds:
                    record["status"] = "gpu_cap_exceeded" if exceeded.is_set() else "duration_limit"
                    break
                time.sleep(1)
            if process.poll() is None:
                cleanup_module.stop_exact_container_job(args.name)
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    cleanup_module.stop_exact_container_job(args.name, force=True)
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)
            if record["status"] == "started":
                record["status"] = "exited" if process.returncode == 0 else "failed"
    except KeyboardInterrupt:
        record["status"] = "operator_interrupted"
        if process is not None and process.poll() is None:
            cleanup_module.stop_exact_container_job(args.name)
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                cleanup_module.stop_exact_container_job(args.name, force=True)
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
    finally:
        stop.set()
        thread.join(timeout=12)
        try:
            cleanup = cleanup_module.stop_exact_container_job(args.name)
            record["post_exit_task_cleanup"] = {"exit_code": cleanup.returncode,
                                                 "stdout": cleanup.stdout, "stderr": cleanup.stderr}
            if cleanup.stdout.strip():
                time.sleep(2)
                cleanup_module.stop_exact_container_job(args.name, force=True)
        except (OSError, subprocess.TimeoutExpired) as error:
            record["post_exit_task_cleanup_error"] = str(error)
        record.update(exit_code=process.returncode if process is not None else None,
                      ended_local=datetime.now().astimezone().isoformat(), elapsed_seconds=time.monotonic() - started)
        with (directory / "stdout.log").open(errors="replace") as stream:
            paths = [line[5:].strip() for line in stream if line.startswith("RUN: ")]
        if paths:
            log = Path(paths[-1].replace("/workspace/himloco", str(ROOT), 1))
            record["simulator_log_dir"] = str(log)
            if (log / "result.json").is_file():
                record["result_json"] = str(log / "result.json")
        save()
    print(json.dumps(record, indent=2), flush=True)
    raise SystemExit(0 if record["status"] == "exited" else 1)


if __name__ == "__main__":
    main()
