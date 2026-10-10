#!/usr/bin/env bash
set -Eeuo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$repo_root"
geometry_logs=${1:-/home/cone/robotics/logs/himloco-overnight-20261011/frozen-height-depth-probe}
mkdir -p -- "$geometry_logs"
guard() {
  python3 - "$repo_root" <<'PY'
import hashlib
import json
from pathlib import Path
import sys
root = Path(sys.argv[1])
plan_file = root / 'reproduction/stair-final-evaluation-plan.json'
if hashlib.sha256(plan_file.read_bytes()).hexdigest() != 'fd27265a2d714662a3d03404903537cf6abec3c13ae2f65f21b7edf38b5391ae':
    raise SystemExit('Height/depth probe guard: original plan changed')
plan = json.loads(plan_file.read_text())
manifest = dict(plan['implementation_source_sha256'])
for path_key, hash_key in [
    ('checkpoint', 'checkpoint_sha256'), ('secondary_checkpoint', 'secondary_checkpoint_sha256'),
    ('final_geometry_file', 'final_geometry_sha256'), ('heading_geometry_file', 'heading_geometry_sha256'),
    ('acceptance_file', 'acceptance_sha256'),
]:
    manifest[plan[path_key]] = plan[hash_key]
for relative, expected in manifest.items():
    if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
        raise SystemExit(f'Height/depth probe guard: changed {relative}')
PY
}
for geometry_speed in 0.3 0.5; do
  guard
  geometry_name="frozen-height-depth-speed${geometry_speed/./}"
  printf 'Starting %s at %s\n' "$geometry_name" "$(date --iso-8601=seconds)"
  bash isaaclab/run.sh evaluate --terrain stairs --viz none \
    --checkpoint artifacts/go2-stairs-control660/model_660.pt --reward_profile contact \
    --stair_batch reproduction/stair-frozen-height-depth-probe.json --num_envs 576 \
    --eval_seconds 40 --speed "$geometry_speed" --eval_randomized \
    --eval_seed 601 --eval_seed 607 --eval_seed 613 --seed 1 --domain_profile none \
    --run_name "$geometry_name" > "$geometry_logs/$geometry_name.log" 2>&1
  printf 'Finished %s at %s; collection exit 0\n' "$geometry_name" "$(date --iso-8601=seconds)"
done
guard
printf 'Height/depth diagnostic collection finished at %s\n' "$(date --iso-8601=seconds)"
