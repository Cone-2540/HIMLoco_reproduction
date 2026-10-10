# Force continuation with a matched 40-update contact control

Status: all five low-speed reports complete. This reuses the 24-case tuning matrix at 0.3 m/s, seeds 11/29/47 and 32 environments per case/seed. The original 95% gate remains fixed; this is not independent final evaluation or two-speed acceptance.

| Policy | Origin | Added contact updates after 620 | Added force updates after 620 | Cumulative updates after 570 |
| --- | --- | ---: | ---: | ---: |
| contact620 | model570 | 0 | 0 | 50 |
| control660 | contact620 | 40 | 0 | 90 |
| force660 | contact620 | 0 | 40 | 90 |
| force700 | contact620 | 0 | 80 | 130 |
| force720 | contact620 | 0 | 100 | 150 |

The contact620 row preserves the archived baseline. Only control660 versus force660 matches the 40-update continuation budget and the saved common contact620 origin. Checked training manifests, restored Adam/PPO/HIM rates, initial exploration summaries and nominal startup physics agree. The checked reward difference is the force proxy weight -0.02, retaining contact count -0.1. This is one matched training realization; the dirty force launch has no recoverable exact source snapshot. It does not prove identical full trajectories, GPU determinism or reward effects across training seeds.

The control requested 100 additional updates, but the operator stopped it after saving model660. Independent checkpoint metadata confirms 40 saved updates and 16,384,000 new environment steps. The console/event record completes 48 updates; eight later updates are not saved and are excluded. Any partial next rollout is unknown, and no control result.json exists. Do not call this a completed 100-update control. The force training did complete 100 updates to model720 with finite parameters; its training/export result alone does not establish locomotion.

Both branches use seed 1, 4096 environments, fixed PPO/HIM learning rate 0.0001 and maximum initial terrain level 4 (levels sampled 0 through 4). The force proxy is the sum of per-body min(relu((F−50)/50)^2,4) over 8 thigh/calf bodies, with retained-history net normal force F. At ≥150 N its cost saturates at 0.0016/body/20 ms policy step; it is not an impulse, damage or force-limit measure.

| Policy | Completed | Worst case/seed | Case/seed gates | Final gate | Falls/stalls/escapes | History/current base | Maximum pause(s) |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| contact620 | 2302/2304 | 31/32 | 72/72 | True | 0/2/0 | 0/0 | 3.620 |
| control660 | 2304/2304 | 32/32 | 72/72 | True | 0/0/0 | 0/0 | 0.560 |
| force660 | 2302/2304 | 30/32 | 71/72 | False | 2/0/0 | 0/0 | 0.940 |
| force700 | 2302/2304 | 31/32 | 72/72 | True | 2/0/0 | 0/0 | 1.880 |
| force720 | 2290/2304 | 26/32 | 69/72 | False | 14/0/0 | 0/0 | 0.640 |

31/32 passes 95%; 30/32 fails. Overall totals and low pauses cannot replace the case/seed gate. Aggregate fall flags with zero base contacts do not by themselves establish physical toppling or a collision cause. Failed/shortened episodes remain in the source; low action/contact/jerk there cannot establish smoother competent traversal.

| Right minus left | Budget matched? | Completion better/equal/worse cases | Lower current leg cases | Lower action second RMS cases | Lower jerk cases | Lower current slip cases | Lower tracking cases | Lower lateral cases | Both full/failure-free cases |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| control660 − contact620 | False | 1/23/0 | 12/24 | 16/24 | 18/24 | 11/24 | 21/24 | 21/24 | 23/24 |
| force700 − contact620 | False | 1/22/1 | 18/24 | 18/24 | 16/24 | 11/24 | 24/24 | 19/24 | 22/24 |
| force660 − control660 | True | 0/23/1 | 18/24 | 19/24 | 16/24 | 15/24 | 15/24 | 13/24 | 23/24 |
| force700 − control660 | False | 0/23/1 | 19/24 | 14/24 | 11/24 | 10/24 | 18/24 | 10/24 | 23/24 |
| force720 − control660 | False | 0/23/1 | 19/24 | 15/24 | 18/24 | 9/24 | 13/24 | 16/24 | 23/24 |
| force720 − force700 | False | 0/23/1 | 11/24 | 18/24 | 17/24 | 3/24 | 8/24 | 14/24 | 23/24 |

These are strict numerical differences of case means, with no calibrated significance threshold. Metrics average three seed aggregates per case, then equally weight cases; they are not pooled RMS. Unequal budgets remain descriptive.

| Direction/policy | Current leg contact | Action second RMS | Root jerk(m/s³) | Current slip proxy | XY tracking RMSE(m/s) | Lateral error(m) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ascending/contact620 | 8.62% | 0.09687 | 46.64 | 14.20% | 0.05900 | 0.10149 |
| ascending/control660 | 7.30% | 0.09754 | 46.54 | 14.00% | 0.05349 | 0.07568 |
| ascending/force660 | 7.71% | 0.09467 | 45.73 | 13.82% | 0.05442 | 0.06631 |
| ascending/force700 | 6.77% | 0.09628 | 46.75 | 14.71% | 0.05292 | 0.07323 |
| ascending/force720 | 7.00% | 0.08896 | 42.79 | 15.73% | 0.05200 | 0.05106 |
| descending/contact620 | 30.69% | 0.07799 | 58.63 | 26.12% | 0.06428 | 0.05768 |
| descending/control660 | 32.76% | 0.07299 | 53.86 | 26.60% | 0.06134 | 0.05233 |
| descending/force660 | 29.65% | 0.07189 | 52.06 | 26.21% | 0.06144 | 0.05570 |
| descending/force700 | 28.80% | 0.07304 | 52.71 | 25.71% | 0.05776 | 0.05139 |
| descending/force720 | 28.81% | 0.07312 | 54.01 | 25.91% | 0.06505 | 0.06065 |

## Interpretation

The equal 40-update comparison gives control660 full traversal (2304/2304, zero failure flags, maximum pause 0.56 s) versus force660 at 2302/2304, with two fall flags concentrated in case 15/seed 11 and a failed 30/32 gate. Force660 has lower case means for current leg contact in 18/24, action second RMS in 19/24, jerk in 16/24 and current slip in 15/24. These motion directions do not compensate for its concentrated traversal regression.

Control660 is a low-speed candidate from the continued contact branch. Against its contact620 origin it removes the two recorded stalls and passes every case/seed 32/32, with lower tracking and lateral errors in 21/24 cases each. Its descent mean current leg contact increases from 30.69% to 32.76% and current slip from 26.12% to 26.60%, while jerk drops from 58.63 to 53.86 m/s³. Continuing the existing reward can improve traversal without adding a force term, with residual contact/slip tradeoffs.

Force700 passes all 72 low-speed case/seed gates, but keeps one aggregate fall flag in each of seeds 11 and 47 at the 20 cm descent (31/32/31) and a 1.88 s pause. Relative to control660, its current leg contact is lower in 19/24 cases, action second RMS in 14/24, jerk in 11/24, current slip in 10/24, tracking error in 18/24 and lateral error in 10/24. It uses 80 added updates versus 40, so this comparison cannot isolate the force term. Its 72/72 analyzer eligibility still allows those two failures; only 70/72 paired case/seeds are full and failure-free.

Force700 improves tracking RMSE in all 24 cases relative to archived contact620, but ascent jerk and slip means are slightly higher. The later force720 fails with 14 fall flags concentrated in case 15 despite a shorter 0.64 s maximum pause. This distinguishes passing the unchanged traversal gate from choosing the newest update or the smallest motion value.

Control660 and force700 warrant the other-speed check before final candidate freeze. This reused matrix does not certify smoothness. Preserve failed force660/680/720 outcomes and do not return to tuning after the independent final geometry set has been opened.

## Recorded failure geometry and seeds

contact620, case 8 (asc; 17/25/0 cm rise/tread/nose): completions 31/31/32, geometry gate=True, maximum pause 3.620 s. seed 11/env 284, ['stall'], root x=1.7631 m; seed 29/env 277, ['stall'], root x=2.0145 m.

