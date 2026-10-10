# Frozen independent staircase validation

Collection status: complete. Scientific acceptance: FAIL. Primary control660 and nominal-only secondary slide680 were frozen at 2026-10-11T05:47:03.427901+08:00 before independent final outcomes. The selection stays fixed; these results trigger no retuning. Freeze checks: 33/33 verified; pending evaluations: 0. GPU/driver operations are outside this CPU report.

The whole 16-case matrix retains the original gate: every case and reset seed must complete at least 95%, with each fall/stall/escape fraction at most 5% and zero history-base contact. At32 envs,31/32 passes completion and30/32 fails. The4 paper-corresponding,8 unseen,2 long and2 stretch groups provide detail; a failing stretch still fails the entire matrix.

| Evaluation | Completed | Worst case/seed | Fall/stall/escape flags | Base history/current | Whole-matrix gate | Maxpause(s) |
| --- | ---: | ---: | --- | --- | --- | ---: |
| nominal_primary_speed0.3 | 1494/1536 | 12/32 | 34/8/0 | 33/32 | FAIL | 3.64 |
| nominal_secondary_speed0.3 | 1485/1536 | 20/32 | 10/10/31 | 7/7 | FAIL | 3.64 |
| nominal_primary_speed0.5 | 1511/1536 | 21/32 | 3/0/22 | 3/0 | FAIL | 0.32 |
| nominal_secondary_speed0.5 | 1466/1536 | 5/32 | 0/0/70 | 0/0 | FAIL | 0.22 |
| foot_nominal_primary_speed0.3 | 1498/1536 | 16/32 | 31/7/0 | 26/21 | FAIL | 3.68 |
| foot_low_primary_speed0.3 | 1532/1536 | 30/32 | 4/0/0 | 1/0 | FAIL | 0.48 |
| foot_high_primary_speed0.3 | 1410/1536 | 2/32 | 42/84/0 | 40/38 | FAIL | 3.90 |
| standard_heading-control_primary_speed0.3 | 1152/1152 | 32/32 | 0/0/0 | 0/0 | PASS | 0.38 |
| standard_zero-yaw_primary_speed0.3 | 1050/1152 | 10/32 | 7/0/95 | 2/1 | FAIL | 1.18 |
| dynamics_seed71_primary_speed0.3 | 1420/1536 | 19/32 | 45/42/30 | 36/30 | FAIL | 3.90 |
| dynamics_seed73_primary_speed0.3 | 1405/1536 | 13/32 | 55/51/26 | 42/34 | FAIL | 3.92 |
| dynamics_seed79_primary_speed0.3 | 1429/1536 | 15/32 | 54/29/25 | 44/38 | FAIL | 3.88 |

Primary control660 passes all paper-corresponding and unseen geometry case/seeds at both speeds. At 0.3 m/s it also passes both long cases; the stretch descent fails. At 0.5 m/s the long descent and one stretch-descent reset seed fail. Therefore its whole nominal matrix fails at both speeds. Secondary slide680 fails long descent at both speeds and stretch descent at 0.3 m/s; its reduced slip proxy does not preserve all traversal outcomes. The primary stays fixed.

Flags are nonexclusive; unique noncompletions equal total minus completed. JSON retains every failed endpoint, anomaly count, zero-action control and first episode exposure; CSV contains one row per case/reset seed. Smoothness remains separate from traversal.

## Final geometry strata

