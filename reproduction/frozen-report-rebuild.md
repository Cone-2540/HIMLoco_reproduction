# Rebuild frozen CPU reports

These programs use Python’s standard library. They read saved first episodes and physical readbacks; they do not import Isaac Sim, Torch or CUDA, train policies, change drivers, or alter the frozen protocol.

The repository defaults to the project containing each script, so commands work from any current directory. Use `--repo-root /path/to/HIMLoco` to override it. The stair and material summaries also accept `--run-log-root /path/to/overnight-logs` for master logs and the saved execution-plan copy. The default master-log directory is `~/robotics/logs/himloco-overnight-20261011`.

```bash
python3 reproduction/summarize-frozen-material-speed05.py
python3 reproduction/validate-frozen-stair-validation.py --supplement
python3 reproduction/summarize-frozen-flat-regression.py
python3 reproduction/summarize-frozen-stair-validation.py
python3 reproduction/validate-frozen-stair-validation.py
python3 reproduction/summarize-frozen-stair-diagnostics.py --kind speed
python3 reproduction/validate-frozen-stair-validation.py --diagnostic speed
python3 reproduction/summarize-frozen-stair-diagnostics.py --kind calf
python3 reproduction/validate-frozen-stair-validation.py --diagnostic calf
python3 reproduction/summarize-frozen-stair-diagnostics.py --kind dynamics05
python3 reproduction/validate-frozen-stair-validation.py --diagnostic dynamics05
python3 reproduction/summarize-frozen-stair-diagnostics.py --kind geometry
python3 reproduction/validate-frozen-stair-validation.py --diagnostic geometry
```

Run the optional material supplement first so the original final report can link its current summary. The original report still determines completion from its original 11 scenes only. The flat summary has its own original velocity/survival gates. The heading-dependence report is generated with the stair summary when both heading scenes exist.

Raw simulation logs and checkpoints are local ignored files. Missing result logs produce pending entries, never a synthetic pass. A missing flat result prints `pending_flat_result`; no completed flat artifact is invented. Freeze files retain their expected hashes; a mismatching available checkpoint, runtime source, acceptance or geometry file stops aggregation. Missing local hashed files remain unavailable, and the original final report cannot be marked complete until all required hashes match.

The material summarizer shares the stair summarizer’s definitions and aggregation loop by selecting its syntax tree before any report-writing statements. Its only code dependency is the sibling `summarize-frozen-stair-validation.py`. The stair summarizer calls the existing CPU `analyze-stair-motion.py` in a temporary directory and embeds the resulting comparisons, so no previous `/tmp` analysis files are needed.

Generated CSV columns and original gates stay unchanged. Compressed JSON is lossless and contains source identities, SHA-256 checks, failures, counts, denominators, physical readbacks, and comparison limits. The independent validator compares JSON/CSV rows with raw per-environment first-episode outcomes and recomputes all case/resetseed gates. Full continuous-video interpretation remains separate from numeric traversal checks.

The speed-probe and calf-envelope summaries are separate diagnostics. Their original scientific scope and frozen selection remain unchanged; new speed subsets do not become independent final acceptance. The speed geometry file `stair-frozen-speed-probe.json` is preserved, while its analysis is saved as `.json.gz`. The calf report pairs each legacy-envelope scene with the original same-speed nominal scene and labels the missing backend torque-speed readback explicitly.

The `dynamics05` diagnostic kind rebuilds the separately recorded higher-speed combined-dynamics supplement. It verifies initial/final mass, COM, PD scales and inertia scaling while retaining all failed episodes; it does not change the original 11-scene status. Speed collection attempts include the failed first 0.6 m/s OOM and the complete unchanged-protocol retry; collection failure and policy acceptance are distinct.

The `geometry` kind preserves the18-case height/depth matrix `.json` and saves its analysis as `.json.gz`, Markdown and CSV. Its fresh reset seeds follow an adaptive geometry choice after final failures; individual boundary-map passes are diagnostic and do not certify a safe operating envelope.
