# Force720 runtime audit and frozen-policy validation commands

CPU-only independent audit on 2026-10-11; no GPU task or Git mutation was
started. Commands below are a **future execution template**, not executed
results. The policy must be frozen from tuning before these final tests.

## Runtime checks

`isaaclab/logs/2026-10-11_04-45-41_stairs-hard-force720/config.json` confirms:

- Checkpoint is archived `artifacts/go2-stairs-contact620/model_620.pt`;
  100 additional updates, 4096 environments, seed 1, speed range 0.25–0.65,
  policy dt 0.005 × 4 = 0.02 s, fixed LR 1e-4 and checkpoint Adam retained.
- Realized PPO/HIM learning-rate attributes **and both Adam group rates**
  are 1e-4, resumed iteration 620. No exploration-standard-deviation override.
- `resolved_leg_reward_body_selections` for count and force proxy are exactly
  equal: FL_thigh/FL_calf/FR_thigh/FR_calf/RL_thigh/RL_calf/RR_thigh/RR_calf.
- `faithful→contact` changes only `leg_contacts=-0.1`.
  `contact→contact_force` changes only `leg_contact_force_proxy=-0.02`.
  A CPU full-term-config comparison confirms prior weights/functions/parameters
  are identical, rather than checking weight dictionaries alone.
- Hard terrain variant hash matches contact670 and faithful-control670:
  `803cbcdff5fbdffadf6e33cdd555dbcc734a738af81d0b64f588934d9e5b9795`.
  Those runs also use seed 1, 4096 environments, speed range 0.25–0.65,
  maximum initial level 4 and 20 s training
  episodes. The first four saved root initial positions agree exactly.

`start_level=4` sets **maximum initial level 4**; pinned
`terrain_importer.py:401` samples levels uniformly from integers 0…4. It does
not place every environment at level 4. The complete realized initial level
array is not persisted, so only distribution/configuration equality and the
recorded initial rows are verified. `source_commit=7bd0bfd` and
`source_tracked_files_dirty=True` are the launch records; do not call this
run clean. The subsequent `b7c22c8` change contains reports/analyzer artifacts,
not training/control source, but no exact startup diff snapshot is stored.
Preserve this provenance and freeze the final reviewable source before final
evaluation.

The new term is `sum_i min(relu((F_i−50)/50)^2,4)`, where `F_i` is the peak
net contact-force norm in each body's retained history. At ≥150 N its extra
cost is 0.0016/body/policy step, so it stops distinguishing 150/292/489 N.
Offline contact620 descent mean costs are 3.63e-5 at 0.3 m/s and 4.86e-5
at 0.5 m/s per step. It targets high-force contacts
without zeroing or doubling all contacts. It is not impulse, energy or damage.
Keep pause/stall/tracking and contact/jerk/video checks: two capped bodies plus
existing count cost 0.0072/step, enough to exceed the 0.3 m/s linear tracking
gap 0.00605 for that step. Reduction through stopping/support avoidance is not
an improvement. No differentiable simulation/contact gradient is required.

## Duration and heading scope

The frozen 16-case final JSON has two 12-step/0.25 m-tread flights. Their last
riser is at x = 3.75 m, the final platform begins at x = 4.0 m and the root
goal is at x = 4.65 m. With randomized start x ≥ −0.08 m and 0.5 s goal dwell,
nominal 0.3 m/s travel requires at most
`(4.65+0.08)/0.3+0.5=16.27 s`; 0.5 m/s requires 9.96 s. **40 s is adequate**
without weakening the unchanged 4 s/0.05 m stall rule. Count every case × seed
with ≥32 rows and the existing final 95% gate (31/32), zero base contacts and
numerical failures, and existing fall/stall/escape limits.

The default evaluator includes an external heading controller every 20 ms:
`command_wz=clamp(-1.0*root_yaw,−0.5,+0.5)` rad/s, target yaw 0. Its inputs are
root yaw only; it supplies an ordinary policy velocity command, with no
lateral-position correction. The policy executes after this command update
(`stair_evaluation.py:478`). Reports should say:

> The frozen HIM policy is evaluated with an external proportional heading
> controller (gain 1 s⁻¹, yaw-rate command limit ±0.5 rad/s) and nominal dynamics.
> This is a policy-plus-heading-controller traversal result.

`--open_loop_heading` sets yaw-rate command identically zero. It removes only
that external heading correction; the policy still uses IMU/joint feedback.
Call this a **zero yaw-rate-command stress test**, not an open-loop robot.

## Executable templates after selection

Run from the repository root. Set both variables to the frozen checkpoint and
its documented profile; keep them fixed through the tests. `--viz none` is
the supported headless option; this CLI has no `--headless` flag.

