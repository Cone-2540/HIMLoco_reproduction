# Bootstrap120 independent staircase evaluation

This analysis uses frozen-checkpoint evaluation at 0.3 m/s, randomized initial poses, and reset seeds 11, 29, 47. Each case has 32 environments per seed. Dynamics are fixed; startup terrain/material choices are not resampled between reset seeds. Training diagnostics are not used as validation.

The 120-update policy completes 94/96 of the six-step 8 cm ascent flights and all 96/96 descent flights. Its worst ascent seed is 30/32 (93.75%), so it still fails the final per-seed 95% criterion. In contrast to the faithful first run (0/96 ascent, stalled at the first riser), every trial now reaches root x ≥1.3 m. The two remaining stalls occur at maximum root x=2.584 m and 1.598 m, in the later flight and middle section, respectively.

| Case | Model60 pooled / worst seed | Model100 pooled / worst seed | Model120 pooled / worst seed |
|---|---|---|---|
| 2.5 cm asc | 46/96 (47.92%) / 43.75% | 60/96 (62.50%) / 53.12% | 72/96 (75.00%) / 68.75% |
| 2.5 cm desc | 96/96 (100.00%) / 100.00% | 96/96 (100.00%) / 100.00% | 96/96 (100.00%) / 100.00% |
| 5 cm asc | 23/96 (23.96%) / 9.38% | 44/96 (45.83%) / 43.75% | 87/96 (90.62%) / 81.25% |
| 5 cm desc | 96/96 (100.00%) / 100.00% | 96/96 (100.00%) / 100.00% | 96/96 (100.00%) / 100.00% |
| 8 cm asc | 17/96 (17.71%) / 12.50% | 93/96 (96.88%) / 93.75% | 94/96 (97.92%) / 93.75% |
| 8 cm desc | 96/96 (100.00%) / 100.00% | 96/96 (100.00%) / 100.00% | 96/96 (100.00%) / 100.00% |
| 16 cm asc | 0/96 (0.00%) / 0.00% | 0/96 (0.00%) / 0.00% | 0/96 (0.00%) / 0.00% |
| 16 cm desc | 1/96 (1.04%) / 0.00% | 4/96 (4.17%) / 0.00% | 4/96 (4.17%) / 0.00% |

For model120, the 2.5 cm ascent has 24 stalls; 23 reach root x ≥2.8 m, the final platform start. The 5 cm ascent has 8 stalls; 7 reach that same platform start. Root position alone does not certify full traversal: the seed47 2.5 cm representative ends at root x≈2.975 m with rear feet x≈2.660/2.481 m, still on the last steps, and measured forward speed near zero despite the 0.3 m/s command. These are mostly actual rear-leg/end-of-flight transition failures, not merely a final-goal threshold rejecting an already completed flight.

The 16 cm ascent remains a first-riser problem: all 96 stall and maximum root positions span approximately 0.772–0.960 m, before the first riser at 1.0 m. The 16 cm descent completes only 4/96, with 66 falls, 24 stalls and 2 lateral escapes. This is a material regression from the earlier faithful 100-update policy, which completed 88/96 of that descent case. The bootstrap result therefore improves 8 cm capability without establishing broad staircase robustness.

All model120 trials report zero nonfinite states, invalid physics states, invalid starts, base-contact environments and timeout failures. The 8 cm ascent case maximum pause durations are 1.08, 1.60 and 3.54 s for seeds11/29/47. Case-level maximum pause is not necessarily the pause of the plotted representative environment. No smoothness certification follows from traversal counts or action-change curves.

Artifacts:

- `stair-bootstrap120-evaluation.{json,csv,md}`: all 3 candidates, 8 cases and 3 seeds (72 case/seed rows), including every failed case, recorded thresholds and worst-seed summaries.
- `stair-bootstrap120-checkpoint-comparison.{png,pdf}`: pooled and worst-seed completion, side by side.
- `stair-bootstrap120-8cm-case4-asc-seed29.{png,pdf}` and `stair-bootstrap120-8cm-case5-desc-seed29.{png,pdf}`: actual recorded representative first-episode telemetry.
- `stair-bootstrap120-failure-locations.json`: per-environment failure locations and last recorded representative states. No foot trajectory is fabricated for failed environments that were not recorded.

A useful next experiment should address rear-leg transitions near the end of smaller flights and continue ascent curriculum toward larger risers, while retaining held-out 16 cm descent to expose regressions. Specific reward/step-height changes remain hypotheses until tested in matched runs.
