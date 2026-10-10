"""Independent first-episode staircase traversal and motion-quality evaluation.

Geometry coordinates are relative to scene.env_origins. Successful traversal
requires all four feet beyond the last riser, the body at the goal, correct
platform height, upright posture and a continuous goal dwell. A timeout,
standing on the starting landing or a later auto-reset episode cannot pass.
"""

import math
from contextlib import contextmanager

import torch


DEFAULT_THRESHOLDS = {
    "completion_fraction": 0.90,
    "minimum_num_envs": 32,
    "stall_window_s": 4.0,
    "stall_progress_m": 0.05,
    "contact_force_n": 1.0,
    "slip_speed_m_s": 0.10,
    "goal_foot_clearance_m": 0.10,
    "goal_foot_height_tolerance_m": 0.12,
    "minimum_base_clearance_m": 0.18,
    "maximum_base_clearance_m": 0.60,
    "upright_gravity_z": -0.8,
}


def _tensor(value):
    return value if isinstance(value, torch.Tensor) else value.torch


def _validate_geometry(geometry):
    if isinstance(geometry, (list, tuple)):
        if not geometry:
            raise ValueError("Provide at least one staircase geometry")
        for item in geometry:
            _validate_geometry(item)
        return
    required = ("direction", "num_steps", "step_height", "step_depth", "width", "start_x",
                "last_riser_x", "goal_x", "goal_platform_z")
    if any(name not in geometry for name in required):
        raise ValueError("Incomplete staircase geometry metadata")
    if geometry["direction"] not in ("asc", "desc") or geometry.get("travel_sign", 1) != 1:
        raise ValueError("Evaluation requires asc/desc stairs traversed along positive x")
    if geometry["goal_x"] <= geometry["start_x"] or geometry["last_riser_x"] >= geometry["goal_x"]:
        raise ValueError("Goal must be beyond the full flight")
    if not all(math.isfinite(float(geometry[name])) for name in required if name != "direction"):
        raise ValueError("Staircase geometry must be finite")


def _geometry_for_envs(geometry, env):
    """Fixed batches map each terrain column to its exact metadata."""
    if not isinstance(geometry, (list, tuple)):
        return geometry, torch.zeros(env.num_envs, device=env.device, dtype=torch.long), [geometry]
    types = _tensor(env.scene.terrain.terrain_types).long()
    if bool((types < 0).any()) or bool((types >= len(geometry)).any()):
        raise ValueError("Terrain column does not match supplied geometry list")
    numeric = ("num_steps", "step_height", "step_depth", "width", "start_x", "first_riser_x", "last_riser_x",
               "goal_x", "goal_platform_start_x", "goal_platform_z", "lateral_center_y", "goal_dwell_s")
    defaults = {"lateral_center_y": 0.0, "goal_dwell_s": 0.5}
    parameters = {}
    for name in numeric:
        values = [item.get(name, defaults.get(name, item.get("last_riser_x"))) for item in geometry]
        parameters[name] = torch.tensor(values, device=env.device)[types]
    return parameters, types, list(geometry)


def _parameter(value, reference, *, feet=False):
    result = torch.as_tensor(value, device=reference.device, dtype=reference.dtype)
    return result[:, None] if feet and result.ndim else result


def _command_cfg(command, seconds, speed):
    command.heading_command = False
    command.rel_heading_envs = 0.0
    command.rel_standing_envs = 0.0
    command.debug_vis = False
    command.resampling_time_range = (seconds + 1.0, seconds + 1.0)
    command.ranges.lin_vel_x = (speed, speed)
    command.ranges.lin_vel_y = (0.0, 0.0)
    command.ranges.ang_vel_z = (0.0, 0.0)
    command.ranges.heading = None


def configure_stair_evaluation(cfg, geometry, seconds=30.0, speed=0.3, randomized=False,
                               dynamics_randomized=False):
    """Configure before environment construction; randomized means reset perturbations.

    Ground/robot material choices remain those supplied by the caller. Startup
    mass, COM and actuator gain randomization are disabled by default so repeated
    seeds only alter resets. dynamics_randomized preserves caller-configured
    startup events; it does not synthesize new randomization ranges.
    Friction-heldout cases require a separately constructed environment.
    Sensor refresh is explicitly eager during evaluation. The installed contact
    sensor also refreshes nonempty history eagerly when scene reads are lazy.
    """
    _validate_geometry(geometry)
    if seconds <= 0 or speed <= 0 or not math.isfinite(speed):
        raise ValueError("Require positive duration and commanded forward speed")
    cfg.compute_final_obs = True
    cfg.episode_length_s = float(seconds)
    cfg.observations.policy.enable_corruption = False
    cfg.observations.critic.enable_corruption = False
    scene = getattr(cfg, "scene", None)
    if hasattr(scene, "lazy_sensor_update"):
        scene.lazy_sensor_update = False
    contact_cfg = getattr(scene, "contact_forces", None)
    physics_dt = getattr(getattr(cfg, "sim", None), "dt", None)
    if contact_cfg is not None and physics_dt is not None:
        contact_cfg.update_period = float(physics_dt)
    if hasattr(cfg.curriculum, "terrain_levels"):
        cfg.curriculum.terrain_levels = None
    if hasattr(cfg.terminations, "stair_goal_reached"):
        cfg.terminations.stair_goal_reached = None
    events_to_remove = ("push_robot",) if dynamics_randomized else (
        "push_robot", "add_base_mass", "base_com", "him_actuator_gains"
    )
    for name in events_to_remove:
        if hasattr(cfg.events, name):
            setattr(cfg.events, name, None)
    delta, yaw, vel = (0.08, 0.08, 0.03) if randomized else (0.0, 0.0, 0.0)
    # Every batch flight uses the same starting-landing origin convention.
    reset_geometry = geometry[0] if isinstance(geometry, (list, tuple)) else geometry
    if isinstance(geometry, (list, tuple)) and any(item["start_x"] != reset_geometry["start_x"] for item in geometry):
        raise ValueError("Batch geometry must share the same reset start_x")
    cfg.events.reset_base.params["pose_range"] = {
        "x": (reset_geometry["start_x"] - delta, reset_geometry["start_x"] + delta),
        "y": (reset_geometry.get("lateral_center_y", 0.0) - delta, reset_geometry.get("lateral_center_y", 0.0) + delta),
        "yaw": (-yaw, yaw), "z": (0.0, 0.0), "roll": (0.0, 0.0), "pitch": (0.0, 0.0),
    }
    cfg.events.reset_base.params["velocity_range"] = {
        name: (-vel, vel) for name in ("x", "y", "z", "roll", "pitch", "yaw")
    }
    cfg.events.reset_robot_joints.params["position_range"] = (0.95, 1.05) if randomized else (1.0, 1.0)
    cfg.events.reset_robot_joints.params["velocity_range"] = (-0.03, 0.03) if randomized else (0.0, 0.0)
    if getattr(cfg.events, "base_external_force_torque", None) is not None:
        cfg.events.base_external_force_torque.params["force_range"] = (0.0, 0.0)
        cfg.events.base_external_force_torque.params["torque_range"] = (0.0, 0.0)
    _command_cfg(cfg.commands.base_velocity, seconds, float(speed))
    return cfg