```bash
selected_checkpoint='<frozen checkpoint inside this repository>'
selected_profile='<contact or contact_force, matching frozen checkpoint>'

final_eval() {
  bash isaaclab/run.sh evaluate --terrain stairs \
    --checkpoint "$selected_checkpoint" --reward_profile "$selected_profile" \
    --stair_batch reproduction/stair-heldout-final.json --num_envs 512 \
    --eval_seconds 40 --eval_randomized \
    --eval_seed 101 --eval_seed 211 --eval_seed 307 --seed 1 --viz none "$@"
}
final_eval --speed 0.3 --domain_profile none --run_name frozen-final-speed03
final_eval --speed 0.5 --domain_profile none --run_name frozen-final-speed05
```

### Material isolation

`none` inherits an **all-robot-body** material event. `basic` replaces it with
**foot-only**. `--friction` modifies the selected event's ranges, not its body
selector. Therefore compare all three values within **basic**, first a new
nominal 0.8/0.6 control, then low 0.45/0.35 and high 1.0/0.8, without
`--eval_dynamics`. CPU config construction confirms mass/COM/gain events are
removed in all three, while terrain coefficients are 1/1. Each call constructs
a new scene; use the same frozen policy, cases, seeds and speed:

```bash
final_eval --speed 0.3 --domain_profile basic --friction 0.8 0.6 \
  --run_name frozen-foot-nominal-speed03
final_eval --speed 0.3 --domain_profile basic --friction 0.45 0.35 \
  --run_name frozen-foot-low-speed03
final_eval --speed 0.3 --domain_profile basic --friction 1.0 0.8 \
  --run_name frozen-foot-high-speed03
```

These commands establish material sensitivity only at 0.3 m/s; repeat the same
nominal/low/high trio at 0.5 m/s before claiming both-speed material robustness.
The basic preset manifest is generated before fixed-friction override and may
advertise stale ranges; use `friction_override` plus actual foot material
readback. Confirm terrain mesh's physics binding and authored 1/1, restitution 0
and multiply combine modes in `terrain_material`. Pair-effective solver
coefficients remain unavailable. Do not contrast `none` nominal directly
against basic low and attribute all differences solely to foot friction.

### Dynamics with fixed nominal foot material

To examine mass/COM/PD variability while keeping foot friction nominal, use
`--domain_profile robust --eval_dynamics --friction 0.8 0.6`. It retains
startup mass factor 0.8–1.25, COM bounds ±0.03/0.02/0.01 m and reset PD factors
0.9–1.1. This is
combined mass/COM/PD variation, not a single-parameter effect:

```bash
for construction_seed in 71 73 79; do
  final_eval --speed 0.3 --domain_profile robust --eval_dynamics \
    --friction 0.8 0.6 --seed "$construction_seed" \
    --run_name "frozen-dynamics-seed-$construction_seed-speed03"
done
```

The later `--seed` replaces `final_eval`'s default 1 because argparse accepts
the last scalar occurrence; reset seeds 101/211/307 stay fixed. Each call is a
new construction seed/scene. This planned dynamics test always fixes foot
friction to 0.8/0.6; the three material tests above cover friction separately.
Startup properties remain
fixed across reset seeds in one scene, but PD gains resample at each reset.
Initial/final PD summaries can include later automatic resets and do not
provide exact first-episode row-to-gain pairing. Existing readbacks verify
applied distributions only at capture times. Repeat speed 0.5 m/s separately if
that scope is required and time permits.

### Minimum heading stress coverage

Use **`stair-validation-core-standard.json`**, which has 12 cases; the similarly
named `stair-validation-standard.json` has only 8. With 384 environments there
are 32/case. One 0.3 m/s zero-yaw run with 3 reset seeds covers all six standard
geometries in both directions. For clean attribution, run a matching heading
baseline with the exact same 12-case batch, construction seed and reset seeds:

```bash
standard_heading_eval() {
  bash isaaclab/run.sh evaluate --terrain stairs \
    --checkpoint "$selected_checkpoint" --reward_profile "$selected_profile" \
    --stair_batch reproduction/stair-validation-core-standard.json \
    --num_envs 384 --speed 0.3 --eval_seconds 40 --eval_randomized \
    --eval_seed 401 --eval_seed 409 --eval_seed 419 \
    --domain_profile none --seed 1 --viz none "$@"
}
standard_heading_eval --run_name frozen-standard-heading-control
standard_heading_eval --open_loop_heading --run_name frozen-standard-zero-yaw
```

Those reset seeds are proposed new seeds, not asserted unused; check the run
inventory before calling them fresh. If budget allows only the zero-yaw run,
compare scope-limited case statistics to existing baseline and state that
startup/reset rows are not a matched 12-case pair. Report per-case/seed
completion, escape, heading/lateral error and tracking/contact/motion metrics.
Do not loosen lane gates for this stress test. If it fails, say:

> Nominal traversal passed with external heading correction. The separate
> zero yaw-rate-command standard-stair test shows the stated directional
> stability limits; independent heading robustness is not established.

