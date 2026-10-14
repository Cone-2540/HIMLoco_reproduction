#!/usr/bin/env python3
"""HIM deployment interface in MuJoCo; no Isaac dependencies or terrain actor inputs."""
import argparse
import hashlib
import json
import time
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
import torch

ASSETS = Path.home() / 'robotics/assets/mujoco-menagerie-go2/unitree_go2'
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / 'artifacts/go2-stairs-night2-faithful-seed1213-760/policy.pt'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


RUNNER_SOURCE_SHA256 = sha(__file__)


def dc_torque(target, q, dq, kp, kd, effort, velocity):
    requested = kp * (target - q) - kd * dq
    bounded_velocity = np.clip(dq, -2 * velocity, 2 * velocity)
    maximum = np.minimum(effort * (1 - bounded_velocity / velocity), effort)
    minimum = np.maximum(effort * (-1 - bounded_velocity / velocity), -effort)
    return np.clip(requested, minimum, maximum), requested


def observation(command, omega, gravity, q, dq, default, previous_action):
    return np.concatenate((np.asarray(command) * [2, 2, .25], omega * .25,
                           gravity, q - default, dq * .05, previous_action)).astype(np.float32)


def push_history(history, frame):
    return np.concatenate((frame, history[:-45])).astype(np.float32)


def make_model(args, output):
    xml = ET.parse(args.assets / 'go2.xml')
    root = xml.getroot()
    root.find('compiler').set('meshdir', str((args.assets / 'assets').resolve()))
    option = root.find('option')
    option.set('timestep', str(args.dt))
    option.set('integrator', 'implicitfast')
    option.set('iterations', '100')
    visual = ET.SubElement(root, 'visual')
    ET.SubElement(visual, 'global', offwidth='1280', offheight='720')
    if not args.stock_joint_physics:
        joint = root.find("default/default[@class='go2']/joint")
        for key in ('damping', 'armature', 'frictionloss'):
            joint.set(key, '0')
    collision = root.find("default/default[@class='go2']/default[@class='collision']")
    collision.find('geom').set('contype', '1')
    collision.find('geom').set('conaffinity', '2')
    if args.contact_profile == 'rigid':
        foot = collision.find("default[@class='foot']/geom")
        foot.set('solimp', '.9 .95 .001')
        foot.set('solref', '.01 1')
        foot.set('condim', '3')
    # Disable robot self collision, as in the training USD, but retain every leg geom.
    world = root.find('worldbody')
    ET.SubElement(world, 'light', pos='0 0 6', dir='0 0 -1', diffuse='.8 .8 .8')
    ET.SubElement(world, 'geom', name='floor', type='plane', size='0 0 .1',
                  rgba='.25 .3 .35 1', contype='2', conaffinity='1',
                  friction=f'{args.friction} .02 .01', condim='3')
    start = 1.2
    end = start + args.steps * args.depth
    def box(name, x0, x1, height, color):
        if height <= 0:
            return
        ET.SubElement(world, 'geom', name=name, type='box',
                      pos=f'{(x0+x1)/2} 0 {height/2}',
                      size=f'{(x1-x0)/2} {args.width/2} {height/2}',
                      contype='2', conaffinity='1', friction=f'{args.friction} .02 .01',
                      condim='3', rgba=color)
    def nose(name,x0,x1,top):
        if args.nosing<=0:return
        thickness=min(.03,args.height/3)
        ET.SubElement(world,'geom',name=name,type='box',
                      pos=f'{(x0+x1)/2} 0 {top-thickness/2}',
                      size=f'{(x1-x0)/2} {args.width/2} {thickness/2}',
                      contype='2',conaffinity='1',friction=f'{args.friction} .02 .01',
                      condim='3',rgba='.7 .7 .75 1')
    if args.terrain == 'asc':
        for i in range(args.steps):
            box(f'step_{i}', start + i*args.depth, end+2,
                (i+1)*args.height, '.55 .6 .65 1' if i%2 else '.65 .65 .65 1')
            nose(f'nosing_{i}',start+i*args.depth-args.nosing,start+i*args.depth,(i+1)*args.height)
    elif args.terrain == 'desc':
        box('start_platform', -3, start, args.steps*args.height, '.55 .6 .65 1')
        nose('platform_nosing',start,start+args.nosing,args.steps*args.height)
        for i in range(args.steps-1):
            box(f'step_{i}', start+i*args.depth, start+(i+1)*args.depth,
                (args.steps-i-1)*args.height, '.6 .6 .65 1')
            nose(f'nosing_{i}',start+(i+1)*args.depth,start+(i+1)*args.depth+args.nosing,
                 (args.steps-i-1)*args.height)
    path = output / 'model.xml'
    xml.write(path)
    model = mujoco.MjModel.from_xml_path(str(path))
    base = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'base')
    model.body_mass[base] *= args.mass_scale
    model.body_inertia[base] *= args.mass_scale
    model.body_ipos[base] += args.com_offset
    for name in ('FL', 'FR', 'RL', 'RR'):
        gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, name)
        model.geom_friction[gid, 0] = args.friction
    return model, base, start, end


