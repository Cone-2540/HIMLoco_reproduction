# Two-speed tuning comparison: contact control, foot slide and force candidates

Status: all eight candidate/speed reports complete. All runs preserve 24 geometries, seeds 11/29/47, 32 environments per case/seed and the original 95% gate. This is the reused tuning/regression matrix; independent final geometries/seeds have not been scored here.

| Candidate | Training profile | Added updates after contact620 | Cumulative updates after model570 |
| --- | --- | ---: | ---: |
| control660 | contact | 40 | 90 |
| slide660 | contact_slide | 40 | 90 |
| slide680 | contact_slide | 60 | 110 |
| force700 | contact_force | 80 | 130 |

The equal 40-update pair is slide660 versus control660 from the same archived contact620. The slide branch adds only feet_slide=-0.05, retaining leg_contacts=-0.1 and the faithful terms. It uses the existing foot world XY-velocity-squared penalty gated by retained-history foot normal force above 1 N, with matching FL/FR/RL/RR sensor/asset ordering. Its clean-source launch, unchanged actor/collision geometry and training/startup controls are independently audited in compressed JSON. The 60/80-update slide680/force700 comparisons have unequal budgets and cannot isolate reward effects.

The control planned 100 updates but was interrupted: model660 saves 40; 48 complete updates are observed, with eight later updates unsaved/excluded and any next partial rollout unknown. The slide run completed 60 updates to model680 with finite parameters and validated export. All branches use one training seed, restored Adam state, fixed PPO/HIM learning rate 0.0001 and maximum initial terrain level 4 (sampled 0 through 4). Force launch source was dirty; slide/control launch sources are clean. This remains one training realization, with saved-state and nondeterministic GPU limits.

| Candidate | Speed(m/s) | Completed | Worst case/seed | Case/seed gates | Final gate | Falls/stalls/escapes | History/current base | Maximum pause(s) |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- | ---: |
| control660 | 0.3 | 2304/2304 | 32/32 | 72/72 | True | 0/0/0 | 0/0 | 0.560 |
| control660 | 0.5 | 2304/2304 | 32/32 | 72/72 | True | 0/0/0 | 0/0 | 0.100 |
| slide660 | 0.3 | 2304/2304 | 32/32 | 72/72 | True | 0/0/0 | 0/0 | 2.500 |
| slide660 | 0.5 | 2304/2304 | 32/32 | 72/72 | True | 0/0/0 | 0/0 | 0.420 |
| slide680 | 0.3 | 2304/2304 | 32/32 | 72/72 | True | 0/0/0 | 0/0 | 0.840 |
| slide680 | 0.5 | 2304/2304 | 32/32 | 72/72 | True | 0/0/0 | 0/0 | 0.600 |
| force700 | 0.3 | 2302/2304 | 31/32 | 72/72 | True | 2/0/0 | 0/0 | 1.880 |
| force700 | 0.5 | 2304/2304 | 32/32 | 72/72 | True | 0/0/0 | 0/0 | 0.080 |

31/32 passes 95%; 30/32 fails. Failure labels are nonexclusive and aggregate fall flags alone do not establish physical toppling or a collision cause. Overall completion and lower pause/action/jerk/contact on failed or shortened episodes cannot replace the case/seed gate.

| Right minus left | Speed | Equal training budget? | Lower current leg cases | Lower action second RMS cases | Lower jerk cases | Lower current slip cases | Lower tracking cases | Lower lateral cases | Both full/failure-free cases |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| slide660 − control660 | 0.3 | True | 17/24 | 21/24 | 10/24 | 24/24 | 2/24 | 10/24 | 24/24 |
| slide680 − control660 | 0.3 | False | 19/24 | 12/24 | 9/24 | 24/24 | 9/24 | 8/24 | 24/24 |
| force700 − control660 | 0.3 | False | 19/24 | 14/24 | 11/24 | 10/24 | 18/24 | 10/24 | 23/24 |
| slide680 − slide660 | 0.3 | False | 16/24 | 2/24 | 9/24 | 21/24 | 22/24 | 10/24 | 24/24 |
| slide660 − force700 | 0.3 | False | 10/24 | 19/24 | 16/24 | 24/24 | 0/24 | 8/24 | 23/24 |
| slide660 − control660 | 0.5 | True | 16/24 | 23/24 | 20/24 | 24/24 | 0/24 | 9/24 | 24/24 |
| slide680 − control660 | 0.5 | False | 19/24 | 16/24 | 13/24 | 24/24 | 4/24 | 10/24 | 24/24 |
| force700 − control660 | 0.5 | False | 15/24 | 12/24 | 18/24 | 9/24 | 20/24 | 7/24 | 24/24 |
| slide680 − slide660 | 0.5 | False | 21/24 | 0/24 | 4/24 | 13/24 | 19/24 | 16/24 | 24/24 |
| slide660 − force700 | 0.5 | False | 12/24 | 24/24 | 16/24 | 24/24 | 0/24 | 16/24 | 24/24 |

