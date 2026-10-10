# Go2 domain randomization: actual parameter readback

Reviewed on 2026-10-11 against the existing container `isaaclab-local-lab-1`,
Isaac Lab 3 at `/workspace/isaaclab`, and its `isaacsim_physx` Go2 configuration.
No driver, system, or simulator installation was modified. All checks performed
for this review use CPU only; the GPU smoke runs are a separate runtime check.

## API compatibility and expected physical parameters

The real task configuration was resolved with
`resolve_task_config("Isaac-Velocity-Rough-UnitreeGo2", "", overrides=["physics=isaacsim_physx"])`.
For both profiles, every event parameter bound successfully to the installed
event's `__call__` signature, rather than to a mock signature. DCMotor is an
IdealPDActuator subclass in this installation.

| Quantity | Basic | Robust | Actual readback |
| --- | --- | --- | --- |
| Base mass | Existing log-uniform 0.8–1.25 × original mass | Same | `robot.data.body_mass.torch[:, base_ids]` |
| Base inertia | Existing `recompute_inertia=True` default, scaled with mass | Same | `robot.data.body_inertia.torch[:, base_ids]`, flattened 3×3 |
| Base COM offset x/y/z | ±0.01 / ±0.01 / ±0.005 m | ±0.03 / ±0.02 / ±0.01 m | `robot.data.body_com_pose_b.torch[:, base_ids, :3]` minus cached original |
| Foot static friction | 0.6–1.1 | Same | PhysX shape materials, component 0 |
| Foot dynamic friction | 0.5–1.0 and ≤ static | Same | PhysX shape materials, component 1 |
| Foot restitution | 0 | Same | PhysX shape materials, component 2 |
| Actual actuator kp | 25 | 22.5–27.5 | `robot.actuators["base_legs"].stiffness` |
| Actual actuator kd | 0.5 | 0.45–0.55 | `robot.actuators["base_legs"].damping` |

Mass, COM and materials are startup events. Robust gains are reset events and
start from fixed original defaults each reset. The terrain material remains
static/dynamic 1.0 with `multiply` friction combine mode. Only feet are selected
by the replacement material event; the original material event's whole-body
selection is not retained. Motor strength and action delay are not randomized.

The installed signatures accept `make_consistent=True`, `com_range`, and
`operation="scale"` with stiffness/damping distribution parameters. Explicit
DCMotor gains are owned by the actuator tensors. The solver's
`robot.data.joint_stiffness` may remain zero: it is not evidence that PD
randomization failed.

## Capture function and baseline meaning

`isaaclab/stair_randomization.py:capture_domain_parameters(env)` returns a
JSON-safe report after the environment's initial reset and at later resets.
It reads all current environments, emits min/max/mean/std and the first three
environment rows, and does not invoke events, physics setters or RNG. Lab
getters may refresh their normal read caches. Missing independent fields are
reported as `{"status": "unavailable", "reason": "..."}` without hiding
other measurements.

For original mass/inertia, use the original tensors cached in the instantiated
`add_base_mass` event, obtained via
`env.event_manager.get_term_cfg("add_base_mass").func.default_mass` and
`.default_inertia`. The deprecated `data.default_mass` property captures the
value at its first read and can accidentally call already randomized mass
"default". The helper therefore avoids it. The report also compares actual
inertia to original inertia × current/original mass.

For original COM, use `base_com.func.default_com`. The quaternion must remain
unchanged. With profile `none`, an absent COM event means original COM offsets
cannot be reconstructed from live values alone; the report says so.

For PD, robust uses the event's `default_actuator_stiffness` and
`default_actuator_damping`. Without a gain event, the helper labels values
resolved from the explicit actuator configuration as a **configured reference**;
it does not claim they are a recorded pre-randomization snapshot. This preserves
usefulness for profile `none` and `basic`.

Material readback uses
`wp.to_torch(robot.root_view.get_material_properties())` in backend shape order.
Public foot IDs are mapped once through `robot.map_body_ids_to_backend`, then
mapped to collision shapes using per-body shape counts. The selected foot
values are checked against the event's cached 64-material bucket pool. Material
events do not retain pre-randomization materials, so an original material
snapshot is explicitly unavailable. The helper targets this pinned PhysX API;
other backends with different view APIs get explicit unavailable reasons.

## Minimal integration and smoke checks

Immediately after `robot` and the environment are available and the initial
reset is complete (before training), and optionally once again after training:

```python
from stair_randomization import capture_domain_parameters
(log_dir / "domain-parameters-initial.json").write_text(
    json.dumps(capture_domain_parameters(env.unwrapped), indent=2)
)
```

