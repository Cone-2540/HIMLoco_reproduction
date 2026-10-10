#!/usr/bin/env python3
"""Preview or execute the prescribed staircase/flat replay training jobs.

The default only prints commands. --execute explicitly starts the existing
GPU simulator; its success code means training completed, not goal acceptance.
"""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shlex
import subprocess


def jobs(plan, *, pilot=False, arm=None, seed=None):
    common = plan["common_training"]
    arms = [item for item in plan["arms"] if arm is None or item["id"] == arm]
    seeds = [seed] if seed is not None else common["paired_continuation_seeds"]
    if pilot:
        arms = [item for item in plan["arms"] if item["id"] == "C"]
        seeds = [plan["preflight"]["seed"]]
    for item in arms:
        for continuation_seed in seeds:
            config = plan["preflight"] if pilot else common
            name = (plan["preflight"]["run_name"] if pilot else
                    f"phase1-{item['id']}-seed{continuation_seed}")
            arguments = [
                "train", "--terrain", "stairs", "--stair_stage", common["stair_stage"],
                "--reward_profile", common["reward_profile"],
                "--checkpoint", common["checkpoint"],
                "--num_envs", str(config["num_envs"]),
                "--steps_per_env", str(config.get("steps_per_env", common["policy_steps_per_update"])),
                "--max_iterations", str(config.get("max_iterations", common["saved_updates_per_arm"])),
                "--save_interval", str(config["save_interval"]),
                "--learning_rate", str(common["ppo_learning_rate"]),
                "--resume_learning_rate", str(common["him_learning_rate"]),
                "--lr_schedule", common["lr_schedule"],
                "--start_level", str(common["stair_initial_maximum_level"]),
                "--stair_speed_range", *map(str, common["stair_forward_speed_range"]),
                "--turn_fraction", str(common["turn_fraction"]),
                "--domain_profile", common["domain_profile"],
                "--flat_replay_fraction", str(item["flat_replay_fraction"]),
                "--seed", str(continuation_seed), "--run_name", name, "--viz", "none",
            ]
            if item["flat_replay_all_directions"]:
                arguments.append("--flat_replay_all_directions")
            yield name, arguments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--pilot", action="store_true", help="Three-update preflight, excluded from formal arms.")
    parser.add_argument("--arm", choices=["A", "B", "C"])
    parser.add_argument("--seed", type=int, choices=[1001, 1009, 1013])
    parser.add_argument("--log-root", type=Path)
    args = parser.parse_args()
    if args.pilot and (args.arm is not None or args.seed is not None):
        parser.error("--pilot cannot select a formal arm or continuation seed")
    root = Path(__file__).resolve().parents[1]
    plan_path = root / "reproduction/stair-generalization-phase1-plan.json"
    plan = json.loads(plan_path.read_text())
    checkpoint = root / plan["common_training"]["checkpoint"]
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != plan["common_training"]["checkpoint_sha256"]:
        raise ValueError("The prescribed common starting checkpoint does not match")
    selected = list(jobs(plan, pilot=args.pilot, arm=args.arm, seed=args.seed))
    if not args.execute:
        for _, arguments in selected:
            print(shlex.join(["bash", "isaaclab/run.sh", *arguments]))
        return
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True)
    if dirty.strip():
        raise ValueError("Commit the prepared source and protocol before executing; the worktree must be clean")
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    log_root = args.log_root or Path.home() / "robotics/logs" / f"himloco-generalization-{stamp}"
    # Each invocation preserves its own logs; never overwrite a prior attempt.
    log_root.mkdir(parents=True, exist_ok=False)
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    records = []
    for name, arguments in selected:
        command = ["bash", str(root / "isaaclab/run.sh"), *arguments]
        output = log_root / (name + ".stdout.log")
        print(f"START {name}: {output}", flush=True)
        started = datetime.now().astimezone().isoformat()
        record = {"name": name, "command": command, "source_commit": source_commit,
                  "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                  "checkpoint_sha256": plan["common_training"]["checkpoint_sha256"],
                  "started_local": started, "status": "started",
                  "exit_code": None, "stdout_log": str(output),
                  "pilot_excluded_from_selection": args.pilot}
        records.append(record)
        records_path = log_root / "launch-records.json"
        records_path.write_text(json.dumps(records, indent=2) + "\n")
        with output.open("x") as stream:
            process = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT)
        record.update(ended_local=datetime.now().astimezone().isoformat(),
                      exit_code=process.returncode,
                      status="exited" if process.returncode == 0 else "failed")
        records_path.write_text(json.dumps(records, indent=2) + "\n")
        print(f"END {name}: exit={process.returncode}", flush=True)
        if process.returncode:
            raise SystemExit(process.returncode)


if __name__ == "__main__":
    main()
