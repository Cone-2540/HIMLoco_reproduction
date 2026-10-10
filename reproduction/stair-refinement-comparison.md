# Stair refinement comparison: hard520, hard570, contact620

All results below use 0.3 m/s commands, six-step flights, width 1.2 m, seeds 11/29/47, and 32 environments per case/seed. The first 12 cases are standard stairs; the last 12 tune higher/nosed stairs. The final gate applies to each case/seed: 31/32 passes the 95% completion requirement; 30/32 fails. No acceptance threshold is changed.

| Checkpoint / scope | Completed | Unique failures | Falls | Stalls | Escapes | Base history / current | Worst case/seed | Final all-case pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| standard370 / standard | 1152/1152 | 0 | 0 | 0 | 0 | 0 / — | 32/32 | True |
| hard520 / standard | 1067/1152 | 85 | 0 | 85 | 0 | 0 / 0 | 10/32 | False |
| hard520 / hard | 1084/1152 | 68 | 0 | 68 | 0 | 0 / 0 | 16/32 | False |
| hard570 / standard | 1079/1152 | 73 | 7 | 34 | 33 | 6 / 5 | 21/32 | False |
| hard570 / hard | 1110/1152 | 42 | 1 | 41 | 0 | 1 / 0 | 22/32 | False |
| contact620 / standard | 1150/1152 | 2 | 0 | 2 | 0 | 0 / 0 | 31/32 | True |
| contact620 / hard | 1152/1152 | 0 | 0 | 0 | 0 | 0 / 0 | 32/32 | True |

Failure flags can overlap. In hard570, seed 29, env 22 is both a fall and a lateral escape; summing failure categories would overcount. All new runs finish their recorded first episodes before the 30 s budget; standard370 uses 25 s.

## Standard capability regression

standard370 previously completed 1152/1152 at this speed, with every case/seed 32/32 and zero falls, stalls, escapes or base contacts. hard570 drops to 1079/1152: 8 cm ascent 72/96, 12 cm 74/96, 14 cm 87/96, 16 cm 82/96, 17 cm/25 cm-tread 92/96. All standard descents and the 17 cm/40 cm-tread ascent remain 96/96. hard520 drops to 1067/1152, particularly 14 cm ascent 34/96 and 16 cm 76/96; it preserves zero falls and escapes.

The 46 hard570 noncompletions in 8 cm/12 cm ascent all end on +y: root y 0.219–0.660 m. 36 end with root x on or after the goal-platform start. Sparse successful traces also drift toward +y while yaw remains close to zero. Lane/support loss is a concrete late-traversal problem, not a completion-budget shortage. Escape can be triggered by a foot beyond the lane while the root remains inside it.

Relative to standard370, hard570 improves action second-difference RMS in only 3/12 standard cases and root jerk in 6/12; tracking RMSE and history leg-contact fraction are worse in all 12. These are trajectory-level comparisons with early termination, not certified smoothness or a controlled training ablation.

## Same-batch hard570 versus hard520

hard570 completes 1110/1152 hard cases versus 1084/1152 for hard520. The 3 cm nosing ascent improves 55/96→76/96; 1 cm nosing 89→92; 20 cm/25 cm-tread/2 cm-nose ascent 89→93. The 2 cm nosing ascent stays 84/96 and hard570 adds one fall/base-history contact. 18 cm ascent regresses 96→94; 20 cm non-nosed ascent and all hard descents except the single failed 20 cm/nosed descent remain 96/96.

Across all 24 cases, hard570 adds 38 completions but also 8 falls and 33 escape flags. Its hard-case action second-difference RMS is lower in 7/12 and jerk lower in 9/12, while current leg-contact fraction is lower in 5/12. Current foot-slip proxy and lateral error are worse in all 12 hard cases. Keep both checkpoints and the standard370 baseline; hard570 is not a universal replacement.

