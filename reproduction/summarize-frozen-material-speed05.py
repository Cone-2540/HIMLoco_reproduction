#!/usr/bin/env python3
"""Summarize the separately prescribed 0.5m/s friction supplement on CPU.

Defaults to the repository containing this script. Missing ignored logs produce
pending entries. Uses the sibling staircase summarizer's exact schema/aggregation
definitions and data loop via AST selection; no main-report writes execute.
No simulator, Torch or GPU is imported. Original CSV fields are preserved.
"""
import argparse,ast,csv,gzip,hashlib,io,json,os,sys
from datetime import datetime
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1])
parser.add_argument('--run-log-root',type=Path,default=Path.home()/'robotics/logs/himloco-overnight-20261011')
args=parser.parse_args()
R=args.repo_root.expanduser().resolve();out=R/'reproduction/stair-frozen-material-speed05'
protocolpath=R/'reproduction/stair-material-speed05-supplement-plan.json';protocol=json.loads(protocolpath.read_text())
original=R/'reproduction/stair-final-evaluation-plan.json'
assert hashlib.sha256(original.read_bytes()).hexdigest()==protocol['original_plan_sha256']
assert protocol['speed_m_s']==.5 and protocol['reset_seeds']==[101,211,307]
# Reuse precisely the same CPU schema/hash/first-episode aggregation code,
# evaluating its definitions and data loop only; no report mutations execute.
common_source=Path(__file__).with_name('summarize-frozen-stair-validation.py')
tree=ast.parse(common_source.read_text());index=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='spec' and isinstance(n.iter,ast.Name) and n.iter.id=='SPECS')
namespace={'__file__':str(common_source)};exec(compile(ast.Module(body=tree.body[:index],type_ignores=[]),str(common_source),'exec'),namespace)
namespace['SPECS']=[{'id':f'foot_{label}_primary_speed0.5','scene':f'frozen-foot-{label}-speed05','role':'primary','speed':.5,'geometry':'final','domain':'basic','seed':1,'friction':friction,'heading':True,'dynamics':False,'reset_seeds':[101,211,307]} for label,friction in [('nominal',[.8,.6]),('low',[.45,.35]),('high',[1.,.8])]]
exec(compile(ast.Module(body=[tree.body[index]],type_ignores=[]),str(common_source),'exec'),namespace)
evals=namespace['EVAL'];raw=namespace['RAW'];rows=namespace['CSV'];pending=namespace['PENDING'];byid={e['evaluation_id']:e for e in evals};pairs=[]
for label in ['low','high']:
 left='foot_nominal_primary_speed0.5';right=f'foot_{label}_primary_speed0.5'
 if left not in raw or right not in raw:continue
 a,b=raw[left],raw[right];at,bt=a['policy']['trials'],b['policy']['trials'];bts={t['seed']:t for t in bt};ea,eb=byid[left],byid[right]
 nonfoot=lambda e:namespace['normalized_summary']({k:v for k,v in e['domain_readbacks']['initial'].items() if k!='foot_material'})
 pairing={'pair':label+'_versus_nominal','left':left,'right':right,'deliberate_difference':'foot-only friction','geometry_exact':a['geometry']==b['geometry'],'reset_seeds_exact':sorted(t['seed'] for t in at)==sorted(t['seed'] for t in bt),'initial_root_xyz_exact':all(t['per_env']['initial_root_relative_xyz_m']==bts[t['seed']]['per_env']['initial_root_relative_xyz_m'] for t in at),'aggregate_initial_pose_distribution_exact':all(t['initial_reset_distribution']==bts[t['seed']]['initial_reset_distribution'] for t in at),'thresholds_exact':a['policy']['thresholds']==b['policy']['thresholds'] and a['final_acceptance']['thresholds']==b['final_acceptance']['thresholds'],'contact_sampling_exact':a['policy']['contact_sampling']==b['policy']['contact_sampling'],'heading_control_exact':a['policy']['heading_control']==b['policy']['heading_control'],'saved_non_foot_physical_readbacks_exact':nonfoot(ea)==nonfoot(eb),'per_env_initial_quaternions_recorded':False,'case_comparisons':[]}
 for ca,cb in zip(ea['case_metrics'],eb['case_metrics']):
  pairing['case_comparisons'].append({'case_index':ca['case_index'],'case_name':ca['case_name'],'completion_change_right_minus_left':cb['counts']['completions']-ca['counts']['completions'],'both_case_gates_passed':ca['all_seed_final_traversal_passed'] and cb['all_seed_final_traversal_passed'],'both_full_failure_free':ca['full_traversal_without_failure_flags'] and cb['full_traversal_without_failure_flags'],'metric_changes_right_minus_left':{k:cb['metrics_mean_of_seed_aggregates'][k]-ca['metrics_mean_of_seed_aggregates'][k] if ca['metrics_mean_of_seed_aggregates'][k] is not None and cb['metrics_mean_of_seed_aggregates'][k] is not None else None for k in namespace['METRICS']}})
 pairs.append(pairing)