| Evaluation | Group | Completed | Passed case/seeds | Gate |
| --- | --- | ---: | ---: | --- |
| nominal_primary_speed0.3 | paper_corresponding_4 | 384/384 | 12/12 | PASS |
| nominal_primary_speed0.3 | unseen_geometry_8 | 768/768 | 24/24 | PASS |
| nominal_primary_speed0.3 | long_12_step_2 | 192/192 | 6/6 | PASS |
| nominal_primary_speed0.3 | stretch_23cm_2 | 150/192 | 3/6 | FAIL |
| nominal_secondary_speed0.3 | paper_corresponding_4 | 384/384 | 12/12 | PASS |
| nominal_secondary_speed0.3 | unseen_geometry_8 | 768/768 | 24/24 | PASS |
| nominal_secondary_speed0.3 | long_12_step_2 | 161/192 | 3/6 | FAIL |
| nominal_secondary_speed0.3 | stretch_23cm_2 | 172/192 | 3/6 | FAIL |
| nominal_primary_speed0.5 | paper_corresponding_4 | 384/384 | 12/12 | PASS |
| nominal_primary_speed0.5 | unseen_geometry_8 | 768/768 | 24/24 | PASS |
| nominal_primary_speed0.5 | long_12_step_2 | 169/192 | 3/6 | FAIL |
| nominal_primary_speed0.5 | stretch_23cm_2 | 190/192 | 5/6 | FAIL |
| nominal_secondary_speed0.5 | paper_corresponding_4 | 384/384 | 12/12 | PASS |
| nominal_secondary_speed0.5 | unseen_geometry_8 | 768/768 | 24/24 | PASS |
| nominal_secondary_speed0.5 | long_12_step_2 | 122/192 | 3/6 | FAIL |
| nominal_secondary_speed0.5 | stretch_23cm_2 | 192/192 | 6/6 | PASS |
| foot_nominal_primary_speed0.3 | paper_corresponding_4 | 384/384 | 12/12 | PASS |
| foot_nominal_primary_speed0.3 | unseen_geometry_8 | 768/768 | 24/24 | PASS |
| foot_nominal_primary_speed0.3 | long_12_step_2 | 192/192 | 6/6 | PASS |
| foot_nominal_primary_speed0.3 | stretch_23cm_2 | 154/192 | 3/6 | FAIL |
| foot_low_primary_speed0.3 | paper_corresponding_4 | 384/384 | 12/12 | PASS |
| foot_low_primary_speed0.3 | unseen_geometry_8 | 768/768 | 24/24 | PASS |
| foot_low_primary_speed0.3 | long_12_step_2 | 192/192 | 6/6 | PASS |
| foot_low_primary_speed0.3 | stretch_23cm_2 | 188/192 | 5/6 | FAIL |
| foot_high_primary_speed0.3 | paper_corresponding_4 | 384/384 | 12/12 | PASS |
| foot_high_primary_speed0.3 | unseen_geometry_8 | 761/768 | 21/24 | FAIL |
| foot_high_primary_speed0.3 | long_12_step_2 | 192/192 | 6/6 | PASS |
| foot_high_primary_speed0.3 | stretch_23cm_2 | 73/192 | 0/6 | FAIL |
| dynamics_seed71_primary_speed0.3 | paper_corresponding_4 | 379/384 | 11/12 | FAIL |
| dynamics_seed71_primary_speed0.3 | unseen_geometry_8 | 736/768 | 16/24 | FAIL |
| dynamics_seed71_primary_speed0.3 | long_12_step_2 | 170/192 | 2/6 | FAIL |
| dynamics_seed71_primary_speed0.3 | stretch_23cm_2 | 135/192 | 0/6 | FAIL |
| dynamics_seed73_primary_speed0.3 | paper_corresponding_4 | 379/384 | 10/12 | FAIL |
| dynamics_seed73_primary_speed0.3 | unseen_geometry_8 | 736/768 | 15/24 | FAIL |
| dynamics_seed73_primary_speed0.3 | long_12_step_2 | 176/192 | 2/6 | FAIL |
| dynamics_seed73_primary_speed0.3 | stretch_23cm_2 | 114/192 | 0/6 | FAIL |
| dynamics_seed79_primary_speed0.3 | paper_corresponding_4 | 378/384 | 10/12 | FAIL |
| dynamics_seed79_primary_speed0.3 | unseen_geometry_8 | 743/768 | 15/24 | FAIL |
| dynamics_seed79_primary_speed0.3 | long_12_step_2 | 177/192 | 3/6 | FAIL |
| dynamics_seed79_primary_speed0.3 | stretch_23cm_2 | 131/192 | 0/6 | FAIL |

## Failed case and reset seed gates

