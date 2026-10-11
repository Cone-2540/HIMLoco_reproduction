#!/usr/bin/env python3
"""Archive one completed night2 training job with an independent CPU checkpoint audit.

Uses Python's standard library on the host. A CUDA-hidden container subprocess
imports the already installed Torch and loads checkpoint tensors onto CPU only.
Never starts simulation/training, changes GPU configuration, or overwrites an
existing artifact directory. Example:

  python3 reproduction/archive-stair-night2-model.py \
    --log-dir isaaclab/logs/2026-10-12_00-56-30_night2-faithful-seed1201-plus100 \
    --wrapper-dir /home/cone/robotics/logs/20261012-005628_night2-faithful-seed1201-plus100 \
    --output artifacts/go2-stairs-night2-faithful-seed1201-760
"""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
ZONE = timezone(timedelta(hours=8))

CPU_AUDIT_SCRIPT = r'''
import json, os, sys, torch
assert os.environ.get('CUDA_VISIBLE_DEVICES') == ''
assert not torch.cuda.is_initialized()
request = json.loads(sys.argv[1])
origin = torch.load(request['origin'], map_location='cpu', weights_only=True)
final = torch.load(request['final'], map_location='cpu', weights_only=True)
required = ('model_state_dict', 'optimizer_state_dict', 'estimator_optimizer_state_dict', 'iter')
for label, checkpoint in (('origin', origin), ('final', final)):
    if not all(key in checkpoint for key in required):
        raise ValueError(label + ': unsupported checkpoint schema')
    if not all(isinstance(value, torch.Tensor) and value.device.type == 'cpu' for value in checkpoint['model_state_dict'].values()):
        raise ValueError(label + ': model state must contain CPU tensors')
    if not all(torch.isfinite(value).all().item() for value in checkpoint['model_state_dict'].values()):
        raise ValueError(label + ': nonfinite model state')
if final['iter'] - origin['iter'] != request['updates']:
    raise ValueError('Actual checkpoint iteration difference does not match saved update budget')
source_shapes = {key: list(value.shape) for key, value in origin['model_state_dict'].items()}
final_shapes = {key: list(value.shape) for key, value in final['model_state_dict'].items()}
if source_shapes != final_shapes:
    raise ValueError('Checkpoint network structure changed across continuation')
expected_shapes = {'actor.0.weight': [512,64], 'critic.0.weight': [512,235],
                   'estimator.encoder.0.weight': [128,270], 'estimator.target.0.weight': [128,45],
                   'estimator.proto.weight': [32,16], 'std': [12]}
for key, expected in expected_shapes.items():
    if final_shapes.get(key) != expected:
        raise ValueError('Unexpected HIM/actor/critic shape ' + key)
optimizers = {}
expected_delta = request['updates'] * request['epochs'] * request['minibatches']
for name in ('optimizer_state_dict', 'estimator_optimizer_state_dict'):
    old, new = origin[name], final[name]
    if set(old) != {'state','param_groups'} or set(new) != {'state','param_groups'}:
        raise ValueError('Unsupported optimizer schema ' + name)
    if old['param_groups'] != new['param_groups']:
        raise ValueError('Adam parameter groups/settings changed ' + name)
    if not old['state'] or set(old['state']) != set(new['state']):
        raise ValueError('Adam state keys were reset/rebuilt ' + name)
    rows=[]
    for key, current in new['state'].items():
        previous=old['state'][key]
        if set(previous) != set(current) or not {'step','exp_avg','exp_avg_sq'} <= set(current):
            raise ValueError('Unsupported/reset Adam member ' + name)
        for field,value in current.items():
            if isinstance(value,torch.Tensor):
                if value.device.type != 'cpu' or not torch.isfinite(value).all().item():
                    raise ValueError('Nonfinite/nonCPU Adam value')
                if list(value.shape) != list(previous[field].shape):
                    raise ValueError('Adam member shape changed')
        old_step=float(previous['step']);new_step=float(current['step'])
        if new_step - old_step != expected_delta:
            raise ValueError('Adam steps were not continuously retained ' + name)
        rows.append({'parameter_state_id':key,'origin_step':old_step,'final_step':new_step,'delta':new_step-old_step})
    optimizers[name]={'state_count':len(rows),'parameter_groups':[
        {key:value for key,value in group.items() if key!='params'} | {'parameter_count':len(group['params'])}
        for group in new['param_groups']], 'per_state_step_continuation':rows,
        'all_state_tensors_finite':True,
        'continuation_scope':'State keys/groups/shapes preserved and every updated Adam step advanced exactly updates*epochs*minibatches. Final tensors differ after learning; this does not independently reconstruct initial moments before the live first update.'}
std=final['model_state_dict']['std']
if not (std > 0).all().item():
    raise ValueError('Invalid Gaussian exploration standard deviations')
assert not torch.cuda.is_initialized()
print(json.dumps({'status':'CPU_checkpoint_audit_passed','origin_iteration':origin['iter'],
    'final_iteration':final['iter'],'saved_additional_updates':final['iter']-origin['iter'],
    'checkpoint_schema_version':final.get('checkpoint_version'),
    'model_state_tensor_count':len(final_shapes),'model_state_shapes':final_shapes,
    'all_model_tensors_finite':True,'network_shapes_preserved':True,'optimizers':optimizers,
    'std':{'values':std.tolist(),'min':float(std.min()),'max':float(std.max()),'finite':True,'all_positive':True},
    'origin_tot_timesteps':origin.get('tot_timesteps'),'final_tot_timesteps':final.get('tot_timesteps'),
    'cuda_initialized':torch.cuda.is_initialized(), 'torch_version':torch.__version__,
    'scope':'Existing trusted task checkpoints loaded with weights_only=True/map_location=cpu/CUDA hidden; no simulator or live training access.'}))
'''


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def path_on_host(value):
    value = str(value)
    if value.startswith('/workspace/himloco/'):
        return ROOT / value[len('/workspace/himloco/'):]
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def path_in_container(path):
    return '/workspace/himloco/' + str(path.resolve().relative_to(ROOT))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_training_plan(config, result, plan):
    """Check actual arm identity and saved budget against its explicit plan."""
    common = plan['common']
    for name, actual, expected in (
        ('num_envs', config['num_envs'], common['num_envs']),
        ('steps_per_env', config['train']['runner']['num_steps_per_env'], common['steps_per_env']),
        ('additional_updates', result['iterations'], common['additional_updates_per_job']),
    ):
        require(actual == expected, 'Actual ' + name + ' differs from frozen training plan')
    profiles = {arm['profile'] for arm in plan['arms']}
    require(config['stair_reward']['profile'] in profiles, 'Reward profile is outside the frozen training plan arms')
    seeds = {plan[key] for key in ('initial_paired_training_seed', 'planned_confirmation_seed') if key in plan}
    if seeds:
        require(config['seed'] in seeds, 'Training seed is outside the frozen training plan')