summary=[]
for e in evals:
 c=e['groups']['all']['counts'];summary.append({'material':e['specification']['id'].split('_')[1],'evaluation_id':e['evaluation_id'],'completions':c['completions'],'num_envs':c['num_envs'],'unique_noncompletions':c['unique_noncompletions'],'final_traversal_passed':e['final_traversal_passed'],'fall_stall_escape_flags':{k:c[k] for k in ['falls','stalls','lateral_escapes']},'history_base_contact_envs':c['base_contact_envs']})
ready=len(evals)==3 and not pending and not namespace['ERRORS']
master=args.run_log_root.expanduser().resolve()/'frozen-material-speed05-master.log'
limits=['This is a separately recorded0.5m/s friction supplement, added after the original nominal0.3/0.5m/s outcomes. It does not change the original frozen protocol status, primary selection, checkpoint or acceptance gates; no training or retuning follows these results.',
 'Lower and higher footfriction are compared to the0.5m/s foot-only basic nominal reference, not the domainnone all-body nominal scene.',
 'The complete16cases and every resetseed keep original95% completion,<=5% each failure fraction and zero historybasecontact gates. Stratifying paper/unseen/long/stretch never removes a failed case from the whole-matrix outcome.',
 'This tests friction sensitivity on nominal mass/COM/PD at0.5m/s; it provides no0.5m/s combined-dynamics evidence. Secondary slide680 is not tested.',
 'Actual foot shape and authored terrain material values are read back; those coefficients are not calibrated named materials or solver contact-pair coefficients. Foot-link worldXYspeed is a slip proxy, not contact-point tangent slip.',
 'Only first episodes contribute; motion excludes the firstsecond and retains failed/truncated cases. Lower action/jerk on early failures is not evidence of smoother full traversal.',
 'Physical/sensor cadence and sparse trace limits match the original report:5ms physics,20ms policy,historyages0/5/10ms,oneenv/case/seed at0.1s; no whole-batch impact or duration bound.',
 'Three resetseeds share startup physical parameters. Full per-env initial orientation/state is not saved; pairing checks only recorded initial rootpositions and aggregate pose distributions. No complete smoothness or real-robot readiness claim follows.']
doc={'schema_version':1,'status':'complete' if ready else 'partial_waiting_for_supplement_material_scenes','generated_local':datetime.now().astimezone().isoformat(),'scope':'Distinct frozen primary0.5m/s foot-only friction sensitivity; original frozen protocol stays separate','protocol':str(protocolpath.relative_to(R)),'protocol_sha256':hashlib.sha256(protocolpath.read_bytes()).hexdigest(),'protocol_snapshot':protocol,'original_freeze_hash_checks':namespace['HASHES'],'evaluations_summary':summary,'evaluations':evals,'controlled_comparisons':pairs,'pending':pending,'load_errors':namespace['ERRORS'],'all_material_scenes_passed':all(e['final_traversal_passed'] for e in evals) if ready else None,'master_log':str(master),'master_log_text':master.read_text() if master.is_file() else None,'limits':limits}
md=['# Frozen foot-material sensitivity at0.5m/s','',f"Status: {'complete' if ready else 'partial; waiting for supplement scenes'}. This is a separately recorded supplement for the frozen primarycontrol660; it leaves the original frozen protocol, selection and acceptance unchanged. Lower/higher friction are compared with the same-speed foot-only basic nominal reference.",'',
 '| Foot material | Completed | Worst case/seed | Fall/stall/escape flags | Base history/current | Whole16-case gate | Maxpause(s) |',
 '| --- | ---: | ---: | --- | --- | --- | ---: |']
