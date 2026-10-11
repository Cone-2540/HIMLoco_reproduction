#!/usr/bin/env python3
"""Run one night2 job with durable logs, resource samples and deadline cleanup.

Only arguments after -- are forwarded to the existing simulator entry point.
This wrapper never changes drivers or system settings. A job exit is not a
scientific acceptance claim; evaluate result.json separately.
"""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time


DEADLINE = datetime.fromisoformat("2026-10-12T07:20:00+08:00")


def stop_exact_container_job(name, force=False):
    script = """import os, signal, sys
name = sys.argv[1]
requested_signal = signal.SIGKILL if sys.argv[2] == 'kill' else signal.SIGTERM
for directory in os.listdir('/proc'):
    if not directory.isdigit() or int(directory) == os.getpid():
        continue
    try:
        args = open('/proc/' + directory + '/cmdline', 'rb').read().split(b'\\0')
        args = [arg.decode(errors='replace') for arg in args if arg]
        if '/workspace/himloco/isaaclab/run.py' in args and '--run_name' in args:
            index = args.index('--run_name')
            if index + 1 < len(args) and args[index + 1] == name:
                os.kill(int(directory), requested_signal)
                print('terminated task process', directory)
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        pass
"""
    return subprocess.run(["docker", "exec", "isaaclab-local-lab-1", "/isaac-sim/kit/python/bin/python3", "-c", script, name,
                           "kill" if force else "terminate"],
                          capture_output=True, text=True, timeout=20)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--max-seconds", type=float, default=3600)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.name.startswith("night2-") or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in args.name):
        parser.error("Use a simple, unique night2- job name")
    forwarded = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
    if not forwarded or forwarded[0] not in ("train", "evaluate", "play"):
        parser.error("Forward train/evaluate/play arguments after --")
    if "--run_name" in forwarded:
        parser.error("The wrapper supplies --run_name")
    now = datetime.now().astimezone()
    remaining = (DEADLINE - now).total_seconds()
    if remaining <= 0:
        parser.error("The user-authorized deadline has passed")
    root = Path(__file__).resolve().parents[1]
    stamp = now.strftime("%Y%m%d-%H%M%S")
    directory = Path.home() / "robotics/logs" / (stamp + "_" + args.name)
    directory.mkdir(parents=True, exist_ok=False)
    command = ["bash", str(root / "isaaclab/run.sh"), *forwarded,
               "--run_name", args.name, "--shutdown_timeout", "20", "--viz", "none"]
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    source_dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip())
    source_paths = ["isaaclab/run.py", "isaaclab/stair_rewards.py", "isaaclab/stair_terrain.py",
                    "isaaclab/stair_evaluation.py", "isaaclab/adapter.py"]
    record = {"name": args.name, "command": command, "started_local": now.isoformat(),
              "deadline_local": DEADLINE.isoformat(), "timeout_seconds": min(args.max_seconds, remaining),
              "source_commit": source, "source_dirty": source_dirty,
              "source_sha256": {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_paths},
              "status": "started", "exit_code": None, "scientific_acceptance": "NOT_ASSESSED"}
    record_path = directory / "launch-record.json"
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    stop = threading.Event()

    def monitor():
        with (directory / "gpu-resource.csv").open("x") as stream:
            stream.write("local_time,name,driver_version,memory_used_mib,memory_total_mib,temperature_c,power_w,utilization_percent\n")
            while not stop.is_set():
                try:
                    sample = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.used,memory.total,temperature.gpu,power.draw,utilization.gpu", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)
                    if sample.returncode == 0:
                        for row in sample.stdout.strip().splitlines():
                            stream.write(datetime.now().astimezone().isoformat() + "," + row + "\n")
                        stream.flush()
                except (OSError, subprocess.TimeoutExpired):
                    pass
                stop.wait(10)

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    print("JOB_LOG: " + str(directory), flush=True)
    started = time.monotonic()
    with (directory / "stdout.log").open("x") as output:
        process = subprocess.Popen(command, cwd=root, stdout=output, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        record["host_wrapper_child_pid"] = process.pid
        record_path.write_text(json.dumps(record, indent=2) + "\n")
        try:
            process.wait(timeout=record["timeout_seconds"])
            record["status"] = "exited" if process.returncode == 0 else "failed"
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            record["status"] = "deadline_or_operator_interrupted"
            try:
                cleanup = stop_exact_container_job(args.name)
                record["task_cleanup"] = {"exit_code": cleanup.returncode,
                                          "stdout": cleanup.stdout, "stderr": cleanup.stderr}
            except (OSError, subprocess.TimeoutExpired) as error:
                record["task_cleanup_error"] = str(error)
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                cleanup = stop_exact_container_job(args.name, force=True)
                record["task_force_cleanup"] = {"exit_code": cleanup.returncode,
                                                 "stdout": cleanup.stdout, "stderr": cleanup.stderr}
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
        finally:
            stop.set()
            thread.join(timeout=12)
            record.update(exit_code=process.returncode,
                          ended_local=datetime.now().astimezone().isoformat(),
                          elapsed_seconds=time.monotonic() - started)
            with (directory / "stdout.log").open(errors="replace") as stream:
                run_lines = [line[5:].strip() for line in stream if line.startswith("RUN: ")]
            if run_lines:
                path = Path(run_lines[-1].replace("/workspace/himloco", str(root), 1))
                record["simulator_log_dir"] = str(path)
                if (path / "result.json").exists():
                    record["result_json"] = str(path / "result.json")
            record_path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2), flush=True)
    raise SystemExit(0 if process.returncode == 0 else (process.returncode or 1))


if __name__ == "__main__":
    main()
