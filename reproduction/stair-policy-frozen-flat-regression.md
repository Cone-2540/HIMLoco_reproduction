# Frozen stair-policy flat regression

The frozen control660 stair checkpoint fails the original six-command nominal plane regression. It receives zero gradient updates and starts from reset. This preserves the stair selection and remains separate from the earlier dedicated flat-policy evaluation.

Each command uses 64 environments for 20 s, with tracking after 2 s warmup and survival measured from startup through the terminal step. The unchanged gate requires XY MAE <0.2 m/s, yaw MAE <0.3 rad/s, survival >=95%, and eligible finite source data. Upright/height diagnostics add no gate.

| Command [vx,vy,yaw] | Survival | First falls | XY MAE / RMSE (m/s) | Yaw MAE / RMSE (rad/s) | Mean observed [vx,vy,yaw] | Upright fraction | Gate |
| --- | ---: | ---: | --- | --- | --- | ---: | --- |
| [0.3,0.0,0.0] | 64/64 | 0 | 0.02830/0.02995 | 0.01784/0.02194 | [0.29223,0.00629,0.00591] | 1.00000 | PASS |
| [0.5,0.0,0.0] | 64/64 | 0 | 0.02841/0.03035 | 0.02335/0.02823 | [0.48827,0.00428,0.00271] | 1.00000 | PASS |
| [-0.5,0.0,0.0] | 64/64 | 0 | 0.49997/0.49997 | 0.00046/0.00308 | [-0.00003,-0.00011,0.00011] | 1.00000 | FAIL: XY_MAE |
| [0.0,0.3,0.0] | 0/64 | 64 | 0.62515/0.65216 | 0.77098/1.29008 | [0.03086,-0.25018,0.74058] | 0.00000 | FAIL: XY_MAE;yaw_MAE;first_episode_survival |
| [0.0,0.0,0.5] | 62/64 | 2 | 0.07697/0.09922 | 0.21742/0.27208 | [0.01555,0.01402,0.29474] | 0.99837 | PASS |
| [0.0,0.0,-0.5] | 64/64 | 0 | 0.00081/0.00551 | 0.49847/0.49856 | [0.00056,-0.00027,-0.00153] | 1.00000 | FAIL: yaw_MAE |

The source records no roll RMS/peak or flat posture trace. Upright fraction uses combined roll/pitch tilt and cannot identify roll specifically. Height and full duration exposure are retained below.

| Command | Mean height (m) | Nominal-height fraction | Mean first episode duration (s) | First requested timeouts | Tracking / height samples | Finite physics |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| [0.3,0.0,0.0] | 0.25898 | 1.00000 | 20.00 | 64 | 57600/57536 | True |
| [0.5,0.0,0.0] | 0.24329 | 1.00000 | 20.00 | 64 | 57600/57536 | True |
| [-0.5,0.0,0.0] | 0.23881 | 1.00000 | 20.00 | 64 | 57600/57536 | True |
| [0.0,0.3,0.0] | 0.13778 | 0.00000 | 2.27 | 0 | 852/788 | True |
| [0.0,0.0,0.5] | 0.26142 | 0.82880 | 19.64 | 62 | 56455/56391 | True |
| [0.0,0.0,-0.5] | 0.25411 | 1.00000 | 20.00 | 64 | 57600/57536 | True |

## Matching zero-action controls

| Command | Survival | XY MAE (m/s) | Yaw MAE (rad/s) | Gate |
| --- | ---: | ---: | ---: | --- |
| [0.3,0.0,0.0] | 64/64 | 0.30100 | 0.00006 | FAIL: XY_MAE |
| [0.5,0.0,0.0] | 64/64 | 0.50100 | 0.00006 | FAIL: XY_MAE |
| [-0.5,0.0,0.0] | 64/64 | 0.49900 | 0.00006 | FAIL: XY_MAE |
| [0.0,0.3,0.0] | 64/64 | 0.30050 | 0.00006 | FAIL: XY_MAE |
| [0.0,0.0,0.5] | 64/64 | 0.00786 | 0.50001 | FAIL: yaw_MAE |
| [0.0,0.0,-0.5] | 64/64 | 0.00786 | 0.49999 | FAIL: yaw_MAE |

## Limits

- This is the unchanged frozen stair checkpoint evaluated on a plane, with zero gradient updates. It is separate from the earlier dedicated flat checkpoint selection and does not replace that historical result.
- One nominal reset seed and six command cases are used, not a material/dynamics or randomized-reset flat robustness test.
- Tracking excludes the first 2 s warmup; survival includes startup and the terminal step. Only each environment’s first episode contributes, and pre-reset terminal velocities remain included.
- XY MAE is mean Euclidean XY velocity error; XY RMSE is sqrt(mean squared XY-vector error). Flat tracking uses the ordinary body-frame velocity commands, unlike external stair heading feedback.
- Upright fraction tests projected gravity_z<-0.8, combining roll and pitch. The flat evaluator does not save roll RMS/peak or a posture trace; this report cannot infer per-axis roll from the upright fraction.
- Height statistics omit done rows because post-step root state has already reset; terminal upright observations remain included. Minimum/maximum height diagnostic uses post-step states across the loop, including later reset episodes.
- Requested-timeout terminations are expected at 20 s and can coexist with full survival; a fall on a timeout step still counts as a fall. All-episode counters are preserved separately and do not inflate first episode survival.
- Source flat criteria remain strict XY MAE<0.2 m/s,yaw MAE<0.3 rad/s,survival>=95%,>=64 envs,>=20 s,no source failure reason. Height/upright are descriptive and introduce no new acceptance gate.
- These nominal simulation tests do not establish real-robot readiness.

Raw source: `isaaclab/logs/2026-10-11_06-09-35_frozen-stair-policy-flat-regression/result.json`; checkpoint SHA-256 `79fcc69b9447ecfb4df9fcfb41224cdab78632649f38fd9faf09c7b6adf69c61`. Lossless compressedJSON preserves the complete original report, configuration and independently recomputed gates; CSV contains policy and zero-action rows.
