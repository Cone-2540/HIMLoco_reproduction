#!/usr/bin/env python3
"""Wait on one explicit root-launched training wrapper, then CPU archive/audit.

This never launches GPU work or selects a policy. It preserves unsuccessful or
partial training and refuses archive/audit overwrite. Root supplies the exact
wrapper path; no latest-directory discovery is performed.
"""

import argparse
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("round3", ROOT / "reproduction/run-stair-night2-round3-comparison.py")
round3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(round3)
JOB_NAME = "night2-round3-contact-light-seed1213-plus100"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wrapper-dir", type=Path, required=True)
    parser.add_argument("--source-proof", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/go2-stairs-night2-round3-contact-light-seed1213-760")
    parser.add_argument("--audit-output", type=Path, default=ROOT / "reproduction/stair-night2-round3-light-training-audit.json")
    args = parser.parse_args()
    wrapper = args.wrapper_dir.expanduser().resolve(strict=True)
    proof_path = round3.explicit_file(args.source_proof)
    proof_hash, proof = round3.digest(proof_path), round3.read(proof_path)
    output, audit_output = args.output.expanduser().resolve(), args.audit_output.expanduser().resolve()
    round3.require(not output.exists() and not audit_output.exists(), "Archive/audit overwrite refused")
    round3.validate_proof(proof)
    record_path = wrapper / "launch-record.json"
    initial = round3.read(record_path)
    round3.require(initial.get("name") == JOB_NAME, "Wrapper does not belong to exact root-launched round3 job")
    round3.require(initial.get("source_sha256") == proof["current_runtime_sha256"], "Launched training source differs from actual CPU proof")
    print("WATCHING_EXACT_WRAPPER: " + str(wrapper), flush=True)
    while True:
        record = round3.read(record_path)
        round3.require(record.get("name") == JOB_NAME and record.get("source_sha256") == initial["source_sha256"], "Wrapper identity changed")
        if record.get("status") != "started":
            break
        round3.require(datetime.now(round3.ZONE) < round3.DEADLINE, "Deadline reached; preserve partial training, do not archive as complete")
        time.sleep(10)
    round3.require(record.get("status") == "exited" and record.get("exit_code") == 0, "Training wrapper failed/interrupted; no archive created")
    round3.require(round3.digest(proof_path) == proof_hash, "Source proof changed during training")
    round3.validate_proof(proof)
    log = Path(record.get("simulator_log_dir", "")).resolve(strict=True)
    log.relative_to(ROOT / "isaaclab/logs")
    config = round3.read(log / "config.json")
    round3.require(config.get("mode") == "train" and config.get("stair_reward", {}).get("profile") == "contact_light"
                   and config.get("seed") == 1213 and config.get("num_envs") == 7680, "Training actual identity differs")
    done = subprocess.run([sys.executable, str(ROOT / "reproduction/archive-stair-night2-model.py"),
                           "--log-dir", str(log), "--wrapper-dir", str(wrapper), "--output", str(output),
                           "--plan", str(ROOT / round3.TRAINING_PLAN)], cwd=ROOT, capture_output=True, text=True, timeout=120)
    print(done.stdout, end="", flush=True)
    round3.require(done.returncode == 0, "CPU archive failed; preserve all output: " + done.stderr)
    baseline = round3.archive_identity("baseline-faithful1213", "faithful", round3.BASELINE, proof)
    candidate = round3.archive_identity("contact-light1213", "contact_light", str(output / "model_760.pt"), proof)
    round3.validate_pair(baseline, candidate)
    manifest_path = output / "manifest.json"
    value = {"schema_version": 1, "round": 3, "created_local": datetime.now(round3.ZONE).isoformat(),
             "status": "matched_reward_only_training_CPU_archived_and_verified",
             "actual_training_wrapper": str(wrapper), "actual_training_run": str(log),
             "launch_record_sha256": round3.digest(record_path),
             "training_source_commit": record["source_commit"], "training_source_dirty_original": record.get("source_dirty"),
             "source_proof_file": str(proof_path), "source_proof_sha256": proof_hash,
             "candidate_manifest_sha256": round3.digest(manifest_path), "baseline": baseline, "candidate": candidate,
             "archive_members_verified_each": 19, "common_control660_origin": True,
             "same_saved_100updates_7680env_100steps_76_8M": True,
             "same_full_training_configuration_except_declared_reward": True,
             "same_initial_physical_readbacks_except_anonymous_USD_layer_identifier": True,
             "sole_reward_change_from_faithful": {"leg_contacts": -0.02},
             "both_Adam_states_retained_delta_steps": 2000, "unchanged_model_tensor_shapes": 30,
             "cuda_initialized_by_checkpoint_audit": False, "GPU_work_launched_by_watcher": False,
             "automatic_policy_selection": False, "stair_performance_assessed": False,
             "limits": "One paired training seed1213, reused narrowly source-compatible faithful baseline. Saved config and sampled physical readbacks do not prove every initial tensor, deterministic CUDA trajectories or reward causality. No traversal/smoothness acceptance implied."}
    round3.backend.save_json_exclusive(audit_output, value)
    print(json.dumps({"status": value["status"], "archive": str(output), "audit": str(audit_output),
                      "checkpoint_sha256": candidate["checkpoint_sha256"], "cuda_initialized": False}), flush=True)


if __name__ == "__main__":
    main()
