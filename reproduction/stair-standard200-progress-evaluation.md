# Recorded staircase evaluations

No models are selected and no thresholds are changed. Pooled completion counts all recorded
environments; minimum case/seed completion preserves the worst reset seed. A direction total
does not replace individual cases. Missing metrics remain unavailable. Material settings are
only reported when recorded; reset seeds do not imply fresh startup material samples.

## 1. 2026-10-11_02-29-54_standard200-core-progress (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_02-29-54_standard200-core-progress/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_02-15-45_stairs-standard-faithful270/model_200.pt` (source: config)
- Speed: 0.3 m/s; reset randomized: True; dynamics randomized: False; independent reset validation eligible: False.
- Minimum pooled case completion: 90.62%; minimum case/seed completion: 90.62%; observations complete: True.
- Reported evaluation passed: True; reported final traversal passed: False.
- Validation scope: randomized reset cases
- Recorded reset seeds: [29]; missing configured reset seeds: [].
- Seed/material sampling scope: reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds
- Material configuration: `{"domain_randomization_profile":null,"foot_material":null,"friction_override":null,"parameter_scope":"Material parameter ranges not recorded; inherited environment materials are unknown","seed_scope":"reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds","terrain_material":null}`
- Recorded thresholds: `{"evaluation":{"completion_fraction":0.9,"contact_force_n":1.0,"goal_foot_clearance_m":0.1,"goal_foot_height_tolerance_m":0.12,"maximum_base_clearance_m":0.6,"minimum_base_clearance_m":0.18,"minimum_num_envs":32,"slip_speed_m_s":0.1,"stall_progress_m":0.05,"stall_window_s":4.0,"upright_gravity_z":-0.8},"final_acceptance":{"completion_fraction":0.95,"maximum_base_contact_envs":0,"maximum_failure_fraction":0.05,"maximum_flight_pause_s_for_motion_flag":1.0}}`

| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | asc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 15.39% | 1.080 | True |
| 1 | desc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.16 / 0.27 | 29 | 29 / 32 | 90.62% | 0 | 3 | 0 | 0 | 14.29% | 3.600 | False |
| 3 | desc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.08% | 0.100 | True |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 100.00% | 100.00% | 29 | 0.00% | 0.00% | 0.00% | 0.00% | 1.080 |
| 1 | 100.00% | 100.00% | 29 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 90.62% | 90.62% | 29 | 0.00% | 9.38% | 0.00% | 0.00% | 3.600 |
| 3 | 100.00% | 100.00% | 29 | 0.00% | 0.00% | 0.00% | 0.00% | 0.100 |

