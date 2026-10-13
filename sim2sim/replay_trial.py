#!/usr/bin/env python3
"""Replay a saved matrix trial's exact domain parameters, including failures."""
import argparse
import json
from pathlib import Path
import sys
from run import parse,run


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('matrix',type=Path)
    p.add_argument('--case',required=True)
    p.add_argument('--seed',type=int,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--video',action='store_true')
    a=p.parse_args()
    records=[t for t in json.loads(a.matrix.read_text())['trials'] if t['case']==a.case and t['seed']==a.seed]
    if len(records)!=1:p.error('Need one exact case and seed')
    t=records[0];argv=['','--output',str(a.output)]
    if a.video:argv.append('--video')
    def number(value):return f'{value:.12f}' if isinstance(value,float) else str(value)
    for key,value in t['arguments'].items():
        if key=='output':continue
        flag='--'+key.replace('_','-')
        if isinstance(value,bool):
            if value:argv.append(flag)
        elif value is not None:
            argv.append(flag)
            argv.extend([number(v) for v in value] if isinstance(value,list) else [number(value)])
    sys.argv=argv;r=run(parse())
    audit={'case':a.case,'seed':a.seed,'original_success':t['success'],'replay_success':r['success'],
           'original_calf_force':t.get('calf_peak_normal_force_n'),'replay_calf_force':r['calf_peak_normal_force_n'],
           'matrix':str(a.matrix.resolve()),'output':str(a.output.resolve())}
    (a.output/'replay-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit),flush=True)


if __name__=='__main__':main()
