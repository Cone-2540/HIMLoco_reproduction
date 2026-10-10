"""Finite training/playback check using HIMLoco's original task and runner."""

import json
import os
import sys
from pathlib import Path

import isaacgym
from isaacgym import gymapi
import torch
from legged_gym.envs import *
from legged_gym.utils import get_args, task_registry, export_policy_as_jit


def main():
    # The original parser stays intact; these options only select the validation phase.
    mode = os.environ.get("HIM_VERIFY_MODE", "train")
    flat = os.environ.get("HIM_VERIFY_FLAT", "1") == "1"
    terrain = os.environ.get("HIM_VERIFY_TERRAIN", 'plane' if flat else 'trimesh')
    if terrain not in ('plane', 'trimesh', 'heightfield'):
        raise ValueError('HIM_VERIFY_TERRAIN must be plane, trimesh or heightfield')
    checkpoint = os.environ.get("HIM_VERIFY_CHECKPOINT")
    if checkpoint:
        checkpoint = str(Path(checkpoint).expanduser().resolve())
    steps = int(os.environ.get("HIM_VERIFY_STEPS", "500"))
    render = os.environ.get("HIM_VERIFY_RENDER", "0") == "1"
    args = get_args()
    args.headless = not render
    torch.set_num_threads(4)
    env_cfg, train_cfg = task_registry.get_cfgs(args.task)
    env_cfg.terrain.mesh_type = terrain
    if terrain == 'plane':
        env_cfg.terrain.curriculum = False
    if mode == 'play':
        env_cfg.noise.add_noise = False
        env_cfg.domain_rand.push_robots = False
    env, env_cfg = task_registry.make_env(name=args.task, args=args, env_cfg=env_cfg)
    runner, train_cfg = task_registry.make_alg_runner(env=env, name=args.task, args=args, train_cfg=train_cfg)
    output = Path(runner.log_dir)
    camera = None
    if render:
        camera_props = gymapi.CameraProperties()
        camera_props.width = 960
        camera_props.height = 640
        camera = env.gym.create_camera_sensor(env.envs[0], camera_props)
    result = {"task": args.task, "simulator": "Isaac Gym Preview 4", "python": sys.version, "torch": torch.__version__, "device": args.rl_device, "terrain": terrain, "num_envs": env.num_envs, "actor_observations": env.num_obs, "critic_observations": env.num_privileged_obs}
    if checkpoint:
        runner.load(checkpoint, load_optimizer=mode == 'train')
    minimum_relative_height = float('inf')
    if mode == 'train':
        runner.learn(train_cfg.runner.max_iterations, init_at_random_ep_len=True)
        result["iterations"] = train_cfg.runner.max_iterations
        result["checkpoint"] = str(output / ('model_%d.pt' % runner.current_learning_iteration))
        export_policy_as_jit(runner.alg.actor_critic, str(output / 'exported'))
    else:
        policy = runner.get_inference_policy(device=args.rl_device)
        resets = 0
        mean_reward = 0.0
        with torch.inference_mode():
            obs = env.get_observations()
            for step in range(steps):
                actions = policy(obs)
                if not torch.isfinite(actions).all():
                    raise RuntimeError('non-finite policy actions')
                obs, _, rewards, dones, _, _, _ = env.step(actions)
                if not torch.isfinite(obs).all() or not torch.isfinite(rewards).all():
                    raise RuntimeError('non-finite simulation values')
                resets += dones.sum().item()
                mean_reward += rewards.mean().item()
                relative_height = env.root_states[:, 2] - env.measured_heights.mean(dim=1)
                minimum_relative_height = min(minimum_relative_height, relative_height.min().item())
                if (step + 1) % 100 == 0:
                    print('Playback %d/%d, resets=%d' % (step + 1, steps, resets), flush=True)
        result.update(play_steps=steps, resets=resets, mean_step_reward=mean_reward / steps)
        result['minimum_base_height_above_sampled_terrain_m'] = minimum_relative_height
    result['parameters_finite'] = all(torch.isfinite(p).all().item() for p in runner.alg.actor_critic.parameters())
    if not result['parameters_finite']:
        raise RuntimeError('non-finite model parameters')
    result['status'] = 'passed'
    result['scope'] = 'Execution and numerical validity only; not converged locomotion performance.'
    relative_height = env.root_states[:, 2] - env.measured_heights.mean(dim=1)
    result['final_base_height_above_sampled_terrain_m'] = relative_height.tolist()
    if (relative_height < -1.0).any() or minimum_relative_height < -1.0:
        result['status'] = 'physics_anomaly'
        result['warning'] = 'Base fell more than 1 m below sampled terrain; inspect terrain collisions.'
    output.mkdir(parents=True, exist_ok=True)
    if camera is not None:
        position = env.root_states[0, :3].tolist()
        target = gymapi.Vec3(*position)
        eye = gymapi.Vec3(position[0] + 1.5, position[1] + 1.5, position[2] + 1.0)
        env.gym.set_camera_location(camera, env.envs[0], eye, target)
        env.gym.step_graphics(env.sim)
        env.gym.render_all_camera_sensors(env.sim)
        env.gym.write_camera_image_to_file(env.sim, env.envs[0], camera, gymapi.IMAGE_COLOR, str(output / 'go2.png'))
        result['image'] = str(output / 'go2.png')
    (output / ('validation_%s.json' % mode)).write_text(json.dumps(result, indent=2) + '\n')
    if runner.writer is not None:
        runner.writer.close()
    if env.viewer is not None:
        env.gym.destroy_viewer(env.viewer)
    env.gym.destroy_sim(env.sim)
    print('RESULT: %s' % output, flush=True)
    if result['status'] != 'passed':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
