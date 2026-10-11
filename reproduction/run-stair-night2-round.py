#!/usr/bin/env python3
"""Execute matched saved-update reward arms; development evaluation is separate."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1201)
    parser.add_argument("--profiles", nargs="+", choices=["faithful", "faithful_tracking", "contact", "contact_light", "contact_vertical", "contact_clearance"],
                        default=["faithful", "contact", "contact_vertical", "contact_clearance"])
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--plan", type=Path,
                        default=Path(__file__).resolve().parent / "stair-night2-training-plan.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    plan = json.loads(args.plan.expanduser().resolve().read_text())
    common = plan["common"]
    for profile in args.profiles:
        now = datetime.now().astimezone()
        if now >= datetime.fromisoformat(plan["stop_new_training_by_local"]):
            print("No new training: validation/closeout time reserve reached", flush=True)
            raise SystemExit(2)
        name = f"night2-{profile}-seed{args.seed}-plus{args.iterations}"
        command = [sys.executable, str(root / "reproduction/run-stair-night2-job.py"),
                   "--name", name, "--max-seconds", "3600", "--", "train",
                   "--terrain", "stairs", "--stair_stage", common["stair_stage"],
                   "--reward_profile", profile, "--checkpoint", plan["checkpoint"],
                   "--num_envs", str(common["num_envs"]), "--steps_per_env", str(common["steps_per_env"]),
                   "--max_iterations", str(args.iterations), "--save_interval", str(common["save_interval"]),
                   "--learning_rate", str(common["ppo_learning_rate"]),
                   "--resume_learning_rate", str(common["him_learning_rate"]),
                   "--lr_schedule", common["lr_schedule"], "--start_level", str(common["start_level"]),
                   "--stair_speed_range", *map(str, common["stair_speed_range"]),
                   "--turn_fraction", str(common["turn_fraction"]),
                   "--domain_profile", common["domain_profile"], "--seed", str(args.seed)]
        print("MATCHED_ARM_START: " + name, flush=True)
        result = subprocess.run(command, cwd=root)
        if result.returncode:
            print("Round stopped at failed/interrupted job; preserve logs", flush=True)
            raise SystemExit(result.returncode)
        print("MATCHED_ARM_DONE: " + name, flush=True)


if __name__ == "__main__":
    main()
