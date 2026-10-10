# Easy-stair faithful baseline evaluation

Source: `isaaclab/logs/2026-10-11_01-21-27_easy100-core-checkpoints/result.json`
and its `candidates/` results. This report aggregates existing records; it does
not run additional simulation.

Each case uses 32 environments and reset seeds 11, 29 and 47, for 96 trials.
Initial poses, joint positions and velocities are randomized. Dynamics remain
nominal. Reset seeds do not resample startup terrain/material/dynamics.

| Checkpoint | Up 8 cm | Down 8 cm | Up 16 cm | Down 16 cm |
|---|---:|---:|---:|---:|
| 60 updates | 0/96 | 50/96 (52.08%) | 0/96 | 6/96 (6.25%) |
| 80 updates | 0/96 | 79/96 (82.29%) | 0/96 | 74/96 (77.08%) |
| 100 updates | 0/96 | 85/96 (88.54%) | 0/96 | 88/96 (91.67%) |

The final criterion is at least 95% completion, at most 5% each of falls,
stalls and lateral escapes, and zero base contact in each case and seed.
None of these candidates passes. A case with 32 trials needs at least 31
completions to exceed 95%; the best individual descent result is 30/32.

## Ascent failure location

All ascent trials stall, with zero falls and lateral escapes. For the
100-update checkpoint, the representative traces for all three seeds show:

- The first stair riser is at x = 1.000 m. Front-foot link centers stop at
  maximum recorded x = 0.98015–0.98031 m, consistent with their finite foot
  collision radius touching the riser.
- Once root x exceeds 0.65 m, the highest recorded foot-link center is only
  0.0236–0.0376 m above the ground, below both the 8 cm and 16 cm step tops.
- In the 8 cm, seed 29 representative trace, the final root x is 0.8966 m,
  forward speed is approximately −0.00010 m/s, all four feet are in contact,
  and the action second-difference RMS is approximately 0.0000105.
- The body remains near ground-level standing clearance. The policy gradually
  settles into a fixed pose instead of producing a lift and step over the riser.

These are physical first-step failures. The final-platform completion
threshold is not causing the ascent failure: the robot never reaches the
first stair. Trace values come from one representative environment per case
at 0.1 s cadence, so they are not exact extrema over every physics frame or
every environment.

## Coordinate and numerical checks

Ascent and descent both travel in positive x. Descent starts on the upper
landing; its terrain origin includes the starting platform height, making
the final relative z −0.48 m or −0.96 m. The seed 29, 16 cm descent trace
physically follows all six steps and reaches feet z near −0.96 m on the
final platform. This supports the direction, case mapping and relative
height convention.

All three candidates report zero nonfinite environments, invalid physics
environments, invalid starts and base-contact environments. No lateral
escapes occur. The zero-action control completes 0/384 trials. The current
scanner diagnostic shows genuine ground-height variation; there is no
evidence of the previously suspected sensor-height saturation.

## Next experiment

Preserve this faithful reward run as a baseline. A useful next experiment is
an ascent-focused curriculum with smaller first steps, increasing height
only after actual traversal. Evaluate its checkpoints on both easier
diagnostic steps and the existing 8/16 cm held-out flights.

The body-relative foot-clearance reward, upward-velocity penalty and
orientation penalty are plausible contributors to the low-lift, standing
solution. Their causal role is not established by these traces. Treat any
reward change as a separately named ablation with the same initialization
and validation cases.

Descent completion improves with training, but 16 cm descent pitch RMS is
approximately 0.34 rad and some environments fall. Low action variation
after an ascent stall does not demonstrate smooth stair motion. Motion
quality still requires video review and a comparison baseline.

## Artifacts

- `stair-easy100-evaluation-summary.json`: counts, seed results, metric
  ranges and exact representative trace evidence with source paths.
- `stair-easy100-checkpoint-comparison.png` / `.pdf`: candidate completion
  and ascent progress comparison.
- `stair-easy100-failure-case0-asc-seed29.png` / `.pdf`: 8 cm ascent failure.
- `stair-easy100-failure-case1-desc-seed29.png` / `.pdf`: 8 cm descent trace.
- `stair-easy100-failure-case2-asc-seed29.png` / `.pdf`: 16 cm ascent failure.
- `stair-easy100-failure-case3-desc-seed29.png` / `.pdf`: 16 cm descent trace.

The trace plots are reproducible with:

```bash
python3 reproduction/plot-stair-eval.py \
  isaaclab/logs/2026-10-11_01-21-27_easy100-core-checkpoints/result.json \
  --seed 29 --output reproduction/stair-easy100-failure
```
