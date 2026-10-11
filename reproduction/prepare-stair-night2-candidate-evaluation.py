#!/usr/bin/env python3
"""Print explicit same-scene development commands; never launch simulation.

Pass four LABEL TRAINING_PROFILE CHECKPOINT triples. The common evaluation
reward profile is kept separate from each policy's training profile. All input
paths must identify existing files inside the current repository.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shlex


ROOT = Path(__file__).resolve().parents[1]


def checkpoint_identity(value):
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve(strict=True)
    relative = path.relative_to(ROOT)
    if not path.is_file():
        raise ValueError(f"Not a checkpoint file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(relative), "sha256": digest.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="artifacts/go2-stairs-control660/model_660.pt")
    parser.add_argument("--candidate", action="append", nargs=3, required=True,
                        metavar=("LABEL", "TRAINING_PROFILE", "CHECKPOINT"))
    parser.add_argument("--evaluation_profile", default="contact")
    parser.add_argument("--speed", action="append", type=float, choices=(0.3, 0.5))
    parser.add_argument("--include_zero_yaw", action="store_true")
    parser.add_argument("--run_prefix", default="night2-four-arms-development")
    parser.add_argument("--manifest", type=Path, help="Optional new JSON output; refuses overwrite")
    args = parser.parse_args()
    try:
        if len(args.candidate) != 4:
            raise ValueError("Declare exactly four candidate triples")
        labels = [label for label, _, _ in args.candidate]
        if len(set(labels)) != 4 or any(not label for label in labels):
            raise ValueError("Candidate labels must be unique and nonempty")
        baseline = checkpoint_identity(args.baseline)
        candidates = [{"label": label, "training_reward_profile": profile, **checkpoint_identity(path),
                       "expected_child_result_relative_path": f"candidates/{index}_{Path(path).stem}/result.json"}
                      for index, (label, profile, path) in enumerate(args.candidate)]
        speeds = args.speed or [0.3, 0.5]
        if len(set(speeds)) != len(speeds):
            raise ValueError("Duplicate speeds")
        jobs = []
        for speed in speeds:
            for heading in ([True, False] if args.include_zero_yaw else [True]):
                name = args.run_prefix + "-speed" + ("03" if speed == 0.3 else "05") + ("-heading" if heading else "-zero-yaw")
                command = ["bash", "isaaclab/run.sh", "evaluate", "--terrain", "stairs",
                    "--checkpoint", baseline["path"], "--reward_profile", args.evaluation_profile,
                    "--stair_batch", "reproduction/stair-night2-development-geometries.json", "--num_envs", "576",
                    "--speed", str(speed), "--eval_seconds", "40", "--eval_randomized",
                    "--eval_seed", "11", "--eval_seed", "29", "--eval_seed", "47", "--seed", "1",
                    "--domain_profile", "none", "--eval_trace_stride", "1", "--viz", "none", "--run_name", name]
                for candidate in candidates:
                    command += ["--candidate_checkpoint", candidate["path"]]
                if not heading:
                    command.append("--open_loop_heading")
                jobs.append({"speed_m_s": speed, "heading_control_enabled": heading, "run_name": name,
                             "argv": command, "shell_command": shlex.join(command)})
        manifest = {"status": "commands_prepared_not_executed", "stage": "development", "baseline": baseline,
                    "candidate_order": candidates, "evaluation_reward_profile": args.evaluation_profile,
                    "training_profile_is_separate_from_shared_evaluation_rewards": True,
                    "startup_parameter_scope": "default eval removes random mass/COM/gains; common scene physics fixed across policies",
                    "jobs": jobs, "summary_instruction": "Explicitly pass each candidate's corresponding speed result paths to summarize-stair-night2.py --stage development; do not pool different checkpoint hashes or glob final files"}
        if args.manifest:
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            with args.manifest.open("x") as stream:
                json.dump(manifest, stream, indent=2)
                stream.write("\n")
        for job in jobs:
            print(job["shell_command"])
        print(json.dumps({"status": manifest["status"], "jobs": len(jobs), "candidate_order": candidates,
                          "manifest": str(args.manifest) if args.manifest else None}))
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