def main():
    parser=argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--log-dir',type=Path,required=True)
    parser.add_argument('--wrapper-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--plan',type=Path,default=ROOT/'reproduction/stair-night2-training-plan.json')
    parser.add_argument('--container',default='isaaclab-local-lab-1')
    args=parser.parse_args()
    log=args.log_dir.expanduser().resolve();wrapper=args.wrapper_dir.expanduser().resolve()
    output=args.output.expanduser().resolve();plan_path=args.plan.expanduser().resolve()
    require(not output.exists(),'Refusing to overwrite existing artifact directory: '+str(output))
    require(output.parent.is_dir(),'Artifact parent must already exist')
    config=json.loads((log/'config.json').read_text());result=json.loads((log/'result.json').read_text())
    launch=json.loads((wrapper/'launch-record.json').read_text());plan=json.loads(plan_path.read_text())
    require(config.get('mode')=='train','Only a completed training run can be archived by this tool')
    require(launch.get('status')=='exited' and launch.get('exit_code')==0,'Wrapper did not finish successfully')
    require(result.get('status')=='smoke_passed' and result.get('parameters_finite') is True,'Training result is not finite/completed')
    validate_training_plan(config, result, plan)
    origin=path_on_host(config['checkpoint']);final=log/result['checkpoint'];policy=log/result['export']
    updates=result['iterations'];num_envs=result['num_envs'];steps=config['train']['runner']['num_steps_per_env']
    require(isinstance(updates,int) and updates>0,'Unsupported update count')
    require(num_envs==config['num_envs'],'num_envs disagrees between actual config and result')
    require(updates==config['requested_additional_training_updates'],'Requested/saved additional update budgets differ')
    require(result['completed_iterations']==config['runtime_training_state_before_learning']['completed_updates']+updates,'Result final iteration is inconsistent')
    expected_steps=updates*num_envs*steps
    require(result['environment_steps_this_run']==expected_steps,'Result environment step budget is inconsistent')
    require(digest(origin)==plan['checkpoint_sha256'],'Origin checkpoint SHA differs from frozen training plan')
    require(config.get('source_commit')==launch.get('source_commit'),'Config/launch source commits disagree')
    require(config['runtime_training_state_before_learning']['optimizer_state']=='checkpoint Adam retained','This job does not declare complete optimizer resume')
    require(config.get('exploration_std_override') is None,'Exploration std was explicitly reset')
    for name in ('domain-parameters-initial.json','domain-parameters-final.json','physics-diagnostic.json'):
        require((log/name).exists(),'Required runtime readback missing: '+name)
    require(final.is_file() and final.stat().st_size>0,'Final checkpoint file missing/empty')
    require(policy.is_file() and policy.stat().st_size>0,'Exported policy file missing/empty')
    for path,sha in launch['source_sha256'].items():
        require(digest(ROOT/path)==sha,'Current runtime source differs from launched snapshot: '+path)
    request={'origin':path_in_container(origin),'final':path_in_container(final),'updates':updates,
             'epochs':config['train']['algorithm']['num_learning_epochs'],
             'minibatches':config['train']['algorithm']['num_mini_batches']}
    command=['docker','exec','-i','-e','CUDA_VISIBLE_DEVICES=','-e','OMP_NUM_THREADS=2',args.container,
             '/isaac-sim/python.sh','-',json.dumps(request,separators=(',',':'))]
    audit_run=subprocess.run(command,input=CPU_AUDIT_SCRIPT,capture_output=True,text=True,timeout=60)
    if audit_run.returncode:
        raise RuntimeError('CPU checkpoint schema/continuation verification failed; no artifact was created.\n'+audit_run.stdout+audit_run.stderr)
    audit=json.loads(audit_run.stdout.strip())
    require(audit['origin_iteration']==config['runtime_training_state_before_learning']['completed_updates'],'Actual origin iter differs from live pretraining metadata')
    require(audit['final_iteration']==result['completed_iterations'],'Actual final iter differs from result')
    require(audit['cuda_initialized'] is False,'CPU inspection unexpectedly initialized CUDA')
    require(audit['final_tot_timesteps']-audit['origin_tot_timesteps']==expected_steps,'Actual checkpoint timesteps do not match run budget')
    # After all verification succeeds, exclusively create this concrete archive.
    output.mkdir(exist_ok=False)
    copied={}
    def copy(source,name):
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        require(digest(source)==digest(target),'Copied artifact differs: '+name)
        copied[name]={'bytes':target.stat().st_size,'sha256':digest(target),'source':str(source)}
    for source,name in ((final,final.name),(policy,'policy.pt'),(log/'config.json','config.json'),
                        (log/'result.json','result.json'),(wrapper/'launch-record.json','launch-record.json'),
                        (plan_path,'training-plan.json')):
        copy(source,name)
    for name in ('domain-parameters-initial.json','domain-parameters-final.json','physics-diagnostic.json'):
        copy(log/name,name)
    for name in ('stdout.log','gpu-resource.csv'):
        if (wrapper/name).exists():copy(wrapper/name,name)
    for source in sorted(log.glob('events.out.tfevents.*')):
        copy(source,source.name)
    for source_name in launch['source_sha256']:
        copy(ROOT/source_name,'source/'+source_name)
    generated={'checkpoint-cpu-audit.json':audit,'stair-manifest.json':config['stairs']}
    for name,data in generated.items():
        target=output/name;target.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
        copied[name]={'bytes':target.stat().st_size,'sha256':digest(target),'source':'Generated exclusively from verified saved checkpoint/config'}
    manifest={
        'schema_version':1,'recorded_local':datetime.now(ZONE).isoformat(),
        'status':'not-evaluated','training_status':'completed_and_CPU_checkpoint_verified',
        'scope':'Archived Go2/Isaac Lab HIM continuation; training completion/export/finite tensors do not establish locomotion or smoothness.',
        'reward_profile':config['stair_reward']['profile'],'training_seed':config['seed'],
        'checkpoint_completed_updates':audit['final_iteration'],'saved_additional_updates':updates,
        'num_envs':num_envs,'steps_per_env':steps,'environment_steps_this_run':expected_steps,
        'origin_checkpoint':str(origin.relative_to(ROOT)),'origin_checkpoint_sha256':digest(origin),
        'origin_checkpoint_completed_updates':audit['origin_iteration'],
        'training_run':str(log.relative_to(ROOT)),'training_wrapper_directory':str(wrapper),
        'source_provenance':{'config_commit':config['source_commit'],'config_tracked_files_dirty':config.get('source_tracked_files_dirty'),
                             'wrapper_commit':launch['source_commit'],'wrapper_source_dirty':launch.get('source_dirty'),
                             'verified_runtime_source_sha256':launch['source_sha256'],
                             'scope':'Both original dirty flags retained; exact selected runtime files verified and copied, no claim of an entirely clean launch worktree.'},
        'export_max_abs_error':result['export_max_abs_error'],'training_seconds':result['training_seconds'],
        'independent_evaluation_pending':True,'smoothness_verified':False,'hardware_deployment_ready':False,
        'cpu_checkpoint_audit':'checkpoint-cpu-audit.json','files':copied}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'artifact_directory':str(output),'reward_profile':manifest['reward_profile'],
                      'saved_updates':updates,'completed_updates':audit['final_iteration'],'environment_steps':expected_steps,
                      'checkpoint_sha256':copied[final.name]['sha256'],'files':len(copied),
                      'scientific_status':manifest['status'],'cuda_initialized':audit['cuda_initialized']},ensure_ascii=False))


if __name__=='__main__':
    main()
