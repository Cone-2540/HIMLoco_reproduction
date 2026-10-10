# Recorded staircase evaluations

No models are selected and no thresholds are changed. Pooled completion counts all recorded
environments; minimum case/seed completion preserves the worst reset seed. A direction total
does not replace individual cases. Missing metrics remain unavailable. Material settings are
only reported when recorded; reset seeds do not imply fresh startup material samples.

## 1. 2026-10-11_02-04-54_bootstrap120-progress-checkpoints (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_02-04-54_bootstrap120-progress-checkpoints/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_01-48-50_stairs-bootstrap-discovery120/model_120.pt` (source: result)
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
| 0 | asc | 0.025 / 0.3 | 11 | 24 / 32 | 75.00% | 0 | 8 | 0 | 0 | 14.94% | 3.700 | False |
| 1 | desc | 0.025 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.05 / 0.3 | 11 | 31 / 32 | 96.88% | 0 | 0 | 1 | 0 | 5.87% | 2.560 | True |
| 3 | desc | 0.05 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 1.61% | 1.080 | True |
| 5 | desc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 80.41% | 3.680 | False |
| 7 | desc | 0.16 / 0.27 | 11 | 1 / 32 | 3.12% | 22 | 8 | 1 | 0 | 29.13% | 5.320 | False |
| 0 | asc | 0.025 / 0.3 | 29 | 26 / 32 | 81.25% | 0 | 6 | 0 | 0 | 15.28% | 3.720 | False |
| 1 | desc | 0.025 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.05 / 0.3 | 29 | 26 / 32 | 81.25% | 0 | 6 | 0 | 0 | 11.48% | 3.760 | False |
| 3 | desc | 0.05 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 2.58% | 1.600 | True |
| 5 | desc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 79.40% | 2.960 | False |
| 7 | desc | 0.16 / 0.27 | 29 | 3 / 32 | 9.38% | 21 | 7 | 1 | 0 | 26.79% | 5.360 | False |
| 0 | asc | 0.025 / 0.3 | 47 | 22 / 32 | 68.75% | 0 | 10 | 0 | 0 | 16.88% | 3.700 | False |
| 1 | desc | 0.025 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.05 / 0.3 | 47 | 30 / 32 | 93.75% | 0 | 2 | 0 | 0 | 10.96% | 3.740 | False |
| 3 | desc | 0.05 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.08 / 0.3 | 47 | 30 / 32 | 93.75% | 0 | 2 | 0 | 0 | 6.18% | 3.540 | False |
| 5 | desc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 80.66% | 3.680 | False |
| 7 | desc | 0.16 / 0.27 | 47 | 0 / 32 | 0.00% | 23 | 9 | 0 | 0 | 27.34% | 3.800 | False |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 75.00% | 68.75% | 47 | 0.00% | 31.25% | 0.00% | 0.00% | 3.720 |
| 1 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 90.62% | 81.25% | 29 | 0.00% | 18.75% | 3.12% | 0.00% | 3.760 |
| 3 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 4 | 97.92% | 93.75% | 47 | 0.00% | 6.25% | 0.00% | 0.00% | 3.540 |
| 5 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 6 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 3.680 |
| 7 | 4.17% | 0.00% | 47 | 71.88% | 28.12% | 3.12% | 0.00% | 5.360 |

