#!/usr/bin/env bash
# Use the user's existing Isaac Lab container; never install system packages.
set -Eeuo pipefail
BASE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export HIM_REPO_ROOT
HIM_REPO_ROOT=$(cd -- "$BASE/.." && pwd)
LAB_ROOT=${LAB_ROOT:-"$HOME/isaaclab"}
if [[ ! -f "$LAB_ROOT/compose.yaml" ]]; then
  printf 'Existing Isaac Lab compose file missing: %s/compose.yaml\n' "$LAB_ROOT" >&2
  exit 2
fi
# Accept checkpoint paths in the host checkout, even from another cwd.
args=("$@")
for ((i=0; i<${#args[@]}; i++)); do
  if [[ ${args[i]} == --checkpoint ]]; then
    (( i+1 < ${#args[@]} )) || { printf '%s\n' 'Missing checkpoint path' >&2; exit 2; }
    checkpoint=$(realpath -- "${args[i+1]}")
    case "$checkpoint" in
      "$HIM_REPO_ROOT"/*) args[i+1]="/workspace/himloco/${checkpoint#"$HIM_REPO_ROOT"/}" ;;
      /workspace/himloco/*) args[i+1]="$checkpoint" ;;
      *) printf 'Checkpoint must be inside the repository: %s\n' "$checkpoint" >&2; exit 2 ;;
    esac
  fi
done
compose=(docker compose -f "$LAB_ROOT/compose.yaml" -f "$BASE/compose.override.yaml")
"${compose[@]}" up -d
extra_args=()
for arg in "${args[@]}"; do
  if [[ $arg == --video ]]; then
    extra_args=(-e PYTHONPATH=/workspace/isaaclab/data_storage/python-extras/video)
  fi
done
exec "${compose[@]}" exec -T "${extra_args[@]}" -w /workspace/himloco/isaaclab lab \
  /isaac-sim/python.sh /workspace/himloco/isaaclab/run.py "${args[@]}"
