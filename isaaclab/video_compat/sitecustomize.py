"""Project-scoped MoviePy compatibility for Isaac Lab RGB video recordings.

Enabled only by run.sh --video with HIM_VIDEO_EXACT_FRAMES=1. MoviePy 1.0.3's
float time lookup can duplicate or skip RGB cache entries with NumPy 2, and
floating clip duration can add an extra encoded frame. Read RGB cache entries
directly by integer index instead. Installed packages and simulation code are
untouched. Unsupported sequence modes fail explicitly in this isolated path.
"""

import os


if os.environ.get("HIM_VIDEO_EXACT_FRAMES") == "1":
    import math
    import hashlib
    import json
    from pathlib import Path
    import sys

    import numpy as np
    from moviepy.video.io.ImageSequenceClip import ImageSequenceClip

    _overlay_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    def _exact_rgb_cache_frames(self, fps=None, with_times=False, logger=None, dtype=None):
        """Emit each RGB array cache entry exactly once, in cache order."""
        sequence = self.sequence
        if len(sequence) == 0 or not all(isinstance(frame, np.ndarray) for frame in sequence):
            raise ValueError("HIM exact video cache requires a nonempty sequence of RGB arrays")
        resolved_fps = float(self.fps if fps is None else fps)
        source_fps = float(self.fps)
        if not math.isfinite(resolved_fps) or resolved_fps <= 0:
            raise ValueError("HIM exact video cache requires a finite positive fps")
        if not math.isclose(resolved_fps, source_fps, rel_tol=0, abs_tol=1e-9):
            raise ValueError("HIM exact video cache forbids fps resampling")
        # Fail explicitly instead of silently returning to float lookup.
        if not all(frame.ndim == 3 and frame.shape[2] == 3 for frame in sequence):
            raise ValueError("HIM exact video cache supports RGB arrays with shape HxWx3")
        yielded = 0
        for index in range(len(sequence)):
            frame = sequence[index]
            if dtype is not None and frame.dtype != dtype:
                frame = frame.astype(dtype)
            yielded += 1
            yield (index / resolved_fps, frame) if with_times else frame
        print("HIM_VIDEO_COMPAT_EMITTED " + json.dumps({
            "schema_version": 1, "method": "integer_index_rgb_v1",
            "cache_frame_count": len(sequence), "frames_yielded": yielded,
            "fps": resolved_fps, "overlay_sha256": _overlay_sha256,
        }, sort_keys=True), file=sys.stderr, flush=True)

    _exact_rgb_cache_frames._him_exact_frames_v1 = True
    ImageSequenceClip.iter_frames = _exact_rgb_cache_frames
    print("[HIMVideoCompat] RGB cache frames use exact integer indices (project overlay)",
          file=sys.stderr)
