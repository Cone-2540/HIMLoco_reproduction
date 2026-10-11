#!/usr/bin/env python3
"""CPU-only actual-source compatibility proof for the declared contact_light patch.

Run in the existing Lab Python with CUDA_VISIBLE_DEVICES empty. This constructs
the installed Go2 configuration only; no environment, simulation or training.
The predeclared proposal hashes are mandatory, never inferred from current files.
"""

import argparse
import ast
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STATIC_FILES = (
    "isaaclab/adapter.py", "isaaclab/checkpoint_transfer.py", "isaaclab/stair_terrain.py",
    "isaaclab/stair_evaluation.py", "isaaclab/stair_randomization.py",
    "isaaclab/vendor/him_rsl_rl/modules/him_actor_critic.py",
    "isaaclab/vendor/him_rsl_rl/modules/him_estimator.py",
    "isaaclab/vendor/him_rsl_rl/algorithms/him_ppo.py",
    "isaaclab/vendor/him_rsl_rl/runners/him_on_policy_runner.py",
)
RUNTIME_FILES = ("isaaclab/run.py", "isaaclab/stair_rewards.py", "isaaclab/stair_terrain.py",
                 "isaaclab/stair_evaluation.py", "isaaclab/adapter.py")
OLD_PROFILES = ("stock", "faithful", "faithful_tracking", "tuned", "contact", "contact_force",
                "contact_slide", "contact_vertical", "contact_clearance")
