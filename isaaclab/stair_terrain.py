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
from isaaclab.terrains.trimesh.mesh_terrains_cfg import MeshPlaneTerrainCfg
from isaaclab.utils import configclass


STAGES = {
    "bootstrap": {"height_range": (0.025, 0.08), "depths": (0.30, 0.36), "nosings": (0.0,)},
    "easy": {"height_range": (0.05, 0.12), "depths": (0.28, 0.30, 0.32, 0.36), "nosings": (0.0,)},
    "standard": {"height_range": (0.05, 0.17), "depths": (0.20, 0.25, 0.27, 0.30, 0.35, 0.40), "nosings": (0.0,)},
    "hard": {"height_range": (0.08, 0.23), "depths": (0.20, 0.25, 0.27, 0.30, 0.35, 0.40), "nosings": (0.0, 0.01, 0.02, 0.03)},
    # Keep the published stair dimensions as exact training columns, while the
    # other columns interpolate only a moderate six-riser curriculum. This is
    # a new distribution; it does not revise any old stage or held-out case.
    "paper_mixed": {"height_range": (0.11, 0.20), "depths": (0.25, 0.27, 0.30, 0.35),
                    "nosings": (0.0, 0.01, 0.02),
                    "fixed_paper_geometries": ((0.16, 0.27), (0.17, 0.25))},
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


def build_stair_generator(stage="easy", *, spec=None, num_rows=10, num_cols=24, seed=1,
                          flat_fraction=0.0):
    """Training uses ascending/descending variants; spec selects a fixed heldout flight.

    ``spec`` keys: step_height (or height), step_depth (or depth), nosing,
    direction, num_steps, width, landing_length. Heldout tiles expand to contain
    longer flights. Training retains six risers and default 8 m x 3 m tiles.
    Optional 25% flat replay uses actual plane meshes in contiguous columns.
    Its other columns retain every original stair variant with equal exposure.
    """
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {', '.join(STAGES)}")
    if num_rows < 1 or num_cols < 1:
        raise ValueError("Terrain grid dimensions must be positive")
    if not math.isfinite(float(flat_fraction)) or flat_fraction not in (0.0, 0.25):
        raise ValueError("flat_fraction must be 0.0 or 0.25")
    if spec is not None and flat_fraction:
        raise ValueError("Flat replay is training-only, not a held-out stair specification")
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
            for height, depth in selected.get("fixed_paper_geometries", ()):
                key = f"{direction}_paper_height_{height:.2f}_tread_{depth:.2f}"
                variants[key] = StraightStairTerrainCfg(direction=direction,
                    step_height_range=(height, height), step_depth=depth, nosing=0.0)
        curriculum = True
        # Columns must represent every type; never silently omit a tread/nosing.
        num_cols = max(num_cols, len(variants))
        if flat_fraction:
            stair_count = len(variants)
            # A multiple of this unit assigns exactly 25% flat columns and an
            # equal integer number of columns to every remaining stair type.
            unit = 4 * stair_count // math.gcd(3, stair_count)
            num_cols = unit * math.ceil(num_cols / unit)
            for term in variants.values():
                term.proportion = 0.75 / stair_count
            variants = {"flat_replay": MeshPlaneTerrainCfg(proportion=0.25,
                                                          convert_to_heightfield=False), **variants}
            # Use the same strict cumulative boundary test as Lab; fail early
            # rather than silently leave a hard geometry without a column.
            cumulative = np.cumsum([term.proportion for term in variants.values()], dtype=float)
            cumulative /= cumulative[-1]
            selected = np.searchsorted(cumulative, np.arange(num_cols) / num_cols + 0.001, side="right")
            if set(selected) != set(range(len(variants))):
                raise ValueError("Terrain columns omit a requested replay/stair variant")
    return TerrainGeneratorCfg(seed=seed, size=size, num_rows=num_rows, num_cols=num_cols,
                               curriculum=curriculum, sub_terrains=variants, border_width=4.0,
                               difficulty_range=(0.0, 1.0), use_cache=False, color_scheme="height")


def _column_stair_cfgs(generator_cfg):
    configs = list(generator_cfg.sub_terrains.values())
    cumulative = np.cumsum([term.proportion for term in configs], dtype=float)
    cumulative /= cumulative[-1]
    return [configs[int(np.searchsorted(cumulative, index / generator_cfg.num_cols + 0.001, side="right"))]
            for index in range(generator_cfg.num_cols)]


def _column_geometry_tensors(env):
    """Resolve variant geometry once; per-step manager terms only index tensors."""
    generator = env.scene.terrain.cfg.terrain_generator
    if getattr(env, "_him_stair_geometry_source", None) != id(generator):
        configs = _column_stair_cfgs(generator)
        is_stair = [isinstance(term, StraightStairTerrainCfg) for term in configs]
        if any(not stair and not isinstance(term, MeshPlaneTerrainCfg)
               for term, stair in zip(configs, is_stair)):
            raise ValueError("Stair manager terms support straight stairs and true replay planes only")
        geometries = [stair_metadata(term.step_height_range[0], term.step_depth, term.nosing,
                                    term.direction, term.num_steps, term.width, term.landing_length,
                                    generator.size, term.nosing_thickness) if stair else None
                      for term, stair in zip(configs, is_stair)]
        env._him_stair_column_geometry = {
            # Zero entries are unused tensor placeholders, not a zero-height
            # stair geometry: all stair manager decisions require is_stair.
            name: torch.tensor([geometry[name] if geometry is not None else 0.0
                                for geometry in geometries], device=env.device)
            for name in ("goal_x", "last_riser_x", "goal_platform_start_x", "width")
        }
        env._him_stair_column_geometry["is_stair"] = torch.tensor(is_stair, device=env.device, dtype=torch.bool)
        env._him_stair_column_geometry["flat_column_indices"] = tuple(
            index for index, stair in enumerate(is_stair) if not stair)
        env._him_stair_column_geometry["is_ascending"] = torch.tensor(
            [stair and term.direction == "asc" for term, stair in zip(configs, is_stair)],
            device=env.device, dtype=torch.bool)
        env._him_stair_geometry_source = id(generator)
    return env._him_stair_column_geometry


def _tensor(value):
    return value if isinstance(value, torch.Tensor) else value.torch


def flat_env_mask(env):
    """Identify replay environments from the actual Lab terrain column map."""
    return ~_column_geometry_tensors(env)["is_stair"][env.scene.terrain.terrain_types]


def flat_replay_region_exit(env, margin=1.0):
    """Truncate replay near the outer true-flat block, never count a stair fail.

    Flat columns are contiguous and cover all generator rows. Neighbouring
    true-flat tiles remain usable, but their surrounding stair columns and
    terrain border must not enter an all-direction replay episode. The inward
    margin protects the scanner and feet. Edge spawns can truncate sooner than
    the configured episode duration; this is a training timeout only.
    """
    if not math.isfinite(float(margin)) or margin < 0:
        raise ValueError("Flat replay boundary margin must be finite and nonnegative")
    columns = _column_geometry_tensors(env)
    indices = columns["flat_column_indices"]
    if not indices:
        return torch.zeros(env.scene.terrain.terrain_types.shape, device=env.device, dtype=torch.bool)
    if "flat_region_bounds" not in columns:
        if any(right - left != 1 for left, right in zip(indices, indices[1:])):
            raise ValueError("Replay plane columns must form one contiguous block")
        terrain = env.scene.terrain
        flat_columns = ~columns["is_stair"]
        origins = _tensor(terrain.terrain_origins)[:, flat_columns, :2]
        half_size = torch.as_tensor(terrain.cfg.terrain_generator.size, device=env.device) / 2
        columns["flat_region_bounds"] = torch.stack((origins.amin(dim=(0, 1)) - half_size,
                                                     origins.amax(dim=(0, 1)) + half_size))
        columns["flat_region_inner_bounds"] = {}
    # Validate/cache each margin once. No device-to-host scalar checks occur
    # in the policy-step path after the block is constructed.
    cached_bounds = columns["flat_region_inner_bounds"]
    if margin not in cached_bounds:
        bounds = columns["flat_region_bounds"]
        if bool((bounds[1] - bounds[0] <= 2 * margin).any()):
            raise ValueError("Flat replay block has no interior for the boundary margin")
        cached_bounds[margin] = torch.stack((bounds[0] + margin, bounds[1] - margin))
    bounds = cached_bounds[margin]
    root = _tensor(env.scene["robot"].data.root_pos_w)[:, :2]
    outside = ((root < bounds[0]) | (root > bounds[1])).any(dim=1)
    return outside & flat_env_mask(env)


def stair_corridor_exit(env, width=None, margin=0.05):
    """End episodes that bypass the staircase by walking beside the corridor."""
    root = env.scene["robot"].data.root_pos_w.torch
    columns = _column_geometry_tensors(env)
    terrain_types = env.scene.terrain.terrain_types
    if width is None:
        width = columns["width"][terrain_types]
    return ((root[:, 1] - env.scene.env_origins[:, 1]).abs() > width / 2 + margin) & columns["is_stair"][terrain_types]


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
    return progress & corridor & upright & feet_clear & standing & columns["is_stair"][terrain_type]


def stair_terrain_curriculum(env, env_ids, required_progress=0.8):
    """Promote completed flights; demote falls/early timeouts, using directed progress.

    Stock distance curriculum could reward walking behind/beside these stairs.
    This version also forbids promoting a genuine termination on the goal step.
    Returned fractions describe only the current training reset rows. Direction
    reset counts distinguish missing samples from zero success; they are not
    independent held-out traversal results.
    """
    ids = torch.as_tensor(env_ids, device=env.device, dtype=torch.long)
    terrain = env.scene.terrain
    geometry = _column_geometry_tensors(env)
    reset_ids = ids
    all_stairs = geometry["is_stair"][terrain.terrain_types]
    ids = ids[all_stairs[ids]]
    goal_x = geometry["goal_x"]
    root = env.scene["robot"].data.root_pos_w.torch
    progress = root[ids, 0] - env.scene.env_origins[ids, 0]
    target = goal_x[terrain.terrain_types[ids]]
    manager = env.termination_manager
    terminated = manager.terminated[ids]
    directed_goal = (progress >= target) & ~terminated
    reached_goal = (manager.get_term("stair_goal_reached")[ids] & ~terminated
                    if hasattr(manager, "get_term") else directed_goal)
    # Root progress alone cannot certify that the hind feet and body satisfy
    # the training goal. Promote only actual goals; keep the directed fallback
    # for environments without the manager term-query API.
    move_up = directed_goal & reached_goal
    move_down = ~move_up & (terminated | (progress < target * required_progress))
    if len(ids):
        terrain.update_env_origins(ids, move_up, move_down)
    ascending = geometry["is_ascending"][terrain.terrain_types]
    ended_ascending = ascending[ids]
    levels = terrain.terrain_levels.float()
    diagnostics = {"levels_mean": (levels * all_stairs).sum() / all_stairs.sum().clamp_min(1),
                   "flat_reset_count": (~all_stairs[reset_ids]).sum()}
    for direction, mask, ended_mask in (("asc", ascending, ended_ascending),
                                        ("desc", ~ascending & all_stairs, ~ended_ascending)):
        count = ended_mask.sum()
        diagnostics[f"{direction}_levels_mean"] = (levels * mask).sum() / mask.sum().clamp_min(1)
        diagnostics[f"{direction}_goal_fraction"] = (reached_goal & ended_mask).sum() / count.clamp_min(1)
        diagnostics[f"{direction}_terminated_fraction"] = (terminated & ended_mask).sum() / count.clamp_min(1)
        diagnostics[f"{direction}_reset_count"] = count
    return diagnostics


def configure_stair_terrain(cfg, stage="easy", *, spec=None, num_rows=10, num_cols=24, seed=1,
                            flat_fraction=0.0):
    """Apply geometry/sensors/curriculum to an existing pinned Lab Go2 rough cfg.

    The caller selects rewards and commands. This function retains the robot,
    simulator backend, actions and policy observations, and returns a manifest.
    The existing height scanner must be present; instantiate the rough task cfg.
    """
    if getattr(cfg.scene, "height_scanner", None) is None:
        raise ValueError("Stair configuration requires the Go2 rough cfg height_scanner")
    generator = build_stair_generator(stage, spec=spec, num_rows=num_rows, num_cols=num_cols,
                                     seed=seed, flat_fraction=flat_fraction)
    cfg.scene.terrain.terrain_type = "generator"
    cfg.scene.terrain.terrain_generator = generator
    cfg.scene.terrain.max_init_terrain_level = 0
    cfg.scene.height_scanner.pattern_cfg = patterns.GridPatternCfg(resolution=0.1, size=[1.6, 1.0])
    cfg.scene.height_scanner.mesh_prim_paths = ["/World/ground"]
    cfg.scene.base_height_scanner = cfg.scene.height_scanner.copy()
    cfg.scene.base_height_scanner.pattern_cfg = patterns.GridPatternCfg(resolution=0.05, size=[0.3, 0.4])
    cfg.scene.base_height_scanner.update_period = cfg.sim.dt * cfg.decimation
    cfg.terminations.stair_corridor_exit = TerminationTermCfg(func=stair_corridor_exit)
    cfg.terminations.flat_replay_region_exit = (TerminationTermCfg(func=flat_replay_region_exit,
                                                                 time_out=True, params={"margin": 1.0})
                                               if flat_fraction else None)
    if spec is None:
        cfg.curriculum.terrain_levels = CurriculumTermCfg(func=stair_terrain_curriculum)
        cfg.terminations.stair_goal_reached = TerminationTermCfg(func=stair_goal_reached, time_out=True)
    else:
        cfg.curriculum.terrain_levels = None
        cfg.terminations.stair_goal_reached = None
    configs = _column_stair_cfgs(generator)
    stair_configs = [term for term in configs if isinstance(term, StraightStairTerrainCfg)]
    manifest = {"stage": stage, "seed": seed, "heldout": spec is not None,
                "num_rows": generator.num_rows, "num_cols": generator.num_cols,
                "terrain_size": list(generator.size), "num_steps": stair_configs[0].num_steps,
                "width": stair_configs[0].width, "landing_length": stair_configs[0].landing_length,
                "convert_to_heightfield": False,
                "geometry_reference": "relative to scene.env_origins; positive x travel",
                "height_scanner_samples": 187,
                "curriculum_promotion": "directed goal progress and actual stair_goal_reached, excluding genuine terminations",
                "curriculum_diagnostics_scope": "current training reset rows by ascent/descent; "
                    "zero fraction with reset_count=0 means no samples; not independent held-out validation",
                "variants": [{"direction": term.direction, "step_height_range": list(term.step_height_range),
                              "step_depth": term.step_depth, "nosing": term.nosing,
                              "num_steps": term.num_steps, "width": term.width,
                              "landing_length": term.landing_length}
                             if isinstance(term, StraightStairTerrainCfg) else
                             {"kind": "flat", "collision_representation": "true plane triangle mesh",
                              "terrain_local_origin": [generator.size[0] / 2, generator.size[1] / 2, 0.0]}
                             for term in configs]}
    if flat_fraction:
        flat_columns = [index for index, term in enumerate(configs) if isinstance(term, MeshPlaneTerrainCfg)]
        manifest["flat_replay"] = {
            "requested_fraction": flat_fraction, "actual_column_fraction": len(flat_columns) / generator.num_cols,
            "flat_columns": flat_columns,
            "stair_columns": [index for index in range(generator.num_cols) if index not in flat_columns],
            "environment_column_mapping": "scene.terrain.terrain_types",
            "origin": "plane tile centre at local (size_x/2,size_y/2,0); Lab world translation applies",
            "world_block_bounds": "all row/flat-column terrain_origins min/max XY, expanded by half tile size",
            "boundary_timeout": {"term": "flat_replay_region_exit", "inward_margin_m": 1.0,
                                  "counts_as_failure": False,
                                  "scope": "training only; can shorten edge-spawn episodes"},
            "curriculum": "no promotion/demotion or stair goal/corridor for flat environments",
            "diagnostics": "flat_reset_count separate from ascent/descent reset counts",
        }
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
