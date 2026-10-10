# Recorded staircase evaluations

No models are selected and no thresholds are changed. Pooled completion counts all recorded
environments; minimum case/seed completion preserves the worst reset seed. A direction total
does not replace individual cases. Missing metrics remain unavailable. Material settings are
only reported when recorded; reset seeds do not imply fresh startup material samples.

## 1. 2026-10-11_02-39-54_standard270-checkpoints-validation (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_02-39-54_standard270-checkpoints-validation/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_02-15-45_stairs-standard-faithful270/model_270.pt` (source: result)
- Speed: 0.3 m/s; reset randomized: True; dynamics randomized: False; independent reset validation eligible: True.
- Minimum pooled case completion: 92.71%; minimum case/seed completion: 90.62%; observations complete: True.
- Reported evaluation passed: True; reported final traversal passed: False.
- Validation scope: randomized reset cases
- Recorded reset seeds: [11, 29, 47]; missing configured reset seeds: [].
- Seed/material sampling scope: reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds
- Material configuration: `{"domain_randomization_profile":null,"foot_material":null,"friction_override":null,"parameter_scope":"Material parameter ranges not recorded; inherited environment materials are unknown","seed_scope":"reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds","terrain_material":null}`
- Recorded thresholds: `{"evaluation":{"completion_fraction":0.9,"contact_force_n":1.0,"goal_foot_clearance_m":0.1,"goal_foot_height_tolerance_m":0.12,"maximum_base_clearance_m":0.6,"minimum_base_clearance_m":0.18,"minimum_num_envs":32,"slip_speed_m_s":0.1,"stall_progress_m":0.05,"stall_window_s":4.0,"upright_gravity_z":-0.8},"final_acceptance":{"completion_fraction":0.95,"maximum_base_contact_envs":0,"maximum_failure_fraction":0.05,"maximum_flight_pause_s_for_motion_flag":1.0}}`

| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | asc | 0.08 / 0.3 | 11 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 16.30% | 1.400 | True |
| 1 | desc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 21.28% | 2.120 | True |
| 5 | desc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.02% | 0.040 | True |
| 6 | asc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 18.71% | 1.680 | True |
| 7 | desc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.18% | 0.200 | True |
| 8 | asc | 0.17 / 0.25 | 11 | 30 / 32 | 93.75% | 0 | 2 | 0 | 0 | 18.47% | 3.680 | False |
| 9 | desc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.81% | 0.280 | True |
| 10 | asc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.04% | 0.140 | True |
| 0 | asc | 0.08 / 0.3 | 29 | 30 / 32 | 93.75% | 0 | 2 | 0 | 0 | 16.25% | 1.600 | False |
| 1 | desc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 22.45% | 2.220 | True |
| 5 | desc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.20% | 0.180 | True |
| 6 | asc | 0.16 / 0.27 | 29 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 17.69% | 1.860 | True |
| 7 | desc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.33% | 0.160 | True |
| 8 | asc | 0.17 / 0.25 | 29 | 30 / 32 | 93.75% | 0 | 2 | 0 | 0 | 16.08% | 3.680 | False |
| 9 | desc | 0.17 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 1.30% | 0.640 | True |
| 10 | asc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.11% | 0.080 | True |
| 0 | asc | 0.08 / 0.3 | 47 | 30 / 32 | 93.75% | 0 | 2 | 0 | 0 | 16.15% | 2.020 | False |
| 1 | desc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.21% | 0.540 | True |
| 3 | desc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 47 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 20.54% | 3.680 | True |
| 5 | desc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.04% | 0.080 | True |
| 6 | asc | 0.16 / 0.27 | 47 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 16.75% | 1.640 | True |
| 7 | desc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.30% | 0.280 | True |
| 8 | asc | 0.17 / 0.25 | 47 | 29 / 32 | 90.62% | 0 | 3 | 0 | 0 | 15.51% | 3.660 | False |
| 9 | desc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 1.41% | 0.620 | True |
| 10 | asc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.08% | 0.120 | True |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 94.79% | 93.75% | 29, 47 | 0.00% | 6.25% | 0.00% | 0.00% | 2.020 |
| 1 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.540 |
| 3 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 4 | 98.96% | 96.88% | 47 | 0.00% | 3.12% | 0.00% | 0.00% | 3.680 |
| 5 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.180 |
| 6 | 97.92% | 96.88% | 29, 47 | 0.00% | 3.12% | 0.00% | 0.00% | 1.860 |
| 7 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.280 |
| 8 | 92.71% | 90.62% | 47 | 0.00% | 9.38% | 0.00% | 0.00% | 3.680 |
| 9 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.640 |
| 10 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 11 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.140 |

