# Bootstrap120 8 cm video review

The sampled video frames, cross-checked with the recorded first-episode
telemetry, support complete traversal of the six 8 cm steps by the camera's
representative robot, env0, in both directions. Ascent reaches the upper
landing; descent reaches the lower landing. All four feet are beyond the
final-platform start in the last valid recorded states, at the expected
relative heights of approximately +0.48 m and −0.48 m.

Sampled poses remain upright, with leg flexion and no visible overturning or
belly support. In recorded env0 stair-flight samples, peak absolute roll is
approximately 3.31° ascent / 5.81° descent, and peak absolute pitch is
approximately 16.75° / 14.36°. No base contact was reported. These samples
do not establish smoothness or exclude motion between sampled frames; no
matching baseline video was compared. The observed robot is one environment,
not every environment in the evaluation batch.

## Separate policy and control footage

The original recordings include the default zero-action negative control.
Their final return to the starting platform is an evaluation reset, not a
failed traversal or continued policy walking.

| Recording | Total video | Policy batch phase | Env0 measured policy episode | Reset-and-zero-action control |
|---|---|---|---|---|
| Ascent | 949 frames, 18.98 s | Frames 0–747; 0 ≤ video t < 14.96 s | Simulation time through completion at 13.28 s; active policy video ends around 13.26 s | Frames 748–948; 14.96 ≤ t < 18.98 s |
| Descent | 901 frames, 18.02 s | Frames 0–699; 0 ≤ video t < 14.00 s | Simulation time through completion at 13.86 s; active policy video ends around 13.84 s | Frames 700–900; 14.00 ≤ t < 18.02 s |

The recorder captures once after each environment step at 50 fps. Its frame
PTS begins at zero, so recorded simulation-step time is approximately video
time plus 0.02 s. Ascent has a one-frame display delay at the control reset:
frame748 at 14.96 s still shows the upper platform, while frame749 at 14.98 s
first shows the reset lower starting platform. Descent visibly resets at
frame700, 14.00 s. Use execution-phase boundaries when trimming, rather than
assuming the first visibly changed frame is the first control step.

After env0 completes, the evaluator zeros its actions while the remaining
batch finishes. Thus ascent from roughly 13.28 s simulation time to 14.96 s,
and descent from 13.86 s to 14.00 s, are completed-env holding periods within
the policy batch. They are not evidence of ongoing policy behavior. They
are also distinct from the subsequent reset-and-zero-action control.

The separate ascent video evaluation completes 30/32 with two stalls; the
descent video evaluation completes 32/32. This single-seed/single-geometry
recording is a different batch from the earlier eight-case, three-seed
validation, where 8 cm ascent completed 94/96. Do not combine their counts
or replace the broader validation with the successful camera env0.

## Policy-only recording option

`isaaclab/run.py` now accepts `--video_policy_only` only together with
`--video`, `evaluate`, and `--terrain stairs`. It passes
`include_zero_action=False` to the existing staircase evaluation suite.
The default evaluation continues to include the negative control.

The configuration records `video_policy_only`,
`evaluation_include_zero_action`, `video_length`, and `video_fps`.
For a continuous single-flight policy recording, use one reset seed and one
checkpoint; this flag only removes the zero-action control phase. Multiple
reset seeds and candidate checkpoints still begin separate trials, and
physics termination behavior remains as configured. A long enough
`--video_length` is needed to capture the entire flight.

CPU checks passed: source compilation, 18 combinations of mode/terrain/video
to validate CLI restrictions, default negative-control behavior, suite
argument association, and configuration metadata association. No new GPU
evaluation was launched to test the option during this review.

## Evidence

- `stair-bootstrap120-8cm-ascent-frames.png` and
  `stair-bootstrap120-8cm-descent-frames.png`: previously generated snapshots.
- `stair-bootstrap120-8cm-video-phase-boundary.png`: frames around the control
  reset, with explicit direction and video time.
- `stair-bootstrap120-8cm-video-review.json`: video frame counts, timing,
  representative completion and pose data, and source provenance.
- Raw ascent: `isaaclab/logs/2026-10-11_02-12-01_bootstrap120-8cm-asc-video/videos/go2_stairs_asc_0000.mp4`.
- Raw descent: `isaaclab/logs/2026-10-11_02-14-22_bootstrap120-8cm-desc-video/videos/go2_stairs_desc_0000.mp4`.
