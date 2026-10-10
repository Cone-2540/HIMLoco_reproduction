# Recorded staircase evaluations

No models are selected and no thresholds are changed. Pooled completion counts all recorded
environments; minimum case/seed completion preserves the worst reset seed. A direction total
does not replace individual cases. Missing metrics remain unavailable. Material settings are
only reported when recorded; reset seeds do not imply fresh startup material samples.

## 1. 2026-10-11_02-43-45_standard270-matched-speed05 (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_02-43-45_standard270-matched-speed05/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_02-15-45_stairs-standard-faithful270/model_270.pt` (source: result)
- Speed: 0.5 m/s; reset randomized: True; dynamics randomized: False; independent reset validation eligible: True.
- Minimum pooled case completion: 98.96%; minimum case/seed completion: 96.88%; observations complete: True.
- Reported evaluation passed: True; reported final traversal passed: True.
- Validation scope: randomized reset cases
- Recorded reset seeds: [11, 29, 47]; missing configured reset seeds: [].
- Seed/material sampling scope: reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds
- Material configuration: `{"domain_randomization_profile":null,"foot_material":null,"friction_override":null,"parameter_scope":"Material parameter ranges not recorded; inherited environment materials are unknown","seed_scope":"reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds","terrain_material":null}`
- Recorded thresholds: `{"evaluation":{"completion_fraction":0.9,"contact_force_n":1.0,"goal_foot_clearance_m":0.1,"goal_foot_height_tolerance_m":0.12,"maximum_base_clearance_m":0.6,"minimum_base_clearance_m":0.18,"minimum_num_envs":32,"slip_speed_m_s":0.1,"stall_progress_m":0.05,"stall_window_s":4.0,"upright_gravity_z":-0.8},"final_acceptance":{"completion_fraction":0.95,"maximum_base_contact_envs":0,"maximum_failure_fraction":0.05,"maximum_flight_pause_s_for_motion_flag":1.0}}`

| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | asc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.42% | 0.220 | True |
| 1 | desc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 7 | desc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.99% | 0.360 | True |
| 9 | desc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.56% | 0.720 | True |
| 11 | desc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.58% | 0.260 | True |
| 1 | desc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.01% | 0.020 | True |
| 7 | desc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 29 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 3.13% | 3.680 | True |
| 9 | desc | 0.17 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.73% | 0.240 | True |
| 1 | desc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 7 | desc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.82% | 0.540 | True |
| 9 | desc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.260 |
| 1 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 3 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 4 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 5 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 6 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.020 |
| 7 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 8 | 98.96% | 96.88% | 29 | 0.00% | 3.12% | 0.00% | 0.00% | 3.680 |
| 9 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 10 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.720 |
| 11 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |

## 2. 0_model_240 (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_02-43-45_standard270-matched-speed05/candidates/0_model_240/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_02-15-45_stairs-standard-faithful270/model_240.pt` (source: result)
- Speed: 0.5 m/s; reset randomized: True; dynamics randomized: False; independent reset validation eligible: True.
- Minimum pooled case completion: 94.79%; minimum case/seed completion: 93.75%; observations complete: True.
- Reported evaluation passed: True; reported final traversal passed: False.
- Validation scope: randomized reset cases
- Recorded reset seeds: [11, 29, 47]; missing configured reset seeds: [].
- Seed/material sampling scope: reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds
- Material configuration: `{"domain_randomization_profile":null,"foot_material":null,"friction_override":null,"parameter_scope":"Material parameter ranges not recorded; inherited environment materials are unknown","seed_scope":"reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds","terrain_material":null}`
- Recorded thresholds: `{"evaluation":{"completion_fraction":0.9,"contact_force_n":1.0,"goal_foot_clearance_m":0.1,"goal_foot_height_tolerance_m":0.12,"maximum_base_clearance_m":0.6,"minimum_base_clearance_m":0.18,"minimum_num_envs":32,"slip_speed_m_s":0.1,"stall_progress_m":0.05,"stall_window_s":4.0,"upright_gravity_z":-0.8},"final_acceptance":{"completion_fraction":0.95,"maximum_base_contact_envs":0,"maximum_failure_fraction":0.05,"maximum_flight_pause_s_for_motion_flag":1.0}}`

| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | asc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 2.75% | 0.320 | True |
| 1 | desc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.35% | 0.180 | True |
| 7 | desc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 11 | 30 / 32 | 93.75% | 0 | 2 | 0 | 0 | 5.80% | 3.860 | False |
| 9 | desc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 2.95% | 0.320 | True |
| 1 | desc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.19% | 0.100 | True |
| 7 | desc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 29 | 30 / 32 | 93.75% | 0 | 2 | 0 | 0 | 5.86% | 3.840 | False |
| 9 | desc | 0.17 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 2.65% | 0.540 | True |
| 1 | desc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.59% | 0.160 | True |
| 7 | desc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 47 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 3.39% | 3.520 | True |
| 9 | desc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.540 |
| 1 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 3 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 4 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 5 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 6 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.180 |
| 7 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 8 | 94.79% | 93.75% | 11, 29 | 0.00% | 6.25% | 0.00% | 0.00% | 3.860 |
| 9 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 10 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 11 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |

