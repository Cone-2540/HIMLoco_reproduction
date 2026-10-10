#!/usr/bin/env bash
set -Eeuo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$repo_root"
video_logs=${1:-/home/cone/robotics/logs/himloco-overnight-20261011/frozen-failure-videos}
mkdir -p -- "$video_logs"
guard() {
  python3 - "$repo_root" <<'PY'
import hashlib
import json
from pathlib import Path
import sys
root = Path(sys.argv[1])
plan_file = root / 'reproduction/stair-final-evaluation-plan.json'
if hashlib.sha256(plan_file.read_bytes()).hexdigest() != 'fd27265a2d714662a3d03404903537cf6abec3c13ae2f65f21b7edf38b5391ae':
    raise SystemExit('Failure video guard: original plan changed')
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
        raise SystemExit(f'Failure video guard: changed {relative}')
PY
}
run_failure_video() {
  local video_name=$1 video_env=$2 video_seed=$3 video_speed=$4
  shift 4
  guard
  printf 'Starting %s at %s\n' "$video_name" "$(date --iso-8601=seconds)"
  bash isaaclab/run.sh evaluate --terrain stairs --reward_profile contact \
    --checkpoint artifacts/go2-stairs-control660/model_660.pt \
    --stair_batch reproduction/stair-heldout-final.json --num_envs 512 \
    --eval_seconds 40 --speed "$video_speed" --eval_randomized --eval_seed "$video_seed" \
    --seed 1 --eval_trace_stride 1 --video --video_policy_only --video_length 2000 \
    --video_isolate_env --video_env_index "$video_env" \
    --video_eye 2.4 2.4 1.7 --video_lookat 0 0 0.3 \
    --run_name "$video_name" "$@" > "$video_logs/$video_name.log" 2>&1
  printf 'Finished %s at %s; collection exit 0\n' "$video_name" "$(date --iso-8601=seconds)"
}
run_failure_video frozen-failure-long12-desc-video 416 211 0.5 --domain_profile none
run_failure_video frozen-failure-stretch-desc-video 481 101 0.3 --domain_profile none
run_failure_video frozen-failure-highfriction-lip-asc-video 329 101 0.3 --domain_profile basic --friction 1.0 0.8
guard
printf 'Selected failure video collection finished at %s\n' "$(date --iso-8601=seconds)"
