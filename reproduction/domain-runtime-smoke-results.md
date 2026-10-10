# Actual domain randomization runtime smoke results

Both **basic** and **robust** passed independent readback checks against actual
PhysX parameters. Each run used 64 Go2 environments, 24 steps per rollout and
2 optimizer updates (3,072 environment steps). CUDA updates and export finished
with finite parameters and export maximum absolute error 1.1921e-7.

**These weights are discarded runtime artifacts.** They were not selected,
deployed, or evaluated as trained locomotion policies. This check establishes
physical randomization and runtime compatibility; it is not a traversal or
robustness result. The reviewer only read saved evidence and did not launch GPU
work, change source, install packages, or change drivers.

| Profile | Actual base mass kg | Original-mass ratio | Actual kp | Actual kd | Independent checks |
| --- | --- | --- | --- | --- | --- |
| basic | 5.601104–8.599453 | 0.809291–1.242516 | 25.000000–25.000000 | 0.500000–0.500000 | 27 / 27 |
| robust | 5.601104–8.599453 | 0.809291–1.242516 | 22.503906–27.493235 | 0.450074–0.549952 | 27 / 27 |

The original base mass is 6.92100048 kg. Actual ratios span 0.809291–1.242516,
inside the preserved log-uniform 0.8–1.25 configuration, with real variation
across environments. Inertia matches original inertia multiplied by mass ratio:
maximum full-buffer error is 0 at initial capture and 4.47035e-8 kg m² at final
capture for both runs. Recomputing the first three saved tensors independently
also passes the 1e-6 kg m² tolerance.

| COM offset axis | Basic observed min/max m | Robust observed min/max m |
| --- | --- | --- |
| x | -0.00977059 / 0.00996456 | -0.02931177 / 0.02989369 |
| y | -0.00965832 / 0.00973818 | -0.01931664 / 0.01947637 |
| z | -0.00472229 / 0.00485546 | -0.00944457 / 0.00971092 |

COM varies within basic limits ±[0.01, 0.01, 0.005] m and robust limits
±[0.03, 0.02, 0.01] m. Original COM quaternions are preserved. Startup COM and
foot material reports remain exactly unchanged during both runs. Mass/inertia
backend readback has small float32 differences; the largest reported mass
sample change is 4.76837e-7 kg, inside the 1e-6 kg tolerance.

Basic actuator tensors remain exactly kp=25 and kd=0.5. Robust tensors show
independent gain variation and stay inside kp 22.5–27.5 and kd 0.45–0.55.
Original gain caches remain exactly fixed at 25/0.5. Between initial and final
capture, robust aggregate kp mean changes by -0.00372024 and kd mean by
-0.000287498, proving later resampling within these two updates. The first
three saved environment gain samples remain unchanged; the aggregate evidence
does not establish which or how many environments reset during the smoke.

All four feet map from public/backend bodies 15–18 to collision shapes 23–26.
Actual static friction spans 0.614946–1.099526; dynamic spans
0.505612–0.993657. Restitution is zero, dynamic friction is never larger than
static, and all observed shape triples belong to the cached bucket pool.
64 unique materials were observed. Terrain friction remains 1.0 with multiply
combine mode. Actual motor strength and action delay are not randomized.

All live current fields and original mass/inertia/COM event caches were
available and finite. Robust has original PD event caches; basic uses the
explicitly labeled configured gain reference. The only expected unavailable
field is the original
foot-material snapshot: the installed material event does not save it. The
report states this reason explicitly; it uses cached buckets as assignment
provenance, not as a fictional original material baseline.

Evidence comes from source commit
`783412201fe10fb27b951c522ba6b4f3cc3ef993`:

- `isaaclab/logs/2026-10-11_02-41-57_domain-basic-runtime-smoke/`
- `isaaclab/logs/2026-10-11_02-42-26_domain-robust-runtime-smoke/`

Each directory contains `config.json`, `result.json`, and
`domain-parameters-{initial,final}.json`. The companion
`domain-runtime-smoke-results.json` records individual assertions, numeric
ranges, tolerances, small samples and SHA-256 hashes of the inspected files.
The initial/final ranges cover the full readback buffers; independent manual
arithmetic uses the three saved sample rows. This short check cannot prove
long-horizon physical robustness or algorithm convergence.
