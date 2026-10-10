# Matched contact reward ablation: 50 and 100 updates

Status: all eight branch/update/speed reports are complete. Each branch continues from model570 for the same 50 or 100 updates. All 24 geometries, reset seeds 11/29/47, 32 environments per case/seed and the original 95% casewise gate are preserved. Each training branch uses seed 1; evaluation reset seeds are not independent training repetitions.

Both branches restore HIMActorCritic, HIMPPO, the HIM estimator and Adam state from model570. They use 4096 environments, 100 total updates, maximum initial terrain level 4 (initial levels sampled from 0 through 4), command range 0.25–0.65 m/s and fixed learning rate 0.0001 for PPO and HIM, with no exploration standard deviation override. Checked training/terrain manifests, restored optimizer rates and initial exploration summaries match. Their only reward weight difference is leg_contacts=-0.1 on eight thigh/calf bodies above 1 N. The released Go1 collision weight is zero, so this contact term is a Go2 adaptation.

Training source commits differ (`84b9816` for contact; `d3d38d6` for faithful, with tracked files dirty). Between those commits, tracked adapter, reward, terrain and vendored algorithm files did not change; domain readback code did. Saved manifests match the checked controls, but the dirty runtime source limits verification beyond its saved manifest. This evidence does not establish equal per-environment RNG state, full trajectories or deterministic GPU execution.

| Update / added updates | Branch | Speed (m/s) | Completed | Worst case/seed | Case/seed gates | Final gate | Maximum pause (s) | Falls/stalls/escapes |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | --- |
| 620/50 | faithful | 0.3 | 2292/2304 | 29/32 | 69/72 | False | 3.740 | 4/8/0 |
| 620/50 | contact | 0.3 | 2302/2304 | 31/32 | 72/72 | True | 3.620 | 0/2/0 |
| 670/100 | faithful | 0.3 | 2302/2304 | 31/32 | 72/72 | True | 3.760 | 0/2/0 |
| 670/100 | contact | 0.3 | 2302/2304 | 30/32 | 71/72 | False | 3.540 | 0/2/0 |
| 620/50 | faithful | 0.5 | 2304/2304 | 32/32 | 72/72 | True | 0.240 | 0/0/0 |
| 620/50 | contact | 0.5 | 2304/2304 | 32/32 | 72/72 | True | 0.080 | 0/0/0 |
| 670/100 | faithful | 0.5 | 2304/2304 | 32/32 | 72/72 | True | 0.220 | 0/0/0 |
| 670/100 | contact | 0.5 | 2304/2304 | 32/32 | 72/72 | True | 0.140 | 0/0/0 |

With 32 environments, 31/32 passes the recorded 95% gate; 30/32 fails. Failure flags are nonexclusive. An overall completion total cannot replace the worst case/seed gate.

## Matched motion and contact changes

| Added updates | Speed (m/s) | Lower current leg contact cases | Lower action second difference cases | Lower jerk cases | Lower current slip cases | Lower tracking error cases | Lower lateral error cases | Both full and failure-free cases |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 50 | 0.3 | 24/24 | 4/24 | 8/24 | 16/24 | 8/24 | 1/24 | 20/24 |
| 50 | 0.5 | 24/24 | 1/24 | 9/24 | 1/24 | 10/24 | 12/24 | 24/24 |
| 100 | 0.3 | 24/24 | 19/24 | 21/24 | 1/24 | 13/24 | 22/24 | 22/24 |
| 100 | 0.5 | 24/24 | 20/24 | 22/24 | 15/24 | 12/24 | 8/24 | 24/24 |

Each lower count compares contact minus faithful case means at equal update count and speed. These are strict numerical differences, with no calibrated significance threshold. Failed or shortened episodes remain in the data. A lower contact or action measure on such episodes does not establish smoother competent traversal. Metrics average three seed aggregates per case, then weight cases equally; they are not pooled trajectory RMS.

| Added updates / speed / direction | Branch | Current leg contact | Action second RMS | Root jerk (m/s³) | Current slip proxy | XY tracking RMSE (m/s) | Lateral error (m) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 50/0.3/ascending | faithful | 17.86% | 0.09377 | 49.91 | 14.37% | 0.06923 | 0.08196 |
| 50/0.3/ascending | contact | 8.61% | 0.09687 | 46.63 | 14.20% | 0.05900 | 0.10150 |
| 50/0.3/descending | faithful | 39.55% | 0.07210 | 50.43 | 26.28% | 0.05780 | 0.04822 |
| 50/0.3/descending | contact | 30.68% | 0.07801 | 58.64 | 26.12% | 0.06433 | 0.05758 |
| 50/0.5/ascending | faithful | 14.98% | 0.16401 | 75.59 | 16.67% | 0.06867 | 0.05215 |
| 50/0.5/ascending | contact | 9.20% | 0.17575 | 74.18 | 17.58% | 0.06725 | 0.06249 |
| 50/0.5/descending | faithful | 39.71% | 0.11360 | 84.35 | 23.40% | 0.06693 | 0.05999 |
| 50/0.5/descending | contact | 20.07% | 0.11820 | 91.19 | 24.83% | 0.06840 | 0.05477 |
| 100/0.3/ascending | faithful | 22.24% | 0.09665 | 50.61 | 14.25% | 0.07110 | 0.08929 |
| 100/0.3/ascending | contact | 8.88% | 0.09195 | 43.35 | 16.00% | 0.05815 | 0.04905 |
| 100/0.3/descending | faithful | 45.09% | 0.07297 | 54.26 | 24.79% | 0.04899 | 0.05339 |
| 100/0.3/descending | contact | 29.85% | 0.07243 | 53.73 | 26.36% | 0.05662 | 0.05062 |
| 100/0.5/ascending | faithful | 20.02% | 0.17073 | 81.97 | 18.03% | 0.06681 | 0.06131 |
| 100/0.5/ascending | contact | 9.02% | 0.16804 | 69.74 | 16.66% | 0.06575 | 0.05423 |
| 100/0.5/descending | faithful | 44.81% | 0.11904 | 88.04 | 23.97% | 0.06330 | 0.05431 |
| 100/0.5/descending | contact | 20.15% | 0.11694 | 81.20 | 24.69% | 0.06747 | 0.08602 |

## Interpretation and candidate readiness

At 0.5 m/s, all four policies complete 2304/2304, pass all 72 case/seed gates and record zero fall/stall/escape/base contact counts. Contact reduces current leg contact in all 24 geometries at both update counts. This effect in one matched training realization does not imply uniform smoothness.

After 50 updates at 0.5 m/s, contact has lower action second RMS in only 1/24 cases, lower jerk in 9/24 and lower current slip in 1/24. After 100 updates, the corresponding counts are 20/24, 22/24 and 15/24. In the 100-update descent means, current leg contact drops from 44.81% to 20.15% and jerk from 88.04 to 81.20 m/s³, while lateral error rises from 0.05431 to 0.08602 m and tracking RMSE from 0.06330 to 0.06747 m/s.

At 0.3 m/s, faithful670 and contact670 each complete 2302/2304. The faithful stalls are split between seeds 11 and 29 in case 20 (17 cm rise/27 cm tread/3 cm nose ascent), giving 31/31/32 and passing all case/seed gates. Contact stalls concentrate in case 15, seed 29 (20 cm rise/27 cm tread/no nose descent), giving 32/30/32 and failing the unchanged gate. Its full 0.5 m/s result does not erase this failure. Contact has lower current leg contact in 24/24 low-speed cases after 100 updates, lower action second RMS in 19/24 and jerk in 21/24, but lower current slip in only 1/24.

The gate-qualified policies on this two-speed tuning matrix are **faithful670, contact620**. Keep **contact620** as the contact-branch candidate for independent final testing. The contact-only 620/640/670 selection is preserved in `stair-contact-checkpoint-selection.md`. Passing the tuning gate does not certify smoothness; remaining pauses, current/history contact, forces, slipping and tracking must be reviewed together. No weighted scalar score selects a universal winner.

## Independent saved motion review

| Added updates | Speed (m/s) | Matched case/seed pairs | Eligible under saved evidence and 95% gates | Both full and failure-free | Protocol differences |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 50 | 0.3 | 72 | 69 | 62 | 0 |
| 50 | 0.5 | 72 | 72 | 72 | 0 |
| 100 | 0.3 | 72 | 71 | 69 | 0 |
| 100 | 0.5 | 72 | 72 | 72 | 0 |

The CPU analyzer uses the saved 95% gate for eligibility, so a passing 31/32 row can include one stall. The full/failure-free column makes that difference explicit. The excluded 100-update low-speed pair is seed 29/case 15: contact lowers current leg contact by 24.18 percentage points but increases action second RMS by 0.01145, jerk by 29.77 m/s³ and tracking RMSE by 0.01314 m/s, with two stalls. Its reduced contact cannot demonstrate competent smoothness.

| Added updates / speed | Branch | Active representative rows after warmup | Largest sampled current named leg force (N) | Largest retained-history force (N) |
| --- | --- | ---: | ---: | ---: |
| 50/0.3 | faithful | 9150 | 423.5 | 443.6 |
| 50/0.3 | contact | 9048 | 489.6 | 617.2 |
| 50/0.5 | faithful | 5324 | 394.5 | 420.3 |
| 50/0.5 | contact | 5292 | 341.6 | 420.1 |
| 100/0.3 | faithful | 8708 | 300.6 | 412.0 |
| 100/0.3 | contact | 8938 | 621.9 | 716.6 |
| 100/0.5 | faithful | 5191 | 299.4 | 465.1 |
| 100/0.5 | contact | 5253 | 478.2 | 478.2 |

These are sparse 0.1 s traces from one environment per case/seed, not whole-batch impact maxima, tangential friction forces or contact duration. Peak bodies, cases and times are retained in JSON and can differ between policies. Lower contact frequency, action variation or jerk can coexist with large sampled forces; cross-policy peak ratios do not isolate impact severity.

## Recorded failures

contact620, 0.3 m/s, case 8 (asc; 17/25/0 cm rise/tread/nose): seed completions 31/31/32; geometry gate=True; maximum pause 3.620 s. seed 11, env 284, flags ['stall'], root xyz [1.763127326965332, 0.15993118286132812, 0.9231264591217041]; seed 29, env 277, flags ['stall'], root xyz [2.014478921890259, 0.22210407257080078, 1.0921097993850708].

contact670, 0.3 m/s, case 15 (desc; 20/27/0 cm rise/tread/nose): seed completions 32/30/32; geometry gate=False; maximum pause 3.540 s. seed 29, env 485, flags ['stall'], root xyz [2.393447160720825, -0.0070819854736328125, -0.8389308452606201]; seed 29, env 495, flags ['stall'], root xyz [2.416645050048828, -0.013965606689453125, -0.8347141742706299].

faithful620, 0.3 m/s, case 4 (asc; 14/27/0 cm rise/tread/nose): seed completions 31/32/31; geometry gate=True; maximum pause 3.740 s. seed 11, env 134, flags ['stall'], root xyz [1.8904175758361816, 0.0921630859375, 0.7472989559173584]; seed 47, env 145, flags ['stall'], root xyz [2.160433053970337, 0.07081985473632812, 0.8843061327934265].

faithful620, 0.3 m/s, case 15 (desc; 20/27/0 cm rise/tread/nose): seed completions 30/31/31; geometry gate=False; maximum pause 0.080 s. seed 11, env 503, flags ['fall'], root xyz [1.4363195896148682, 0.16972732543945312, -0.0738382339477539]; seed 11, env 511, flags ['fall'], root xyz [1.4428987503051758, 0.2708158493041992, -0.0624699592590332]; seed 29, env 482, flags ['fall'], root xyz [1.3947162628173828, 0.14865779876708984, -0.019225358963012695]; seed 47, env 490, flags ['fall'], root xyz [1.384621024131775, 0.28715991973876953, -0.022881269454956055].

faithful620, 0.3 m/s, case 23 (desc; 20/25/2 cm rise/tread/nose): seed completions 29/31/30; geometry gate=False; maximum pause 3.600 s. seed 11, env 761, flags ['stall'], root xyz [2.327608108520508, 0.09286880493164062, -0.8522521257400513]; seed 11, env 765, flags ['stall'], root xyz [2.3318684101104736, 0.0766448974609375, -0.8498748540878296]; seed 11, env 767, flags ['stall'], root xyz [2.3276467323303223, 0.1077117919921875, -0.8529876470565796]; seed 29, env 739, flags ['stall'], root xyz [2.3266663551330566, 0.041271209716796875, -0.8585985898971558]; seed 47, env 744, flags ['stall'], root xyz [2.328399896621704, 0.01004791259765625, -0.8556197881698608]; seed 47, env 748, flags ['stall'], root xyz [2.326979875564575, 0.15587615966796875, -0.8571599721908569].

faithful670, 0.3 m/s, case 20 (asc; 17/27/3 cm rise/tread/nose): seed completions 31/31/32; geometry gate=True; maximum pause 3.760 s. seed 11, env 652, flags ['stall'], root xyz [1.8268951177597046, 0.09083366394042969, 0.8458822965621948]; seed 29, env 661, flags ['stall'], root xyz [1.8035845756530762, 0.08683204650878906, 0.8423051834106445].

The faithful620 fall labels are aggregate termination flags, with zero recorded base contacts. Its failed environments lack representative traces; terminal positions alone do not establish physical toppling or a specific collision cause.

## Matching and measurement limits

The 100-update policies at each speed share one evaluation construction, as do both 50-update low-speed policies. The 50-update contact620 high-speed result is reused from an earlier construction. Saved geometries, reset seeds, per-environment initial root xyz, aggregate initial pose records, headings/controller, thresholds, contact sampling and nominal mass/inertia/COM/PD/foot readbacks match. Full per-environment initial quaternions are missing. The older high-speed run lacks the new terrain USD material readback, so direct matching of those terrain readbacks is unverified.

Foot material snapshots are fixed at static/dynamic friction 0.8/0.6 and restitution 0. Nominal domain mode applies its material event to all robot bodies, so this is not an isolated foot friction test. New terrain USD provenance records composed authored friction 1/1, restitution 0 and multiply combination. Those are not solver-effective contact-pair coefficients. Reset seeds do not resample startup materials.

Current/history any-leg contact means presence at policy boundaries; it does not measure scrape duration, damage, the reward body count or tangential friction. At 5 ms physics and 20 ms policy steps, history length 3 retains ages 0/5/10 ms; a first-substep-only impact at age 15 ms can be overwritten. Current net-normal vector norms include horizontal riser normals. Slip uses foot-link world horizontal speed conditioned on contact, with different current/history denominators. First episodes are captured before autoreset and stop at completion/failure; ordinary metrics exclude the first second.

A pause flag is not smoothness acceptance. Use independent final geometries and seeds at both speeds, alongside force/contact/action/jerk/tracking evidence and visual review of stalled, drifting and high-contact cases. Preserve tuning failures and the original gate. One training seed cannot establish broad reward causality, robustness across training seeds or arbitrary stairs.
