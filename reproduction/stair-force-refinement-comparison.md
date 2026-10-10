# Force proxy refinement: force660/680 against contact620

Status: complete at 0.3 m/s. This preserves the reused 24-case tuning matrix, reset seeds 11/29/47, 32 environments per case/seed and the original 95% gate. It does not provide independent final testing or force-branch acceptance at both speeds.

| Label | Training origin | Force updates after contact620 | Cumulative updates after model570 |
| --- | --- | ---: | ---: |
| contact620 | model570 | 0 | 50 |
| force640 (not evaluated here) | contact620 | 20 | 70 |
| force660 | contact620 | 40 | 90 |
| force680 | contact620 | 60 | 110 |

force640 and contact640 are different policies despite the same absolute counter. contact640 continues the contact branch from model570 for 70 updates. This force branch starts from archived contact620; it retains the contact count term and adds the bounded force proxy. Against contact620, extra training and the new force cost change together, so these results cannot isolate the force reward effect.

The new term is sum_i min(relu((F_i−50)/50)^2,4), with F_i the retained-history net normal-force norm for each thigh/calf body. Weight -0.02 is scaled by the 20 ms policy step; at >=150 N it saturates at 0.0016 cost per body/step. It is not impulse, energy, damage or a force limiter. Both PPO and HIM retain Adam state with fixed learning rate 0.0001; seed 1 and maximum initial terrain level 4 (levels sampled 0 through 4). Source commit/dirty state and exact reward manifest are preserved in compressed JSON.

| Policy | Completed | Worst case/seed | Case/seed gates | Final gate | Falls/stalls/escapes | History/current base | Maximum pause (s) |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| contact620 | 2302/2304 | 31/32 | 72/72 | True | 0/2/0 | 0/0 | 3.620 |
| force660 | 2302/2304 | 30/32 | 71/72 | False | 2/0/0 | 0/0 | 0.940 |
| force680 | 2291/2304 | 26/32 | 69/72 | False | 12/1/0 | 0/0 | 3.620 |

31/32 passes 95%; 30/32 fails. Gate failures remain disqualifying even if overall completion, jerk, action variation or contact frequency improves. Aggregate fall flags do not by themselves establish physical toppling or a collision cause. A lower motion statistic on failed/stopped episodes does not establish smoother competent traversal.

| Right minus left | Completion better/equal/worse cases | Lower current leg cases | Lower action second RMS cases | Lower jerk cases | Lower current slip cases | Lower tracking cases | Lower lateral cases | Both full/failure-free cases |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| force660 − contact620 | 1/22/1 | 17/24 | 22/24 | 18/24 | 18/24 | 22/24 | 19/24 | 22/24 |
| force680 − contact620 | 1/21/2 | 22/24 | 23/24 | 19/24 | 7/24 | 11/24 | 23/24 | 21/24 |
| force680 − force660 | 0/22/2 | 18/24 | 14/24 | 15/24 | 8/24 | 10/24 | 16/24 | 22/24 |

Counts are strict numerical directions of case means, with no calibrated significance threshold. Failed cases remain descriptive and marked in CSV/JSON; the last column distinguishes full and failure-free traversal.

| Direction / policy | Current leg contact | History leg contact | Action second RMS | Root jerk (m/s³) | Current slip proxy | XY tracking RMSE (m/s) | Lateral error (m) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ascending/contact620 | 8.62% | 10.80% | 0.09687 | 46.64 | 14.20% | 0.05900 | 0.10149 |
| ascending/force660 | 7.71% | 10.06% | 0.09467 | 45.73 | 13.82% | 0.05442 | 0.06631 |
| ascending/force680 | 6.45% | 8.10% | 0.09253 | 44.86 | 14.92% | 0.05317 | 0.05968 |
| descending/contact620 | 30.69% | 32.91% | 0.07799 | 58.63 | 26.12% | 0.06428 | 0.05768 |
| descending/force660 | 29.65% | 32.02% | 0.07189 | 52.06 | 26.21% | 0.06144 | 0.05570 |
| descending/force680 | 29.30% | 31.78% | 0.07266 | 53.20 | 26.01% | 0.06538 | 0.04959 |

## Recorded failures and pauses

force660, case 15 (desc, 20/27/0 cm rise/tread/nose): seed completions 30/32/32, geometry gate=False, max pause=0.940 s. seed 11/env 481, ['fall'], root x=1.5395 m; seed 11/env 491, ['fall'], root x=1.5601 m.

force680, case 15 (desc, 20/27/0 cm rise/tread/nose): seed completions 32/31/29, geometry gate=False, max pause=0.540 s. seed 29/env 504, ['fall'], root x=1.5887 m; seed 47/env 483, ['fall'], root x=1.5609 m; seed 47/env 501, ['fall'], root x=1.5583 m; seed 47/env 507, ['fall'], root x=1.5307 m.

force680, case 23 (desc, 20/25/2 cm rise/tread/nose): seed completions 26/29/32, geometry gate=False, max pause=3.620 s. seed 11/env 744, ['fall'], root x=1.5138 m; seed 11/env 748, ['fall'], root x=1.5579 m; seed 11/env 754, ['stall'], root x=1.3146 m; seed 11/env 755, ['fall'], root x=1.5024 m; seed 11/env 764, ['fall'], root x=1.5272 m; seed 11/env 767, ['fall'], root x=1.5037 m; seed 29/env 747, ['fall'], root x=1.5058 m; seed 29/env 755, ['fall'], root x=1.5228 m; seed 29/env 758, ['fall'], root x=1.5033 m.

contact620, case 8 (asc, 17/25/0 cm rise/tread/nose): seed completions 31/31/32, geometry gate=True, max pause=3.620 s. seed 11/env 284, ['stall'], root x=1.7631 m; seed 29/env 277, ['stall'], root x=2.0145 m.

## Saved matching and CPU motion review

All policies use the same evaluation construction and saved case/seed initial root positions, aggregate pose, headings, thresholds, contact cadence and nominal physical readbacks. Full per-environment initial quaternions are absent. Inference uses an external proportional heading controller; these are policy-plus-heading-controller results. Nominal startup materials remain fixed across reset seeds.

| Pair | Matched case/seed pairs | Eligible under saved evidence and declared 95% gates | Both full and failure-free | Protocol differences |
| --- | ---: | ---: | ---: | ---: |
| force660 − contact620 | 72 | 71 | 69 | 0 |
| force680 − contact620 | 72 | 69 | 66 | 0 |
| force680 − force660 | 72 | 68 | 67 | 0 |

The analyzer gate can admit a 31/32 row with one stall. The separate full/failure-free count exposes that limitation. Sparse named force peaks and excluded case/seed metric deltas are retained in compressed JSON. These one-environment, 0.1 s traces cannot establish whole-batch impact duration or severity; peaks on different bodies/cases/times do not isolate a controlled change.

Smoothness remains unverified. Require the original per-case/seed traversal gate, then examine pause, current/history contact, forces, slip, action, jerk and tracking together. A passing low-speed tuning result still requires the other speed and independent final cases; do not select a stopped or failing policy merely for lower jerk.

Detailed case/seed summaries, provenance, matching checks and failures are stored losslessly in `stair-force-refinement-comparison.json.gz`; raw simulator results remain under the source run directories. The CSV contains per-case counts/gates, motion metrics and changes against the same-batch contact620 baseline.

## Sparse named force peaks

| Policy | Active representative rows after warmup | Largest sampled current force (N) | Largest retained-history force (N) |
| --- | ---: | ---: | ---: |
| contact620 | 9046 | 489.6 | 617.2 |
| force660 | 8922 | 350.2 | 397.9 |
| force680 | 9069 | 266.6 | 487.9 |

These maxima can occur on different bodies, cases and times. Lower sampled peak force cannot compensate for the recorded traversal failures or establish gentle contact duration.

Neither evaluated force checkpoint passes the 0.3 m/s case/seed gate. Preserve contact620 as the contact-branch candidate for the separate final comparison; no force checkpoint is selected from this run. The comparison cannot isolate force-reward causality because continued training also changes.