| Evaluation | Seed | Case | Completed | Fall/stall/escape | Base | Failed gate terms |
| --- | ---: | --- | ---: | --- | ---: | --- |
| nominal_primary_speed0.3 | 101 | desc_stretch23cm_20cm | 12/32 | 17/3/0 | 16 | completion_fraction, falls, stalls, history_base_contact |
| nominal_primary_speed0.3 | 211 | desc_stretch23cm_20cm | 25/32 | 4/3/0 | 4 | completion_fraction, falls, stalls, history_base_contact |
| nominal_primary_speed0.3 | 307 | desc_stretch23cm_20cm | 17/32 | 13/2/0 | 13 | completion_fraction, falls, stalls, history_base_contact |
| nominal_secondary_speed0.3 | 101 | desc_long12_17cm_25cm | 20/32 | 0/0/12 | 0 | completion_fraction, lateral_escapes |
| nominal_secondary_speed0.3 | 211 | desc_long12_17cm_25cm | 20/32 | 0/0/12 | 0 | completion_fraction, lateral_escapes |
| nominal_secondary_speed0.3 | 307 | desc_long12_17cm_25cm | 25/32 | 0/0/7 | 0 | completion_fraction, lateral_escapes |
| nominal_secondary_speed0.3 | 101 | desc_stretch23cm_20cm | 26/32 | 4/2/0 | 3 | completion_fraction, falls, stalls, history_base_contact |
| nominal_secondary_speed0.3 | 211 | desc_stretch23cm_20cm | 25/32 | 4/3/0 | 3 | completion_fraction, falls, stalls, history_base_contact |
| nominal_secondary_speed0.3 | 307 | desc_stretch23cm_20cm | 25/32 | 2/5/0 | 1 | completion_fraction, falls, stalls, history_base_contact |
| nominal_primary_speed0.5 | 101 | desc_long12_17cm_25cm | 27/32 | 0/0/5 | 0 | completion_fraction, lateral_escapes |
| nominal_primary_speed0.5 | 211 | desc_long12_17cm_25cm | 21/32 | 1/0/10 | 1 | completion_fraction, lateral_escapes, history_base_contact |
| nominal_primary_speed0.5 | 307 | desc_long12_17cm_25cm | 25/32 | 0/0/7 | 0 | completion_fraction, lateral_escapes |
| nominal_primary_speed0.5 | 307 | desc_stretch23cm_20cm | 30/32 | 2/0/0 | 2 | completion_fraction, falls, history_base_contact |
| nominal_secondary_speed0.5 | 101 | desc_long12_17cm_25cm | 11/32 | 0/0/21 | 0 | completion_fraction, lateral_escapes |
| nominal_secondary_speed0.5 | 211 | desc_long12_17cm_25cm | 5/32 | 0/0/27 | 0 | completion_fraction, lateral_escapes |
| nominal_secondary_speed0.5 | 307 | desc_long12_17cm_25cm | 10/32 | 0/0/22 | 0 | completion_fraction, lateral_escapes |
| foot_nominal_primary_speed0.3 | 101 | desc_stretch23cm_20cm | 16/32 | 13/3/0 | 10 | completion_fraction, falls, stalls, history_base_contact |
| foot_nominal_primary_speed0.3 | 211 | desc_stretch23cm_20cm | 23/32 | 8/1/0 | 7 | completion_fraction, falls, history_base_contact |
| foot_nominal_primary_speed0.3 | 307 | desc_stretch23cm_20cm | 19/32 | 10/3/0 | 9 | completion_fraction, falls, stalls, history_base_contact |
| foot_low_primary_speed0.3 | 101 | desc_stretch23cm_20cm | 30/32 | 2/0/0 | 1 | completion_fraction, falls, history_base_contact |
| foot_high_primary_speed0.3 | 101 | asc_unseen_lip25mm_16cm_33cm | 29/32 | 0/3/0 | 0 | completion_fraction, stalls |
| foot_high_primary_speed0.3 | 211 | asc_unseen_lip25mm_16cm_33cm | 30/32 | 0/2/0 | 0 | completion_fraction, stalls |
| foot_high_primary_speed0.3 | 307 | asc_unseen_lip25mm_16cm_33cm | 30/32 | 0/2/0 | 0 | completion_fraction, stalls |
| foot_high_primary_speed0.3 | 101 | asc_stretch23cm_20cm | 21/32 | 0/11/0 | 0 | completion_fraction, stalls |
| foot_high_primary_speed0.3 | 211 | asc_stretch23cm_20cm | 22/32 | 0/10/0 | 0 | completion_fraction, stalls |
| foot_high_primary_speed0.3 | 307 | asc_stretch23cm_20cm | 19/32 | 0/13/0 | 0 | completion_fraction, stalls |
| foot_high_primary_speed0.3 | 101 | desc_stretch23cm_20cm | 2/32 | 18/12/0 | 17 | completion_fraction, falls, stalls, history_base_contact |
| foot_high_primary_speed0.3 | 211 | desc_stretch23cm_20cm | 6/32 | 6/20/0 | 5 | completion_fraction, falls, stalls, history_base_contact |
| foot_high_primary_speed0.3 | 307 | desc_stretch23cm_20cm | 3/32 | 18/11/0 | 18 | completion_fraction, falls, stalls, history_base_contact |
| standard_zero-yaw_primary_speed0.3 | 409 | asc_easy8cm_30cm | 28/32 | 0/0/4 | 0 | completion_fraction, lateral_escapes |
| standard_zero-yaw_primary_speed0.3 | 419 | asc_easy8cm_30cm | 27/32 | 2/0/3 | 0 | completion_fraction, falls, lateral_escapes |
| standard_zero-yaw_primary_speed0.3 | 401 | desc_standard12cm_30cm | 30/32 | 0/0/2 | 0 | completion_fraction, lateral_escapes |
| standard_zero-yaw_primary_speed0.3 | 409 | desc_standard12cm_30cm | 26/32 | 0/0/6 | 0 | completion_fraction, lateral_escapes |
| standard_zero-yaw_primary_speed0.3 | 419 | desc_standard12cm_30cm | 29/32 | 0/0/3 | 0 | completion_fraction, lateral_escapes |
| standard_zero-yaw_primary_speed0.3 | 409 | desc_standard14cm_27cm | 28/32 | 0/0/4 | 0 | completion_fraction, lateral_escapes |
| standard_zero-yaw_primary_speed0.3 | 419 | desc_standard14cm_27cm | 28/32 | 0/0/4 | 0 | completion_fraction, lateral_escapes |
| standard_zero-yaw_primary_speed0.3 | 401 | asc_standard17cm_40cm | 29/32 | 1/0/2 | 0 | completion_fraction, lateral_escapes |
| standard_zero-yaw_primary_speed0.3 | 419 | asc_standard17cm_40cm | 26/32 | 2/0/4 | 1 | completion_fraction, falls, lateral_escapes, history_base_contact |
| standard_zero-yaw_primary_speed0.3 | 401 | desc_standard17cm_40cm | 15/32 | 1/0/16 | 1 | completion_fraction, lateral_escapes, history_base_contact |
| standard_zero-yaw_primary_speed0.3 | 409 | desc_standard17cm_40cm | 11/32 | 0/0/21 | 0 | completion_fraction, lateral_escapes |
| standard_zero-yaw_primary_speed0.3 | 419 | desc_standard17cm_40cm | 10/32 | 0/0/22 | 0 | completion_fraction, lateral_escapes |
| dynamics_seed71_primary_speed0.3 | 101 | asc_paper_Aliengo_17cm_25cm | 30/32 | 2/0/0 | 2 | completion_fraction, falls, history_base_contact |
| dynamics_seed71_primary_speed0.3 | 101 | asc_unseen_11cm_33cm | 29/32 | 1/0/2 | 0 | completion_fraction, lateral_escapes |
| dynamics_seed71_primary_speed0.3 | 211 | asc_unseen_11cm_33cm | 27/32 | 0/1/4 | 0 | completion_fraction, lateral_escapes |
| dynamics_seed71_primary_speed0.3 | 307 | asc_unseen_11cm_33cm | 29/32 | 3/0/0 | 2 | completion_fraction, falls, history_base_contact |
| dynamics_seed71_primary_speed0.3 | 101 | asc_unseen_165mm_29cm | 30/32 | 1/0/1 | 1 | completion_fraction, history_base_contact |
| dynamics_seed71_primary_speed0.3 | 101 | desc_unseen_165mm_29cm | 30/32 | 0/1/1 | 0 | completion_fraction |
| dynamics_seed71_primary_speed0.3 | 101 | asc_unseen_lip25mm_16cm_33cm | 29/32 | 2/0/2 | 2 | completion_fraction, falls, lateral_escapes, history_base_contact |
| dynamics_seed71_primary_speed0.3 | 307 | asc_unseen_lip25mm_16cm_33cm | 28/32 | 0/3/1 | 0 | completion_fraction, stalls |
| dynamics_seed71_primary_speed0.3 | 101 | desc_unseen_lip25mm_16cm_33cm | 30/32 | 0/0/2 | 0 | completion_fraction, lateral_escapes |
| dynamics_seed71_primary_speed0.3 | 101 | asc_long12_17cm_25cm | 26/32 | 5/0/1 | 5 | completion_fraction, falls, history_base_contact |
| dynamics_seed71_primary_speed0.3 | 211 | asc_long12_17cm_25cm | 25/32 | 4/1/2 | 3 | completion_fraction, falls, lateral_escapes, history_base_contact |
| dynamics_seed71_primary_speed0.3 | 307 | asc_long12_17cm_25cm | 28/32 | 1/0/3 | 1 | completion_fraction, lateral_escapes, history_base_contact |
| dynamics_seed71_primary_speed0.3 | 101 | desc_long12_17cm_25cm | 29/32 | 1/0/2 | 1 | completion_fraction, lateral_escapes, history_base_contact |
| dynamics_seed71_primary_speed0.3 | 101 | asc_stretch23cm_20cm | 22/32 | 0/10/0 | 0 | completion_fraction, stalls |
| dynamics_seed71_primary_speed0.3 | 211 | asc_stretch23cm_20cm | 26/32 | 0/5/1 | 0 | completion_fraction, stalls |
| dynamics_seed71_primary_speed0.3 | 307 | asc_stretch23cm_20cm | 25/32 | 0/7/0 | 0 | completion_fraction, stalls |
| dynamics_seed71_primary_speed0.3 | 101 | desc_stretch23cm_20cm | 20/32 | 9/3/0 | 8 | completion_fraction, falls, stalls, history_base_contact |
| dynamics_seed71_primary_speed0.3 | 211 | desc_stretch23cm_20cm | 23/32 | 6/3/0 | 5 | completion_fraction, falls, stalls, history_base_contact |
| dynamics_seed71_primary_speed0.3 | 307 | desc_stretch23cm_20cm | 19/32 | 10/3/0 | 6 | completion_fraction, falls, stalls, history_base_contact |
| dynamics_seed73_primary_speed0.3 | 101 | asc_paper_A1_16cm_27cm | 31/32 | 1/0/0 | 1 | history_base_contact |
| dynamics_seed73_primary_speed0.3 | 101 | asc_paper_Aliengo_17cm_25cm | 30/32 | 1/0/1 | 1 | completion_fraction, history_base_contact |
| dynamics_seed73_primary_speed0.3 | 101 | asc_unseen_11cm_33cm | 28/32 | 3/0/1 | 2 | completion_fraction, falls, history_base_contact |
| dynamics_seed73_primary_speed0.3 | 211 | asc_unseen_11cm_33cm | 24/32 | 4/0/4 | 3 | completion_fraction, falls, lateral_escapes, history_base_contact |
| dynamics_seed73_primary_speed0.3 | 307 | asc_unseen_11cm_33cm | 29/32 | 0/0/3 | 0 | completion_fraction, lateral_escapes |
| dynamics_seed73_primary_speed0.3 | 307 | asc_unseen_165mm_29cm | 31/32 | 1/0/1 | 1 | history_base_contact |
| dynamics_seed73_primary_speed0.3 | 211 | asc_unseen_lip15mm_17cm_29cm | 31/32 | 1/0/0 | 1 | history_base_contact |
| dynamics_seed73_primary_speed0.3 | 101 | asc_unseen_lip25mm_16cm_33cm | 29/32 | 1/1/1 | 1 | completion_fraction, history_base_contact |
| dynamics_seed73_primary_speed0.3 | 211 | asc_unseen_lip25mm_16cm_33cm | 31/32 | 1/0/0 | 1 | history_base_contact |
| dynamics_seed73_primary_speed0.3 | 307 | asc_unseen_lip25mm_16cm_33cm | 29/32 | 1/1/1 | 1 | completion_fraction, history_base_contact |
| dynamics_seed73_primary_speed0.3 | 101 | desc_unseen_lip25mm_16cm_33cm | 29/32 | 0/0/3 | 0 | completion_fraction, lateral_escapes |
| dynamics_seed73_primary_speed0.3 | 101 | asc_long12_17cm_25cm | 26/32 | 5/0/1 | 5 | completion_fraction, falls, history_base_contact |
| dynamics_seed73_primary_speed0.3 | 211 | asc_long12_17cm_25cm | 30/32 | 2/0/0 | 2 | completion_fraction, falls, history_base_contact |
| dynamics_seed73_primary_speed0.3 | 307 | asc_long12_17cm_25cm | 29/32 | 2/1/0 | 2 | completion_fraction, falls, history_base_contact |
| dynamics_seed73_primary_speed0.3 | 307 | desc_long12_17cm_25cm | 29/32 | 0/1/2 | 0 | completion_fraction, lateral_escapes |
| dynamics_seed73_primary_speed0.3 | 101 | asc_stretch23cm_20cm | 18/32 | 0/14/0 | 0 | completion_fraction, stalls |
| dynamics_seed73_primary_speed0.3 | 211 | asc_stretch23cm_20cm | 26/32 | 0/6/0 | 0 | completion_fraction, stalls |
| dynamics_seed73_primary_speed0.3 | 307 | asc_stretch23cm_20cm | 24/32 | 0/8/0 | 0 | completion_fraction, stalls |
| dynamics_seed73_primary_speed0.3 | 101 | desc_stretch23cm_20cm | 18/32 | 8/6/0 | 6 | completion_fraction, falls, stalls, history_base_contact |
| dynamics_seed73_primary_speed0.3 | 211 | desc_stretch23cm_20cm | 13/32 | 12/6/1 | 10 | completion_fraction, falls, stalls, history_base_contact |
| dynamics_seed73_primary_speed0.3 | 307 | desc_stretch23cm_20cm | 15/32 | 12/5/0 | 5 | completion_fraction, falls, stalls, history_base_contact |
| dynamics_seed79_primary_speed0.3 | 211 | asc_paper_A1_16cm_27cm | 31/32 | 1/0/0 | 1 | history_base_contact |
| dynamics_seed79_primary_speed0.3 | 307 | asc_paper_Aliengo_17cm_25cm | 30/32 | 0/0/2 | 0 | completion_fraction, lateral_escapes |
| dynamics_seed79_primary_speed0.3 | 211 | asc_unseen_11cm_33cm | 26/32 | 3/0/4 | 2 | completion_fraction, falls, lateral_escapes, history_base_contact |
| dynamics_seed79_primary_speed0.3 | 307 | asc_unseen_11cm_33cm | 28/32 | 0/0/4 | 0 | completion_fraction, lateral_escapes |
| dynamics_seed79_primary_speed0.3 | 101 | asc_unseen_165mm_29cm | 30/32 | 1/0/1 | 1 | completion_fraction, history_base_contact |
| dynamics_seed79_primary_speed0.3 | 211 | asc_unseen_165mm_29cm | 31/32 | 1/0/0 | 1 | history_base_contact |
| dynamics_seed79_primary_speed0.3 | 307 | asc_unseen_165mm_29cm | 30/32 | 2/0/0 | 1 | completion_fraction, falls, history_base_contact |
| dynamics_seed79_primary_speed0.3 | 101 | asc_unseen_lip25mm_16cm_33cm | 30/32 | 1/0/1 | 1 | completion_fraction, history_base_contact |
| dynamics_seed79_primary_speed0.3 | 211 | asc_unseen_lip25mm_16cm_33cm | 31/32 | 1/0/0 | 1 | history_base_contact |
| dynamics_seed79_primary_speed0.3 | 307 | asc_unseen_lip25mm_16cm_33cm | 30/32 | 0/1/1 | 0 | completion_fraction |
| dynamics_seed79_primary_speed0.3 | 101 | desc_unseen_lip25mm_16cm_33cm | 30/32 | 0/0/2 | 0 | completion_fraction, lateral_escapes |
| dynamics_seed79_primary_speed0.3 | 101 | asc_long12_17cm_25cm | 26/32 | 3/2/1 | 3 | completion_fraction, falls, stalls, history_base_contact |
| dynamics_seed79_primary_speed0.3 | 211 | asc_long12_17cm_25cm | 28/32 | 1/1/2 | 1 | completion_fraction, lateral_escapes, history_base_contact |
| dynamics_seed79_primary_speed0.3 | 307 | asc_long12_17cm_25cm | 28/32 | 4/0/0 | 4 | completion_fraction, falls, history_base_contact |
| dynamics_seed79_primary_speed0.3 | 101 | asc_stretch23cm_20cm | 23/32 | 0/8/1 | 0 | completion_fraction, stalls |
| dynamics_seed79_primary_speed0.3 | 211 | asc_stretch23cm_20cm | 28/32 | 0/3/1 | 0 | completion_fraction, stalls |
| dynamics_seed79_primary_speed0.3 | 307 | asc_stretch23cm_20cm | 27/32 | 0/5/0 | 0 | completion_fraction, stalls |
| dynamics_seed79_primary_speed0.3 | 101 | desc_stretch23cm_20cm | 19/32 | 12/1/0 | 8 | completion_fraction, falls, history_base_contact |
| dynamics_seed79_primary_speed0.3 | 211 | desc_stretch23cm_20cm | 19/32 | 9/4/0 | 8 | completion_fraction, falls, stalls, history_base_contact |
| dynamics_seed79_primary_speed0.3 | 307 | desc_stretch23cm_20cm | 15/32 | 14/3/0 | 12 | completion_fraction, falls, stalls, history_base_contact |