## 2. 0_model_240 (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_02-39-54_standard270-checkpoints-validation/candidates/0_model_240/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_02-15-45_stairs-standard-faithful270/model_240.pt` (source: result)
- Speed: 0.3 m/s; reset randomized: True; dynamics randomized: False; independent reset validation eligible: True.
- Minimum pooled case completion: 78.12%; minimum case/seed completion: 75.00%; observations complete: True.
- Reported evaluation passed: False; reported final traversal passed: False.
- Validation scope: randomized reset cases
- Recorded reset seeds: [11, 29, 47]; missing configured reset seeds: [].
- Seed/material sampling scope: reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds
- Material configuration: `{"domain_randomization_profile":null,"foot_material":null,"friction_override":null,"parameter_scope":"Material parameter ranges not recorded; inherited environment materials are unknown","seed_scope":"reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds","terrain_material":null}`
- Recorded thresholds: `{"evaluation":{"completion_fraction":0.9,"contact_force_n":1.0,"goal_foot_clearance_m":0.1,"goal_foot_height_tolerance_m":0.12,"maximum_base_clearance_m":0.6,"minimum_base_clearance_m":0.18,"minimum_num_envs":32,"slip_speed_m_s":0.1,"stall_progress_m":0.05,"stall_window_s":4.0,"upright_gravity_z":-0.8},"final_acceptance":{"completion_fraction":0.95,"maximum_base_contact_envs":0,"maximum_failure_fraction":0.05,"maximum_flight_pause_s_for_motion_flag":1.0}}`

| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | asc | 0.08 / 0.3 | 11 | 26 / 32 | 81.25% | 0 | 6 | 0 | 0 | 22.07% | 3.540 | False |
| 1 | desc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 5.09% | 1.040 | True |
| 3 | desc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 7.40% | 1.740 | True |
| 5 | desc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 9.63% | 1.660 | True |
| 7 | desc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.84% | 1.080 | True |
| 9 | desc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.35% | 0.920 | True |
| 10 | asc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 29 | 25 / 32 | 78.12% | 0 | 7 | 0 | 0 | 22.41% | 3.520 | False |
| 1 | desc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 3.85% | 2.800 | True |
| 3 | desc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 11.71% | 2.160 | True |
| 5 | desc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 10.93% | 1.360 | True |
| 7 | desc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 2.35% | 1.080 | True |
| 9 | desc | 0.17 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.43% | 1.140 | True |
| 10 | asc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 47 | 24 / 32 | 75.00% | 0 | 8 | 0 | 0 | 24.20% | 3.600 | False |
| 1 | desc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 4.51% | 1.080 | True |
| 3 | desc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 4.40% | 1.520 | True |
| 5 | desc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 8.51% | 1.400 | True |
| 7 | desc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.02% | 0.060 | True |
| 8 | asc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.25% | 0.160 | True |
| 9 | desc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.28% | 0.520 | True |
| 10 | asc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 78.12% | 75.00% | 47 | 0.00% | 25.00% | 0.00% | 0.00% | 3.600 |
| 1 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 2.800 |
| 3 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 4 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 2.160 |
| 5 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 6 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 1.660 |
| 7 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.060 |
| 8 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 1.080 |
| 9 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 1.140 |
| 10 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 11 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |

## 3. 1_model_200 (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_02-39-54_standard270-checkpoints-validation/candidates/1_model_200/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_02-15-45_stairs-standard-faithful270/model_200.pt` (source: result)
- Speed: 0.3 m/s; reset randomized: True; dynamics randomized: False; independent reset validation eligible: True.
- Minimum pooled case completion: 16.67%; minimum case/seed completion: 6.25%; observations complete: True.
- Reported evaluation passed: False; reported final traversal passed: False.
- Validation scope: randomized reset cases
- Recorded reset seeds: [11, 29, 47]; missing configured reset seeds: [].
- Seed/material sampling scope: reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds
- Material configuration: `{"domain_randomization_profile":null,"foot_material":null,"friction_override":null,"parameter_scope":"Material parameter ranges not recorded; inherited environment materials are unknown","seed_scope":"reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds","terrain_material":null}`
- Recorded thresholds: `{"evaluation":{"completion_fraction":0.9,"contact_force_n":1.0,"goal_foot_clearance_m":0.1,"goal_foot_height_tolerance_m":0.12,"maximum_base_clearance_m":0.6,"minimum_base_clearance_m":0.18,"minimum_num_envs":32,"slip_speed_m_s":0.1,"stall_progress_m":0.05,"stall_window_s":4.0,"upright_gravity_z":-0.8},"final_acceptance":{"completion_fraction":0.95,"maximum_base_contact_envs":0,"maximum_failure_fraction":0.05,"maximum_flight_pause_s_for_motion_flag":1.0}}`

| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | asc | 0.08 / 0.3 | 11 | 30 / 32 | 93.75% | 0 | 2 | 0 | 0 | 15.96% | 3.020 | False |
| 1 | desc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 11 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 9.39% | 1.540 | True |
| 3 | desc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 11 | 28 / 32 | 87.50% | 0 | 4 | 0 | 0 | 11.33% | 3.460 | False |
| 5 | desc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 11 | 24 / 32 | 75.00% | 0 | 8 | 0 | 0 | 16.34% | 3.500 | False |
| 7 | desc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.98% | 0.760 | True |
| 8 | asc | 0.17 / 0.25 | 11 | 4 / 32 | 12.50% | 0 | 28 | 0 | 0 | 10.70% | 1.320 | False |
| 9 | desc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.63% | 0.500 | True |
| 10 | asc | 0.17 / 0.4 | 11 | 7 / 32 | 21.88% | 0 | 25 | 0 | 0 | 0.42% | 0.160 | False |
| 11 | desc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 29 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 15.72% | 2.200 | True |
| 1 | desc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 29 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 7.85% | 1.000 | True |
| 3 | desc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 29 | 29 / 32 | 90.62% | 0 | 3 | 0 | 0 | 8.88% | 2.060 | False |
| 5 | desc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 29 | 18 / 32 | 56.25% | 0 | 14 | 0 | 0 | 24.15% | 2.500 | False |
| 7 | desc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.53% | 0.200 | True |
| 8 | asc | 0.17 / 0.25 | 29 | 6 / 32 | 18.75% | 0 | 26 | 0 | 0 | 4.13% | 0.720 | False |
| 9 | desc | 0.17 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.36% | 0.220 | True |
| 10 | asc | 0.17 / 0.4 | 29 | 2 / 32 | 6.25% | 0 | 30 | 0 | 0 | 0.00% | 0.000 | False |
| 11 | desc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 47 | 31 / 32 | 96.88% | 0 | 1 | 0 | 0 | 14.72% | 1.020 | True |
| 1 | desc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 7.30% | 0.760 | True |
| 3 | desc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 5.82% | 1.000 | True |
| 5 | desc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 47 | 26 / 32 | 81.25% | 0 | 6 | 0 | 0 | 15.60% | 3.500 | False |
| 7 | desc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.83% | 0.360 | True |
| 8 | asc | 0.17 / 0.25 | 47 | 7 / 32 | 21.88% | 0 | 25 | 0 | 0 | 10.17% | 0.860 | False |
| 9 | desc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.37% | 0.280 | True |
| 10 | asc | 0.17 / 0.4 | 47 | 7 / 32 | 21.88% | 0 | 25 | 0 | 0 | 0.21% | 0.080 | False |
| 11 | desc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 95.83% | 93.75% | 11 | 0.00% | 6.25% | 0.00% | 0.00% | 3.020 |
| 1 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 97.92% | 96.88% | 11, 29 | 0.00% | 3.12% | 0.00% | 0.00% | 1.540 |
| 3 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 4 | 92.71% | 87.50% | 11 | 0.00% | 12.50% | 0.00% | 0.00% | 3.460 |
| 5 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 6 | 70.83% | 56.25% | 29 | 0.00% | 43.75% | 0.00% | 0.00% | 3.500 |
| 7 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.760 |
| 8 | 17.71% | 12.50% | 11 | 0.00% | 87.50% | 0.00% | 0.00% | 1.320 |
| 9 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.500 |
| 10 | 16.67% | 6.25% | 29 | 0.00% | 93.75% | 0.00% | 0.00% | 0.160 |
| 11 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |

