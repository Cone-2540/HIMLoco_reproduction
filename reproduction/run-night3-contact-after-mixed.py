#!/usr/bin/env python3
"""One small existing reward adaptation after the primary deployment-domain arm."""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
DEADLINE=datetime.fromisoformat('2026-10-14T07:20:00+08:00')


def main():
    parent=ROOT/'reproduction/night3-deployment-pipeline.json'
    while True:
        if datetime.now().astimezone()>=DEADLINE:raise SystemExit('Deadline reached')
        data=json.loads(parent.read_text()) if parent.exists() else {'jobs':[]}
        if len(data['jobs'])==2:
            if data['jobs'][-1]['exit_code']!=0:raise SystemExit('Primary domain arm failed')
            break
        time.sleep(5)
    print('Starting contact-light deployment arm3',flush=True)
    result=subprocess.run([sys.executable,str(ROOT/'reproduction/run-night3-job.py'),
        '--name','night3-deployment-contact-light-arm3','--max-seconds','4200','--',
        'train','--terrain','stairs','--reward_profile','contact_light','--domain_profile','deployment',
        '--checkpoint','artifacts/go2-night3-robust-faithful-arm1/model_860.pt',
        '--num_envs','7680','--steps_per_env','100','--max_iterations','200','--save_interval','20',
        '--stair_stage','paper_mixed','--start_level','4','--seed','1403','--stair_speed_range','.25','.65',
        '--learning_rate','.0001','--lr_schedule','fixed','--resume_learning_rate','.0001','--reset_noise_std','.2'],
        cwd=ROOT,text=True,capture_output=True)
    print(result.stdout,flush=True)
    if result.stderr:print(result.stderr,file=sys.stderr,flush=True)
    index=result.stdout.find('\n{')
    if index>=0:(ROOT/'reproduction/night3-contact-arm3-launch.json').write_text(result.stdout[index+1:])
    raise SystemExit(result.returncode)


if __name__=='__main__':main()