BASELINE = "artifacts/go2-stairs-night2-faithful-seed1213-760/model_760.pt"


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_source(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize(value):
    if isinstance(value, dict):
        return {str(k): normalize(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [normalize(v) for v in value]
    if isinstance(value, slice):
        return {"slice": [value.start, value.stop, value.step]}
    if isinstance(value, Path):
        return str(value)
    if callable(value):
        return {"callable": value.__module__ + ":" + value.__qualname__}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "to_dict"):
        return normalize(value.to_dict())
    return {"type": type(value).__module__ + ":" + type(value).__qualname__, "value": str(value)}


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def audit(output):
    require(os.environ.get("CUDA_VISIBLE_DEVICES") == "", "CUDA must be hidden explicitly")
    import torch
    require(not torch.cuda.is_available() and not torch.cuda.is_initialized(), "CPU only")
    sys.path.insert(0, str(ROOT / "isaaclab"))
    import isaaclab_tasks
    from isaaclab_tasks.utils import resolve_task_config
    from isaaclab.managers import RewardTermCfg
    from stair_terrain import configure_stair_terrain
    def actual_config():
        cfg, _ = resolve_task_config("Isaac-Velocity-Rough-UnitreeGo2", "", overrides=["physics=isaacsim_physx"])
        configure_stair_terrain(cfg, "paper_mixed", num_rows=10, num_cols=28, seed=1213, flat_fraction=0.0)
        return cfg
    proposal_path = ROOT / "reproduction/stair-night2-round3-training-proposal.json"
    proposal = json.loads(proposal_path.read_text())
    expected = proposal["patch_proposal"]["proposed_source_sha256"]
    actual_patch = {name: digest(ROOT / name) for name in expected}
    require(actual_patch == expected, "Applied runtime/workflow must equal predeclared contact_light patch")
    directory = (ROOT / BASELINE).parent
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    commit = manifest["source_provenance"]["config_commit"]
    static = {}
    for name in STATIC_FILES:
        saved = subprocess.run(["git", "show", commit + ":" + name], cwd=ROOT,
                               capture_output=True, check=True, timeout=20).stdout
        old_hash = hashlib.sha256(saved).hexdigest()
        require(old_hash == digest(ROOT / name), "Non-reward runtime changed: " + name)
        static[name] = {"archived_training_commit_sha256": old_hash, "current_sha256": old_hash, "equal": True}
    archived_runtime = manifest["source_provenance"]["verified_runtime_source_sha256"]
    for name in RUNTIME_FILES:
        member = "source/" + name
        require(digest(directory / member) == manifest["files"][member]["sha256"] == archived_runtime[name],
                "Baseline archived runtime identity changed: " + name)
    old_path = directory / "source/isaaclab/stair_rewards.py"
    new_path = ROOT / "isaaclab/stair_rewards.py"
    old = load_source(old_path, "round3_old_rewards")
    new = load_source(new_path, "round3_current_rewards")
    helpers = {}
    old_tree, new_tree = ast.parse(old_path.read_text()), ast.parse(new_path.read_text())
    old_functions = {n.name: ast.dump(n, include_attributes=False) for n in old_tree.body if isinstance(n, ast.FunctionDef)}
    new_functions = {n.name: ast.dump(n, include_attributes=False) for n in new_tree.body if isinstance(n, ast.FunctionDef)}
    require(set(old_functions) == set(new_functions), "Reward functions added/removed")
    for name, value in old_functions.items():
        if name == "configure_stair_rewards":
            continue
        require(value == new_functions[name], "Reward helper AST changed: " + name)
        helpers[name] = hashlib.sha256(value.encode()).hexdigest()
    require(len(helpers) == 11, "Expected exactly eleven preserved reward helpers")
    old_profiles = {}
    faithful_cfg = None
    faithful_manifest = None
    for profile in OLD_PROFILES:
        cfg_old, cfg_new = actual_config(), actual_config()
        a = old.configure_stair_rewards(cfg_old, profile)
        b = new.configure_stair_rewards(cfg_new, profile)
        config_a, config_b = normalize(cfg_old.to_dict()), normalize(cfg_new.to_dict())
        require(a == b and config_a == config_b, "Existing actual Go2 config or manifest changed: " + profile)
        old_profiles[profile] = {"full_actual_go2_configuration_equal": True, "manifest_equal": True,
                                 "configuration_sha256": signature(config_a), "manifest_sha256": signature(a)}
        if profile == "faithful":
            faithful_cfg, faithful_manifest = cfg_new, b
    light_cfg = actual_config()
    light_manifest = new.configure_stair_rewards(light_cfg, "contact_light")
    terms = lambda cfg: {n: normalize(t.to_dict()) for n, t in vars(cfg.rewards).items() if isinstance(t, RewardTermCfg)}
    faithful_terms, light_terms = terms(faithful_cfg), terms(light_cfg)
    require(set(light_terms) == set(faithful_terms) | {"leg_contacts"}, "New reward term set differs")
    require(all(light_terms[n] == v for n, v in faithful_terms.items()), "Faithful terms changed in light")
    strong_cfg = actual_config()
    new.configure_stair_rewards(strong_cfg, "contact")
    strong_contact = terms(strong_cfg)["leg_contacts"]
    light_contact = dict(light_terms["leg_contacts"])
    require(light_contact["weight"] == -0.02 and strong_contact["weight"] == -0.1, "Wrong contact weights")
    light_contact["weight"] = -0.1
    require(light_contact == strong_contact, "Existing leg_contacts function/parameters changed")
    # Compare full actual cfg after removing the sole added reward, not just weights.
    light_config = normalize(light_cfg.to_dict())
    light_config["rewards"].pop("leg_contacts")
    require(light_config == normalize(faithful_cfg.to_dict()), "Non-reward config differs")
    require(not torch.cuda.is_initialized(), "CUDA initialized during configuration audit")
    value = {
        "schema_version": 1, "status": "actual_applied_contact_light_source_compatibility_CPU_verified",
        "created_local": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "baseline_checkpoint": BASELINE, "baseline_checkpoint_sha256": digest(ROOT / BASELINE),
        "baseline_manifest_sha256": digest(manifest_path), "baseline_training_commit": commit,
        "proposal_file": str(proposal_path.relative_to(ROOT)), "proposal_sha256": digest(proposal_path),
        "applied_patch_file_sha256": actual_patch,
        "current_runtime_sha256": {n: digest(ROOT / n) for n in RUNTIME_FILES},
        "baseline_archived_runtime_sha256": archived_runtime,
        "unchanged_nonreward_files": static, "preserved_reward_helper_AST_sha256": helpers,
        "old_profiles": old_profiles, "faithful_reward_manifest": faithful_manifest,
        "light_reward_manifest": light_manifest,
        "light_only_difference": {"term": "leg_contacts", "weight": -0.02,
                                  "function_and_parameters_equal_existing_contact": True,
                                  "all_other_actual_configuration_equal": True},
        "audit_script_sha256": digest(Path(__file__)),
        "cuda_initialized": False, "simulation_started": False, "training_started": False,
        "scope": "Actual installed Go2 cfg and RewardTermCfg; compatibility proof for this exact preregistered patch only. Does not prove equivalent future training trajectories or stair performance.",
    }
    with output.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": value["status"], "output": str(output), "old_profiles": len(old_profiles),
                      "unchanged_files": len(static), "reward_helpers": len(helpers), "cuda_initialized": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        audit(args.output.resolve())
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.error(str(error))
