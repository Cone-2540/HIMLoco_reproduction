#!/usr/bin/env bash
# Keep legacy dependencies and loader settings scoped to this process.
set -Eeuo pipefail
REPO=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROBOTICS_ROOT=${ROBOTICS_ROOT:-"$HOME/robotics"}
HIM_ENV="$ROBOTICS_ROOT/envs/himloco-py37"
if [[ ! -x "$HIM_ENV/bin/python" ]]; then
  printf '未找到原版环境：%s\n请先运行 bash reproduction/setup-original.sh。\n' "$HIM_ENV" >&2
  exit 2
fi
export PATH="$HIM_ENV/bin:$PATH"
export LD_LIBRARY_PATH="$HIM_ENV/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TORCH_EXTENSIONS_DIR="$ROBOTICS_ROOT/cache/torch-extensions/himloco-py37"
export MAX_JOBS=4
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export TZ=Asia/Shanghai
cd "$REPO"
exec "$HIM_ENV/bin/python" "$@"
