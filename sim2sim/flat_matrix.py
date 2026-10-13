#!/usr/bin/env python3
"""Full-duration forward, backward, lateral, turning and stop checks."""
import argparse
import contextlib
import json
from pathlib import Path
import sys
from run import parse,run,DEFAULT_POLICY


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--policy',type=Path,default=DEFAULT_POLICY)
    p.add_argument('--config',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed-start',type=int,default=1400)
    p.add_argument('--seeds',type=int,default=4)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    commands={'forward03':[.3,0,0],'forward05':[.5,0,0],'backward':[-.3,0,0],
              'left':[0,.3,0],'right':[0,-.3,0],'yawpositive':[0,0,.5],
              'yawnegative':[0,0,-.5],'stop':[0,0,0]}
    record={'commands':commands,'seed_start':a.seed_start,'seeds_per_case':a.seeds,
            'gate':'20s first-episode survival, body XY MAE<=.2, yaw MAE<=.3; stop XY MAE<=.08 and displacement<=.5m; turns displacement<=1m',
            'summary':[],'trials':[]}
    for name,cmd in commands.items():
        trials=[]
        for seed in range(a.seed_start,a.seed_start+a.seeds):
            sys.argv=['','--policy',str(a.policy),'--config',str(a.config or a.policy.parent/'config.json'),
                      '--output',str(a.output/f'{name}-seed{seed}'),'--command',*[str(x) for x in cmd],
                      '--seconds','20','--seed',str(seed),'--initial-joint-noise','.03','--fixed-duration']
            with (a.output/'trial-console.txt').open('a') as stream,contextlib.redirect_stdout(stream):r=run(parse())
            row={k:r[k] for k in ['success','reason','simulation_seconds','final_position','xy_velocity_mae_m_s','yaw_velocity_mae_rad_s','arguments','policy_sha256']}
            row.update(case=name,seed=seed);trials.append(row);record['trials'].append(row)
        s={'case':name,'passed':sum(x['success'] for x in trials),'total':len(trials)}
        record['summary'].append(s);print(json.dumps(s),flush=True)
        (a.output/'matrix.json').write_text(json.dumps(record,indent=2)+'\n')
    record['passed']=sum(x['success'] for x in record['trials']);record['total']=len(record['trials'])
    (a.output/'matrix.json').write_text(json.dumps(record,indent=2)+'\n')
    print(f"TOTAL {record['passed']}/{record['total']}")


if __name__=='__main__':main()
