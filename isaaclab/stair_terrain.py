"""Straight stairs for training and independent held-out evaluation.

All paths travel in +x: ``asc`` gains elevation and ``desc`` loses elevation.
Default flights have six risers, a 1.2 m corridor and 2 m landings at both
ends. Fixed held-out specs can use longer flights and wider corridors. A
nosing is a thin, closed slab that overhangs the lower surface;
its underside remains a real collision surface. No heightfield conversion is
allowed. Actor observations remain unchanged by this module.

Geometry metadata uses coordinates relative to the returned terrain origin,
the centre of the starting landing. Lab translates mesh and origin together,
so those coordinates also apply relative to ``scene.env_origins``.
"""

from __future__ import annotations

import math

import numpy as np
import torch
import trimesh
from isaaclab.managers import CurriculumTermCfg, TerminationTermCfg
from isaaclab.sensors import patterns
from isaaclab.terrains import SubTerrainBaseCfg, TerrainGeneratorCfg
from isaaclab.utils import configclass


STAGES = {
    "easy": {"height_range": (0.05, 0.12), "depths": (0.28, 0.30, 0.32, 0.36), "nosings": (0.0,)},
    "standard": {"height_range": (0.05, 0.17), "depths": (0.20, 0.25, 0.27, 0.30, 0.35, 0.40), "nosings": (0.0,)},
    "hard": {"height_range": (0.08, 0.23), "depths": (0.20, 0.25, 0.27, 0.30, 0.35, 0.40), "nosings": (0.0, 0.01, 0.02, 0.03)},
}


def stair_metadata(step_height=0.16, step_depth=0.27, nosing=0.0, direction="asc",
                   num_steps=6, width=1.2, landing_length=2.0, size=(8.0, 3.0),
                   nosing_thickness=0.02):
    """Describe one exact flight, using SI units and terrain-origin coordinates."""
    if direction not in ("asc", "desc"):
        raise ValueError("direction must be asc or desc")
    values = (step_height, step_depth, nosing, num_steps, width, landing_length, *size, nosing_thickness)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("Stair dimensions must be finite")
    if (num_steps < 1 or int(num_steps) != num_steps or step_height <= 0 or step_depth <= 0
            or width <= 0 or landing_length <= 0 or nosing < 0 or nosing >= step_depth
            or nosing_thickness <= 0 or nosing_thickness >= step_height):
        raise ValueError("Invalid stair dimensions or nosing thickness")
    num_steps = int(num_steps)
    length = 2 * landing_length + num_steps * step_depth
    if size[0] < length or size[1] < width:
        raise ValueError("Flight and landings must fit in terrain size")
    sign = 1 if direction == "asc" else -1
    first = landing_length / 2.0
    goal_platform_start = first + num_steps * step_depth
    start_z = 0.0 if direction == "asc" else num_steps * step_height
    origin = [(size[0] - length) / 2 + landing_length / 2, size[1] / 2, start_z]
    treads = [
        {"index": index + 1, "x_min": first + index * step_depth,
         "x_max": first + (index + 1) * step_depth,
         "top_z": sign * (index + 1) * step_height}
        for index in range(num_steps)
    ]
    return {
        "schema_version": 1, "direction": direction, "travel_sign": 1,
        "num_steps": int(num_steps), "step_height": float(step_height),
        "step_depth": float(step_depth), "width": float(width), "nosing": float(nosing),
        "nosing_thickness": float(nosing_thickness), "landing_length": float(landing_length),
        "start_x": 0.0, "first_riser_x": first,
        "last_riser_x": first + (num_steps - 1) * step_depth,
        "goal_platform_start_x": goal_platform_start,
        "goal_x": goal_platform_start + min(0.65, landing_length / 2),
        "flight_end_x": first + num_steps * step_depth + landing_length,
        "start_platform_z": 0.0, "goal_platform_z": sign * num_steps * step_height,
        "lateral_center_y": 0.0, "goal_dwell_s": 0.5,
        "terrain_local_origin": origin, "terrain_size": list(size), "treads": treads,
        "collision_representation": "closed triangle meshes with physical overhang undersides",
        "convert_to_heightfield": False,
    }


def _box(x0, x1, y0, y1, z0, z1, role):
    box = trimesh.creation.box(
        extents=(x1 - x0, y1 - y0, z1 - z0),
        transform=trimesh.transformations.translation_matrix(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)),
    )
    box.metadata["role"] = role
    return box


def stair_meshes(difficulty, cfg):
    """Isaac Lab terrain function returning closed meshes and the spawn origin."""
    d = float(difficulty)
    if not math.isfinite(d) or not 0 <= d <= 1:
        raise ValueError("difficulty must be finite and between 0 and 1")
    height = cfg.step_height_range[0] + d * (cfg.step_height_range[1] - cfg.step_height_range[0])
    geometry = stair_metadata(height, cfg.step_depth, cfg.nosing, cfg.direction,
                              cfg.num_steps, cfg.width, cfg.landing_length, cfg.size, cfg.nosing_thickness)
    origin = np.array(geometry["terrain_local_origin"], dtype=float)
    x_start = origin[0] - cfg.landing_length / 2
    y0, y1 = cfg.size[1] / 2 - cfg.width / 2, cfg.size[1] / 2 + cfg.width / 2
    meshes = [_box(0, cfg.size[0], 0, cfg.size[1], -0.10, 0, "foundation")]

    def surface(a, b, top, lip_sign=0, role="tread"):
        if top <= 0:
            return  # The common foundation supplies the zero-height surface.
        if cfg.nosing == 0 or lip_sign == 0:
            meshes.append(_box(a, b, y0, y1, 0, top, role))
        else:
            lower = top - cfg.nosing_thickness
            meshes.append(_box(a, b, y0, y1, 0, lower, role + "_support"))
            xa = a - cfg.nosing if lip_sign < 0 else a
            xb = b + cfg.nosing if lip_sign > 0 else b
            meshes.append(_box(xa, xb, y0, y1, lower, top, role + "_nosing"))

    flight_start = x_start + cfg.landing_length
    total_height = cfg.num_steps * height
    if cfg.direction == "desc":
        surface(x_start, flight_start, total_height, +1, "start_landing")
    for index in range(cfg.num_steps):
        a, b = flight_start + index * cfg.step_depth, flight_start + (index + 1) * cfg.step_depth
        top = (index + 1) * height if cfg.direction == "asc" else (cfg.num_steps - index - 1) * height
        surface(a, b, top, -1 if cfg.direction == "asc" else +1)
    if cfg.direction == "asc":
        end = flight_start + cfg.num_steps * cfg.step_depth
        surface(end, end + cfg.landing_length, total_height, 0, "goal_landing")
    for mesh in meshes:
        mesh.metadata["stair_geometry"] = geometry
    return meshes, origin


@configclass
class StraightStairTerrainCfg(SubTerrainBaseCfg):
    function = stair_meshes
    convert_to_heightfield: bool = False
    direction: str = "asc"
    step_height_range: tuple[float, float] = (0.05, 0.12)
    step_depth: float = 0.30
    width: float = 1.2
    num_steps: int = 6
    landing_length: float = 2.0
    nosing: float = 0.0
    nosing_thickness: float = 0.02


def _fixed_stair_spec(spec):
    """Validate dimensions and reserve at least 1 m extra length per tile."""
    height = float(spec.get("step_height", spec.get("height", 0.16)))
    depth = float(spec.get("step_depth", spec.get("depth", 0.27)))
    nose, direction = float(spec.get("nosing", 0.0)), spec.get("direction", "asc")
    count = float(spec.get("num_steps", 6))
    width = float(spec.get("width", 1.2))
    landing = float(spec.get("landing_length", 2.0))
    thickness = float(spec.get("nosing_thickness", 0.02))
    if not all(math.isfinite(value) for value in (height, depth, nose, count, width, landing, thickness)):
        raise ValueError("Stair dimensions must be finite")
    if count < 1 or count != int(count) or width <= 0 or landing <= 0 or depth <= 0:
        raise ValueError("Invalid stair flight dimensions")
    count = int(count)
    # Preserve default 8 x 3 m tiles. Longer flights expand in 2 m increments:
    # e.g. 12 * 0.40 + two 2 m landings = 8.8 m needs a 10 m tile.
    size = (max(8.0, 2.0 * math.ceil((2.0 * landing + count * depth + 1.0) / 2.0)),
            max(3.0, width + 1.0))
    stair_metadata(height, depth, nose, direction, count, width, landing, size, thickness)
    return StraightStairTerrainCfg(direction=direction, step_height_range=(height, height),
                                   step_depth=depth, nosing=nose, num_steps=count, width=width,
                                   landing_length=landing, nosing_thickness=thickness), size


