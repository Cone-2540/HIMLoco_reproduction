#!/usr/bin/env python3
"""Summarize separate frozen speed/calf diagnostics using Python standard library.

The default project is this script's parent repository; raw ignored logs absent
from a checkout remain pending. No simulator, Torch, GPU or driver is used.
Shared AST selection reuses the sibling summarizer's aggregation definitions
and data loop without executing its report-writing statements. Original CSV
columns, first-episode failures and final gate thresholds remain unchanged.
"""
import argparse, ast, csv, gzip, hashlib, io, json, os, sys
from datetime import datetime
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--kind',required=True,choices=['speed','calf','dynamics05','geometry'])
parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1])
parser.add_argument('--run-log-root',type=Path,default=Path.home()/'robotics/logs/himloco-overnight-20261011')
args=parser.parse_args();root=args.repo_root.expanduser().resolve()
prefix='stair-frozen-speed-probe' if args.kind=='speed' else 'stair-frozen-calf-sensitivity' if args.kind=='calf' else 'stair-frozen-dynamics-speed05' if args.kind=='dynamics05' else 'stair-frozen-height-depth-probe'
protocol_path=root/'reproduction'/(prefix+'-plan.json');protocol=json.loads(protocol_path.read_text())
original_path=root/'reproduction/stair-final-evaluation-plan.json'
assert hashlib.sha256(original_path.read_bytes()).hexdigest()==protocol['original_plan_sha256']
source_path=Path(__file__).with_name('summarize-frozen-stair-validation.py')
tree=ast.parse(source_path.read_text())
index=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='spec' and isinstance(n.iter,ast.Name) and n.iter.id=='SPECS')
namespace={'__file__':str(source_path)};saved_arguments=sys.argv
try:
 sys.argv=[str(source_path),'--repo-root',str(root),'--run-log-root',str(args.run_log_root)]
 exec(compile(ast.Module(body=tree.body[:index],type_ignores=[]),str(source_path),'exec'),namespace)
finally:sys.argv=saved_arguments

def specification(label,scene,speed,geometry,seeds):
 return {'id':label,'scene':scene,'role':'primary','speed':speed,'geometry':geometry,'domain':'none','seed':1,'friction':None,'heading':True,'dynamics':False,'reset_seeds':seeds}

specs=[]
if args.kind=='speed':
 for speed in protocol['speeds_m_s']:
  tag=f'{round(speed*10):02d}';spec=specification('speed_probe_'+tag,'frozen-speed-probe-'+tag,speed,'probe',protocol['reset_seeds'])
  spec['geometry_file']=protocol['geometry'];specs.append(spec)
elif args.kind=='calf':
 for speed in [.3,.5]:
  tag='03' if speed==.3 else '05'
  specs.append(specification(f'nominal_primary_speed{speed:g}','frozen-final-speed'+tag,speed,'final',[101,211,307]))
  specs.append(specification(f'legacy_calf_primary_speed{speed:g}','frozen-calf-legacy-speed'+tag,speed,'final',[101,211,307]))
elif args.kind=='dynamics05':
 for seed in protocol['construction_seeds']:
  spec=specification(f'dynamics_seed{seed}_primary_speed0.5',f'frozen-dynamics-seed-{seed}-speed05',.5,'final',protocol['reset_seeds'])
  spec.update(domain='robust',seed=seed,friction=[.8,.6],dynamics=True);specs.append(spec)
else:
 for speed in protocol['speeds_m_s']:
  tag='03' if speed==.3 else '05';spec=specification('height_depth_probe_'+tag,'frozen-height-depth-speed'+tag,speed,'boundary',protocol['reset_seeds']);spec['geometry_file']=protocol['geometry'];specs.append(spec)
namespace['SPECS']=specs
exec(compile(ast.Module(body=[tree.body[index]],type_ignores=[]),str(source_path),'exec'),namespace)
evaluations=namespace['EVAL'];raw=namespace['RAW'];rows=namespace['CSV'];pending=namespace['PENDING'];by_id={e['evaluation_id']:e for e in evaluations}
normalize=namespace['normalized_summary'];pairs=[]
if args.kind=='speed':
 pair_specs=[(f'speed_probe_{round(left*10):02d}',f'speed_probe_{round(right*10):02d}') for left,right in zip(protocol['speeds_m_s'][:-1],protocol['speeds_m_s'][1:])]
elif args.kind=='calf':pair_specs=[(f'nominal_primary_speed{speed:g}',f'legacy_calf_primary_speed{speed:g}') for speed in [.3,.5]]
elif args.kind=='geometry':pair_specs=[('height_depth_probe_03','height_depth_probe_05')]
else:pair_specs=[]
for left_id,right_id in pair_specs:
 if left_id not in raw or right_id not in raw:continue
 left,right=raw[left_id],raw[right_id];ea,eb=by_id[left_id],by_id[right_id];lt,rt=left['policy']['trials'],right['policy']['trials'];right_trials={t['seed']:t for t in rt}
 pair={'left':left_id,'right':right_id,'deliberate_difference':'commanded forward speed' if args.kind in ['speed','geometry'] else 'legacy calf torque-speed envelope','geometry_exact':left['geometry']==right['geometry'],'reset_seeds_exact':sorted(t['seed'] for t in lt)==sorted(t['seed'] for t in rt),'initial_root_xyz_exact':all(t['per_env']['initial_root_relative_xyz_m']==right_trials[t['seed']]['per_env']['initial_root_relative_xyz_m'] for t in lt),'aggregate_initial_pose_distribution_exact':all(t['initial_reset_distribution']==right_trials[t['seed']]['initial_reset_distribution'] for t in lt),'thresholds_exact':left['policy']['thresholds']==right['policy']['thresholds'] and left['final_acceptance']['thresholds']==right['final_acceptance']['thresholds'],'contact_sampling_exact':left['policy']['contact_sampling']==right['policy']['contact_sampling'],'heading_control_exact':left['policy']['heading_control']==right['policy']['heading_control'],'foot_material_readbacks_exact':normalize(ea['domain_readbacks']['initial']['foot_material'])==normalize(eb['domain_readbacks']['initial']['foot_material']),'saved_physical_readbacks_exact':normalize(ea['domain_readbacks']['initial'])==normalize(eb['domain_readbacks']['initial']),'per_env_initial_quaternions_recorded':False,'case_comparisons':[]}
 for a,b in zip(ea['case_metrics'],eb['case_metrics']):
  pair['case_comparisons'].append({'case_index':a['case_index'],'case_name':a['case_name'],'completion_change_right_minus_left':b['counts']['completions']-a['counts']['completions'],'both_original_case_gates_passed':a['all_seed_final_traversal_passed'] and b['all_seed_final_traversal_passed'],'both_full_failure_free':a['full_traversal_without_failure_flags'] and b['full_traversal_without_failure_flags'],'metrics_change_right_minus_left':{k:b['metrics_mean_of_seed_aggregates'][k]-a['metrics_mean_of_seed_aggregates'][k] if a['metrics_mean_of_seed_aggregates'][k] is not None and b['metrics_mean_of_seed_aggregates'][k] is not None else None for k in namespace['METRICS']}})
 pairs.append(pair)