def _body_ids(names, suffix):
    return [index for index, name in enumerate(names) if name.lower().endswith(suffix)]


def _yaw_roll_pitch(quat):
    # Isaac Lab 3 uses xyzw, unlike the older wxyz convention.
    x, y, z, w = quat.unbind(-1)
    roll = torch.atan2(2 * (w*x + y*z), 1 - 2 * (x*x + y*y))
    pitch = torch.asin((2 * (w*y - z*x)).clamp(-1, 1))
    yaw = torch.atan2(2 * (w*z + x*y), 1 - 2 * (y*y + z*z))
    return yaw, roll, pitch


class StairStateCapture:
    """Capture at termination computation, after physics and before auto-reset.

    This narrowly scoped hook is restored on every exit, including exceptions.
    It modifies only this env instance's bound compute method, never Lab source.
    """

    def __init__(self, env):
        self.env = env
        self.robot = env.scene["robot"]
        foot_ids = _body_ids(self.robot.body_names, "_foot")
        if len(foot_ids) != 4:
            raise ValueError("Stair evaluation requires exactly four Go2 foot bodies")
        self.foot_ids = torch.tensor(foot_ids, device=env.device, dtype=torch.long)
        self.foot_body_names = [self.robot.body_names[index] for index in foot_ids]
        sensor = env.scene.sensors["contact_forces"]
        self.sensor = sensor
        # Match by name instead of assuming sensor and robot body order agree.
        self.sensor_foot_ids = torch.tensor([sensor.body_names.index(self.robot.body_names[index])
                                            for index in foot_ids], device=env.device, dtype=torch.long)
        if self.sensor_foot_ids.numel() != 4:
            raise ValueError("Contact sensor must include four foot bodies")
        self.base_ids = [index for index, name in enumerate(sensor.body_names) if name.lower() == "base"]
        self.shank_ids = [index for index, name in enumerate(sensor.body_names)
                          if any(part in name.lower() for part in ("calf", "thigh", "shank"))]
        # Attribute the contact-reward bodies in robot order, independently of
        # the legacy aggregate shank selection and the sensor's body ordering.
        leg_ids = [index for index, name in enumerate(self.robot.body_names)
                   if name.endswith(("_thigh", "_calf"))]
        self.leg_ids = torch.tensor(leg_ids, device=env.device, dtype=torch.long)
        self.leg_body_names = [self.robot.body_names[index] for index in leg_ids]
        self.sensor_leg_ids = torch.tensor([sensor.body_names.index(name) for name in self.leg_body_names],
                                           device=env.device, dtype=torch.long)
        # Auxiliary trace-only fields are kept outside the measured state so
        # optional pose availability never changes existing finite/active masks.
        self.leg_trace_telemetry = {}
        self.leg_trace_metadata = {
            "body_order": "leg_body_names",
            "leg_current_normal_force_w_n": {
                "status": "available", "source": "contact_forces.data.net_normal_forces_w",
                "frame": "world", "measurement": "net normal contact force XYZ vector [N]; tangential friction excluded"},
            "leg_link_pos_w_m": {"source": "robot.data.body_link_pos_w", "frame": "world"},
            "leg_link_quat_w_xyzw": {"source": "robot.data.body_link_quat_w", "frame": "world",
                                     "quaternion_order": "xyzw"},
            "scope": "trace-only at the existing pre-reset capture; null field means unavailable; no metric or validity-mask input",
        }
        self.latest = None

    def snapshot(self):
        data = self.robot.data
        force = _tensor(self.sensor.data.net_normal_forces_w).clone()
        current_force = force.norm(dim=-1)
        history = _tensor(self.sensor.data.net_normal_forces_w_history)
        force_peak = history.norm(dim=-1).amax(dim=1).clone() if history.shape[1] else force.norm(dim=-1)
        applied = _tensor(self.robot.actuators.applied_effort).clone()
        computed = _tensor(self.robot.actuators.computed_effort).clone()
        # computed != applied detects the DC torque-speed limiter as well as a
        # fixed limit, unlike comparing with nominal maximum torque alone.
        clipped = (computed - applied).abs() > 1e-4
        limits = _tensor(data.joint_effort_limits)
        near_limit = (applied.abs() >= 0.98 * limits.abs()) & torch.isfinite(limits) & (limits > 0)
        self.leg_trace_telemetry["leg_current_normal_force_w_n"] = force[:, self.sensor_leg_ids].clone()
        for field, attribute, width in (("leg_link_pos_w_m", "body_link_pos_w", 3),
                                        ("leg_link_quat_w_xyzw", "body_link_quat_w", 4)):
            metadata = self.leg_trace_metadata[field]
            try:
                value = getattr(data, attribute, None)
                if value is None:
                    raise AttributeError(f"{attribute} is unavailable")
                tensor = _tensor(value)
                if tensor.ndim != 3 or tensor.shape != (self.env.num_envs, len(self.robot.body_names), width):
                    raise ValueError(f"{attribute} dimensions do not match robot body names")
                self.leg_trace_telemetry[field] = tensor[:, self.leg_ids].clone()
                metadata.update(status="available")
                metadata.pop("reason", None)
            except (AttributeError, NotImplementedError, RuntimeError, TypeError, ValueError) as error:
                self.leg_trace_telemetry[field] = None
                metadata.update(status="unavailable", reason=f"{type(error).__name__}: {error}")
        return {
            "root_pos_w": _tensor(data.root_pos_w).clone(),
            "root_quat_w": _tensor(data.root_quat_w).clone(),
            "root_lin_vel_w": _tensor(data.root_lin_vel_w).clone(),
            "root_lin_vel_b": _tensor(data.root_lin_vel_b).clone(),
            "root_ang_vel_b": _tensor(data.root_ang_vel_b).clone(),
            "gravity": _tensor(data.projected_gravity_b).clone(),
            "feet_pos_w": _tensor(data.body_link_pos_w)[:, self.foot_ids].clone(),
            "feet_vel_w": _tensor(data.body_link_lin_vel_w)[:, self.foot_ids].clone(),
            "foot_contacts": force_peak[:, self.sensor_foot_ids] > 1.0,
            "current_foot_contacts": current_force[:, self.sensor_foot_ids] > 1.0,
            "base_force_n": force_peak[:, self.base_ids].amax(dim=1) if self.base_ids else applied[:, 0] * 0,
            "shank_force_n": force_peak[:, self.shank_ids].amax(dim=1) if self.shank_ids else applied[:, 0] * 0,
            "current_base_force_n": current_force[:, self.base_ids].amax(dim=1) if self.base_ids else applied[:, 0] * 0,
            "current_shank_force_n": current_force[:, self.shank_ids].amax(dim=1) if self.shank_ids else applied[:, 0] * 0,
            "leg_current_normal_force_norm_n": current_force[:, self.sensor_leg_ids].clone(),
            "leg_history_peak_normal_force_norm_n": force_peak[:, self.sensor_leg_ids].clone(),
            "applied_effort": applied, "torque_saturated": clipped | near_limit,
            "peak_contact_force_n": force_peak.amax(dim=1),
        }

    @contextmanager
    def installed(self):
        manager = self.env.termination_manager
        original = manager.compute
        had_own = "compute" in vars(manager)
        own = vars(manager).get("compute")

        def compute_with_snapshot(*args, **kwargs):
            output = original(*args, **kwargs)
            self.latest = self.snapshot()
            return output

        manager.compute = compute_with_snapshot
        try:
            yield self
        finally:
            if had_own:
                manager.compute = own
            else:
                del manager.compute


