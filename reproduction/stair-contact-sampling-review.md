# Stair evaluation contact sampling and current-force metrics

Reviewed on 2026-10-11 against the pinned Isaac Lab 3 / PhysX installation in
`isaaclab-local-lab-1`. The implementation changes only evaluation configuration,
telemetry and CPU regression tests. Training rewards, terrain, dynamics,
completion predicates and acceptance thresholds are unchanged.

## Installed sampling semantics, including older reports

The resolved Go2 task has `sim.dt=0.005`, `decimation=4`, contact
`update_period=0.005`, `history_length=3`, and initially
`scene.lazy_sensor_update=True`. The installed PhysX backend does not handle
policy decimation internally. `ManagerBasedRLEnv.step()` therefore runs four
physics steps and calls `scene.update(dt=physics_dt)` after each one.

The generic `SensorBase.update()` is lazy without `force_recompute`, but this is
**not sufficient evidence to classify this contact sensor as lazily sampled**.
The installed `BaseContactSensor.update()` overrides it: positive-length history
calls `_update_outdated_buffers()` during scene updates even if the scene is
lazy. The PhysX `ContactSensor` inherits that method. This is also documented in
the installed `ContactSensorCfg.history_length` field. Repeated `.data` reads in
the same generation do not add another history entry.

Consequently, the older standard370/standard340 reports are consistent with
5 ms contact history under this pinned source. An earlier concern that their
history necessarily consisted of 20 ms snapshots was incorrect. They did not
record runtime contact timestamps or sampling metadata, so this is an inference
from their saved configuration and the installed implementation, not a new
measurement of their old runs.

At a policy boundary `T`, after warming up the history:

| Quantity | Pinned Go2 evaluation value |
| --- | --- |
| Physics interval | 0.005 s |
| Policy measurement interval | 0.020 s |
| Contact history length | 3, current included |
| History order | Newest first |
| Sample ages | 0, 0.005, 0.010 s |
| Oldest retained sample age | 0.010 s |
| Nominal count window | 3 × 0.005 = 0.015 s |
| All four physics substeps retained at boundary | No |

The nominal count window is not the time between oldest and newest sample.
A contact confined to the first substep, `T-0.015`, can be sampled and then
overwritten by the final substep before the evaluator reads history. History
length is intentionally preserved at three; increasing it would alter the
existing detection semantics and needs a separate experiment. Reset rows start
with zero history, not with previous-episode contact samples.

The evaluator now explicitly sets `scene.lazy_sensor_update=False` when
supported and sets contact `update_period` to physics dt. This makes its scene
refresh request explicit. It does not establish that older contact history was
lazy, and it does not change a training configuration created in a different
process. Eager refresh also applies to the other scene sensors, so runtime cost
should be checked in the next scheduled GPU evaluation.

## Metrics and provenance

Existing `base_contact_step_fraction`, `shank_contact_step_fraction`,
`contact_foot_horizontal_speed_m_s` and `foot_slip_fraction` remain available.
They retain their history-peak calculations. Goal support and fall detection
also retain their existing history fields and thresholds.

The new metrics use only the latest force sample at the policy boundary:

| New metric | Denominator / interpretation |
| --- | --- |
| `current_sample_base_contact_step_fraction` | Valid first-episode environment samples after the first second |
| `current_sample_shank_contact_step_fraction` | The same samples; any selected calf/thigh/shank above the contact threshold |
| `current_sample_contact_foot_horizontal_speed_m_s` | Current-contact foot samples, not all feet or all environment steps |
| `current_sample_foot_slip_fraction` | Fraction of current-contact foot samples with world-horizontal link speed above 0.10 m/s |

The contact-foot denominator is independent for history and current metrics.
An empty denominator yields JSON `null`, not a fabricated zero. Trial and case
`contact_sample_counts` expose the actual denominators. New
`current_sample_base_contact_envs` and `current_sample_shank_contact_envs` count
any current contact during the entire measured first episode, including its
first second, just as the legacy environment contact counters do. Trace rows
include current foot flags and current base/shank forces beside the old fields.

Forces are norms of per-body **net normal force vectors in world coordinates**.
They include horizontal normals from vertical risers; checking only world-z
would miss these. They do not include aggregate tangential friction force.
Foot contact requires strictly more than 1 N. Base/shank metrics use the existing
`contact_force_n` threshold, default 1 N. No threshold was relaxed.

Even the current metrics are slip proxies: force and link velocity refer to the
same policy boundary, but world-horizontal foot-link speed is not the tangential
velocity at an actual contact point. Legacy history gating can include a foot
that has already entered early swing. Current sampling can miss brief impacts
earlier in the policy step. Neither fraction is a measurement of exact scraping
duration or damage.

Each new policy report includes `contact_sampling` with semantics version 2,
sensor type and update method, physics/policy/update intervals, history length,
lazy flag, backend decimation flag, inferred history cadence and age, thresholds
and measurement scopes. The known installed `BaseContactSensor.update` identity
is recognized as an eager history override even with a lazy scene. Unknown
method/backend combinations are not assigned a fictitious physics cadence.
The metadata explicitly says its cadence is inferred from configuration and
the installed step loop; it does not claim runtime timestamps were measured.

Reports without this metadata retain their original meaning. Comparison of
old and new history metrics should first verify the same pinned implementation,
physics/update intervals, history length, force threshold and sample mask.
There are no old current-force metrics to reconstruct from the coarse traces.

## Source evidence and verification

Paths below are relative to `/workspace/isaaclab` in the existing container:

- `source/isaaclab/isaaclab/envs/manager_based_rl_env.py`: outer decimation loop
  and scene updates, lines 229–244.
- `source/isaaclab/isaaclab/scene/interactive_scene.py`: scene sensor refresh,
  line 545.
- `source/isaaclab/isaaclab/sensors/contact_sensor/base_contact_sensor.py`:
  eager positive-history override, lines 65–75.
- `source/isaaclab/isaaclab/sensors/contact_sensor/contact_sensor_cfg.py`:
  history update contract, lines 73–75.
- `source/isaaclab/isaaclab/sensors/sensor_base.py`: generation guard,
  lines 407–419.
- `source/isaaclab_physx/isaaclab_physx/sensors/contact_sensor/kernels.py`:
  reset zeroing and newest-first insertion, around lines 139 and 283–289.
- `source/isaaclab_physx/isaaclab_physx/sensors/contact_sensor/contact_sensor.py`:
  normal-force fetch using physics dt, around line 502.

The CPU evaluator suite passes 23 tests, including history-only contacts with
zero current force, matching current/history denominators, reordered bodies,
horizontal riser normals, strict thresholds, eager/unknown/lazy cadence labeling,
configured zero history despite an allocated slot, slower update periods,
and backend decimation without falsely claiming substep coverage,
pre-reset capture and unchanged full-flight/final gates:

```bash
docker exec -e CUDA_VISIBLE_DEVICES= -w /workspace/himloco/isaaclab \
  isaaclab-local-lab-1 /isaac-sim/python.sh -m unittest test_stair_evaluation -v
```

The actual stock task configuration is additionally resolved on CPU with a
temporary copied policy group assigned to its otherwise absent critic field
(the HIM adapter supplies a critic group in normal use). This confirms the
lazy flag exists and evaluation changes it to false while preserving physics
dt, decimation and history length: `True, .005, 4, .005, 3` becomes
`False, .005, 4, .005, 3`. No GPU rollout was started for this review;
live new metrics must be checked in the parent's next serial evaluation.
