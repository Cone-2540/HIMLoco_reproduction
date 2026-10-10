# Minimal high-force leg-contact adaptation review

CPU review and implementation specification, 2026-10-11. The reviewed
`contact_force` profile is implemented with19 passing CPU reward tests; GPU
smoke/training validation is pending. No collider, observation, driver or
running GPU task was changed during this review. Offline calculations are
saved in `stair-contact-severity-offline.json`. These calculations reshape
saved trajectories; they do not predict a trained policy's outcome.

## Recommended first experiment

Keep the current `contact` profile's faithful terms and `leg_contacts=-0.1`
unchanged. Add **one** separately named, bounded high-force leg-contact term
with conservative weight **-0.02** in the independently named `contact_force`
profile. Resume the archived contact620 checkpoint with fixed, realized
actor/estimator LR **1e-4**, start level4, the same hard terrain distribution,
speed range0.25–0.65 and4096 environments for100 additional updates, after a
64-env/2-update smoke. Preserve contact620
and the current faithful/contact continuations as controls. Save every 20
updates and inspect a 40–60-update checkpoint before spending the whole
100-update budget. Freeze the selected checkpoint before fresh final tests.

This is a Go2 adaptation to discourage forceful contact, not a released HIM
reward or a damage/impulse model. It is more directly aligned with the observed
high-force residuals than doubling the count weight. Doubling count treats a
2 N touch and a 489 N contact identically and penalizes all low-force ankle
touches more heavily. The proposed severity term preserves their existing
penalty and changes only force values above 50 N.

Use one predeclared weight; do not simultaneously change count, action
smoothness, tracking, curriculum, actuator limits or exploration. If video or
early training shows support avoidance/stop behavior, preserve the failed
candidate and discard it or evaluate a separately labeled lower-magnitude
weight ablation; do not silently
edit the same run. The -0.02 choice is supported by its small mean
offline contribution and bounded per-event cost, not by proof that 50 N is a
physical safety boundary. A stronger-0.05/lower-LR5e-5 alternative was
reviewed; the chosen-0.02/same-LR1e-4 specification reduces the per-step
support-avoidance pressure while keeping optimizer settings matched. A causal
reward claim needs a `contact` control resumed from the **same620** checkpoint
with identical LR and remaining training settings. The earlier faithful670
control starts from570 and does not isolate this new term.

## Exact proposed semantics

For each selected body `i` among the same eight named thighs/calves:

```text
F_i = max_history ||net_normal_forces_w_i||
s_i = min(max((F_i - 50 N) / 50 N, 0)^2, 4)
raw = sum_i s_i
additional reward = -0.02 * raw * policy_dt
```

Take the history maximum **per body**, then square/clamp each body, then sum
over eight bodies. Do not square the norm of a sum across bodies, average the
eight columns, square their summed excess, or put one clamp on the entire
environment sum; these give different objectives. Exclude feet, hips and base
exactly as in the current count term and validate the eight runtime names.
Use the retained normal-force history on the same reward step. No new
observation or differentiable contact simulation is required.

At policy dt=0.02 s, count=-0.1 contributes -0.002 per contacted body.
The proposed extra term contributes:

| Per-body history force | Raw severity | Extra reward / policy step | Total count plus extra for that body |
| --- | ---: | ---: | ---: |
| 2–50 N | 0 | 0 | -0.002 |
| 75 N | 0.25 | -0.0001 | -0.0021 |
| 100 N | 1 | -0.0004 | -0.0024 |
| 125 N | 2.25 | -0.0009 | -0.0029 |
| ≥150 N | 4 | -0.0016 | -0.0036 |

The bounded maximum extra cost is -0.0128 if all eight bodies saturate. The
292 N thigh and 489 N calf samples both saturate at the same -0.0016/body;
this term does **not** distinguish force magnitude above 150 N. Capping helps
prevent rare impulses dominating advantages but sacrifices that distinction.
A severity label should therefore be `bounded high-force normal-contact
proxy`, not collision energy, contact impulse, scrape force or injury risk.

## Offline evidence and objective size

The offline reader uses active first-episode trace rows after 1 s, eight saved
named body history peaks, the exact proposed formula and dt=0.02. It includes
4351/4697 ascent/descent rows for620 at0.3 m/s and2616/2676 at0.5 m/s.
These are sparse 100 ms samples of one environment per case/seed, with longer
episodes contributing more rows; they are neither full-batch reward averages
nor the stochastic training distribution. The saved JSON includes every case,
per-body force summaries, source paths, row counts and the calculation limits.

