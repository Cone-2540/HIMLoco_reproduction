#!/usr/bin/env bash
# Supplement the original protocol with the same frozen primary at 0.5 m/s.
set -Eeuo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$repo_root"
supplement_logs=${1:-/home/cone/robotics/logs/himloco-overnight-20261011/frozen-material-speed05}
mkdir -p -- "$supplement_logs"
guard() {
  python3 - "$repo_root" <<'PY'
import hashlib
import json
from pathlib import Path
import sys
root = Path(sys.argv[1])
plan_file = root / 'reproduction/stair-final-evaluation-plan.json'
if hashlib.sha256(plan_file.read_bytes()).hexdigest() != 'fd27265a2d714662a3d03404903537cf6abec3c13ae2f65f21b7edf38b5391ae':
    raise SystemExit('Supplement freeze guard: original plan changed')
plan = json.loads(plan_file.read_text())
manifest = dict(plan['implementation_source_sha256'])
for path_key, hash_key in [
    ('checkpoint', 'checkpoint_sha256'),
    ('secondary_checkpoint', 'secondary_checkpoint_sha256'),
    ('final_geometry_file', 'final_geometry_sha256'),
    ('heading_geometry_file', 'heading_geometry_sha256'),
    ('acceptance_file', 'acceptance_sha256'),
]:
    manifest[plan[path_key]] = plan[hash_key]
for relative, expected in manifest.items():
    if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
        raise SystemExit(f'Supplement freeze guard: changed {relative}')
PY
}
run_material() {
  local material_name=$1 material_static=$2 material_dynamic=$3
  guard
  printf 'Starting frozen-foot-%s-speed05 at %s\n' "$material_name" "$(date --iso-8601=seconds)"
  bash isaaclab/run.sh evaluate --terrain stairs --viz none \
    --checkpoint artifacts/go2-stairs-control660/model_660.pt --reward_profile contact \
    --stair_batch reproduction/stair-heldout-final.json --num_envs 512 \
    --eval_seconds 40 --speed 0.5 --eval_randomized \
    --eval_seed 101 --eval_seed 211 --eval_seed 307 --seed 1 \
    --domain_profile basic --friction "$material_static" "$material_dynamic" \
    --run_name "frozen-foot-$material_name-speed05" \
    > "$supplement_logs/frozen-foot-$material_name-speed05.log" 2>&1
  printf 'Finished frozen-foot-%s-speed05 at %s; collection exit 0\n' "$material_name" "$(date --iso-8601=seconds)"
}
guard
run_material nominal 0.8 0.6
run_material low 0.45 0.35
run_material high 1.0 0.8
guard
printf 'Supplementary material collection finished at %s\n' "$(date --iso-8601=seconds)"
