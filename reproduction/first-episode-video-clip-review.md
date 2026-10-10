# CPU first-episode video clip verification

`clip-first-episode-video.py` reads the recorded environment index, its measured
first-episode duration, and the source video's frame rate/count. It re-encodes
only the retained frame range using CPU FFmpeg/libx264, then decodes the entire
output to verify its frame count, frame rate and dimensions. The adjacent JSON
records input/output hashes, the source metadata hashes and the frame boundary.

Verified with the completed isolated contact620 run, seed 47, env 416:

```bash
python3 reproduction/clip-first-episode-video.py \
  isaaclab/logs/2026-10-11_04-37-10_contact620-calf-event-isolated-video \
  --output /tmp/him-contact620-first-episode.mp4
```

The source has 861 frames at 50 fps. The clip retains exactly frames 0–702:
703 fully decoded frames, 1280 × 720, and 14.06 s encoded duration. It removes
158 trailing frames. The last retained frame has encoded PTS 14.04 s and nominal
simulation time 14.06 s. The selected environment's trace is active at 14.06 s
and first inactive at 14.08 s; output frame 703 is absent. Pixel comparisons of
the first frame, two force-event frames and three endpoint frames agree with
their source frames within 0.77 mean absolute 8-bit RGB units. Encoding is lossy;
nearly stationary adjacent endpoint frames can be similarly close.

Six CPU rejection checks passed: video ending before the episode, failed
selected episode, timeout-ending episode, inconsistent frame rate, a recorded
zero-action phase, and a trace already inactive inside the requested range.
Clean completion before the environment timeout is required because the video
recorder captures after automatic resets, while evaluation telemetry captures
before them. Failed or timeout-ending final frames cannot be safely attributed
from this saved metadata alone. Existing outputs require `--overwrite`.

Test clip: `/tmp/him-contact620-first-episode.mp4`; provenance:
`/tmp/him-contact620-first-episode.json`. No continuous video playback was
reviewed. PTS + 20 ms is the nominal mapping for these recordings; exact
renderer/physics synchronization remains uninstrumented. These checks establish
frame boundaries and encoding integrity, not locomotion smoothness.

No simulator/GPU run, production source edit, protocol-guard edit, Git operation
or package installation was performed.