| Saved policy/speed/direction | Mean contacted body count | Contacted body-hit median | Body-hit fraction >50 N | Mean extra severity / step | Extra cost from doubling count / step |
| --- | ---: | ---: | ---: | ---: | ---: |
| 620 / 0.3 / ascent | 0.11951 | 18.51 N | 12.69% | -0.00000449 | -0.00023903 |
| 620 / 0.3 / descent | 0.37300 | 53.16 N | 52.91% | -0.00003626 | -0.00074601 |
| 620 / 0.5 / ascent | 0.14488 | 18.51 N | 24.54% | -0.00000807 | -0.00028976 |
| 620 / 0.5 / descent | 0.24589 | 62.64 N | 62.31% | -0.00004864 | -0.00049178 |
| 640 / 0.5 / descent | 0.26240 | 60.61 N | 63.78% | -0.00004414 | -0.00052480 |

Thus severity adds only4.9%/9.9% of the corresponding count-doubling cost
in620 descents at0.3/0.5, and1.9%/2.8% in ascents. It applies most strongly to
descents without indiscriminately doubling every >1 N count. It is not only
a rare-extreme event penalty: roughly half or more of descent body-hit samples
exceed50 N. Only1.48%/5.02% of descent body hits reach the150 N cap for620.

The released-style tracking terms can contribute at most
`(1 + 0.5)*0.02=0.03` per policy step. One150 N body costs0.0016 extra,
5.3% of this maximum; the mean descent extra is about0.12–0.16% of it.
Two simultaneous saturated bodies cost0.0032 extra. This is small on average
but behaviorally meaningful near a short forceful contact.

The actual contact670 training log at update620 reports, in
`Episode_Reward/…` units: linear tracking+0.4487; yaw tracking+0.2143;
action smoothness-0.0192; action rate-0.0106; joint acceleration-0.0159;
vertical velocity-0.0086; orientation-0.0101; joint power-0.0006;
leg count-0.0094. **These are episode sums divided by the configured20 s
maximum episode length**, not immediate per-step rates. Mean episode length
484.79 policy steps is about9.70 s. Dividing the logged sums by this mean
length gives only a scale estimate because logger groups/averaging differ:
count≈-0.000388/step, smoothness≈-0.000792, action rate≈-0.000437,
acceleration≈-0.000656, linear tracking≈+0.01851, yaw≈+0.00884.
The estimated mean added severity is below the existing smoothness/count
costs; its saturated per-body sample is several times those mean costs.

`RewardManager.compute` directly sums `term*weight*dt` without a positive-only
clip (`isaaclab/managers/reward_manager.py:129`); it logs episode sums divided
by `max_episode_length_s` on reset (`reward_manager.py:100`). Changing a weight
should not also multiply the custom function by dt, which would double-scale.
Existing stock torque/air-time/alive/limit terms are cleared by
`configure_stair_rewards`; do not assume they protect the proposed behavior.

## Geometry, stance and force interpretation

The geometry audit finds calf-owned distal ankle cylinders intersect the
upper part of independent foot spheres. Some ankle contact at an edge can be
part of support. A50 N threshold is a heuristic and has not been measured on
the user's EDU. Source total robot mass is about15.019 kg, weight147.3 N;
static support averages36.8 N over four feet or73.7 N over two. These are only
load scales, not a valid way to declare a calf-contact threshold safe.

But ankle-overlap geometry does not explain all high-force rows. For620
descents, only4.32%/10.65% of **current** >50 N body-hit samples at0.3/0.5 have
simultaneous contact on that body's corresponding foot. With matched retained
history, the fractions are7.98%/18.78%. Most high-force samples are therefore
not simple simultaneous ankle-plus-foot support. They may be calf support,
landing or riser contact while the foot is airborne; contact points and poses
are needed to distinguish those possibilities. Calves contribute98.11%/96.46%
of the proposed620 descent history-severity sum.

No duplicate foot-to-calf force sum is present in the inspected sensor path.
The measured norm is a **net normal-contact vector resultant**: multiple
opposing normals may cancel; it excludes tangential friction and joint
reaction wrench. A history maximum is a force-sample proxy, not temporal
integral or true impulse. History3 at5 ms retains0/5/10 ms at a20 ms policy
boundary, so the first-substep-only contact can be overwritten. The proposed
term cannot penalize an event never retained by the current sensor. Keep
contact-history semantics unchanged for this single-factor first experiment;
if later collecting all four substeps, declare that as a separate measurement
and objective change.

## Stopping, support avoidance and torque limits