## Material, dynamics and heading scope

Foot-only nominal0.8/0.6,lower0.45/0.35,higher1.0/0.8 use the basic scene with identical prescribed geometry/speed/reset seeds. Terrain authored friction is1/1 with multiply combine mode; shape readbacks do not establish backend contact-pair coefficients. These material scenes test only0.3m/s. Combined dynamics uses three construction seeds 71/73/79: startup mass/COM draws and reset PD gains at nominal foot friction,also only0.3m/s; it does not cover calibrated delay or motor strength.

The12-standard-case heading comparison uses reset seeds 401/409/419 at 0.3 m/s. Normal external heading feedback requests clamp(-yaw,±0.5)rad/s,with no lateral correction. The paired stress requests zero yaw rate while the actor still receives feedback. Per-env initial root positions and aggregate pose distributions are compared in JSON; full initial state is not saved.

| Paired comparison | Geometry | Root positions | Pose distributions | Thresholds | Contact metadata | Heading identical |
| --- | --- | --- | --- | --- | --- | --- |
| nominal_speed0.3 | True | True | True | True | True | True |
| nominal_speed0.5 | True | True | True | True | True | True |
| foot_low | True | True | True | True | True | True |
| foot_high | True | True | True | True | True | True |
| heading_zero_yaw | True | True | True | True | True | False |

