#!/usr/bin/env python3
"""Evaluate explicitly named intermediate checkpoints on CPU while GPU trains."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
CPU = Path.home() / "robotics/envs/himloco-mujoco-py311/bin/python"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-name", required=True)
    p.add_argument("--iterations", type=int, nargs="+", required=True)
    p.add_argument("--timeout-seconds", type=float, default=2400)
    a = p.parse_args()
    output = Path.home() / "robotics/logs" / (a.run_name + "-early-development")
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    scores = []
    for iteration in a.iterations:
        while True:
            paths = list((ROOT / "isaaclab/logs").glob("*_" + a.run_name))
            if len(paths) > 1:
                raise RuntimeError("Ambiguous run name")
            if paths:
                source = paths[0]
                checkpoint = source / f"model_{iteration}.pt"
                if checkpoint.is_file() and time.time() - checkpoint.stat().st_mtime > 2:
                    break
                if (source / "result.json").exists() and not checkpoint.exists():
                    raise RuntimeError("Training finished without requested checkpoint")
            if time.monotonic() - started > a.timeout_seconds:
                raise TimeoutError("Checkpoint wait timed out")
            time.sleep(5)
        directory = output / str(iteration)
        directory.mkdir(exist_ok=False)
        shutil.copyfile(source / "config.json", directory / "config.json")
        policy = directory / "policy.pt"
        print("EARLY_CHECK " + str(iteration), flush=True)
        with (directory / "export-console.txt").open("x") as stream:
            subprocess.run([str(CPU), str(ROOT / "sim2sim/export.py"), str(checkpoint),
                            "--config", str(directory / "config.json"), "--output", str(policy)],
                           cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)
        score = {"iteration": iteration, "development_only": True, "source": str(source),
                 "created_local": datetime.now().astimezone().isoformat(), "results": {}}
        for suite in ("nominal", "deployment"):
            matrix_dir = directory / suite
            with (directory / (suite + "-console.txt")).open("x") as stream:
                subprocess.run([str(CPU), str(ROOT / "sim2sim/matrix.py"), "--policy", str(policy),
                                "--config", str(directory / "config.json"), "--output", str(matrix_dir),
                                "--seeds", "4", "--seed-start", "2000", "--suite", suite],
                               cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)
            subprocess.run([str(CPU), str(ROOT / "sim2sim/posture_metrics.py"), str(matrix_dir), "--matrix",
                            "--stride", "5", "--output", str(directory / (suite + "-posture.json"))], cwd=ROOT, check=True)
            matrix = json.loads((matrix_dir / "matrix.json").read_text())
            score["results"][suite] = {"passed": matrix["passed"], "total": matrix["total"],
                                       "summary": matrix["summary"], "source": str(matrix_dir / "matrix.json")}
        scores.append(score)
        (output / "scores.json").write_text(json.dumps(scores, indent=2) + "\n")
        print("EARLY_SCORE " + json.dumps(score), flush=True)


if __name__ == "__main__":
    main()