There is no explicit progress/goal bonus or anti-stall reward in faithful or
contact. The training goal is a timeout-style termination and curriculum
progress check; the4 s stall rule is a separate evaluator failure gate.
Stationary forward tracking remains positive:
`r_lin=exp(-v_command²/0.25)`. At0.25/0.3/0.5/0.65 m/s, the **lost** linear
tracking reward versus perfect tracking is only0.00442/0.00605/0.01264/0.01631
per step. Standing can also avoid action-rate/acceleration/contact penalties
and retain yaw reward. Two saturated new severity costs0.0032 is below the
0.25 m/s tracking gap before other terms, but combined existing count plus new
severity costs0.0072 for two contacted saturated bodies, exceeding the0.3 m/s
gap for that step. A burst of penalties could encourage
slowing, hesitation or support avoidance even though mean added cost is low.
Do not respond by adding a progress bonus in the same ablation.

The foot exclusion permits the policy to transfer load to feet, which is
intended, but can also produce exaggerated lift, hopping, stiff landings or
out-of-corridor motion. Penalizing severity does not itself reward smooth
foot touchdown. Existing vertical-velocity/orientation and action/energy terms
help, but their presence is not a guarantee. Preserve the base/corridor gates
and exact ankle/calf geometry.

High external contact force does not imply motor saturation: the same620
full-trial torque-saturation fractions are about5.7–6.7e-6 at0.3 m/s and
1.33–1.47e-4 at0.5 m/s. An impact can be supported by geometry and inertia
without an actuator touching its envelope. The DC curve, calf45.43 Nm/15.70
rad/s and hip/thigh23.7 Nm/30.1 rad/s must remain unchanged. Continue reporting
computed-versus-applied torque clipping, joint velocities and applied torque;
do not soften hardware limits to regain reward.

No analytic gradient through `relu`, norm, max or clamp is required. HIM/PPO
collects rewards under `torch.no_grad`/inference, computes advantages/returns,
and updates policy log probabilities. A smooth real-valued reward still
provides more magnitude information than the1 N body count, but the150 N cap
removes that magnitude information above its limit. Do not promise gradient
of contact force will directly guide actions or change HIM's estimator loss.

## Required validation before claiming improvement

Before GPU training, use meaningful CPU tests for50/75/100/150 N boundary
values, independent clamp and sum over eight bodies, name mapping, feet/base
exclusion, current-versus-history selection, finite values and preservation
of every faithful/count term. Runtime metadata must save the full formula,
threshold50, force scale50, cap4, weight-0.02, selected names, effective dt,
checkpoint lineage, source hash, actor/estimator realized LR and starting
terrain-level distribution. Initial training readback should confirm that
all other rewards/physics match the continuation specification.

Use the existing frozen24-case tuning matrix at both0.3 and0.5 with identical
seeds and no threshold changes. Judge per-case/seed completion/stalls/falls/
escapes/base contact before an overall mean. Then compare leg-contact
fractions, force exceedance distribution (50/100/150 N and traced high
quantiles), applied torque/saturation, command tracking, pauses, action
second differences, root jerk and video. Full-batch body-wise force
quantiles require new diagnostics; sparse trace estimates remain labeled.
Compare motion with matched exposure as well as retaining all failure rows.
Lower force or lower action RMS achieved through longer pauses is not success.

Keep the20 ms trace vectors/poses added for the upcoming video as a first
localization aid. They still cannot recover all5 ms impacts or identify a
calf cylinder without contacts. Independent final geometry/material tests
should use a frozen selected policy and fresh seeds. If severity lowers
contacts but loses traversal, or further training improves traversal but
increases force/jerk, preserve that tradeoff rather than calling it smooth.

## Sources

- `isaaclab/stair_rewards.py`: faithful/contact configuration and reset-safe
  action/acceleration rewards; `isaaclab/stair_terrain.py:241` and`:332`: goal
  termination/curriculum; `isaaclab/run.py:375`: no-grad training collection.
- Pinned `isaaclab/envs/mdp/rewards.py:273`: count from per-body history peak;
  `:315`: exp velocity tracking; `isaaclab/managers/reward_manager.py:100`
  and`:129`: logging and dt scaling.
- `rsl_rl/rsl_rl/algorithms/him_ppo.py:102`,`:115`,`:157`: reward collection,
  return construction and clipped likelihood-ratio surrogate.
- `/home/cone/robotics/logs/himloco-overnight-20261011/contact670.log`:
  actual620-update reward terms and episode length.
- `stair-contact-severity-offline.json`: exact paths and sparse retrospective
  statistics; `go2-stair-contact-geometry-review.md`: source ownership and
  solid-overlap findings; `stair-refinement-comparison.md`: traversal and
  residual contact/action/jerk tradeoffs.
