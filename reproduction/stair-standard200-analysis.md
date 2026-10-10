# Standard200 single-seed staircase progress

Independent frozen-checkpoint evaluation of `stairs-standard-faithful270/model_200.pt`: command 0.3 m/s, reset seed 29, randomized starting pose, nominal dynamics, 32 environments per case. This is an intermediate single-seed result; independent multi-seed validation is still required. Training diagnostics do not enter these counts.

| Case | Complete | Falls | Stalls | Escapes | Final 95% traversal gate |
|---|---:|---:|---:|---:|---|
| 8 cm asc | 32/32 | 0 | 0 | 0 | PASS |
| 8 cm desc | 32/32 | 0 | 0 | 0 | PASS |
| 16 cm asc | 29/32 | 0 | 3 | 0 | FAIL |
| 16 cm desc | 32/32 | 0 | 0 | 0 | PASS |

The 16 cm ascent now completes 29/32 full six-step flights and final-platform dwell. The reported evaluation `passed=True` uses a 90% threshold; it does not satisfy the separately recorded final 95% threshold. Three stalls (9.375%) exceed the final 5% failure limit. The 16 cm descent completes 32/32 with no falls or lateral escapes in this seed.

## Three ascent stalls

| Env | Exact maximum displacement from reset (m) | Conservative maximum course root x (m) | Location supported by current data |
|---|---:|---|---|
| 68 | 2.765933514 | [2.687224, 2.845400] | Final-platform area after the last riser |
| 69 | 1.225912929 | [1.147203, 1.305379] | First-to-second-step area |
| 90 | 2.691299915 | [2.612590, 2.770766] | End-of-flight transition / final-platform edge |

The course first riser is x=1.00 m; subsequent risers are 1.27, 1.54, 1.81, 2.08 and 2.35 m. The final platform begins at 2.62 m and the root goal is 3.27 m. The recorded `per_env.max_progress_m` is maximum displacement from each randomized reset, not exact course x. Above ranges add the batch initial root-x range [−0.078710, +0.079466] m; individual failed-env initial x was not recorded. All three upper bounds remain below the root goal.

Trace environments are only 0/32/64/96. Failed env68/69/90 have no foot trajectory. Their rear-foot positions, lift heights and contact mechanism cannot be quantified from this run; an end-of-flight root location is insufficient to prove rear-leg obstruction. These are two later-flight stalls and one early-flight stall, without claiming a specific foot cause.

## Successful representative foot motion

The plotted 16 cm ascent env64 completes at 11.76 s. At the last active sample, 11.72 s, root x=3.4067 m and z=1.2031 m; all feet have x≥3.1290 m, beyond final-platform start 2.62 m. The rear-positioned pair has x≈3.129/3.230 m and z≈0.983/0.984 m, consistent with foot-link centers above the +0.96 m platform.

At the first recorded samples with each foot x≥1.03 m, foot-link center z is 0.256, 0.184, 0.183 and 0.184 m (times 3.22, 3.02, 4.92 and 4.32 s). This supports successful crossing of the 16 cm first riser. These are center heights at 0.1 s sample cadence, not exact swing peaks or toe-clearance measurements. They describe successful env64, not the three untraced failures.

Descent env96 completes at 13.74 s. At 13.72 s, all feet x≥3.1471 m and feet z≈−0.903 to −0.937 m above the final −0.96 m landing; root z≈−0.7173 m. Both plots show genuine full-flight trajectories rather than an automatic reset being counted as success.

## Motion metrics

All rows below use seed 29, 0.3 m/s command and the same 0.02 s policy cadence. Metrics cover the active first episode and exclude the first second for motion statistics. The 16 cm/27 cm-tread rows and bootstrap 8 cm/30 cm-tread rows have different geometry; they do not establish motion-quality improvement. The two 8 cm model rows allow a geometry-matched descriptive comparison, though evaluation batches and startup material draws differ.

| Model / case | Flight pause fraction | Case max pause s | Action first RMS | Action second RMS | Acceleration RMS m/s² | Jerk RMS m/s³ | Roll RMS rad | Pitch RMS rad |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| bootstrap120 8 cm asc | 0.0258 | 1.60 | 0.1896 | 0.1028 | 1.055 | 46.18 | 0.0360 | 0.1582 |
| bootstrap120 8 cm desc | 0.0000 | 0.00 | 0.1375 | 0.0674 | 0.860 | 31.47 | 0.0394 | 0.1448 |
| standard200 8 cm asc | 0.1539 | 1.08 | 0.1910 | 0.1096 | 1.372 | 51.46 | 0.1134 | 0.1981 |
| standard200 8 cm desc | 0.0000 | 0.00 | 0.1507 | 0.0730 | 0.916 | 35.66 | 0.0473 | 0.1300 |
| standard200 16 cm asc | 0.1429 | 3.60 | 0.2316 | 0.1351 | 1.805 | 85.29 | 0.1033 | 0.3089 |
| standard200 16 cm desc | 0.0008 | 0.10 | 0.1648 | 0.0970 | 1.401 | 67.02 | 0.0487 | 0.2724 |

The 16 cm ascent case maximum pause is 3.60 s across all 32 environments, and pause fraction is 14.29%; descent maximum pause is 0.10 s and fraction 0.080%. Case maximum pauses and action RMS in the plot titles summarize all environments; the successful single-env curve can differ.

On the same 8 cm geometry, standard200 ascent action second-difference RMS is 0.1096 versus bootstrap120 0.1028; cumulative pause fraction increases from 2.58% to 15.39% and roll RMS from 0.0360 to 0.1134 rad, although the maximum individual pause shortens from 1.60 to 1.08 s. Descent action second RMS is 0.0730 versus 0.0674. Full traversal on 16 cm expands the observed capability in this seed without establishing smoother motion.

All 128 environments have finite/valid physics and valid starting states, zero base contact, zero falls, zero lateral escapes and zero timeout failures. Leg/thigh/calf contact is present: active-step fractions are 23.05% for 16 cm ascent and 32.31% for descent, with case peak contact force 936.8/468.3 N. This is distinct from base contact and merits video review before making motion-quality claims. No universal smoothness threshold or matching 16 cm baseline video has been checked.

## Artifacts and coordinate correction

- `stair-standard200-16cm-case2-asc-seed29.{png,pdf}` and `stair-standard200-16cm-case3-desc-seed29.{png,pdf}`: representative trajectories, annotated with original 90% versus final 95% gate and full-case aggregate metric scope.
- `stair-standard200-failures.json`: original displacement values, conservative course-x ranges, untraced foot-data limitations, representative foot samples and metric provenance.
- Earlier `stair-bootstrap120-analysis.md` and `stair-bootstrap120-failure-locations.json` have been corrected where displacement was called exact root x. Original values remain as `max_displacement_from_reset_m` with conservative reset-offset bounds. Recorded representative root/foot traces are actual course-relative coordinates and remain unchanged. Historical evaluations were not rerun.
