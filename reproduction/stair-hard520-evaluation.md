# Recorded staircase evaluations

No models are selected and no thresholds are changed. Pooled completion counts all recorded
environments; minimum case/seed completion preserves the worst reset seed. A direction total
does not replace individual cases. Missing metrics remain unavailable. Material settings are
only reported when recorded; reset seeds do not imply fresh startup material samples.

## 1. 2026-10-11_03-43-07_hard520-interim-tuning (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_03-43-07_hard520-interim-tuning/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_03-13-12_stairs-hard-faithful570/model_520.pt` (source: result)
- Speed: 0.3 m/s; reset randomized: True; dynamics randomized: False; independent reset validation eligible: True.
- Minimum pooled case completion: 62.50%; minimum case/seed completion: 56.25%; observations complete: True.
- Reported evaluation passed: False; reported final traversal passed: False.
- Validation scope: randomized reset cases
- Recorded reset seeds: [11, 29, 47]; missing configured reset seeds: [].
- Seed/material sampling scope: reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds
- Material configuration: `{"domain_randomization_profile":null,"foot_material":null,"friction_override":null,"parameter_scope":"Material parameter ranges not recorded; inherited environment materials are unknown","seed_scope":"reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds","terrain_material":null}`
- Recorded thresholds: `{"evaluation":{"completion_fraction":0.9,"contact_force_n":1.0,"goal_foot_clearance_m":0.1,"goal_foot_height_tolerance_m":0.12,"maximum_base_clearance_m":0.6,"minimum_base_clearance_m":0.18,"minimum_num_envs":32,"slip_speed_m_s":0.1,"stall_progress_m":0.05,"stall_window_s":4.0,"upright_gravity_z":-0.8},"final_acceptance":{"completion_fraction":0.95,"maximum_base_contact_envs":0,"maximum_failure_fraction":0.05,"maximum_flight_pause_s_for_motion_flag":1.0}}`

| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | asc | 0.18 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 1 | desc | 0.18 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.03% | 0.080 | True |
| 2 | asc | 0.2 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.03% | 0.060 | True |
| 3 | desc | 0.2 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 1.90% | 1.400 | True |
| 4 | asc | 0.17 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.24% | 0.160 | True |
| 5 | desc | 0.17 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.17 / 0.27 | 11 | 27 / 32 | 84.38% | 0 | 5 | 0 | 0 | 9.26% | 3.800 | False |
| 7 | desc | 0.17 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.27 | 11 | 18 / 32 | 56.25% | 0 | 14 | 0 | 0 | 23.57% | 3.800 | False |
| 9 | desc | 0.17 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.2 / 0.25 | 11 | 28 / 32 | 87.50% | 0 | 4 | 0 | 0 | 7.13% | 2.660 | False |
| 11 | desc | 0.2 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 2.49% | 0.680 | True |
| 0 | asc | 0.18 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.33% | 0.600 | True |
| 1 | desc | 0.18 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.14% | 0.340 | True |
| 2 | asc | 0.2 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.09% | 0.080 | True |
| 3 | desc | 0.2 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.59% | 0.440 | True |
| 4 | asc | 0.17 / 0.27 | 29 | 29 / 32 | 90.62% | 0 | 3 | 0 | 0 | 4.34% | 3.680 | False |
| 5 | desc | 0.17 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.05% | 0.160 | True |
| 6 | asc | 0.17 / 0.27 | 29 | 29 / 32 | 90.62% | 0 | 3 | 0 | 0 | 5.42% | 3.640 | False |
| 7 | desc | 0.17 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.12% | 0.200 | True |
| 8 | asc | 0.17 / 0.27 | 29 | 22 / 32 | 68.75% | 0 | 10 | 0 | 0 | 20.03% | 3.820 | False |
| 9 | desc | 0.17 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.04% | 0.120 | True |
| 10 | asc | 0.2 / 0.25 | 29 | 29 / 32 | 90.62% | 0 | 3 | 0 | 0 | 6.64% | 3.780 | False |
| 11 | desc | 0.2 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 1.52% | 0.420 | True |
| 0 | asc | 0.18 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.07% | 0.120 | True |
| 1 | desc | 0.18 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.16% | 0.240 | True |
| 2 | asc | 0.2 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.06% | 0.080 | True |
| 3 | desc | 0.2 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.86% | 0.580 | True |
| 4 | asc | 0.17 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.11% | 0.120 | True |
| 5 | desc | 0.17 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.08% | 0.240 | True |
| 6 | asc | 0.17 / 0.27 | 47 | 28 / 32 | 87.50% | 0 | 4 | 0 | 0 | 7.04% | 3.720 | False |
| 7 | desc | 0.17 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.27 | 47 | 20 / 32 | 62.50% | 0 | 12 | 0 | 0 | 21.64% | 3.820 | False |
| 9 | desc | 0.17 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.05% | 0.160 | True |
| 10 | asc | 0.2 / 0.25 | 47 | 30 / 32 | 93.75% | 0 | 2 | 0 | 0 | 5.58% | 3.500 | False |
| 11 | desc | 0.2 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 2.52% | 0.840 | True |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.600 |
| 1 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.340 |
| 2 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.080 |
| 3 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 1.400 |
| 4 | 96.88% | 90.62% | 29 | 0.00% | 9.38% | 0.00% | 0.00% | 3.680 |
| 5 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.240 |
| 6 | 87.50% | 84.38% | 11 | 0.00% | 15.62% | 0.00% | 0.00% | 3.800 |
| 7 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.200 |
| 8 | 62.50% | 56.25% | 11 | 0.00% | 43.75% | 0.00% | 0.00% | 3.820 |
| 9 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.160 |
| 10 | 90.62% | 87.50% | 11 | 0.00% | 12.50% | 0.00% | 0.00% | 3.780 |
| 11 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.840 |

