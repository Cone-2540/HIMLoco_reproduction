# Frozen policy and export independent audit

CPU-only audit of the plan frozen at 2026-10-11 05:47:03 +08:00, before the
independent final runs. Primary remains control660 / `contact`; the predeclared
secondary is slide680 / `contact_slide` for the two nominal speeds only.

Both checkpoint SHA-256 values match the frozen plan. The final geometry,
heading geometry and acceptance JSON hashes also match, as do all 28 listed
runtime Python source hashes. Every file and byte count in both artifact
manifests was checked, including each exported `policy.pt`, training records
and the primary's operator-stop record. Detailed hashes are saved in
`frozen-policy-independent-audit.json`.

Each training checkpoint contains 22 actor/HIM/std tensors. Each TorchScript
export correctly contains the 14 inference tensors: eight actor and six HIM
encoder tensors. All 14 are bit-identical to their checkpoint counterparts.
The eight omitted training-only tensors are exploration std, six HIM target
network tensors and the prototype embedding; they are not used by deterministic
inference. Therefore the export should not be described as containing all 22
training tensors.

Loading the complete checkpoint into the original CPU HIMActorCritic and
comparing against its saved TorchScript export on 52 observation histories
of width 270 gave exactly zero maximum absolute action difference for both
policies. Samples covered zero and seeded random histories at multiple scales.
Inference left every model weight unchanged. CUDA was masked and unavailable.

This establishes file and export synchronization, not locomotion quality or
deployment readiness. Continuous video and independent per-case/seed results
remain separate evidence; the frozen primary is not changed by those results.
