"""Optional, documented Go2 stair domain randomization using pinned public APIs.

Apply after terrain/reward configuration and before simulator launch. These
presets do not alter the actor observations or replace the Go2 DC motor model.
The deployment profile adds a DC motor subclass with physics-step command
delay and reset-sampled strength. Basic/robust keep the original motor unchanged.
"""

from __future__ import annotations

import copy


def _domain_attempt(read):
    """Keep a failed read visible without hiding independent measurements."""
    try:
        result = read()
        return {"status": "available", **result}
    except Exception as error:
        return {"status": "unavailable", "reason": f"{type(error).__name__}: {error}"}


def _domain_tensor(value):
    import torch

    tensor = getattr(value, "torch", value)
    if not isinstance(tensor, torch.Tensor):
        raise TypeError(f"Expected a Torch tensor or Lab ProxyArray, got {type(value).__name__}")
    return tensor.detach()


def _domain_summary(value):
    """Small JSON-safe summaries; never edit the input tensor or use RNG."""
    import torch

    tensor = _domain_tensor(value).to(device="cpu", dtype=torch.float64)
    if not tensor.numel():
        raise ValueError("The selected tensor is empty")
    finite = torch.isfinite(tensor)
    valid = tensor[finite]
    samples = tensor[:3] if tensor.ndim else tensor
    # Avoid emitting NaN/Infinity, which are not valid JSON numbers.
    samples = samples.tolist()

    def safe(item):
        import math

        return [safe(v) for v in item] if isinstance(item, list) else (item if math.isfinite(item) else None)

    return {"shape": list(tensor.shape), "finite": bool(finite.all()),
            "nonfinite_count": int((~finite).sum()),
            "min": float(valid.min()) if valid.numel() else None,
            "max": float(valid.max()) if valid.numel() else None,
            "mean": float(valid.mean()) if valid.numel() else None,
            "std": float(valid.std(unbiased=False)) if valid.numel() else None,
            "samples_first_envs": safe(samples)}


def _domain_event(env, name):
    term = env.event_manager.get_term_cfg(name)
    if isinstance(term.func, (str, type)):
        raise RuntimeError(f"Event {name!r} has not been instantiated")
    return term


def _domain_base_property(env, robot, body_ids, field, default_field):
    actual = _domain_tensor(getattr(robot.data, field))[:, body_ids]
    result = {"source": f"robot.data.{field}.torch", "observed": _domain_summary(actual)}

    def baseline():
        event = _domain_event(env, "add_base_mass")
        value = getattr(event.func, default_field, None)
        if value is None:
            raise RuntimeError(f"add_base_mass has no cached {default_field}; capture after startup")
        default = _domain_tensor(value)[:, body_ids]
        return {"source": f"add_base_mass.func.{default_field}", "values": _domain_summary(default)}

    result["default"] = _domain_attempt(baseline)
    if field == "body_mass":
        def mass_ratio():
            event = _domain_event(env, "add_base_mass")
            default = _domain_tensor(event.func.default_mass)[:, body_ids]
            if (default <= 0).any():
                raise ValueError("The cached default mass is not positive")
            return {"values": _domain_summary(actual / default),
                    "operation": event.params["operation"],
                    "distribution": event.params.get("distribution", "uniform"),
                    "distribution_parameters": list(event.params["mass_distribution_params"])}

        result["observed_to_default_ratio"] = _domain_attempt(mass_ratio)
    else:
        def inertia_check():
            event = _domain_event(env, "add_base_mass")
            default_mass = _domain_tensor(event.func.default_mass)[:, body_ids]
            default_inertia = _domain_tensor(event.func.default_inertia)[:, body_ids]
            mass = _domain_tensor(robot.data.body_mass)[:, body_ids]
            if (default_mass <= 0).any():
                raise ValueError("The cached default mass is not positive")
            expected = default_inertia * (mass / default_mass)[..., None]
            return {"recompute_inertia": event.params.get("recompute_inertia", True),
                    "max_abs_error_from_default_times_mass_ratio_kg_m2": float((actual - expected).abs().max())}

        result["mass_scaled_inertia_check"] = _domain_attempt(inertia_check)
    return result


