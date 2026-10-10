#!/usr/bin/env bash
set -Eeuo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$repo_root"
probe_logs=${1:-/home/cone/robotics/logs/himloco-overnight-20261011/frozen-speed-probe}
mkdir -p -- "$probe_logs"
guard() {
  python3 - "$repo_root" <<'PY'
import hashlib
import json
from pathlib import Path
import sys
root = Path(sys.argv[1])
plan_file = root / 'reproduction/stair-final-evaluation-plan.json'
if hashlib.sha256(plan_file.read_bytes()).hexdigest() != 'fd27265a2d714662a3d03404903537cf6abec3c13ae2f65f21b7edf38b5391ae':
    raise SystemExit('Speed probe guard: original plan changed')
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
        raise SystemExit(f'Speed probe guard: changed {relative}')
PY
}
for probe_speed in 0.2 0.3 0.4 0.5 0.6; do
  guard
  probe_name="frozen-speed-probe-${probe_speed/./}"
  printf 'Starting %s at %s\n' "$probe_name" "$(date --iso-8601=seconds)"
  bash isaaclab/run.sh evaluate --terrain stairs --viz none \
    --checkpoint artifacts/go2-stairs-control660/model_660.pt --reward_profile contact \
    --stair_batch reproduction/stair-frozen-speed-probe.json --num_envs 192 \
    --eval_seconds 40 --speed "$probe_speed" --eval_randomized \
    --eval_seed 503 --eval_seed 509 --eval_seed 521 --seed 1 --domain_profile none \
    --run_name "$probe_name" > "$probe_logs/$probe_name.log" 2>&1
  printf 'Finished %s at %s; collection exit 0\n' "$probe_name" "$(date --iso-8601=seconds)"
done
guard
printf 'Frozen speed probe collection finished at %s\n' "$(date --iso-8601=seconds)"
