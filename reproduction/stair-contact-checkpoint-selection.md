# Contact checkpoint selection: 620/640/670 at 0.3 and 0.5 m/s

Status: all six contact speed results are complete; candidate review follows. This is the reused 24-case tuning/regression matrix, with seeds 11/29/47 and 32 environments per case/seed. The original casewise gate is preserved; 31/32 passes 95%, 30/32 fails. Independent final testing is a separate step. The matched faithful control is complete and reported in `stair-matched-contact-ablation.md`.

| Model | Speed(m/s) | Completed | Worst case/seed | Fall/stall/escape flags | Base history/current | Final traversal | Max pause(s) | Pause flag |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: | --- |
| 620 | 0.3 | 2302/2304 | 31/32 | 0/2/0 | 0/0 | True | 3.620 | True |
| 620 | 0.5 | 2304/2304 | 32/32 | 0/0/0 | 0/0 | True | 0.080 | False |
| 640 | 0.3 | 2299/2304 | 30/32 | 1/4/0 | 0/0 | False | 3.600 | True |
| 640 | 0.5 | 2304/2304 | 32/32 | 0/0/0 | 0/0 | True | 0.260 | False |
| 670 | 0.3 | 2302/2304 | 30/32 | 0/2/0 | 0/0 | False | 3.540 | True |
| 670 | 0.5 | 2304/2304 | 32/32 | 0/0/0 | 0/0 | True | 0.140 | False |

A pause flag=False does not certify smoothness. Unique failures, nonexclusive labels, invalid/numerical counts and zero-action controls are preserved in JSON. All cases, including stalled or failed rows, remain in the comparisons. Lower action RMS on a stopped or shortened episode is not evidence of better full traversal.

## Completed 0.5 m/s comparison: 640 versus 620

Both checkpoints complete 2304/2304 with every case/seed 32/32 and zero fall/stall/escape/base/numerical anomalies. Their maximum pauses are 0.08 s(620) and 0.26 s(640). Geometry, initial root positions, aggregate initial pose distributions and protocol/contact metadata match in the shared construction.

640 has lower action second-difference RMS in 20/24 cases, root jerk in 19/24 and current slip proxy in 21/24. Current any-leg contact is lower in only 8/24, tracking RMSE in 13/24 and lateral error in 12/24. The direction means expose the tradeoff below. Counts of numerical improvements do not establish their significance.

| Model/speed/direction | Action second RMS | Root jerk(m/s³) | Current leg contact | Current slip proxy | XY tracking RMSE(m/s) | Lateral error(m) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 620/0.3/ascending | 0.09687 | 46.64 | 8.57% | 14.21% | 0.05884 | 0.10139 |
| 620/0.3/descending | 0.07791 | 58.48 | 30.69% | 26.13% | 0.06426 | 0.05769 |
| 620/0.5/ascending | 0.17575 | 74.18 | 9.20% | 17.58% | 0.06725 | 0.06249 |
| 620/0.5/descending | 0.11820 | 91.19 | 20.07% | 24.83% | 0.06840 | 0.05477 |
| 640/0.3/ascending | 0.08963 | 43.76 | 8.20% | 14.72% | 0.06064 | 0.07637 |
| 640/0.3/descending | 0.07340 | 53.91 | 32.54% | 27.00% | 0.06147 | 0.07253 |
| 640/0.5/ascending | 0.16494 | 68.82 | 9.32% | 16.28% | 0.07049 | 0.05806 |
| 640/0.5/descending | 0.11727 | 88.79 | 23.17% | 24.56% | 0.06583 | 0.05942 |
| 670/0.3/ascending | 0.09195 | 43.34 | 8.88% | 16.00% | 0.05814 | 0.04906 |
| 670/0.3/descending | 0.07242 | 53.73 | 29.85% | 26.36% | 0.05662 | 0.05062 |
| 670/0.5/ascending | 0.16804 | 69.74 | 9.02% | 16.66% | 0.06575 | 0.05423 |
| 670/0.5/descending | 0.11694 | 81.20 | 20.15% | 24.69% | 0.06747 | 0.08602 |

At 0.5 m/s, 640 reduces ascent action variation and jerk but increases ascent tracking error; descent current leg contact rises 20.07%→23.17%, with lateral error 0.05477→0.05942 m. Neither 620 nor 640 dominates the other across these quality measures. The 0.3 m/s result matters especially because 620 already has two 17 cm/25 cm-tread ascent stalls(31/31/32) and a 3.62 s pause there.

An independent CPU motion analysis validates 72/72 matched case/seed comparisons at 0.5 m/s. Its representative 0.1 s traces have 5292 active post-warmup rows for 620 and 5282 for 640. Largest sampled named current forces are 341.6 N(620, FL_calf, case 15) and 468.7 N(640, FR_calf, case 13); retained-history maxima 420.1 N and 594.1 N. These peaks are from different cases and do not establish a controlled impact increase; they also show why lower action variation alone cannot certify gentle contact.

A concrete matched ascent tradeoff is seed 47/case 12: 620→640 current leg contact 13.38%→12.92%, action second RMS 0.18697→0.17208 and jerk 77.10→67.29 improve, while tracking RMSE 0.07308→0.08319 m/s worsens. At seed 47/case 9 descent, jerk 102.17→87.12 and tracking improve, but current leg contact 20.32%→26.19% and action second RMS 0.12187→0.12364 worsen.

## Casewise comparison at matched speed

| Speed | Pair(right-left) | Completion improved/equal/worse cases | Action 2 lower cases | Jerk lower cases | Current leg lower cases | Tracking lower cases | Both failure-free cases |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 0.3 | 640-620 | 1/21/2 | 24/24 | 20/24 | 12/24 | 10/24 | 21/24 |
| 0.3 | 670-620 | 1/22/1 | 23/24 | 18/24 | 12/24 | 16/24 | 22/24 |
| 0.3 | 670-640 | 2/22/0 | 11/24 | 14/24 | 14/24 | 21/24 | 22/24 |
| 0.5 | 640-620 | 0/24/0 | 20/24 | 19/24 | 8/24 | 13/24 | 24/24 |
| 0.5 | 670-620 | 0/24/0 | 20/24 | 23/24 | 13/24 | 13/24 | 24/24 |
| 0.5 | 670-640 | 0/24/0 | 7/24 | 14/24 | 18/24 | 14/24 | 24/24 |

All numeric deltas, per-seed completion/failure counts, gate results, longest pauses and contact sample denominators are in JSON. The table includes failed cases descriptively; its last column distinguishes complete failure-free traversal before treating low motion metrics as a quality improvement.

## Recorded 0.3 m/s failures

620 case 8, asc, 17 cm rise/25 cm tread/0 cm nose: completion seeds 31/31/32; final geometry gate=True; max pause 3.620 s; terminal root x values 2.0170 m(seed 11, env 271), 2.0145 m(seed 29, env 277).

640 case 15, desc, 20 cm rise/27 cm tread/0 cm nose: completion seeds 30/30/32; final geometry gate=False; max pause 3.600 s; terminal root x values 2.3995 m(seed 11, env 504), 2.4127 m(seed 11, env 511), 2.4107 m(seed 29, env 496), 2.4001 m(seed 29, env 506).

640 case 23, desc, 20 cm rise/25 cm tread/2 cm nose: completion seeds 31/32/32; final geometry gate=True; max pause 0.140 s; terminal root x values 1.8433 m(seed 11, env 752).

670 case 15, desc, 20 cm rise/27 cm tread/0 cm nose: completion seeds 32/30/32; final geometry gate=False; max pause 3.540 s; terminal root x values 2.3934 m(seed 29, env 485), 2.4166 m(seed 29, env 495).

The independent 620-versus 670 low-speed motion review finds 72 matched case/seed pairs and 71 eligible comparisons under the saved matching evidence and case/seed 95% gates. The excluded seed 29/case 15 changes 32/32→30/32; its current leg fraction drops 3.04 percentage points and action second RMS by 0.001273, while jerk increases 4.82 m/s³. That lower contact/action on a failed, truncated episode cannot establish smoother competent traversal. All-env policy-measurement exposures differ: 1444290 samples(620), 1425422(670).

The 640 seed 11/case 23 failure is an aggregate fall flag with zero reported base contacts; its recorded env 752 has no representative force trace. The saved terminal positions alone cannot distinguish gravity fall, other genuine termination or specific impact. Do not label it confirmed physical toppling. The 20 cm/27 cm descent stalls end with root x 2.39–2.42 m, after the 2.35 m last support face but before the 2.62 m final platform start; front feet reach the low platform while rear feet remain near the upper steps. This is late flight and final platform transition stalling. Endpoint placement does not prove its collision cause.

## Candidate choice

Recommend **contact620** as the contact-branch candidate for independent final validation. It is the only contact checkpoint passing every case/seed at both speeds. The concentrated 20 cm descent failures exclude contact640 and contact670 under the unchanged gate, even when their action, jerk or tracking metrics improve.

contact620 still has two 17 cm/25 cm ascent stalls and a 3.62 s pause at 0.3 m/s. This selection prioritizes traversal with recorded motion limits. It does not certify smoothness or real robot readiness. The matched faithful control is complete in `stair-matched-contact-ablation.md`: faithful670 passes both speeds, while faithful620 fails at 0.3 m/s. The same-batch contact620 low-speed recheck retains its case/seed outcome signatures and two stalls. Keep contact620 and faithful670 as candidates for independent final comparison; the tuning matrix does not select a universal smoothness winner.

The saved state checks include geometry, root positions, aggregate pose summaries, headings, thresholds, inference controller and foot readbacks. Full per-env initial quaternions are unavailable; equal aggregate summaries are not full-state matching. Nominal foot readbacks are fixed 0.8/0.6/0; reset seeds do not create independent startup material samples. Source commits and dirty state are retained per run.

Current force is the latest net-normal-force vector norm at a 20 ms policy boundary, including horizontal riser normals. History 3 at 5 ms retains ages 0/5/10 ms and can omit first-substep-only contacts. Any-leg fraction is presence, not sustained scraping, severity or the reward's count of contacting bodies. Current/history contact-foot denominators differ, and foot-link horizontal speed is a slip proxy.

## Same-batch matched recheck

The subsequent contact620 low-speed run shares the matched faithful/control evaluation construction. It reproduces the original per-case/seed completion, fall/stall/escape/base counts, gate results and failure seed/case/environment identifiers. Its original results remain above; the later run and matching checks are recorded in JSON. Identical outcome signatures do not establish identical continuous metrics or deterministic GPU execution.