def build_stair_generator(stage="easy", *, spec=None, num_rows=10, num_cols=24, seed=1):
    """Training uses ascending/descending variants; spec selects a fixed heldout flight.

    ``spec`` keys: step_height (or height), step_depth (or depth), nosing,
    direction, num_steps, width, landing_length. Heldout tiles expand to contain
    longer flights. Training retains six risers and default 8 m x 3 m tiles.
    """
    if stage not in STAGES:
        raise ValueError("stage must be easy, standard or hard")
    if num_rows < 1 or num_cols < 1:
        raise ValueError("Terrain grid dimensions must be positive")
    if spec is not None:
        term, size = _fixed_stair_spec(spec)
        variants = {"heldout": term}
        curriculum = False
    else:
        size = (8.0, 3.0)
        selected = STAGES[stage]
        variants = {}
        for direction in ("asc", "desc"):
            for depth in selected["depths"]:
                for nose in selected["nosings"]:
                    key = f"{direction}_tread_{depth:.2f}_nosing_{nose:.2f}"
                    variants[key] = StraightStairTerrainCfg(direction=direction,
                        step_height_range=selected["height_range"], step_depth=depth, nosing=nose)
        curriculum = True
        # Columns must represent every type; never silently omit a tread/nosing.
        num_cols = max(num_cols, len(variants))
    return TerrainGeneratorCfg(seed=seed, size=size, num_rows=num_rows, num_cols=num_cols,
                               curriculum=curriculum, sub_terrains=variants, border_width=4.0,
                               difficulty_range=(0.0, 1.0), use_cache=False, color_scheme="height")


def _column_stair_cfgs(generator_cfg):
    configs = list(generator_cfg.sub_terrains.values())
    cumulative = np.cumsum([term.proportion for term in configs], dtype=float)
    cumulative /= cumulative[-1]
    return [configs[int(np.searchsorted(cumulative, index / generator_cfg.num_cols + 0.001))]
            for index in range(generator_cfg.num_cols)]


def _column_geometry_tensors(env):
    """Resolve variant geometry once; per-step manager terms only index tensors."""
    generator = env.scene.terrain.cfg.terrain_generator
    if getattr(env, "_him_stair_geometry_source", None) != id(generator):
        configs = _column_stair_cfgs(generator)
        geometries = [stair_metadata(term.step_height_range[0], term.step_depth, term.nosing,
                                    term.direction, term.num_steps, term.width, term.landing_length,
                                    generator.size, term.nosing_thickness) for term in configs]
        env._him_stair_column_geometry = {
            name: torch.tensor([geometry[name] for geometry in geometries], device=env.device)
            for name in ("goal_x", "last_riser_x", "goal_platform_start_x", "width")
        }
        env._him_stair_geometry_source = id(generator)
    return env._him_stair_column_geometry


def _tensor(value):
    return value if isinstance(value, torch.Tensor) else value.torch


def stair_corridor_exit(env, width=None, margin=0.05):
    """End episodes that bypass the staircase by walking beside the corridor."""
    root = env.scene["robot"].data.root_pos_w.torch
    if width is None:
        width = _column_geometry_tensors(env)["width"][env.scene.terrain.terrain_types]
    return (root[:, 1] - env.scene.env_origins[:, 1]).abs() > width / 2 + margin


def stair_goal_reached(env):
    """Finish training episodes safely on the final landing, as a timeout.

    Feet must clear the final riser, the body must be upright and at standing
    height, and the goal must be reached inside the 1.2 m corridor. Held-out
    evaluation omits this term so its stricter dwell test remains independent.
    """
    columns = _column_geometry_tensors(env)
    terrain_type = env.scene.terrain.terrain_types
    robot = env.scene["robot"]
    root = _tensor(robot.data.root_pos_w)
    relative = root - env.scene.env_origins
    progress = relative[:, 0] >= columns["goal_x"][terrain_type]
    corridor = relative[:, 1].abs() <= columns["width"][terrain_type] / 2
    upright = _tensor(robot.data.projected_gravity_b)[:, 2] < -0.8
    if not hasattr(env, "_him_stair_foot_ids"):
        foot_ids, _ = robot.find_bodies(".*_foot")
        if len(foot_ids) != 4:
            raise ValueError("Go2 stair success requires exactly four foot bodies")
        env._him_stair_foot_ids = torch.as_tensor(foot_ids, device=env.device, dtype=torch.long)
    feet = _tensor(robot.data.body_pos_w)[:, env._him_stair_foot_ids]
    feet_clear = ((feet[:, :, 0] - env.scene.env_origins[:, None, 0]) >=
                  columns["last_riser_x"][terrain_type, None] + 0.1).all(dim=1)
    # The close scanner is centred above the body, so after goal_x all rays
    # land on the final platform. Invalid ray hits cannot count as success.
    hits = _tensor(env.scene["base_height_scanner"].data.ray_hits_w)[:, :, 2]
    valid = torch.isfinite(hits).all(dim=1)
    clearance = root[:, 2] - hits.median(dim=1).values
    standing = valid & (clearance >= 0.18) & (clearance <= 0.60)
    return progress & corridor & upright & feet_clear & standing


def stair_terrain_curriculum(env, env_ids, required_progress=0.8):
    """Promote completed flights; demote falls/early timeouts, using directed progress.

    Stock distance curriculum could reward walking behind/beside these stairs.
    This version also forbids promoting a genuine termination on the goal step.
    """
    ids = torch.as_tensor(env_ids, device=env.device, dtype=torch.long)
    terrain = env.scene.terrain
    goal_x = _column_geometry_tensors(env)["goal_x"]
    root = env.scene["robot"].data.root_pos_w.torch
    progress = root[ids, 0] - env.scene.env_origins[ids, 0]
    target = goal_x[terrain.terrain_types[ids]]
    terminated = env.termination_manager.terminated[ids]
    move_up = (progress >= target) & ~terminated
    move_down = ~move_up & (terminated | (progress < target * required_progress))
    terrain.update_env_origins(ids, move_up, move_down)
    return terrain.terrain_levels.float().mean()


def configure_stair_terrain(cfg, stage="easy", *, spec=None, num_rows=10, num_cols=24, seed=1):
    """Apply geometry/sensors/curriculum to an existing pinned Lab Go2 rough cfg.

    The caller selects rewards and commands. This function retains the robot,
    simulator backend, actions and policy observations, and returns a manifest.
    The existing height scanner must be present; instantiate the rough task cfg.
    """
    if getattr(cfg.scene, "height_scanner", None) is None:
        raise ValueError("Stair configuration requires the Go2 rough cfg height_scanner")
    generator = build_stair_generator(stage, spec=spec, num_rows=num_rows, num_cols=num_cols, seed=seed)
    cfg.scene.terrain.terrain_type = "generator"
    cfg.scene.terrain.terrain_generator = generator
    cfg.scene.terrain.max_init_terrain_level = 0
    cfg.scene.height_scanner.pattern_cfg = patterns.GridPatternCfg(resolution=0.1, size=[1.6, 1.0])
    cfg.scene.height_scanner.mesh_prim_paths = ["/World/ground"]
    cfg.scene.base_height_scanner = cfg.scene.height_scanner.copy()
    cfg.scene.base_height_scanner.pattern_cfg = patterns.GridPatternCfg(resolution=0.05, size=[0.3, 0.4])
    cfg.scene.base_height_scanner.update_period = cfg.sim.dt * cfg.decimation
    cfg.terminations.stair_corridor_exit = TerminationTermCfg(func=stair_corridor_exit)
    if spec is None:
        cfg.curriculum.terrain_levels = CurriculumTermCfg(func=stair_terrain_curriculum)
        cfg.terminations.stair_goal_reached = TerminationTermCfg(func=stair_goal_reached, time_out=True)
    else:
        cfg.curriculum.terrain_levels = None
        cfg.terminations.stair_goal_reached = None
    configs = _column_stair_cfgs(generator)
    manifest = {"stage": stage, "seed": seed, "heldout": spec is not None,
                "num_rows": generator.num_rows, "num_cols": generator.num_cols,
                "terrain_size": list(generator.size), "num_steps": configs[0].num_steps,
                "width": configs[0].width, "landing_length": configs[0].landing_length,
                "convert_to_heightfield": False,
                "geometry_reference": "relative to scene.env_origins; positive x travel",
                "height_scanner_samples": 187,
                "variants": [{"direction": term.direction, "step_height_range": list(term.step_height_range),
                              "step_depth": term.step_depth, "nosing": term.nosing,
                              "num_steps": term.num_steps, "width": term.width,
                              "landing_length": term.landing_length} for term in configs]}
    if spec is not None:
        term = configs[0]
        manifest["geometry"] = stair_metadata(term.step_height_range[0], term.step_depth, term.nosing, term.direction,
                                              term.num_steps, term.width, term.landing_length,
                                              generator.size, term.nosing_thickness)
    return manifest


def configure_stair_batch(cfg, specs, *, seed=1):
    """Install fixed held-out flights in deterministic columns in one simulator.

    ``specs`` is an ordered sequence of the same dicts accepted by ``spec`` in
    :func:`configure_stair_terrain`. Each column has one fixed geometry; all
    heights remain fixed despite using the generator's curriculum layout to
    obtain deterministic columns. Runtime curriculum and successful-episode
    timeouts are both disabled. Isaac Lab groups environment ids by column:
    use ``scene.terrain.terrain_types`` to choose metadata for each robot.

    Prefer ``num_envs`` divisible by the number of specs. Equal groups then
    provide equal trial counts without rebuilding physics for every flight.
    """
    specs = list(specs)
    if not specs:
        raise ValueError("Stair batch must contain at least one specification")
    # Reuse the single-flight configuration to keep sensors/terminations
    # identical, then replace only the terrain generator with the full batch.
    manifest = configure_stair_terrain(cfg, spec=specs[0], num_rows=1, num_cols=1, seed=seed)
    variants, columns, requested_sizes = {}, [], []
    for index, spec in enumerate(specs):
        term, size = _fixed_stair_spec(spec)
        requested_sizes.append(size)
        name = str(spec.get("name", f"case_{index:02d}"))
        variants[f"column_{index:02d}"] = term
        columns.append({"column": index, "name": name})
    common_size = tuple(max(size[axis] for size in requested_sizes) for axis in range(2))
    for column, term in zip(columns, variants.values()):
        column["geometry"] = stair_metadata(term.step_height_range[0], term.step_depth, term.nosing,
                                             term.direction, term.num_steps, term.width, term.landing_length,
                                             common_size, term.nosing_thickness)
    generator = TerrainGeneratorCfg(seed=seed, size=common_size, num_rows=1, num_cols=len(specs),
                                    curriculum=True, sub_terrains=variants, border_width=4.0,
                                    difficulty_range=(0.0, 1.0), use_cache=False, color_scheme="height")
    cfg.scene.terrain.terrain_generator = generator
    cfg.scene.terrain.max_init_terrain_level = 0
    cfg.curriculum.terrain_levels = None
    cfg.terminations.stair_goal_reached = None
    manifest.pop("geometry", None)
    manifest.update({"stage": "heldout_batch", "batch": True, "num_rows": 1, "num_cols": len(specs),
                     "terrain_size": list(common_size),
                     "columns": columns,
                     "geometry": [column["geometry"] for column in columns],
                     "variant_names": [column["name"] for column in columns],
                     "variants": [{"direction": term.direction, "step_height_range": list(term.step_height_range),
                                   "step_depth": term.step_depth, "nosing": term.nosing,
                                   "num_steps": term.num_steps, "width": term.width,
                                   "landing_length": term.landing_length}
                                  for term in variants.values()],
                     "environment_column_mapping": "scene.terrain.terrain_types",
                     "generator_curriculum_layout": True, "runtime_curriculum": False})
    for field in ("num_steps", "width", "landing_length"):
        values = {getattr(term, field) for term in variants.values()}
        manifest[field] = next(iter(values)) if len(values) == 1 else None
    return manifest


def heldout_stair_specs():
    """Named exact cases, distinct from arbitrary easy random-curriculum draws."""
    specs = [
        {"name": f"{direction}_{name}", "direction": direction, "step_height": height,
         "step_depth": depth, "nosing": nose}
        for direction in ("asc", "desc")
        for name, height, depth, nose in (
            ("a1_paper_16cm_27cm", 0.16, 0.27, 0.0),
            ("aliengo_paper_17cm_25cm", 0.17, 0.25, 0.0),
            ("tall_20cm_wide_40cm", 0.20, 0.40, 0.0),
            ("tall_23cm_narrow_20cm", 0.23, 0.20, 0.0),
            ("lip_1cm_16cm_27cm", 0.16, 0.27, 0.01),
            ("lip_2cm_17cm_25cm", 0.17, 0.25, 0.02),
            ("lip_3cm_16cm_27cm", 0.16, 0.27, 0.03),
        )
    ]
    specs.extend({"name": f"{direction}_long{count}_17cm_{int(depth * 100)}cm",
                  "direction": direction, "step_height": .17, "step_depth": depth,
                  "num_steps": count, "nosing": 0.0}
                 for direction in ("asc", "desc") for count, depth in ((10, .25), (12, .25), (12, .40)))
    return specs