| Standard12 heading mode | Completed | Escape flags | XY tracking RMSE (m/s) | Yaw tracking MAE (rad/s) | Heading absolute error (rad) | Lateral absolute error (m) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| standard_heading-control_primary_speed0.3 | 1152/1152 | 0 | 0.05244 | 0.03193 | 0.00868 | 0.06927 |
| standard_zero-yaw_primary_speed0.3 | 1050/1152 | 95 | 0.05400 | 0.03311 | 0.06500 | 0.10771 |

The yaw tracking target differs deliberately between modes; compare the outcome and heading/lateral drift alongside the target-relative yaw error, without interpreting lower yaw error as universally better heading.

## Fixed nominal checkpoint motion comparison

The table below keeps only cases with complete traversal and zero failure flags for both frozen checkpoints across all three reset seeds; failed cases remain in every gate/outcome table above. Values count strict numerical reductions for slide680 relative to control660, without significance or smoothness calibration. The checkpoints differ by reward and 20 training updates, so this is not an isolated reward-effect estimate.

| Speed (m/s) | Jointly failure free cases | Current leg contact lower | Action second difference lower | Root jerk lower | Current slip proxy lower | XY tracking error lower | Lateral error lower |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.3 | 14 | 12/14 | 3/14 | 6/14 | 14/14 | 2/14 | 7/14 |
| 0.5 | 14 | 12/14 | 10/14 | 8/14 | 14/14 | 2/14 | 8/14 |

## Actual physical parameter readbacks

| Evaluation | Foot static/dynamic | Initial base mass range (kg) | Initial Kp range | Initial Kd range | Initial/final readbacks verified |
| --- | --- | --- | --- | --- | --- |
| foot_nominal_primary_speed0.3 | 0.8/0.6 | 6.9210–6.9210 | 25.0000–25.0000 | 0.5000–0.5000 | available_and_verified/available_and_verified |
| foot_low_primary_speed0.3 | 0.45/0.35 | 6.9210–6.9210 | 25.0000–25.0000 | 0.5000–0.5000 | available_and_verified/available_and_verified |
| foot_high_primary_speed0.3 | 1.0/0.8 | 6.9210–6.9210 | 25.0000–25.0000 | 0.5000–0.5000 | available_and_verified/available_and_verified |
| dynamics_seed71_primary_speed0.3 | 0.8/0.6 | 5.5400–8.6334 | 22.5003–27.4996 | 0.4500–0.5500 | available_and_verified/available_and_verified |
| dynamics_seed73_primary_speed0.3 | 0.8/0.6 | 5.5381–8.6469 | 22.5033–27.4996 | 0.4500–0.5500 | available_and_verified/available_and_verified |
| dynamics_seed79_primary_speed0.3 | 0.8/0.6 | 5.5400–8.6316 | 22.5035–27.4998 | 0.4500–0.5500 | available_and_verified/available_and_verified |

COM offsets, inertia, PD scale ratios and final summaries remain in JSON. Initial/final summaries can reflect gains after automatic resets and cannot be assigned exactly to each recorded first episode. All verified terrain bindings retain authored 1/1 friction and multiply combine mode.

## Separate0.5m/s foot-material supplement

Status: complete. The separately recorded protocol adds foot-only nominal/lower/higher friction at 0.5 m/s, with the same frozen primary, final geometries and original gates. It pairs lower/higher with the0.5m/s basic nominal reference. These additional scenes do not change the original frozen protocol status and do not test0.5m/s combined dynamics. Report: `reproduction/stair-frozen-material-speed05.md`.

| Supplement material | Completed | Whole16-case gate |
| --- | ---: | --- |
| nominal | 1520/1536 | FAIL |
| low | 1535/1536 | PASS |
| high | 1395/1536 | FAIL |

## Flat regression

Status: complete. The frozen stairpolicy is tested from reset on six prescribed20s plane commands with64envs and zero gradient updates. Its original survival/tracking criteria are distinct from staircase completion. Source: `isaaclab/logs/2026-10-11_06-09-35_frozen-stair-policy-flat-regression/result.json`. Original flatgate: FAIL. Detailed report: `reproduction/stair-policy-frozen-flat-regression.md`.

