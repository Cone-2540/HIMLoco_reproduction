# Recorded staircase evaluations

No models are selected and no thresholds are changed. Pooled completion counts all recorded
environments; minimum case/seed completion preserves the worst reset seed. A direction total
does not replace individual cases. Missing metrics remain unavailable. Material settings are
only reported when recorded; reset seeds do not imply fresh startup material samples.

## 1. 2026-10-11_01-21-27_easy100-core-checkpoints (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_01-21-27_easy100-core-checkpoints/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_00-51-49_stairs-easy-faithful-100/model_100.pt` (source: result)
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
| 0 | asc | 0.08 / 0.3 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 73.42% | 3.680 | False |
| 1 | desc | 0.08 / 0.3 | 11 | 26 / 32 | 81.25% | 0 | 6 | 0 | 0 | 2.33% | 3.580 | False |
| 2 | asc | 0.16 / 0.27 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 72.55% | 3.560 | False |
| 3 | desc | 0.16 / 0.27 | 11 | 29 / 32 | 90.62% | 1 | 2 | 0 | 0 | 1.96% | 3.400 | False |
| 0 | asc | 0.08 / 0.3 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 73.85% | 3.620 | False |
| 1 | desc | 0.08 / 0.3 | 29 | 30 / 32 | 93.75% | 0 | 2 | 0 | 0 | 1.27% | 3.280 | False |
| 2 | asc | 0.16 / 0.27 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 71.99% | 3.620 | False |
| 3 | desc | 0.16 / 0.27 | 29 | 29 / 32 | 90.62% | 3 | 0 | 0 | 0 | 0.04% | 0.060 | False |
| 0 | asc | 0.08 / 0.3 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 74.05% | 3.640 | False |
| 1 | desc | 0.08 / 0.3 | 47 | 29 / 32 | 90.62% | 0 | 3 | 0 | 0 | 1.81% | 3.740 | False |
| 2 | asc | 0.16 / 0.27 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 73.87% | 3.600 | False |
| 3 | desc | 0.16 / 0.27 | 47 | 30 / 32 | 93.75% | 1 | 1 | 0 | 0 | 0.84% | 0.740 | False |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 3.680 |
| 1 | 88.54% | 81.25% | 11 | 0.00% | 18.75% | 0.00% | 0.00% | 3.740 |
| 2 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 3.620 |
| 3 | 91.67% | 90.62% | 11, 29 | 9.38% | 6.25% | 0.00% | 0.00% | 3.400 |

## 2. 2026-10-11_01-46-30_move200-core-checkpoints (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_01-46-30_move200-core-checkpoints/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_01-27-53_stairs-easy-move200/model_200.pt` (source: result)
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
| 0 | asc | 0.08 / 0.3 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 60.65% | 3.640 | False |
| 1 | desc | 0.08 / 0.3 | 11 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 2.15% | 3.040 | True |
| 2 | asc | 0.16 / 0.27 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 59.88% | 3.620 | False |
| 3 | desc | 0.16 / 0.27 | 11 | 27 / 32 | 84.38% | 5 | 0 | 0 | 0 | 0.33% | 0.360 | False |
| 0 | asc | 0.08 / 0.3 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 54.36% | 3.640 | False |
| 1 | desc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.16 / 0.27 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 63.37% | 3.660 | False |
| 3 | desc | 0.16 / 0.27 | 29 | 28 / 32 | 87.50% | 4 | 0 | 0 | 0 | 0.23% | 0.260 | False |
| 0 | asc | 0.08 / 0.3 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 60.27% | 3.580 | False |
| 1 | desc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.51% | 1.120 | True |
| 2 | asc | 0.16 / 0.27 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 60.39% | 3.640 | False |
| 3 | desc | 0.16 / 0.27 | 47 | 29 / 32 | 90.62% | 3 | 0 | 0 | 0 | 0.00% | 0.000 | False |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 3.640 |
| 1 | 98.96% | 96.88% | 11 | 0.00% | 3.12% | 0.00% | 0.00% | 3.040 |
| 2 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 3.660 |
| 3 | 87.50% | 84.38% | 11 | 15.62% | 0.00% | 0.00% | 0.00% | 0.360 |

