#!/usr/bin/env python3
"""Paired MuJoCo evaluation with explicit reset, dynamics and controller provenance."""
import argparse
import contextlib
from datetime import datetime
import json
from pathlib import Path
import sys
import numpy as np
from run import parse, run, DEFAULT_POLICY


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--policy',type=Path,default=DEFAULT_POLICY)
    p.add_argument('--config',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seeds',type=int,default=8)
    p.add_argument('--seed-start',type=int,default=1400)
    p.add_argument('--suite',choices=['nominal','randomized','stress','deployment'],default='nominal')
    p.add_argument('--record-policy-input',action='store_true')
    p.add_argument('--record-leg-contacts',action='store_true')
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    configs=[]
    for terrain in ['flat','asc','desc']:
        for speed in [.3,.5]:
            configs.append(dict(name=f'{terrain}-16x27-v{speed}',terrain=terrain,height=.16,depth=.27,speed=speed))
    if a.suite in ('stress','deployment'):
        for terrain in ['asc','desc']:
            for h,d in [(.11,.35),(.17,.25),(.20,.30)]:
                configs.append(dict(name=f'{terrain}-{h}x{d}-v03',terrain=terrain,height=h,depth=d,speed=.3))
    record={'started_local':datetime.now().astimezone().isoformat(),'suite':a.suite,
            'seed_start':a.seed_start,'seeds_per_case':a.seeds,'cases':configs,
            'policy':str(a.policy.resolve()),'summary':[],'trials':[]}
    for case in configs:
        trials=[]
        for seed in range(a.seed_start,a.seed_start+a.seeds):
            rng=np.random.default_rng(seed)
            argv=['run','--policy',str(a.policy),'--config',str(a.config or a.policy.parent/'config.json'),
                  '--output',str(a.output/f"{case['name']}-seed{seed}"),'--terrain',case['terrain'],
                  '--height',str(case['height']),'--depth',str(case['depth']),
                  '--command',str(case['speed']),'0','0','--seconds','25','--seed',str(seed),
                  '--initial-yaw',f'{rng.uniform(-.06,.06):.12f}',
                  '--initial-y',f'{rng.uniform(-.04,.04):.12f}','--initial-joint-noise','.03']
            if case['terrain']!='flat':argv+=['--heading-feedback']
            if a.record_policy_input:argv+=['--record-policy-input']
            if a.record_leg_contacts:argv+=['--record-leg-contacts']
            if a.suite!='nominal':
                argv+=['--friction',str(rng.uniform(.6,1.1)),
                       '--mass-scale',str(np.exp(rng.uniform(np.log(.8),np.log(1.25)))),
                       '--gain-scale',str(1. if a.suite=='deployment' else rng.uniform(.9,1.1)),
                       '--com-offset',f'{rng.uniform(-.03,.03):.12f}',f'{rng.uniform(-.02,.02):.12f}',f'{rng.uniform(-.01,.01):.12f}',
                       '--obs-noise']
            if a.suite=='stress':
                argv+=['--motor-strength',str(rng.uniform(.9,1.1)),
                       '--delay-physics-steps',str(rng.integers(0,3))]
            if a.suite=='deployment':
                argv+=['--per-joint-gains','.9','1.1','--per-joint-strength','.9','1.1',
                       '--per-foot-friction','.6','1.1','--delay-physics-steps',str(rng.integers(0,3))]
            sys.argv=argv
            with (a.output/'trial-console.txt').open('a') as stream,contextlib.redirect_stdout(stream):
                result=run(parse())
            row={k:result[k] for k in ['success','reason','simulation_seconds','final_position','body_contact_fraction','calf_contact_fraction','body_loaded_contact_fraction','calf_loaded_contact_fraction','calf_peak_normal_force_n','xy_velocity_mae_m_s','yaw_velocity_mae_rad_s','mean_action_rate_squared','policy_sha256','arguments']}
            row.update(case=case['name'],seed=seed,result_file=str(Path(result['arguments']['output'])/'result.json'))
            record['trials'].append(row)
            trials.append(row)
        summary=dict(case=case['name'],passed=sum(x['success'] for x in trials),total=len(trials),
                     mean_calf_contact_fraction=float(np.mean([x['calf_contact_fraction'] for x in trials])),
                     mean_body_contact_fraction=float(np.mean([x['body_contact_fraction'] for x in trials])),
                     mean_calf_loaded_contact_fraction=float(np.mean([x['calf_loaded_contact_fraction'] for x in trials])),
                     maximum_calf_normal_force_n=max(x['calf_peak_normal_force_n'] for x in trials),
                     mean_xy_velocity_mae_m_s=float(np.mean([x['xy_velocity_mae_m_s'] for x in trials if x['xy_velocity_mae_m_s'] is not None])),
                     mean_yaw_velocity_mae_rad_s=float(np.mean([x['yaw_velocity_mae_rad_s'] for x in trials if x['yaw_velocity_mae_rad_s'] is not None])))
        record['summary'].append(summary)
        (a.output/'matrix.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(summary),flush=True)
    record['ended_local']=datetime.now().astimezone().isoformat()
    record['passed']=sum(x['success'] for x in record['trials'])
    record['total']=len(record['trials'])
    record['acceptance_scope']='first episode, finite/upright completion; smoothness and tracking assessed separately from trace'
    (a.output/'matrix.json').write_text(json.dumps(record,indent=2)+'\n')
    print(f"TOTAL: {record['passed']}/{record['total']}",flush=True)


if __name__=='__main__':main()