def _domain_base_com(env, robot, body_ids):
    actual = _domain_tensor(robot.data.body_com_pose_b)[:, body_ids]
    result = {"source": "robot.data.body_com_pose_b.torch",
              "position_m": _domain_summary(actual[..., :3]),
              "quaternion_xyzw": _domain_summary(actual[..., 3:])}

    def baseline_and_offset():
        event = _domain_event(env, "base_com")
        if event.func.default_com is None:
            raise RuntimeError("base_com has not cached its original COM; capture after startup")
        default = _domain_tensor(event.func.default_com)[:, body_ids]
        offset = actual[..., :3] - default[..., :3]
        offset_cpu = offset.to(device="cpu")
        return {"source": "base_com.func.default_com", "position_m": _domain_summary(default[..., :3]),
                "offset_m": _domain_summary(offset),
                "offset_min_xyz_m": offset_cpu.amin(dim=(0, 1)).tolist(),
                "offset_max_xyz_m": offset_cpu.amax(dim=(0, 1)).tolist(),
                "configured_offset_ranges_m": event.params["com_range"],
                "max_abs_quaternion_change": float((actual[..., 3:] - default[..., 3:]).abs().max())}

    result["default_and_offset"] = _domain_attempt(baseline_and_offset)
    return result


def _domain_actuator_gains(env, robot):
    from isaaclab.actuators import IdealPDActuator
    from isaaclab.actuators.actuator_base import resolve_joint_parameter

    result = {}
    for name, actuator in robot.actuators.items():
        def read(actuator=actuator, name=name):
            if not isinstance(actuator, IdealPDActuator):
                raise TypeError(f"{type(actuator).__name__} is not a Lab IdealPD/DCMotor actuator")
            gains = {"actuator_type": type(actuator).__name__, "joint_names": list(actuator.joint_names)}
            if hasattr(actuator, "drive_strength"):
                gains["drive_strength"] = _domain_summary(actuator.drive_strength)
                gains["position_delay_physics_steps"] = _domain_summary(actuator.positions_delay_buffer.time_lags)
                gains["position_delay_seconds"] = _domain_summary(actuator.positions_delay_buffer.time_lags * env.physics_dt)
            for property_name in ("stiffness", "damping"):
                def read_gain(property_name=property_name):
                    actual = _domain_tensor(getattr(actuator, property_name))

                    def baseline():
                        try:
                            event = _domain_event(env, "him_actuator_gains")
                        except ValueError:
                            # This is a configured reference, not a fabricated startup snapshot.
                            value = getattr(actuator.cfg, property_name)
                            if value is None:
                                raise RuntimeError(f"No gain event baseline or explicit actuator.cfg.{property_name}")
                            default = resolve_joint_parameter(value, None, actuator.joint_names,
                                                              actual.shape[0], actual.device)
                            source = f"actuator.cfg.{property_name} (configured reference)"
                        else:
                            default = getattr(event.func, f"default_actuator_{property_name}")[name]
                            source = f"him_actuator_gains.func.default_actuator_{property_name}[{name!r}]"
                        default = _domain_tensor(default)
                        return {"source": source, "values": _domain_summary(default),
                                "observed_to_default_ratio": _domain_summary(actual / default)
                                if (default != 0).all() else {"status": "unavailable", "reason": "Default gains include zero"}}

                    return {"source": f"robot.actuators[{name!r}].{property_name}",
                            "observed": _domain_summary(actual), "default": _domain_attempt(baseline)}

                gains[property_name] = _domain_attempt(read_gain)
            return gains

        result[name] = _domain_attempt(read)
    if not result:
        raise RuntimeError("The robot has no actuator groups")
    return {"groups": result,
            "note": "Explicit DCMotor gains live on the actuator; zero solver joint_stiffness is not a PD readback"}


def _domain_foot_material(env, robot):
    import torch
    import warp as wp

    foot_ids = [i for i, name in enumerate(robot.body_names) if name.endswith("_foot")]
    if not foot_ids:
        raise ValueError("No bodies ending in '_foot' were found")
    backend_ids = [int(i) for i in robot.map_body_ids_to_backend(foot_ids)]
    event = None
    try:
        event = _domain_event(env, "physics_material")
    except ValueError:
        pass  # Actual materials are still readable without a randomization event.
    impl = getattr(event.func, "_impl", None) if event is not None else None
    counts = getattr(impl, "num_shapes_per_body", None)
    if counts is None:
        counts = [robot._physics_sim_view.create_rigid_body_view(path).max_shapes
                  for path in robot.root_view.link_paths[0]]
    if sum(counts) != robot.root_view.max_shapes:
        raise ValueError(f"Body shape counts sum to {sum(counts)}, root view has {robot.root_view.max_shapes}")
    shape_ids = [shape for body in backend_ids
                 for shape in range(sum(counts[:body]), sum(counts[:body + 1]))]
    if not shape_ids:
        raise ValueError("The foot bodies have no collision shapes")
    materials = wp.to_torch(robot.root_view.get_material_properties())[:, shape_ids].detach().cpu()
    result = {"source": "wp.to_torch(robot.root_view.get_material_properties())",
              "body_names": [robot.body_names[i] for i in foot_ids],
              "public_body_ids": foot_ids, "backend_body_ids": backend_ids, "shape_ids": shape_ids,
              "static_friction": _domain_summary(materials[..., 0]),
              "dynamic_friction": _domain_summary(materials[..., 1]),
              "restitution": _domain_summary(materials[..., 2]),
              "dynamic_le_static": bool((materials[..., 1] <= materials[..., 0]).all()),
              "unique_material_count": int(torch.unique(materials.reshape(-1, 3), dim=0).shape[0]),
              "default": {"status": "unavailable",
                          "reason": "The PhysX material event does not retain pre-randomization materials"}}
    if event is not None:
        result["configured_ranges"] = {key: value for key, value in event.params.items() if key != "asset_cfg"}
    else:
        result["configured_ranges"] = {"status": "unavailable", "reason": "No physics_material event"}

    def bucket_pool():
        if impl is None or not hasattr(impl, "material_buckets"):
            raise RuntimeError("No cached PhysX material buckets")
        buckets = _domain_tensor(impl.material_buckets).cpu()
        # Equality is appropriate: the backend stores these same float32 triples.
        unique = torch.unique(materials.reshape(-1, 3), dim=0)
        matches = (unique[:, None] == buckets[None]).all(dim=-1).any(dim=-1)
        return {"source": "physics_material.func._impl.material_buckets",
                "values": _domain_summary(buckets), "all_observed_materials_in_bucket_pool": bool(matches.all())}

    result["bucket_pool"] = _domain_attempt(bucket_pool)
    return result


def _terrain_authored_attribute(prim, name, numeric=False):
    """Read composed authored USD values, never replace missing values with cfg."""
    import math

    attribute = prim.GetAttribute(name)
    if not attribute or not attribute.HasAuthoredValueOpinion():
        raise RuntimeError(f"No authored USD value for {name}; backend/schema fallback is not verified")
    value = attribute.Get()
    if value is None:
        raise RuntimeError(f"Authored USD value for {name} is blocked or unresolved")
    if numeric:
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f"Non-finite USD value for {name}")
    else:
        value = str(value)
    return {"value": value, "attribute": name, "has_authored_value_opinion": True,
            "source": "composed authored USD attribute, not solver effective contact coefficient"}


def _domain_terrain_material(env):
    """Resolve real terrain mesh physics bindings from this env's existing USD stage."""
    from pxr import Usd, UsdGeom, UsdPhysics, UsdShade

    terrain = getattr(env.scene, "terrain", None)
    if terrain is None:
        raise RuntimeError("The environment has no scene.terrain")
    prim_path = getattr(getattr(terrain, "cfg", None), "prim_path", None)
    if not prim_path:
        raise RuntimeError("scene.terrain.cfg.prim_path is unavailable")
    stage = getattr(getattr(env, "sim", None), "stage", None)
    if stage is None:
        raise RuntimeError("env.sim.stage is unavailable; no alternate stage was created or attached")
    root = stage.GetPrimAtPath(prim_path)
    if not root.IsValid():
        raise ValueError(f"Terrain USD prim {prim_path!r} is absent from env.sim.stage")
    meshes = [prim for prim in Usd.PrimRange(root)
              if prim.IsA(UsdGeom.Mesh) and prim.HasAPI(UsdPhysics.CollisionAPI)]
    if not meshes:
        raise RuntimeError(f"No USD collision meshes under terrain prim {prim_path!r}")

    def bound_material(prim):
        material, relationship = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial(materialPurpose="physics")
        if not material or not material.GetPrim().IsValid():
            raise RuntimeError(f"No resolved physics-purpose material binding for {prim.GetPath()}")
        material_prim = material.GetPrim()
        if not material_prim.HasAPI(UsdPhysics.MaterialAPI):
            raise RuntimeError(f"Bound USD material {material.GetPath()} has no PhysicsMaterialAPI")
        fields = {}
        for key, name, numeric in (
            ("static_friction", "physics:staticFriction", True),
            ("dynamic_friction", "physics:dynamicFriction", True),
            ("restitution", "physics:restitution", True),
            ("friction_combine_mode", "physxMaterial:frictionCombineMode", False),
            ("restitution_combine_mode", "physxMaterial:restitutionCombineMode", False),
            ("damping_combine_mode", "physxMaterial:dampingCombineMode", False),
        ):
            fields[key] = _domain_attempt(lambda name=name, numeric=numeric:
                                          _terrain_authored_attribute(material_prim, name, numeric))
        return {"material_prim_path": str(material.GetPath()),
                "binding_relationship_path": str(relationship.GetPath()) if relationship else None,
                "binding_relationship_targets": [str(path) for path in relationship.GetTargets()] if relationship else [],
                "material_applied_schemas": list(material_prim.GetAppliedSchemas()),
                "attributes": fields}

    def mesh_report(prim):
        subsets = UsdGeom.Subset.GetAllGeomSubsets(UsdGeom.Imageable(prim))
        return {"mesh_prim_path": str(prim.GetPath()),
                "collision_enabled": UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get(),
                "physics_binding": _domain_attempt(lambda: bound_material(prim)),
                "geometry_subsets": [{"subset_prim_path": str(subset.GetPath()),
                    "physics_binding": _domain_attempt(lambda subset=subset: bound_material(subset.GetPrim()))}
                    for subset in subsets]}

    configured = getattr(terrain.cfg, "physics_material", None)
    return {"source": "env.sim.stage; UsdShade.MaterialBindingAPI.ComputeBoundMaterial(materialPurpose='physics')",
            "scope": "actual composed terrain USD mesh bindings and authored material attributes; not solver contact-pair coefficients",
            "stage_root_layer_identifier": str(stage.GetRootLayer().identifier),
            "terrain_prim_path": str(prim_path),
            "imported_terrain_prim_paths": [str(path) for path in getattr(terrain, "terrain_prim_paths", [])],
            "collision_mesh_count": len(meshes), "collision_meshes": [mesh_report(prim) for prim in meshes],
            "configured_reference": {"source": "scene.terrain.cfg.physics_material; configuration only",
                "values": {name: getattr(configured, name, None) for name in (
                    "static_friction", "dynamic_friction", "restitution", "friction_combine_mode", "restitution_combine_mode")}},
            "solver_effective_contact_coefficients": {"status": "unavailable",
                "reason": "No solver contact-pair material readback is performed; effective coefficients also depend on the other shape, combine-mode priority and backend state"}}


def capture_domain_parameters(env):
    """Read current Go2 physical parameters after reset, without modifying them.

    The JSON-safe report separates live values, cached original values and
    configured references. It works with ``none`` too, and labels missing reads
    (including absent default caches) ``unavailable`` with a reason. It neither
    invokes events/setters nor consumes RNG; Lab getters may refresh read caches.
    This implementation targets the pinned PhysX backend and explicit Go2 PD.
    """
    try:
        robot = env.scene["robot"]
        base_ids = [i for i, name in enumerate(robot.body_names) if name == "base"]
        if not base_ids:
            raise ValueError("No body named 'base' was found")
    except Exception as error:
        return {"status": "unavailable", "reason": f"{type(error).__name__}: {error}"}
    return {"status": "captured", "scope": "current physical parameters; not a robustness validation",
            "base_body_names": [robot.body_names[i] for i in base_ids], "base_body_ids": base_ids,
            "base_mass_kg": _domain_attempt(lambda: _domain_base_property(
                env, robot, base_ids, "body_mass", "default_mass")),
            "base_inertia_kg_m2": _domain_attempt(lambda: _domain_base_property(
                env, robot, base_ids, "body_inertia", "default_inertia")),
            "base_com": _domain_attempt(lambda: _domain_base_com(env, robot, base_ids)),
            "actuator_pd": _domain_attempt(lambda: _domain_actuator_gains(env, robot)),
            "foot_material": _domain_attempt(lambda: _domain_foot_material(env, robot)),
            "terrain_material": _domain_attempt(lambda: _domain_terrain_material(env))}


def _require_dc_actuators(cfg):
    from isaaclab.actuators import DCMotorCfg

    actuators = cfg.scene.robot.actuators
    if not actuators or any(not isinstance(term, DCMotorCfg) for term in actuators.values()):
        raise ValueError("Stair randomization requires the existing Go2 DCMotorCfg actuators")
    if getattr(cfg.sim, "use_newton_actuators", False):
        raise ValueError("Stair randomization is validated for Lab-executed DC motors, not native Newton")
    return actuators


def _mass_manifest(cfg):
    term = getattr(cfg.events, "add_base_mass", None)
    if term is None:
        return {"enabled": False, "preserved": True}
    return {"enabled": True, "preserved": True, "mode": term.mode,
            "parameters": {key: value for key, value in term.params.items()
                           if key != "asset_cfg"}}


def configure_stair_randomization(cfg, profile="basic"):
    """Configure optional physical variability; return provenance.

    ``basic`` varies foot friction and a small base COM offset. ``robust`` adds
    larger COM offsets and independent +/-10% PD gains. The existing base mass
    distribution is retained exactly, including its inertia recomputation flag.
    ``deployment`` additionally randomizes motor strength and 0–10 ms position
    command latency without changing HIM. ``none`` leaves events unchanged.

    PhysX contact materials are bucketed at startup, and gains are resampled at
    reset from their original defaults through the pinned supported API. This
    avoids compounding gain changes over repeated resets or material-limit use.
    """
    if profile not in ("none", "basic", "robust", "deployment"):
        raise ValueError("domain profile must be none, basic, robust, or deployment")
    if profile == "none":
        return {"profile": "none", "events_unchanged": True}
    _require_dc_actuators(cfg)
    from isaaclab.managers import EventTermCfg, SceneEntityCfg

    mdp = "isaaclab.envs.mdp:"
    cfg.events.physics_material = EventTermCfg(
        func=mdp + "randomize_rigid_body_material", mode="startup", params={
            "asset_cfg": SceneEntityCfg("robot", body_names=".*_foot"),
            "static_friction_range": (0.6, 1.1),
            "dynamic_friction_range": (0.5, 1.0),
            "restitution_range": (0.0, 0.0),
            "num_buckets": 64,
            "make_consistent": True,
        },
    )
    com_limits = (0.01, 0.01, 0.005) if profile == "basic" else (0.03, 0.02, 0.01)
    com_range = {axis: (-limit, limit) for axis, limit in zip(("x", "y", "z"), com_limits)}
    cfg.events.base_com = EventTermCfg(
        func=mdp + "randomize_rigid_body_com", mode="startup", params={
            "asset_cfg": SceneEntityCfg("robot", body_names="base"),
            "com_range": com_range,
        },
    )
    cfg.events.him_actuator_gains = None
    if profile in ("robust", "deployment"):
        cfg.events.him_actuator_gains = EventTermCfg(
            func=mdp + "randomize_actuator_gains", mode="reset", params={
                "asset_cfg": SceneEntityCfg("robot"),
                "stiffness_distribution_params": (0.9, 1.1),
                "damping_distribution_params": (0.9, 1.1),
                "operation": "scale",
                "distribution": "uniform",
            },
        )
    if profile == "deployment":
        from deployment_motor import deployment_config
        cfg.scene.robot.actuators = {name: deployment_config(motor) for name, motor in cfg.scene.robot.actuators.items()}
    terrain_material = cfg.scene.terrain.physics_material
    return {
        "profile": profile,
        "foot_material": {"mode": "startup", "static_friction_range": [0.6, 1.1],
                          "dynamic_friction_range": [0.5, 1.0],
                          "dynamic_le_static": True, "restitution": 0.0, "buckets": 64},
        "terrain_material": {name: getattr(terrain_material, name, None) for name in (
            "static_friction", "dynamic_friction", "friction_combine_mode")},
        "base_com_range_m": com_range,
        "base_mass": _mass_manifest(cfg),
        "pd_gain_scale": [0.9, 1.1] if profile in ("robust", "deployment") else [1.0, 1.0],
        "pd_gain_mode": "reset from fixed defaults" if profile in ("robust", "deployment") else "unchanged",
        "actuator_model": "DCMotor with reset-randomized strength/position latency" if profile == "deployment" else "existing DCMotor preserved",
        "motor_strength_randomization": [0.9,1.1] if profile == "deployment" else False,
        "action_delay_randomization": {"physics_substeps": [0,2], "seconds": [0,.01], "mode": "reset"} if profile == "deployment" else False,
        "remaining_deployment_gaps": [
            "No motor-strength scaling: public gain randomization is not torque-envelope randomization",
            "No 0-15ms action delay: requires physics-substep command buffering while preserving DC curve",
        ],
    }


def configure_conservative_calf_limits(cfg, mode="evaluate"):
    """Evaluation-only alternative knee ratio from the local Unitree URDF.

    The old calf pair 35.55 Nm / 20.07 rad/s reduces peak joint torque and raises
    rated joint speed relative to the USD pair 45.43 / 15.70. Their mechanical
    power products differ by only 0.033%. This is a gearbox sensitivity test,
    not evidence that the user's EDU has either exact knee ratio.
    """
    if mode not in ("evaluate", "play"):
        raise ValueError("Conservative calf limits are evaluation/play only")
    actuators = _require_dc_actuators(cfg)
    if list(actuators) != ["base_legs"]:
        raise ValueError("Conservative calf limits require the pinned Go2 base_legs actuator group")
    actuator = copy.deepcopy(actuators["base_legs"])
    # The pinned Go2 group covers all 12 joints. Each dictionary explicitly
    # preserves hip/thigh settings rather than assigning a blanket scalar.
    expected = (".*_hip_joint", ".*_thigh_joint", ".*_calf_joint")
    before = {}
    for name, calf in (("actuator_effort_limit", 35.55), ("saturation_effort", 35.55),
                       ("actuator_velocity_limit", 20.07)):
        value = getattr(actuator, name)
        if not isinstance(value, dict) or set(value) != set(expected):
            raise ValueError(f"Expected pinned Go2 joint-specific {name}")
        before[name] = dict(value)
        replacement = dict(value)
        replacement[".*_calf_joint"] = calf
        setattr(actuator, name, replacement)
    # Rated model speed alone is not a solver override in Lab 3; keep both
    # explicit so the original USD calf hard limit does not confound this test.
    actuator.joint_velocity_limit = dict(actuator.actuator_velocity_limit)
    actuator.joint_effort_limit = dict(actuator.actuator_effort_limit)
    cfg.scene.robot.actuators = dict(actuators, base_legs=actuator)
    return {
        "profile": "legacy_urdf_calf_curve", "scope": "evaluation-only gearbox sensitivity",
        "source": "local Unitree go2.urdf calf limits",
        "before": before,
        "calf_effort_limit_Nm": 35.55, "calf_velocity_limit_rad_s": 20.07,
        "joint_and_actuator_limits_consistent": True,
        "previous_motor_power_product_W": 45.43 * 15.70,
        "motor_power_product_W": 35.55 * 20.07,
        "robot_and_pd_gains": "unchanged",
    }