calf_audits=[]
if args.kind=='calf':
 for e in evaluations:
  cfg=e['configuration_snapshot'];legacy=e['evaluation_id'].startswith('legacy_calf')
  manifest=cfg['calf_limit_sensitivity']
  if not legacy:assert manifest is None;continue
  assert manifest['profile']=='legacy_urdf_calf_curve' and manifest['scope']=='evaluation-only gearbox sensitivity'
  assert manifest['calf_effort_limit_Nm']==35.55 and manifest['calf_velocity_limit_rad_s']==20.07 and manifest['joint_and_actuator_limits_consistent'] is True
  before=manifest['before'];assert before['actuator_effort_limit']['.*_calf_joint']==45.43 and before['saturation_effort']['.*_calf_joint']==45.43 and before['actuator_velocity_limit']['.*_calf_joint']==15.7
  assert before['actuator_effort_limit']['.*_hip_joint']==23.7 and before['actuator_effort_limit']['.*_thigh_joint']==23.7
  assert before['actuator_velocity_limit']['.*_hip_joint']==30.1 and before['actuator_velocity_limit']['.*_thigh_joint']==30.1
  assert manifest['robot_and_pd_gains']=='unchanged'
  caller=(root/'isaaclab/run.py').read_text();implementation=(root/'isaaclab/stair_randomization.py').read_text()
  assert 'calf_manifest = configure_conservative_calf_limits(cfg, args.mode)' in caller and 'def configure_conservative_calf_limits' in implementation
  calf_audits.append({'evaluation_id':e['evaluation_id'],'configuration_manifest':manifest,'frozen_call_site_sha256':hashlib.sha256((root/'isaaclab/run.py').read_bytes()).hexdigest(),'frozen_implementation_sha256':hashlib.sha256((root/'isaaclab/stair_randomization.py').read_bytes()).hexdigest(),'evidence':'Saved manifest returned by the actual configuration helper invoked before simulator construction; frozen source call/implementation hashes verified. The physical domain readback has no torque-speed or joint-limit fields, so no backend envelope measurement is claimed.'})

ready=len(evaluations)==len(specs) and not pending and not namespace['ERRORS']
master_name='frozen-speed-probe-master.log' if args.kind=='speed' else 'frozen-calf-sensitivity-master.log' if args.kind=='calf' else 'frozen-dynamics-speed05-master.log' if args.kind=='dynamics05' else 'frozen-height-depth-probe-master.log'
master=args.run_log_root.expanduser().resolve()/master_name
limits=['These are separately prescribed diagnostics after final failures were observed. They do not alter the original frozen protocol outcome, primary/secondary selection, reward, checkpoints or training; no retuning follows the observations.',
 'Original95% case/resetseed completion,<=5% each fall/stall/escape and zero historybasecontact gates remain. A passing gate can contain one failure among32; complete zero-failure traversal is reported separately.',
 'Only the saved prescribed domain/profile is tested with the external heading controller. These simulation results establish no real-robot robustness or full dynamics calibration.',
 'Motion metrics use first episodes before autoreset, excluding the firstsecond and averaging seed-level case aggregates equally. Failed/truncated trajectories remain; their lower action/contact/jerk values cannot prove smoother competent traversal.',
 'Recorded per-env rootpositions and aggregate initial pose match where declared, but full per-env initial orientation/state is not saved. Sensor/force/slip proxies and sparse0.1s trace limits match the main report; continuous video remains separate.']
if args.kind=='speed':
 limits += ['The six geometries were chosen to diagnose known failure modes. New resetseeds503/509/521 do not turn this adaptive subset into a fresh independent final test or certify an operating envelope. A passing individual speed cannot overwrite the original final FAIL.',
 'Changing speed changes trajectory duration, contact timing and heading-command responses. No monotonic speed relation or universally optimal speed is inferred.']
elif args.kind=='calf':
 limits += ['The legacy curve changes calf peak/saturation torque45.43→35.55Nm and calf motor/joint speedlimit15.70→20.07rad/s,while preserving the existing DCMotor shape,hip/thigh settings,morphology and PD gains. It is not globally a lower envelope at every speed.',
 'Neither curve is measured on the user’s Go2 EDU. The saved configuration helper/manifest confirms configuration application; physical readbacks omit torque-speed and joint-limit fields,so backend envelope measurement is unavailable.',
 'The torque×speed products are configuration-derived approximations,not measured instantaneous motor power. No delay,thermal derating,battery-state or calibrated motor-strength sensitivity is covered.']
