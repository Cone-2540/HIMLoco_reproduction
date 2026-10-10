#!/usr/bin/env bash
# Install the original software stack inside a user-owned robotics directory.
# No sudo, shell initialization, host CUDA Toolkit, or driver/config changes.
set -Eeuo pipefail
if [[ ${1:-} == --help ]]; then
  printf '%s\n' \
    'Usage: ROBOTICS_ROOT="$HOME/robotics" bash reproduction/setup-original.sh' \
    'Requires Linux x86_64, curl, tar, sha256sum and an existing C++ compiler.' \
    'Downloads NVIDIA Isaac Gym Preview 4 and micromamba 2.9.0 from official sources.' \
    'Creates envs/himloco-py37 using the pinned conda/pip manifests beside this script.' \
    'NVIDIA license files are retained in the extracted simulator directory.'
  exit 0
fi
if [[ $# -gt 0 ]]; then
  printf 'Unknown argument: %s\n' "$1" >&2
  exit 2
fi
if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
  printf '%s\n' 'This locked environment requires Linux x86_64.' >&2
  exit 2
fi
for tool in curl tar sha256sum c++; do
  if ! command -v "$tool" >/dev/null; then
    printf 'Required existing tool is missing: %s\n' "$tool" >&2
    exit 2
  fi
done

REPRO=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO=$(cd -- "$REPRO/.." && pwd)
ROBOTICS_ROOT=${ROBOTICS_ROOT:-"$HOME/robotics"}
mkdir -p -- "$ROBOTICS_ROOT"
ROBOTICS_ROOT=$(cd -- "$ROBOTICS_ROOT" && pwd)
HIM_ENV="$ROBOTICS_ROOT/envs/himloco-py37"
GYM_ROOT="$ROBOTICS_ROOT/simulators/isaacgym-preview4"
MAMBA="$ROBOTICS_ROOT/tools/bin/micromamba"
mkdir -p -- "$ROBOTICS_ROOT"/{downloads,tools/bin,tools/mamba,envs,simulators,cache/pip}
export MAMBA_ROOT_PREFIX="$ROBOTICS_ROOT/tools/mamba"
export PIP_CACHE_DIR="$ROBOTICS_ROOT/cache/pip"
export PYTHONNOUSERSITE=1
unset PYTHONPATH

download_checked() {
  local url=$1 archive=$2 digest=$3
  if [[ ! -f "$archive" ]]; then
    curl --fail --location --retry 3 --connect-timeout 30 --output "$archive.part" "$url"
    printf '%s  %s\n' "$digest" "$archive.part" | sha256sum --check --status
    mv -- "$archive.part" "$archive"
  fi
  if ! printf '%s  %s\n' "$digest" "$archive" | sha256sum --check --status; then
    printf 'Archive hash mismatch; inspect or remove this file before retrying: %s\n' "$archive" >&2
    exit 2
  fi
}

if [[ ! -x "$MAMBA" ]]; then
  mamba_archive="$ROBOTICS_ROOT/downloads/micromamba-linux-64.tar.bz2"
  download_checked 'https://micro.mamba.pm/api/micromamba/linux-64/2.9.0' \
    "$mamba_archive" '8761c382127e6363bd9e0a2451aa3ef90d071a79133f736e2f759a3bf13040dd'
  tar -xjf "$mamba_archive" -C "$ROBOTICS_ROOT/tools" bin/micromamba
fi
if [[ $("$MAMBA" --version) != 2.9.0 ]]; then
  printf 'Expected micromamba 2.9.0 at %s; existing file was left unchanged.\n' "$MAMBA" >&2
  exit 2
fi

gym_archive="$ROBOTICS_ROOT/downloads/IsaacGym_Preview_4_Package.tar.gz"
download_checked 'https://developer.nvidia.com/isaac-gym-preview-4' \
  "$gym_archive" 'c51d77ac1144b91b356f439c7313d8d59468147e37187ebffe7cdbc3154fdb8f'
if [[ ! -e "$GYM_ROOT" ]]; then
  gym_stage=$(mktemp -d "$ROBOTICS_ROOT/simulators/.isaacgym-preview4.XXXXXX")
  trap 'rm -rf -- "$gym_stage"' EXIT
  tar -xzf "$gym_archive" -C "$gym_stage" --strip-components=1
  mv -- "$gym_stage" "$GYM_ROOT"
  trap - EXIT
fi
if [[ ! -f "$GYM_ROOT/python/isaacgym/_bindings/linux-x86_64/gym_37.so" ]]; then
  printf 'Expected Preview 4 Python 3.7 bindings are missing from %s\n' "$GYM_ROOT" >&2
  exit 2
fi

if [[ ! -e "$HIM_ENV" ]]; then
  "$MAMBA" create --yes --prefix "$HIM_ENV" --file "$REPRO/original-conda-explicit.txt"
fi
if [[ ! -x "$HIM_ENV/bin/python" ]] || \
   [[ $("$HIM_ENV/bin/python" -c 'import platform; print(platform.python_version())') != 3.7.16 ]]; then
  printf 'Expected Python 3.7.16 at %s; existing directory was left unchanged.\n' "$HIM_ENV" >&2
  exit 2
fi
"$HIM_ENV/bin/python" -m pip install \
  --find-links https://download.pytorch.org/whl/cu113/torch_stable.html \
  --requirement "$REPRO/original-requirements.txt"
"$HIM_ENV/bin/python" -m pip install --no-deps --editable "$GYM_ROOT/python" \
  --editable "$REPO/rsl_rl" --editable "$REPO/legged_gym"
"$HIM_ENV/bin/python" -m pip check
printf 'Original environment ready at %s\nRun: bash original.sh train --max_iterations 100\n' "$HIM_ENV"