## 3. 0_model_80 (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_01-21-27_easy100-core-checkpoints/candidates/0_model_80/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_00-51-49_stairs-easy-faithful-100/model_80.pt` (source: result)
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
| 0 | asc | 0.08 / 0.3 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 74.69% | 3.620 | False |
| 1 | desc | 0.08 / 0.3 | 11 | 27 / 32 | 84.38% | 0 | 5 | 0 | 0 | 6.02% | 3.380 | False |
| 2 | asc | 0.16 / 0.27 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 71.92% | 3.640 | False |
| 3 | desc | 0.16 / 0.27 | 11 | 22 / 32 | 68.75% | 3 | 7 | 0 | 0 | 8.65% | 3.720 | False |
| 0 | asc | 0.08 / 0.3 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 76.92% | 3.640 | False |
| 1 | desc | 0.08 / 0.3 | 29 | 26 / 32 | 81.25% | 0 | 6 | 0 | 0 | 5.10% | 3.420 | False |
| 2 | asc | 0.16 / 0.27 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 75.56% | 3.620 | False |
| 3 | desc | 0.16 / 0.27 | 29 | 26 / 32 | 81.25% | 3 | 3 | 0 | 0 | 4.48% | 3.660 | False |
| 0 | asc | 0.08 / 0.3 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 73.43% | 3.640 | False |
| 1 | desc | 0.08 / 0.3 | 47 | 26 / 32 | 81.25% | 0 | 6 | 0 | 0 | 5.85% | 2.880 | False |
| 2 | asc | 0.16 / 0.27 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 75.65% | 3.640 | False |
| 3 | desc | 0.16 / 0.27 | 47 | 26 / 32 | 81.25% | 2 | 4 | 0 | 0 | 3.71% | 3.720 | False |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 3.640 |
| 1 | 82.29% | 81.25% | 29, 47 | 0.00% | 18.75% | 0.00% | 0.00% | 3.420 |
| 2 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 3.640 |
| 3 | 77.08% | 68.75% | 11 | 9.38% | 21.88% | 0.00% | 0.00% | 3.720 |

## 4. 1_model_60 (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_01-21-27_easy100-core-checkpoints/candidates/1_model_60/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_00-51-49_stairs-easy-faithful-100/model_60.pt` (source: result)
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
| 0 | asc | 0.08 / 0.3 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 77.16% | 3.680 | False |
| 1 | desc | 0.08 / 0.3 | 11 | 20 / 32 | 62.50% | 0 | 12 | 0 | 0 | 6.20% | 2.880 | False |
| 2 | asc | 0.16 / 0.27 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 74.74% | 3.680 | False |
| 3 | desc | 0.16 / 0.27 | 11 | 2 / 32 | 6.25% | 17 | 13 | 0 | 0 | 1.53% | 0.720 | False |
| 0 | asc | 0.08 / 0.3 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 72.23% | 3.660 | False |
| 1 | desc | 0.08 / 0.3 | 29 | 17 / 32 | 53.12% | 0 | 15 | 0 | 0 | 8.38% | 3.500 | False |
| 2 | asc | 0.16 / 0.27 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 73.42% | 3.660 | False |
| 3 | desc | 0.16 / 0.27 | 29 | 1 / 32 | 3.12% | 23 | 8 | 0 | 0 | 0.34% | 0.160 | False |
| 0 | asc | 0.08 / 0.3 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 77.33% | 3.680 | False |
| 1 | desc | 0.08 / 0.3 | 47 | 13 / 32 | 40.62% | 0 | 19 | 0 | 0 | 5.76% | 3.540 | False |
| 2 | asc | 0.16 / 0.27 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 78.81% | 3.680 | False |
| 3 | desc | 0.16 / 0.27 | 47 | 3 / 32 | 9.38% | 16 | 13 | 0 | 0 | 1.13% | 0.580 | False |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 3.680 |
| 1 | 52.08% | 40.62% | 47 | 0.00% | 59.38% | 0.00% | 0.00% | 3.540 |
| 2 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 3.680 |
| 3 | 6.25% | 3.12% | 29 | 71.88% | 40.62% | 0.00% | 0.00% | 0.720 |

## 5. 0_model_160 (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_01-46-30_move200-core-checkpoints/candidates/0_model_160/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_01-27-53_stairs-easy-move200/model_160.pt` (source: result)
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
| 0 | asc | 0.08 / 0.3 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 58.49% | 3.660 | False |
| 1 | desc | 0.08 / 0.3 | 11 | 28 / 32 | 87.50% | 0 | 4 | 0 | 0 | 1.43% | 0.920 | False |
| 2 | asc | 0.16 / 0.27 | 11 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 58.11% | 3.580 | False |
| 3 | desc | 0.16 / 0.27 | 11 | 23 / 32 | 71.88% | 3 | 6 | 0 | 0 | 1.04% | 0.680 | False |
| 0 | asc | 0.08 / 0.3 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 60.29% | 3.620 | False |
| 1 | desc | 0.08 / 0.3 | 29 | 26 / 32 | 81.25% | 0 | 6 | 0 | 0 | 0.00% | 0.000 | False |
| 2 | asc | 0.16 / 0.27 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 56.97% | 3.620 | False |
| 3 | desc | 0.16 / 0.27 | 29 | 28 / 32 | 87.50% | 1 | 3 | 0 | 0 | 1.22% | 1.000 | False |
| 0 | asc | 0.08 / 0.3 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 61.44% | 3.640 | False |
| 1 | desc | 0.08 / 0.3 | 47 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.16 / 0.27 | 47 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 59.01% | 3.640 | False |
| 3 | desc | 0.16 / 0.27 | 47 | 26 / 32 | 81.25% | 2 | 4 | 0 | 0 | 5.76% | 3.640 | False |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 3.660 |
| 1 | 88.54% | 81.25% | 29 | 0.00% | 18.75% | 0.00% | 0.00% | 0.920 |
| 2 | 0.00% | 0.00% | 11, 29, 47 | 0.00% | 100.00% | 0.00% | 0.00% | 3.640 |
| 3 | 80.21% | 71.88% | 11 | 9.38% | 18.75% | 0.00% | 0.00% | 3.640 |