elif args.kind=='dynamics05':
 limits += ['This is the distinct0.5m/s combined dynamics supplement,with startup massscale.8–1.25,COMoffsetxyz±.03/.02/.01m,and resetPDscale.9–1.1 at fixed nominalfootfriction. Mass/COM remain fixed across resetseeds and PD may change with autoresets.',
 'Combined mass/COM/PD variability does not isolate a single causal parameter. Initial/final physical readbacks verify distributions and inertia scaling,but do not store exact first-episode per-env gain assignments.',
 'The original0.3m/s final dynamics tests remain separate; adding the0.5m/s supplement does not change the original frozen protocol status or imply passage at either speed. No calibrated actuator delay,strength,thermal or battery sensitivity is covered.']
else:
 limits += ['The18geometries cover height18/20/23cm ×depth20/27/33cm ×up/down at.3/.5m/s. They were selected after observed final failures; fresh resetseeds601/607/613 do not make this adaptive diagnostic an independent final acceptance.',
 'The map reports completion and every original case/seed gate,not a safe operating envelope. Local passes and plausible rise/tread trends do not change the original final FAIL or certify unseen physical stairs.']
summary=[{'evaluation_id':e['evaluation_id'],'speed_m_s':e['specification']['speed'],'counts':e['groups']['all']['counts'],'final_traversal_passed':e['final_traversal_passed'],'maximum_pause_s':e['groups']['all']['maximum_pause_s']} for e in evaluations]
attempts=[]
for spec in specs:
 for directory in sorted((root/'isaaclab/logs').glob('*_'+spec['scene'])):
  result=directory/'result.json';config=directory/'config.json'
  attempts.append({'evaluation_id':spec['id'],'directory':str(directory.relative_to(root)),'config_present':config.is_file(),'config_sha256':hashlib.sha256(config.read_bytes()).hexdigest() if config.is_file() else None,'result_present':result.is_file(),'result_sha256':hashlib.sha256(result.read_bytes()).hexdigest() if result.is_file() else None,'used_as_selected_result':spec['id'] in by_id and by_id[spec['id']]['result']==str(result.relative_to(root)),'collection_status':'saved_complete_result' if result.is_file() else 'no_completed_result; failed or currently running collection, not a policy gate outcome'})
collection_failures=[]
if args.kind=='speed':
 stdout=args.run_log_root.expanduser().resolve()/'frozen-speed-probe/frozen-speed-probe-06.log'
 if stdout.is_file():
  content=stdout.read_text();lines=[line for line in content.splitlines() if any(token in line.lower() for token in ['outofmemory','out of memory','cuda error'])]
  if lines:collection_failures.append({'scene':'frozen-speed-probe-06','stdout':str(stdout),'stdout_sha256':hashlib.sha256(stdout.read_bytes()).hexdigest(),'failure':'Initial collection GPU memory allocation failed; this is not a completed policy acceptance result.','diagnostic_lines':lines,'owned_process_cleanup_record':'reproduction/overnight-owned-process-cleanup.json','retry_protocol_unchanged':True})
doc={'schema_version':1,'status':'complete' if ready else 'partial_waiting_for_diagnostic_scenes','diagnostic_kind':args.kind,'generated_local':datetime.now().astimezone().isoformat(),'protocol':str(protocol_path.relative_to(root)),'protocol_sha256':hashlib.sha256(protocol_path.read_bytes()).hexdigest(),'protocol_snapshot':protocol,'geometry_sha256':hashlib.sha256((root/protocol['geometry']).read_bytes()).hexdigest(),'original_freeze_hash_checks':namespace['HASHES'],'selection_unchanged':True,'original_suite_status_unchanged':True,'evaluations_summary':summary,'evaluations':evaluations,'controlled_comparisons':pairs,'calf_configuration_audits':calf_audits,'pending':pending,'load_errors':namespace['ERRORS'],'collection_attempts':attempts,'collection_failures':collection_failures,'master_log':str(master),'master_log_text':master.read_text() if master.is_file() else None,'limits':limits}
md=['# Frozen '+('speed probe' if args.kind=='speed' else 'legacy calf-envelope sensitivity' if args.kind=='calf' else 'combined dynamics at0.5m/s' if args.kind=='dynamics05' else 'rise/tread geometry probe'),'',f"Status: {'complete' if ready else 'partial; waiting for diagnostic scenes'}. These are separate diagnostics with the frozen primarycontrol660,zero gradientupdates and unchanged original case/seed gates. They do not replace the original final matrix or select a new checkpoint.",'',
 '| Evaluation | Speed(m/s) | Completed | Worst case/seed | Fall/stall/escape flags | Historybase | Original whole-matrix gate | Maxpause(s) |',
 '| --- | ---: | ---: | ---: | --- | ---: | --- | ---: |']
for spec in specs:
 e=by_id.get(spec['id'])
 if not e:md.append(f"| {spec['id']} | {spec['speed']} | pending | — | — | — | pending | — |");continue
 g=e['groups']['all'];c=g['counts'];md.append(f"| {e['evaluation_id']} | {spec['speed']} | {c['completions']}/{c['num_envs']} | {g['minimum_case_seed_completions']}/32 | {c['falls']}/{c['stalls']}/{c['lateral_escapes']} | {c['base_contact_envs']} | {'PASS' if e['final_traversal_passed'] else 'FAIL'} | {g['maximum_pause_s']:.2f} |")
if args.kind=='geometry' and len(evaluations)==2:
 md += ['', 'The0.3m/s map fails four descent cases; all nine ascent cases complete without failure flags. At0.5m/s all original case/resetseed gates pass with1725/1728 completions,but23cm/20cm descent has one stall and a3.72s maximum pause,and23cm/27cm descent has two fall flags. This local6-step adaptive diagnostic is neither zero-failure nor a smoothness certificate and does not cover the12-step long-descent failure in the original final matrix.']
if args.kind=='speed' and len(evaluations)==5:
 md += ['', 'Every prescribed speed fails at least one original case/resetseed gate. At0.6m/s the stretch descent is complete,but the12-step descent still has5lateral escapes across the three seeds; the matrix remainsFAIL. New seeds on an adaptive subset do not define a validated speed range.']
if args.kind=='dynamics05':
 md += ['', 'These combined-dynamics trials keep their own collection status and case gates. Any successes here do not change the original0.3m/s dynamics failures or the original frozen protocol scientific acceptance. Initial/final gain summaries may include automatic resets and are not per-first-episode gain snapshots.']
md += ['', 'Failure flags are nonexclusive. JSON/CSV retain unique noncompletions, all anomalies, zero-action controls, each case/seed gate and exposure. Command exit0 means saved collection,not scientific acceptance.', '',
 '| Evaluation | Case | Completed by resetseed | Counts fall/stall/escape/base | Original all-seed gate | Full zero-failure traversal |',
 '| --- | --- | --- | --- | --- | --- |']
for e in evaluations:
 for c in e['case_metrics']:
  count=c['counts'];show='/'.join(str(c['completion_counts_by_seed'][str(seed)]) for seed in e['specification']['reset_seeds']);flags='/'.join(str(count[k]) for k in ['falls','stalls','lateral_escapes','base_contact_envs'])
  md.append(f"| {e['evaluation_id']} | {c['case_name']} | {show} | {flags} | {'PASS' if c['all_seed_final_traversal_passed'] else 'FAIL'} | {c['full_traversal_without_failure_flags']} |")
if args.kind=='geometry':
 md += ['', '## Rise/tread boundary tables', '', 'Each cell is completed/96 across three resetseeds followed by the unchanged all-seed gate. FAIL may come from basecontact or individual failure fractions even when completion is high.']
 for e in evaluations:
  for direction in ['asc','desc']:
   md += ['', f"### {e['specification']['speed']}m/s {direction}", '', '| Rise | Tread20cm | Tread27cm | Tread33cm |', '| --- | --- | --- | --- |']
   for height in [.18,.20,.23]:
    cells=[]
    for depth in [.20,.27,.33]:
     case=next(c for c in e['case_metrics'] if c['geometry']['direction']==direction and c['geometry']['step_height']==height and c['geometry']['step_depth']==depth)
     cells.append(f"{case['counts']['completions']}/96 {'PASS' if case['all_seed_final_traversal_passed'] else 'FAIL'}")
    md.append(f"| {round(height*100)}cm | "+' | '.join(cells)+' |')
