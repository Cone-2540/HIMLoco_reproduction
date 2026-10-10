# Frozen control660 complete frame-sequence review

This review inspects every retained frame in chronological contact-sheet
order, linked to dense 20 ms first-episode telemetry. It is not a real-time
video playback review: no video player was used. Complete decoded-frame
coverage improves on selected stills, but does not by itself certify continuous
smoothness. The frozen policy and criteria are unchanged.

## Six-step 16 cm ascent, 0.3 m/s

Source run: `isaaclab/logs/2026-10-11_05-48-28_frozen-control660-16cm-asc-video`.
Recorded env 0, seed 101, primary archived control660 / `contact`, with external
heading correction. Policy-only rendering hides other environments without
changing physics. Source records commit `be0801f` and tracked-files dirty;
the independent audit verified all 28 frozen runtime source hashes.

The first episode completes in 12.46 s. Its clip retains all 623 frames
0–622 at 50 fps, removing six later frames. Every frame was visually inspected
in chronological row-major order on `frozen-control660-16cm-asc-all-frames/`
pages 01–11; the adjacent coverage JSON records each page, frame range and
hash. Every retained frame maps to one active dense trace sample from
0.02–12.46 s. Encoded PTS is nominal simulation time minus 20 ms; renderer
versus physics timing was not independently instrumented.

| Pages / simulation interval | Complete-sequence observation |
| --- | --- |
| 01–02 / 0.02–2.40 s | Continuous approach on the lower landing; regular leg cycling, no pose discontinuity or visible loss of support. |
| 03 / 2.42–3.60 s | Foreleg approach to the first riser transitions into lift around 3.3 s; body pitches for ascent while hind feet remain below. No reset or sustained stop is visible. |
| 04–06 / 3.62–7.20 s | Repeated staggered foot lifts and rising body translation continue through the flight. Far-side legs and parts of the feet are occluded by the body/steps. |
| 07–08 / 7.22–9.60 s | Forelegs reach the upper landing around 8.2–8.4 s and hind legs follow; body pitch relaxes across this transition. |
| 09–11 / 9.62–12.46 s | Continued forward walking on the upper platform to the completion boundary; no visible fall, autoreset or long halt. |

The visual sequence agrees with clean recorded completion and zero flight
pause frames. It does **not** establish no leg/riser contact: the selected
env records FL_calf current force 167.54 N at 5.44 s and RR_calf 87.19 N at
6.46 s. Current base force is zero throughout. Framewise body roll ranges
−0.09396 to +0.03124 rad; pitch follows the climbing posture and must not be
assessed against flat horizontal posture alone. Contact-gated foot world-XY
speeds include appreciable tails; they are foot-link velocity proxies, not
exact contact-point slip. Camera occlusion and thumbnail resolution prevent
exact scrape/contact-point attribution.

The entire 32-env scene completes 32/32 with zero fall/stall/escape/base-contact
counts, but its aggregate metrics are distinct from the single recorded env.
Neither this scene nor the selected video's success erases failed cases in
the independent 16-case matrix. No claim of silky locomotion or real-robot
readiness is made. A matching competent baseline and actual continuous
playback remain needed for the separately declared smoothness acceptance.

Supporting artifacts: first-episode MP4/JSON, all-frame coverage JSON/pages,
`frozen-control660-16cm-asc-frame-telemetry.csv` (623 rows × 158 columns), its
summary JSON and full-duration telemetry figure. Telemetry was checked as
complete, active, finite and ordered without duplicate or skipped frames.

## Six-step 16 cm descent, 0.3 m/s

Source run: `isaaclab/logs/2026-10-11_05-50-31_frozen-control660-16cm-desc-video`.
Recorded env 0, seed 101 completes cleanly in 13.56 s. All 678 retained
frames 0–677 were inspected on pages 01–12 in chronological row-major order,
including the final 18-frame page. Eleven source frames after the selected
completion were excluded; no first-episode frame was skipped. Dense trace
has one active finite sample per retained frame, from 0.02–13.56 s.

| Pages / simulation interval | Complete-sequence observation |
| --- | --- |
| 01–02 / 0.02–2.40 s | Regular walking on the upper landing approaches the descending edge. |
| 03 / 2.42–3.60 s | Forelegs begin stepping below the top edge; hind legs remain on the higher landing and the body follows the grade. |
| 04–07 / 3.62–8.40 s | Staggered downward leg cycles continue with forward/downward translation through the flight. No reset or sustained halt appears in the inspected sequence. |
| 08–10 / 8.42–12.00 s | Forelegs reach the lower landing while hind legs finish the last steps; body pitch relaxes as all four legs transition onto the landing. |
| 11–12 / 12.02–13.56 s | Regular forward walking continues on the lower platform to completion, with no visible fall or pose discontinuity. |

The selected episode has zero flight pause frames and zero current base
contact. It has calf contact: current FR_calf peak 101.26 N at 5.50 s;
the sensor-history maximum is 252.81 N. The current force sampled once per
20 ms policy step can miss an intervening physics peak, so the lower current
peak is not evidence of negligible scraping. Body roll is −0.08707 to
+0.04957 rad and yaw −0.04578 to +0.00603 rad. These measurements support
bounded pose during this episode without establishing exact foot placement,
contact-point slip, or comparative smoothness. Far legs/feet are periodically
occluded. No true continuous playback was performed.

Supporting artifacts use prefix `frozen-control660-16cm-desc`: first-episode
MP4/JSON, all-frame coverage JSON/pages, the 678 × 158 CSV, summary JSON and
telemetry figure. The single recorded success does not replace the complete
heldout matrix or the separately declared baseline/smoothness acceptance.

## Twelve-step 17/25 cm descent, 0.3 m/s

Source run: `isaaclab/logs/2026-10-11_05-52-20_frozen-control660-long12-desc-video`.
The selected env 416 is case 13 (17 cm rise / 25 cm tread / 12 steps),
seed 101. It completes cleanly in 20.42 s. All 1,021 retained frames 0–1,020
were inspected on pages 01–18, including the last single-frame page. Ten
trailing source frames were removed. Every retained frame has an active
finite trace sample at 20 ms intervals from 0.02–20.42 s.

| Pages / simulation interval | Complete-sequence observation |
| --- | --- |
| 01–02 / 0.02–2.40 s | Walking approaches the top edge on the upper landing. |
| 03–04 / 2.42–4.80 s | Forelegs extend below the landing; hind legs follow into the flight. The body adopts a descending posture without a visible reset or fall. |
| 05–13 / 4.82–15.60 s | Repeated staggered leg cycles and forward/downward body translation continue through the longer flight. The full sequence contains no sustained halt or large pose discontinuity. |
| 14–15 / 15.62–18.00 s | Forelegs reach the bottom landing, followed by hind-leg transitions over the final steps; pitch relaxes towards the flat posture. |
| 16–18 / 18.02–20.42 s | Forward walking continues away from the stairs to the completion boundary, with no visible fall. |

This selected episode has zero flight pause frames and current base force
zero. Current FR_calf peak is 107.95 N at 16.14 s; history peak is 394.81 N,
so policy-boundary current samples alone would understate physics contact
peaks. Roll is −0.07527 to +0.04622 rad and yaw −0.04099 to +0.01295 rad.
The root moves from course-frame y = 0.04047 m after the first step to
0.27145 m at completion, demonstrating some lateral drift despite small yaw.
The clip does not establish zero scraping, precise contact-point slip or a
smoothness pass. Occlusion and thumbnail resolution limit attribution of
individual contacts to stair edges.

Other 511 robots were hidden from this rendering; their physics remained
active and neighboring terrain remained visible. The whole 512-env scene
has 492/512 completions and preserves failures in case 15. Selected case 13
completion must not be presented as a full matrix pass. Supporting artifacts
use prefix `frozen-control660-long12-desc`: clip/metadata, 18 pages/coverage
JSON, 1,021 × 158 CSV, summary JSON and full-duration figure. No real-time
continuous playback was performed.

## Twelve-step 17/25 cm ascent, 0.3 m/s

Source run: `isaaclab/logs/2026-10-11_05-54-57_frozen-control660-long12-asc-video`.
The selected env 384 is case 12, seed 101, and completes cleanly in 17.80 s.
All 890 retained frames 0–889 were inspected on pages 01–15 in chronological
row-major order, including the final 50-frame page. The 141 source frames
after selected completion were excluded; other environments continue in
those frames, so they do not belong to this selected first episode. All 890
dense samples are active and finite, ordered from 0.02–17.80 s.

| Pages / simulation interval | Complete-sequence observation |
| --- | --- |
| 01–02 / 0.02–2.40 s | Continuous lower-landing approach to the flight. |
| 03 / 2.42–3.60 s | Foreleg lifts begin the first riser around 3.3 s, followed by increasing body pitch and hind-leg entry. |
| 04–11 / 3.62–13.20 s | Repeated staggered lifts move the body upward along all 12 steps, without a visible reset, fall or sustained halt. Forefeet and far-side lower legs are frequently obscured by the stair/side geometry. |
| 12–13 / 13.22–15.60 s | Forelegs transition onto the upper landing around 13.5 s; hind legs follow and the body posture relaxes. |
| 14–15 / 15.62–17.80 s | Continued walking on the upper landing to completion with no visible fall or pose discontinuity. |

Current base force is zero and flight pause frames are zero. Calf contacts
remain: FL_calf current peak 84.32 N at 7.24 s (history 139.69 N), and
RR_calf current peak 72.08 N at 13.86 s (history 116.91 N). Roll is
−0.10290 to +0.04237 rad, yaw −0.07666 to +0.01660 rad. Pitch reaches
−0.58970 rad during climbing and cannot be interpreted as flat-ground
attitude error. Root y moves from 0.02315 m after the first step to 0.18183 m
at completion. Bounded pose and clean selected completion do not establish
contact-free ascent, measured contact-point slip, smoothness acceptance or
whole-matrix success. The 512-env run retains case 15 failures and completes
492/512 overall. No true continuous playback was performed.

Supporting artifacts use prefix `frozen-control660-long12-asc`: clip/metadata,
15 contact-sheet pages/coverage JSON, the 890 × 158 dense CSV, summary JSON
and full-duration figure. Across the four reviewed clips, every one of 3,212
retained frames on 56 pages was visually inspected. The independent material
verification records page hashes and exact CSV/trace correspondence. This
review only covers the four selected successful episodes at 0.3 m/s, while
the frozen evaluation explicitly retains other cases and conditions that fail.
