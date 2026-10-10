# Frozen combined dynamics at 0.5 m/s

Status: complete. These are separate diagnostics with the frozen primary control660,zero gradient updates and unchanged original case/seed gates. They do not replace the original final matrix or select a new checkpoint.

| Evaluation | Speed(m/s) | Completed | Worst case/seed | Fall/stall/escape flags | History base | Original whole-matrix gate | Maxpause(s) |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: |
| dynamics_seed71_primary_speed0.5 | 0.5 | 1501/1536 | 23/32 | 8/2/26 | 4 | FAIL | 3.50 |
| dynamics_seed73_primary_speed0.5 | 0.5 | 1486/1536 | 21/32 | 14/8/28 | 6 | FAIL | 3.94 |
| dynamics_seed79_primary_speed0.5 | 0.5 | 1492/1536 | 23/32 | 18/7/19 | 9 | FAIL | 3.78 |

These combined-dynamics trials keep their own collection status and case gates. Any successes here do not change the original0.3m/s dynamics failures or the original frozen protocol scientific acceptance. Initial/final gain summaries may include automatic resets and are not per-first episode gain snapshots.

Failure flags are nonexclusive. JSON/CSV retain unique noncompletions, all anomalies, zero-action controls, each case/seed gate and exposure. Command exit0 means saved collection,not scientific acceptance.

| Evaluation | Case | Completed by reset seed | Counts fall/stall/escape/base | Original all-seed gate | Full zero failure traversal |
| --- | --- | --- | --- | --- | --- |
| dynamics_seed71_primary_speed0.5 | asc_paper_A1_16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed71_primary_speed0.5 | desc_paper_A1_16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed71_primary_speed0.5 | asc_paper_Aliengo_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed71_primary_speed0.5 | desc_paper_Aliengo_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed71_primary_speed0.5 | asc_unseen_11cm_33cm | 32/30/32 | 1/0/2/1 | FAIL | False |
| dynamics_seed71_primary_speed0.5 | desc_unseen_11cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed71_primary_speed0.5 | asc_unseen_165mm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed71_primary_speed0.5 | desc_unseen_165mm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed71_primary_speed0.5 | asc_unseen_lip15mm_17cm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed71_primary_speed0.5 | desc_unseen_lip15mm_17cm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed71_primary_speed0.5 | asc_unseen_lip25mm_16cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed71_primary_speed0.5 | desc_unseen_lip25mm_16cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed71_primary_speed0.5 | asc_long12_17cm_25cm | 32/32/31 | 0/0/1/0 | PASS | False |
| dynamics_seed71_primary_speed0.5 | desc_long12_17cm_25cm | 23/27/25 | 0/0/21/0 | FAIL | False |
| dynamics_seed71_primary_speed0.5 | asc_stretch23cm_20cm | 32/30/31 | 1/0/2/1 | FAIL | False |
| dynamics_seed71_primary_speed0.5 | desc_stretch23cm_20cm | 30/30/28 | 6/2/0/2 | FAIL | False |
| dynamics_seed73_primary_speed0.5 | asc_paper_A1_16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed73_primary_speed0.5 | desc_paper_A1_16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed73_primary_speed0.5 | asc_paper_Aliengo_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed73_primary_speed0.5 | desc_paper_Aliengo_17cm_25cm | 32/31/32 | 1/0/0/0 | PASS | False |
| dynamics_seed73_primary_speed0.5 | asc_unseen_11cm_33cm | 32/31/31 | 1/1/0/1 | FAIL | False |
| dynamics_seed73_primary_speed0.5 | desc_unseen_11cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed73_primary_speed0.5 | asc_unseen_165mm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed73_primary_speed0.5 | desc_unseen_165mm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed73_primary_speed0.5 | asc_unseen_lip15mm_17cm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed73_primary_speed0.5 | desc_unseen_lip15mm_17cm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed73_primary_speed0.5 | asc_unseen_lip25mm_16cm_33cm | 31/32/31 | 2/0/0/2 | FAIL | False |
| dynamics_seed73_primary_speed0.5 | desc_unseen_lip25mm_16cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed73_primary_speed0.5 | asc_long12_17cm_25cm | 32/31/31 | 1/1/0/1 | FAIL | False |
| dynamics_seed73_primary_speed0.5 | desc_long12_17cm_25cm | 25/23/21 | 0/0/27/0 | FAIL | False |
| dynamics_seed73_primary_speed0.5 | asc_stretch23cm_20cm | 31/29/29 | 1/5/1/0 | FAIL | False |
| dynamics_seed73_primary_speed0.5 | desc_stretch23cm_20cm | 26/30/31 | 8/1/0/2 | FAIL | False |
| dynamics_seed79_primary_speed0.5 | asc_paper_A1_16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed79_primary_speed0.5 | desc_paper_A1_16cm_27cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed79_primary_speed0.5 | asc_paper_Aliengo_17cm_25cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed79_primary_speed0.5 | desc_paper_Aliengo_17cm_25cm | 32/32/31 | 1/0/0/0 | PASS | False |
| dynamics_seed79_primary_speed0.5 | asc_unseen_11cm_33cm | 32/31/30 | 2/0/1/2 | FAIL | False |
| dynamics_seed79_primary_speed0.5 | desc_unseen_11cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed79_primary_speed0.5 | asc_unseen_165mm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed79_primary_speed0.5 | desc_unseen_165mm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed79_primary_speed0.5 | asc_unseen_lip15mm_17cm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed79_primary_speed0.5 | desc_unseen_lip15mm_17cm_29cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed79_primary_speed0.5 | asc_unseen_lip25mm_16cm_33cm | 32/32/32 | 0/0/0/0 | PASS | True |
| dynamics_seed79_primary_speed0.5 | desc_unseen_lip25mm_16cm_33cm | 31/32/32 | 0/0/1/0 | PASS | False |
| dynamics_seed79_primary_speed0.5 | asc_long12_17cm_25cm | 32/32/31 | 0/0/1/0 | PASS | False |
| dynamics_seed79_primary_speed0.5 | desc_long12_17cm_25cm | 27/28/25 | 1/0/15/1 | FAIL | False |
| dynamics_seed79_primary_speed0.5 | asc_stretch23cm_20cm | 32/31/29 | 0/4/0/0 | FAIL | False |
| dynamics_seed79_primary_speed0.5 | desc_stretch23cm_20cm | 27/23/28 | 14/3/1/6 | FAIL | False |

