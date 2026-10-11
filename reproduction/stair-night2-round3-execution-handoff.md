Round3 root execution handoff, prepared 2026-10-12 about05:40 CST. All GPU commands below are for root after the current100update training has completed and its archive audit has succeeded; this document itself starts nothing. Do not launch seed1229 tonight.

Measured cost evidence is `stair-night2-round3-cost-and-baseline-reuse.json`: completed100update training wrappers1757.8–1825.9s; old shared three-policy development895.7s for two scenes; old shared two-policy final1285.9s for four scenes. New development has two policies, so budget roughly10–12min (projection, not measurement). Reserve22–25min for the four new final scenes. A training finish near06:04 gives development/freeze/final near06:40, leaving about40min for selected video/flat/closeout until07:20. Retain unsuccessful and partial matrices; collection exit0 never means scientific PASS.

Development uses the original18cases/576env, reset11/29/47, speeds0.3/0.5, default heading. Primary construction and comparator is faithful1213; candidate actual training profile is contact_light, recorded by mandatory sidecar.

```bash
python3 reproduction/run-stair-night2-round3-comparison.py \
  --stage development \
  --candidate artifacts/go2-stairs-night2-round3-contact-light-seed1213-760/model_760.pt \
  --source-proof reproduction/stair-night2-round3-source-compatibility-actual-cpu.json \
  --output-dir /home/cone/robotics/logs/night2-round3-development-20261012 \
  --execute
```

The output directory must be new. For a dry run omit both `--execute` and `--output-dir`, to avoid reserving the execute destination prematurely. The unchanged per-job wrapper enforces07:20 and exact idle checks prevent concurrent scenes.

Root reviews both summaries and selects using development only. Light selection evidence path:

```text
/home/cone/robotics/logs/night2-round3-development-20261012/contact-light1213-development-summary.json
```

If retaining faithful, use `baseline-faithful1213-development-summary.json` and the existing faithful checkpoint instead. The corresponding `LABEL-training-identity.json` must exist and match the archived identity. The helper requires an explicit root-authored reason derived from development; it performs no automatic selection. API:

```python
spec = importlib.util.spec_from_file_location("round3", "reproduction/run-stair-night2-round3-comparison.py")
round3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(round3)
value = round3.selection_payload(
    checkpoint, development_summary, actual_root_development_reason,
    "reproduction/stair-night2-round3-source-compatibility-actual-cpu.json")
round3.backend.save_json_exclusive(
    Path("reproduction/stair-night2-round3-selected-final-freeze.json"), value)
```

Freeze fields generated and strictly validated: schema_version1, round3, statusfrozen_before_final, created_local; development_only/no_final_evidence_used; explicit selection_reason; selected and fixed faithful baseline complete19member archive identities, saved100/7680/100/76.8M/seed1213/origin660→760/reward weights/Adam/schema/config/initial-readback identity; source full clean Git commit and every runtime/workflow hash; four preregistered protocol hashes; actual source proof explicit file/hash; development108rows/geometry/plan/model hash plus actual-training sidecar file/hash; automatic_candidate_selectionfalse and retuning_from_final_allowedfalse. Existing old selection freeze remains untouched.

Final uses reserved16cases/512env, freshreset1301/1303/1307, speeds0.3/0.5, both heading and zero yaw: four serial jobs, faithful comparator and frozen selected policy. Selecting faithful produces one policy per scene instead of a duplicate comparison.

```bash
python3 reproduction/run-stair-night2-round3-comparison.py \
  --stage final \
  --selection-file reproduction/stair-night2-round3-selected-final-freeze.json \
  --source-proof reproduction/stair-night2-round3-source-compatibility-actual-cpu.json \
  --output-dir /home/cone/robotics/logs/night2-round3-final-20261012 \
  --execute
```

Controllers receive separate verdicts. New final cannot be used to choose or retune a candidate; old final remains failed/known diagnostic. Continuous video and contact quality review are separate from numerical collection.

Flat is an independent new freshseed1301 check, same strict seven-command20s/64env gates. Root sets SELECTED_CHECKPOINT from the new freeze. No extra training or warmstart actor change:235→48critic reset copies22actor/HIM/std tensors exactly.

```bash
python3 reproduction/run-stair-night2-job.py \
  --name night2-round3-flat7-selected-seed1301 --max-seconds 1200 -- \
  evaluate --terrain flat --checkpoint SELECTED_CHECKPOINT --warm_start reset \
  --num_envs 64 --eval_seconds 20 --seed 1301 \
  --command 0.3 0 0 --command 0.5 0 0 --command -0.5 0 0 \
  --command 0 0.3 0 --command 0 -0.3 0 --command 0 0 0.5 --command 0 0 -0.5
```

After the explicit flat wrapper exits0 and config/result/export exist, give the exact run and wrapper paths to the CPU reviewer; never choose a latest glob.

```bash
docker exec -e CUDA_VISIBLE_DEVICES= -e OMP_NUM_THREADS=2 \
  -w /workspace/himloco isaaclab-local-lab-1 /isaac-sim/python.sh \
  reproduction/audit-stair-night2-round3-flat-transfer.py \
  --checkpoint SELECTED_CHECKPOINT \
  --selection-file reproduction/stair-night2-round3-selected-final-freeze.json \
  --flat-run EXACT_FLAT_RUN \
  --output reproduction/stair-night2-round3-flat-transfer-actual-cpu.json

python3 reproduction/summarize-stair-night2-round3-flat.py \
  --run EXACT_FLAT_RUN --wrapper-dir EXACT_FLAT_WRAPPER \
  --selection-file reproduction/stair-night2-round3-selected-final-freeze.json \
  --transfer-audit reproduction/stair-night2-round3-flat-transfer-actual-cpu.json \
  --output-prefix reproduction/stair-night2-round3-flat-regression
```

The independent new auditor requires0absoluteactiondiff to fullstairactor/archivedstairpolicy/transferred/actualflat export on140fixed270input histories. It checks all19archive members,22exactcopies+8freshcritic and nolearning/noCUDA. Flat summary invokes the full round3 freeze/source/proof guard and recomputes unchanged gates:XYMAE<0.2m/s,yawMAE<0.3rad/s,survival≥95%. Oldseed907/oldfreeze are rejected. Retain all seven policy and seven zero-action results including failures. Existing faithful oldflat2/7failure remains separate historical evidence.
