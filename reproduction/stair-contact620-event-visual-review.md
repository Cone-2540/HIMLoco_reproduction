# Contact620 calf event visual review

CPU analysis of seed 47, env 416, case 13 (six descending 18 cm steps, 27 cm depth, no nosing) at 0.3 m/s. Selected stills from the isolated 50 fps replay are shown in `stair-contact620-event-visual-review.png`; complete numeric geometry and replay comparisons are in the adjacent JSON.

The full-batch and visibility-isolated `result.json` files are byte-for-byte identical. All 768 environments complete in both replays, and all first-episode per-env fields, metrics, 24 case results, initial reset fields, and 861 trace rows (including every force/pose value) match exactly. This supports the visual-only isolation leaving these recorded physics results unchanged.

The environment origin reconstructed independently from all four fixed calf-to-foot transforms is [-1.8099999304901937, 4.499999997596711, 1.080000001112198] m. Across 2812 active foot pose samples, maximum component residuals are [4.3552117157119596e-07, 4.790157195344591e-07, 1.4102080347910828e-07] m.

| Time | Current FR_calf normal vector [N] | Norm [N] | Nearest nominal source cylinder | Descending upper edge (x,z) [m] | Nominal signed edge/cylinder gap |
|---|---|---:|---|---|---:|
| 7.18 s | (238.088608, approximately 0, 190.015442) | 304.617859 | FR_calf/mesh_0, long proximal cylinder | after tread 3: (1.81, -0.54) | -0.545 mm |
| 8.32 s | (402.527557, approximately 0, 278.675354) | 489.579803 | FR_calf/mesh_0, long proximal cylinder | after tread 4: (2.08, -0.72) | -0.501 mm |

At 7.18 s the other source cylinders are 88.6 mm and 137.0 mm from their nearest descending upper edge; at 8.32 s they are 80.2 mm and 129.2 mm away. The near-zero mesh_0 gaps and positive X/Z normal force support a proximal-calf/edge collision interpretation. Negative source-cylinder signed gaps mean the ideal authored edge lies about 0.5 mm inside the transformed authored cylinder; they are not measured PhysX penetration depths. The foot sphere has its own rigid-body owner and is drawn separately.

Each event includes seven frames at 20 ms intervals from 60 ms before to 60 ms after. The nominal simulation-time mapping is encoded video PTS + 20 ms, based on one post-step recording per policy step; exact renderer/physics synchronization was not instrumented. Every selected frame is inside env 416’s measured active first episode.

The selected stills show the body sloping downhill, with the rear feet higher than the front feet. At 8.32 s, recorded current force rises from 0 N at 8.30 s to 489.6 N, then returns to 0 N at 8.34 s. This describes policy-boundary samples, not the duration or impulse of the underlying contact.

This review uses selected stills only. Continuous video was not watched. No measured contact points, per-shape forces, cooked collision mapping, or effective collision offsets are available. The sensor reports net normal vectors and excludes friction; several normals can sum or cancel. These two highlighted retained-history peaks also appear in the current sample, so their recorded current poses are relevant, but the same inference must not be applied to older history-only peaks.

No GPU launch, simulator run, policy edit, source edit, commit, or push was performed for this analysis.