| Case | Direction | Rise / tread / nose (cm) | hard520 seed 11/29/47 | hard570 seed 11/29/47 | contact620 seed 11/29/47 |
| --- | --- | --- | --- | --- | --- |
| 0 | asc | 8/30/0 | 32/32/32 | 23/23/26 | 32/32/32 |
| 1 | desc | 8/30/0 | 32/32/32 | 32/32/32 | 32/32/32 |
| 2 | asc | 12/30/0 | 31/32/32 | 21/26/27 | 32/32/32 |
| 3 | desc | 12/30/0 | 32/32/32 | 32/32/32 | 32/32/32 |
| 4 | asc | 14/27/0 | 12/10/12 | 28/30/29 | 32/32/32 |
| 5 | desc | 14/27/0 | 32/32/32 | 32/32/32 | 32/32/32 |
| 6 | asc | 16/27/0 | 25/27/24 | 28/26/28 | 32/32/32 |
| 7 | desc | 16/27/0 | 32/32/32 | 32/32/32 | 32/32/32 |
| 8 | asc | 17/25/0 | 32/31/31 | 32/30/30 | 31/31/32 |
| 9 | desc | 17/25/0 | 32/32/32 | 32/32/32 | 32/32/32 |
| 10 | asc | 17/40/0 | 32/32/32 | 32/32/32 | 32/32/32 |
| 11 | desc | 17/40/0 | 32/32/32 | 32/32/32 | 32/32/32 |
| 12 | asc | 18/27/0 | 32/32/32 | 30/32/32 | 32/32/32 |
| 13 | desc | 18/27/0 | 32/32/32 | 32/32/32 | 32/32/32 |
| 14 | asc | 20/27/0 | 32/32/32 | 32/32/32 | 32/32/32 |
| 15 | desc | 20/27/0 | 32/32/32 | 32/32/32 | 32/32/32 |
| 16 | asc | 17/27/1 | 27/31/31 | 30/31/31 | 32/32/32 |
| 17 | desc | 17/27/1 | 32/32/32 | 32/32/32 | 32/32/32 |
| 18 | asc | 17/27/2 | 29/28/27 | 29/29/26 | 32/32/32 |
| 19 | desc | 17/27/2 | 32/32/32 | 32/32/32 | 32/32/32 |
| 20 | asc | 17/27/3 | 16/22/17 | 25/29/22 | 32/32/32 |
| 21 | desc | 17/27/3 | 32/32/32 | 32/32/32 | 32/32/32 |
| 22 | asc | 20/25/2 | 31/27/31 | 31/31/31 | 32/32/32 |
| 23 | desc | 20/25/2 | 32/32/31 | 31/32/32 | 32/32/32 |

## contact620 interim adaptation

This checkpoint is 50 updates after hard570. Training adds leg_contacts=-0.1 on eight thigh/calf bodies at a strict 1 N normal-force-norm threshold; feet/base/hips are excluded. This is a Go2 adaptation: the released Go1 collision reward weight is zero. The penalty counts bodies from retained history, whereas evaluator leg-contact fraction records whether any selected body contacts. Both PPO and HIM estimator retain Adam state and use fixed 0.0001 after the override, compared with the previous fixed 0.0003 rate. The starting terrain level also changes from 0 to 4. Reward, learning rate and starting curriculum change together, so comparison with hard570 alone is not an isolated contact-penalty ablation. The separate faithful control uses the same lower rate, starting level and update budget as the contact branch.

contact620 completes 2302/2304 versus hard570 2189/2304; worst case/seed 31/32; final gate passed. It records 0 falls, 2 stalls, 0 escape flags and 0/0 history/current base-contact environments.

standard: completion 1079→1150; worst case/seed 31/32; maxpause 3.760→3.620 s. Macro mean current leg-contact 31.33%→17.78%; current slip proxy 21.47%→20.37%; action second-difference RMS 0.08568→0.08077; jerk 47.76→42.40 m/s³.

hard: completion 1110→1152; worst case/seed 32/32; maxpause 3.720→0.640 s. Macro mean current leg-contact 35.77%→21.49%; current slip proxy 20.52%→19.96%; action second-difference RMS 0.10107→0.09402; jerk 68.26→62.72 m/s³.

The two failures are case 8, 17 cm rise/25 cm tread/no nose ascent: seed 11, env 271 and seed 29, env 277. Their terminal root x is 2.0170 m and 2.0145 m, before the last 2.25 m riser; both are stalls, not final-platform stalls. Seed completion is 31/31/32. The 3.62 s maximum pause leaves motion_improvement_needed=True, despite traversal_passed=True. This also remains a two-environment regression from standard370's 96/96 for the geometry.

Versus hard570, current and history leg-contact fractions are lower in all 24 cases. Action second-difference RMS and root jerk each improve in 17/24, tracking RMSE in 22/24, and lateral error in 23/24. Current slip proxy improves in 17/24. Seven action cases worsen: descents, with indices 9, 11, 13, 15, 17, 19, 21. The jerk worsening indices are 7, 11, 13, 15, 17, 19, 21. All are descents. Reduced contact frequency does not imply universal impact or action improvement.