for label in ['nominal','low','high']:
 e=byid.get(f'foot_{label}_primary_speed0.5')
 if not e:md.append(f'| {label} | pending | — | — | — | pending | — |');continue
 g=e['groups']['all'];c=g['counts'];md.append(f"| {label} | {c['completions']}/{c['num_envs']} | {g['minimum_case_seed_completions']}/32 | {c['falls']}/{c['stalls']}/{c['lateral_escapes']} | {c['base_contact_envs']}/{c['current_sample_base_contact_envs']} | {'PASS' if e['final_traversal_passed'] else 'FAIL'} | {g['maximum_pause_s']:.2f} |")
md+=['','## Preserved geometry strata','', '| Material | Group | Completed | Passed case/seeds | Gate |','| --- | --- | ---: | ---: | --- |']
for e in evals:
 for group in ['paper_corresponding_4','unseen_geometry_8','long_12_step_2','stretch_23cm_2']:
  z=e['groups'][group];c=z['counts'];md.append(f"| {e['specification']['friction']} | {group} | {c['completions']}/{c['num_envs']} | {z['case_seed_traversal_passes']}/{z['case_seed_count']} | {'PASS' if z['all_case_seed_traversal_passed'] else 'FAIL'} |")
md+=['','## Failed original case/seed gates','', '| Material | Seed | Case | Completed | Fall/stall/escape | Historybase | Failed gate terms |','| --- | ---: | --- | ---: | --- | ---: | --- |']
for e in evals:
 for c in e['case_metrics']:
  for r in c['seed_rows']:
   g=r['independently_recomputed_final_gate']
   if not g['traversal_passed']:md.append(f"| {e['specification']['friction']} | {r['seed']} | {c['case_name']} | {r['completions']}/32 | {r['falls']}/{r['stalls']}/{r['lateral_escapes']} | {r['base_contact_envs']} | {', '.join(g['failed_gate_terms'])} |")
md+=['','## Saved pairing and readback evidence','', '| Pair | Geometry | Root positions | Aggregate pose | Thresholds | Contactmetadata | Heading | Saved nonfoot parameters |','| --- | --- | --- | --- | --- | --- | --- | --- |']
for p in pairs:md.append('| '+' | '.join(str(p[k]) for k in ['pair','geometry_exact','initial_root_xyz_exact','aggregate_initial_pose_distribution_exact','thresholds_exact','contact_sampling_exact','heading_control_exact','saved_non_foot_physical_readbacks_exact'])+' |')
md+=['','The actual foot shape values are nominal0.8/0.6,lower0.45/0.35,higher1.0/0.8 (static/dynamic),with restitution0. Terrain authored values stay1/1 with multiply combine mode. Initial/final actual readbacks,first-episode anomaly counts,zero-action controls and nonexclusive versus unique failures are preserved in JSON.','', '## Limits','']+[f'- {s}' for s in limits]+['']
b=json.dumps(doc,indent=2,allow_nan=False).encode();buffer=io.BytesIO()
with gzip.GzipFile(fileobj=buffer,mode='wb',mtime=0) as gz:gz.write(b)
assert gzip.decompress(buffer.getvalue())==b
csvbuf=io.StringIO();w=csv.DictWriter(csvbuf,fieldnames=namespace['CSV_FIELDS'],lineterminator='\n');w.writeheader();w.writerows(rows)
for suffix,content in [('.json.gz',buffer.getvalue()),('.md',namespace['format_markdown']('\n'.join(md))),('.csv',csvbuf.getvalue())]:
 dest=out.with_suffix(suffix);tmp=Path(str(dest)+'.tmp');tmp.write_bytes(content) if isinstance(content,bytes) else tmp.write_text(content);os.replace(tmp,dest)
print(json.dumps({'status':doc['status'],'evaluations':len(evals),'pending':len(pending),'csv_rows':len(rows),'summary':summary}))
