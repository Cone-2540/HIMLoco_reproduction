"""Run original HIMLoco learning with Isaac Lab 3 / Unitree Go2 physics."""

import argparse
import copy
import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import warp as wp

wp.config.enable_backward = False

import gymnasium as gym
import torch
from isaaclab.app import add_launcher_args, launch_simulation
from isaaclab.managers import ObservationGroupCfg, ObservationTermCfg
from isaaclab.utils import configclass
from isaaclab.utils.noise import UniformNoiseCfg
import isaaclab_tasks
from isaaclab_tasks.utils import resolve_task_config

sys.path.insert(0, str(Path(__file__).parent / "vendor"))
from him_rsl_rl.runners.him_on_policy_runner import HIMOnPolicyRunner
from adapter import HIMVecEnv

MDP = "isaaclab.envs.mdp:"


@configclass
class PolicyObservations(ObservationGroupCfg):
    velocity_commands = ObservationTermCfg(func=MDP + "generated_commands", params={"command_name": "base_velocity"}, scale=(2.0, 2.0, 0.25))
    base_ang_vel = ObservationTermCfg(func=MDP + "base_ang_vel", scale=0.25, noise=UniformNoiseCfg(n_min=-0.2, n_max=0.2))
    projected_gravity = ObservationTermCfg(func=MDP + "projected_gravity", noise=UniformNoiseCfg(n_min=-0.05, n_max=0.05))
    joint_pos = ObservationTermCfg(func=MDP + "joint_pos_rel", noise=UniformNoiseCfg(n_min=-0.01, n_max=0.01))
    joint_vel = ObservationTermCfg(func=MDP + "joint_vel_rel", scale=0.05, noise=UniformNoiseCfg(n_min=-1.5, n_max=1.5))
    actions = ObservationTermCfg(func=MDP + "last_action")
    enable_corruption = True
    concatenate_terms = True


@configclass
class CriticObservations(PolicyObservations):
    base_lin_vel = ObservationTermCfg(func=MDP + "base_lin_vel", scale=2.0)
    enable_corruption = False


@configclass
class HIMObservations:
    policy = PolicyObservations()
    critic = CriticObservations()


class ExportPolicy(torch.nn.Module):
    def __init__(self, actor_critic):
        super().__init__()
        self.encoder = actor_critic.estimator.encoder
        self.actor = actor_critic.actor

    def forward(self, history: torch.Tensor) -> torch.Tensor:
        estimate = self.encoder(history)
        velocity = estimate[:, :3]
        latent = torch.nn.functional.normalize(estimate[:, 3:], dim=-1)
        return self.actor(torch.cat((history[:, :45], velocity, latent), dim=-1))


def export_and_verify(model, sample, log_dir):
    model.eval()
    sample = sample[:8].clone()
    with torch.inference_mode():
        expected = model.act_inference(sample).cpu()
    export = torch.jit.script(copy.deepcopy(ExportPolicy(model)).cpu().eval())
    export.save(str(log_dir / "policy.pt"))
    with torch.inference_mode():
        actual = torch.jit.load(str(log_dir / "policy.pt"))(sample.cpu())
    torch.testing.assert_close(actual, expected, atol=1e-5, rtol=1e-5)
    return (actual - expected).abs().max().item()