## Saved matching evidence

| Pair | Geometry | Root positions | Aggregate pose | Thresholds | Contact metadata | Heading | Foot material | Saved physical readbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

Three new construction seeds 71/73/79 redraw startup mass/COM. Footfriction stays0.8/0.6 and terrain-authored1/1multiply. PD gains resample from nominal defaults at resets. Actual massratio,COM offset,Kp/Kdscale and inertia-scaling checks are preserved for initial/final readbacks; they do not establish exact per-env episode gain maps.

## Limits

- These are separately prescribed diagnostics after final failures were observed. They do not alter the original frozen protocol outcome, primary/secondary selection, reward, checkpoints or training; no retuning follows the observations.
- Original95% case/reset seed completion,<=5% each fall/stall/escape and zero history base contact gates remain. A passing gate can contain one failure among32; complete zero failure traversal is reported separately.
- Only the saved prescribed domain/profile is tested with the external heading controller. These simulation results establish no real-robot robustness or full dynamics calibration.
- Motion metrics use first episodes before autoreset, excluding the first second and averaging seed-level case aggregates equally. Failed/truncated trajectories remain; their lower action/contact/jerk values cannot prove smoother competent traversal.
- Recorded per-env root positions and aggregate initial pose match where declared, but full per-env initial orientation/state is not saved. Sensor/force/slip proxies and sparse0.1s trace limits match the main report; continuous video remains separate.
- This is the distinct0.5m/s combined dynamics supplement,with startup mass scale.8–1.25,COM offsetxyz±.03/.02/.01m,and resetPD scale.9–1.1 at fixed nominalfoot friction. Mass/COM remain fixed across reset seeds and PD may change with autoresets.
- Combined mass/COM/PD variability does not isolate a single causal parameter. Initial/final physical readbacks verify distributions and inertia scaling,but do not store exact first episode per-env gain assignments.
- The original0.3m/s final dynamics tests remain separate; adding the0.5m/s supplement does not change the original frozen protocol status or imply passage at either speed. No calibrated actuator delay,strength,thermal or battery sensitivity is covered.
