# Saved staircase motion analysis review

The new [analyze-stair-motion.py](analyze-stair-motion.py) analyzes saved first-episode motion without Isaac Sim or a GPU. It reproduces the standard370 video review's principal action/contact/foot-correction events, keeps the hard520 comparison at equal geometry, seed, speed and case, and reads the newer named thigh/calf telemetry. It reports evidence and its sampling limits; it does not certify smoothness or change any acceptance threshold.

The original acceptance file requires at least 32 environments per case/seed, three distinct reset seeds, 95% completion per case/seed, no more than 5% falls/stalls/escapes and zero base-contact environments. The tool's `declared_per_case_traversal_gate_passed` applies those existing per-case conditions. It is a comparison filter, not a claim that a whole matrix satisfies the three-seed requirement or that motion passes the continuous-video requirement. With 32 environments, 31/32 passes completion and 30/32 fails.

## Tool use and outputs

```bash
python3 -B reproduction/analyze-stair-motion.py \
  isaaclab/logs/2026-10-11_03-10-39_standard370-16cm-asc-speed03-video/result.json \
  isaaclab/logs/2026-10-11_03-11-42_standard370-16cm-desc-speed03-video/result.json \
  --output reproduction/stair-motion-standard370-video --plot

python3 -B reproduction/analyze-stair-motion.py \
  isaaclab/logs/2026-10-11_03-43-07_hard520-interim-tuning/candidates/0_model_370/result.json \
  isaaclab/logs/2026-10-11_03-43-07_hard520-interim-tuning/result.json \
  --output reproduction/stair-motion-hard520-vs370

python3 -B reproduction/analyze-stair-motion.py \
  isaaclab/logs/2026-10-11_03-53-37_hard570-regression-and-tuning/result.json \
  isaaclab/logs/2026-10-11_04-07-03_contact620-interim-regression/result.json \
  --output reproduction/stair-motion-contact620-vs570

python3 -B reproduction/analyze-stair-motion.py --self-test
```

Each invocation writes JSON containing trace statistics, event times/positions, telemetry availability, original case metrics and matched comparisons; Markdown containing a compact overview; and CSV containing named current/history body peaks and foot-retraction events. `--plot` adds a PNG/PDF overview of sampled action and aggregate force peaks. Source numbers in that plot follow the JSON source order. `--seed`, `--case` and `--top-events` select a smaller review scope. `--controller zero_action` reads a saved negative-control report using the same analysis. The core tool uses only the standard library; plotting additionally needs matplotlib.

Comparison deltas follow input order: right minus left. A match requires the same recorded geometry, case index, reset seed and nonmissing commanded speed. The tool checks saved controller/protocol fields, initial root-position arrays, startup physical readbacks and foot-material readbacks. It labels motion comparisons eligible only when that evidence matches and both cases pass the declared traversal gate. Full per-env initial orientation/state, per-trial gain reads and terrain-material reads are not established merely by those checks. Candidates in the same evaluation may share one startup sidecar; its equality is construction evidence, not an independent dynamics experiment.

## Standard370 video traces

The two files each record env0, seed29, six 16 cm steps with 27 cm treads, no nosing and a 0.3 m/s command. Trace cadence is **0.1 s**, independent of the **50 fps** camera rate; policy dt is 0.02 s. Both complete, with no fall, stall, lateral escape or reported flight pause. They contain only one environment each and supplement the broader validation counts. Ascent/descent geometries differ, so the analyzer correctly creates no matched checkpoint comparison between these recordings.

Foot names are recovered from the respective `domain-parameters-initial.json` readbacks in the order `FL_foot, FR_foot, RL_foot, RR_foot`, and the tool saves that provenance. The older result files have no named per-body leg-force arrays. All eight thigh/calf force entries remain explicitly unavailable; the aggregate force cannot identify a particular leg or collider.

| Recorded event | Sampled value | Simulation time | Root relative XYZ at event, m |
|---|---:|---:|---|
| Ascent action second-difference peak after warmup | 0.386637 | 3.12 s | [0.755801, 0.044854, 0.282653] |
| Ascent aggregate leg-history force peak after warmup | 73.208771 N | 4.22 s | [1.059698, 0.049840, 0.433888] |
| Ascent largest root-flight foot retraction, RR_foot | 0.008658 m | 9.22–9.32 s | Event endpoints retained in JSON/CSV |
| Descent largest root-flight foot retraction, FL_foot | 0.081849 m | 4.32–4.42 s | [1.102208, 0.065086, 0.166562] at end |
| Descent aggregate leg-history force peak after warmup | 143.389008 N | 4.42 s | [1.102208, 0.065086, 0.166562] |
| Descent action second-difference peak after warmup | 0.426041 | 7.02 s | [1.719709, 0.072199, −0.185009] |

The FL_foot course-x position falls from 1.414742 to 1.332893 m while z falls from −0.176105 to −0.269248 m at the descent correction. Its history-contact flag at the end is false; a current-contact flag is unavailable in that old trace. The coincident aggregate leg force and foot-center correction support a local motion event, without identifying which body contacted the stair or its collision mechanism. Normal gait corrections also satisfy the tool's foot-retraction definition.

The values above reproduce [stair-standard370-video-review.md](stair-standard370-video-review.md). Root-flight sampled world vx stays positive: 0.170–0.383 m/s ascent and 0.134–0.378 m/s descent. Recorded policy-cadence pause maxima are zero. The existing review inspected selected stills, including denser transition stills and final frames; it did not establish complete continuous playback. Sampled event peaks and apparent forward traversal therefore do not exclude short events between records.

## Hard520 versus the same-batch model370 candidate

The older hard520 tuning matrix contains 12 cases × seeds11/29/47 × 32 environments, with a 0.3 m/s command. The tool extracts **72 representative environment traces**, **72 source case/seed rows** and **36 matched comparisons**. Initial root arrays, startup physical/foot-material evidence and saved contact/protocol metadata match in every pair. **20 pairs** have both cases passing the existing per-case gate; the other **16 remain descriptive**. No failed or stalled comparator qualifies as evidence of smoother competent traversal because its action or jerk is low.

Source totals remain unchanged: model520 completes **1092/1152**, with all 60 failures being stalls on nosing ascent. The matched model370 completes **788/1152**, with 354 stalls and 10 falls. Model520 improves capability, but fails the final per-case completion criterion on some nosing ascents. The source matrix remains interim tuning rather than independent held-out acceptance.

Every model520 descent case completes 96/96 across the three seeds, yet its current-boundary any-leg contact fraction is roughly **44.5–48.8%**, versus **23.8–27.4%** in model370. These current-force measurements establish boundary contacts and a contact tradeoff; history gating alone cannot explain them. They do not measure scraping duration, exact contact point or damage. The tool preserves original case metrics and contact sample denominators separately from representative trace fractions. See [stair-hard520-analysis.md](stair-hard520-analysis.md) for the full capability and failure-endpoint interpretation.

## New named-force telemetry: contact620 versus hard570

The newer files provide report `leg_body_names` and trace `leg_current_normal_force_norm_n` / `leg_history_peak_normal_force_norm_n`. The analyzer joins columns by name, including the eight expected Go2 thigh/calf bodies, and records each body's post-warmup current/history peak with seed, case, environment, time and root position. It retains current/history contact sample fractions separately at the report's existing strict 1 N threshold.

This additional validation extracts **144 traces**, **144 source case/seed rows** and **72 matching comparisons**. Saved initial root arrays, physical/foot-material evidence and protocol fields match in all 72. Hard570 passes the per-case gate in 50 pairs; contact620 passes in all 72, so **50 comparisons are eligible** and 22 remain descriptive. The files cover 24 cases × three seeds × 32 environments; source completion is 2189/2304 for hard570 and 2302/2304 for contact620.

The analyzer reproduces **8,941** active post-warmup recorded rows for hard570 and **9,048** for contact620. An independent read-only check also reproduces hard520's newer candidate count of **8,820** rows. All checked rows have finite eight-element arrays; each body's history peak is at least its current value; and each row's maximum over the eight bodies equals its corresponding current/history aggregate force. There are zero discrepancies. These checks establish internal saved-telemetry consistency, not independent calibration or a particular collider's contact ownership.

| contact620 named current-force event | Sampled peak | Seed / case / env | Time | Root relative XYZ, m |
|---|---:|---|---:|---|
| FR_calf, 18 cm descent | 489.579803 N | 47 / 13 / 416 | 8.32 s | [1.992588, 0.040509, −0.415016] |
| FR_thigh, 20 cm descent | 291.936279 N | 47 / 15 / 480 | 3.32 s | [0.888277, −0.013353, 0.244616] |

These are largest sampled current calf/thigh events in the recorded environments, not all-environment maximum body forces. Each case/seed records one representative environment at 0.1 s cadence. The broader completion/contact results and continuation tradeoffs are in [stair-refinement-comparison.md](stair-refinement-comparison.md); the two case8 stalls and 3.62 s source maximum pause still require motion review despite the traversal gate passing.

## Sampling and interpretation safeguards

Active masks are kept per case/environment and never reactivate a completed first episode. The tool rejects duplicate IDs, inconsistent column dimensions, duplicate/nonfinite/nonincreasing active timestamps and body manifests that disagree with recorded columns. Trace endpoints can precede the actual terminal state; original pre-reset source endpoints/outcomes are preserved separately.

The evaluator excludes the first second from motion statistics; at 0.02 s policy dt, the first eligible step is timestamp1.02 s. Recorded action differences are one-policy-step differences sampled at trace timestamps. Sparse action snapshots are never differentiated. Dense action second differences are derived only when every observed policy boundary is present. Physical root jerk remains the original full-policy-cadence source metric. Tracking includes sampled world vx and an explicitly labeled yaw-only body-XY error proxy; the source's full-body-frame tracking metric remains authoritative on pitched stairs.

Foot retractions use decreases of course/world-x foot-center position between adjacent recorded samples with the root on the stair flight. Missing root-flight intervals yield unavailable retraction evidence instead of a misleading zero. Contact transitions and pause runs are observed trace events; sparse hits do not establish continuous duration. Source policy-cadence longest pause stays available alongside sampled endpoint spans.

For the recorded v2 contact reports, the history contains three samples at physics5 ms: ages0/5/10 ms at a policy20 ms boundary. Oldest age is 10 ms; the nominal sample-count window is 15 ms. A first-substep-only contact at age15 ms may already be overwritten. Current/history forces are world-frame **net normal-force vector norms**, including horizontal riser normals and excluding tangential friction. Foot-link horizontal speed is a slip proxy, not contact-point tangential slip; current/history contact-foot denominators differ. A reward that counts contacted bodies differs from an evaluator fraction that asks whether any selected leg body contacts.

Seven embedded tests pass, covering dense body attribution/action derivation, sparse-action/pause handling, missing force manifests/current-history separation, first-episode masking, invalid timestamps/dimensions, absent flight intervals and mismatched/stalled comparisons. All three real-data invocations succeed; optional PNG/PDF rendering was run and inspected. Work was CPU-only. No training/evaluation source files, thresholds, GPU state, commits or pushes were changed by this task.

Generated bundles: `stair-motion-standard370-video.{json,md,csv,png,pdf}`, `stair-motion-hard520-vs370.{json,md,csv}`, and `stair-motion-contact620-vs570.{json,md,csv}`.