The minimum supplementary scope is standard 12 cases at 0.3 m/s. It does not
prove heading robustness on the 16-case final set, 0.5 m/s speed or low-friction/dynamics
conditions. Keep the selected checkpoint frozen regardless of the outcome.

## Static template validation

All four Bash fences passed `bash -n`. A shadow `bash` function captured the
ten expanded command argument lists without executing `run.sh`; all ten
passed the actual argument definitions extracted from `run.py` by AST.
The launcher option `--viz none` was checked separately. Construction seeds
71/73/79 override the default scalar seed correctly while the appended reset
seeds remain 101/211/307. This checks syntax and CLI types/options only; the
checkpoint/profile placeholders still require a frozen real selection, and
none of these evaluation templates has been run as part of this audit.

## Actual frozen-validation script audit

`reproduction/run-frozen-stair-validation.sh` now checks the plan before any
output directory creation and again before each simulation launch. Required
top-level freeze fields are `status="frozen"`, `checkpoint`, `reward_profile`
and `checkpoint_sha256`. The requested checkpoint must resolve to that exact
file inside this repository, and its SHA-256 must match. The existing final
geometry, standard heading geometry and acceptance-file paths and hashes must
also match. Required heading fields are `heading_geometry_file` and
`heading_geometry_sha256`. A nonempty `implementation_source_sha256` mapping
must include `isaaclab/run.py`; its keys are repository-relative runtime Python
paths, including the vendored algorithm files and excluding tests. Every
listed source file is hash-checked before every launch. `source_git_commit`
records provenance and is not a guard restriction, so report-only changes can
be committed without invalidating the frozen algorithm. The guard
rejects protocol fields that differ from the script's durations, counts,
seeds, speeds, material pairs, dynamics schedule or flat commands. A copy of
the accepted plan is saved with the output logs.

Execution order prioritizes the two nominal speeds, the three foot-material
scenes, the paired heading scenes and flat regression; the three dynamics
construction seeds run last. Each launch prints start/end wall-clock times,
elapsed time to milliseconds and process exit status. No automatic skipping
or budget-based stopping is added.

CPU-only temporary repository fixtures verified all 11 actual expanded CLI
calls: eight final-matrix scenes (including three construction seeds for
combined dynamics), two paired heading scenes, and one flat scene. Eight
invalid initial freeze fixtures and ten additional heading/source fixtures
were rejected before any simulator call or log directory creation. Altering
the checkpoint or runtime source after the first shadow launch was rejected
before the second launch. Report-only changes and a different provenance-only
`source_git_commit` were accepted. `bash -n` and whitespace checks pass.
No actual validation scene was launched in these checks.

All staircase calls retain matching zero-action controls. The requested
duration ceiling is 10 × 40 s × 3 reset seeds × 2 controllers = 2400
simulation seconds, plus six flat commands × 20 s × 2 controllers = 240 s.
At 20 ms policy/5 ms physics cadence this is at most 132,000 policy-batch
steps and 528,000 physics-batch steps. Staircase trials stop when all their
first episodes finish or fail, so actual steps are lower; flat trials
normally execute their full duration. These simulated durations are not
wall-clock predictions, and environments run in parallel.

The flat call explicitly retains the frozen profile and uses
`--warm_start reset` to transfer actor/HIM tensors into the flat critic architecture. It
does not train the policy; six forward/backward/lateral/turn commands and
matching zero-action controls exercise behavior outside staircase tracking.
A CPU transfer check copied 22 actor/HIM/std tensors, retained eight fresh
critic tensors, produced bit-identical actions on 17 observation rows, and
kept weights unchanged after five inference calls without optimizer updates.
Flat regression uses one nominal seed and does not establish flat robustness
across reset seeds or randomized dynamics.

Recent 768-environment suites used roughly 1.42–4.35 wall seconds per actual
simulation second, with about 9–10 s from scene metadata to policy export.
A successful 10-scene stair workload around 600–780 simulation seconds plus
the flat suite gives a planning estimate of **25–70 minutes**, before any
teardown hangs or continuous-video recording. Trials that frequently reach
the full 40 s limit can increase this to roughly 1–3 hours. The 30 s teardown
watchdog can add up to 5.5 minutes across 11 launches. These are estimates
from recent runs, not a completion deadline or benchmark guarantee.

The script does not record video or dense 20 ms traces. Freeze-matched,
policy-only recordings in both directions remain a separate required step
before a continuous smoothness claim. Source-manifest coverage depends on
recording all relevant runtime modules, not just their entry point.
Acceptance SHA-256 freezes the declared criteria, while `assess_final`
currently applies matching hardcoded defaults rather than loading that JSON.
Simulation process exit success means results were produced; inspect each
saved `result.json` and `final_acceptance` to decide whether a gate passed.
