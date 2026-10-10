#!/usr/bin/env bash
# Optional video dependencies live in the existing container's shared data mount.
set -Eeuo pipefail
BASE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export HIM_REPO_ROOT
HIM_REPO_ROOT=$(cd -- "$BASE/.." && pwd)
LAB_ROOT=${LAB_ROOT:-"$HOME/isaaclab"}
compose=(docker compose -f "$LAB_ROOT/compose.yaml" -f "$BASE/compose.override.yaml")
"${compose[@]}" up -d
"${compose[@]}" exec -T lab /isaac-sim/python.sh -m pip install \
  --target /workspace/isaaclab/data_storage/python-extras/video --no-deps \
  'moviepy==1.0.3' 'imageio==2.37.2' 'imageio-ffmpeg==0.6.0' \
  'decorator==4.4.2' 'proglog==0.1.12'
