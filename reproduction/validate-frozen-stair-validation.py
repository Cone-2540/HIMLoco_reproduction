#!/usr/bin/env python3
"""Cross-check the frozen MD/CSV/JSON.gz data against local raw first episodes.

Uses only the Python standard library and never imports simulator/GPU packages.
Run after its summarizer; --supplement selects material0.5m/s and
--diagnostic speed/calf selects the separate diagnostic reports.
The repository defaults to the parent of reproduction/ from any working directory.
A partial report with absent ignored logs remains pending rather than passing.
"""
import argparse,csv,gzip,hashlib,json,math,statistics,sys
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1])
group=parser.add_mutually_exclusive_group()
group.add_argument('--supplement',action='store_true')
group.add_argument('--diagnostic',choices=['speed','calf','dynamics05','geometry'])
args=parser.parse_args()
R=args.repo_root.expanduser().resolve()
prefix='stair-frozen-speed-probe' if args.diagnostic=='speed' else 'stair-frozen-calf-sensitivity' if args.diagnostic=='calf' else 'stair-frozen-dynamics-speed05' if args.diagnostic=='dynamics05' else 'stair-frozen-height-depth-probe' if args.diagnostic=='geometry' else 'stair-frozen-material-speed05' if args.supplement else 'stair-frozen-final-validation'
P=R/'reproduction'/prefix
z=P.with_suffix('.json.gz').read_bytes();data=gzip.decompress(z);x=json.loads(data);assert json.loads(json.dumps(x,allow_nan=False))==x
rows=list(csv.DictReader(P.with_suffix('.csv').open()));seen=set();checks=0
for e in x['evaluations']:
 raw=json.loads((R/e['result']).read_text());assert hashlib.sha256((R/e['result']).read_bytes()).hexdigest()==e['result_sha256'];checks+=1
 tby={t['seed']:t for t in raw['policy']['trials']};n=len(e['case_metrics']);assert len(tby)==3
 assert len(e['failure_endpoints'])==sum(sum(not a for a in t['per_env']['completed']) for t in tby.values());checks+=1
 assert all(e['all_first_episode_anomaly_counts'][k]==sum(t[k] for t in tby.values()) for k in e['all_first_episode_anomaly_counts']);checks+=1
 summaryrows=[r for r in rows if r['evaluation_id']==e['evaluation_id']];assert len(summaryrows)==n*3
 for c in e['case_metrics']:
  ci=c['case_index'];srows=[r for r in summaryrows if int(r['case_index'])==ci];assert len(srows)==3
  for r in srows:
   seed=int(r['reset_seed']);key=(e['evaluation_id'],seed,ci);assert key not in seen;seen.add(key)
   trial=tby[seed];source=trial['cases'][ci];envs=range(ci*32,(ci+1)*32)
   for key0,source0 in [('completed','completions'),('fall','falls'),('stall','stalls'),('lateral_escape','lateral_escapes')]:
    assert sum(trial['per_env'][key0][i] for i in envs)==int(r[source0])==source[source0];checks+=1
   assert int(r['unique_noncompletions'])==32-int(r['completions'])
   gate=(int(r['completions'])>=31 and int(r['falls'])<=1 and int(r['stalls'])<=1 and int(r['lateral_escapes'])<=1 and int(r['base_contact_envs'])==0 and trial['failure_reason'] is None)
   assert str(gate)==r['final_traversal_passed'];checks+=1
  assert c['counts']['completions']==sum(int(r['completions']) for r in srows)
  for key,value in c['metrics_mean_of_seed_aggregates'].items():
   vals=[t['cases'][ci]['metrics'].get(key) for t in tby.values()];vals=[v for v in vals if v is not None]
   expected=statistics.fmean(vals) if vals else None;assert value==expected;checks+=1
 for group in e['groups'].values():
  case_seed_gate=[r for r in summaryrows if int(r['case_index']) in group['case_indices']]
  assert group['all_case_seed_traversal_passed']==all(r['final_traversal_passed']=='True' for r in case_seed_gate)
  assert group['counts']['num_envs']==32*len(case_seed_gate)
  assert group['counts']['unique_noncompletions']==sum(int(r['unique_noncompletions']) for r in case_seed_gate);checks+=3
 assert e['final_traversal_passed']==e['groups']['all']['all_case_seed_traversal_passed'];checks+=1
assert len(seen)==len(rows);hash_checks=x.get('freeze',{}).get('hash_checks',x.get('original_freeze_hash_checks',[]));assert len(hash_checks)==33 and all(c['matches'] for c in hash_checks if c['actual_sha256'] is not None)
if args.supplement or args.diagnostic:
 assert x['protocol_snapshot']['original_plan_sha256']==hashlib.sha256((R/'reproduction/stair-final-evaluation-plan.json').read_bytes()).hexdigest()
 assert hashlib.sha256((R/x['protocol']).read_bytes()).hexdigest()==x['protocol_sha256']
 assert x['protocol_snapshot']['checkpoint']=='artifacts/go2-stairs-control660/model_660.pt'
 if x['status']=='complete':
  expected_rows,expected_evals=(90,5) if args.diagnostic=='speed' else (192,4) if args.diagnostic=='calf' else (108,2) if args.diagnostic=='geometry' else (144,3)
  assert len(rows)==expected_rows and len(x['evaluations'])==expected_evals and not x['pending']
else:
 assert x['freeze']['execution_copy_equal'] in (None,True)
 assert x['scope']['secondary_scope']=='nominal two speeds only' and x['scope']['case_grouping_preserves_all_original_gates'] is True
 assert x['freeze']['primary_checkpoint']=='artifacts/go2-stairs-control660/model_660.pt' and x['freeze']['no_retuning_from_final_matrix'] is True
 if x['status']=='complete':
  assert len(rows)==552 and len(x['evaluations'])==12 and not x['pending']
  assert x['scientific_acceptance']=='FAIL' and x['all_primary_stair_scenes_passed'] is False
  assert x['flat_regression']['original_flat_gate_passed'] is False
print(json.dumps({'status':x['status'],'evaluations':len(x['evaluations']),'csv_seed_rows':len(rows),'independent_cross_checks':checks,'gzip_lossless':True,'frozen_hash_checks':len(hash_checks),'pending':len(x['pending'])}))
