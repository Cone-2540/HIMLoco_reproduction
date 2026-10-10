"""Controlled flat-ground checks for the Isaac Lab HIM adapter.

Metrics use only the first episode of each environment, including its pre-reset
terminal velocity. Auto-reset episodes must not hide a fall or inflate survival.
"""

import math

import torch


DEFAULT_THRESHOLDS = {
    "xy_mae_m_s": 0.2,
    "yaw_mae_rad_s": 0.3,
    "first_episode_survival_fraction": 0.95,
    "minimum_duration_s": 20.0,
    "minimum_num_envs": 64,
}


def _fixed_command(command_cfg, command, duration_s):
    command_cfg.heading_command = False
    command_cfg.rel_heading_envs = 0.0
    command_cfg.rel_standing_envs = 0.0
    command_cfg.debug_vis = False
    command_cfg.resampling_time_range = (duration_s + 1.0, duration_s + 1.0)
    command_cfg.ranges.lin_vel_x = (float(command[0]), float(command[0]))
    command_cfg.ranges.lin_vel_y = (float(command[1]), float(command[1]))
    command_cfg.ranges.ang_vel_z = (float(command[2]), float(command[2]))
    command_cfg.ranges.heading = None


def configure_evaluation(cfg, command=(0.5, 0.0, 0.0), duration_s=20.0, *, seconds=None):
    """Configure before creating the simulator; preserve training reward/actuators.

Startup mass/COM randomization is removed, material coefficients stay fixed,
and every reset uses the nominal pose with zero root and joint velocity.
"""
    if seconds is not None:
        duration_s = seconds
    if cfg.scene.terrain.terrain_type != "plane":
        raise ValueError("Controlled evaluation requires plane terrain")
    cfg.episode_length_s = float(duration_s)
    cfg.compute_final_obs = True
    cfg.observations.policy.enable_corruption = False
    cfg.observations.critic.enable_corruption = False
    for name in ("push_robot", "add_base_mass", "base_com"):
        if hasattr(cfg.events, name):
            setattr(cfg.events, name, None)
    root = cfg.events.reset_base.params
    root["pose_range"] = {key: (0.0, 0.0) for key in ("x", "y", "z", "roll", "pitch", "yaw")}
    root["velocity_range"] = {key: (0.0, 0.0) for key in ("x", "y", "z", "roll", "pitch", "yaw")}
    cfg.events.reset_robot_joints.params["position_range"] = (1.0, 1.0)
    cfg.events.reset_robot_joints.params["velocity_range"] = (0.0, 0.0)
    if getattr(cfg.events, "base_external_force_torque", None) is not None:
        cfg.events.base_external_force_torque.params["force_range"] = (0.0, 0.0)
        cfg.events.base_external_force_torque.params["torque_range"] = (0.0, 0.0)
    _fixed_command(cfg.commands.base_velocity, command, duration_s)
    return cfg


def _tensor(value):
    # Lab 3 exposes asset arrays through .torch; mocks/older APIs may use tensors.
    return value if isinstance(value, torch.Tensor) else value.torch


def _physics_state(wrapped):
    data = wrapped.env.scene["robot"].data
    state = {
        name: _tensor(getattr(data, name))
        for name in (
            "root_pos_w", "root_lin_vel_b", "root_ang_vel_b",
            "projected_gravity_b", "joint_pos", "joint_vel",
        )
    }
    return state