| Flat command [vx,vy,yaw] | Survived | First falls | XY MAE (m/s) | Yaw MAE (rad/s) | Upright fraction | Original gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| [0.3, 0.0, 0.0] | 64/64 | 0 | 0.028300 | 0.017840 | 1.000000 | PASS |
| [0.5, 0.0, 0.0] | 64/64 | 0 | 0.028414 | 0.023349 | 1.000000 | PASS |
| [-0.5, 0.0, 0.0] | 64/64 | 0 | 0.499974 | 0.000456 | 1.000000 | FAIL |
| [0.0, 0.3, 0.0] | 0/64 | 64 | 0.625148 | 0.770983 | 0.000000 | FAIL |
| [0.0, 0.0, 0.5] | 62/64 | 2 | 0.076970 | 0.217419 | 0.998370 | PASS |
| [0.0, 0.0, -0.5] | 64/64 | 0 | 0.000806 | 0.498475 | 1.000000 | FAIL |

The frozen stairpolicy passes3/6 commands: two forwards and positive yaw. Backward and negative yaw commands barely move; lateralcommand has0/64 full duration survival. Positive yaw passes95% survival with2first episode falls,so it is not failure free. Per-axis roll RMS/peak were not recorded. The earlier dedicated flat checkpoint result does not replace this stair-policy regression.

## Measurement and interpretation limits

- Frozen primary remains control660 irrespective of final outcomes; secondary slide680 is a nominal two-speed comparator only and is not tested across material, heading or dynamics scenes.
- The final control660 versus slide680 comparison is descriptive at checkpoint level: slide680 has feet_slide enabled and20more training updates from the common620 origin. It cannot isolate the effect of the slide reward; matched40-update tuning evidence is separate.
- Every final case keeps the original95% case/seed completion and <=5% each fall/stall/lateral-escape,zero history-base-contact gate. With32 envs,31 passes completion and30 fails. Nonstretch/stretch labels only stratify results; any failed case fails the whole evaluated matrix.
- Paper-corresponding geometry is transferred to Go2/Isaac Lab; geometric success alone does not reproduce every paper claim or establish real-robot transfer.
- Reset seeds do not redraw startup material/mass/COM. Three dynamics construction seeds provide new startup draws; PD gains can be redrawn by resets/autoresets. Initial/final distribution summaries are not exact per-env first episode gain snapshots.
- Material and combined dynamics are evaluated only at 0.3 m/s. Foot-only basic nominal/low/high isolate intended foot-friction changes; domainnone nominal changes material on all robot bodies and cannot serve as the only isolated-foot reference.
- Readbacks describe robot shape parameters and actual composed terrain USD authored attributes; they do not measure solver contact-pair coefficients or calibrated real named materials.
- Headingcontrol uses root yaw target 0,gain1,clamp±.5rad/s,no lateral correction. Zero-yaw stress sets ordinary yaw-rate command tozero; policy retains IMU/joint feedback. It is not an open-loop robot test.
- Motion metrics are arithmetic means of seed-level case aggregates and then macro means over cases,not pooled trajectory RMS. First episodes are preserved before autoreset; motion excludes first second. Nonexclusive failure flags and unique noncompletions are both retained.
- Lower action/contact/jerk on failed or shorter episodes does not prove smoother competent traversal. No pause flag and no single scalar certifies smoothness; complete continuous video review both directions remains separate.
- Current/history netnormalforce vector norms include riser normals and exclude tangential friction; current/history leg presence differs from body-count rewards. Slip is foot-link worldXYspeed proxy,not contact-point terrain-tangent slip.
- Physics 5ms,policy 20ms,retainedhistory3 with sample ages0/5/10 ms;15 ms-old initial substep impact may be lost. Sensor cadence is inferred from config/stepping; runtime timestamps were not measured.
- Sparse0.1s traces cover one representative env/case/seed and cannot bound whole-batch force peaks,substep impulse or duration. Full per-env initial orientation/state is not stored.

Sources: frozen plan/acceptance/geometry files, raw result/config/physics-diagnostic/domain-parameter files linked in compressedJSON. Raw trajectories remain local in ignored IsaacLab logs; JSONgzip compression is lossless.
