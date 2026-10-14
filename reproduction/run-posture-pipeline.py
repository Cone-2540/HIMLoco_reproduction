#!/usr/bin/env python3
"""Train a conservative posture ablation, then Isaac/MuJoCo/domain checks.

Dry-run is the default. No deployed/frozen policy is overwritten and no model
is promoted automatically. Evaluation metrics remain separate from job exits.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CPU = Path.home() / "robotics/envs/himloco-mujoco-py311/bin/python"
BASELINE = ROOT / "artifacts/go2-night3-selected/model.pt"
EXPECTED = "4e0c046734eda739fbea83ee7177ac7f3a6dbd35ef5fd0dae0a83e48f92cd83b"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--wait-for-docker", type=float, default=0,
                   help="Wait this many seconds for the user to restore Docker socket access.")
    p.add_argument("--num-envs", type=int, default=8192)
    p.add_argument("--updates", type=int, default=120)
    p.add_argument("--posture-weight", type=float, default=-.08)
    p.add_argument("--reward-profile", choices=["posture", "posture_contact", "posture_symmetric"], default="posture")
    p.add_argument("--symmetry-weight", type=float, default=-.08)
    p.add_argument("--checkpoint", type=Path, default=BASELINE)
    p.add_argument("--start-iteration", type=int, default=860)
    p.add_argument("--seed", type=int, default=2001)
    p.add_argument("--tag", default="20261014-weak")
    a = p.parse_args()
    if a.updates < 40 or a.updates % 40 or a.num_envs < 128 or any(c not in "0123456789abcdefghijklmnopqrstuvwxyz-" for c in a.tag):
        p.error("Use updates divisible by 40, num-envs>=128 and a simple unique tag")
    if hashlib.sha256(BASELINE.read_bytes()).hexdigest() != EXPECTED:
        raise SystemExit("Frozen baseline identity changed")
    if not a.checkpoint.is_file():
        p.error("Checkpoint does not exist")
    name = "posture-" + a.tag
    train = ["train", "--terrain", "stairs", "--reward_profile", a.reward_profile,
             "--posture_weight", str(a.posture_weight), "--posture_angle_deg", "65",
             "--posture_swing_weight", ".25", "--symmetry_weight", str(a.symmetry_weight),
             "--checkpoint", str(a.checkpoint.resolve()),
             "--stair_stage", "paper_mixed", "--start_level", "4", "--domain_profile", "deployment",
             "--learning_rate", ".00005", "--resume_learning_rate", ".00005", "--lr_schedule", "fixed",
             "--seed", str(a.seed), "--stair_speed_range", ".25", ".65",
             "--flat_replay_fraction", ".25", "--flat_replay_all_directions"]
    smoke = [*train, "--num_envs", "128", "--steps_per_env", "24", "--max_iterations", "3", "--save_interval", "1"]
    formal = [*train, "--num_envs", str(a.num_envs), "--steps_per_env", "100",
              "--max_iterations", str(a.updates), "--save_interval", "20"]
    checkpoints = list(range(a.start_iteration + 40, a.start_iteration + a.updates + 1, 40))
    evaluation = ["evaluate", "--terrain", "stairs", "--reward_profile", "faithful",
                  "--checkpoint", str(BASELINE), "--stair_batch", str(ROOT / "reproduction/posture-20261014-geometries.json"),
                  "--num_envs", "512", "--eval_seed", "2000", "--eval_seed", "2003",
                  "--eval_randomized", "--eval_seconds", "25", "--speed", ".3", "--seed", "2000"]
    plan = {"frozen_baseline_sha256": EXPECTED, "training": formal, "smoke": smoke,
            "training_checkpoint_sha256": hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
            "training_start_iteration": a.start_iteration,
            "candidate_iterations": checkpoints, "isaac_nominal_paired": evaluation,
            "mujoco": {"development_seed_start": 2000, "seeds_per_case": 4,
                       "suites": ["nominal", "deployment"], "final_seed_start_reserved": 2400},
            "gpu_cap_mib": 15360, "original_model_overwrite": False,
            "automatic_model_promotion": False, "new_paper_reward_adaptation": a.reward_profile,
            "domain_training": "retain existing deployment distribution; domain tests follow nominal sim2sim"}
    if not a.execute:
        print(json.dumps(plan, indent=2))
        return
    deadline = time.monotonic() + a.wait_for_docker
    while True:
        probe = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
        if probe.returncode == 0:
            break
        if time.monotonic() >= deadline:
            raise SystemExit("Docker socket access unavailable; no GPU job was started. " + probe.stderr.strip())
        print("Waiting for restored Docker socket access", flush=True)
        time.sleep(10)
    directory = Path.home() / "robotics/logs" / (name + "-pipeline")
    directory.mkdir(parents=True, exist_ok=False)
    progress = {"plan": plan, "started_local": datetime.now().astimezone().isoformat(), "jobs": [], "candidates": []}
    progress_path = directory / "pipeline.json"
    def save():
        temporary = progress_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(progress, indent=2) + "\n")
        temporary.replace(progress_path)
    save()

    def job(label, seconds, arguments):
        command = [sys.executable, str(ROOT / "reproduction/run-posture-job.py"),
                   "--name", name + "-" + label, "--max-seconds", str(seconds), "--", *arguments]
        output = directory / (label + "-launcher.txt")
        print("START " + label, flush=True)
        with output.open("x") as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        lines = output.read_text().splitlines()
        logs = [Path(line[9:]) for line in lines if line.startswith("JOB_LOG: ")]
        record = json.loads((logs[-1] / "launch-record.json").read_text()) if logs else {
            "status": "launch_failed", "launcher_output": str(output), "exit_code": result.returncode}
        progress["jobs"].append(record)
        save()
        if result.returncode or record["status"] != "exited":
            raise RuntimeError(label + " did not finish: " + str(record))
        return Path(record["simulator_log_dir"])

    try:
        job("smoke", 240, smoke)
        source = job("train", max(3600, a.updates * 30), formal)
        for i in checkpoints:
            if not (source / f"model_{i}.pt").is_file():
                raise RuntimeError("Checkpoint iteration does not match declared start iteration")
        artifacts = ROOT / "artifacts" / name
        artifacts.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(source / "config.json", artifacts / "config.json")
        for i in checkpoints:
            shutil.copyfile(source / f"model_{i}.pt", artifacts / f"model_{i}.pt")
        args_eval = list(evaluation)
        for i in checkpoints:
            args_eval.extend(["--candidate_checkpoint", str(artifacts / f"model_{i}.pt")])
        isaac = job("isaac-nominal", 900, args_eval)
        progress["isaac_nominal_result"] = str(isaac / "result.json")
        save()
        for i in checkpoints:
            policy = artifacts / f"policy_{i}.pt"
            with (directory / f"export-{i}.txt").open("x") as stream:
                subprocess.run([str(CPU), str(ROOT / "sim2sim/export.py"), str(artifacts / f"model_{i}.pt"),
                                "--config", str(artifacts / "config.json"), "--output", str(policy)],
                               cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)
            candidate = {"iteration": i, "policy": str(policy), "matrices": {}}
            for suite in ("nominal", "deployment"):
                output = directory / f"iter{i}-{suite}"
                with (directory / f"iter{i}-{suite}-console.txt").open("x") as stream:
                    subprocess.run([str(CPU), str(ROOT / "sim2sim/matrix.py"), "--policy", str(policy),
                                    "--config", str(artifacts / "config.json"), "--output", str(output),
                                    "--seeds", "4", "--seed-start", "2000", "--suite", suite,
                                    "--record-policy-input"],
                                   cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)
                subprocess.run([str(CPU), str(ROOT / "sim2sim/posture_metrics.py"), str(output),
                                "--matrix", "--stride", "5", "--output", str(directory / f"iter{i}-{suite}-posture.json")],
                               cwd=ROOT, check=True)
                matrix = json.loads((output / "matrix.json").read_text())
                candidate["matrices"][suite] = {"passed": matrix["passed"], "total": matrix["total"],
                                                 "summary": matrix["summary"], "source": str(output / "matrix.json")}
            progress["candidates"].append(candidate)
            save()
        domain_args = [*args_eval, "--domain_profile", "deployment", "--eval_dynamics"]
        isaac_domain = job("isaac-domain", 900, domain_args)
        progress["isaac_domain_result"] = str(isaac_domain / "result.json")
        progress["status"] = "development_evidence_ready_no_promotion"
    except Exception as error:
        progress["status"] = "failed"
        progress["error"] = f"{type(error).__name__}: {error}"
        save()
        raise
    finally:
        progress["ended_local"] = datetime.now().astimezone().isoformat()
        save()
    print("PIPELINE_EVIDENCE: " + str(progress_path), flush=True)


if __name__ == "__main__":
    main()
