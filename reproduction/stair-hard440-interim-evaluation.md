# Recorded staircase evaluations

No models are selected and no thresholds are changed. Pooled completion counts all recorded
environments; minimum case/seed completion preserves the worst reset seed. A direction total
does not replace individual cases. Missing metrics remain unavailable. Material settings are
only reported when recorded; reset seeds do not imply fresh startup material samples.

## 1. 2026-10-11_03-26-44_hard440-interim-contact-v2 (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_03-26-44_hard440-interim-contact-v2/result.json`
- Checkpoint: `/workspace/himloco/isaaclab/logs/2026-10-11_03-13-12_stairs-hard-faithful570/model_440.pt` (source: result)
- Speed: 0.3 m/s; reset randomized: True; dynamics randomized: False; independent reset validation eligible: False.
- Minimum pooled case completion: 71.88%; minimum case/seed completion: 71.88%; observations complete: True.
- Reported evaluation passed: False; reported final traversal passed: False.
- Validation scope: randomized reset cases
- Recorded reset seeds: [29]; missing configured reset seeds: [].
- Seed/material sampling scope: reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds
- Material configuration: `{"domain_randomization_profile":null,"foot_material":null,"friction_override":null,"parameter_scope":"Material parameter ranges not recorded; inherited environment materials are unknown","seed_scope":"reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds","terrain_material":null}`
- Recorded thresholds: `{"evaluation":{"completion_fraction":0.9,"contact_force_n":1.0,"goal_foot_clearance_m":0.1,"goal_foot_height_tolerance_m":0.12,"maximum_base_clearance_m":0.6,"minimum_base_clearance_m":0.18,"minimum_num_envs":32,"slip_speed_m_s":0.1,"stall_progress_m":0.05,"stall_window_s":4.0,"upright_gravity_z":-0.8},"final_acceptance":{"completion_fraction":0.95,"maximum_base_contact_envs":0,"maximum_failure_fraction":0.05,"maximum_flight_pause_s_for_motion_flag":1.0}}`

| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | asc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 3.89% | 0.760 | True |
| 1 | desc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.17 / 0.27 | 29 | 23 / 32 | 71.88% | 0 | 8 | 1 | 0 | 15.48% | 3.840 | False |
| 3 | desc | 0.17 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.2 / 0.27 | 29 | 29 / 32 | 90.62% | 0 | 3 | 0 | 0 | 5.30% | 3.720 | False |
| 5 | desc | 0.2 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.03% | 0.060 | True |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 100.00% | 100.00% | 29 | 0.00% | 0.00% | 0.00% | 0.00% | 0.760 |
| 1 | 100.00% | 100.00% | 29 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 71.88% | 71.88% | 29 | 0.00% | 25.00% | 3.12% | 0.00% | 3.840 |
| 3 | 100.00% | 100.00% | 29 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 4 | 90.62% | 90.62% | 29 | 0.00% | 9.38% | 0.00% | 0.00% | 3.720 |
| 5 | 100.00% | 100.00% | 29 | 0.00% | 0.00% | 0.00% | 0.00% | 0.060 |

## 2. 0_model_370 (policy)

- Result: `/home/cone/Research/HIMLoco/isaaclab/logs/2026-10-11_03-26-44_hard440-interim-contact-v2/candidates/0_model_370/result.json`
- Checkpoint: `/workspace/himloco/artifacts/go2-stairs-standard370/model_370.pt` (source: result)
- Speed: 0.3 m/s; reset randomized: True; dynamics randomized: False; independent reset validation eligible: False.
- Minimum pooled case completion: 0.00%; minimum case/seed completion: 0.00%; observations complete: True.
- Reported evaluation passed: False; reported final traversal passed: False.
- Validation scope: randomized reset cases
- Recorded reset seeds: [29]; missing configured reset seeds: [].
- Seed/material sampling scope: reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds
- Material configuration: `{"domain_randomization_profile":null,"foot_material":null,"friction_override":null,"parameter_scope":"Material parameter ranges not recorded; inherited environment materials are unknown","seed_scope":"reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds","terrain_material":null}`
- Recorded thresholds: `{"evaluation":{"completion_fraction":0.9,"contact_force_n":1.0,"goal_foot_clearance_m":0.1,"goal_foot_height_tolerance_m":0.12,"maximum_base_clearance_m":0.6,"minimum_base_clearance_m":0.18,"minimum_num_envs":32,"slip_speed_m_s":0.1,"stall_progress_m":0.05,"stall_window_s":4.0,"upright_gravity_z":-0.8},"final_acceptance":{"completion_fraction":0.95,"maximum_base_contact_envs":0,"maximum_failure_fraction":0.05,"maximum_flight_pause_s_for_motion_flag":1.0}}`

| Case | Direction | Height / tread (m) | Seed | Completed / envs | Completion | Falls | Stalls | Escapes | Base contact envs | Pause fraction | Longest pause (s) | Reported final pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | asc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 1 | desc | 0.16 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 2 | asc | 0.17 / 0.27 | 29 | 0 / 32 | 0.00% | 0 | 32 | 0 | 0 | 71.21% | 3.780 | False |
| 3 | desc | 0.17 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.00% | 0.000 | True |
| 4 | asc | 0.2 / 0.27 | 29 | 17 / 32 | 53.12% | 0 | 15 | 0 | 0 | 6.08% | 0.780 | False |
| 5 | desc | 0.2 / 0.27 | 29 | 32 / 32 | 100.00% | 0 | 0 | 0 | 0 | 0.78% | 0.940 | True |

| Case | Pooled completion | Minimum seed completion | Worst completion seeds | Max seed falls | Max seed stalls | Max seed escapes | Max seed base contacts | Max pause (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | 100.00% | 100.00% | 29 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 1 | 100.00% | 100.00% | 29 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 2 | 0.00% | 0.00% | 29 | 0.00% | 100.00% | 0.00% | 0.00% | 3.780 |
| 3 | 100.00% | 100.00% | 29 | 0.00% | 0.00% | 0.00% | 0.00% | 0.000 |
| 4 | 53.12% | 53.12% | 29 | 0.00% | 46.88% | 0.00% | 0.00% | 0.780 |
| 5 | 100.00% | 100.00% | 29 | 0.00% | 0.00% | 0.00% | 0.00% | 0.940 |

