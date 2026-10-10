# Final staircase protocol and hard570 failure review

Independent CPU review on 2026-10-11. No GPU rollout, reward change, training
change or threshold change was made for this review. The only executable change
is evaluation metadata clarifying startup versus reset-time dynamics sampling;
25 evaluator CPU tests pass.

## Verified hard570 versus hard520 tradeoff

Both checkpoints were evaluated in the same frozen 24-column environment at
0.3 m/s, with 32 environments per case and randomized reset seeds 11/29/47.
The geometry, all saved initial root positions, and initial reset distribution
summaries are exactly equal between the primary and candidate reports.
Nominal dynamics were used; physical readback has base mass 6.92100048 kg,
kp/kd 25/0.5, foot static/dynamic friction 0.8/0.6 and zero restitution.

Evidence:

- `isaaclab/logs/2026-10-11_03-53-37_hard570-regression-and-tuning/primary-result.json`
- `isaaclab/logs/2026-10-11_03-53-37_hard570-regression-and-tuning/candidates/0_model_520/result.json`
- The same directory's `config.json` and `domain-parameters-initial.json`.

| Measurement | hard520 | hard570 |
| --- | ---: | ---: |
| Completed environments | 2151/2304 | 2189/2304 |
| Fall flags | 0 | 8 |
| Stall flags | 153 | 75 |
| Lateral escape flags | 0 | 33 |
| Environments with base contact | 0 | 7 |
| Case × seed final traversal gates passed | 58/72 | 50/72 |
| 8 cm / 30 cm ascent completions by seed | 32, 32, 32 | 23, 23, 26 |
| 12 cm / 30 cm ascent completions by seed | 31, 32, 32 | 21, 26, 27 |
| 14 cm / 27 cm ascent completions by seed | 12, 10, 12 | 28, 30, 29 |
| 16 cm / 27 cm ascent completions by seed | 25, 27, 24 | 28, 26, 28 |
| 17 cm / 27 cm ascent with 3 cm nosing | 16, 22, 17 | 25, 29, 22 |

More pooled completions do not establish a uniformly better checkpoint:
hard570 reduces stalls on several cases while losing easy-ascent stability.
Neither checkpoint passes the full final case/seed gate. Selecting the largest
update number or overall completion fraction would hide this tradeoff.

All 33 hard570 escapes occur in 8/12 cm ascent and have positive final root y.
Thirty have root y beyond +0.65 m; three have root still inside the margin but
a flight foot beyond +0.65 m. These three are seed 11 environments 23/90 and
seed 29 environment 17. The latter is an intentional anti-bypass foot condition,
not a contradictory root condition. One environment has both fall and escape;
failure counters are not mutually exclusive.

Most root-boundary escape endpoints have y approximately 0.651–0.660 m.
Several left-side foot centers sit near y=0.622 m, close to the 0.6 m mesh side
plus foot radius, and the final landing clearance is often only 0.05–0.16 m.
The evidence is consistent with positive lateral drift, side contact and low
body posture preceding failure. It does not identify the causal sequence or
prove a specific reward defect. For example, an endpoint's clearance measured
relative to the goal platform is not local terrain clearance before reaching
that platform.

The easy-ascent failed rows (including stalls) have mean initial y +0.04479 m,
versus -0.01517 m for completed rows. Both sets span both signs, so initial y is
an association rather than a complete predictor. The recorded first row of
each easy case also drifts positively despite finishing: environment 0 finishes
near y=0.433–0.474 m and environment 64 near y=0.291–0.410 m. Corresponding
mean absolute lateral error rises from 0.123/0.091 m in hard520 to 0.219/0.210 m
in hard570. This supports an actual policy regression, not only a threshold
edge case or reset-position mismatch.

Possible causes such as the base-height objective, speed/objective tradeoffs,
asymmetric learned support, HIM/actor update drift, or curriculum sampling are
still hypotheses. Frozen inference and zero-action controls rule out an
optimizer update during evaluation; they do not identify the training cause.
Use the pending faithful/contact comparison and per-leg diagnostics before
assigning that cause or introducing another reward change.

## What each existing gate means

The evaluator measures only each environment's first episode, using a snapshot
after physics and termination computation and before automatic reset. Finished
rows become inactive; later reset poses cannot create completions. The terminal
sample remains part of that first episode's measurements.

Full-flight success requires the root at goal x; every foot beyond the last
riser by 0.10 m and beyond the final platform start by 0.03 m; every foot within
0.12 m of final platform height; root inside ±0.60 m and feet inside ±0.65 m;
base clearance 0.18–0.60 m; gravity z below -0.8; at least two history-contact
feet; no fall, escape or genuine termination; and a continuous 0.5 s dwell.
The tighter success corridor is intentionally distinct from the escape margin.
Standing just outside the success corridor can therefore stall without first
being labeled an escape.