force660, case 15 (desc; 20/27/0 cm rise/tread/nose): completions 30/32/32, geometry gate=False, maximum pause 0.940 s. seed 11/env 481, ['fall'], root x=1.5395 m; seed 11/env 491, ['fall'], root x=1.5601 m.

force700, case 15 (desc; 20/27/0 cm rise/tread/nose): completions 31/32/31, geometry gate=True, maximum pause 1.880 s. seed 11/env 498, ['fall'], root x=1.5202 m; seed 47/env 490, ['fall'], root x=1.5169 m.

force720, case 15 (desc; 20/27/0 cm rise/tread/nose): completions 29/27/26, geometry gate=False, maximum pause 0.640 s. seed 11/env 492, ['fall'], root x=1.7786 m; seed 11/env 493, ['fall'], root x=1.4097 m; seed 11/env 501, ['fall'], root x=1.4329 m; seed 29/env 484, ['fall'], root x=1.4243 m; seed 29/env 486, ['fall'], root x=1.6127 m; seed 29/env 487, ['fall'], root x=1.5239 m; seed 29/env 495, ['fall'], root x=1.8791 m; seed 29/env 502, ['fall'], root x=1.4142 m; seed 47/env 485, ['fall'], root x=1.5035 m; seed 47/env 488, ['fall'], root x=1.4130 m; seed 47/env 491, ['fall'], root x=1.4172 m; seed 47/env 500, ['fall'], root x=1.4306 m; seed 47/env 504, ['fall'], root x=1.4280 m; seed 47/env 511, ['fall'], root x=1.4142 m.

## Saved matching and independent CPU motion review

The 40-update force/control pair uses different evaluation constructions. Exact saved geometry, reset seeds, initial root xyz arrays, aggregate pose, heading/controller, thresholds, contact cadence and nominal physical readbacks are checked in compressed JSON. Full per-environment initial quaternions are absent. The new force700/720/control660 policies share one scene. Inference uses external proportional heading correction, so these are policy-plus-heading-controller results.

| Pair | Matched case/seed pairs | Eligible under saved evidence and 95% gates | Both full/failure-free | Protocol differences |
| --- | ---: | ---: | ---: | ---: |
| control660 − contact620 | 72 | 72 | 70 | 0 |
| force700 − contact620 | 72 | 72 | 68 | 0 |
| force660 − control660 | 72 | 71 | 71 | 0 |
| force700 − control660 | 72 | 72 | 70 | 0 |
| force720 − control660 | 72 | 69 | 69 | 0 |
| force720 − force700 | 72 | 69 | 69 | 0 |

The gate can admit 31/32 with one stall. The separate full/failure-free count makes that distinction visible. Excluded pairs and their outcome/metric deltas remain in compressed JSON.

| Policy | Active sparse rows after warmup | Largest sampled current named leg force(N) | Largest retained-history force(N) |
| --- | ---: | ---: | ---: |
| contact620 | 9046 | 489.6 | 617.2 |
| control660 | 8811 | 378.4 | 456.7 |
| force660 | 8922 | 350.2 | 397.9 |
| force700 | 8802 | 349.9 | 349.9 |
| force720 | 9131 | 649.6 | 649.6 |

These 0.1 s traces sample one environment per case/seed. Peaks can occur on different bodies, cases and times; they are not whole-batch maxima, impulse, tangential friction, scrape duration or damage. Current/history contact means policy-boundary presence; history 3 at 5 ms retains 0/5/10 ms ages at 20 ms cadence and can miss first-substep-only impacts. Slip uses foot-link horizontal world speed conditioned on contact, with different current/history denominators. Nominal material events cover all robot bodies and remain fixed across reset seeds.

Detailed source provenance, checkpoint/interruption audit, case/seed metrics, failures and comparisons are preserved losslessly in `stair-force-controlled-comparison.json.gz`; per-case counts/gates and changes against control660 are in CSV. Earlier force660/680/contact620 results remain in `stair-force-refinement-comparison.md`. Smoothness and independent final performance remain unverified.

Low-speed gate-qualified force checkpoints: force700. Require 0.5 m/s and independent final testing before selecting a force checkpoint; do not relax gates for lower jerk/forces.