def _contact_sampling_metadata(env, capture, limits):
    """Describe configured cadence without claiming measured runtime timestamps."""
    scene_cfg = getattr(env.scene, "cfg", getattr(getattr(env, "cfg", None), "scene", None))
    sensor_cfg = getattr(capture.sensor, "cfg", None)
    physics_dt = getattr(env, "physics_dt", None)
    if physics_dt is None:
        physics_dt = getattr(getattr(getattr(env, "cfg", None), "sim", None), "dt", None)
    physics_dt = float(physics_dt) if physics_dt is not None else None
    update_period = getattr(sensor_cfg, "update_period", None)
    update_period = float(update_period) if update_period is not None else None
    lazy = getattr(scene_cfg, "lazy_sensor_update", None)
    handles_decimation = getattr(env, "_physics_handles_decimation", None)
    buffer_length = int(_tensor(capture.sensor.data.net_normal_forces_w_history).shape[1])
    configured_length = getattr(sensor_cfg, "history_length", None)
    history_length = int(configured_length) if configured_length is not None else buffer_length
    update = getattr(capture.sensor, "update", None)
    update_method = (getattr(update, "__module__", "") + "." + getattr(update, "__qualname__", "")) if update is not None else None
    # This installed BaseContactSensor override refreshes nonempty history even
    # if SensorBase.update receives force_recompute=False from a lazy scene.
    history_updates = history_length > 0 and update_method == "isaaclab.sensors.contact_sensor.base_contact_sensor.BaseContactSensor.update"
    cadence, interval = "unknown", None
    if lazy is False or history_updates:
        scene_dt = float(env.step_dt) if handles_decimation is True else physics_dt if handles_decimation is False else None
        if scene_dt is not None and update_period is not None and update_period <= scene_dt + 1e-9:
            interval = scene_dt
            cadence = "eager_policy_step_history" if handles_decimation else "eager_physics_step_history"
    elif lazy is True:
        cadence = "lazy_read_driven_history"
    if not history_length:
        cadence, interval = "current_force_fallback_without_history", None
    physics_step_history = (interval is not None and handles_decimation is False
                            and physics_dt is not None and abs(interval - physics_dt) <= 1e-9)
    return {
        "semantics_version": 2,
        "physics_dt_s": physics_dt,
        "policy_sample_dt_s": float(env.step_dt),
        "sensor_update_period_s": update_period,
        "scene_lazy_sensor_update": lazy,
        "physics_handles_policy_decimation": handles_decimation,
        "sensor_type": type(capture.sensor).__module__ + "." + type(capture.sensor).__qualname__,
        "sensor_update_method": update_method,
        "installed_sensor_updates_nonempty_history_with_lazy_scene": history_updates,
        "history_length": history_length,
        "history_buffer_length": buffer_length,
        "history_length_source": "sensor_configuration" if configured_length is not None else "buffer_shape_configuration_unavailable",
        "history_order": "newest_first",
        "history_sampling": cadence,
        "inferred_history_sample_dt_s": interval,
        "history_oldest_sample_age_s_after_warmup": (history_length - 1) * interval if interval is not None else None,
        "history_nominal_count_window_s": history_length * interval if interval is not None else None,
        "history_count_window_definition": "history_length times sample interval; distinct from oldest sample age",
        "history_covers_entire_policy_step": history_length * interval + 1e-9 >= float(env.step_dt) if physics_step_history else None,
        "cadence_evidence": "inferred from instantiated config and scene stepping; runtime sensor timestamps were not measured",
        "history_limit": "history peaks can miss contacts outside the retained samples; reset rows start with zero history",
        "current_sample_scope": "latest sensor force at the policy boundary before auto-reset; no substep duration inference",
        "force_measure": "world-frame vector norm of net normal force, including riser normals; no tangential friction force",
        "foot_contact_threshold_n": 1.0,
        "base_and_shank_contact_threshold_n": limits["contact_force_n"],
        "slip_speed_threshold_m_s": limits["slip_speed_m_s"],
        "slip_velocity_measure": "foot-link world-horizontal speed at the policy boundary; not contact-point tangential slip",
        "legacy_results": "reports without this metadata keep their original sampling semantics and cannot be assumed to use physics-step history",
    }


