# Stretch descent association review

Saved first episodes show higher completion at **0.5 m/s** for nominal materials and at **lower foot-material coefficients** for the 0.3 m/s material probe. The same data show persistent calf contacts, higher contact-gated foot speeds in the higher-completion conditions, and failures concentrated near the first 23 cm drop. These are condition-specific associations, not evidence for an optimum speed/friction or smoother motion.

| Condition | Completed /96 | Falls | Stalls | Current foot XY speed (m/s) | Current slip proxy fraction | Pitch RMS (rad) |
|---|---:|---:|---:|---:|---:|---:|
| none nominal 0.3 | 54 | 34 | 8 | 0.142 | 0.234 | 0.379 |
| none nominal 0.5 | 94 | 2 | 0 | 0.216 | 0.281 | 0.421 |
| basic nominal 0.3 | 58 | 31 | 7 | 0.137 | 0.232 | 0.393 |
| basic low 0.3 | 92 | 4 | 0 | 0.206 | 0.330 | 0.395 |

Counts sum three reset seeds 101/211/307 × 32 environments, case 15 only. Numeric proxy columns are arithmetic means of the three per-seed case reports; they are not a newly pooled estimate. They use valid active first-episode samples after 1 s, and episode duration differs between successful and failed runs. “Slip proxy” means current normal-force-gated foot world-XY link speed > 0.10 m/s, not measured contact-point tangential slip.

For nominal 0.3 m/s with the `none` configuration, 33/34 falls end with root x in [1.0, 1.2) m; the six-step geometry begins at x 1.0 and its first tread ends at x 1.2. All 8 stalls end at root x 1.424–2.128 m. For basic nominal 0.3 m/s, 25/31 falls lie in that first-tread interval and 7 stalls end at 1.238–2.083 m. The two remaining nominal 0.5 m/s falls lie at root x≈1.2001 m. Low material 0.3 m/s has 4 falls and 0 stalls. Root endpoints localize the robot, not a measured limb/collider contact point.

Representative env 480, seed 307, falls at 0.3 m/s with nominal materials in both configurations: `none` ends at t 4.42 s/root x 1.1904 m; `basic` ends at t 4.44 s/root x 1.1895 m. Their recorded pitch near the end is about +0.42 rad. At the last `none` sample the base current-force norm is 12.3 N; fall classification includes a > 1 N base-force gate, so a large pitch angle is not required for a fall label. The basic trace ends 20 ms before its terminal result and cannot identify the exact terminal trigger. In this same seed/env, nominal 0.5 m/s and basic low 0.3 m/s complete, despite continuing calf contacts and sometimes larger pitch angles through the flight.

Representative basic nominal 0.3 m/s, seed 101/env 480, stalls at 13.94 s. Its recorded plateau from 11.62–13.92 s holds root x≈1.843 m, |vx|≤0.0034 m/s and pitch≈0.602 rad. FR calf current-force norm remains 65.1–70.2 N; FR foot current-contact is false in all 24 plateau samples while FL/RL/RR gates are true. At 13.92 s the FR calf force vector is [4.33, 0.0044, 69.32] N, base current force is zero and action-delta RMS is 8.8e−5. Low material in that seed/env completes 11.64 s. This supports a persistent calf-supported low-progress configuration as an observed stall mode; it does not locate the contact or prove that friction causes the support state.

The reported base mass/inertia, COM and actuator PD readback objects match exactly across all four conditions, as do all 96 stored initial root XYZ positions for each paired comparison. Evaluated dynamics randomization was false even for the `basic`-profile launches. `none` nominal and `basic` nominal both read back foot coefficients 0.8 static/0.6 dynamic; low reads back 0.45/0.35. The profile label must not be described as a tested mass/COM randomization in this comparison. Initial XYZ and readback agreement do not include every simulator state variable: `none` and `basic` nominal still differ 54 vs 58 completions. Terrain material readbacks also match after excluding the anonymous USD stage identifier, the only differing terrain-readback field. Solver contact-pair effective friction was unavailable.

Matched episode labels also show reversals: nominal 0.3→0.5 has 42 failed episodes become successful and two previously successful episodes fall; basic nominal→low has 36 failed episodes become successful and two previously successful episodes fall. Even with matching stored initial positions, these observations do not establish universal improvement.

Higher completion does not coincide with lower slip proxy: nominal speed 0.5 averages 0.281 vs 0.234 at 0.3; low material 0.3 averages 0.330 vs 0.232 for basic nominal. Pitch RMS is also higher for nominal 0.5. Contact timing, support and progression may be involved, but the saved data cannot isolate a causal mechanism or demonstrate less scraping.

Detailed traces cover only env 480 in each seed, with 100 ms sample spacing; all 96 per-condition first-episode endpoints and outcomes are used in the population plots. Inactive post-episode/reset rows were excluded. No stretch-condition video or exact collision-point measurement is available. The successful 16 cm / long 12 videos are different geometries and do not visually certify these stretch failures.

Only existing primary-policy phases were read; secondary candidates and zero-action phases were excluded. Frozen primary checkpoint SHA256 is `79fcc69b9447ecfb4df9fcfb41224cdab78632649f38fd9faf09c7b6adf69c61`. Source provenance remains as recorded in the linked configs, including dirty state. No GPU launch, runtime/protocol change, or Git operation was performed.

Artifacts: [all-condition associations](stair-stretch-association-review.png), [seed 307 representative traces](stair-stretch-association-review-representative-traces.png), [seed 101 stall support](stair-stretch-association-review-stall.png), [machine-readable evidence](stair-stretch-association-review.json), [384 first-episode endpoints](stair-stretch-association-review.csv). Each figure also has a PDF. Raw run directories and SHA256 config/result/material hashes are retained in the JSON.