## 2. 0_model_370 (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_03-43-07_hard520-interim-tuning/candidates/0_model_370/result.json`
- Checkpoint: `/workspace/himloco/artifacts/go2-stairs-standard370/model_370.pt` (source: result)
- Speed: 0.3 m/s; reset randomized: True; dynamics randomized: False; independent reset validation eligible: True.
- Minimum pooled case completion: 0.00%; minimum case/seed completion: 0.00%; observations complete: True.
- Reported evaluation passed: False; reported final traversal passed: False.
- Validation scope: randomized reset cases
- Recorded reset seeds: [11, 29, 47]; missing configured reset seeds: [].
- Seed/material sampling scope: reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds
- Material configuration: `{"domain_randomization_profile":null,"foot_material":null,"friction_override":null,"parameter_scope":"Material parameter ranges not recorded; inherited environment materials are unknown","seed_scope":"reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds","terrain_material":null}`
- Recorded thresholds: `{"evaluation":{"completion_fraction":0.9,"contact_force_n":1.0,"goal_foot_clearance_m":0.1,"goal_foot_height_tolerance_m":0.12,"maximum_base_clearance_m":0.6,"minimum_base_clearance_m":0.18,"minimum_num_envs":32,"slip_speed_m_s":0.1,"stall_progress_m":0.05,"stall_window_s":4.0,"upright_gravity_z":-0.8},"final_acceptance":{"completion_fraction":0.95,"maximum_base_contact_envs":0,"maximum_failure_fraction":0.05,"maximum_flight_pause_s_for_motion_flag":1.0}}`

| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | asc | 0.18 / 0.27 | 11 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 0.00% | 0.000 | True |
| 1 | desc | 0.18 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.02% | 0.060 | True |
| 2 | asc | 0.2 / 0.27 | 11 | 9 / 32 | 28.12% | 0 | 23 | 0 | 0 | 6.35% | 0.760 | False |
| 3 | desc | 0.2 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.20% | 0.120 | True |
| 4 | asc | 0.17 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 26.18% | 1.400 | True |
| 5 | desc | 0.17 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.17 / 0.27 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 70.35% | 3.820 | False |
| 7 | desc | 0.17 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.27 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 69.04% | 3.840 | False |
| 9 | desc | 0.17 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.2 / 0.25 | 11 | 0 / 32 | 0.00% | 2 | 30 | 0 | 1 | 67.12% | 2.700 | False |
| 11 | desc | 0.2 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.15% | 0.140 | True |
| 0 | asc | 0.18 / 0.27 | 29 | 30 / 32 | 93.75% | 0 | 2 | 0 | 0 | 0.00% | 0.000 | False |
| 1 | desc | 0.18 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.2 / 0.27 | 29 | 9 / 32 | 28.12% | 0 | 23 | 0 | 0 | 4.62% | 0.660 | False |
| 3 | desc | 0.2 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.20% | 0.180 | True |
| 4 | asc | 0.17 / 0.27 | 29 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 27.52% | 3.700 | True |
| 5 | desc | 0.17 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.17 / 0.27 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 70.02% | 3.820 | False |
| 7 | desc | 0.17 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.27 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 67.34% | 3.820 | False |
| 9 | desc | 0.17 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.2 / 0.25 | 29 | 0 / 32 | 0.00% | 1 | 31 | 0 | 0 | 72.90% | 2.900 | False |
| 11 | desc | 0.2 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.11% | 0.100 | True |
| 0 | asc | 0.18 / 0.27 | 47 | 30 / 32 | 93.75% | 0 | 2 | 0 | 0 | 0.00% | 0.000 | False |
| 1 | desc | 0.18 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.01% | 0.020 | True |
| 2 | asc | 0.2 / 0.27 | 47 | 13 / 32 | 40.62% | 0 | 19 | 0 | 0 | 4.53% | 0.780 | False |
| 3 | desc | 0.2 / 0.27 | 47 | 31 / 32 | 96.88% | 1 | 0 | 0 | 0 | 0.77% | 0.320 | True |
| 4 | asc | 0.17 / 0.27 | 47 | 29 / 32 | 90.62% | 2 | 1 | 0 | 2 | 29.69% | 3.680 | False |
| 5 | desc | 0.17 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.17 / 0.27 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 73.36% | 3.820 | False |
| 7 | desc | 0.17 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.27 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 69.03% | 3.820 | False |
| 9 | desc | 0.17 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.2 / 0.25 | 47 | 0 / 32 | 0.00% | 3 | 29 | 0 | 1 | 64.59% | 3.500 | False |
| 11 | desc | 0.2 / 0.25 | 47 | 31 / 32 | 96.88% | 1 | 0 | 0 | 0 | 0.00% | 0.000 | True |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 94.79% | 93.75% | 29, 47 | 0.00% | 6.25% | 0.00% | 0.00% | 0.000 |
| 1 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.060 |
| 2 | 32.29% | 28.12% | 11, 29 | 0.00% | 71.88% | 0.00% | 0.00% | 0.780 |
| 3 | 98.96% | 96.88% | 47 | 3.12% | 0.00% | 0.00% | 0.00% | 0.320 |
| 4 | 95.83% | 90.62% | 47 | 6.25% | 3.12% | 0.00% | 6.25% | 3.700 |
| 5 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 6 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 3.820 |
| 7 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 8 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 3.840 |
| 9 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 10 | 0.00% | 0.00% | 11, 29, 47 | 9.38% | 96.88% | 0.00% | 3.12% | 3.500 |
| 11 | 98.96% | 96.88% | 47 | 3.12% | 0.00% | 0.00% | 0.00% | 0.140 |

