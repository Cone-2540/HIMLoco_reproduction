# Frozen staircase video materials verification

Four complete selected first episodes contain **3212 CPU-decoded frames**, **56 contact-sheet pages**, and **3212 paired dense telemetry rows**. Every retained frame occurs exactly once in chronological sheets and the CSV; all recorded telemetry values were checked against the corresponding selected-environment trace, and the generated frame metadata was checked against the expected frame index and time convention (158 columns total).

| Episode | Env / case | Geometry | Frames / seconds | Pages | Trailing frames removed |
|---|---:|---|---:|---:|---:|
| 16cm-asc | 0 / 0 | 6 × 16 cm / 27 cm; asc | 623 / 12.46 | 11 | 6 |
| 16cm-desc | 0 / 0 | 6 × 16 cm / 27 cm; desc | 678 / 13.56 | 12 | 11 |
| long12-asc | 384 / 12 | 12 × 17 cm / 25 cm; asc | 890 / 17.80 | 15 | 141 |
| long12-desc | 416 / 13 | 12 × 17 cm / 25 cm; desc | 1021 / 20.42 | 18 | 10 |

All four use frozen control660 checkpoint SHA256 `79fcc69b9447ecfb4df9fcfb41224cdab78632649f38fd9faf09c7b6adf69c61`, reset seed 101, configured forward speed 0.3 m/s, and 50 fps. Each selected episode completed without fall, stall, or lateral escape before timeout. The two six-step video trials completed 32/32 environments each. The long video trials each contain the full 16-case, 512-environment matrix: 492 completions, 17 falls and 3 stalls. Failed case 15 is six-step descent at 23 cm height / 20 cm depth (12/32 completed). These successful selected long clips do not establish that the whole batch passed.

Run configs retain source commit `be0801ffba1f0accd7c78b0958e817e31512c940` and `source_tracked_files_dirty=true`. Runtime-source freeze validation and actor identity are covered by the independent frozen-policy audit; this material report does not replace those checks.

Sheets are 1920 × 2012 pixels, six columns by ten rows, with 320 × 180 thumbnails. A fixed original-image crop `(360, 300, 1000, 660)` was checked at the beginning, middle and endpoint of each video to choose readable framing. Every thumbnail carries its zero-based frame index, encoded PTS and nominal simulation time. Cropping and view occlusion remain relevant when judging limb contact. Robot USD visibility isolation is recorded in each config and does not remove neighboring terrain from the long-case background.

Pinned recorder begins after first policy step. Frame n encoded PTS is n/50 seconds; nominal matching dense trace time is (n+1)*0.02 seconds. Exact render/physics synchronization was not independently instrumented. Episode telemetry is measured before reset; failed or timeout-ending selected episodes are rejected by clipping guard.

CSV fields cover root position and world velocity, yaw/roll/pitch, four feet positions/world-XY speed/current and retained contacts, 12 actions named by joint, action deltas, flight pause, base/shank forces, eight named thigh/calf current and retained force norms, current force vectors and link world poses, and commanded velocities. All CSV rows are active, finite and time-aligned. Descriptive JSON and six-panel plots cover the entire episode, including startup. Figures and summary statistics refer to the selected environment only.

Camera and thumbnail occlusion can hide feet/calf surfaces. Foot world-XY link speed gated by current or retained normal-force contact is a proxy, not contact-point tangential slip. History force can exceed the current recorded policy-boundary sample. Full frame coverage does not certify smooth locomotion or absence of scraping.

**Real continuous playback was not watched.** The parent reviewer separately inspects every contact-sheet page in order and records the scope of that visual review. This report verifies material completeness and recorded telemetry pairing.

## Artifacts

- `frozen-control660-16cm-asc`: [`clip`](frozen-control660-16cm-asc-first-episode.mp4), [`provenance`](frozen-control660-16cm-asc-first-episode.json), [`all-frame page index`](frozen-control660-16cm-asc-all-frames.json), [`CSV`](frozen-control660-16cm-asc-frame-telemetry.csv), [`summary`](frozen-control660-16cm-asc-frame-telemetry-summary.json), [`plot`](frozen-control660-16cm-asc-frame-telemetry.png).
- `frozen-control660-16cm-desc`: [`clip`](frozen-control660-16cm-desc-first-episode.mp4), [`provenance`](frozen-control660-16cm-desc-first-episode.json), [`all-frame page index`](frozen-control660-16cm-desc-all-frames.json), [`CSV`](frozen-control660-16cm-desc-frame-telemetry.csv), [`summary`](frozen-control660-16cm-desc-frame-telemetry-summary.json), [`plot`](frozen-control660-16cm-desc-frame-telemetry.png).
- `frozen-control660-long12-asc`: [`clip`](frozen-control660-long12-asc-first-episode.mp4), [`provenance`](frozen-control660-long12-asc-first-episode.json), [`all-frame page index`](frozen-control660-long12-asc-all-frames.json), [`CSV`](frozen-control660-long12-asc-frame-telemetry.csv), [`summary`](frozen-control660-long12-asc-frame-telemetry-summary.json), [`plot`](frozen-control660-long12-asc-frame-telemetry.png).
- `frozen-control660-long12-desc`: [`clip`](frozen-control660-long12-desc-first-episode.mp4), [`provenance`](frozen-control660-long12-desc-first-episode.json), [`all-frame page index`](frozen-control660-long12-desc-all-frames.json), [`CSV`](frozen-control660-long12-desc-frame-telemetry.csv), [`summary`](frozen-control660-long12-desc-frame-telemetry-summary.json), [`plot`](frozen-control660-long12-desc-frame-telemetry.png).

Machine-readable cross-verification: [frozen-video-materials-verification.json](frozen-video-materials-verification.json).

## Reproduction

[inspect-first-episode-frames.py](inspect-first-episode-frames.py) uses existing clips, adjacent provenance and raw saved run JSON. Its default inputs are the four frozen clips. `python3 -B reproduction/inspect-first-episode-frames.py --verify-only` passed for all 3212 frames, all 56 sheet hashes/coverage and all CSV values. Use `--overwrite` to regenerate local full sheets and telemetry. The CSV writer now uses LF line endings; the four CSV files were rebuilt with identical numeric content and their summary hashes updated. Existing complete page files and coverage indexes were kept byte for byte. A separate generation roundtrip under `/tmp/him-frame-inspector-roundtrip`, repeated after LF normalization, reproduced the 623-row CSV byte for byte and confirmed all 11 ascent sheet files remain byte identical. The script requires existing OpenCV, Pillow, NumPy and Matplotlib; it never starts the simulator.