def completion_mask(state, origins, geometry, thresholds=None):
    """Pure tensor predicate shared by evaluation and CPU regression checks."""
    limits = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    relative = state["root_pos_w"] - origins
    feet = state["feet_pos_w"] - origins[:, None, :]
    goal_z = _parameter(geometry["goal_platform_z"], relative)
    y = _parameter(geometry.get("lateral_center_y", 0.0), relative)
    last_riser = _parameter(geometry["last_riser_x"], relative)
    platform_start = _parameter(geometry.get("goal_platform_start_x", geometry["last_riser_x"]), relative)
    width = _parameter(geometry["width"], relative)
    root_clearance = relative[:, 2] - goal_z
    return (
        (relative[:, 0] >= geometry["goal_x"])
        & (feet[:, :, 0].amin(dim=1) >= last_riser + limits["goal_foot_clearance_m"])
        & (feet[:, :, 0].amin(dim=1) >= platform_start + 0.03)
        & ((feet[:, :, 2] - _parameter(geometry["goal_platform_z"], feet, feet=True)).abs().amax(dim=1) < limits["goal_foot_height_tolerance_m"])
        & ((relative[:, 1] - y).abs() < width / 2)
        & ((feet[:, :, 1] - _parameter(geometry.get("lateral_center_y", 0.0), feet, feet=True)).abs().amax(dim=1) < width / 2 + 0.05)
        & (root_clearance >= limits["minimum_base_clearance_m"])
        & (root_clearance <= limits["maximum_base_clearance_m"])
        & (state["gravity"][:, 2] < limits["upright_gravity_z"])
        & (state["foot_contacts"].sum(dim=1) >= 2)
    )


@torch.inference_mode()
def _reset_trial(wrapped, seconds, speed, seed):
    term = wrapped.env.command_manager.get_term("base_velocity")
    _command_cfg(term.cfg, seconds, speed)
    wrapped.env.seed(seed)
    torch.manual_seed(seed)
    wrapped.reset()
    term.is_standing_env.zero_()
    term.is_heading_env.zero_()


def _apply_command(wrapped, speed, yaw_rate):
    term = wrapped.env.command_manager.get_term("base_velocity")
    term.vel_command_b[:, 0] = speed
    term.vel_command_b[:, 1] = 0
    term.vel_command_b[:, 2] = yaw_rate
    term.is_standing_env.zero_()
    term.is_heading_env.zero_()
    wrapped.obs_buf[:, :3] = term.vel_command_b * term.vel_command_b.new_tensor((2.0, 2.0, 0.25))
    wrapped.privileged_obs_buf[:, :3] = wrapped.obs_buf[:, :3]


def _finite_state(state):
    return all(bool(torch.isfinite(value).all()) for value in state.values())


