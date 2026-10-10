#!/usr/bin/env bash
# Execute the saved final protocol only after recording a frozen checkpoint.
# Uses the existing simulation container; no installations or system changes.
set -Eeuo pipefail
if [[ $# != 3 ]]; then
  printf 'Usage: %s CHECKPOINT REWARD_PROFILE OUTPUT_LOG_DIRECTORY\n' "$0" >&2
  exit 2
fi
selected_checkpoint=$1
selected_profile=$2
validation_logs=$3
case "$selected_profile" in
  faithful|contact|contact_force|contact_slide) ;;
  *) printf 'Unsupported frozen reward profile: %s\n' "$selected_profile" >&2; exit 2 ;;
esac
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$repo_root"
selected_checkpoint=$(realpath -- "$selected_checkpoint")
freeze_plan="$repo_root/reproduction/stair-final-evaluation-plan.json"
validate_freeze() {
  python3 - "$repo_root" "$freeze_plan" "$selected_checkpoint" "$selected_profile" \
    "${secondary_checkpoint-}" "${secondary_profile-}" "${1:-locked}" <<'PY'
import hashlib
import json
from pathlib import Path
import re
import sys

root, plan_file, checkpoint, profile, expected_secondary, expected_secondary_profile, stage = sys.argv[1:]
root = Path(root).resolve()

def require(condition, message):
    if not condition:
        raise SystemExit(f"Frozen validation guard: {message}")

def repo_file(value, label):
    require(isinstance(value, str) and bool(value), f"missing {label}")
    path = Path(value)
    path = (path if path.is_absolute() else root / path).resolve()
    require(path.is_relative_to(root), f"{label} must be inside the repository")
    require(path.is_file(), f"{label} does not exist: {path}")
    return path

def check_hash(path, expected, label):
    require(isinstance(expected, str) and re.fullmatch(r"[0-9a-fA-F]{64}", expected),
            f"missing or invalid {label} SHA-256")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    require(digest.hexdigest() == expected.lower(), f"{label} SHA-256 mismatch: {path}")

with Path(plan_file).open() as stream:
    plan = json.load(stream)
require(plan.get("status") == "frozen", "plan status must be exactly 'frozen'")
require(plan.get("no_retuning_from_final_matrix") is True, "no-retuning rule must be recorded")
frozen_checkpoint = repo_file(plan.get("checkpoint"), "frozen checkpoint")
require(frozen_checkpoint == repo_file(checkpoint, "requested checkpoint"),
        "requested checkpoint differs from the frozen checkpoint")
require(plan.get("reward_profile") == profile, "requested profile differs from the frozen profile")
check_hash(frozen_checkpoint, plan.get("checkpoint_sha256"), "checkpoint")
secondary_keys = ("secondary_checkpoint", "secondary_checkpoint_sha256", "secondary_reward_profile")
has_secondary = any(plan.get(key) is not None for key in secondary_keys)
secondary_path = secondary_profile = ""
if has_secondary:
    secondary_path = repo_file(plan.get("secondary_checkpoint"), "secondary checkpoint")
    require(secondary_path != frozen_checkpoint, "secondary checkpoint must differ from primary")
    secondary_profile = plan.get("secondary_reward_profile")
    require(secondary_profile in ("faithful", "contact", "contact_force", "contact_slide"),
            "missing or unsupported secondary reward profile")
    check_hash(secondary_path, plan.get("secondary_checkpoint_sha256"), "secondary checkpoint")
    require("\n" not in str(secondary_path), "secondary checkpoint path must not contain a newline")
if stage != "initial":
    require(str(secondary_path) == expected_secondary and secondary_profile == expected_secondary_profile,
            "secondary checkpoint/profile changed after the initial freeze guard")
for path_key, hash_key, required_relative in (
    ("final_geometry_file", "final_geometry_sha256", "reproduction/stair-heldout-final.json"),
    ("acceptance_file", "acceptance_sha256", "reproduction/stair-acceptance.json"),
    ("heading_geometry_file", "heading_geometry_sha256", "reproduction/stair-validation-core-standard.json"),
):
    path = repo_file(plan.get(path_key), path_key)
    require(path == (root / required_relative).resolve(), f"{path_key} differs from this script")
    check_hash(path, plan.get(hash_key), path_key)

implementation_sources = plan.get("implementation_source_sha256")
require(isinstance(implementation_sources, dict) and bool(implementation_sources),
        "a nonempty implementation_source_sha256 dictionary is required")
require("isaaclab/run.py" in implementation_sources,
        "implementation_source_sha256 must include isaaclab/run.py")
for relative, expected in implementation_sources.items():
    require(isinstance(relative, str) and bool(relative), "invalid implementation source path")
    relative_path = Path(relative)
    require(not relative_path.is_absolute() and ".." not in relative_path.parts,
            f"implementation source paths must be repository-relative: {relative}")
    require(relative_path.suffix == ".py" and "tests" not in relative_path.parts
            and not relative_path.name.startswith("test_") and relative_path.name != "conftest.py",
            f"implementation source manifest must contain runtime Python files, not tests: {relative}")
    check_hash(repo_file(relative, "implementation source"), expected, f"implementation source {relative}")

# The protocol is explicit in the shell; refuse silently divergent plan values.
require(plan.get("seconds") == 40 and plan.get("envs") == 512,
        "plan duration or environment count differs from this script")
require(plan.get("final_reset_seeds") == [101, 211, 307]
        and plan.get("speeds_m_s") == [0.3, 0.5], "final seeds or speeds differ from this script")
materials = plan.get("materials", {})
require(materials.get("scene_profile") == "basic" and materials.get("eval_dynamics") is False
        and materials.get("speed_m_s") == 0.3 and materials.get("construction_seed") == 1
        and materials.get("foot_static_dynamic_pairs") == {
            "nominal": [0.8, 0.6], "lower": [0.45, 0.35], "higher": [1.0, 0.8]},
        "material protocol differs from this script")
dynamics = plan.get("combined_dynamics", {})
require(dynamics.get("scene_profile") == "robust" and dynamics.get("eval_dynamics") is True
        and dynamics.get("construction_seeds") == [71, 73, 79]
        and dynamics.get("reset_seeds") == [101, 211, 307]
        and dynamics.get("speed_m_s") == 0.3
        and dynamics.get("foot_static_dynamic_pair") == [0.8, 0.6],
        "dynamics protocol differs from this script")
require(plan.get("heading_controller", {}).get("supplementary_reset_seeds") == [401, 409, 419],
        "heading stress reset seeds differ from this script")
flat = plan.get("flat_regression", {})
require(flat.get("envs") == 64 and flat.get("seconds") == 20
        and flat.get("warm_start") == "reset" and flat.get("gradient_updates") == 0
        and flat.get("commands") == [[0.3, 0, 0], [0.5, 0, 0], [-0.5, 0, 0],
                                    [0, 0.3, 0], [0, 0, 0.5], [0, 0, -0.5]],
        "flat regression protocol differs from this script")
if has_secondary:
    print(secondary_path)
    print(secondary_profile)
PY
}
frozen_secondary=$(validate_freeze initial)
secondary_checkpoint="" secondary_profile=""
secondary_args=()
if [[ -n $frozen_secondary ]]; then
  secondary_checkpoint=${frozen_secondary%$'\n'*}
  secondary_profile=${frozen_secondary##*$'\n'}
  secondary_args=(--candidate_checkpoint "$secondary_checkpoint")
fi
mkdir -p -- "$validation_logs"
cp -- "$freeze_plan" "$validation_logs/frozen-evaluation-plan.json"
common=(evaluate --terrain stairs --checkpoint "$selected_checkpoint"
  --reward_profile "$selected_profile" --stair_batch reproduction/stair-heldout-final.json
  --num_envs 512 --eval_seconds 40 --eval_randomized
  --eval_seed 101 --eval_seed 211 --eval_seed 307 --seed 1 --viz none)
run_checked() {
  local validation_name=$1
  shift
  validate_freeze > /dev/null
  local wall_start_ns wall_end_ns wall_elapsed_ns command_exit=0
  wall_start_ns=$(date +%s%N)
  printf 'Starting %s at %s\n' "$validation_name" "$(date --iso-8601=seconds)"
  bash isaaclab/run.sh "$@" --run_name "$validation_name" \
    > "$validation_logs/$validation_name.log" 2>&1 || command_exit=$?
  wall_end_ns=$(date +%s%N)
  wall_elapsed_ns=$((wall_end_ns - wall_start_ns))
  printf 'Finished %s at %s; elapsed %d.%03d s; command exit %d\n' \
    "$validation_name" "$(date --iso-8601=seconds)" \
    "$((wall_elapsed_ns / 1000000000))" "$(((wall_elapsed_ns % 1000000000) / 1000000))" \
    "$command_exit"
  return "$command_exit"
}
run_final() {
  local validation_name=$1
  shift
  run_checked "$validation_name" "${common[@]}" "$@"
}
run_final frozen-final-speed03 --speed 0.3 --domain_profile none "${secondary_args[@]}"
run_final frozen-final-speed05 --speed 0.5 --domain_profile none "${secondary_args[@]}"
run_final frozen-foot-nominal-speed03 --speed 0.3 --domain_profile basic --friction 0.8 0.6
run_final frozen-foot-low-speed03 --speed 0.3 --domain_profile basic --friction 0.45 0.35
run_final frozen-foot-high-speed03 --speed 0.3 --domain_profile basic --friction 1.0 0.8
heading=(evaluate --terrain stairs --checkpoint "$selected_checkpoint"
  --reward_profile "$selected_profile" --stair_batch reproduction/stair-validation-core-standard.json
  --num_envs 384 --eval_seconds 40 --eval_randomized --speed 0.3
  --eval_seed 401 --eval_seed 409 --eval_seed 419 --domain_profile none --seed 1 --viz none)
run_checked frozen-standard-heading-control "${heading[@]}"
run_checked frozen-standard-zero-yaw "${heading[@]}" --open_loop_heading
run_checked frozen-stair-policy-flat-regression evaluate --terrain flat \
  --checkpoint "$selected_checkpoint" --reward_profile "$selected_profile" \
  --warm_start reset --num_envs 64 --eval_seconds 20 --viz none \
  --command 0.3 0 0 --command 0.5 0 0 --command -0.5 0 0 \
  --command 0 0.3 0 --command 0 0 0.5 --command 0 0 -0.5
for construction_seed in 71 73 79; do
  run_final "frozen-dynamics-seed-$construction_seed-speed03" --speed 0.3 \
    --domain_profile robust --eval_dynamics --friction 0.8 0.6 --seed "$construction_seed"
done
printf 'Frozen validation commands finished at %s\n' "$(date --iso-8601=seconds)"
