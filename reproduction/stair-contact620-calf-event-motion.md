# Saved staircase motion analysis

CPU-only saved first-episode trace analysis; no acceptance thresholds changed.

Trace peaks are sampled observations. Existing evaluator case metrics and traversal outcomes remain authoritative.

| Source / seed / case / env | Cadence s | Completed / stall / escape | Sampled action second peak | Sampled leg aggregate peak N | Largest flight foot retraction m |
|---|---:|---|---:|---:|---:|
| 2026-10-11_04-31-42_contact620-calf-event-batch-video / 47 / 13 / 416 | 0.020 | True / False / False | 0.592 | 617.161 | 0.030 |

Named current/history body peaks and their times/positions are in JSON and CSV. Unrecorded per-leg values are unavailable.

| Matched seed / case | Left completion | Right completion | Right − left action second RMS | Right − left jerk RMS | Eligible controlled motion comparison |
|---|---:|---:|---:|---:|---|

Comparison direction follows input order. Failing/stalled comparators and mismatched construction evidence are labeled descriptive only.

- Source case statistics cover all measured policy steps; trace statistics cover only recorded active samples.
- Current/history contact and foot-link horizontal speed are proxies, not exact scraping/slip duration.
- Sparse action snapshots are never differentiated; recorded policy-step action differences are retained.
- Named leg force is never reconstructed from aggregate shank force.
- Low action variation in a stalled policy does not establish smooth traversal.
- This analysis does not replace continuous video review, unseen-case validation or material/dynamics tests.
