"""Released HIM reward semantics, transferred to the pinned Isaac Lab Go2 task.

Only training rewards see terrain sensors. No term adds terrain to the actor.
The ``faithful`` profile uses the released Go1 weights; ``tuned`` is an explicit
small stair ablation, and ``contact`` adds only a leg-contact penalty to faithful.
``contact_force`` retains contact and adds a bounded high-force contact proxy.
``contact_slide`` retains contact and adds the existing foot XY-speed proxy.
``contact_vertical`` and ``contact_clearance`` each change only one original
reward weight from contact; both preserve the released reward formulas.
``faithful_tracking`` changes only the original XY velocity tracking weight
from faithful, without adding contact or lateral-controller terms.
``posture`` adds a support-aware soft shank-angle penalty to faithful. It does
not force a particular joint pose or add terrain/contact inputs to the actor.
``posture_contact`` keeps posture and adds the user's separate head/non-foot
contact-count penalties at -1/-0.01 with a 0.3 N normal-force threshold.
The controller, asset, and physics remain Go2/Isaac Lab,
so this profile alone does not establish an identical paper reproduction.

Isaac Lab manager types are imported inside the configuration function. This
module itself is safe to import before the simulator and in CPU-only tests.
"""

from __future__ import annotations

import math

import torch


def _tensor(value):
    """Lab 3 stores physics arrays in wrappers exposing a Torch view."""
    return getattr(value, "torch", value)


def _inverse_rotate(quaternion, vectors):
    """Rotate world vectors into body coordinates using pinned Lab 3 xyzw.

    This matches Isaac Gym's runtime quaternion order. Lab 2 used wxyz; using
    that older Lab convention here silently corrupts both pitch and yaw rewards.
    """
    q = quaternion[:, None, :3].expand_as(vectors)
    w = quaternion[:, None, 3:4]
    return vectors - 2.0 * w * torch.cross(q, vectors, dim=-1) + 2.0 * torch.cross(
        q, torch.cross(q, vectors, dim=-1), dim=-1
    )


def validate_reward_frames(env):
    """Check actual physics quaternions against the pinned math implementation.

    Run once during scene validation, outside the training loop. The pinned
    ``quat_apply_inverse`` independently handles actual xyzw identity, yaw and
    pitch, avoiding a self-consistent synthetic convention error in tests.
    """
    from isaaclab.utils.math import quat_apply_inverse

    quaternion = _tensor(env.scene["robot"].data.root_quat_w)[:8]
    if not torch.isfinite(quaternion).all():
        raise ValueError("Non-finite physics quaternion")
    torch.testing.assert_close(quaternion.norm(dim=-1), torch.ones_like(quaternion[:, 0]),
                               atol=1e-4, rtol=1e-4)
    vectors = torch.eye(3, device=quaternion.device, dtype=quaternion.dtype)
    vectors = vectors[None].expand(quaternion.shape[0], -1, -1)
    actual = _inverse_rotate(quaternion, vectors)
    expected = quat_apply_inverse(quaternion[:, None].expand(-1, 3, -1).reshape(-1, 4),
                                 vectors.reshape(-1, 3)).reshape_as(actual)
    torch.testing.assert_close(actual, expected, atol=1e-5, rtol=1e-5)
    return {"quaternion_order": "xyzw", "checked_physics_quaternions": len(quaternion),
            "root_position": "root link origin", "root_velocity": "root COM",
            "foot_position": "foot link origin", "foot_velocity": "foot COM"}


def joint_power_l1(env, asset_cfg):
    """Original sum(abs(joint velocity) * abs(applied motor torque))."""
    robot = env.scene[asset_cfg.name]
    velocity = _tensor(robot.data.joint_vel)[:, asset_cfg.joint_ids]
    effort = _tensor(robot.actuators.applied_effort)[:, asset_cfg.joint_ids]
    return (velocity.abs() * effort.abs()).sum(dim=1)


def foot_clearance_body_l2(env, asset_cfg, target_height=-0.20):
    """Original body-relative foot-height error weighted by relative XY speed.

    This does not prescribe world foot height while ascending. It also does not
    reward prolonged flight or large swings beyond the target height.

    Pinned Lab aliases body_pos_w to body_link_pos_w and body_lin_vel_w to
    body_com_lin_vel_w. Go2 foot COM is exactly its link origin, so the foot
    position/velocity pair is consistent. Root pos uses link origin and root
    velocity uses COM, matching the released Gym root-state reward semantics.
    """
    robot = env.scene[asset_cfg.name]
    root_position = _tensor(robot.data.root_pos_w)
    root_velocity = _tensor(robot.data.root_lin_vel_w)
    quaternion = _tensor(robot.data.root_quat_w)
    foot_position = _tensor(robot.data.body_pos_w)[:, asset_cfg.body_ids]
    foot_velocity = _tensor(robot.data.body_lin_vel_w)[:, asset_cfg.body_ids]
    body_position = _inverse_rotate(quaternion, foot_position - root_position[:, None, :])
    body_velocity = _inverse_rotate(quaternion, foot_velocity - root_velocity[:, None, :])
    error = (body_position[..., 2] - target_height).square()
    return (error * body_velocity[..., :2].norm(dim=-1)).sum(dim=1)


def terrain_relative_base_height_l2(
    env, asset_cfg, sensor_cfg, target_height=0.30, footprint=(0.15, 0.20)
):
    """Original close-under-base terrain-relative clearance penalty.

    The preferred sensor is the dedicated 0.30 x 0.40 m base-height grid. The
    footprint filter also makes the existing broad critic grid usable without
    allowing distant stair treads to raise or lower the clearance target. Ray
    origins are deliberately ignored: the scanner begins 20 m above the base.
    Invalid/missed rays are excluded; no valid ray contributes zero penalty and
    must be rejected separately by scene validation, rather than producing NaN.
    """
    robot = env.scene[asset_cfg.name]
    root = _tensor(robot.data.root_pos_w)
    hits = _tensor(env.scene[sensor_cfg.name].data.ray_hits_w)
    quaternion = _tensor(robot.data.root_quat_w)
    x, y, z, w = quaternion.unbind(dim=1)
    yaw = torch.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y.square() + z.square()))
    delta = hits[..., :2] - root[:, None, :2]
    local_x = yaw.cos()[:, None] * delta[..., 0] + yaw.sin()[:, None] * delta[..., 1]
    local_y = -yaw.sin()[:, None] * delta[..., 0] + yaw.cos()[:, None] * delta[..., 1]
    valid = torch.isfinite(hits).all(dim=-1)
    valid &= (local_x.abs() <= footprint[0] + 1e-4) & (local_y.abs() <= footprint[1] + 1e-4)
    count = valid.sum(dim=1)
    terrain_height = torch.where(valid, hits[..., 2], 0.0).sum(dim=1) / count.clamp_min(1)
    error = root[:, 2] - terrain_height - target_height
    return torch.where(count > 0, error.square(), 0.0)


def _step_history(env, key, value):
    """Cache one value per policy step, clearing rows at episode boundaries.

    ManagerBasedRLEnv increments episode_length_buf before reward computation,
    so a value <= 1 identifies the first reward after automatic/manual reset.
    A repeated diagnostic call within the same step never advances history.
    """
    step = int(env.common_step_counter)
    state = getattr(env, key, None)
    if state is None:
        state = {"step": -1, "value": torch.zeros_like(value), "previous": torch.zeros_like(value)}
        setattr(env, key, state)
    if state["step"] != step:
        reset = env.episode_length_buf <= 1
        state["previous"] = torch.where(reset[:, None], 0.0, state["value"])
        state["value"] = value.clone()
        state["step"] = step
    return state["previous"]


def action_smoothness_l2(env):
    """Original sum((a[t] - 2*a[t-1] + a[t-2])**2), with reset-safe history."""
    action = env.action_manager.action
    previous = env.action_manager.prev_action
    older = _step_history(env, "_him_previous_action_history", previous)
    return (action - 2.0 * previous + older).square().sum(dim=1)


def policy_joint_acceleration_l2(env, asset_cfg):
    """Original joint-velocity difference over a policy step, not a physics step."""
    current = _tensor(env.scene[asset_cfg.name].data.joint_vel)[:, asset_cfg.joint_ids]
    previous = _step_history(env, "_him_joint_velocity_history", current)
    return ((current - previous) / env.step_dt).square().sum(dim=1)


def feet_slide_l2(env, sensor_cfg, asset_cfg, threshold=1.0):
    """World-XY foot-link/COM speed squared gated by retained contact history.

    This is a velocity proxy, not relative contact-point or terrain-tangent slip.
    The original tuned-profile function and its history gate are unchanged.
    """
    sensor = env.scene[sensor_cfg.name]
    force = _tensor(sensor.data.net_normal_forces_w_history)[:, :, sensor_cfg.body_ids]
    contact = force.norm(dim=-1).amax(dim=1) > threshold
    velocity = _tensor(env.scene[asset_cfg.name].data.body_lin_vel_w)[:, asset_cfg.body_ids, :2]
    return (velocity.square().sum(dim=-1) * contact).sum(dim=1)


def leg_contact_force_proxy(env, sensor_cfg, threshold_n=50.0, force_scale_n=50.0, cap_per_body=4.0):
    """Bounded high-force normal-contact proxy, not an impact impulse.

    Match the count term's per-body retained-history normal-force norm peak.
    Empty/disabled history uses the current sample. Rectify and normalize each
    selected body's excess, square and cap independently, then sum over bodies.
    The manager supplies weight and policy dt; this function applies neither.
    """
    parameters = {}
    for name, value in (("threshold_n", threshold_n), ("force_scale_n", force_scale_n),
                        ("cap_per_body", cap_per_body)):
        value = float(value)
        if not math.isfinite(value) or (value < 0.0 if name == "threshold_n" else value <= 0.0):
            raise ValueError(f"{name} must be finite and {'non-negative' if name == 'threshold_n' else 'positive'}")
        parameters[name] = value
    sensor = env.scene[sensor_cfg.name]
    history = _tensor(getattr(sensor.data, "net_normal_forces_w_history", None))
    if history is None or history.shape[1] == 0:
        force = _tensor(sensor.data.net_normal_forces_w)[:, sensor_cfg.body_ids].norm(dim=-1)
    else:
        force = history[:, :, sensor_cfg.body_ids].norm(dim=-1).amax(dim=1)
    excess = ((force - parameters["threshold_n"]) / parameters["force_scale_n"]).clamp_min(0.0)
    return excess.square().clamp_max(parameters["cap_per_body"]).sum(dim=1)


def _contact_peak_norm(env, sensor_cfg):
    sensor = env.scene[sensor_cfg.name]
    history = _tensor(getattr(sensor.data, "net_normal_forces_w_history", None))
    if history is not None and history.shape[1] > 0:
        return history[:, :, sensor_cfg.body_ids].norm(dim=-1).amax(dim=1)
    return _tensor(sensor.data.net_normal_forces_w)[:, sensor_cfg.body_ids].norm(dim=-1)


def shank_horizontal_l2(
    env, knee_cfg, foot_cfg, foot_sensor_cfg, calf_sensor_cfg,
    max_stance_angle_deg=65.0, swing_weight=0.25, threshold_n=1.0,
):
    """Soft excess angle to WORLD down, with reduced cost during free swing.

    Knee/foot and the two contact selections MUST have the same leg order;
    the runtime checks the resolved names before learning. A calf-supported
    leg gets the full weight even if its foot is not touching the terrain.
    Free swing retains a small cost, avoiding a discontinuous zero-cost escape.
    The normalized cosine deficit is capped before squaring (per-leg cap 4).
    No prescribed gait phase, body-pitch target, joint offset or actor input.
    """
    robot = env.scene[knee_cfg.name]
    positions = _tensor(robot.data.body_link_pos_w)
    shank = positions[:, foot_cfg.body_ids] - positions[:, knee_cfg.body_ids]
    down_cosine = -shank[..., 2] / shank.norm(dim=-1).clamp_min(1e-6)
    cosine_limit = math.cos(math.radians(max_stance_angle_deg))
    excess = ((cosine_limit - down_cosine) / cosine_limit).clamp(0.0, 2.0)
    support = (_contact_peak_norm(env, foot_sensor_cfg) > threshold_n) | (
        _contact_peak_norm(env, calf_sensor_cfg) > threshold_n
    )
    phase_weight = swing_weight + (1.0 - swing_weight) * support.to(excess.dtype)
    return (phase_weight * excess.square()).mean(dim=1)


def slow_mirror_bias_l2(env, asset_cfg, time_constant_s=0.8,
                        deadband_rad=0.10, scale_rad=0.35, warmup_s=1.5,
                        stair_scale=0.0):
    """Penalize persistent L/R pose bias under straight-moving commands.

    Hip mirror differences are sums; thigh/calf differences are differences.
    A reset-safe EMA averages out normal alternating gait, with a deadband.
    Turning, lateral commands and first 1.5 s are unpenalized. The default
    excludes stairs; an explicit stair_scale adds reduced stair exposure. This is
    reward state only; it is not added to actor inputs or controller targets.
    Selection MUST be grouped hip/thigh/calf and FL/FR/RL/RR within each group.
    """
    from stair_terrain import flat_env_mask

    robot = env.scene[asset_cfg.name]
    q = _tensor(robot.data.joint_pos)[:, asset_cfg.joint_ids]
    command = env.command_manager.get_command("base_velocity")
    flat = flat_env_mask(env)
    terrain_weight = torch.where(flat, 1.0, float(stair_scale))
    eligible = (terrain_weight > 0) & (command[:, 0].abs() > 0.1)
    eligible &= (command[:, 1].abs() < 0.05) & (command[:, 2].abs() < 0.15)
    difference = torch.stack((q[:, 0] + q[:, 1], q[:, 2] + q[:, 3],
                              q[:, 4] - q[:, 5], q[:, 6] - q[:, 7],
                              q[:, 8] - q[:, 9], q[:, 10] - q[:, 11]), dim=1)
    key = "_him_slow_mirror_bias"
    state = getattr(env, key, None)
    if state is None:
        state = {"step": -1, "mean": torch.zeros_like(difference),
                 "age": torch.zeros_like(command[:, 0]),
                 "max_raw_cost_seen": torch.zeros((), device=q.device, dtype=q.dtype)}
        setattr(env, key, state)
    step = int(env.common_step_counter)
    if state["step"] != step:
        reset = (env.episode_length_buf <= 1) | (~eligible)
        alpha = 1.0 - math.exp(-float(env.step_dt) / time_constant_s)
        state["mean"] = torch.where(reset[:, None], 0.0,
                                     (1.0 - alpha) * state["mean"] + alpha * difference)
        state["age"] = torch.where(reset, 0.0, state["age"] + float(env.step_dt))
        state["step"] = step
    error = ((state["mean"].abs() - deadband_rad).clamp_min(0.0) / scale_rad).square().clamp_max(4.0)
    value = error.mean(1) * terrain_weight * (eligible & (state["age"] >= warmup_s))
    state["max_raw_cost_seen"] = torch.maximum(state["max_raw_cost_seen"], value.max())
    return value


def configure_stair_rewards(cfg, profile="faithful", *, posture_weight=-0.08,
                            posture_angle_deg=65.0, posture_swing_weight=0.25,
                            symmetry_weight=-0.08, symmetry_stair_scale=0.0):
    """Replace stock rewards before launch and return serializable provenance.

    Call after terrain configuration has installed ``base_height_scanner``.
    ``stock`` leaves the task configuration unchanged for migration comparisons.
    All non-stock presets preserve the original 0.25 tracking variance,
    first/second action differences, energy and body-relative clearance terms.
    ``contact`` preserves every faithful term and adds one Go2 adaptation.
    ``contact_force`` retains all contact terms and adds one bounded force proxy.
    ``contact_slide`` retains all contact terms and adds only the tuned foot proxy.
    ``contact_vertical`` halves the original vertical-velocity penalty.
    ``contact_clearance`` doubles only the original body-relative foot-height
    penalty; this does not turn that reward into terrain-relative swing clearance.
    ``faithful_tracking`` increases only faithful's XY tracking weight to 1.5.
    """
    contact_profiles = ("contact", "contact_light", "contact_force", "contact_slide", "contact_vertical", "contact_clearance")
    posture_profiles = ("posture", "posture_contact", "posture_symmetric")
    if profile not in ("faithful", "faithful_tracking", "tuned", *contact_profiles, *posture_profiles, "stock"):
        raise ValueError("Unknown stair reward profile")
    if profile in posture_profiles:
        if not math.isfinite(posture_weight) or posture_weight >= 0.0:
            raise ValueError("posture_weight must be finite and negative")
        if not math.isfinite(posture_angle_deg) or not 30.0 <= posture_angle_deg <= 80.0:
            raise ValueError("posture_angle_deg must be in [30, 80]")
        if not math.isfinite(posture_swing_weight) or not 0.0 < posture_swing_weight <= 1.0:
            raise ValueError("posture_swing_weight must be in (0, 1]")
    if profile == "posture_symmetric" and (not math.isfinite(symmetry_weight) or symmetry_weight >= 0):
        raise ValueError("symmetry_weight must be finite and negative")
    if profile == "posture_symmetric" and (not math.isfinite(symmetry_stair_scale)
                                           or not 0.0 <= symmetry_stair_scale <= 1.0):
        raise ValueError("symmetry_stair_scale must be finite in [0,1]")
    if profile == "stock":
        return {"profile": "stock", "source": "pinned Isaac Lab Go2 task"}
    sensor_name = "base_height_scanner"
    if getattr(cfg.scene, sensor_name, None) is None:
        sensor_name = "height_scanner"
    if getattr(cfg.scene, sensor_name, None) is None:
        raise ValueError("Stair rewards require a terrain ray scanner; configure terrain first")
    if profile in (*contact_profiles, *posture_profiles) and getattr(cfg.scene, "contact_forces", None) is None:
        raise ValueError("Contact reward requires the contact_forces sensor")
    from isaaclab.managers import RewardTermCfg, SceneEntityCfg

    # Prevent residual stock torque/air-time/position-limit rewards from silently
    # changing the released objective when the source task adds optional terms.
    for name, term in list(vars(cfg.rewards).items()):
        if term is not None and hasattr(term, "weight"):
            setattr(cfg.rewards, name, None)
    robot = SceneEntityCfg("robot")
    feet = SceneEntityCfg("robot", body_names=".*_foot", preserve_order=True)
    scan = SceneEntityCfg(sensor_name)
    mdp = "isaaclab.envs.mdp:"
    custom = "stair_rewards:"

    def add(name, function, weight, **params):
        setattr(cfg.rewards, name, RewardTermCfg(func=function, weight=weight, params=params))

    add("track_lin_vel_xy_exp", mdp + "track_lin_vel_xy_exp", 1.5 if profile == "faithful_tracking" else 1.0,
        command_name="base_velocity", std=math.sqrt(0.25))
    add("track_ang_vel_z_exp", mdp + "track_ang_vel_z_exp", 0.5,
        command_name="base_velocity", std=math.sqrt(0.25))
    add("lin_vel_z_l2", mdp + "lin_vel_z_l2",
        -0.5 if profile == "tuned" else (-1.0 if profile == "contact_vertical" else -2.0))
    add("ang_vel_xy_l2", mdp + "ang_vel_xy_l2", -0.05)
    add("flat_orientation_l2", mdp + "flat_orientation_l2", -0.1 if profile == "tuned" else -0.2)
    add("dof_acc_l2", custom + "policy_joint_acceleration_l2", -2.5e-7, asset_cfg=robot)
    add("joint_power", custom + "joint_power_l1", -2e-5, asset_cfg=robot)
    add("base_height", custom + "terrain_relative_base_height_l2", -1.0,
        asset_cfg=robot, sensor_cfg=scan, target_height=0.30)
    add("foot_clearance", custom + "foot_clearance_body_l2",
        -0.02 if profile == "contact_clearance" else -0.01,
        asset_cfg=feet, target_height=-0.20)
    add("action_rate_l2", mdp + "action_rate_l2", -0.01)
    add("action_smoothness", custom + "action_smoothness_l2", -0.01)
    if profile in ("tuned", "contact_slide"):
        add("feet_slide", custom + "feet_slide_l2", -0.05, asset_cfg=feet,
            sensor_cfg=SceneEntityCfg("contact_forces", body_names=".*_foot", preserve_order=True))
    if profile in contact_profiles:
        add("leg_contacts", mdp + "undesired_contacts", -0.02 if profile == "contact_light" else -0.1, threshold=1.0,
            sensor_cfg=SceneEntityCfg("contact_forces", body_names=[".*_thigh", ".*_calf"]))
    if profile == "contact_force":
        add("leg_contact_force_proxy", custom + "leg_contact_force_proxy", -0.02,
            threshold_n=50.0, force_scale_n=50.0, cap_per_body=4.0,
            sensor_cfg=SceneEntityCfg("contact_forces", body_names=[".*_thigh", ".*_calf"]))
    if profile in posture_profiles:
        legs = ("FL", "FR", "RL", "RR")
        def selection(name, part):
            return SceneEntityCfg(name, body_names=[leg + "_" + part for leg in legs], preserve_order=True)
        add("shank_horizontal", custom + "shank_horizontal_l2", posture_weight,
            knee_cfg=selection("robot", "calf"), foot_cfg=selection("robot", "foot"),
            foot_sensor_cfg=selection("contact_forces", "foot"),
            calf_sensor_cfg=selection("contact_forces", "calf"),
            max_stance_angle_deg=posture_angle_deg, swing_weight=posture_swing_weight,
            threshold_n=1.0)
    if profile == "posture_contact":
        add("head_undesired_contacts", mdp + "undesired_contacts", -1.0, threshold=0.3,
            sensor_cfg=SceneEntityCfg("contact_forces", body_names=["Head_.*"]))
        add("other_undesired_contacts", mdp + "undesired_contacts", -0.01, threshold=0.3,
            sensor_cfg=SceneEntityCfg("contact_forces", body_names=[".*_hip", ".*_thigh", ".*_calf"]))
    if profile == "posture_symmetric":
        add("slow_mirror_bias", custom + "slow_mirror_bias_l2", symmetry_weight,
            asset_cfg=SceneEntityCfg("robot", joint_names=[leg + "_" + part + "_joint"
                for part in ("hip", "thigh", "calf") for leg in ("FL", "FR", "RL", "RR")],
                preserve_order=True), time_constant_s=0.8, deadband_rad=0.10,
                scale_rad=0.35, warmup_s=1.5, stair_scale=symmetry_stair_scale)
    manifest = {
        "profile": profile,
        "source": "released HIMLoco Go1 config/reward code at ef289ac",
        "base_height_sensor": sensor_name,
        "height_target_m": 0.30,
        "body_foot_height_target_m": -0.20,
        "joint_acceleration_interval": "policy step",
        "physics_quaternion_order": "xyzw",
        "weights": {name: term.weight for name, term in vars(cfg.rewards).items()
                    if term is not None and hasattr(term, "weight")},
        "tuned_changes": [
            "vertical velocity penalty -2 -> -0.5",
            "orientation penalty -0.2 -> -0.1",
            "contact-only foot slip penalty -0.05",
        ] if profile == "tuned" else [],
        "adaptation_changes": (["faithful plus leg_contacts -0.1; no other faithful term changes"]
            + (["contact plus bounded leg_contact_force_proxy -0.02; no other contact term changes"]
               if profile == "contact_force" else [])
            + (["contact plus feet_slide -0.05; no other contact term changes"]
               if profile == "contact_slide" else [])
            + (["contact lin_vel_z_l2 -2 -> -1; no other contact term changes"]
               if profile == "contact_vertical" else [])
            + (["contact foot_clearance -0.01 -> -0.02; no other contact term changes"]
               if profile == "contact_clearance" else [])) if profile in contact_profiles else (
            ["faithful track_lin_vel_xy_exp 1 -> 1.5; no other faithful term changes"]
            if profile == "faithful_tracking" else []),
        "contact_penalty": {
            "baseline_profile": "faithful",
            "term": "leg_contacts",
            "function": mdp + "undesired_contacts",
            "body_name_patterns": [".*_thigh", ".*_calf"],
            "expected_selected_go2_bodies": 8,
            "excluded_bodies": "feet, base and hips",
            "threshold_n": 1.0,
            "measurement": "count of selected bodies with retained-history net-normal-force vector norm strictly above threshold",
            "weight_scaling": "Isaac Lab reward manager multiplies -0.1 by policy dt",
            "reproduction_scope": "added Go2 adaptation; released Go1 collision weight is zero",
        } if profile in contact_profiles else None,
        "force_proxy_penalty": {
            "baseline_profile": "contact",
            "term": "leg_contact_force_proxy",
            "function": custom + "leg_contact_force_proxy",
            "body_name_patterns": [".*_thigh", ".*_calf"],
            "expected_selected_go2_bodies": 8,
            "excluded_bodies": "feet, base and hips",
            "threshold_n": 50.0,
            "force_scale_n": 50.0,
            "cap_per_body": 4.0,
            "weight": -0.02,
            "formula": "sum_i min(max((F_i-50)/50,0)^2,4); F_i=max_history(norm(net_normal_force_i))",
            "measurement": "bounded per-body retained-history normal-contact-force norm excess; current sample if history is empty or disabled",
            "interpretation_limit": "force-sample proxy, not impact impulse, energy, scrape duration or damage; forces >=150N saturate",
            "weight_scaling": "Isaac Lab reward manager multiplies -0.02 by policy dt; function has no dt factor",
            "reproduction_scope": "added Go2 adaptation; all faithful terms and contact count -0.1 retained",
            "actor_observations_and_collision_geometry": "unchanged",
        } if profile == "contact_force" else None,
        "slide_proxy_penalty": {
            "baseline_profile": "contact",
            "term": "feet_slide",
            "function": custom + "feet_slide_l2",
            "asset_body_name_pattern": ".*_foot",
            "sensor_body_name_pattern": ".*_foot",
            "preserve_order": True,
            "expected_selected_go2_bodies": 4,
            "expected_go2_body_names": ["FL_foot", "FR_foot", "RL_foot", "RR_foot"],
            "threshold_n": 1.0,
            "threshold_parameter_source": "unchanged feet_slide_l2 default threshold=1.0",
            "weight": -0.05,
            "formula": "sum_i (v_world_x_i^2+v_world_y_i^2) * (max_history(norm(net_normal_force_i)) > 1)",
            "contact_gating": "retained-history net-normal-force vector norm strictly above threshold; same function/params as tuned feet_slide",
            "velocity_source": "robot.data.body_lin_vel_w; pinned Lab alias body_com_lin_vel_w; Go2 foot COM equals foot-link origin",
            "velocity_frame": "world XY",
            "raw_term_units": "m^2/s^2; sum over four feet, unbounded",
            "history_requirement": "nonempty contact-force history; existing helper has no current-only fallback",
            "interpretation_limit": "foot-link XY velocity proxy, not exact contact-point slip, terrain-tangent speed or slip duration; retained contact may outlast current contact",
            "weight_scaling": "Isaac Lab reward manager multiplies -0.05 by policy dt; function has no dt factor",
            "reproduction_scope": "added Go2 adaptation; all faithful terms and contact count -0.1 retained; no tuned vertical-velocity/orientation changes",
            "actor_observations_and_collision_geometry": "unchanged",
        } if profile == "contact_slide" else None,
    }
    if profile in posture_profiles:
        manifest["adaptation_changes"] = [
            "faithful plus support-aware shank_horizontal; all released reward terms unchanged"
        ]
        manifest["posture_penalty"] = {
            "term": "shank_horizontal", "weight": posture_weight,
            "max_stance_angle_deg": posture_angle_deg, "swing_weight": posture_swing_weight,
            "threshold_n": 1.0, "leg_order": ["FL", "FR", "RL", "RR"],
            "geometry": "knee/calf link origin to foot link origin, world frame",
            "formula": "mean_i phase_i * clamp((cos(theta_max)-cos(theta_i))/cos(theta_max),0,2)^2",
            "support": "foot OR calf retained-history net-normal-force norm > 1 N",
            "phase_weight": "1 when supported, swing_weight otherwise",
            "weight_scaling": "reward manager multiplies weight by policy dt; function applies no dt",
            "scope": "Go2 reward adaptation, not an original paper reward; mean over all four legs",
            "limitations": "soft posture preference, not terrain clearance or a force/damage limit",
            "actor_observations_controller_and_collision_geometry": "unchanged",
        }
    if profile == "posture_contact":
        manifest["adaptation_changes"].append(
            "posture plus user head contact -1 and hip/thigh/calf contact -0.01 at 0.3 N; all other terms unchanged")
        manifest["separate_contact_penalties"] = {
            "baseline_profile": "posture", "threshold_n": 0.3,
            "head": {"term": "head_undesired_contacts", "weight": -1.0,
                     "patterns": ["Head_.*"], "expected_bodies": ["Head_upper", "Head_lower"]},
            "other": {"term": "other_undesired_contacts", "weight": -0.01,
                      "patterns": [".*_hip", ".*_thigh", ".*_calf"], "expected_body_count": 12},
            "measurement": "count of bodies with retained-history net-normal-force norm > threshold",
            "weight_scaling": "reward manager multiplies each weight by policy dt",
            "limitations": "contact count does not directly measure clearance, shank angle, impulse or damage",
            "reproduction_scope": "explicit user-requested Go2 contact reward adaptation",
        }
    if profile == "posture_symmetric":
        manifest["adaptation_changes"].append(
            "posture plus reset-safe EMA mirror joint bias under straight-moving commands; explicit terrain weights")
        manifest["symmetry_penalty"] = {
            "term": "slow_mirror_bias", "weight": symmetry_weight,
            "time_constant_s": 0.8, "deadband_rad": 0.10, "scale_rad": 0.35,
            "warmup_s": 1.5, "raw_cost_cap": 4.0,
            "flat_scale": 1.0, "stair_scale": symmetry_stair_scale,
            "scope": "flat scale1, explicit stair scale; abs(vx)>0.1, abs(vy)<0.05, abs(yaw rate)<0.15",
            "mirror": "hip sums, thigh/calf differences; front and rear pairs",
            "limitations": "EMA reward state; does not prescribe a gait phase or guarantee symmetry; different treads can justify temporary bias",
            "actor_inputs_added": False,
        }
    if profile in ("contact_vertical", "contact_clearance"):
        vertical = profile == "contact_vertical"
        manifest["reward_weight_ablation"] = {
            "baseline_profile": "contact",
            "term": "lin_vel_z_l2" if vertical else "foot_clearance",
            "original_weight": -2.0 if vertical else -0.01,
            "weight": -1.0 if vertical else -0.02,
            "function_and_parameters": "unchanged from contact and released HIMLoco",
            "all_other_contact_terms": "unchanged",
            "interpretation": (
                "reduce cost of required vertical base motion on stairs; does not directly penalize bounce amplitude"
                if vertical else
                "stronger original body-relative moving-foot height target at -0.20m; not terrain-relative swing clearance"
            ),
            "actor_observations_and_collision_geometry": "unchanged",
        }
    if profile == "faithful_tracking":
        manifest["reward_weight_ablation"] = {
            "baseline_profile": "faithful",
            "term": "track_lin_vel_xy_exp",
            "original_weight": 1.0,
            "weight": 1.5,
            "function_and_parameters": "unchanged from faithful and released HIMLoco; body XY error, variance 0.25",
            "all_other_faithful_terms": "unchanged; no added contact terms",
            "interpretation": "increase existing commanded body XY velocity tracking reward; no added lateral controller or world-position target",
            "actor_observations_and_collision_geometry": "unchanged",
        }
    if profile == "contact_light":
        manifest["adaptation_changes"] = [
            "faithful plus existing leg_contacts -0.02; no other faithful term changes"
        ]
        manifest["contact_penalty"]["weight_scaling"] = "Isaac Lab reward manager multiplies -0.02 by policy dt"
        manifest["contact_penalty"]["reproduction_scope"] = "added Go2 adaptation; released Go1 collision weight is zero; one-fifth existing contact profile weight"
        manifest["reward_weight_ablation"] = {
            "baseline_profile": "faithful",
            "term": "leg_contacts",
            "original_weight": 0.0,
            "weight": -0.02,
            "function_and_parameters": "existing contact undesired_contacts retained-history count, same eight thigh/calf bodies, strict threshold 1N",
            "all_other_faithful_terms": "unchanged",
            "interpretation": "weak existing leg-contact count penalty; not force severity, scrape duration or impact impulse",
            "actor_observations_and_collision_geometry": "unchanged",
        }
    return manifest