Counts are strict numerical directions of case means, with no calibrated significance threshold. They include descriptive failed-case rows; JSON and CSV retain gates, durations, failure counts and exposure denominators. Metrics average seed aggregates then weight cases equally, not pooled RMS.

| Candidate/speed/direction | Current leg contact | History leg contact | Action second RMS | Root jerk(m/s³) | Current slip proxy | XY tracking RMSE(m/s) | Lateral error(m) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| control660/0.3/ascending | 7.30% | 9.40% | 0.09754 | 46.54 | 14.00% | 0.05349 | 0.07569 |
| slide660/0.3/ascending | 7.92% | 10.16% | 0.09429 | 44.32 | 10.92% | 0.06478 | 0.08154 |
| slide680/0.3/ascending | 6.84% | 8.50% | 0.09870 | 45.52 | 10.46% | 0.05689 | 0.07577 |
| force700/0.3/ascending | 6.77% | 8.49% | 0.09628 | 46.75 | 14.71% | 0.05292 | 0.07323 |
| control660/0.3/descending | 32.76% | 35.32% | 0.07298 | 53.87 | 26.60% | 0.06133 | 0.05232 |
| slide660/0.3/descending | 29.51% | 31.50% | 0.06945 | 55.52 | 22.02% | 0.06940 | 0.05244 |
| slide680/0.3/descending | 28.87% | 30.85% | 0.07330 | 56.91 | 21.57% | 0.06094 | 0.05698 |
| force700/0.3/descending | 28.80% | 31.19% | 0.07304 | 52.71 | 25.71% | 0.05776 | 0.05139 |
| control660/0.5/ascending | 7.76% | 10.54% | 0.17999 | 73.82 | 17.12% | 0.06311 | 0.05296 |
| slide660/0.5/ascending | 8.68% | 11.65% | 0.16676 | 69.62 | 14.81% | 0.07261 | 0.05229 |
| slide680/0.5/ascending | 7.33% | 9.76% | 0.17301 | 70.64 | 13.84% | 0.06539 | 0.05092 |
| force700/0.5/ascending | 7.25% | 9.62% | 0.17376 | 72.35 | 16.85% | 0.06016 | 0.05204 |
| control660/0.5/descending | 20.80% | 22.93% | 0.11669 | 85.65 | 24.18% | 0.07071 | 0.05906 |
| slide660/0.5/descending | 15.02% | 16.69% | 0.11410 | 84.42 | 20.56% | 0.08290 | 0.06617 |
| slide680/0.5/descending | 13.59% | 15.29% | 0.11778 | 86.74 | 20.85% | 0.08126 | 0.06560 |
| force700/0.5/descending | 20.25% | 22.18% | 0.11939 | 83.88 | 25.95% | 0.06522 | 0.06829 |

## Two-speed candidate readiness

| Candidate | Both speed gates pass | Both speeds full/failure-free | Unique noncompletions | Maximum pause(s) |
| --- | --- | --- | ---: | ---: |
| control660 | True | True | 0 | 0.560 |
| slide660 | True | True | 0 | 2.500 |
| slide680 | True | True | 0 | 0.840 |
| force700 | True | False | 2 | 1.880 |

Passing the traversal gate is necessary, but does not certify smoothness. Prioritize all first-episode outcomes at both speeds, then assess pauses, current/history contact, force, action, jerk, slip and tracking together. Preserve rejected force660/680/720 and faithful620/contact670 failures in their earlier reports. Independent final testing must use the frozen selected checkpoint and original gates; do not resume tuning against those final cases.

## Candidate decision before independent final tests

Recommend **control660** as the primary frozen candidate. It has zero noncompletions and zero fall/stall/escape/base counts at both speeds, with the shortest maximum pauses (0.56 s at 0.3 m/s and 0.10 s at 0.5 m/s). Its current leg contact and slip remain quality limits, and inference includes external heading correction. Smoothness is unverified.

Keep **slide680** as the predeclared secondary comparison. It also completes both speeds without failure flags and reduces current slip in all 24 case means at each speed. Relative to control660, tracking RMSE is lower in only 9/24 low-speed cases and 4/24 high-speed cases; jerk is lower in 9/24 and 13/24, lateral error in 8/24 and 10/24. Its 0.84/0.60 s pauses are larger. This persistent slip benefit has tracking and motion tradeoffs, and 60 versus 40 added updates prevents an isolated reward claim.

The equal 40-update slide660/control660 pair supports a current-slip reduction in all 24 cases at both speeds for this realization. Slide660 also lowers action second RMS in 21/24 low-speed and 23/24 high-speed cases, but tracking improves in only 2/24 and 0/24 and its low-speed pause is 2.50 s. Force700 passes both casewise gates but retains two low-speed fall flags and a 1.88 s pause. These findings make them less suitable as the primary candidate under the stated traversal/pause/tracking priorities.

Control660 and both slide candidates have all 72 matched case/seed pairs full and failure-free in the saved CPU motion reviews. Force700 low-speed pairs remain gate-eligible, but only 70/72 are full and failure-free. Named sampled force peaks still reach hundreds of newtons, on different bodies, times and geometries; they do not isolate impact severity. Both added rewards measure proxies.

Freeze this choice before opening the final geometry set. The secondary comparison cannot be promoted by choosing the better final outcome. Keep failed tuning results and unchanged gates; independent final failures are reported as limitations and are not used for another tuning round.

## Recorded failures

force700, 0.3 m/s, case 15 (desc; 20/27/0 cm rise/tread/nose): completions 31/32/31, geometry gate=True, maximum pause 1.880 s. seed 11/env 498, ['fall'], root x=1.5202 m; seed 47/env 490, ['fall'], root x=1.5169 m.

## Saved matching and independent motion checks

Saved geometry, reset seeds, root xyz arrays, aggregate pose, heading/controller, thresholds, contact metadata and nominal mass/inertia/COM/PD/foot readbacks are checked per pair. Some candidates reuse separate evaluation constructions; full per-environment initial quaternions are absent. Nominal terrain authored USD properties and physical readbacks are available, but solver-effective pair coefficients are not. Inference includes an external proportional heading controller, so these are policy-plus-heading-controller results.

| Pair | Speed | Matched case/seed pairs | Saved evidence and 95% gate eligible | Both full/failure-free | Protocol differences |
| --- | ---: | ---: | ---: | ---: | ---: |
| slide660 − control660 | 0.3 | 72 | 72 | 72 | 0 |
| slide680 − control660 | 0.3 | 72 | 72 | 72 | 0 |
| force700 − control660 | 0.3 | 72 | 72 | 70 | 0 |
| slide680 − slide660 | 0.3 | 72 | 72 | 72 | 0 |
| slide660 − force700 | 0.3 | 72 | 72 | 70 | 0 |
| slide660 − control660 | 0.5 | 72 | 72 | 72 | 0 |
| slide680 − control660 | 0.5 | 72 | 72 | 72 | 0 |
| force700 − control660 | 0.5 | 72 | 72 | 72 | 0 |
| slide680 − slide660 | 0.5 | 72 | 72 | 72 | 0 |
| slide660 − force700 | 0.5 | 72 | 72 | 72 | 0 |

| Candidate / speed | Active sparse rows after warmup | Largest sampled current named leg force (N) | Largest retained-history force (N) |
| --- | ---: | ---: | ---: |
| control660/0.3 | 8811 | 378.4 | 456.7 |
| control660/0.5 | 5211 | 451.8 | 490.6 |
| slide660/0.3 | 9385 | 162.6 | 571.3 |
| slide660/0.5 | 5716 | 444.7 | 444.7 |
| slide680/0.3 | 8792 | 506.8 | 506.8 |
| slide680/0.5 | 5528 | 457.3 | 468.4 |
| force700/0.3 | 8802 | 349.9 | 349.9 |
| force700/0.5 | 5187 | 370.7 | 467.4 |

The analyzer gate may admit 31/32 with one failure; the full/failure-free count exposes that distinction. Sparse 0.1 s traces record one environment per case/seed and cannot establish whole-batch force maxima, impulse, duration or damage. Current/history any-leg contact means presence at policy boundaries. History 3 at 5 ms retains 0/5/10 ms at 20 ms cadence and can omit first-substep-only impacts. Foot world XY velocity is a slip proxy, not exact contact-point velocity or terrain-tangent slipping. Current/history denominators differ, and nominal material events cover all robot bodies rather than isolated feet.

All detailed metrics, failure endpoints, training/source/interruption audit and paired changes are stored losslessly in `stair-slide-checkpoint-comparison.json.gz`. The CSV retains one row per candidate/speed/case. Raw simulation reports remain local. Smoothness and real robot readiness remain unverified.
