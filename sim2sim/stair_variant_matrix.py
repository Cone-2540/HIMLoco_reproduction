#!/usr/bin/env python3
"""Moderate 1/2 cm stair nosings, with paired reset and friction conditions."""
import argparse
import contextlib
from datetime import datetime
import json
from pathlib import Path
import sys

import numpy as np

from run import parse, run


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seed-start", type=int, default=2000)
    p.add_argument("--seeds", type=int, default=4)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    report = {"started_local": datetime.now().astimezone().isoformat(),
              "policy": str(a.policy.resolve()), "seed_start": a.seed_start,
              "seeds_per_case": a.seeds, "trials": [], "summary": [],
              "scope": "six 16 cm x 27 cm steps, 1/2 cm thin overhang, speed .3 m/s; paired initial pose and friction .6/.85/1.1; heading feedback; no mass/gain randomization"}
    path = a.output / "matrix.json"
    for terrain in ("asc", "desc"):
        for nosing in (.01, .02):
            case = f"{terrain}-16x27-nose{round(nosing*100)}cm"
            trials = []
            for index, seed in enumerate(range(a.seed_start, a.seed_start+a.seeds)):
                rng = np.random.default_rng(seed)
                friction = (.6, .85, 1.1)[index % 3]
                sys.argv = ["run", "--policy", str(a.policy), "--config", str(a.config),
                            "--output", str(a.output / f"{case}-seed{seed}"), "--terrain", terrain,
                            "--height", ".16", "--depth", ".27", "--nosing", str(nosing),
                            "--seconds", "25", "--seed", str(seed), "--friction", str(friction),
                            "--initial-yaw", f"{rng.uniform(-.06,.06):.12f}",
                            "--initial-y", f"{rng.uniform(-.04,.04):.12f}",
                            "--initial-joint-noise", ".03", "--heading-feedback",
                            "--record-policy-input", "--record-leg-contacts"]
                with (a.output / "trial-console.txt").open("a") as stream, contextlib.redirect_stdout(stream):
                    result = run(parse())
                row = {k: result[k] for k in ("success", "reason", "simulation_seconds",
                       "calf_loaded_contact_fraction", "calf_peak_normal_force_n", "xy_velocity_mae_m_s",
                       "policy_sha256", "runner_source_sha256", "arguments")}
                row.update(case=case, seed=seed, result_file=str(Path(result["arguments"]["output"]) / "result.json"))
                trials.append(row)
                report["trials"].append(row)
            summary = {"case": case, "passed": sum(t["success"] for t in trials), "total": len(trials),
                       "mean_calf_loaded_contact_fraction": float(np.mean([t["calf_loaded_contact_fraction"] for t in trials])),
                       "max_calf_normal_force_n": max(t["calf_peak_normal_force_n"] for t in trials),
                       "mean_xy_velocity_mae_m_s": float(np.mean([t["xy_velocity_mae_m_s"] for t in trials]))}
            report["summary"].append(summary)
            path.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(summary), flush=True)
    report.update(passed=sum(t["success"] for t in report["trials"]), total=len(report["trials"]),
                  ended_local=datetime.now().astimezone().isoformat())
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"TOTAL {report['passed']}/{report['total']}")


if __name__ == "__main__":
    main()