md += ['', '## Saved matching evidence','', '| Pair | Geometry | Rootpositions | Aggregatepose | Thresholds | Contactmetadata | Heading | Footmaterial | Saved physicalreadbacks |',
 '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
for p in pairs:md.append('| '+p['left']+' → '+p['right']+' | '+' | '.join(str(p[k]) for k in ['geometry_exact','initial_root_xyz_exact','aggregate_initial_pose_distribution_exact','thresholds_exact','contact_sampling_exact','heading_control_exact','foot_material_readbacks_exact','saved_physical_readbacks_exact'])+' |')
if args.kind=='speed':
 md += ['', 'The six-case subset contains16cm/27cm up/down,12-step17cm/25cm up/down and23cm/20cm stretch up/down. Resetseeds503/509/521 are new,but the subset was chosen after known final failures. This diagnostic does not certify a safe operating envelope or provide a new independent final acceptance.']
elif args.kind=='calf':
 md += ['', 'The curve configuration changes calf torque45.43→35.55Nm and velocitylimit15.70→20.07rad/s,including saturation and joint limits. Hip/thigh settings and PD are preserved. This changes the existing torque-speed curve rather than applying a globally smaller torque bound. Configuration manifests came from the actual helper call before construction; physical readbacks do not contain torque-speed/joint-limit fields. These are uncalibrated model choices for Go2 EDU,not hardware measurements.']
elif args.kind=='dynamics05':
 md += ['', 'Three new constructionseeds71/73/79 redraw startup mass/COM. Footfriction stays0.8/0.6 and terrain-authored1/1multiply. PDgains resample from nominal defaults at resets. Actual massratio,COMoffset,Kp/Kdscale and inertia-scaling checks are preserved for initial/final readbacks; they do not establish exact per-env episode gain maps.']
else:
 md += ['', 'This adaptively selected boundary map covers18fixed6-step cases:18/20/23cm rise×20/27/33cm tread×up/down,no nosing,at0.3/0.5m/s,seeds601/607/613. New resetseeds and individual local passes do not replace the independent final matrix or certify a safe operating envelope.']
if collection_failures:
 md += ['', '## Preserved collection failure and retry', '',
  'The first0.6m/s collection failed to allocate GPUmemory and saved no result. Its configuration directory and stdout SHA-256 are retained in JSON. The run owner verified and stopped completed task-owned orphan simulation processes,without driver changes or container reset; the unchanged protocol retry saved a complete result. The OOM is a collection failure,not a completed policy gate outcome.',
  '', 'Cleanup record: `reproduction/overnight-owned-process-cleanup.json`. The first failed collection remains in `collection_attempts` alongside the selected complete retry.']
md += ['', '## Limits','']+[f'- {s}' for s in limits]+['']
serialized=json.dumps(doc,indent=2,allow_nan=False).encode();buf=io.BytesIO()
with gzip.GzipFile(fileobj=buf,mode='wb',mtime=0) as stream:stream.write(serialized)
assert gzip.decompress(buf.getvalue())==serialized
csvbuf=io.StringIO();writer=csv.DictWriter(csvbuf,fieldnames=namespace['CSV_FIELDS'],lineterminator='\n');writer.writeheader();writer.writerows(rows)
output=root/'reproduction'/prefix
for suffix,content in [('.json.gz',buf.getvalue()),('.md',namespace['format_markdown']('\n'.join(md))),('.csv',csvbuf.getvalue())]:
 dest=output.with_suffix(suffix);temp=Path(str(dest)+'.tmp');temp.write_bytes(content) if isinstance(content,bytes) else temp.write_text(content);os.replace(temp,dest)
print(json.dumps({'status':doc['status'],'kind':args.kind,'evaluations':len(evaluations),'pending':len(pending),'csv_rows':len(rows),'summary':summary}))