def train_config(steps):
    return {
        "runner": {"policy_class_name": "HIMActorCritic", "algorithm_class_name": "HIMPPO", "num_steps_per_env": steps, "save_interval": 20},
        "policy": {"actor_hidden_dims": [512, 256, 128], "critic_hidden_dims": [512, 256, 128], "activation": "elu", "init_noise_std": 1.0},
        "algorithm": {"value_loss_coef": 1.0, "use_clipped_value_loss": True, "clip_param": 0.2, "entropy_coef": 0.01, "num_learning_epochs": 5, "num_mini_batches": 4, "learning_rate": 1e-3, "schedule": "adaptive", "gamma": 0.99, "lam": 0.95, "desired_kl": 0.01, "max_grad_norm": 1.0},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, conflict_handler="resolve")
    parser.add_argument("mode", choices=["train", "play", "evaluate"])
    parser.add_argument("--num_envs", type=int, default=1024)
    parser.add_argument("--max_iterations", type=int, default=1000)
    parser.add_argument("--steps_per_env", type=int, default=100)
    parser.add_argument("--play_steps", type=int, default=500)
    parser.add_argument("--terrain", choices=["flat", "rough", "stairs"], default="flat")
    parser.add_argument("--stair_stage", choices=["easy", "standard", "hard"], default="easy")
    parser.add_argument("--stair_height", type=float)
    parser.add_argument("--stair_depth", type=float, default=0.27)
    parser.add_argument("--stair_nosing", type=float, default=0.0)
    parser.add_argument("--stair_direction", choices=["asc", "desc"], default="asc")
    parser.add_argument("--reward_profile", choices=["faithful", "tuned", "stock"], default="faithful")
    parser.add_argument("--speed", type=float, default=0.3)
    parser.add_argument("--eval_seed", type=int, action="append")
    parser.add_argument("--eval_randomized", action="store_true")
    parser.add_argument("--friction", type=float, nargs=2, metavar=("STATIC", "DYNAMIC"))
    parser.add_argument("--start_level", type=int, default=0)
    parser.add_argument("--stair_pushes", action="store_true")
    parser.add_argument("--stair_batch", type=Path, help="JSON list of fixed evaluation stair specifications.")
    parser.add_argument("--domain_profile", choices=["none", "basic", "robust"], default="none")
    parser.add_argument("--conservative_calf", action="store_true")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--warm_start", choices=["reset", "expand"],
                        help="Explicit actor/HIM transfer with fresh optimizers; reset or extend critic.")
    parser.add_argument("--learning_rate", type=float, default=1e-3)
    parser.add_argument("--lr_schedule", choices=["adaptive", "fixed"], default="adaptive")
    parser.add_argument("--entropy_coef", type=float, default=0.01)
    parser.add_argument("--save_interval", type=int, default=20)
    parser.add_argument("--run_name", default="smoke")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--turn_fraction", type=float, default=0.0,
                        help="Training command fraction with zero XY and random yaw; 0 preserves stock sampling.")
    parser.add_argument("--eval_seconds", type=float, default=20.0)
    parser.add_argument("--command", type=float, nargs=3, action="append", metavar=("VX", "VY", "YAW"),
                        help="Fixed command; repeat to choose evaluation cases.")
    parser.add_argument("--video", action="store_true", help="Record a headless Kit camera clip.")
    parser.add_argument("--video_length", type=int, default=500)
    parser.add_argument("--shutdown_timeout", type=float, default=30.0,
                        help="After results are saved, exit if Isaac Sim teardown hangs; 0 disables.")
    add_launcher_args(parser)
    args = parser.parse_args()
    args.physics = "isaacsim_physx"
    args.device = "cuda:0"
    if not 0 <= args.turn_fraction <= 1:
        parser.error("--turn_fraction must be between 0 and 1")
    if not torch.cuda.is_available():
        raise RuntimeError("This entry point requires CUDA in the existing Isaac Lab container")
    torch.manual_seed(args.seed)
    task = "Isaac-Velocity-" + ("Rough" if args.terrain == "stairs" else args.terrain.title()) + "-UnitreeGo2"
    cfg, _ = resolve_task_config(task, "", overrides=["physics=isaacsim_physx"])
    cfg.scene.num_envs = args.num_envs
    cfg.seed = args.seed
    cfg.sim.device = args.device
    cfg.sim.use_newton_actuators = False
    source_usd = cfg.scene.robot.spawn.usd_path
    shared_usd = Path("/workspace/isaaclab/data_storage/assets/isaaclab6.1/Go2/go2.usd")
    if shared_usd.is_file():
        # Pin the already downloaded asset, avoiding remote stat timeouts on
        # every short diagnostic run. Relative USD dependencies stay together.
        cfg.scene.robot.spawn.usd_path = str(shared_usd)
    cfg.compute_final_obs = True
    cfg.observations = HIMObservations()
    cfg.scene.terrain.visual_material = None
    cfg.scene.sky_light.spawn.texture_file = None
    cfg.commands.base_velocity.debug_vis = False
    if args.mode == "train" and args.turn_fraction > 0:
        cfg.commands.base_velocity.turn_fraction = args.turn_fraction
    # Add privileged terrain samples only to the critic.
    if args.terrain in ("rough", "stairs"):
        from isaaclab.managers import SceneEntityCfg
        cfg.observations.critic.height_scan = ObservationTermCfg(func=MDP + "height_scan", params={"sensor_cfg": SceneEntityCfg("height_scanner")}, scale=5.0, clip=(-1.0, 1.0))
    stair_manifest = reward_manifest = domain_manifest = calf_manifest = None
    if args.terrain == "stairs":
        from stair_terrain import configure_stair_terrain, configure_stair_batch
        from stair_rewards import configure_stair_rewards
        spec = None
        if args.mode != "train" or args.stair_height is not None:
            spec = {"height": args.stair_height if args.stair_height is not None else 0.16,
                    "depth": args.stair_depth, "direction": args.stair_direction, "nosing": args.stair_nosing}
        if args.stair_batch:
            if args.mode == "train":
                parser.error("--stair_batch is for frozen evaluation/play scenes")
            specs = json.loads(args.stair_batch.read_text())
            stair_manifest = configure_stair_batch(cfg, specs, seed=args.seed)
        else:
            stair_manifest = configure_stair_terrain(cfg, args.stair_stage, spec=spec, seed=args.seed,
                                                     num_rows=10 if spec is None else 2, num_cols=24 if spec is None else 4)
        cfg.scene.terrain.max_init_terrain_level = args.start_level
        reward_manifest = configure_stair_rewards(cfg, args.reward_profile)
        cfg.episode_length_s = max(args.eval_seconds, 20.0)
        cfg.commands.base_velocity.heading_command = True
        cfg.commands.base_velocity.rel_heading_envs = 1.0
        cfg.commands.base_velocity.rel_standing_envs = 0.0
        cfg.commands.base_velocity.ranges.lin_vel_x = (0.2, 0.6)
        cfg.commands.base_velocity.ranges.lin_vel_y = (-0.03, 0.03)
        cfg.commands.base_velocity.ranges.ang_vel_z = (-0.5, 0.5)
        cfg.commands.base_velocity.ranges.heading = (0.0, 0.0)
        cfg.events.reset_base.params["pose_range"] = {"x": (-0.15, 0.15), "y": (-0.12, 0.12), "yaw": (-0.15, 0.15)}
        cfg.events.reset_base.params["velocity_range"] = {key: (0., 0.) for key in ("x", "y", "z", "roll", "pitch", "yaw")}
        cfg.events.reset_robot_joints.params["position_range"] = (0.85, 1.15)
        if not args.stair_pushes:
            cfg.events.push_robot = None
        cfg.events.base_com.params["com_range"] = {"x": (-0.02, 0.02), "y": (-0.02, 0.02), "z": (-0.01, 0.01)}
        if args.domain_profile != "none":
            from stair_randomization import configure_stair_randomization
            domain_manifest = configure_stair_randomization(cfg, args.domain_profile)
        if args.conservative_calf:
            from stair_randomization import configure_conservative_calf_limits
            calf_manifest = configure_conservative_calf_limits(cfg, args.mode)
    if args.friction:
        static, dynamic = args.friction
        if not 0 < dynamic <= static:
            parser.error("Require 0 < dynamic friction <= static friction")
        cfg.scene.terrain.physics_material.static_friction = 1.0
        cfg.scene.terrain.physics_material.dynamic_friction = 1.0
        cfg.events.physics_material.params["static_friction_range"] = (static, static)
        cfg.events.physics_material.params["dynamic_friction_range"] = (dynamic, dynamic)
    if args.mode in ("play", "evaluate"):
        if args.checkpoint is None:
            parser.error("play/evaluate requires --checkpoint")
        cfg.events.push_robot = None
        cfg.observations.policy.enable_corruption = False
    if args.terrain == "stairs" and args.mode in ("evaluate", "play"):
        from stair_evaluation import configure_stair_evaluation
        configure_stair_evaluation(cfg, stair_manifest["geometry"], seconds=args.eval_seconds,
                                  speed=args.speed, randomized=args.eval_randomized)
    elif args.mode == "evaluate":
        from evaluation import configure_evaluation
        configure_evaluation(cfg, seconds=args.eval_seconds)
    elif args.mode == "play" and args.command:
        from evaluation import configure_evaluation
        configure_evaluation(cfg, command=args.command[0], seconds=max(20.0, args.play_steps * cfg.sim.dt * cfg.decimation))
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d_%H-%M-%S")
    log_dir = Path(__file__).parent / "logs" / (stamp + "_" + args.run_name)
    log_dir.mkdir(parents=True, exist_ok=False)
    if args.video:
        if args.mode == "train":
            parser.error("Use video during play/evaluate")
        if getattr(args, "visualizer_explicit", False) and args.visualizer is None:
            parser.error("--video requires omitting --viz none")
        from isaaclab.envs.utils.video_recorder_cfg import VideoRecorderCfg
        from isaaclab_visualizers.kit import KitVisualizerCfg
        cfg.sim.visualizer_cfgs = [KitVisualizerCfg(
            headless=True, window_width=1280, window_height=720,
            eye=(2.4, 2.4, 1.7), lookat=(0.0, 0.0, 0.3),
            origin_type="asset", origin_env_index=0, origin_track_path="robot",
        )]
        cfg.video_recorders = [VideoRecorderCfg(
            source="visualizer:kit", output_dir=str(log_dir / "videos"),
            video_length=args.video_length, fps=50, output_filename_prefix="go2_flat",
        )]
        args.enable_cameras = True
    config = train_config(args.steps_per_env)
    config["algorithm"]["learning_rate"] = args.learning_rate
    config["algorithm"]["schedule"] = args.lr_schedule
    config["algorithm"]["entropy_coef"] = args.entropy_coef
    config["runner"]["save_interval"] = args.save_interval
    metadata = {"task": task, "seed": args.seed, "num_envs": args.num_envs, "train": config,
                "observation": "45 per frame, newest first, 6 frames; critic velocity at 45:48",
                "physics": "isaacsim_physx", "torch": torch.__version__, "cuda": torch.version.cuda,
                "gpu": torch.cuda.get_device_name(), "gpu_capability": torch.cuda.get_device_capability(),
                "python": sys.version, "algorithm_source": "vendored original HIMLoco at ef289ac",
                "mode": args.mode, "checkpoint": str(args.checkpoint) if args.checkpoint else None,
                "robot_usd": cfg.scene.robot.spawn.usd_path, "robot_usd_source": source_usd, "physics_dt": cfg.sim.dt,
                "policy_decimation": cfg.decimation, "episode_length_s": cfg.episode_length_s,
                "reward_weights": {name: term.weight for name, term in vars(cfg.rewards).items()
                                   if term is not None and hasattr(term, "weight")},
                "command_override": args.command, "evaluation_seconds": args.eval_seconds,
                "video": args.video, "training_turn_fraction": args.turn_fraction if args.mode == "train" else None}
    metadata.update({"terrain": args.terrain, "stairs": stair_manifest, "stair_reward": reward_manifest,
                     "domain_randomization": domain_manifest, "calf_limit_sensitivity": calf_manifest,
                     "friction_override": args.friction, "stair_pushes": args.stair_pushes,
                     "evaluation_seeds": args.eval_seed, "evaluation_randomized": args.eval_randomized})
    (log_dir / "config.json").write_text(json.dumps(metadata, indent=2))
    print(f"RUN: {log_dir}", flush=True)
    with launch_simulation(cfg, args):
        if args.mode == "train" and args.turn_fraction > 0:
            from commands import HIMVelocityCommand
            cfg.commands.base_velocity.class_type = HIMVelocityCommand
        env = gym.make(task, cfg=cfg)
        wrapped = HIMVecEnv(env)
        robot = wrapped.env.scene["robot"]
        metadata["joint_names"] = robot.joint_names
        metadata["default_joint_positions"] = robot.data.default_joint_pos.torch[0].tolist()
        metadata["action_scale"] = cfg.actions.joint_pos.scale
        (log_dir / "config.json").write_text(json.dumps(metadata, indent=2))
        runner = HIMOnPolicyRunner(wrapped, config, str(log_dir), args.device)
        if args.terrain == "stairs" and args.reward_profile != "stock":
            from stair_rewards import validate_reward_frames
            metadata["reward_frame_validation"] = validate_reward_frames(wrapped.env)
            (log_dir / "config.json").write_text(json.dumps(metadata, indent=2))
        print(f"HIM dimensions: actor={wrapped.num_obs}, frame={wrapped.num_one_step_obs}, critic={wrapped.num_privileged_obs}, actions={wrapped.num_actions}", flush=True)
        if args.checkpoint:
            if args.warm_start:
                from checkpoint_transfer import warm_start
                metadata["transfer"] = warm_start(runner, str(args.checkpoint), args.warm_start)
                (log_dir / "config.json").write_text(json.dumps(metadata, indent=2))
            else:
                runner.load(str(args.checkpoint), load_optimizer=args.mode == "train")
        diagnostic = {"root_pos_w": robot.data.root_pos_w.torch[:4].tolist(),
                      "root_quat_w_xyzw": robot.data.root_quat_w.torch[:4].tolist(),
                      "projected_gravity_b": robot.data.projected_gravity_b.torch[:4].tolist(),
                      "critic_shape": list(wrapped.get_privileged_observations().shape)}
        if args.terrain in ("rough", "stairs"):
            scanner = wrapped.env.scene["height_scanner"]
            scan = wrapped.get_privileged_observations()[:, 48:]
            diagnostic.update({"scanner_pos_w": scanner.data.pos_w.torch[:4].tolist(),
                               "ray_hits_z_quantiles": torch.quantile(scanner.data.ray_hits_w.torch[..., 2].flatten(), torch.tensor([0., .25, .5, .75, 1.], device=args.device)).tolist(),
                               "scan_quantiles": torch.quantile(scan.flatten(), torch.tensor([0., .25, .5, .75, 1.], device=args.device)).tolist(),
                               "scan_unsaturated_fraction": float((scan.abs() < 4.999).float().mean())})
        (log_dir / "physics-diagnostic.json").write_text(json.dumps(diagnostic, indent=2))
        if args.mode != "train":
            export_error = export_and_verify(runner.alg.actor_critic, wrapped.get_observations(), log_dir)
        if args.mode == "train":
            started = time.monotonic()
            runner.learn(args.max_iterations, init_at_random_ep_len=True)
            model = runner.alg.actor_critic
            if not all(torch.isfinite(p).all().item() for p in model.parameters()):
                raise RuntimeError("Non-finite trained parameters")
            export_error = export_and_verify(model, wrapped.get_observations(), log_dir)
            (log_dir / "result.json").write_text(json.dumps({"status": "smoke_passed", "scope": "CUDA training and export; locomotion requires separate evaluation", "iterations": args.max_iterations, "completed_iterations": runner.current_learning_iteration, "num_envs": args.num_envs, "environment_steps_this_run": args.max_iterations * args.steps_per_env * args.num_envs, "training_seconds": time.monotonic() - started, "parameters_finite": True, "checkpoint": f"model_{runner.current_learning_iteration}.pt", "export": "policy.pt", "export_max_abs_error": export_error, "peak_cuda_memory_bytes": torch.cuda.max_memory_allocated()}, indent=2))
        elif args.mode == "evaluate":
            policy = runner.get_inference_policy(device=args.device)
            if args.terrain == "stairs":
                from stair_evaluation import evaluate_stair_suite, assess_final
                result = evaluate_stair_suite(wrapped, policy, stair_manifest["geometry"],
                                             seconds=args.eval_seconds, speed=args.speed,
                                             seeds=tuple(args.eval_seed or [args.seed]), randomized=args.eval_randomized,
                                             progress=lambda metrics: print(json.dumps(metrics), flush=True))
                result["final_acceptance"] = assess_final(result)
            else:
                from evaluation import evaluate_suite
                options = {"commands": args.command} if args.command else {}
                result = evaluate_suite(wrapped, policy, seconds=args.eval_seconds, seed=args.seed,
                                        progress=lambda metrics: print(json.dumps(metrics), flush=True), **options)
            result["export_max_abs_error"] = export_error
            (log_dir / "result.json").write_text(json.dumps(result, indent=2))
            print(json.dumps(result, indent=2), flush=True)
        else:
            policy = runner.get_inference_policy(device=args.device)
            dones_total = 0
            with torch.inference_mode():
                for step in range(args.play_steps):
                    actions = policy(wrapped.get_observations())
                    if not torch.isfinite(actions).all():
                        raise RuntimeError("Non-finite actions")
                    _, _, rewards, dones, _, _, _ = wrapped.step(actions)
                    if not torch.isfinite(rewards).all():
                        raise RuntimeError("Non-finite rewards")
                    dones_total += dones.sum().item()
                    if (step + 1) % 100 == 0:
                        print(f"Playback {step + 1}/{args.play_steps}, mean reward={rewards.mean().item():.4f}, resets={dones_total}", flush=True)
            (log_dir / "result.json").write_text(json.dumps({"status": "smoke_passed", "scope": "Playback numerical check", "play_steps": args.play_steps, "num_envs": args.num_envs, "resets": dones_total, "actions_finite": True, "export_max_abs_error": export_error}, indent=2))
        print(f"RESULT: {log_dir}", flush=True)
        # Kit 6.1 can hang in teardown after a completed headless run. This only
        # terminates this CLI process after all artifacts have been saved.
        if args.shutdown_timeout > 0:
            def shutdown_watchdog():
                print("Isaac Sim teardown timeout; saved results are complete.", flush=True)
                os._exit(0)
            timer = threading.Timer(args.shutdown_timeout, shutdown_watchdog)
            timer.daemon = True
            timer.start()
        env.close()
    print(f"RESULT: {log_dir}", flush=True)


if __name__ == "__main__":
    main()
