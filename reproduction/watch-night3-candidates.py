#!/usr/bin/env python3
"""CPU-only development evaluation while the existing GPU learner continues."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
PY=Path.home()/'robotics/envs/himloco-mujoco-py311/bin/python'
DEADLINE=datetime.fromisoformat('2026-10-14T07:20:00+08:00')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-name',required=True)
    p.add_argument('--artifact',required=True)
    p.add_argument('--iterations',type=int,nargs='+',required=True)
    a=p.parse_args()
    output=ROOT/'artifacts'/a.artifact
    scores_path=ROOT/'reproduction'/f'night3-{a.run_name}-development-scores.json'
    scores=json.loads(scores_path.read_text()) if scores_path.exists() else []
    for iteration in a.iterations:
        while True:
            if datetime.now().astimezone()>=DEADLINE:raise SystemExit('Deadline reached')
            paths=list((ROOT/'isaaclab/logs').glob('*_'+a.run_name))
            if len(paths)>1:raise SystemExit('Ambiguous simulator source')
            if paths and (paths[0]/f'model_{iteration}.pt').is_file():
                if time.time()-(paths[0]/f'model_{iteration}.pt').stat().st_mtime>3:break
            if paths and (paths[0]/'result.json').is_file() and not (paths[0]/f'model_{iteration}.pt').is_file():
                raise SystemExit(f'Training ended without checkpoint {iteration}')
            time.sleep(10)
        source=paths[0]
        output.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source/'config.json',output/'config.json')
        policy=output/f'policy_{iteration}.pt'
        if not policy.exists():
            subprocess.run([str(PY),str(ROOT/'sim2sim/export.py'),str(source/f'model_{iteration}.pt'),
                            '--config',str(output/'config.json'),'--output',str(policy)],cwd=ROOT,check=True)
        summary={'iteration':iteration,'source':str(source),'policy':str(policy),'development_only':True}
        for suite in ['deployment','flat8']:
            directory=Path.home()/'robotics/logs'/f'night3-{a.run_name}-iter{iteration}-{suite}'
            if not (directory/'matrix.json').exists():
                command=[str(PY),str(ROOT/'sim2sim'/('matrix.py' if suite=='deployment' else 'flat_matrix.py')),
                         '--policy',str(policy),'--config',str(output/'config.json'),'--output',str(directory),
                         '--seeds','8' if suite=='deployment' else '4']
                if suite=='deployment':command+=['--suite','deployment']
                subprocess.run(command,cwd=ROOT,check=True)
            matrix=json.loads((directory/'matrix.json').read_text())
            summary[suite]={'passed':matrix['passed'],'total':matrix['total'],'cases':matrix['summary'],'directory':str(directory)}
            shutil.copyfile(directory/'matrix.json',ROOT/'reproduction'/f'night3-{a.run_name}-iter{iteration}-{suite}.json')
        scores=[s for s in scores if s['iteration']!=iteration]+[summary]
        scores.sort(key=lambda s:s['iteration'])
        scores_path.write_text(json.dumps(scores,indent=2)+'\n')
        print('CANDIDATE_SCORE '+json.dumps(summary),flush=True)
    print('Development monitoring finished; final reserved seeds still required',flush=True)


if __name__=='__main__':main()