## 2. 0_model_100 (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_02-04-54_bootstrap120-progress-checkpoints/candidates/0_model_100/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_01-48-50_stairs-bootstrap-discovery120/model_100.pt` (source: result)
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
| 0 | asc | 0.025 / 0.3 | 11 | 17 / 32 | 53.12% | 0 | 15 | 0 | 0 | 18.39% | 3.700 | False |
| 1 | desc | 0.025 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.05 / 0.3 | 11 | 15 / 32 | 46.88% | 0 | 15 | 2 | 0 | 21.55% | 3.760 | False |
| 3 | desc | 0.05 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 2.85% | 0.880 | True |
| 5 | desc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 80.20% | 3.500 | False |
| 7 | desc | 0.16 / 0.27 | 11 | 2 / 32 | 6.25% | 25 | 4 | 1 | 0 | 24.55% | 3.960 | False |
| 0 | asc | 0.025 / 0.3 | 29 | 20 / 32 | 62.50% | 0 | 12 | 0 | 0 | 17.59% | 3.720 | False |
| 1 | desc | 0.025 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.05 / 0.3 | 29 | 15 / 32 | 46.88% | 0 | 17 | 0 | 0 | 22.68% | 3.720 | False |
| 3 | desc | 0.05 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.08 / 0.3 | 29 | 30 / 32 | 93.75% | 0 | 2 | 0 | 0 | 4.68% | 3.540 | False |
| 5 | desc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 78.28% | 3.500 | False |
| 7 | desc | 0.16 / 0.27 | 29 | 2 / 32 | 6.25% | 27 | 3 | 0 | 0 | 25.84% | 4.900 | False |
| 0 | asc | 0.025 / 0.3 | 47 | 23 / 32 | 71.88% | 0 | 8 | 0 | 0 | 13.02% | 3.700 | False |
| 1 | desc | 0.025 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.05 / 0.3 | 47 | 14 / 32 | 43.75% | 0 | 18 | 0 | 0 | 22.40% | 3.760 | False |
| 3 | desc | 0.05 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.08 / 0.3 | 47 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 3.42% | 3.280 | True |
| 5 | desc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 78.08% | 3.540 | False |
| 7 | desc | 0.16 / 0.27 | 47 | 0 / 32 | 0.00% | 28 | 4 | 0 | 0 | 28.30% | 4.860 | False |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 62.50% | 53.12% | 11 | 0.00% | 46.88% | 0.00% | 0.00% | 3.720 |
| 1 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 45.83% | 43.75% | 47 | 0.00% | 56.25% | 6.25% | 0.00% | 3.760 |
| 3 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 4 | 96.88% | 93.75% | 29 | 0.00% | 6.25% | 0.00% | 0.00% | 3.540 |
| 5 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 6 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 3.540 |
| 7 | 4.17% | 0.00% | 47 | 87.50% | 12.50% | 3.12% | 0.00% | 4.900 |

## 3. 1_model_60 (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_02-04-54_bootstrap120-progress-checkpoints/candidates/1_model_60/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_01-48-50_stairs-bootstrap-discovery120/model_60.pt` (source: result)
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
| 0 | asc | 0.025 / 0.3 | 11 | 18 / 32 | 56.25% | 0 | 13 | 1 | 0 | 15.52% | 3.840 | False |
| 1 | desc | 0.025 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.05 / 0.3 | 11 | 12 / 32 | 37.50% | 0 | 20 | 0 | 0 | 21.46% | 3.980 | False |
| 3 | desc | 0.05 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.08 / 0.3 | 11 | 4 / 32 | 12.50% | 0 | 28 | 0 | 0 | 23.72% | 3.660 | False |
| 5 | desc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 62.17% | 2.560 | False |
| 7 | desc | 0.16 / 0.27 | 11 | 1 / 32 | 3.12% | 19 | 12 | 0 | 0 | 28.77% | 3.660 | False |
| 0 | asc | 0.025 / 0.3 | 29 | 14 / 32 | 43.75% | 1 | 14 | 0 | 1 | 18.00% | 3.840 | False |
| 1 | desc | 0.025 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.05 / 0.3 | 29 | 8 / 32 | 25.00% | 0 | 24 | 0 | 0 | 24.11% | 4.080 | False |
| 3 | desc | 0.05 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.08 / 0.3 | 29 | 4 / 32 | 12.50% | 0 | 28 | 0 | 0 | 23.41% | 0.740 | False |
| 5 | desc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 59.47% | 2.360 | False |
| 7 | desc | 0.16 / 0.27 | 29 | 0 / 32 | 0.00% | 19 | 13 | 0 | 0 | 30.21% | 3.800 | False |
| 0 | asc | 0.025 / 0.3 | 47 | 14 / 32 | 43.75% | 0 | 15 | 1 | 0 | 18.52% | 3.860 | False |
| 1 | desc | 0.025 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.05 / 0.3 | 47 | 3 / 32 | 9.38% | 0 | 28 | 1 | 0 | 29.64% | 4.100 | False |
| 3 | desc | 0.05 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.08 / 0.3 | 47 | 9 / 32 | 28.12% | 0 | 23 | 0 | 0 | 17.13% | 0.720 | False |
| 5 | desc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 65.17% | 2.200 | False |
| 7 | desc | 0.16 / 0.27 | 47 | 0 / 32 | 0.00% | 19 | 13 | 0 | 0 | 30.86% | 3.780 | False |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 47.92% | 43.75% | 29, 47 | 3.12% | 46.88% | 3.12% | 3.12% | 3.860 |
| 1 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 23.96% | 9.38% | 47 | 0.00% | 87.50% | 3.12% | 0.00% | 4.100 |
| 3 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 4 | 17.71% | 12.50% | 11, 29 | 0.00% | 87.50% | 0.00% | 0.00% | 3.660 |
| 5 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 6 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 2.560 |
| 7 | 1.04% | 0.00% | 29, 47 | 59.38% | 40.62% | 0.00% | 0.00% | 3.800 |

