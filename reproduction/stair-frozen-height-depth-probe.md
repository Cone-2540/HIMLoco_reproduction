# Frozen rise/tread geometry probe

Status: complete. These are separate diagnostics with the frozen primary control660,zero gradient updates and unchanged original case/seed gates. They do not replace the original final matrix or select a new checkpoint.

| Evaluation | Speed(m/s) | Completed | Worst case/seed | Fall/stall/escape flags | History base | Original whole-matrix gate | Maxpause(s) |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: |
| height_depth_probe_03 | 0.3 | 1656/1728 | 13/32 | 47/25/0 | 36 | FAIL | 3.64 |
| height_depth_probe_05 | 0.5 | 1725/1728 | 31/32 | 2/1/0 | 0 | PASS | 3.72 |

The0.3m/s map fails four descent cases; all nine ascent cases complete without failure flags. At0.5m/s all original case/reset seed gates pass with1725/1728 completions,but23cm/20 cm descent has one stall and a3.72s maximum pause,and23cm/27 cm descent has two fall flags. This local6-step adaptive diagnostic is neither zero failure nor a smoothness certificate and does not cover the12-step long-descent failure in the original final matrix.

Failure flags are nonexclusive. JSON/CSV retain unique noncompletions, all anomalies, zero-action controls, each case/seed gate and exposure. Command exit0 means saved collection,not scientific acceptance.

| Evaluation | Case | Completed by reset seed | Counts fall/stall/escape/base | Original all-seed gate | Full zero failure traversal |
| --- | --- | --- | --- | --- | --- |
| height_depth_probe_03 | asc_probe18cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_03 | desc_probe18cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_03 | asc_probe18cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_03 | desc_probe18cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_03 | asc_probe18cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_03 | desc_probe18cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_03 | asc_probe20cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_03 | desc_probe20cm_20cm | 32/31/30 | 0/3/0/0 | FAIL | False |
| height_depth_probe_03 | asc_probe20cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_03 | desc_probe20cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_03 | asc_probe20cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_03 | desc_probe20cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_03 | asc_probe23cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_03 | desc_probe23cm_20cm | 15/13/20 | 37/11/0/36 | FAIL | False |
| height_depth_probe_03 | asc_probe23cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_03 | desc_probe23cm_27cm | 27/27/27 | 8/7/0/0 | FAIL | False |
| height_depth_probe_03 | asc_probe23cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_03 | desc_probe23cm_33cm | 30/29/31 | 2/4/0/0 | FAIL | False |
| height_depth_probe_05 | asc_probe18cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | desc_probe18cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | asc_probe18cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | desc_probe18cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | asc_probe18cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | desc_probe18cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | asc_probe20cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | desc_probe20cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | asc_probe20cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | desc_probe20cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | asc_probe20cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | desc_probe20cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | asc_probe23cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | desc_probe23cm_20cm | 32/31/32 | 0/1/0/0 | PASS | False |
| height_depth_probe_05 | asc_probe23cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | desc_probe23cm_27cm | 32/31/31 | 2/0/0/0 | PASS | False |
| height_depth_probe_05 | asc_probe23cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| height_depth_probe_05 | desc_probe23cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |

## Rise/tread boundary tables

Each cell is completed/96 across three reset seeds followed by the unchanged all-seed gate. FAIL may come from basecontact or individual failure fractions even when completion is high.

### 0.3 m/s asc

| Rise | Tread20cm | Tread27cm | Tread33cm |
| --- | --- | --- | --- |
| 18 cm | 96/96 PASS | 96/96 PASS | 96/96 PASS |
| 20 cm | 96/96 PASS | 96/96 PASS | 96/96 PASS |
| 23 cm | 96/96 PASS | 96/96 PASS | 96/96 PASS |

### 0.3 m/s desc

| Rise | Tread20cm | Tread27cm | Tread33cm |
| --- | --- | --- | --- |
| 18 cm | 96/96 PASS | 96/96 PASS | 96/96 PASS |
| 20 cm | 93/96 FAIL | 96/96 PASS | 96/96 PASS |
| 23 cm | 48/96 FAIL | 81/96 FAIL | 90/96 FAIL |

### 0.5 m/s asc

| Rise | Tread20cm | Tread27cm | Tread33cm |
| --- | --- | --- | --- |
| 18 cm | 96/96 PASS | 96/96 PASS | 96/96 PASS |
| 20 cm | 96/96 PASS | 96/96 PASS | 96/96 PASS |
| 23 cm | 96/96 PASS | 96/96 PASS | 96/96 PASS |

### 0.5 m/s desc

| Rise | Tread20cm | Tread27cm | Tread33cm |
| --- | --- | --- | --- |
| 18 cm | 96/96 PASS | 96/96 PASS | 96/96 PASS |
| 20 cm | 96/96 PASS | 96/96 PASS | 96/96 PASS |
| 23 cm | 95/96 PASS | 94/96 PASS | 96/96 PASS |

## Saved matching evidence

| Pair | Geometry | Root positions | Aggregate pose | Thresholds | Contact metadata | Heading | Foot material | Saved physical readbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| height_depth_probe_03 → height_depth_probe_05 | True | True | True | True | True | True | True | True |

This adaptively selected boundary map covers18fixed6-step cases:18/20/23 cm rise×20/27/33 cm tread×up/down,no nosing,at 0.3/0.5 m/s,seeds 601/607/613. New reset seeds and individual local passes do not replace the independent final matrix or certify a safe operating envelope.

## Limits

- These are separately prescribed diagnostics after final failures were observed. They do not alter the original frozen protocol outcome, primary/secondary selection, reward, checkpoints or training; no retuning follows the observations.
- Original95% case/reset seed completion,<=5% each fall/stall/escape and zero history base contact gates remain. A passing gate can contain one failure among32; complete zero failure traversal is reported separately.
- Only the saved prescribed domain/profile is tested with the external heading controller. These simulation results establish no real-robot robustness or full dynamics calibration.
- Motion metrics use first episodes before autoreset, excluding the first second and averaging seed-level case aggregates equally. Failed/truncated trajectories remain; their lower action/contact/jerk values cannot prove smoother competent traversal.
- Recorded per-env root positions and aggregate initial pose match where declared, but full per-env initial orientation/state is not saved. Sensor/force/slip proxies and sparse0.1s trace limits match the main report; continuous video remains separate.
- The18 geometries cover height18/20/23 cm ×depth20/27/33 cm ×up/down at.3/.5m/s. They were selected after observed final failures; fresh reset seeds 601/607/613 do not make this adaptive diagnostic an independent final acceptance.
- The map reports completion and every original case/seed gate,not a safe operating envelope. Local passes and plausible rise/tread trends do not change the original final FAIL or certify unseen physical stairs.
