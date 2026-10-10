# Recorded staircase evaluations

No models are selected and no thresholds are changed. Pooled completion counts all recorded
environments; minimum case/seed completion preserves the worst reset seed. A direction total
does not replace individual cases. Missing metrics remain unavailable. Material settings are
only reported when recorded; reset seeds do not imply fresh startup material samples.

## 1. 2026-10-11_03-04-27_standard370-low-speed-validation (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_03-04-27_standard370-low-speed-validation/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_02-45-21_stairs-standard-low-speed370/model_370.pt` (source: result)
- Speed: 0.3 m/s; reset randomized: True; dynamics randomized: False; independent reset validation eligible: True.
- Minimum pooled case completion: 100.00%; minimum case/seed completion: 100.00%; observations complete: True.
- Reported evaluation passed: True; reported final traversal passed: True.
- Validation scope: randomized reset cases
- Recorded reset seeds: [11, 29, 47]; missing configured reset seeds: [].
- Seed/material sampling scope: reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds
- Material configuration: `{"domain_randomization_profile":null,"foot_material":null,"friction_override":null,"parameter_scope":"Material parameter ranges not recorded; inherited environment materials are unknown","seed_scope":"reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds","terrain_material":null}`
- Recorded thresholds: `{"evaluation":{"completion_fraction":0.9,"contact_force_n":1.0,"goal_foot_clearance_m":0.1,"goal_foot_height_tolerance_m":0.12,"maximum_base_clearance_m":0.6,"minimum_base_clearance_m":0.18,"minimum_num_envs":32,"slip_speed_m_s":0.1,"stall_progress_m":0.05,"stall_window_s":4.0,"upright_gravity_z":-0.8},"final_acceptance":{"completion_fraction":0.95,"maximum_base_contact_envs":0,"maximum_failure_fraction":0.05,"maximum_flight_pause_s_for_motion_flag":1.0}}`

| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | asc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 4.53% | 0.960 | True |
| 1 | desc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 7 | desc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 9 | desc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 3.69% | 0.340 | True |
| 1 | desc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 7 | desc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 9 | desc | 0.17 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 3.61% | 0.360 | True |
| 1 | desc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 7 | desc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 9 | desc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.960 |
| 1 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 3 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 4 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 5 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 6 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 7 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 8 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 9 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 10 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 11 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |

## 2. 2026-10-11_03-08-49_standard370-speed05-validation (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_03-08-49_standard370-speed05-validation/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_02-45-21_stairs-standard-low-speed370/model_370.pt` (source: result)
- Speed: 0.5 m/s; reset randomized: True; dynamics randomized: False; independent reset validation eligible: True.
- Minimum pooled case completion: 100.00%; minimum case/seed completion: 100.00%; observations complete: True.
- Reported evaluation passed: True; reported final traversal passed: True.
- Validation scope: randomized reset cases
- Recorded reset seeds: [11, 29, 47]; missing configured reset seeds: [].
- Seed/material sampling scope: reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds
- Material configuration: `{"domain_randomization_profile":null,"foot_material":null,"friction_override":null,"parameter_scope":"Material parameter ranges not recorded; inherited environment materials are unknown","seed_scope":"reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds","terrain_material":null}`
- Recorded thresholds: `{"evaluation":{"completion_fraction":0.9,"contact_force_n":1.0,"goal_foot_clearance_m":0.1,"goal_foot_height_tolerance_m":0.12,"maximum_base_clearance_m":0.6,"minimum_base_clearance_m":0.18,"minimum_num_envs":32,"slip_speed_m_s":0.1,"stall_progress_m":0.05,"stall_window_s":4.0,"upright_gravity_z":-0.8},"final_acceptance":{"completion_fraction":0.95,"maximum_base_contact_envs":0,"maximum_failure_fraction":0.05,"maximum_flight_pause_s_for_motion_flag":1.0}}`

| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | asc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 1 | desc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 7 | desc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.06% | 0.100 | True |
| 9 | desc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 1 | desc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 7 | desc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.08% | 0.120 | True |
| 9 | desc | 0.17 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 1 | desc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 7 | desc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.08% | 0.120 | True |
| 9 | desc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 1 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 3 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 4 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 5 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 6 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 7 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 8 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.120 |
| 9 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 10 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 11 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |

## 3. 0_model_340 (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_03-04-27_standard370-low-speed-validation/candidates/0_model_340/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_02-45-21_stairs-standard-low-speed370/model_340.pt` (source: result)
- Speed: 0.3 m/s; reset randomized: True; dynamics randomized: False; independent reset validation eligible: True.
- Minimum pooled case completion: 100.00%; minimum case/seed completion: 100.00%; observations complete: True.
- Reported evaluation passed: True; reported final traversal passed: True.
- Validation scope: randomized reset cases
- Recorded reset seeds: [11, 29, 47]; missing configured reset seeds: [].
- Seed/material sampling scope: reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds
- Material configuration: `{"domain_randomization_profile":null,"foot_material":null,"friction_override":null,"parameter_scope":"Material parameter ranges not recorded; inherited environment materials are unknown","seed_scope":"reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds","terrain_material":null}`
- Recorded thresholds: `{"evaluation":{"completion_fraction":0.9,"contact_force_n":1.0,"goal_foot_clearance_m":0.1,"goal_foot_height_tolerance_m":0.12,"maximum_base_clearance_m":0.6,"minimum_base_clearance_m":0.18,"minimum_num_envs":32,"slip_speed_m_s":0.1,"stall_progress_m":0.05,"stall_window_s":4.0,"upright_gravity_z":-0.8},"final_acceptance":{"completion_fraction":0.95,"maximum_base_contact_envs":0,"maximum_failure_fraction":0.05,"maximum_flight_pause_s_for_motion_flag":1.0}}`

| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | asc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.20% | 0.240 | True |
| 1 | desc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 7 | desc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 9 | desc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.13% | 0.200 | True |
| 1 | desc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.04% | 0.100 | True |
| 6 | asc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 7 | desc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 9 | desc | 0.17 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.01% | 0.020 | True |
| 0 | asc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.04% | 0.060 | True |
| 1 | desc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 7 | desc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 9 | desc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.240 |
| 1 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 3 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 4 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 5 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.100 |
| 6 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 7 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 8 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 9 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 10 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 11 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.020 |

## 4. 0_model_340 (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_03-08-49_standard370-speed05-validation/candidates/0_model_340/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_02-45-21_stairs-standard-low-speed370/model_340.pt` (source: result)
- Speed: 0.5 m/s; reset randomized: True; dynamics randomized: False; independent reset validation eligible: True.
- Minimum pooled case completion: 100.00%; minimum case/seed completion: 100.00%; observations complete: True.
- Reported evaluation passed: True; reported final traversal passed: True.
- Validation scope: randomized reset cases
- Recorded reset seeds: [11, 29, 47]; missing configured reset seeds: [].
- Seed/material sampling scope: reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds
- Material configuration: `{"domain_randomization_profile":null,"foot_material":null,"friction_override":null,"parameter_scope":"Material parameter ranges not recorded; inherited environment materials are unknown","seed_scope":"reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds","terrain_material":null}`
- Recorded thresholds: `{"evaluation":{"completion_fraction":0.9,"contact_force_n":1.0,"goal_foot_clearance_m":0.1,"goal_foot_height_tolerance_m":0.12,"maximum_base_clearance_m":0.6,"minimum_base_clearance_m":0.18,"minimum_num_envs":32,"slip_speed_m_s":0.1,"stall_progress_m":0.05,"stall_window_s":4.0,"upright_gravity_z":-0.8},"final_acceptance":{"completion_fraction":0.95,"maximum_base_contact_envs":0,"maximum_failure_fraction":0.05,"maximum_flight_pause_s_for_motion_flag":1.0}}`

| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | asc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 1 | desc | 0.08 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.04% | 0.060 | True |
| 7 | desc | 0.16 / 0.27 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.53% | 0.160 | True |
| 9 | desc | 0.17 / 0.25 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 11 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 1 | desc | 0.08 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.03% | 0.040 | True |
| 5 | desc | 0.14 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 7 | desc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.34% | 0.160 | True |
| 9 | desc | 0.17 / 0.25 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 0 | asc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 1 | desc | 0.08 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 3 | desc | 0.12 / 0.3 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 5 | desc | 0.14 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 6 | asc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 7 | desc | 0.16 / 0.27 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 8 | asc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.07% | 0.060 | True |
| 9 | desc | 0.17 / 0.25 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 10 | asc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 11 | desc | 0.17 / 0.4 | 47 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 1 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 3 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 4 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.040 |
| 5 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 6 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.060 |
| 7 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 8 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.160 |
| 9 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 10 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 11 | 100.00% | 100.00% | 11, 29, 47 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |

