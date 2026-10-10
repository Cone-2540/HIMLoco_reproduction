# Go2 staircase contact geometry and rigid-body attribution audit

Read-only CPU audit, 2026-10-11. No GPU rollout, collider/asset/stage edit,
physics step, driver change, training change or reward change was performed.
The machine-readable evidence is `go2-contact-geometry-readback.json` in this
directory. It records every parsed collider, body, fixed joint, transform,
material binding, shape count and source hash; stage-root serialization is
identical before and after the audit.

## Finding

The current asset has separate foot rigid bodies with separate spherical
colliders. Each calf owns three additional cylinders, and each thigh owns a
box. The OpenUSD physics parser explicitly assigns the foot sphere to the foot,
not the calf. Existing live PhysX material readback retains independent foot
body IDs 15–18 and foot shape slots 23–26. There is no evidence of a fixed-foot
merge or a duplicated foot sphere being reported again as a calf collider.
The local contact-sensor implementation also copies each body-pattern's net
contact force to that body's output; it does not sum fixed-joint reactions or
foot forces into the calf output.

However, the distal calf cylinder genuinely intersects the upper portion of
the foot sphere in this asset. Calf-owned ankle geometry can therefore contact
a stair edge/riser while the foot sphere also contacts the terrain. This is
different from both duplicated sensor attribution and a proven long scrape
along the shin. Current body force norms do not identify which calf cylinder,
which stair surface, the contact position or tangential motion. The geometry
audit cannot establish the mechanism of the reported 489.6 N or 291.9 N events
without synchronized contact/pose evidence.

## Asset and parser provenance

- Host asset: `/home/cone/isaaclab/data/assets/isaaclab6.1/Go2/go2.usd`.
- Container asset: `/workspace/isaaclab/data_storage/assets/isaaclab6.1/Go2/go2.usd`.
- Referenced geometry: `Props/instanceable_meshes.usd`; traversing instance
  proxies is necessary to see the collision prims.
- `go2.usd` SHA-256:
  `ba171c972b987d8c8fb7157ccad2ba9c0c1fed105755d2d8af46bef96cc11c6d`.
- `instanceable_meshes.usd` SHA-256:
  `82087cf9d4f6deeecb3437560b6061847f5f0228f7e524e253ed5e88cf218c08`.
- Stage units are metres, Z-up. The CPU reader uses `Usd.Stage.Open`,
  `Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies())`,
  `UsdGeom.XformCache`, and the installed
  `UsdPhysics.LoadUsdPhysicsFromRange(stage, [Sdf.Path('/go2_description')])`.
- The parser returns **19 rigid bodies, 27 collision shapes, 6 fixed joints**
  and one articulation. All 27 shapes are valid and collision-enabled.

This is authored/parsed USD evidence, rather than a new live PhysX cooking or
contact-pair dump. The running config explicitly selects `isaacsim_physx`
(`isaaclab/run.py:170`) and references this USD (`run.py:177`). It does not
invoke the URDF converter's `merge_fixed_joints` option. The installed Newton
parser is not the active backend and is not used as evidence for PhysX.

## Exact rigid-body and shape ownership

For every leg `L` in FL/FR/RL/RR, the body prims are siblings under
`/go2_description`: `L_thigh`, `L_calf`, and `L_foot`. The collision Xforms are
children of their respective owner, not descendants of another rigid body.
For example:

| Collision prim | Parent prim | Parsed rigid-body owner |
| --- | --- | --- |
| `/go2_description/FR_thigh/collisions/mesh_0` | `FR_thigh/collisions` | `/go2_description/FR_thigh` |
| `/go2_description/FR_calf/collisions/mesh_0` | `FR_calf/collisions` | `/go2_description/FR_calf` |
| `/go2_description/FR_calf/collisions/mesh_1` | `FR_calf/collisions` | `/go2_description/FR_calf` |
| `/go2_description/FR_calf/collisions/mesh_2` | `FR_calf/collisions` | `/go2_description/FR_calf` |
| `/go2_description/FR_foot/collisions/mesh_0` | `FR_foot/collisions` | `/go2_description/FR_foot` |

Shape counts are: base 1 box; four hips 1 cylinder each; four thighs 1 box each;
four calves 3 cylinders each; four feet 1 sphere each; Head_upper 1 cylinder;
Head_lower 1 sphere. Total: `1 + 4 + 4 + 12 + 4 + 1 + 1 = 27`.
Foot source mass is 0.04 kg per link; each calf is 0.154 kg, each thigh 1.152 kg.

Each `L_calf/L_foot_joint` is an enabled `PhysicsFixedJoint`, body0=`L_calf`,
body1=`L_foot`, `excludeFromArticulation=False`. Its calf-local anchor is
`(0, 0, -0.213)` m and foot-local anchor `(0, 0, 0)`; both local joint
orientations are the same, so the preserved source relative foot rotation is
identity. Fixed-joint pair collision is disabled. A fixed joint constrains
relative motion; its presence does not make the foot sphere a calf-owned shape.

## Dimensions and locations

Positions below are in the **owning rigid body's frame**, not world coordinates
on a stair. Cylinder height is full axial height; axis vectors are local Z
after the collider's rotation. These are physical shape parameters and composed
transforms; the report does not treat a visual mesh or an authored `extent`
alone as a collision surface.

| Shape | Geometry and size (m) | Centre (m) | Axis in body frame |
| --- | --- | --- | --- |
| Every thigh `mesh_0` | box; body-axis dimensions `(0.034, 0.0245, 0.213)` | `(0, 0, -0.1065)` | long axis along body Z; canonical box rotated +90° about Y |
| FL calf `mesh_0` | cylinder r=0.012, h=0.120 | `(0.008, 0, -0.060)` | `(-0.20846, 0, 0.97803)` |
| FR/RL/RR calf `mesh_0` | cylinder r=0.013, h=0.120 | `(0.010, 0, -0.060)` | `(-0.19867, 0, 0.98007)` |
| Every calf `mesh_1` | cylinder r=0.011, h=0.065 | `(0.020, 0, -0.148)` | `(0.04998, 0, 0.99875)` |
| Every calf `mesh_2` | cylinder r=0.0155, h=0.030 | `(0.0080133, 0, -0.1874502)` | `(0.50553, 0, 0.86281)` |
| Every foot `mesh_0` | sphere r=0.022 | `(-0.002, 0, 0)` in foot frame | sphere; no preferred axis |

The calf's full collision envelope runs from about z=+0.0014 to z=-0.20823 m
in its own frame. The foot sphere centre in that same calf frame is
`(-0.002, 0, -0.213)` and its source-frame bottom is z=-0.235 m.
The distal cylinder's lower cap centre is
`(0.0004303, 0, -0.2003923)` m. It is **0.0128398 m** from the foot sphere
centre, less than the sphere radius **0.022 m**, establishing actual solid
intersection, rather than merely overlapping bounding boxes. The calf geometry
is about 26.77 mm above the lowest foot-sphere point in this source orientation.
Runtime joint/body rotation changes world clearances to a tread or riser.

This overlap does not mean that the exact sphere is duplicated. There are two
different collision shapes owned by two retained rigid bodies. With self
collisions disabled in the configured Go2, their internal overlap is not
intended to produce calf-foot self-contact, but both can independently meet an
external edge. The small FL-versus-other-calf geometry difference is recorded;
it does not by itself explain an FR peak or learned asymmetry.

## Runtime mapping and material limits

The following exact mapping appears in the initial readbacks of
`04-07-03_contact620-interim-regression`,
`04-13-00_contact620-640-speed05-tuning`, and
`04-17-41_stairs-hard-faithful-control670` under `isaaclab/logs`:

| Foot name | Public body ID | Backend body ID | USD-owned sphere count |
| --- | ---: | ---: | ---: |
| FL_foot | 15 | 15 | 1 |
| FR_foot | 16 | 16 | 1 |
| RL_foot | 17 | 17 | 1 |
| RR_foot | 18 | 18 | 1 |

The JSON records foot shape slots `[23, 24, 25, 26]` as one flat list, not a per-foot
shape-ID dictionary. USD predicts one sphere per foot and the observed four
foot slots agree. Do not present an unrecorded per-foot PhysX shape-path map or
all calf backend indices as measured. The current reader derives ranges from
per-link `create_rigid_body_view(link_path).max_shapes` in backend link order,
maps public IDs with `map_body_ids_to_backend`, and checks that their sum equals
the articulation's `max_shapes` (`stair_randomization.py:181`). The actual full
per-body backend shape-count list is not saved in these snapshots.

The source USD has no resolved physics-material binding on any of its 27
colliders; parsed `materials` lists are empty. This does **not** mean that the
runtime shapes lack materials. The startup PhysX material event writes the
material-property buffer; existing foot readback measures static/dynamic
0.8/0.6 and restitution 0. The current `none` profile selects all robot bodies;
basic/robust select feet. Direct per-calf/thigh material-property readback and
per-shape effective contact/rest offsets are not saved here. No source contact
or rest offset is authored on these colliders, so backend defaults/overrides
must not be invented from this CPU audit.

## Contact-sensor path and sampling

The PhysX articulation retains backend `root_view.link_paths` and initializes
with `create_articulation_view` (`isaaclab_physx/assets/articulation/articulation.py:3935`).
The sensor resolves contact-reporting **body** paths, creates one rigid-body
and rigid-contact view pattern per resolved body, and checks the returned body
count (`isaaclab_physx/sensors/contact_sensor/contact_sensor.py:335`).
`body_names` comes from actual body-view prim paths (`contact_sensor.py:164`).
It fetches `get_net_contact_forces(dt=physics_dt)` (`contact_sensor.py:502`).
The update kernel indexes `src_idx = sensor * num_envs + env` and copies that
single body's force into `[env, sensor]` without a fixed-joint or articulation
force sum (`contact_sensor/kernels.py:282`). This is a contact reporter, not a
joint-wrench readout.

An independent source review also checked the installed container tensor API:
`/isaac-sim/extscache/omni.physics.tensors-110.3.2+110.3.0.lx64.r.cp312.u7f4/omni/physics/tensors/api.py`.
Its sensor paths/names are backend-derived (lines 4895–4913); the net-contact
getter provides one vector per sensor and includes all interacting prims,
rather than only filter matches (4922–4952). Incoming joint wrench has a
separate getter (2228–2255), unused by this sensor. Articulation backend names
come from actual `root_view.shared_metatype.link_names`
(`isaaclab_physx/assets/articulation/articulation.py:179`), with explicit
public-order translation in `base_articulation.py:338`. The Python tensor API
delegates to the native backend: this audit does not claim to inspect closed
native contact/cooking code or to rule out every possible backend defect.

`StairStateCapture` selects eight thigh/calf names in robot order and looks up
each in the sensor's own names (`stair_evaluation.py:185`). The independent
9048-row contact620 trace audit verifies eight finite values, history≥current,
and agreement with the aggregate shank maxima. This protects row/name mapping;
it does not resolve the three calf shapes, contact partner or surface location.
Current measurements are the final 5 ms step at a 20 ms policy boundary;
three history slots retain 0/5/10 ms, and 100 ms saved traces miss intervening
impacts. Norms erase direction, and net contact force can combine multiple
points; opposing normals can cancel, so a norm is not a scalar sum of patch
forces or the largest individual patch force. Neither a large norm nor a
17–34% presence fraction establishes
scraping duration, contact-point tangential speed, damage or a per-shape peak.

The installed `omni.cip.core/common/physics_utils.py` is a collider-authoring/
cooking helper. Its merge helper concerns selected meshes, not proof that this
running articulation merges fixed foot links. It was read only; no helper was
invoked and no collider API was applied. The parser ownership and existing
backend evidence are the applicable observations here.

## Concrete events and verification needed

In `04-07-03_contact620-interim-regression/result.json`, these are **current**
force peaks from the traced first episodes after the first second:

| Body | Current force | Seed / original env / case | Time | Correlated sample |
| --- | ---: | --- | ---: | --- |
| FR_calf | 489.5798 N | 47 / 416 / 13: 18 cm, 27 cm tread, no nose descent | 8.32 s | FR_foot also in contact; body pitch 0.34390 rad |
| FR_thigh | 291.9363 N | 47 / 480 / 15: 20 cm, 27 cm tread, no nose descent | 3.32 s | FR_foot in contact; FL_calf 66.1540 N; pitch 0.11483 rad |

The traces contain root orientation and foot link positions, but lack joint
positions, calf/thigh link poses, normal-force vectors and contact positions.
They cannot locate a calf cylinder or show that the thigh box met the riser.
Single-case seed-47 video has different environment/RNG allocation from the
original 768-env batch and is not automatically a replay of env 416 or 480.
Use it as a qualitative check unless original initialization and scene ordering
are reproduced and verified.

For a mechanism-level diagnostic, keep the checkpoint, controller, asset,
physics settings and gates fixed. Record side/front views close to the right
front ankle and thigh on these descents, plus synchronized numerical samples:

1. Actual body-view prim paths, public→backend mapping, per-link shape counts,
   and actual shape material/contact-offset values. Save the raw map, not only
   a name-ordered body force array.
2. Leg/foot link world poses, joint positions and **world force vectors** for
   each physics substep; preserve all four substeps rather than only the last
   sample or a three-slot history. An evaluator `record_stride=1` still gives
   policy-rate 20 ms snapshots and does not by itself supply 5 ms evidence.
3. Terrain-filtered per-body contacts: normal forces, individual contact
   points, normals/separation and partner identity, with counts/start indices
   where exposed. Sensor `track_contact_points` with a terrain filter gives
   group-averaged points; raw `get_contact_data` is preferable when several
   points/surfaces meet. Do not pretend an averaged point identifies one of
   three calf cylinders.
4. Transform the recorded points into the owning link frame and compare them
   against these parsed cylinder/box/sphere surfaces and exact stair geometry.
   This distinguishes distal ankle overlap, mid-calf/riser contact, thigh-box
   contact and any unexpected partner. Visible touch alone cannot establish
   force; combine video with the synchronized contact records. Tangential
   contact-point velocity/friction data is needed for a scrape/slip claim.

These are proposed read-only diagnostic measurements, not implemented changes
or claims that the missing mechanism has been verified. Retain the current
contact counts as body-contact proxies and do not remove the calf penalty or
alter colliders on the basis of an unproven sensor-duplication explanation.
