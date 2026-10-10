# Frozen legacy calf-envelope sensitivity

Status: complete. These are separate diagnostics with the frozen primary control660,zero gradient updates and unchanged original case/seed gates. They do not replace the original final matrix or select a new checkpoint.

| Evaluation | Speed(m/s) | Completed | Worst case/seed | Fall/stall/escape flags | History base | Original whole-matrix gate | Maxpause(s) |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: |
| nominal_primary_speed0.3 | 0.3 | 1494/1536 | 12/32 | 34/8/0 | 33 | FAIL | 3.64 |
| legacy_calf_primary_speed0.3 | 0.3 | 1490/1536 | 15/32 | 36/9/1 | 36 | FAIL | 3.62 |
| nominal_primary_speed0.5 | 0.5 | 1511/1536 | 21/32 | 3/0/22 | 3 | FAIL | 0.32 |
| legacy_calf_primary_speed0.5 | 0.5 | 1507/1536 | 22/32 | 2/0/27 | 0 | FAIL | 0.34 |

Failure flags are nonexclusive. JSON/CSV retain unique noncompletions, all anomalies, zero-action controls, each case/seed gate and exposure. Command exit0 means saved collection,not scientific acceptance.

| Evaluation | Case | Completed by reset seed | Counts fall/stall/escape/base | Original all-seed gate | Full zero failure traversal |
| --- | --- | --- | --- | --- | --- |
| nominal_primary_speed0.3 | asc_paper_A1_16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | desc_paper_A1_16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | asc_paper_Aliengo_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | desc_paper_Aliengo_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | asc_unseen_11cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | desc_unseen_11cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | asc_unseen_165mm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | desc_unseen_165mm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | asc_unseen_lip15mm_17cm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | desc_unseen_lip15mm_17cm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | asc_unseen_lip25mm_16cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | desc_unseen_lip25mm_16cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | asc_long12_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | desc_long12_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | asc_stretch23cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.3 | desc_stretch23cm_20cm | 12/25/17 | 34/8/0/33 | FAIL | False |
| legacy_calf_primary_speed0.3 | asc_paper_A1_16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | desc_paper_A1_16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | asc_paper_Aliengo_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | desc_paper_Aliengo_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | asc_unseen_11cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | desc_unseen_11cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | asc_unseen_165mm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | desc_unseen_165mm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | asc_unseen_lip15mm_17cm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | desc_unseen_lip15mm_17cm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | asc_unseen_lip25mm_16cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | desc_unseen_lip25mm_16cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | asc_long12_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | desc_long12_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | asc_stretch23cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.3 | desc_stretch23cm_20cm | 15/16/19 | 36/9/1/36 | FAIL | False |
| nominal_primary_speed0.5 | asc_paper_A1_16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.5 | desc_paper_A1_16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.5 | asc_paper_Aliengo_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.5 | desc_paper_Aliengo_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.5 | asc_unseen_11cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.5 | desc_unseen_11cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.5 | asc_unseen_165mm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.5 | desc_unseen_165mm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.5 | asc_unseen_lip15mm_17cm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.5 | desc_unseen_lip15mm_17cm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.5 | asc_unseen_lip25mm_16cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.5 | desc_unseen_lip25mm_16cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.5 | asc_long12_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.5 | desc_long12_17cm_25cm | 27/21/25 | 1/0/22/1 | FAIL | False |
| nominal_primary_speed0.5 | asc_stretch23cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| nominal_primary_speed0.5 | desc_stretch23cm_20cm | 32/32/30 | 2/0/0/2 | FAIL | False |
| legacy_calf_primary_speed0.5 | asc_paper_A1_16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.5 | desc_paper_A1_16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.5 | asc_paper_Aliengo_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.5 | desc_paper_Aliengo_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.5 | asc_unseen_11cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.5 | desc_unseen_11cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.5 | asc_unseen_165mm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.5 | desc_unseen_165mm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.5 | asc_unseen_lip15mm_17cm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.5 | desc_unseen_lip15mm_17cm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.5 | asc_unseen_lip25mm_16cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.5 | desc_unseen_lip25mm_16cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.5 | asc_long12_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.5 | desc_long12_17cm_25cm | 24/22/23 | 0/0/27/0 | FAIL | False |
| legacy_calf_primary_speed0.5 | asc_stretch23cm_20cm | 32/32/32 | 0/0/0/0 | PASS | True |
| legacy_calf_primary_speed0.5 | desc_stretch23cm_20cm | 30/32/32 | 2/0/0/0 | FAIL | False |

## Saved matching evidence

| Pair | Geometry | Root positions | Aggregate pose | Thresholds | Contact metadata | Heading | Foot material | Saved physical readbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nominal_primary_speed0.3 → legacy_calf_primary_speed0.3 | True | True | True | True | True | True | True | True |
| nominal_primary_speed0.5 → legacy_calf_primary_speed0.5 | True | True | True | True | True | True | True | True |

The curve configuration changes calf torque45.43→35.55 Nm and velocitylimit15.70→20.07 rad/s,including saturation and joint limits. Hip/thigh settings and PD are preserved. This changes the existing torque-speed curve rather than applying a globally smaller torque bound. Configuration manifests came from the actual helper call before construction; physical readbacks do not contain torque-speed/joint-limit fields. These are uncalibrated model choices for Go2 EDU,not hardware measurements.

## Limits

- These are separately prescribed diagnostics after final failures were observed. They do not alter the original frozen protocol outcome, primary/secondary selection, reward, checkpoints or training; no retuning follows the observations.
- Original95% case/reset seed completion,<=5% each fall/stall/escape and zero history base contact gates remain. A passing gate can contain one failure among32; complete zero failure traversal is reported separately.
- Only the saved prescribed domain/profile is tested with the external heading controller. These simulation results establish no real-robot robustness or full dynamics calibration.
- Motion metrics use first episodes before autoreset, excluding the first second and averaging seed-level case aggregates equally. Failed/truncated trajectories remain; their lower action/contact/jerk values cannot prove smoother competent traversal.
- Recorded per-env root positions and aggregate initial pose match where declared, but full per-env initial orientation/state is not saved. Sensor/force/slip proxies and sparse0.1s trace limits match the main report; continuous video remains separate.
- The legacy curve changes calf peak/saturation torque45.43→35.55 Nm and calf motor/joint speedlimit15.70→20.07 rad/s,while preserving the existing DCMotor shape,hip/thigh settings,morphology and PD gains. It is not globally a lower envelope at every speed.
- Neither curve is measured on the user’s Go2 EDU. The saved configuration helper/manifest confirms configuration application; physical readbacks omit torque-speed and joint-limit fields,so backend envelope measurement is unavailable.
- The torque×speed products are configuration-derived approximations,not measured instantaneous motor power. No delay,thermal derating,battery-state or calibrated motor-strength sensitivity is covered.
