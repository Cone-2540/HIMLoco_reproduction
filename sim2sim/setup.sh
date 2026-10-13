#!/usr/bin/env bash
set -Eeuo pipefail
SIM2SIM_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
SIM2SIM_ENV=${HIM_MUJOCO_ENV:-"$HOME/robotics/envs/himloco-mujoco-py311"}
SIM2SIM_MAMBA=${HIM_MICROMAMBA:-"$HOME/robotics/tools/bin/micromamba"}
if [[ ! -x "$SIM2SIM_ENV/bin/python" ]]; then
  "$SIM2SIM_MAMBA" create -y -p "$SIM2SIM_ENV" -c conda-forge python=3.11 pip
fi
"$SIM2SIM_ENV/bin/python" -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.6.0+cpu'
"$SIM2SIM_ENV/bin/python" -m pip install -r "$SIM2SIM_ROOT/requirements.txt"
"$SIM2SIM_ENV/bin/python" "$SIM2SIM_ROOT/fetch_assets.py" "$@"
"$SIM2SIM_ENV/bin/python" -m unittest discover -s "$SIM2SIM_ROOT" -p test_interface.py -v