Lateral escape uses root outside width/2 + 0.05 anywhere, or any foot outside
that bound while the foot's x lies within the flight. It includes feet in air;
it is a corridor-placement criterion, not a contact-only support criterion.
The stock stair termination checks root corridor exit, so the evaluator's foot
criterion is deliberately stricter. Keep both rather than relaxing the gate
to accommodate hard570's drift.

`falls` is an aggregate flag: history base contact >1 N, gravity z >-0.5,
non-escape genuine termination, or abnormal root z. The installed nominal task
has genuine base-contact and added corridor termination terms. Without saved
individual term results/gravity at each final row, the one fall without recorded
base contact cannot be precisely attributed. A body touching a stair can be a
fall flag even when the robot never overturns. Reports should say “fall/base
contact or genuine termination”, not claim every row physically toppled.

The separate final gate requires at least 95% completion, at least 32 environments,
each fall/stall/escape fraction at most 5%, zero base-contact environments,
and no trial-level numerical failure for **every case and seed**. At n=32,
31 completions pass the completion threshold while 30 do not; two failure flags
of one type exceed 5%. Pooled 95% completion cannot replace these gates.
Zero-action control should remain unable to complete. Physical/numerical anomaly
counts should also be reported even where completion has already failed.

Smoothness is explicitly unverified. `motion_improvement_needed` uses only the
longest flight pause >1 s as a flag; `False` is not a smoothness certification.
Action differences, jerk, tracking, force and slip proxies need matched-speed
comparison and video. Metrics exclude the first second and stop at each row's
completion/failure, so policies with different failure/finish times have
different measurement exposure. Compare case/seed metrics, not only the pooled
metric dominated by longer episodes; inspect successful and failed behavior
without quietly dropping the failures.

The current force is the final 5 ms physics-step normal-force sample at each
20 ms policy boundary. History length three retains current/T−5 ms/T−10 ms;
the first substep of that policy interval can have been overwritten. Current
and history leg fractions measure sample presence, not scrape duration, force
severity, friction force or contact-point tangential velocity. The new per-leg
force columns permit attribution only for recorded environments/times.

## Concrete telemetry/API risks

1. Batched trace sampling chooses at least one row per geometry. With 24 cases,
   `record_envs=4` actually records 24 environments, one per case. No currently
   recorded easy-case row failed, although other rows did. Do not infer the
   failure mechanism from these successful traces. A later targeted diagnostic
   can expose selected environment IDs or a short per-row terminal snapshot;
   changing trace allocation should preserve all-case coverage and bounded files.
   `record_stride=5` gives 100 ms traces, too sparse for 5 ms impacts.
2. Base-contact presence and per-leg arrays are currently absent from unrecorded
   per-environment endpoints. Root/feet positions are enough to verify root/foot
   escape, but not enough to distinguish base touch from gravity fall. Saving
   final gravity, current/history base force and manager termination causes in
   a future diagnostics-only change would resolve this.
3. With `--domain_profile none`, the inherited material event selects **all
   robot bodies**. `--friction STATIC DYNAMIC` changes its ranges, so it changes
   base/thigh/calf/hip friction as well as feet. `basic`/`robust` replace that
   event with a foot-only selector. Label the former an all-robot material test;
   do not call it isolated foot friction.
4. `--eval_dynamics` preserves caller event modes. Mass/COM/material startup
   samples remain fixed in one scene, but robust PD gains are reset events and
   resample from original defaults at every reset, including later resets of
   finished rows. The previous `seed_scope` wording incorrectly implied all
   dynamics were fixed. Metadata now explicitly states reset-mode events can
   resample; numerical/control logic is unchanged.
5. Initial/final parameter readbacks are useful but robust final PD values may
   belong to later episodes, not the measured first episodes. Capture physical
   parameters after each seeded first reset if a future audit needs exact
   episode-to-gain pairing. Existing readback returns summary/first three rows,
   so exact per-case startup material/mass correlation is also limited.
6. Domain manifests are created before `--friction` overrides. The manifest can
   still advertise basic ranges 0.6–1.1/0.5–1.0 while live materials are fixed
   by the override. Use `friction_override` plus actual readback's configured
   ranges, bucket membership and measured coefficients as the authoritative
   effective values; do not report the stale preset ranges alone.

## Final execution protocol

Freeze checkpoint, inference controller, source commit and declared gates after
the tuning/ablation results. Use the existing final JSON without further
training or selecting a checkpoint based on those final outcomes. Final test
seeds should be fresh, for example 101/211/307, distinct from tuning 11/29/47.
Report exact seeds and any prior use rather than implying new independence.

The 16-case `reproduction/stair-heldout-final.json` includes known paper/control
geometries, unseen tread depths 0.29/0.33 m, interpolated nosings 0.015/0.025 m,
12-step flights, and 23 cm / 20 cm stretch cases. Hard training already covers
height range 0.08–0.23 m, depths including 0.20/0.25/0.27/0.30, and nosings
0/0.01/0.02/0.03. Thus 23 cm and paper geometries are not automatically outside
the training support; call the final set held-out exact cases, distinguishing
interpolation, unseen depth, longer flights and controls. Exact mesh/seed holdout
is not a claim of arbitrary staircase generalization.

Use 512 environments for 16 cases to retain exactly 32/case. Run both 0.3 and
0.5 m/s with identical geometry/seeds and 40 s episode limits. The 12-step
0.25 m case goal is 4.65 m; ideal 0.3 m/s time is 15.5 s plus dwell, so 40 s
provides margin without silently redefining stalls (which remain 4 s / 0.05 m).
When final runs include candidates, predeclare their roles and preserve every
result; do not silently choose the best final test outcome.

For the chosen frozen checkpoint, the parent can execute:

```bash
selected_checkpoint='<frozen checkpoint path inside this repository>'
selected_profile='<faithful or contact, frozen before final tests>'
bash isaaclab/run.sh evaluate --terrain stairs \
  --stair_batch reproduction/stair-heldout-final.json --num_envs 512 \
  --checkpoint "$selected_checkpoint" --reward_profile "$selected_profile" \
  --speed 0.3 --eval_seconds 40 --eval_randomized \
  --eval_seed 101 --eval_seed 211 --eval_seed 307 \
  --domain_profile none --run_name final-heldout-speed03 --viz none
```

Repeat with speed 0.5 and a distinct run name. The shell variables must be set
to the selected local checkpoint path and its documented reward profile; this
is a protocol template, not a claim that these runs have executed. Reward
profile affects reported reward/terms during inference and must match its
manifest; use the same profile for matched performance comparison unless a
different inference-only scope is explicitly declared.
`--viz none` supplies the headless evaluation mode; this CLI has no
`--headless` argument. A video evaluation uses `--video` and omits `--viz none`
so the headless Kit video visualizer can be configured.

Run material sensitivity with a **new foot-only nominal control** first:
`--domain_profile basic --friction 0.8 0.6`, without `--eval_dynamics`.
Evaluation removes mass/COM/gain events in this mode, so mass/COM/gains remain
nominal; the material selector still differs from existing `none` runs on
non-foot bodies, so this new baseline is required. Within this same basic
configuration, repeat low `--friction 0.45 0.35` and high
`--friction 1.0 0.8`, keeping checkpoint, speed, seeds and cases fixed.
The coefficients are proposed sensitivity settings, not measured real stairs.
If time requires a smaller material geometry set, name that set in advance
and constrain the robustness claim to it; do not extrapolate to all 16 cases.

Each material requires a new environment because startup buckets are fixed.
Inside one material environment, compare a predeclared candidate in the same
scene using `--candidate_checkpoint` if needed. Three reset seeds test reset
variability on that material; they do not create three new startup material
draws. Terrain coefficients remain 1/1; the configured multiply combine mode
explains the intended interaction, while actual foot-material readback verifies
the coefficients applied to collision shapes.

Reserve combined dynamics testing for a separate run:
`--domain_profile robust --eval_dynamics --eval_randomized`. Prefer at least
three construction seeds, each in a newly created scene, and fixed reset seeds.
This combines foot materials, startup base mass/COM and reset PD gains, so it is
a joint-domain robustness test, not a way to attribute a material effect.
The existing configured mass range is 0.8–1.25× original with consistent inertia;
robust COM bounds are ±0.03/0.02/0.01 m; kp/kd scale by 0.9–1.1. Verify actual
readback rather than assuming configured ranges were applied.

Priority before 07:29: finish the single-factor contact/faithful comparison and
easy-stair regression; freeze the candidate; run both final geometry speeds;
run foot-only nominal and low/high sensitivity; then combined dynamics if time
remains. Keep any unfinished block explicitly unvalidated. Do not weaken the
case/seed final gate or call the controller smooth based only on absence of a
pause flag. Save short ascent/descent videos on difficult, long and previously
drifting easy cases so motion/contact interpretation has visual evidence.
