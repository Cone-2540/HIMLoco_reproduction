# Frozen policy dependence on external heading commands

On the12 standard cases at 0.3 m/s, the frozen primary completes1152/1152 with external heading feedback but1050/1152 with zero yaw rate commands. The latter has95 lateral escapes,7 fall flags and2 history-base-contact environments. The normal mode passes every original case/reset seed gate; the zero-yaw stress fails. This is a measured dependency under the tested conditions.

Normal heading feedback requests yaw rate=clamp(-yaw,−0.5,+0.5)rad/s toward yaw0,with gain1 and no lateral position correction. The stress requests zero yaw rate through the same ordinary command channel. The actor continues to receive proprioceptive feedback in both modes. Full per-env initial orientation/state is not saved; saved initial root positions and aggregate pose distributions match exactly.

| Mode | Completed | Fall/stall/escape | History base | Heading absolute error (rad) | Lateral absolute error (m) | XY tracking RMSE (m/s) | Gate |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| standard_heading-control_primary_speed0.3 | 1152/1152 | 0/0/0 | 0 | 0.008683 | 0.069265 | 0.052442 | PASS |
| standard_zero-yaw_primary_speed0.3 | 1050/1152 | 7/0/95 | 2 | 0.064996 | 0.107709 | 0.053996 | FAIL |

Means average seed-level case aggregates equally; they are not pooled RMS statistics. Flags are nonexclusive; unique noncompletions are preserved separately. Lower force/action values on failed shorter trajectories do not show better competent motion.

| Standard case | Normal completed by seed401/409/419 | Zero-yaw completed by seed401/409/419 | Normal all-seed gate | Zero-yaw all-seed gate |
| --- | --- | --- | --- | --- |
| asc_easy8cm_30cm | 32/32/32 | 31/28/27 | True | False |
| desc_easy8cm_30cm | 32/32/32 | 32/32/32 | True | True |
| asc_standard12cm_30cm | 32/32/32 | 32/32/32 | True | True |
| desc_standard12cm_30cm | 32/32/32 | 30/26/29 | True | False |
| asc_standard14cm_27cm | 32/32/32 | 32/32/32 | True | True |
| desc_standard14cm_27cm | 32/32/32 | 31/28/28 | True | False |
| asc_target16cm_27cm | 32/32/32 | 32/32/32 | True | True |
| desc_target16cm_27cm | 32/32/32 | 32/32/32 | True | True |
| asc_standard17cm_25cm | 32/32/32 | 32/32/32 | True | True |
| desc_standard17cm_25cm | 32/32/32 | 31/31/32 | True | True |
| asc_standard17cm_40cm | 32/32/32 | 29/31/26 | True | False |
| desc_standard17cm_40cm | 32/32/32 | 15/11/10 | True | False |

The zero-yaw result limits any claim that the actor alone maintains the requested global stairheading. It does not invalidate the explicitly configured heading-feedback result; it documents the condition under which that result was achieved. No thresholds, primary checkpoint or training settings change after these observations.

Source paths,original gates,physical readbacks,case/reset seed metrics,failed endpoints and deliberate protocol difference are preserved in lossless JSONgzip. CSV uses the same columns as the main frozen report. Sparse traces and numeric pause flags do not certify continuous smoothness.
