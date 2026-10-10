# Original Isaac Gym baseline records

The files in this directory record the CPU Go2 baseline verified on 2026-10-10.
They contain no simulator binaries, Python environments, training checkpoints, or
download archives. `${ROBOTICS_ROOT}` means the shared user software directory
(default `$HOME/robotics`); `${REPO_ROOT}` means this checkout. These placeholders
in JSON files are documentation, not shell expansion performed by the simulator.

- `setup-original.sh`: user-level installer using official sources and locked
  versions. It never runs sudo, installs system CUDA/driver packages, or edits
  shell startup files. It retains NVIDIA license files in the extracted package.
- `original-conda-explicit.txt`: Linux x86_64 Python 3.7.16 bootstrap package lock.
- `original-requirements.txt`: project-local pip package versions, including the
  repository's PyTorch 1.10.0+cu113 requirement and compatibility pins. Editable
  Isaac Gym, rsl_rl, and legged_gym packages are installed separately. Host ROS
  packages seen via the local machine's PYTHONPATH are intentionally excluded.
- `downloads.json`, `original-wheel-sha256.txt`, `sources.json`: upstream URLs,
  commits, and hashes for downloaded binaries/assets. Binaries remain external.
- `validation-original.json`: original CPU train/play/export/render results and
  failed GPU/rough-terrain checks. The `passed` status establishes execution and
  finite values; the 100-iteration policy has not converged to stable walking.
- `driver-original.json`: original host driver version and unchanged file hashes.

The installer reuses existing expected locations and checks Python/micromamba
versions. It is syntax-checked and uses the installed baseline's locked files;
it has not been tested by deleting and reinstalling the working environment.
Flat-ground CPU verification is the supported baseline. The original PyTorch
wheel cannot execute RTX 5080 (`sm_120`) kernels, and rough CPU terrains exhibited
collision anomalies on this machine.
