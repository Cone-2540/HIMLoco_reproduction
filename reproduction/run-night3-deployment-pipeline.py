#!/usr/bin/env python3
"""Serialize GPU jobs behind arm1; every simulator child has the 07:20 deadline."""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
DEADLINE=datetime.fromisoformat('2026-10-14T07:20:00+08:00')
PARENT=Path.home()/'robotics/logs/20261014-010128_night3-robust-faithful-arm1/launch-record.json'
OUTPUT=ROOT/'reproduction/night3-deployment-pipeline.json'


def main():
    jobs=[]
    while json.loads(PARENT.read_text())['status']=='started':
        if datetime.now().astimezone()>=DEADLINE:raise SystemExit('Deadline reached')
        time.sleep(5)
    parent=json.loads(PARENT.read_text())
    if parent['exit_code']!=0:raise SystemExit('Arm1 did not finish cleanly; no implicit recovery')
    common=['train','--terrain','stairs','--reward_profile','faithful',
            '--checkpoint','artifacts/go2-stairs-night2-faithful-seed1213-760/model_760.pt',
            '--stair_stage','paper_mixed','--start_level','4','--domain_profile','deployment',
            '--learning_rate','.0001','--lr_schedule','fixed','--resume_learning_rate','.0001',
            '--seed','1402','--stair_speed_range','.25','.65']
    for name,seconds,extra in [
        ('night3-deployment-smoke',360,['--num_envs','128','--steps_per_env','24','--max_iterations','3','--save_interval','1']),
        ('night3-deployment-mixed-arm2',4800,['--num_envs','7680','--steps_per_env','100','--max_iterations','200','--save_interval','20',
                                           '--flat_replay_fraction','.25','--flat_replay_all_directions','--reset_noise_std','.3'])]:
        print(f'Starting {name} at {datetime.now().astimezone().isoformat()}',flush=True)
        process=subprocess.run([sys.executable,str(ROOT/'reproduction/run-night3-job.py'),
                                '--name',name,'--max-seconds',str(seconds),'--',*common,*extra],
                               cwd=ROOT,text=True,capture_output=True)
        print(process.stdout,flush=True)
        if process.stderr:print(process.stderr,file=sys.stderr,flush=True)
        index=process.stdout.find('\n{')
        if index<0:raise SystemExit(f'{name} did not return a launch record')
        job=json.loads(process.stdout[index+1:]);jobs.append(job)
        OUTPUT.write_text(json.dumps({'parent':parent,'jobs':jobs},indent=2)+'\n')
        if process.returncode!=0:raise SystemExit(f'{name} failed: {process.returncode}')
        if name.endswith('smoke'):
            d=json.loads((Path(job['simulator_log_dir'])/'domain-parameters-initial.json').read_text())
            motor=d['actuator_pd']['groups']['base_legs']
            assert motor['status']=='available' and motor['actuator_type']=='DeploymentMotor',motor
            assert motor['drive_strength']['min']>=.9 and motor['drive_strength']['max']<=1.1,motor
            assert motor['position_delay_physics_steps']['min']==0 and motor['position_delay_physics_steps']['max']==2,motor
            assert motor['position_delay_seconds']['max']<=.010001,motor
            print('Physical deployment motor readback passed; starting formal training',flush=True)
    print('Pipeline completed; independent evaluations still required',flush=True)


if __name__=='__main__':main()
