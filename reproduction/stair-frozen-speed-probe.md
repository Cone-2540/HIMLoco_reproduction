# Frozen speed probe

Status: complete. These are separate diagnostics with the frozen primary control660,zero gradient updates and unchanged original case/seed gates. They do not replace the original final matrix or select a new checkpoint.

| Evaluation | Speed(m/s) | Completed | Worst case/seed | Fall/stall/escape flags | History base | Original whole-matrix gate | Maxpause(s) |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: |
| speed_probe_02 | 0.2 | 512/576 | 12/32 | 28/36/0 | 17 | FAIL | 3.96 |
| speed_probe_03 | 0.3 | 529/576 | 16/32 | 40/7/0 | 39 | FAIL | 3.58 |
| speed_probe_04 | 0.4 | 564/576 | 28/32 | 7/1/4 | 7 | FAIL | 3.60 |
| speed_probe_05 | 0.5 | 555/576 | 24/32 | 0/1/20 | 0 | FAIL | 3.72 |
| speed_probe_06 | 0.6 | 570/576 | 30/32 | 1/0/5 | 0 | FAIL | 0.62 |

Every prescribed speed fails at least one original case/reset seed gate. At0.6m/s the stretch descent is complete,but the12-step descent still has5lateral escapes across the three seeds; the matrix remains FAIL. New seeds on an adaptive subset do not define a validated speed range.

Failure flags are nonexclusive. JSON/CSV retain unique noncompletions, all anomalies, zero-action controls, each case/seed gate and exposure. Command exit0 means saved collection,not scientific acceptance.

| Evaluation | Case | Completed by reset seed | Counts fall/stall/escape/base | Original all-seed gate | Full zero failure traversal |
| --- | --- | --- | --- | --- | --- |
| speed_probe_02 | asc_core16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_02 | desc_core16cm_27cm | 32/31/31 | 0/2/0/0 | PASS | False |
| speed_probe_02 | asc_long12_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_02 | desc_long12_17cm_25cm | 29/31/31 | 0/5/0/0 | FAIL | False |
| speed_probe_02 | asc_stretch23cm_20cm | 32/31/32 | 0/1/0/0 | PASS | False |
| speed_probe_02 | desc_stretch23cm_20cm | 12/12/16 | 28/28/0/17 | FAIL | False |
| speed_probe_03 | asc_core16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_03 | desc_core16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_03 | asc_long12_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_03 | desc_long12_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_03 | asc_stretch23cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_03 | desc_stretch23cm_20cm | 16/17/16 | 40/7/0/39 | FAIL | False |
| speed_probe_04 | asc_core16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_04 | desc_core16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_04 | asc_long12_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_04 | desc_long12_17cm_25cm | 32/29/31 | 0/0/4/0 | FAIL | False |
| speed_probe_04 | asc_stretch23cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_04 | desc_stretch23cm_20cm | 28/30/30 | 7/1/0/7 | FAIL | False |
| speed_probe_05 | asc_core16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_05 | desc_core16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_05 | asc_long12_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_05 | desc_long12_17cm_25cm | 28/24/24 | 0/0/20/0 | FAIL | False |
| speed_probe_05 | asc_stretch23cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_05 | desc_stretch23cm_20cm | 32/32/31 | 0/1/0/0 | PASS | False |
| speed_probe_06 | asc_core16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_06 | desc_core16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_06 | asc_long12_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| speed_probe_06 | desc_long12_17cm_25cm | 30/31/30 | 0/0/5/0 | FAIL | False |
| speed_probe_06 | asc_stretch23cm_20cm | 32/32/31 | 1/0/0/0 | PASS | False |
| speed_probe_06 | desc_stretch23cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |

## Saved matching evidence

| Pair | Geometry | Root positions | Aggregate pose | Thresholds | Contact metadata | Heading | Foot material | Saved physical readbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| speed_probe_02 → speed_probe_03 | True | True | True | True | True | True | True | True |
| speed_probe_03 → speed_probe_04 | True | True | True | True | True | True | True | True |
| speed_probe_04 → speed_probe_05 | True | True | True | True | True | True | True | True |
| speed_probe_05 → speed_probe_06 | True | True | True | True | True | True | True | True |

The six-case subset contains16cm/27 cm up/down,12-step17cm/25 cm up/down and23cm/20 cm stretch up/down. Resetseeds503/509/521 are new,but the subset was chosen after known final failures. This diagnostic does not certify a safe operating envelope or provide a new independent final acceptance.

## Preserved collection failure and retry

The first0.6m/s collection failed to allocate GPUmemory and saved no result. Its configuration directory and stdout SHA-256 are retained in JSON. The run owner verified and stopped completed task-owned orphan simulation processes,without driver changes or container reset; the unchanged protocol retry saved a complete result. The OOM is a collection failure,not a completed policy gate outcome.

Cleanup record: `reproduction/overnight-owned-process-cleanup.json`. The first failed collection remains in `collection_attempts` alongside the selected complete retry.

## Limits

- These are separately prescribed diagnostics after final failures were observed. They do not alter the original frozen protocol outcome, primary/secondary selection, reward, checkpoints or training; no retuning follows the observations.
- Original95% case/reset seed completion,<=5% each fall/stall/escape and zero history base contact gates remain. A passing gate can contain one failure among32; complete zero failure traversal is reported separately.
- Only the saved prescribed domain/profile is tested with the external heading controller. These simulation results establish no real-robot robustness or full dynamics calibration.
- Motion metrics use first episodes before autoreset, excluding the first second and averaging seed-level case aggregates equally. Failed/truncated trajectories remain; their lower action/contact/jerk values cannot prove smoother competent traversal.
- Recorded per-env root positions and aggregate initial pose match where declared, but full per-env initial orientation/state is not saved. Sensor/force/slip proxies and sparse0.1s trace limits match the main report; continuous video remains separate.
- The six geometries were chosen to diagnose known failure modes. New reset seeds 503/509/521 do not turn this adaptive subset into a fresh independent final test or certify an operating envelope. A passing individual speed cannot overwrite the original final FAIL.
- Changing speed changes trajectory duration, contact timing and heading-command responses. No monotonic speed relation or universally optimal speed is inferred.
