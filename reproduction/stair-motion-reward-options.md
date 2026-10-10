# Optional leg-contact reward ablation after faithful stair validation

This is an experiment proposal, not a change to the training objective.
Continue the current faithful curriculum first and inspect its stair videos.
Keep algorithm, actor history, critic inputs and existing evaluation gates fixed.
Any added reward should be named as a Go2 adaptation, rather than a faithful
reproduction of the released objective.

## Existing objective and evidence

`configure_stair_rewards(..., profile="faithful")` clears stock reward terms
and reinstalls the released tracking, vertical/angular velocity, orientation,
joint acceleration, power, base height, body-relative foot clearance, and
first/second action-difference terms. There is no thigh/calf contact penalty.
The released Go1 configuration selects thigh/calf/base as collision bodies but
sets `collision=-0.0`. The pinned Go2 stock task also has no active
`undesired_contacts` reward. Absence of this term is therefore deliberate in
the faithful baseline.

The standard staircase validation uses 12 geometry cases × 32 environments ×
3 reset seeds. At 0.3 m/s, both checkpoints complete 1152/1152 environments
with no base contacts. Values below are arithmetic means of the three logged
trial metrics; pause is the maximum across all trials:

| Metric | model340 | model370 |
| --- | ---: | ---: |
| History-gated leg contact sample fraction | 0.18293 | 0.20175 |
| History-gated foot slip proxy fraction | 0.21658 | 0.20958 |
| Action first-difference RMS | 0.17874 | 0.16392 |
| Action second-difference RMS | 0.09100 | 0.07908 |
| Root linear jerk RMS (m/s³) | 52.514 | 46.288 |
| Longest flight pause (s) | 0.240 | 0.960 |

At 0.5 m/s, model370 again completes 1152/1152 with no base contacts. Its
three-trial mean history leg fraction is 0.20558, slip proxy fraction 0.22885,
action first/second-difference RMS 0.24174/0.13082, and jerk RMS 66.837 m/s³.
Its longest pause is 0.120 s. These are a different commanded speed and should
not be used as a matched improvement comparison with the 0.3 m/s rows.

Evidence files:

- `isaaclab/logs/2026-10-11_03-04-27_standard370-low-speed-validation/result.json`
- `isaaclab/logs/2026-10-11_03-04-27_standard370-low-speed-validation/candidates/0_model_340/result.json`
- `isaaclab/logs/2026-10-11_03-08-49_standard370-speed05-validation/primary-result.json`

The evidence supports a tradeoff: model370 has smaller action differences and
root jerk while its history leg contact fraction is higher. It does not prove
that stronger action smoothing would remove scraping. The fractions are
policy-boundary contact indicators, not exact contact duration or severity.
The all-body peak force can be a foot impact and cannot be attributed to legs.
Video and per-leg force observations are needed to establish the actual scrape.

The installed contact sensor refreshes nonempty history every physics step
despite the default lazy scene flag. With 5 ms physics and history length 3,
the boundary retains the current sample and the preceding 5/10 ms samples.
See `stair-contact-sampling-review.md` for the verified source and limits.
History-gated foot speed can count early swing; new current-contact metrics
reduce that mismatch but remain link-speed proxies.

## First ablation: one small leg-contact term

If scraping remains visible after the faithful hard-stair curriculum, first
compare the unchanged faithful reward against **faithful plus one
`undesired_contacts` term**. Do not switch wholesale to `tuned`: that profile
also reduces the vertical velocity penalty from -2 to -0.5, halves the
orientation penalty, and adds a feet-slide term, confounding attribution.

The installed `isaaclab.envs.mdp:undesired_contacts` function is compatible
with this sensor API and counts selected bodies whose history force-vector
norm exceeds the threshold. A minimal proposed term is:

```python
RewardTermCfg(
    func="isaaclab.envs.mdp:undesired_contacts",
    weight=-0.1,
    params={
        "sensor_cfg": SceneEntityCfg(
            "contact_forces", body_names=[".*_thigh", ".*_calf"]
        ),
        "threshold": 1.0,
    },
)
```

The selector resolves the eight `FL/FR/RL/RR_thigh` and
`FL/FR/RL/RR_calf` bodies in the Go2 asset. Exclude feet and hips in this first
experiment; base contact already causes evaluation failure. Assert the resolved
names so a future asset naming change does not silently select nothing or feet.

The -0.1 weight is a starting hypothesis, not a calibrated optimum. Isaac Lab's
reward manager multiplies weights by policy dt: at 0.02 s, one violating leg
body contributes -0.002 for that policy step, versus at most +0.030 from the
combined velocity tracking terms. Multiple simultaneous violating bodies add
their counts. A 20% any-leg-contact sample fraction does not tell us the mean
number of violating bodies, so it cannot alone estimate the penalty budget.

Use the same 1 N threshold initially to preserve the detection definition.
It is a touch threshold, not a damaging-force threshold. Consider 5/10 N only
after collecting per-leg force distributions, and label those as separate
ablations; do not change the acceptance threshold to make contact disappear.
This reward uses recent history and penalizes touching, without distinguishing
brief incidental contact, support, or sustained sliding.

Start baseline and ablation from the same frozen checkpoint. Keep the terrain
stage/distribution, command ranges, domain profile, seeds, environment count,
update budget, PPO settings, and optimizer resume/reset policy identical.
Evaluate both on unchanged standard stairs and held-out hard stairs at matched
0.3/0.5 m/s, with the same reset seeds and physics/sensor cadence. Report
completion, failures, speed tracking, both leg-contact sample fractions,
current/history slip proxies, action differences, jerk, pauses, and videos.
Watch for higher stepping/jumping, slower travel or larger action changes: a
policy can reduce leg contact while making another motion property worse.

## Larger fallback if the single-term result is insufficient

A bounded per-leg force-excess penalty is the next simpler option. For example,
sum a clipped, dimensionless excess above a chosen normal-force threshold on
the same eight bodies using the **current** force sample. Choose force scale
and cap from measured leg-force distributions; normalize the body count or
explicitly retain it in the weight budget. This adds severity sensitivity while
avoiding unbounded response to impacts. It still cannot distinguish scraping
from load-bearing contact and remains a separate Go2 objective change.

A more targeted scraping penalty can combine same-time per-leg normal force
with relative tangential contact-point velocity. It requires actual contact
points and surface/contact normals, body angular velocity and
`v_point = v_link + omega × offset`, plus the contacted body's point velocity
if that body moves. Filtered contact points/normal and friction data in the
installed PhysX sensor may support this, but it is a larger implementation and
validation task. Simply multiplying a historical contact peak by current
world-XY link speed would reproduce the existing temporal mismatch and would
mislabel stair-riser motion as tangential slip.

Use exactly one fallback definition per controlled experiment. The actor
remains terrain blind with 45 observations × 6 history frames = 270 inputs;
the HIM estimator, critic and existing action smoothness terms stay fixed.
Do not infer a universal “silky” threshold from these uncalibrated metrics.

## CPU compatibility checks already performed

The installed `undesired_contacts` implementation reads
`net_normal_forces_w_history.torch`, computes the per-body maximum vector norm
over history, applies strict `> threshold`, and sums body violations. An
independent CPU boundary check yields `[1, 1, 0, 0]` for a horizontal 2 N leg
normal, a 2 N historical leg contact with zero current force, exactly 1 N, and
a 100 N excluded foot respectively. This proves API/selection behavior, not
the effectiveness of any added reward. No reward ablation or GPU job was
started by this review.
