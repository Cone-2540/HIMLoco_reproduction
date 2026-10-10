#!/usr/bin/env bash
set -Eeuo pipefail
REPO=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mode=${1:-help}
if [[ "$mode" == train || "$mode" == play ]]; then
  shift
  export HIM_VERIFY_MODE="$mode"
  if [[ "$mode" == play ]]; then
    if [[ $# -lt 1 || ! -f "$1" ]]; then
      printf '%s\n' '回放用法：bash original.sh play 路径/model_100.pt [其他参数]' >&2
      exit 2
    fi
    export HIM_VERIFY_CHECKPOINT
    HIM_VERIFY_CHECKPOINT=$(realpath -- "$1")
    shift
  fi
  # Resolve in the caller's directory before run-original.sh changes to the repo.
  if [[ -n ${HIM_VERIFY_CHECKPOINT:-} ]]; then
    if [[ ! -f "$HIM_VERIFY_CHECKPOINT" ]]; then
      printf '未找到 checkpoint：%s\n' "$HIM_VERIFY_CHECKPOINT" >&2
      exit 2
    fi
    export HIM_VERIFY_CHECKPOINT
    HIM_VERIFY_CHECKPOINT=$(realpath -- "$HIM_VERIFY_CHECKPOINT")
  fi
  exec bash "$REPO/run-original.sh" "$REPO/verify_original.py" \
    --task go2 --num_envs 64 --max_iterations 100 \
    --sim_device cpu --rl_device cpu --pipeline cpu "$@"
fi
printf '%s\n' \
  '平地训练：bash original.sh train --max_iterations 100' \
  '无窗口回放：bash original.sh play 路径/model_100.pt --num_envs 16' \
  '带窗口回放：HIM_VERIFY_RENDER=1 bash original.sh play 路径/model_100.pt --num_envs 1' \
  '默认 CPU 与平地；详见 README_local_zh.md。'