Descents still have current leg-contact fractions 17.4–34.2% across the 24-case matrix. Sparse contact620 traces retain sizable individual contacts, including FR_calf 489.6 N in 18 cm descent and FR_thigh 291.9 N in 20 cm descent. These are sample peaks from the recorded environments, not whole-batch maximum body forces or damage measurements.

contact620 is a promising adaptation candidate for the recorded 0.3 m/s scope. These 24 cases have been used for tuning and regression; passing this matrix does not provide an independent final evaluation of the selected candidate. Preserve standard370, hard520 and hard570 and the differing scopes; a new speed, material draw or visual-quality claim needs its own evidence.

## Contact/body-force evidence and limits

Current-force and history arrays follow recorded leg_body_names: FL/FR/RL/RR thigh, then FL/FR/RL/RR calf. The sensor indices are matched by body name; training reward-body order differs and must also be joined by names. Report JSON validates finite eight-element arrays and history peak≥current. At each recorded row, the maximum over the eight selected bodies matches the corresponding aggregate current/history shank force. A separate CPU review independently reproduced all three row counts and found zero discrepancies.

| Checkpoint | Active post-first-second traced environment rows | Force-field discrepancies |
| --- | ---: | ---: |
| hard520 | 8820 | 0 |
| hard570 | 8941 | 0 |
| contact620 | 9048 | 0 |

These sparse 0.1 s traces contain one environment per case/seed, not all 32. Their per-body hit fractions are attribution samples and cannot establish scraping duration. Full current/history contact metrics use all valid first-episode measurements after the first second. History 3 at 5 ms retains 0/5/10 ms at a 20 ms policy boundary; the first-substep-only impact can be overwritten. Current normal forces include horizontal riser normals and exclude tangential friction force. Foot-link horizontal speed is a slip proxy with a separate contact-foot denominator.

## Matching and material provenance

hard520 and hard570 share the same 24-case construction, exactly equal per-env initial root positions, aggregate pose distributions, seed lists and contact metadata. contact620 uses the same 24 geometries; its pairing checks are in JSON. Per-env initial quaternions are never recorded. Against the old 12-case standard370 batch, geometry is exact and position differences are at most 1.91 µm, while aggregate initial pose records cover different environment counts. Do not describe that history regression as exact per-env heading matching.

Actual initial/final foot readbacks exist for standard370 and hard570: static friction 0.8, dynamic 0.6, restitution 0, zero dispersion; 768×4 new feet versus 384×4 older feet. contact620 initial readback matches these values; the completed report checks its final readback too. Candidate 520 shares the hard570 environment. No separate physical terrain-material readback is present. Three reset seeds leave startup material/dynamics fixed.

The report preserves case/seed counts and unique failure endpoints. A pause flag is not a smoothness certificate. Increased hard-stair capability must be judged with standard regression, lateral tracking, per-case minimum completion and contact/action/jerk tradeoffs together.

Sources: raw result paths, checkpoints, pairing checks, readback paths and numerical per-case metrics are in `stair-refinement-comparison.json`. Earlier `stair-hard520-analysis.md` and its artifacts are preserved.


## Subsequent matched faithful control

The later `stair-matched-contact-ablation.md` is complete. It compares equal 50 and 100 updates from model570, with the same learning rate, Adam recovery, training seed and checked terrain/configuration controls. At 0.5 m/s all four policies complete 2304/2304. Contact reduces current leg contact in all 24 cases at both update counts, with different quality tradeoffs: after 50 updates most action/slip metrics worsen; after 100 updates action variation and jerk mostly improve while descent lateral and tracking errors increase.

At 0.3 m/s, faithful620 completes 2292/2304 and fails three case/seed gates. faithful670 and contact620 each complete 2302/2304 and pass all 72 case/seed gates, retaining two stalls and maximum pauses of 3.76 and 3.62 s. contact670 also completes 2302/2304, but two stalls concentrate in case 15/seed 29, only 30/32, so it fails the original gate. Keep contact620 and faithful670 for independent final comparison; this reused tuning matrix does not certify smoothness.

The original comparison against model570 changes reward, learning rate and maximum initial terrain level together. The matched control refines its interpretation without replacing its historical numeric evidence. One training seed and saved manifest/dirty-source limits support this realization; they do not establish broad reward causality or arbitrary stair generalization.
