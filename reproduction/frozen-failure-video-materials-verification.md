# Incomplete pre-failure video materials verification

Three diagnostic clips contain **1112 CPU-decoded retained frames on 19 complete chronological pages**. They exclude the terminal rendered frame and one additional policy frame (40 ms); they do not show the full failed episode or exact terminal state. Real continuous playback was not watched. Visual interpretation belongs to the parent reviewer.

| Clip | Selected env / seed | Recorded outcome | Failure time (s) | Retained nominal time (s) | Frames / pages | Paired telemetry |
|---|---:|---|---:|---:|---:|---|
| frozen-failure-long12-desc-prefailure | 416 / 211 | lateral_escape | 10.76 | 0.02–10.72 | 536 / 9 | 536 rows, 158 columns |
| frozen-failure-stretch-desc-prefailure | 481 / 101 | fall | 4.46 | 0.02–4.42 | 221 / 4 | Unavailable for selected environment |
| frozen-failure-highfriction-lip-asc-prefailure | 329 / 101 | stall | 7.14 | 0.02–7.10 | 355 / 6 | Unavailable for selected environment |

The saved trace contains case-leading environments `[0,32,...,480]`. Env481 and env329 are absent. Their indexes explicitly set `telemetry_available=false` and retain the exact selected-environment endpoint, flags and duration from `result.json`; no env480/env320 trace was substituted. Terminal endpoint measurements are separate saved result values, not paired retained video frames.

Env416 has one active dense 20 ms trace row for each of its 536 retained frames. All 158 CSV columns were compared with the selected trace and nominal frame metadata. The CSV uses LF. Summary statistics and the plot cover only the retained pre-failure interval. Foot contact-gated world-XY link speed is a descriptive proxy, not contact-point tangential slip; normal-force history does not identify exact collider contact location.

[inspect-pre-failure-frames.py](inspect-pre-failure-frames.py) reuses CPU decoding, sheet and telemetry helpers while independently requiring an explicit failed selected first episode and at most `round(failure_duration/dt)-2` frames. It accepts explicit clip arguments and `--verify-only`. All three clips passed full CPU decode, page coverage and page hash verification. Available telemetry passed exact scalar verification. In-memory negative checks rejected an extra terminal-adjacent frame, a successful episode, inactive/missing/misaligned selected trace rows and sparse selected trace stride.

Each `*-prefailure-all-frames.json` indexes all local pages and preserves provenance. Only the long-descent clip has `*-prefailure-frame-telemetry.csv`, `*-summary.json` and `*.png` materials. [Machine-readable verification](frozen-failure-video-materials-verification.json) records paths, hashes, outcomes and the exact verification command. Original clips, provenance, run config/result and runtime source were not changed.