def run(args):
    torch.set_num_threads(1)
    runner_sha256 = RUNNER_SOURCE_SHA256
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    config_bytes = args.config.read_bytes()
    config_sha256 = hashlib.sha256(config_bytes).hexdigest()
    config = json.loads(config_bytes)
    names = config['joint_names']
    default = np.asarray(config['default_joint_positions'])
    assert len(names) == len(set(names)) == 12
    model, base, start, end = make_model(args, output)
    data = mujoco.MjData(model)
    joints = np.array([mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, n) for n in names])
    if (joints < 0).any():
        raise ValueError('Missing policy joints')
    qids, vids = model.jnt_qposadr[joints], model.jnt_dofadr[joints]
    if args.armature is not None:
        model.dof_armature[vids] = args.armature
    aids = np.array([np.flatnonzero(model.actuator_trnid[:, 0] == j).item() for j in joints])
    assert len(set(aids)) == 12
    effort = np.array([45.43 if 'calf' in n else 23.7 for n in names])
    velocity = np.array([15.70 if 'calf' in n else 30.1 for n in names])
    if args.conservative_calf:
        effort[8:] = 35.55
        velocity[8:] = 20.07
    model.actuator_ctrlrange[aids] = np.column_stack((-effort, effort))
    rng = np.random.default_rng(args.seed)
    # Recompute derived constants after mass, COM and optional armature edits.
    mujoco.mj_setConst(model, data)
    data.qpos[:3] = [0, args.initial_y, .4 + (args.steps*args.height if args.terrain == 'desc' else 0)]
    yaw = args.initial_yaw
    data.qpos[3:7] = [np.cos(yaw/2), 0, 0, np.sin(yaw/2)]
    data.qpos[qids] = default + rng.uniform(-args.initial_joint_noise, args.initial_joint_noise, 12)
    if args.per_foot_friction:
        for name in ('FL','FR','RL','RR'):
            gid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,name)
            model.geom_friction[gid,0]=rng.uniform(*args.per_foot_friction)
    mujoco.mj_forward(model, data)
    policy = torch.jit.load(str(args.policy), map_location='cpu').eval()
    history, action = np.zeros(270, np.float32), np.zeros(12)
    feet = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, n) for n in ('FL','FR','RL','RR')]
    kp, kd = 25*args.gain_scale, .5*args.gain_scale
    if args.per_joint_gains:
        kp=kp*rng.uniform(*args.per_joint_gains,12)
        kd=kd*rng.uniform(*args.per_joint_gains,12)
    strength = args.motor_strength
    if args.per_joint_strength:
        strength=strength*rng.uniform(*args.per_joint_strength,12)
    renderer = writer = viewer = None
    if args.video:
        import imageio.v2 as imageio
        renderer = mujoco.Renderer(model, height=720, width=1280)
        writer = imageio.get_writer(output/'video.mp4', fps=50, codec='libx264', quality=7)
    if args.viewer:
        from mujoco import viewer as mj_viewer
        viewer = mj_viewer.launch_passive(model, data)
    camera = mujoco.MjvCamera()
    camera.azimuth, camera.elevation, camera.distance = 125, -18, 3.7
    rows, dwell, passed, reason = [], 0., False, 'timeout'
    body_contact_steps, calf_contact_steps = 0, 0
    body_loaded_steps, calf_loaded_steps, calf_peak_force = 0, 0, 0.
    lag = [np.zeros(12) for _ in range(args.delay_steps)]
    physics_lag = None
    started = time.monotonic()
    try:
        with torch.inference_mode():
            for step in range(round(args.seconds / (args.dt*args.decimation))):
                wall_step = time.monotonic()
                observation_time = float(data.time)
                R = data.xmat[base].reshape(3,3)
                yaw_now = np.arctan2(R[1,0], R[0,0])
                command = np.asarray(args.command, dtype=float).copy()
                if args.heading_feedback:
                    command[2] = np.clip(-yaw_now, -.5, .5)
                omega6 = np.zeros(6)
                # mjOBJ_BODY local velocity uses the inertial principal-axis frame,
                # whose orientation differs substantially from the Go2 base link.
                # Read world angular velocity and rotate into the IMU/base-link frame.
                mujoco.mj_objectVelocity(model, data, mujoco.mjtObj.mjOBJ_BODY, base, omega6, 0)
                omega6[:3] = R.T @ omega6[:3]
                linear_velocity_body = R.T @ omega6[3:]
                frame = observation(command, omega6[:3], R.T @ np.array([0,0,-1]),
                                    data.qpos[qids], data.qvel[vids], default, action)
                if args.obs_noise:
                    noise = np.zeros(45)
                    noise[3:6] = rng.uniform(-.2,.2,3)*.25
                    noise[6:9] = rng.uniform(-.05,.05,3)
                    noise[9:21] = rng.uniform(-.01,.01,12)
                    noise[21:33] = rng.uniform(-1.5,1.5,12)*.05
                    frame += noise.astype(np.float32)
                history = push_history(history, frame)
                action = np.clip(policy(torch.from_numpy(history[None])).numpy()[0], -100, 100)
                applied = action
                if lag:
                    lag.append(action.copy())
                    applied = lag.pop(0)
                target = default + config['action_scale']*applied
                body_contact, calf_contact = False, False
                body_loaded, calf_loaded, calf_force_this_step = False, False, 0.
                for _ in range(args.decimation):
                    target_applied = target
                    if args.delay_physics_steps:
                        if physics_lag is None:
                            physics_lag = [target.copy() for _ in range(args.delay_physics_steps)]
                        physics_lag.append(target.copy())
                        target_applied = physics_lag.pop(0)
                    tau, requested = dc_torque(target_applied, data.qpos[qids], data.qvel[vids], kp, kd, effort, velocity)
                    data.ctrl[aids] = np.clip(tau * strength,-effort,effort)
                    mujoco.mj_step(model, data)
                    for contact_index, contact in enumerate(data.contact):
                        contact_force = np.zeros(6)
                        mujoco.mj_contactForce(model, data, contact_index, contact_force)
                        normal_force = abs(contact_force[0])
                        for geom in (contact.geom1, contact.geom2):
                            body = model.geom_bodyid[geom]
                            body_contact |= body == base
                            body_loaded |= body == base and normal_force > 1.
                            name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body) or ''
                            is_calf = 'calf' in name and geom not in feet
                            calf_contact |= is_calf
                            calf_loaded |= is_calf and normal_force > 1.
                            if is_calf:
                                calf_force_this_step = max(calf_force_this_step,normal_force)
                body_contact_steps += int(body_contact)
                calf_contact_steps += int(calf_contact)
                body_loaded_steps += int(body_loaded)
                calf_loaded_steps += int(calf_loaded)
                calf_peak_force = max(calf_peak_force,calf_force_this_step)
                # mj_step integrates qpos/qvel after deriving xmat/cvel. Refresh
                # derived quantities so the next frame uses one coherent timestamp.
                mujoco.mj_forward(model, data)
                R = data.xmat[base].reshape(3,3)
                foot_x = data.geom_xpos[feet,0]
                if args.terrain == 'flat':
                    target_progress = (data.qpos[0]*args.command[0] + data.qpos[1]*args.command[1])
                    crossed = target_progress >= args.flat_distance * max(np.linalg.norm(args.command[:2]), .01)
                else:
                    crossed = bool(np.min(foot_x) > end+.08)
                dwell = dwell+args.dt*args.decimation if crossed and R[2,2]>.85 and not body_contact else 0.
                rows.append(dict(time=float(data.time), policy_observation_time=observation_time,
                                 position=data.qpos[:3].tolist(),
                                 quaternion_wxyz=data.qpos[3:7].tolist(), gravity=(R.T@np.array([0,0,-1])).tolist(),
                                 omega=omega6[:3].tolist(), command=command.tolist(), joint_position=data.qpos[qids].tolist(),
                                 linear_velocity_body=linear_velocity_body.tolist(),
                                 joint_velocity=data.qvel[vids].tolist(), action=action.tolist(),
                                 torque=tau.tolist(), torque_clipped=int(np.sum(np.abs(tau-requested)>1e-5)),
                                 foot_position=data.geom_xpos[feet].tolist(), body_contact=bool(body_contact),
                                 calf_contact=bool(calf_contact), goal_dwell=dwell))
                rows[-1].update(body_loaded_contact=bool(body_loaded),calf_loaded_contact=bool(calf_loaded),
                                calf_peak_normal_force_n=float(calf_force_this_step))
                if args.record_policy_input:
                    rows[-1]["policy_input"] = frame.tolist()
                if writer:
                    camera.lookat[:] = data.qpos[:3]
                    renderer.update_scene(data, camera=camera)
                    writer.append_data(renderer.render())
                if viewer:
                    viewer.sync()
                    time.sleep(max(0,args.dt*args.decimation-(time.monotonic()-wall_step)))
                if not np.isfinite(data.qpos).all() or R[2,2] < .5:
                    reason = 'fall_or_nonfinite'
                    break
                if abs(data.qpos[1]) > args.width/2 + .15 and args.terrain != 'flat':
                    reason = 'left_stair_width'
                    break
                if dwell >= .5 and not args.fixed_duration:
                    passed, reason = True, ('all_feet_on_landing_and_upright_dwell' if args.terrain!='flat' else 'forward_progress_and_upright_dwell')
                    break
    finally:
        if writer:
            writer.close()
            renderer.close()
        if viewer:
            viewer.close()
    (output/'trace.json').write_text(json.dumps(rows))
    tracking_rows = [r for r in rows if r['time'] >= 1.]
    xy_error = np.asarray([np.linalg.norm(np.asarray(r['linear_velocity_body'][:2])-r['command'][:2]) for r in tracking_rows])
    yaw_error = np.asarray([abs(r['omega'][2]-r['command'][2]) for r in tracking_rows])
    if args.fixed_duration and reason=='timeout':
        xy_limit = .08 if np.linalg.norm(args.command)==0 else .2
        passed = bool(xy_error.size and xy_error.mean()<=xy_limit and yaw_error.mean()<=.3)
        if np.linalg.norm(args.command[:2])==0:
            displacement=np.linalg.norm(data.qpos[:2]-[0,args.initial_y])
            passed &= bool(displacement <= (.5 if args.command[2]==0 else 1.))
        reason = 'fixed_duration_tracking_pass' if passed else 'fixed_duration_tracking_fail'
    result = dict(success=passed, reason=reason, simulation_seconds=float(data.time),
                  wall_seconds=time.monotonic()-started, final_position=data.qpos[:3].tolist(),
                  body_contact_fraction=body_contact_steps/max(1,len(rows)), calf_contact_fraction=calf_contact_steps/max(1,len(rows)),
                  body_loaded_contact_fraction=body_loaded_steps/max(1,len(rows)),
                  calf_loaded_contact_fraction=calf_loaded_steps/max(1,len(rows)), calf_peak_normal_force_n=float(calf_peak_force),
                  contact_scope='fraction of 20ms policy intervals with any geometric contact; loaded contact additionally requires >1N normal force in any 5ms physics substep',
                  xy_velocity_mae_m_s=float(xy_error.mean()) if xy_error.size else None,
                  yaw_velocity_mae_rad_s=float(yaw_error.mean()) if yaw_error.size else None,
                  mean_action_rate_squared=float(np.mean(np.diff(np.asarray([r['action'] for r in rows]),axis=0)**2)) if len(rows)>1 else None,
                  policy_sha256=sha(args.policy), config_sha256=config_sha256, generated_xml_sha256=sha(output/'model.xml'),
                  source_model_sha256=sha(args.assets/'go2.xml'), mujoco_version=mujoco.__version__, torch_version=torch.__version__,
                  runner_source_sha256=runner_sha256,
                  protocol_version='2: derived inertial constants and end-of-step state refreshed',
                  policy_joint_order=names, mujoco_qpos_indices=qids.tolist(), mujoco_actuator_indices=aids.tolist(),
                  arguments={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
                  actual_base_mass=float(model.body_mass[base]), actual_base_com=model.body_ipos[base].tolist(),
                  actual_joint_damping=model.dof_damping[vids].tolist(), goal_x=end+.08 if args.terrain!='flat' else None,
                  actual_kp=np.broadcast_to(kp,(12,)).tolist(),actual_kd=np.broadcast_to(kd,(12,)).tolist(),
                  actual_drive_strength=np.broadcast_to(strength,(12,)).tolist(),
                  actual_foot_friction=model.geom_friction[feet].tolist(),
                  goal_definition='all four foot sphere centers past final riser+8cm, upright Rzz>.85, no body contact for 0.5s' if args.terrain!='flat' else 'command-direction 3m progress, upright/no body contact for 0.5s',
                  controller='50Hz HIM/6x45 newest-first, 200Hz explicit PD25/0.5 with IsaacLab DC torque-speed curve',
                  source_manifest=str(args.assets.parent/'SOURCE.json'))
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
    return result


def parse():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--policy',type=Path,default=DEFAULT_POLICY)
    p.add_argument('--config',type=Path,default=DEFAULT_POLICY.parent/'config.json')
    p.add_argument('--assets',type=Path,default=ASSETS)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--terrain',choices=['flat','asc','desc'],default='flat')
    p.add_argument('--height',type=float,default=.16)
    p.add_argument('--depth',type=float,default=.27)
    p.add_argument('--steps',type=int,default=6)
    p.add_argument('--width',type=float,default=1.2)
    p.add_argument('--nosing',type=float,default=0.)
    p.add_argument('--seconds',type=float,default=20.)
    p.add_argument('--dt',type=float,default=.005)
    p.add_argument('--decimation',type=int,default=4)
    p.add_argument('--command',type=float,nargs=3,default=[.3,0,0])
    p.add_argument('--flat-distance',type=float,default=3.)
    p.add_argument('--seed',type=int,default=1400)
    p.add_argument('--initial-yaw',type=float,default=0.)
    p.add_argument('--initial-y',type=float,default=0.)
    p.add_argument('--initial-joint-noise',type=float,default=0.)
    p.add_argument('--friction',type=float,default=1.)
    p.add_argument('--mass-scale',type=float,default=1.)
    p.add_argument('--com-offset',type=float,nargs=3,default=[0,0,0])
    p.add_argument('--gain-scale',type=float,default=1.)
    p.add_argument('--armature',type=float)
    p.add_argument('--contact-profile',choices=['menagerie','rigid'],default='menagerie')
    p.add_argument('--motor-strength',type=float,default=1.)
    p.add_argument('--per-joint-gains',type=float,nargs=2)
    p.add_argument('--per-joint-strength',type=float,nargs=2)
    p.add_argument('--per-foot-friction',type=float,nargs=2)
    p.add_argument('--delay-steps',type=int,default=0)
    p.add_argument('--delay-physics-steps',type=int,default=0)
    p.add_argument('--fixed-duration',action='store_true',help='Flat only: survive the full interval and pass velocity tracking gates')
    p.add_argument('--record-policy-input',action='store_true',
                   help='Save the exact pre-inference frame, including observation noise, for mirror diagnostics')
    for flag in ('heading-feedback','obs-noise','stock-joint-physics','conservative-calf','video','viewer'):
        p.add_argument('--'+flag,action='store_true')
    args = p.parse_args()
    if args.dt!=.005 or args.decimation!=4:
        p.error('Frozen exported policy requires 200Hz physics and 50Hz policy')
    if args.delay_steps<0 or args.seconds<=0 or args.steps<=0 or args.depth<=0 or args.height<=0:
        p.error('Invalid simulation dimensions/timing')
    if args.delay_physics_steps<0 or (args.delay_steps and args.delay_physics_steps):
        p.error('Select either policy-frame delay or physics-substep delay')
    if args.fixed_duration and (args.terrain!='flat' or args.seconds<20):
        p.error('Full-duration flat tracking evaluation requires at least 20s')
    for ranges in [args.per_joint_gains,args.per_joint_strength,args.per_foot_friction]:
        if ranges and not 0<ranges[0]<=ranges[1]:p.error('Randomized physical ranges must be positive and ordered')
    return args


if __name__=='__main__':
    run(parse())