@torch.inference_mode()
def _set_command_and_reset(wrapped, command, duration_s, seed):
    # The previous rollout's history was allocated in inference mode. Reset
    # mutates that history, so every case reset must use the same mode too.
    term = wrapped.env.command_manager.get_term("base_velocity")
    _fixed_command(term.cfg, command, duration_s)
    if hasattr(wrapped.env, "seed"):
        wrapped.env.seed(seed)
    torch.manual_seed(seed)
    wrapped.reset()
    # Disable even the measure-zero standing draw, and set a fixed runtime target.
    term.vel_command_b[:] = torch.tensor(command, device=wrapped.device)
    term.is_standing_env.zero_()
    term.is_heading_env.zero_()
    # Observations from reset already contain this target through fixed ranges.
    # Overwrite the known command slice to guarantee exact deterministic input.
    wrapped.obs_buf[:, :3] = torch.tensor(command, device=wrapped.device) * torch.tensor(
        (2.0, 2.0, 0.25), device=wrapped.device
    )
    wrapped.privileged_obs_buf[:, :3] = wrapped.obs_buf[:, :3]


def _evaluate_case(wrapped, policy, command, num_steps, warmup_steps, seed, zero_action, thresholds, progress):
    device, n = wrapped.device, wrapped.num_envs
    dt = float(wrapped.env.step_dt)
    duration_s = num_steps * dt
    _set_command_and_reset(wrapped, command, duration_s, seed)
    active = torch.ones(n, dtype=torch.bool, device=device)
    first_fall = torch.zeros(n, dtype=torch.bool, device=device)
    first_timeout = torch.zeros_like(first_fall)
    first_steps = torch.zeros(n, dtype=torch.long, device=device)
    sample_count = torch.zeros(n, dtype=torch.long, device=device)
    xy_sum = torch.zeros(n, device=device, dtype=torch.float64)
    xy_sq_sum = torch.zeros_like(xy_sum)
    yaw_sum = torch.zeros_like(xy_sum)
    yaw_sq_sum = torch.zeros_like(xy_sum)
    velocity_sum = torch.zeros(n, 3, device=device, dtype=torch.float64)
    height_sum = torch.zeros((), device=device, dtype=torch.float64)
    height_sample_count = torch.zeros((), device=device, dtype=torch.long)
    nominal_height_count = torch.zeros_like(height_sample_count)
    upright_count = torch.zeros_like(height_sample_count)
    command_tensor = torch.tensor(command, device=device)
    failure_reasons = []
    all_falls = all_timeouts = executed_steps = 0
    minimum_height, maximum_height = float("inf"), -float("inf")

    with torch.inference_mode():
        for step in range(num_steps):
            if zero_action:
                actions = torch.zeros(n, wrapped.num_actions, device=device)
            else:
                actions = policy(wrapped.get_observations())
            if not torch.isfinite(actions).all():
                failure_reasons.append("non_finite_actions")
                break
            _, critic, rewards, dones, infos, ids, terminal = wrapped.step(actions)
            executed_steps = step + 1
            # The adapter returns reset observations. Replace ended rows with
            # their pre-reset critic so reset-to-zero does not bias tracking.
            current = critic.clone()
            current[ids] = terminal
            finite = bool(torch.isfinite(current).all() and torch.isfinite(rewards).all())
            state = _physics_state(wrapped)
            finite = finite and all(bool(torch.isfinite(value).all()) for value in state.values())
            if not finite:
                failure_reasons.append("non_finite_observation_reward_or_physics")
                break
            height = state["root_pos_w"][:, 2]
            minimum_height = min(minimum_height, float(height.min()))
            maximum_height = max(maximum_height, float(height.max()))
            # Plane origin is z=0: guard against finite but invalid runaway physics.
            if bool(((height < -1.0) | (height > 2.0)).any()):
                failure_reasons.append("root_height_outside_flat_physics_bounds")
                break

            timeouts = infos["time_outs"].bool()
            # Read the independent termination signal so a fall on the timeout
            # step counts as a fall instead of being mistaken for survival.
            terminated = infos.get("terminated", getattr(wrapped.env, "reset_terminated", None))
            if terminated is None:
                terminated = dones.bool() & ~timeouts
            else:
                terminated = _tensor(terminated).bool()
            all_falls += int(terminated.sum())
            all_timeouts += int(timeouts.sum())
            first_steps += active.long()
            velocity = torch.cat((current[:, 45:47] / 2.0, current[:, 5:6] / 0.25), dim=-1)
            if step >= warmup_steps:
                error = velocity - command_tensor
                xy_error = torch.linalg.vector_norm(error[:, :2], dim=-1).double()
                yaw_error = error[:, 2].abs().double()
                xy_sum += torch.where(active, xy_error, 0.0)
                xy_sq_sum += torch.where(active, xy_error.square(), 0.0)
                yaw_sum += torch.where(active, yaw_error, 0.0)
                yaw_sq_sum += torch.where(active, yaw_error.square(), 0.0)
                velocity_sum += torch.where(active[:, None], velocity.double(), 0.0)
                sample_count += active.long()
                # Gravity is available in the pre-reset terminal critic. Root
                # height is only available after step/reset, so omit done rows
                # from height metrics instead of measuring the reset posture.
                upright_count += (active & (current[:, 8] < -0.8)).sum()
                height_valid = active & ~dones.bool()
                height_sum += torch.where(height_valid, height.double(), 0.0).sum()
                height_sample_count += height_valid.sum()
                nominal_height_count += (height_valid & (height > 0.2) & (height < 0.6)).sum()
            first_fall |= active & terminated
            first_timeout |= active & timeouts
            active &= ~dones.bool()
            if progress is not None and ((step + 1) % 200 == 0 or step + 1 == num_steps):
                progress({"command": list(command), "zero_action": zero_action, "step": step + 1,
                          "num_steps": num_steps, "first_episode_falls": int(first_fall.sum())})

    count = int(sample_count.sum())
    height_count = int(height_sample_count)
    xy_mae = float(xy_sum.sum() / count) if count else None
    xy_rmse = math.sqrt(float(xy_sq_sum.sum() / count)) if count else None
    yaw_mae = float(yaw_sum.sum() / count) if count else None
    yaw_rmse = math.sqrt(float(yaw_sq_sum.sum() / count)) if count else None
    # Survive the full requested duration, including startup and terminal step.
    survived = ~first_fall & (first_steps >= num_steps)
    survival_fraction = float(survived.float().mean())
    sample_eligible = (n >= thresholds["minimum_num_envs"]
                       and duration_s + 1e-6 >= thresholds["minimum_duration_s"]
                       and executed_steps == num_steps)
    tracking_passed = (xy_mae is not None and xy_mae < thresholds["xy_mae_m_s"]
                       and yaw_mae < thresholds["yaw_mae_rad_s"])
    passed = (sample_eligible and not failure_reasons and tracking_passed
              and survival_fraction >= thresholds["first_episode_survival_fraction"])
    return {
        "command_m_s_m_s_rad_s": [float(value) for value in command],
        "controller": "zero_action" if zero_action else "HIM_policy",
        "passed": bool(passed), "sample_eligible": sample_eligible,
        "num_envs": n, "requested_duration_s": duration_s,
        "executed_steps": executed_steps, "warmup_steps": warmup_steps,
        "tracking_samples": count, "tracking_env_count": int((sample_count > 0).sum()),
        "xy_mae_m_s": xy_mae, "xy_rmse_m_s": xy_rmse,
        "yaw_mae_rad_s": yaw_mae, "yaw_rmse_rad_s": yaw_rmse,
        "mean_measured_vx_vy_yaw": (velocity_sum.sum(0) / count).tolist() if count else None,
        "mean_root_height_m": float(height_sum / height_count) if height_count else None,
        "nominal_height_fraction": float(nominal_height_count / height_count) if height_count else None,
        "upright_fraction": float(upright_count / count) if count else None,
        "height_tracking_samples": height_count,
        "posture_metrics_scope": "first episode after warmup; gravity_z < -0.8 includes terminal critic; "
                                 "0.2 < height < 0.6 and mean height omit auto-reset terminal rows",
        "first_episode_survival_fraction": survival_fraction,
        "first_episode_falls": int(first_fall.sum()),
        "first_episode_timeouts": int(first_timeout.sum()),
        "all_episode_falls": all_falls, "all_episode_timeouts": all_timeouts,
        "mean_first_episode_duration_s": float(first_steps.float().mean()) * dt,
        "minimum_root_height_m": minimum_height if math.isfinite(minimum_height) else None,
        "maximum_root_height_m": maximum_height if math.isfinite(maximum_height) else None,
        "finite_physics": not any(reason.startswith("non_finite") for reason in failure_reasons),
        "failure_reasons": failure_reasons,
    }


def evaluate(wrapped, policy, num_steps=None, warmup_steps=100,
             commands=((0.5, 0.0, 0.0),), include_zero_action=True, seed=1,
             thresholds=None, progress=None):
    """Evaluate fixed commands and an optional zero-action control from fresh resets.

    Call configure_evaluation before env construction. XY MAE is the mean
    Euclidean speed error; XY RMSE is sqrt(mean(||error_xy||**2)). Only the
    first episode contributes samples, so repeated resets cannot mask falls.
    Passing requires >=64 envs, >=20 seconds and at least one moving command.
    The 2-second default warmup affects tracking only; survival includes startup.
    """
    thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    if num_steps is None:
        num_steps = math.ceil(thresholds["minimum_duration_s"] / float(wrapped.env.step_dt))
    if num_steps <= 0 or not 0 <= warmup_steps < num_steps:
        raise ValueError("Require num_steps > warmup_steps >= 0")
    commands = [tuple(float(value) for value in command) for command in commands]
    if not commands or any(len(command) != 3 or not all(math.isfinite(x) for x in command) for command in commands):
        raise ValueError("commands must contain finite (vx, vy, yaw) triples")
    cases, controls, comparisons = [], [], []
    for command in commands:
        cases.append(_evaluate_case(wrapped, policy, command, num_steps, warmup_steps, seed,
                                    False, thresholds, progress))
        if include_zero_action:
            controls.append(_evaluate_case(wrapped, policy, command, num_steps, warmup_steps, seed,
                                           True, thresholds, progress))
            learned, control = cases[-1], controls[-1]
            comparisons.append({
                "command_m_s_m_s_rad_s": list(command),
                "xy_mae_improvement_m_s": (control["xy_mae_m_s"] - learned["xy_mae_m_s"])
                    if learned["xy_mae_m_s"] is not None and control["xy_mae_m_s"] is not None else None,
                "yaw_mae_improvement_rad_s": (control["yaw_mae_rad_s"] - learned["yaw_mae_rad_s"])
                    if learned["yaw_mae_rad_s"] is not None and control["yaw_mae_rad_s"] is not None else None,
            })
    moving_command = any(any(abs(value) >= 0.1 for value in command) for command in commands)
    passed = moving_command and all(case["passed"] for case in cases)
    return {
        "status": "passed" if passed else "failed", "passed": bool(passed),
        "thresholds": thresholds,
        "metrics_scope": "first episode only; pre-reset terminal velocities; survival includes warmup",
        "moving_command_tested": moving_command,
        "cases": cases, "zero_action_cases": controls, "baseline_comparison": comparisons,
    }


def evaluate_suite(wrapped, policy, seconds=20.0,
                   commands=((0.5, 0.0, 0.0), (-0.5, 0.0, 0.0),
                             (0.0, 0.3, 0.0), (0.0, 0.0, 0.5)),
                   warmup_s=2.0, include_zero_action=True, seed=1,
                   thresholds=None, progress=None):
    """Run forward/backward/lateral/turn commands with matching zero-action controls.

    Supply ``commands=((0.5, 0, 0),)`` for the initial forward-only check.
    """
    dt = float(wrapped.env.step_dt)
    return evaluate(wrapped, policy, num_steps=math.ceil(seconds / dt),
                    warmup_steps=math.ceil(warmup_s / dt), commands=commands,
                    include_zero_action=include_zero_action, seed=seed,
                    thresholds=thresholds, progress=progress)
