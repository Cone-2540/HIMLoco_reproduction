"""Verify the opt-in video overlay before entering the unchanged simulator CLI."""

import hashlib
import importlib
import json
import os
from pathlib import Path
import runpy
import sys

if os.environ.get("HIM_VIDEO_EXACT_FRAMES") != "1":
    raise RuntimeError("The exact-video launcher requires HIM_VIDEO_EXACT_FRAMES=1")

from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from moviepy.config import get_setting

if not getattr(ImageSequenceClip.iter_frames, "_him_exact_frames_v1", False):
    raise RuntimeError("Exact-video overlay failed to activate; simulator startup is refused")


def fingerprint(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


overlay = importlib.import_module("sitecustomize")
if Path(overlay.__file__).resolve() != Path(__file__).with_name("sitecustomize.py").resolve():
    raise RuntimeError("Exact-video overlay came from an unexpected directory")

evidence = {
    "schema_version": 1, "method": "integer_index_rgb_v1",
    "patched": True,
    "overlay": fingerprint(overlay.__file__), "launcher": fingerprint(__file__),
    "moviepy_image_sequence": fingerprint(importlib.import_module(
        "moviepy.video.io.ImageSequenceClip").__file__),
    "moviepy_clip": fingerprint(importlib.import_module("moviepy.Clip").__file__),
    "ffmpeg": fingerprint(get_setting("FFMPEG_BINARY")),
    "python": sys.version,
    "numpy": importlib.import_module("numpy").__version__,
}
evidence["overlay_sha256"] = evidence["overlay"]["sha256"]
evidence["launcher_sha256"] = evidence["launcher"]["sha256"]
print("HIM_VIDEO_COMPAT_ACTIVE " + json.dumps(evidence, sort_keys=True), flush=True)
runtime_script = Path(__file__).resolve().parents[1] / "run.py"
if len(sys.argv) < 2 or Path(sys.argv[1]).resolve() != runtime_script:
    raise RuntimeError("The video launcher requires the original run.py path as its first argument")
# Retain the original run.py path in the OS process command line so existing
# exact-job cleanup and idle checks still identify the simulator process.
sys.argv = [str(runtime_script)] + sys.argv[2:]
if sys.argv[1:2] == ["--video-compat-verify-only"]:
    print("HIM_VIDEO_COMPAT_ARGV " + json.dumps({
        "prepared_runtime_argv": [sys.argv[0]] + sys.argv[2:],
        "process_cmdline": Path("/proc/self/cmdline").read_bytes().decode().split("\x00")[:-1],
        "scope": "CPU-only argv and activation inspection; runtime not executed",
    }, sort_keys=True), flush=True)
    sys.exit(0)
sys.path.insert(0, str(runtime_script.parent))
runpy.run_path(str(runtime_script), run_name="__main__")