@torch.inference_mode()
def evaluate_stairs(wrapped, policy, geometry, seconds=30.0, speed=0.3, seeds=(1,), randomized=False,
                    zero_action=False, heading_control=True, heading_gain=1.0, max_yaw_rate=0.5,
                    thresholds=None, progress=None, record_envs=4, record_stride=5,
                    dynamics_randomized=False):
    """Measure complete flights and first-episode smoothness across reset seeds.

    Call configure_stair_evaluation before constructing env. Reset seeds do not
    recreate terrain or startup materials. Heading control uses only root yaw,
    producing ordinary joystick yaw commands; no terrain sensing enters actor.
    Smoothness is reported with units, without claiming an uncalibrated universal
    threshold. Traces permit later jerk/contact analysis and visual verification.
    """
    _validate_geometry(geometry)
    limits = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    if seconds <= 0 or speed <= 0 or record_stride < 1:
        raise ValueError("Require positive duration, speed and record_stride")
    seeds = tuple(int(seed) for seed in seeds)
    if not seeds:
        raise ValueError("Provide at least one reset seed")
    env, n, device = wrapped.env, wrapped.num_envs, wrapped.device
    dt = float(env.step_dt)
    steps = math.ceil(seconds / dt)
    original_geometry = geometry
    geometry, case_ids, case_geometries = _geometry_for_envs(geometry, env)
    trace_ids = torch.cat([(case_ids == index).nonzero(as_tuple=False).flatten()[:max(1, record_envs // len(case_geometries))]
                          for index in range(len(case_geometries))]) if record_envs > 0 else case_ids[:0]
    capture = StairStateCapture(env)
    contact_sampling = _contact_sampling_metadata(env, capture, limits)
    trials = []

    with capture.installed():
        for seed in seeds:
            _reset_trial(wrapped, seconds, speed, seed)
            origins = _tensor(env.scene.env_origins).clone()
            initial = capture.snapshot()
            if not _finite_state(initial):
                raise RuntimeError("Non-finite initial staircase physics")
            initial_relative = initial["root_pos_w"] - origins
            last_measured_relative = initial_relative.clone()
            last_measured_feet = initial["feet_pos_w"] - origins[:, None, :]
            initial_yaw, initial_roll, initial_pitch = _yaw_roll_pitch(initial["root_quat_w"])
            start_valid = ((initial_relative[:, 0] - geometry["start_x"]).abs() < 0.3)
            active = torch.ones(n, device=device, dtype=torch.bool)
            complete = torch.zeros_like(active)
            falls = torch.zeros_like(active)
            escapes = torch.zeros_like(active)
            stalls = torch.zeros_like(active)
            timeouts = torch.zeros_like(active)
            nonfinite = torch.zeros_like(active)
            invalid_physics = torch.zeros_like(active)
            base_contact = torch.zeros_like(active)
            shank_contact = torch.zeros_like(active)
            current_base_contact = torch.zeros_like(active)
            current_shank_contact = torch.zeros_like(active)
            dwell = torch.zeros(n, device=device)
            completion_time = torch.full((n,), float("nan"), device=device)
            max_progress = torch.zeros(n, device=device)
            active_steps = torch.zeros(n, device=device, dtype=torch.long)
            window = max(1, math.ceil(limits["stall_window_s"] / dt))
            position_history = initial_relative[:, 0].repeat(window, 1)
            last_velocity = initial["root_lin_vel_w"]
            last_acceleration = torch.zeros_like(last_velocity)
            last_actions = torch.zeros(n, wrapped.num_actions, device=device)
            previous_action_delta = torch.zeros_like(last_actions)
            last_angular_velocity = initial["root_ang_vel_b"]
            pause_run = torch.zeros(n, device=device)
            longest_pause = torch.zeros_like(pause_run)
            roll_peak_per_env = torch.zeros_like(pause_run)
            statistics = {}
            counts = {}
            peaks = {}
            peak_force_per_env = torch.zeros(n, device=device)
            trace = []

            def accumulate(name, value, mask, elements=1):
                statistics[name] = statistics.get(name, 0.0) + torch.where(mask, value.double(), 0.0)
                counts[name] = counts.get(name, 0) + mask.long() * elements

            failure_reason = None
            executed = 0
            for step in range(steps):
                if not bool(active.any()):
                    break
                current_before = capture.snapshot()
                yaw_before, _, _ = _yaw_roll_pitch(current_before["root_quat_w"])
                yaw_command = (-heading_gain * yaw_before).clamp(-max_yaw_rate, max_yaw_rate) if heading_control else yaw_before * 0
                _apply_command(wrapped, speed, yaw_command)
                actions = torch.zeros(n, wrapped.num_actions, device=device) if zero_action else policy(wrapped.get_observations())
                actions[~active] = 0
                action_finite = torch.isfinite(actions).all(dim=-1)
                nonfinite |= active & ~action_finite
                if not bool((action_finite | ~active).all()):
                    failure_reason = "non_finite_actions"
                    break
                _, _, rewards, dones, infos, _, _ = wrapped.step(actions)
                executed = step + 1
                state = capture.latest
                if state is None:
                    raise RuntimeError("No pre-reset snapshot: Lab termination hook was not executed")
                finite = torch.isfinite(rewards)
                for value in state.values():
                    finite &= torch.isfinite(value).reshape(n, -1).all(dim=1)
                nonfinite |= active & ~finite
                valid = active & finite
                active_steps += valid.long()
                relative = state["root_pos_w"] - origins
                goal_z = _parameter(geometry["goal_platform_z"], relative)
                z_min = torch.minimum(goal_z, torch.zeros_like(goal_z)) - 1.0
                z_max = torch.maximum(goal_z, torch.zeros_like(goal_z)) + 2.0
                abnormal_physics = (relative[:, 2] < z_min) | (relative[:, 2] > z_max)
                invalid_physics |= valid & abnormal_physics
                y = relative[:, 1] - geometry.get("lateral_center_y", 0.0)
                progress_m = relative[:, 0] - initial_relative[:, 0]
                max_progress = torch.where(valid, torch.maximum(max_progress, progress_m), max_progress)
                feet_relative = state["feet_pos_w"] - origins[:, None, :]
                last_measured_relative = torch.where(valid[:, None], relative, last_measured_relative)
                last_measured_feet = torch.where(valid[:, None, None], feet_relative, last_measured_feet)
                flight_feet = ((feet_relative[:, :, 0] >= _parameter(geometry.get("first_riser_x", geometry["start_x"]), relative, feet=True))
                               & (feet_relative[:, :, 0] <= _parameter(geometry.get("goal_platform_start_x", geometry["goal_x"]), relative, feet=True)))
                feet_outside = (feet_relative[:, :, 1] - _parameter(geometry.get("lateral_center_y", 0.0), relative, feet=True)).abs() > _parameter(geometry["width"], relative, feet=True) / 2 + 0.05
                escaped = (y.abs() > geometry["width"] / 2 + 0.05) | (flight_feet & feet_outside).any(dim=1)
                escapes |= valid & escaped
                bases = state["base_force_n"] > limits["contact_force_n"]
                shanks = state["shank_force_n"] > limits["contact_force_n"]
                current_bases = state["current_base_force_n"] > limits["contact_force_n"]
                current_shanks = state["current_shank_force_n"] > limits["contact_force_n"]
                base_contact |= valid & bases
                shank_contact |= valid & shanks
                current_base_contact |= valid & current_bases
                current_shank_contact |= valid & current_shanks
                terminated = _tensor(infos.get("terminated", env.reset_terminated)).bool()
                truncated = _tensor(infos["time_outs"]).bool()
                fallen = bases | (state["gravity"][:, 2] > -0.5) | (terminated & ~escaped) | abnormal_physics
                falls |= valid & fallen
                timeouts |= valid & truncated
                goal = completion_mask(state, origins, geometry, limits) & valid & ~fallen & ~escaped & ~terminated
                dwell = torch.where(goal, dwell + dt, torch.zeros_like(dwell))
                newly_complete = valid & (dwell + 1e-6 >= geometry.get("goal_dwell_s", 0.5)) & start_valid
                complete |= newly_complete
                completion_time[newly_complete] = (step + 1) * dt
                historical = position_history[step % window].clone()
                position_history[step % window] = relative[:, 0]
                stalled = (relative[:, 0] - historical < limits["stall_progress_m"]) & (step >= window)
                stalls |= valid & stalled & ~newly_complete
                yaw, roll, pitch = _yaw_roll_pitch(state["root_quat_w"])
                roll_peak_per_env = torch.where(valid, torch.maximum(roll_peak_per_env, roll.abs()), roll_peak_per_env)
                velocity = state["root_lin_vel_b"]
                acceleration = (state["root_lin_vel_w"] - last_velocity) / dt
                jerk = (acceleration - last_acceleration) / dt
                action_delta = actions - last_actions
                action_second = action_delta - previous_action_delta
                angular_acceleration = (state["root_ang_vel_b"] - last_angular_velocity) / dt
                sample_mask = valid & (step >= math.ceil(1.0 / dt))
                flight_mask = (sample_mask & (relative[:, 0] >= geometry.get("first_riser_x", geometry["start_x"]) - 0.25)
                               & (relative[:, 0] <= geometry.get("goal_platform_start_x", geometry["goal_x"]) + 0.25))
                paused = flight_mask & (state["root_lin_vel_w"][:, 0] < 0.05)
                pause_run = torch.where(paused, pause_run + dt, torch.zeros_like(pause_run))
                longest_pause = torch.maximum(longest_pause, pause_run)
                accumulate("flight_pause_fraction", paused.float(), flight_mask)
                xy_error = torch.linalg.vector_norm(velocity[:, :2] - velocity.new_tensor((speed, 0)), dim=-1)
                for name, value in (
                    ("xy_tracking_mae_m_s", xy_error), ("xy_tracking_mse", xy_error.square()),
                    ("yaw_tracking_mae_rad_s", (state["root_ang_vel_b"][:, 2] - yaw_command).abs()),
                    ("measured_vx_m_s", velocity[:, 0]), ("measured_vy_m_s", velocity[:, 1]),
                    ("heading_abs_error_rad", yaw.abs()), ("roll_mse", roll.square()), ("pitch_mse", pitch.square()),
                    ("lateral_abs_error_m", y.abs()), ("linear_acceleration_squared", acceleration.square().sum(-1)),
                    ("linear_jerk_squared", jerk.square().sum(-1)),
                    ("body_angular_acceleration_squared", angular_acceleration.square().sum(-1)),
                    ("action_delta_squared", action_delta.square().mean(-1)),
                    ("action_second_delta_squared", action_second.square().mean(-1)),
                    ("applied_torque_squared", state["applied_effort"].square().mean(-1)),
                    ("torque_saturation_fraction", state["torque_saturated"].float().mean(-1)),
                    ("base_contact_step_fraction", bases.float()), ("shank_contact_step_fraction", shanks.float()),
                    ("current_sample_base_contact_step_fraction", current_bases.float()),
                    ("current_sample_shank_contact_step_fraction", current_shanks.float()),
                ):
                    accumulate(name, value, sample_mask)
                foot_speed = state["feet_vel_w"][:, :, :2].norm(dim=-1)
                for prefix, field in (("", "foot_contacts"), ("current_sample_", "current_foot_contacts")):
                    contact = state[field] & sample_mask[:, None]
                    speed_name, slip_name = prefix + "contact_foot_horizontal_speed_m_s", prefix + "foot_slip_fraction"
                    statistics[speed_name] = statistics.get(speed_name, 0) + torch.where(contact, foot_speed.double(), 0.0).sum(dim=1)
                    statistics[slip_name] = statistics.get(slip_name, 0) + ((foot_speed > limits["slip_speed_m_s"]) & contact).sum(dim=1)
                    counts[speed_name] = counts.get(speed_name, 0) + contact.sum(dim=1)
                    counts[slip_name] = counts[speed_name]
                peaks["peak_contact_force_n"] = max(peaks.get("peak_contact_force_n", 0), float(state["peak_contact_force_n"][valid].max()) if bool(valid.any()) else 0)
                peak_force_per_env = torch.where(valid, torch.maximum(peak_force_per_env, state["peak_contact_force_n"]), peak_force_per_env)
                last_velocity, last_acceleration = state["root_lin_vel_w"], acceleration
                last_actions, previous_action_delta = actions, action_delta
                last_angular_velocity = state["root_ang_vel_b"]
                if record_envs > 0 and step % record_stride == 0:
                    trace.append({"time_s": (step + 1) * dt, "env_ids": trace_ids.tolist(),
                                  "case_ids": case_ids[trace_ids].tolist(), "active": valid[trace_ids].tolist(),
                                  "root_relative_xyz": relative[trace_ids].tolist(),
                                  "root_linear_velocity_w": state["root_lin_vel_w"][trace_ids].tolist(),
                                  "yaw_roll_pitch": torch.stack((yaw, roll, pitch), dim=-1)[trace_ids].tolist(),
                                  "feet_relative_xyz": (state["feet_pos_w"] - origins[:, None])[trace_ids].tolist(),
                                  "foot_horizontal_speed_m_s": foot_speed[trace_ids].tolist(),
                                  "contacts": state["foot_contacts"][trace_ids].tolist(),
                                  "current_sample_contacts": state["current_foot_contacts"][trace_ids].tolist(),
                                  "actions": actions[trace_ids].tolist(),
                                  "action_delta_rms": action_delta.square().mean(-1).sqrt()[trace_ids].tolist(),
                                  "action_second_delta_rms": action_second.square().mean(-1).sqrt()[trace_ids].tolist(),
                                  "flight_paused": paused[trace_ids].tolist(),
                                  "base_force_n": state["base_force_n"][trace_ids].tolist(),
                                  "shank_force_n": state["shank_force_n"][trace_ids].tolist(),
                                  "current_sample_base_force_n": state["current_base_force_n"][trace_ids].tolist(),
                                  "current_sample_shank_force_n": state["current_shank_force_n"][trace_ids].tolist(),
                                  "leg_current_normal_force_norm_n": state["leg_current_normal_force_norm_n"][trace_ids].tolist(),
                                  "leg_history_peak_normal_force_norm_n": state["leg_history_peak_normal_force_norm_n"][trace_ids].tolist(),
                                  **{name: value[trace_ids].tolist() if value is not None else None
                                     for name, value in capture.leg_trace_telemetry.items()},
                                  "command_vx_vy_yaw": torch.stack((yaw_command * 0 + speed, yaw_command * 0, yaw_command), -1)[trace_ids].tolist()})
                active &= ~(complete | falls | escapes | stalls | nonfinite | dones.bool())
                if progress is not None and ((step + 1) % 200 == 0 or not bool(active.any())):
                    progress({"seed": seed, "step": step + 1, "num_steps": steps, "zero_action": zero_action,
                              "completed": int(complete.sum()), "falls": int(falls.sum()),
                              "stalls": int(stalls.sum()), "lateral_escapes": int(escapes.sum())})
                if bool(nonfinite.any()):
                    failure_reason = "non_finite_physics_or_reward"
                    break

            def metric_summary(mask):
                metrics = {name: float(value[mask].sum() / counts[name][mask].sum())
                           if int(counts[name][mask].sum()) else None for name, value in statistics.items()}
                for source, target in (("xy_tracking_mse", "xy_tracking_rmse_m_s"), ("roll_mse", "roll_rms_rad"),
                                   ("pitch_mse", "pitch_rms_rad"), ("linear_acceleration_squared", "linear_acceleration_rms_m_s2"),
                                   ("linear_jerk_squared", "linear_jerk_rms_m_s3"),
                                   ("body_angular_acceleration_squared", "body_angular_acceleration_rms_rad_s2"),
                                   ("action_delta_squared", "action_delta_rms"),
                                   ("action_second_delta_squared", "action_second_delta_rms"),
                                   ("applied_torque_squared", "applied_torque_rms_nm")):
                    mean = metrics.pop(source, None)
                    metrics[target] = math.sqrt(mean) if mean is not None else None
                return metrics

            def contact_sample_counts(mask):
                return {target: int(counts[source][mask].sum()) if source in counts else 0
                        for source, target in (("base_contact_step_fraction", "environment_samples"),
                            ("contact_foot_horizontal_speed_m_s", "history_contact_foot_samples"),
                            ("current_sample_contact_foot_horizontal_speed_m_s", "current_contact_foot_samples"))}

            metrics = metric_summary(torch.ones_like(active))
            completion_fraction = float(complete.float().mean())
            successful_times = completion_time[complete]
            goal_distance = geometry["goal_x"] - geometry["start_x"]
            case_summaries = []
            for index, case_geometry in enumerate(case_geometries):
                mask = case_ids == index
                case_n = int(mask.sum())
                fraction = float(complete[mask].float().mean()) if case_n else 0.0
                case_summaries.append({"case_index": index, "geometry": case_geometry, "num_envs": case_n,
                    "passed": case_n >= limits["minimum_num_envs"] and fraction >= limits["completion_fraction"] and failure_reason is None,
                    "completion_fraction": fraction, "completions": int(complete[mask].sum()),
                    "falls": int(falls[mask].sum()), "stalls": int(stalls[mask].sum()),
                    "lateral_escapes": int(escapes[mask].sum()), "base_contact_envs": int(base_contact[mask].sum()),
                    "current_sample_base_contact_envs": int(current_base_contact[mask].sum()),
                    "current_sample_shank_contact_envs": int(current_shank_contact[mask].sum()),
                    "contact_sample_counts": contact_sample_counts(mask),
                    "metrics": {**metric_summary(mask),
                        "peak_contact_force_n": float(peak_force_per_env[mask].max()) if case_n else None,
                        "roll_peak_rad": float(roll_peak_per_env[mask].max()) if case_n else None,
                        "longest_flight_pause_s": float(longest_pause[mask].max()) if case_n else None},
                    "mean_max_progress_m": float(max_progress[mask].mean()) if case_n else None})
            initial_distribution = {"root_relative_xyz_min": initial_relative.amin(dim=0).tolist(),
                "root_relative_xyz_max": initial_relative.amax(dim=0).tolist(),
                "root_relative_xyz_std": initial_relative.std(dim=0, unbiased=False).tolist(),
                "yaw_range_rad": [float(initial_yaw.min()), float(initial_yaw.max())],
                "yaw_std_rad": float(initial_yaw.std(unbiased=False)),
                "root_quaternion_xyzw_min": initial["root_quat_w"].amin(dim=0).tolist(),
                "root_quaternion_xyzw_max": initial["root_quat_w"].amax(dim=0).tolist()}
            trials.append({
                "seed": seed, "num_envs": n, "executed_steps": executed, "requested_duration_s": seconds,
                "passed": all(case["passed"] for case in case_summaries),
                "completion_fraction": completion_fraction, "completions": int(complete.sum()),
                "falls": int(falls.sum()), "stalls": int(stalls.sum()), "lateral_escapes": int(escapes.sum()),
                "timeouts_before_completion": int((timeouts & ~complete).sum()), "nonfinite_envs": int(nonfinite.sum()),
                "invalid_physics_envs": int(invalid_physics.sum()),
                "base_contact_envs": int(base_contact.sum()), "shank_contact_envs": int(shank_contact.sum()),
                "current_sample_base_contact_envs": int(current_base_contact.sum()),
                "current_sample_shank_contact_envs": int(current_shank_contact.sum()),
                "contact_sample_counts": contact_sample_counts(torch.ones_like(active)),
                "invalid_start_envs": int((~start_valid).sum()),
                "mean_completion_time_s": float(successful_times.mean()) if successful_times.numel() else None,
                "mean_max_directed_progress_m": float(max_progress.mean()),
                "mean_max_progress_fraction": float((max_progress / goal_distance).clamp(0, 1).mean()),
                "mean_first_episode_measured_duration_s": float(active_steps.float().mean()) * dt,
                "metrics": {**metrics, **peaks, "roll_peak_rad": float(roll_peak_per_env.max()),
                            "longest_flight_pause_s": float(longest_pause.max())}, "failure_reason": failure_reason,
                "per_env": {"completed": complete.tolist(), "fall": falls.tolist(), "stall": stalls.tolist(),
                            "lateral_escape": escapes.tolist(), "max_progress_m": max_progress.tolist(),
                            "max_progress_definition": "maximum forward displacement from this environment's initial reset position",
                            "initial_root_relative_xyz_m": initial_relative.tolist(),
                            "maximum_root_relative_x_m": (initial_relative[:, 0] + max_progress).tolist(),
                            "last_measured_root_relative_xyz_m": last_measured_relative.tolist(),
                            "last_measured_feet_relative_xyz_m": last_measured_feet.tolist(),
                            "first_episode_measured_duration_s": (active_steps * dt).tolist(),
                            "longest_flight_pause_s": longest_pause.tolist(),
                            "completion_time_s": [float(x) if math.isfinite(float(x)) else None for x in completion_time]},
                "trace": trace, "cases": case_summaries, "initial_reset_distribution": initial_distribution,
            })

    return {
        "status": "passed" if all(trial["passed"] for trial in trials) else "failed",
        "passed": all(trial["passed"] for trial in trials), "geometry": original_geometry, "thresholds": limits,
        "controller": "zero_action" if zero_action else "HIM_policy", "trials": trials,
        "foot_body_names": capture.foot_body_names,
        "leg_body_names": capture.leg_body_names,
        "leg_force_trace_scope": "per-leg arrays follow leg_body_names in robot body order, matched to sensor names; current policy-boundary normal-force norm and retained-history peak norm; sparse traces do not measure contact duration",
        "leg_trace_telemetry": capture.leg_trace_metadata,
        "heading_control": {"enabled": heading_control, "target_yaw_rad": 0.0, "gain": heading_gain,
                            "maximum_yaw_rate_rad_s": max_yaw_rate,
                            "inputs": "root yaw only; standard velocity-command channels"},
        "randomized_reset": bool(randomized), "command_forward_speed_m_s": speed,
        "dynamics_randomized": bool(dynamics_randomized),
        "metrics_scope": "first episode until completion/fall/stall/escape/timeout; physics captured before auto-reset; smoothness excludes first second",
        "contact_sampling": contact_sampling,
        "slip_metric_scope": "foot-link horizontal speed gated by retained normal-contact history peaks >1N; cadence is in contact_sampling; proxy, not contact-point tangential slip",
        "current_sample_slip_metric_scope": "foot-link horizontal speed gated only by latest normal-contact force >1N at the same policy boundary; proxy, not contact-point tangential slip",
        "smoothness_passed": None,
        "smoothness_note": "Metrics are reported for comparison; no universal smoothness threshold has been calibrated",
        "seed_scope": (
            "reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds; enabled reset-mode dynamics events (such as actuator gains) resample on resets"
            if dynamics_randomized else
            "reset RNG seeds; startup terrain/material/dynamics are sampled once at environment construction and fixed across reset seeds; mass/COM/gain evaluation randomization is disabled"
        ),
        "validation_scope": "randomized reset cases" if randomized else "nominal deterministic repeated environments; not independent robustness trials",
        "independent_reset_validation_eligible": bool(randomized and len(set(seeds)) >= 3
            and all(trial["initial_reset_distribution"]["yaw_std_rad"] > 1e-6 for trial in trials)),
    }


def evaluate_stair_suite(wrapped, policy, geometry, seconds=30.0, speed=0.3, seeds=(1,),
                         randomized=False, include_zero_action=True, heading_control=True,
                         thresholds=None, progress=None, **kwargs):
    """Evaluate one frozen geometry with repeated seeded first episodes and control."""
    seeds = tuple(seeds)
    learned = evaluate_stairs(wrapped, policy, geometry, seconds, speed, seeds, randomized,
                             heading_control=heading_control, thresholds=thresholds, progress=progress, **kwargs)
    control = evaluate_stairs(wrapped, policy, geometry, seconds, speed, seeds, randomized,
                             zero_action=True, heading_control=heading_control, thresholds=thresholds,
                             progress=progress, **kwargs) if include_zero_action else None
    return {"status": learned["status"], "passed": learned["passed"], "policy": learned,
            "zero_action": control, "geometry": geometry,
            "completion_improvement_fraction": sum(trial["completion_fraction"] for trial in learned["trials"]) / len(seeds)
                - sum(trial["completion_fraction"] for trial in control["trials"]) / len(seeds) if control else None}


def assess_final(report, completion_fraction=0.95, maximum_failure_fraction=0.05,
                 maximum_flight_pause_s=1.0):
    """Apply the separately declared final gate without changing training metrics.

    Long pauses are a motion-quality flag. A final ``silky/smooth`` assertion
    still needs video and comparison with an otherwise matching baseline.
    """
    policy = report.get("policy", report)
    checks = []
    for trial in policy["trials"]:
        for case in trial.get("cases", [trial]):
            n = case["num_envs"]
            failures = {name: case[name] / n if n else 1.0
                        for name in ("falls", "stalls", "lateral_escapes")}
            traversed = (case["completion_fraction"] >= completion_fraction
                         and n >= policy.get("thresholds", DEFAULT_THRESHOLDS)["minimum_num_envs"]
                         and all(value <= maximum_failure_fraction for value in failures.values())
                         and case.get("base_contact_envs", 0) == 0
                         and trial.get("failure_reason") is None)
            pause = case["metrics"].get("longest_flight_pause_s")
            checks.append({"seed": trial["seed"], "case_index": case.get("case_index", 0),
                           "traversal_passed": traversed, "failure_fractions": failures,
                           "motion_improvement_needed": pause is not None and pause > maximum_flight_pause_s})
    return {"traversal_passed": all(check["traversal_passed"] for check in checks),
            "motion_improvement_needed": any(check["motion_improvement_needed"] for check in checks),
            "smoothness_verified": False, "visual_review_required": True, "cases": checks,
            "thresholds": {"completion_fraction": completion_fraction,
                           "maximum_failure_fraction": maximum_failure_fraction,
                           "maximum_flight_pause_s_for_motion_flag": maximum_flight_pause_s,
                           "maximum_base_contact_envs": 0}}
