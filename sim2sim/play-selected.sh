#!/usr/bin/env bash
# Play the frozen night3 candidate, never silently use the previous baseline.
set -Eeuo pipefail
SIM2SIM_REPO=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
SIM2SIM_PY=${HIM_MUJOCO_ENV:-"$HOME/robotics/envs/himloco-mujoco-py311"}/bin/python
exec "$SIM2SIM_PY" "$SIM2SIM_REPO/sim2sim/run.py" \
  --policy "$SIM2SIM_REPO/artifacts/go2-night3-selected/policy.pt" \
  --config "$SIM2SIM_REPO/artifacts/go2-night3-selected/config.json" "$@"
