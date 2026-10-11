Selected faithful seed1213 checkpoint: flat seven-command FAIL (2/7).

Each command uses64 environments for20s; original strict gates:XY MAE<0.2m/s, yaw MAE<0.3rad/s, first-episode survival≥95%. Zero learning updates.

| Command [vx,vy,yaw] | Survival | Falls | XY MAE | Yaw MAE | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| [0.3, 0.0, 0.0] | 64/64 | 0 | 0.02043 | 0.01823 | PASS |
| [0.5, 0.0, 0.0] | 64/64 | 0 | 0.01861 | 0.02488 | PASS |
| [-0.5, 0.0, 0.0] | 64/64 | 0 | 0.49985 | 0.01271 | FAIL: XY_MAE |
| [0.0, 0.3, 0.0] | 0/64 | 64 | unavailable | unavailable | FAIL: XY_MAE, yaw_MAE, first_episode_survival |
| [0.0, -0.3, 0.0] | 5/64 | 59 | 0.29975 | 0.13388 | FAIL: XY_MAE, first_episode_survival |
| [0.0, 0.0, 0.5] | 13/64 | 51 | 0.13423 | 0.39734 | FAIL: yaw_MAE, first_episode_survival |
| [0.0, 0.0, -0.5] | 64/64 | 0 | 0.00139 | 0.49828 | FAIL: yaw_MAE |

All matching zero-action controls and complete raw result/config are retained in JSON and CSV.

One nominal flat reset seed907; no dynamics/material robustness claim.
Only first episodes count; tracking excludes first2s, survival includes startup and terminal step.
Aggregate gates recomputed from saved values; source has no per-environment flat trajectory for independent velocity reconstruction.
Upright fraction combines roll/pitch; per-axis roll RMS/peak and flat jerk are not recorded.
Height metrics omit done rows; all-episode counters include later reset episodes and do not replace first-episode survival.
Critic235→48 reset preserves frozen actor/HIM and performs no learning; successful tensor transfer does not imply flat motion passes.
Flat omnidirectional results remain separate from staircase geometry acceptance and real-robot deployment.
