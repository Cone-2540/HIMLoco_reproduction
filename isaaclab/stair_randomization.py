"""Optional, documented Go2 stair domain randomization using pinned public APIs.

Apply after terrain/reward configuration and before simulator launch. These
presets do not alter the actor observations or replace the Go2 DC motor model.
Actuation delay and motor-strength scaling are deliberately recorded as absent:
neither is faithfully reproduced by merely changing a generic PD limit.
"""

from __future__ import annotations

import copy


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
    """Configure optional basic/robust physical variability; return provenance.

    ``basic`` varies foot friction and a small base COM offset. ``robust`` adds
    larger COM offsets and independent +/-10% PD gains. The existing base mass
    distribution is retained exactly, including its inertia recomputation flag.
    ``none`` leaves all event configuration unchanged.

    PhysX contact materials are bucketed at startup, and gains are resampled at
    reset from their original defaults through the pinned supported API. This
    avoids compounding gain changes over repeated resets or material-limit use.
    """
    if profile not in ("none", "basic", "robust"):
        raise ValueError("domain profile must be none, basic, or robust")
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
    if profile == "robust":
        cfg.events.him_actuator_gains = EventTermCfg(
            func=mdp + "randomize_actuator_gains", mode="reset", params={
                "asset_cfg": SceneEntityCfg("robot"),
                "stiffness_distribution_params": (0.9, 1.1),
                "damping_distribution_params": (0.9, 1.1),
                "operation": "scale",
                "distribution": "uniform",
            },
        )
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
        "pd_gain_scale": [0.9, 1.1] if profile == "robust" else [1.0, 1.0],
        "pd_gain_mode": "reset from fixed defaults" if profile == "robust" else "unchanged",
        "actuator_model": "existing DCMotor preserved",
        "motor_strength_randomization": False,
        "action_delay_randomization": False,
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
