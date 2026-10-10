#!/usr/bin/env bash
set -Eeuo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$repo_root"
calf_logs=${1:-/home/cone/robotics/logs/himloco-overnight-20261011/frozen-calf-sensitivity}
mkdir -p -- "$calf_logs"
guard() {
  python3 - "$repo_root" <<'PY'
import hashlib
import json
from pathlib import Path
import sys
root = Path(sys.argv[1])
plan_file = root / 'reproduction/stair-final-evaluation-plan.json'
if hashlib.sha256(plan_file.read_bytes()).hexdigest() != 'fd27265a2d714662a3d03404903537cf6abec3c13ae2f65f21b7edf38b5391ae':
    raise SystemExit('Calf sensitivity guard: original plan changed')
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
        raise SystemExit(f'Calf sensitivity guard: changed {relative}')
PY
}
for calf_speed in 0.3 0.5; do
  guard
  calf_name="frozen-calf-legacy-speed${calf_speed/./}"
  printf 'Starting %s at %s\n' "$calf_name" "$(date --iso-8601=seconds)"
  bash isaaclab/run.sh evaluate --terrain stairs --viz none \
    --checkpoint artifacts/go2-stairs-control660/model_660.pt --reward_profile contact \
    --stair_batch reproduction/stair-heldout-final.json --num_envs 512 \
    --eval_seconds 40 --speed "$calf_speed" --eval_randomized \
    --eval_seed 101 --eval_seed 211 --eval_seed 307 --seed 1 --domain_profile none \
    --conservative_calf --run_name "$calf_name" > "$calf_logs/$calf_name.log" 2>&1
  printf 'Finished %s at %s; collection exit 0\n' "$calf_name" "$(date --iso-8601=seconds)"
done
guard
printf 'Calf model sensitivity collection finished at %s\n' "$(date --iso-8601=seconds)"
