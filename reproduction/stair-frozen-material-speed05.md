# Frozen foot-material sensitivity at 0.5 m/s

Status: complete. This is a separately recorded supplement for the frozen primary control660; it leaves the original frozen protocol, selection and acceptance unchanged. Lower/higher friction are compared with the same-speed foot-only basic nominal reference.

| Foot material | Completed | Worst case/seed | Fall/stall/escape flags | Base history/current | Whole16-case gate | Maxpause(s) |
| --- | ---: | ---: | --- | --- | --- | ---: |
| nominal | 1520/1536 | 25/32 | 1/1/14 | 0/0 | FAIL | 3.76 |
| low | 1535/1536 | 31/32 | 1/0/0 | 0/0 | PASS | 0.60 |
| high | 1395/1536 | 8/32 | 24/52/65 | 6/5 | FAIL | 3.86 |

## Preserved geometry strata

| Material | Group | Completed | Passed case/seeds | Gate |
| --- | --- | ---: | ---: | --- |
| [0.8, 0.6] | paper_corresponding_4 | 384/384 | 12/12 | PASS |
| [0.8, 0.6] | unseen_geometry_8 | 768/768 | 24/24 | PASS |
| [0.8, 0.6] | long_12_step_2 | 178/192 | 3/6 | FAIL |
| [0.8, 0.6] | stretch_23cm_2 | 190/192 | 6/6 | PASS |
| [0.45, 0.35] | paper_corresponding_4 | 384/384 | 12/12 | PASS |
| [0.45, 0.35] | unseen_geometry_8 | 768/768 | 24/24 | PASS |
| [0.45, 0.35] | long_12_step_2 | 192/192 | 6/6 | PASS |
| [0.45, 0.35] | stretch_23cm_2 | 191/192 | 6/6 | PASS |
| [1.0, 0.8] | paper_corresponding_4 | 383/384 | 12/12 | PASS |
| [1.0, 0.8] | unseen_geometry_8 | 756/768 | 21/24 | FAIL |
| [1.0, 0.8] | long_12_step_2 | 125/192 | 3/6 | FAIL |
| [1.0, 0.8] | stretch_23cm_2 | 131/192 | 3/6 | FAIL |

## Failed original case/seed gates

| Material | Seed | Case | Completed | Fall/stall/escape | History base | Failed gate terms |
| --- | ---: | --- | ---: | --- | ---: | --- |
| [0.8, 0.6] | 101 | desc_long12_17cm_25cm | 29/32 | 0/0/3 | 0 | completion_fraction, lateral_escapes |
| [0.8, 0.6] | 211 | desc_long12_17cm_25cm | 25/32 | 0/0/7 | 0 | completion_fraction, lateral_escapes |
| [0.8, 0.6] | 307 | desc_long12_17cm_25cm | 28/32 | 0/0/4 | 0 | completion_fraction, lateral_escapes |
| [1.0, 0.8] | 101 | asc_unseen_lip25mm_16cm_33cm | 29/32 | 1/2/0 | 1 | completion_fraction, stalls, history_base_contact |
| [1.0, 0.8] | 211 | asc_unseen_lip25mm_16cm_33cm | 29/32 | 0/3/0 | 0 | completion_fraction, stalls |
| [1.0, 0.8] | 307 | asc_unseen_lip25mm_16cm_33cm | 26/32 | 3/3/0 | 3 | completion_fraction, falls, stalls, history_base_contact |
| [1.0, 0.8] | 101 | desc_long12_17cm_25cm | 13/32 | 1/0/18 | 0 | completion_fraction, lateral_escapes |
| [1.0, 0.8] | 211 | desc_long12_17cm_25cm | 8/32 | 0/0/24 | 0 | completion_fraction, lateral_escapes |
| [1.0, 0.8] | 307 | desc_long12_17cm_25cm | 8/32 | 1/0/23 | 0 | completion_fraction, lateral_escapes |
| [1.0, 0.8] | 101 | desc_stretch23cm_20cm | 12/32 | 6/14/0 | 0 | completion_fraction, falls, stalls |
| [1.0, 0.8] | 211 | desc_stretch23cm_20cm | 10/32 | 6/16/0 | 2 | completion_fraction, falls, stalls, history_base_contact |
| [1.0, 0.8] | 307 | desc_stretch23cm_20cm | 14/32 | 5/13/0 | 0 | completion_fraction, falls, stalls |

## Saved pairing and readback evidence

| Pair | Geometry | Root positions | Aggregate pose | Thresholds | Contact metadata | Heading | Saved nonfoot parameters |
| --- | --- | --- | --- | --- | --- | --- | --- |
| low_versus_nominal | True | True | True | True | True | True | True |
| high_versus_nominal | True | True | True | True | True | True | True |

The actual foot shape values are nominal0.8/0.6,lower0.45/0.35,higher1.0/0.8 (static/dynamic),with restitution0. Terrain authored values stay1/1 with multiply combine mode. Initial/final actual readbacks,first episode anomaly counts,zero-action controls and nonexclusive versus unique failures are preserved in JSON.

## Limits

- This is a separately recorded0.5m/s friction supplement, added after the original nominal0.3/0.5 m/s outcomes. It does not change the original frozen protocol status, primary selection, checkpoint or acceptance gates; no training or retuning follows these results.
- Lower and higher foot friction are compared to the0.5m/s foot-only basic nominal reference, not the domainnone all-body nominal scene.
- The complete16 cases and every reset seed keep original95% completion,<=5% each failure fraction and zero history base contact gates. Stratifying paper/unseen/long/stretch never removes a failed case from the whole-matrix outcome.
- This tests friction sensitivity on nominal mass/COM/PD at 0.5 m/s; it provides no0.5m/s combined-dynamics evidence. Secondary slide680 is not tested.
- Actual foot shape and authored terrain material values are read back; those coefficients are not calibrated named materials or solver contact-pair coefficients. Foot-link worldXYspeed is a slip proxy, not contact-point tangent slip.
- Only first episodes contribute; motion excludes the first second and retains failed/truncated cases. Lower action/jerk on early failures is not evidence of smoother full traversal.
- Physical/sensor cadence and sparse trace limits match the original report:5 ms physics,20 ms policy,history ages0/5/10 ms,one env/case/seed at 0.1 s; no whole-batch impact or duration bound.
- Three reset seeds share startup physical parameters. Full per-env initial orientation/state is not saved; pairing checks only recorded initial root positions and aggregate pose distributions. No complete smoothness or real-robot readiness claim follows.