If `env` already refers to the raw manager environment, pass `env` directly.
The helper does not inspect command-line profile names; it reads live values
with any event configuration, including `none`.

Run GPU jobs serially, after the existing training job finishes:

```bash
./isaaclab/run.sh train --terrain stairs --stair_stage bootstrap \
  --domain_profile basic --num_envs 64 --steps_per_env 24 \
  --max_iterations 2 --run_name domain-basic-smoke --viz none --headless
./isaaclab/run.sh train --terrain stairs --stair_stage bootstrap \
  --domain_profile robust --num_envs 64 --steps_per_env 24 \
  --max_iterations 2 --run_name domain-robust-smoke --viz none --headless
```

Two optimizer updates verify training/runtime compatibility, not climbing or
robustness. Readback must have available, finite current values in expected
ranges. Require variation across 64 environments for mass, COM and foot
materials; require variation of robust actuator gains and unchanged basic
gains. Basic/robust COM offsets must stay inside their axis-specific limits,
inertia must match mass scaling, foot dynamic friction must be ≤ static, and
all measured foot material triples must belong to the bucket pool. A later
capture proves robust reset gains remain inside the same ranges; each current
value should be compared with its own saved original baseline.

## Verification performed

The CPU suite uses the real DCMotor and actual mass/COM/gain event classes with
a fake physics storage boundary. It checks actual randomized readbacks against
their cached defaults, backend body/shape ordering, repeated gain resets,
missing-field reasons, strict JSON serialization, and unchanged RNG and input
tensors during capture. It does not construct a simulator or touch GPU work.
All 9 CPU tests passed (6 existing configuration tests and 3 readback tests).
Actual GPU readback evidence must come from the separate smoke result files.

The first live PhysX readback was independently inspected from
`isaaclab/logs/2026-10-11_02-29-54_standard200-core-progress/`
after its single reset-seed 29 evaluation finished. Initial and final parameter
reports are exactly equal, as expected with evaluation dynamics disabled.
All live current fields were available and finite. Across its 128 environments,
base mass is 6.92100048 kg, actuator kp/kd are exactly 25/0.5, and the asset's
local COM position is `[0.021111997, 0, -0.005366]` m. The four feet are public
and backend bodies 15–18, mapped to collision shapes 23–26. Their actual material
is `[static 0.8, dynamic 0.6, restitution 0]` on every selected shape, and every
triple belongs to the cached bucket pool. Original mass/COM event baselines are
explicitly unavailable because this evaluation removes those events. These are
expected absences, rather than failed actual reads. This validates the helper
against the live PhysX APIs for profile `none`; basic/robust randomization still
needs the separate smoke checks.

## Late PPO KL observation and isolation experiment

In `stairs-bootstrap-discovery120`, final update 119 has mean KL 0.07115058,
maximum minibatch-mean KL 0.23751044 and clip fraction 0.49542189. Its schedule
was fixed at 3e-4. The last 20 updates have mean KL 0.02392500. At update 119,
estimator MSE 0.00520003 did not spike (update 118: 0.00516116). These aggregate
metrics cannot assign the KL spike to actor updates or the HIM encoder.

Within each minibatch, the actor distribution and KL are computed using a
detached HIM estimate; then the estimator is updated before the PPO optimizer.
The next minibatch uses the changed encoder. An encoder change can therefore
shift inference action means even with fixed actor weights. This is a
plausible mechanism, not a demonstrated cause of this particular spike.

For a small isolation experiment, record one representative rollout batch
(history, next critic observation, saved mean/std and minibatch permutation).
Load the same checkpoint and optimizer state into two independent CPU copies.
Hold actor and std fixed. Apply only estimator updates to copy A with the
recorded batches; leave copy B unchanged. On the same held-out histories,
compute deterministic `act_inference()` means before/after and exact
equal-variance Gaussian KL `sum((mu_before - mu_after)^2 / (2 * std^2))`.
Record velocity/latent changes and estimator losses as well. Copy B should
produce exactly zero mean shift. If using learning-rate zero as the control,
note that prototype normalization still runs, although prototypes are absent
from inference. A genuine frozen estimator copy is cleaner.

To quantify contributions during full PPO, capture inference means on the
fixed batch immediately before estimator update, after estimator update, and
after actor update; report each mean displacement and distribution KL. Their
KL values do not add linearly. Training with an estimator frozen for a short
matched run is a separate explicitly labeled ablation. No estimator or PPO
behavior has been altered in this review.
