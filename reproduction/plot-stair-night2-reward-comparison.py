#!/usr/bin/env python3
"""Plot archived, paired Night2 development evidence using CPU only.

Examples:
  python3 -B reproduction/plot-stair-night2-reward-comparison.py --check-only
  python3 -B reproduction/plot-stair-night2-reward-comparison.py --self-test
  python3 -B reproduction/plot-stair-night2-reward-comparison.py \
      --round3-directory reproduction/ACTUAL_ROUND3_DEVELOPMENT_DIRECTORY \
      --output-prefix reproduction/stair-night2-reward-comparison

This tool reads only explicitly selected development CSVs and identity sidecars.
It never imports simulator/Torch code, starts a GPU job, or selects a policy.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPRODUCTION = ROOT / "reproduction"
EXPECTED_ROWS = 108
EXPECTED_TRAVERSALS = 3456
SEEDS = {11, 29, 47}
SPEEDS = {0.3, 0.5}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize_rows(rows: list[dict[str, str]], checkpoint_sha: str) -> dict:
    """Count complete matrices without replacing individual gates by a mean."""
    require(len(rows) == EXPECTED_ROWS, f"Expected108 rows, observed {len(rows)}")
    expected_keys = {(c, s, v) for c in range(18) for s in SEEDS for v in SPEEDS}
    keys = []
    for row in rows:
        key = (int(row["case_index"]), int(row["reset_seed"]), float(row["speed_m_s"]))
        keys.append(key)
        require(row["heading_control_enabled"] == "True", "Only default-heading development rows are allowed")
        require(row["checkpoint_sha256"] == checkpoint_sha, "Mixed or unexpected checkpoint hashes")
        require(int(row["num_envs"]) == 32, "Each case/reset/speed must contain32 environments")
        require(0 <= int(row["completions"]) <= 32, "Completion count outside0..32")
        require(row["source_protocol_verified"] == "True", "An archived source protocol is unverified")
        require(row["numeric_assessment_status"] in {"PASS", "FAIL"}, "Incomplete numeric assessment cannot be plotted as final evidence")
        require(row["numeric_acceptance_passed"] == str(row["numeric_assessment_status"] == "PASS"), "Numeric status and accepted flag disagree")
        expected_group = "core" if key[0] < 6 else "moderate" if key[0] < 14 else "long"
        require(row["group"] == expected_group, "Development group indices differ")
        contact = float(row["current_sample_shank_contact_step_fraction"])
        require(math.isfinite(contact) and 0 <= contact <= 1, "Current shank-contact fraction must be finite in[0,1]")
    require(len(set(keys)) == EXPECTED_ROWS and set(keys) == expected_keys, "Duplicate/missing development case/reset/speed rows")
    contacts = {}
    for direction in ("asc", "desc"):
        core = [r for r in rows if r["group"] == "core" and f"_{direction}_" in r["case_name"]]
        require(len(core) == 18, f"Expected18 core {direction} rows")
        contacts[direction] = {
            "case_seed_speed_rows": len(core),
            "mean_current_shank_contact_fraction": statistics.fmean(float(r["current_sample_shank_contact_step_fraction"]) for r in core),
            "all_episodes_completed": all(int(r["completions"]) == 32 for r in core),
            "all_numeric_rows_passed": all(r["numeric_assessment_status"] == "PASS" for r in core),
        }
    return {
        "passed_case_seed_speed_rows": sum(r["numeric_assessment_status"] == "PASS" for r in rows),
        "declared_case_seed_speed_rows": EXPECTED_ROWS,
        "completions": sum(int(r["completions"]) for r in rows),
        "declared_traversals": EXPECTED_TRAVERSALS,
        "core_contact": contacts,
        "numeric_development_verdict": "PASS" if all(r["numeric_assessment_status"] == "PASS" for r in rows) else "FAIL",
    }


def read_policy(directory: Path, label: str, expected_seed: int) -> dict:
    csv_path = directory / f"{label}-development-summary.csv"
    identity_path = directory / f"{label}-training-identity.json"
    summary_path = directory / f"{label}-development-summary.json"
    for path in (csv_path, identity_path, summary_path):
        require(path.is_file(), f"Required archived development evidence missing: {path}")
    sidecar = json.loads(identity_path.read_text())
    identity = sidecar["identity"]
    require(identity.get("training_seed") == expected_seed, f"{label}: expected training seed{expected_seed}")
    require(sidecar.get("summary_sha256") == digest(summary_path), f"{label}: archived JSON summary identity changed")
    summary = json.loads(summary_path.read_text())
    require(summary.get("split") == "development", f"{label}: reserved/final evidence is forbidden here")
    sha = identity["checkpoint_sha256"]
    require(summary.get("checkpoint_sha256") == sha, f"{label}: JSON/model identity differs")
    with csv_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = summarize_rows(rows, sha)
    result.update({
        "label": label,
        "training_reward_profile": identity["training_reward_profile"],
        "training_seed": expected_seed,
        "checkpoint_sha256": sha,
        "source_paths": {"csv": str(csv_path), "json_summary": str(summary_path), "training_identity": str(identity_path)},
        "source_sha256": {str(path): digest(path) for path in (csv_path, identity_path, summary_path)},
    })
    return result


def read_group(directory: Path, title: str, labels: list[str], profiles: set[str], seed: int) -> dict:
    policies = [read_policy(directory, label, seed) for label in labels]
    require({p["training_reward_profile"] for p in policies} == profiles, f"{title}: unexpected or duplicated training rewards")
    return {"title": title, "training_seed": seed, "directory": str(directory), "policies": policies}


def collect(args: argparse.Namespace) -> dict:
    groups = [
        read_group(args.round1_directory, "Round1 | paired training seed1201", ["faithful", "contact", "vertical", "clearance"], {"faithful", "contact", "contact_vertical", "contact_clearance"}, 1201),
        read_group(args.round2_directory, "Round2 | paired training seed1213", ["faithful", "tracking"], {"faithful", "faithful_tracking"}, 1213),
    ]
    if args.round3_directory is not None:
        directory = args.round3_directory
        labels = sorted(path.name.removesuffix("-development-summary.csv") for path in directory.glob("*-development-summary.csv"))
        require(len(labels) == 2, "Explicit round3 directory must contain exactly two development policies")
        group = read_group(directory, "Round3 | paired training seed1213", labels, {"faithful", "contact_light"}, 1213)
        group["policies"].sort(key=lambda p: p["training_reward_profile"] != "faithful")
        groups.append(group)
    return {
        "schema_version": 1,
        "scope": "Archived development matrices only. No reserved result reads, GPU, simulation, training, policy selection or source/result changes.",
        "groups": groups,
        "row_passes_are_archived_individual_numeric_gates": True,
        "contact_mean_weighting": "Equal weight per core case/reset seed/speed row:18 rows per direction, both speeds together; not per-frame pooling.",
        "contact_measurement": "Any thigh/calf normal-force norm over1N at a20ms policy boundary; not continuous contact duration, support force or contact-point slip.",
        "comparability_limits": [
            "Each training-seed group is displayed separately; cross-seed differences do not establish reward causality.",
            "Current shank-contact means are diagnostics, not an acceptance gate.",
            "All rows enter each count; completed averages cannot replace case/reset/speed gate failures.",
            "Shared evaluation scene reward labels do not replace identity sidecars for actual training rewards.",
            "Different continuation rounds may have different starting checkpoints/budgets; this figure alone is not a cross-round causal comparison.",
        ],
    }


def render(data: dict, output_prefix: Path, overwrite: bool = False) -> list[Path]:
    # Import only for explicitly requested rendering; Agg never opens a display.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    outputs = [Path(str(output_prefix) + suffix) for suffix in (".png", ".pdf", ".json")]
    require(overwrite or not any(path.exists() for path in outputs), "Derived output already exists; choose a new prefix or use --overwrite")
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    count = len(data["groups"])
    fig, axes = plt.subplots(count, 3, figsize=(15, 3.4 * count + 1.25), squeeze=False)
    palette = {"faithful": "#2866b1", "contact": "#cb722b", "contact_vertical": "#559654", "contact_clearance": "#976db5", "faithful_tracking": "#bf4d57", "contact_light": "#cf7c28"}
    max_contact = max(p["core_contact"][d]["mean_current_shank_contact_fraction"] for g in data["groups"] for p in g["policies"] for d in ("asc", "desc"))
    for row_index, group in enumerate(data["groups"]):
        policies = group["policies"]
        labels = [p["label"] for p in policies]
        x = list(range(len(policies)))
        colors = [palette[p["training_reward_profile"]] for p in policies]
        for column, key, denominator, title in (
            (0, "passed_case_seed_speed_rows", EXPECTED_ROWS, "Individual case/reset/speed PASS rows"),
            (1, "completions", EXPECTED_TRAVERSALS, "Completed first episodes"),
        ):
            ax = axes[row_index][column]
            values = [p[key] for p in policies]
            bars = ax.bar(x, values, color=colors, width=0.6)
            ax.set_ylim(0, denominator * 1.13)
            ax.axhline(denominator, color="#555555", linewidth=0.7, linestyle=":")
            ax.set_title(title if row_index == 0 else "")
            ax.set_xticks(x, labels, rotation=15, ha="right")
            ax.set_ylabel(f"{group['title']}\nCount / {denominator}" if column == 0 else f"Count / {denominator}")
            for bar, value, p in zip(bars, values, policies):
                ax.annotate(f"{value}/{denominator}\n{p['numeric_development_verdict']}", (bar.get_x() + bar.get_width()/2, value), xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=8)
        ax = axes[row_index][2]
        for direction, offset, color, caption in (("asc", -0.18, "#477ab8", "Core ascent"), ("desc", 0.18, "#d18442", "Core descent")):
            values = [100 * p["core_contact"][direction]["mean_current_shank_contact_fraction"] for p in policies]
            bars = ax.bar([v + offset for v in x], values, width=0.34, color=color, label=caption)
            for bar, value in zip(bars, values):
                ax.annotate(f"{value:.1f}%", (bar.get_x() + bar.get_width()/2, value), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
        ax.set_ylim(0, max(5, 100 * max_contact * 1.23))
        ax.set_title("Current thigh/calf contact: diagnostic mean" if row_index == 0 else "")
        ax.set_ylabel("Mean policy-boundary fraction (%)")
        ax.set_xticks(x, labels, rotation=15, ha="right")
        if row_index == 0:
            ax.legend(fontsize=8, loc="upper left")
        for ax in axes[row_index]:
            ax.spines[["top", "right"]].set_visible(False)
            ax.grid(axis="y", alpha=0.18)
            ax.set_axisbelow(True)
    fig.suptitle("HIMLoco Go2 / Isaac Lab | paired reward development evidence", fontsize=15, y=0.985)
    fig.text(0.5, 0.025,
        "Separate paired training-seed groups; cross-seed differences are not reward causality.\n"
        "Counts retain every case/reset/speed gate. Contact means use18 equal-weight core rows per direction across0.3/0.5m/s; means are not acceptance.\n"
        "Boundary-sampled thigh/calf contact is not continuous contact duration or measured contact-point slip. Nominal simulation; no real-robot claim.",
        ha="center", va="bottom", fontsize=8)
    fig.tight_layout(rect=(0.015, 0.10 if count == 2 else 0.075, 0.995, 0.965))
    fig.savefig(outputs[0], dpi=170, metadata={"Software": "plot-stair-night2-reward-comparison.py"})
    fig.savefig(outputs[1], metadata={"Creator": "plot-stair-night2-reward-comparison.py"})
    plt.close(fig)
    outputs[2].write_text(json.dumps(data, indent=2) + "\n")
    return outputs


def fixture_rows() -> list[dict[str, str]]:
    rows = []
    for case in range(18):
        for seed in sorted(SEEDS):
            for speed in sorted(SPEEDS):
                rows.append({
                    "case_index": str(case), "reset_seed": str(seed), "speed_m_s": str(speed),
                    "heading_control_enabled": "True", "checkpoint_sha256": "fixture-only",
                    "num_envs": "32", "completions": "32", "source_protocol_verified": "True",
                    "numeric_assessment_status": "PASS", "numeric_acceptance_passed": "True",
                    "group": "core" if case < 6 else "moderate" if case < 14 else "long",
                    "case_name": f"fixture_{'asc' if case % 2 == 0 else 'desc'}_{case}",
                    "current_sample_shank_contact_step_fraction": "0.1" if case % 2 == 0 else "0.3",
                })
    return rows


class CpuChecks(unittest.TestCase):
    def test_keeps_failed_row_despite_high_aggregate_completion(self):
        rows = fixture_rows()
        rows[-1].update(completions="30", numeric_assessment_status="FAIL", numeric_acceptance_passed="False")
        data = summarize_rows(rows, "fixture-only")
        self.assertEqual(data["completions"], 3454)
        self.assertEqual(data["passed_case_seed_speed_rows"], 107)
        self.assertEqual(data["numeric_development_verdict"], "FAIL")
        self.assertAlmostEqual(data["core_contact"]["asc"]["mean_current_shank_contact_fraction"], 0.1)
        self.assertAlmostEqual(data["core_contact"]["desc"]["mean_current_shank_contact_fraction"], 0.3)

    def test_rejects_duplicate_missing_and_wrong_hash_rows(self):
        for change in ("duplicate", "missing", "hash", "unknown", "nonfinite"):
            rows = fixture_rows()
            if change == "duplicate": rows[-1] = rows[0].copy()
            elif change == "missing": rows.pop()
            elif change == "hash": rows[-1]["checkpoint_sha256"] = "another-policy"
            elif change == "unknown": rows[-1]["numeric_assessment_status"] = "NOT_ASSESSED"
            else: rows[-1]["current_sample_shank_contact_step_fraction"] = "nan"
            with self.subTest(change=change), self.assertRaises(ValueError):
                summarize_rows(rows, "fixture-only")

    def test_temporary_synthetic_figure_export(self):
        policies = []
        for label, profile in (("fixture-faithful", "faithful"), ("fixture-contact", "contact")):
            metrics = summarize_rows(fixture_rows(), "fixture-only")
            metrics.update(label=label, training_reward_profile=profile)
            policies.append(metrics)
        with tempfile.TemporaryDirectory(prefix="himloco-reward-plot-fixture-") as tmp:
            data = {"scope": "Synthetic CPU plotting fixture; not policy evidence", "groups": [{"title": "Synthetic paired group", "policies": policies}]}
            paths = render(data, Path(tmp) / "fixture")
            self.assertTrue(paths[0].read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertTrue(paths[1].read_bytes().startswith(b"%PDF"))
            self.assertEqual(json.loads(paths[2].read_text())["scope"], data["scope"])
            with self.assertRaises(ValueError): render(data, Path(tmp) / "fixture")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--round1-directory", type=Path, default=REPRODUCTION / "stair-night2-round1-development")
    parser.add_argument("--round2-directory", type=Path, default=REPRODUCTION / "stair-night2-round2-development")
    parser.add_argument("--round3-directory", type=Path, help="Read exactly two explicitly supplied development policies, faithful/contact_light, both seed1213; no round3 reads without this option")
    parser.add_argument("--output-prefix", type=Path, default=REPRODUCTION / "stair-night2-reward-comparison")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite derived plot/metadata artifacts only")
    parser.add_argument("--check-only", action="store_true", help="Validate real archived data and print metrics; create no figure or files")
    parser.add_argument("--self-test", action="store_true", help="CPU-only synthetic guards/export tests, temporary outputs removed; not locomotion evidence")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(CpuChecks)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    data = collect(args)
    if args.check_only:
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps({"outputs": [str(path) for path in render(data, args.output_prefix, args.overwrite)]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
