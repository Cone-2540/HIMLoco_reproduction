#!/usr/bin/env python3
"""Summarize the frozen staircase protocol using Python standard library only.

Run from any directory; the default repository is this script's parent project.
Missing ignored simulator logs produce pending entries. The program verifies the
saved freeze hashes, recomputes case/reset-seed gates, preserves all failures,
and writes the existing MD/CSV/JSON.gz report fields without changing thresholds.
It never imports the simulator or Torch and never trains, retunes or uses GPUs.

Example: python3 reproduction/summarize-frozen-stair-validation.py
"""
import argparse, csv, gzip, hashlib, io, json, math, os, re, statistics, subprocess, sys, tempfile
from datetime import datetime
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1],help='Repository root; defaults to the parent of reproduction/')
parser.add_argument('--run-log-root',type=Path,default=Path.home()/'robotics/logs/himloco-overnight-20261011',help='Directory containing frozen-validation-master.log and frozen-validation/')
args=parser.parse_args()
ROOT=args.repo_root.expanduser().resolve(); LOG=ROOT/'isaaclab/logs'
OUT=ROOT/'reproduction/stair-frozen-final-validation'
MASTER=args.run_log_root.expanduser().resolve()/'frozen-validation-master.log'
FROZEN_COPY=MASTER.parent/'frozen-validation/frozen-evaluation-plan.json'
PLANFILE=ROOT/'reproduction/stair-final-evaluation-plan.json'
plan=json.loads(PLANFILE.read_text()); acceptance=json.loads((ROOT/plan['acceptance_file']).read_text())
assert plan['status']=='frozen' and plan['no_retuning_from_final_matrix'] is True
assert plan['checkpoint']=='artifacts/go2-stairs-control660/model_660.pt'
assert plan['secondary_checkpoint']=='artifacts/go2-stairs-slide680/model_680.pt'
METRICS=['action_delta_rms','action_second_delta_rms','linear_jerk_rms_m_s3','linear_acceleration_rms_m_s2',
 'current_sample_shank_contact_step_fraction','shank_contact_step_fraction','current_sample_foot_slip_fraction',
 'foot_slip_fraction','xy_tracking_rmse_m_s','yaw_tracking_mae_rad_s','heading_abs_error_rad','lateral_abs_error_m',
 'flight_pause_fraction','current_sample_contact_foot_horizontal_speed_m_s','torque_saturation_fraction','roll_rms_rad','roll_peak_rad']
COUNT_KEYS=['num_envs','completions','falls','stalls','lateral_escapes','base_contact_envs','current_sample_base_contact_envs']
ANOMALIES=['timeouts_before_completion','nonfinite_envs','invalid_physics_envs','invalid_start_envs']
CSV_FIELDS=['evaluation_id', 'role', 'scene', 'speed_m_s', 'construction_seed', 'domain_profile', 'heading_control', 'reset_seed', 'case_index', 'case_name', 'case_group', 'direction', 'step_height_m', 'step_depth_m', 'nosing_m', 'num_steps', 'num_envs', 'completions', 'falls', 'stalls', 'lateral_escapes', 'base_contact_envs', 'current_sample_base_contact_envs', 'unique_noncompletions', 'final_traversal_passed', 'failed_gate_terms', 'maximum_pause_s', 'action_delta_rms', 'action_second_delta_rms', 'linear_jerk_rms_m_s3', 'linear_acceleration_rms_m_s2', 'current_sample_shank_contact_step_fraction', 'shank_contact_step_fraction', 'current_sample_foot_slip_fraction', 'foot_slip_fraction', 'xy_tracking_rmse_m_s', 'yaw_tracking_mae_rad_s', 'heading_abs_error_rad', 'lateral_abs_error_m', 'flight_pause_fraction', 'current_sample_contact_foot_horizontal_speed_m_s', 'torque_saturation_fraction', 'roll_rms_rad', 'roll_peak_rad']

def read(path):return json.loads(path.read_text()) if path and path.is_file() else None

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def relative(path):
 try:return str(path.relative_to(ROOT))
 except ValueError:return str(path)

def avg(values):
 values=[v for v in values if v is not None];return statistics.fmean(values) if values else None

def means(rows):return {k:avg(r['metrics'].get(k) for r in rows) for k in METRICS}

def counts(rows):
 d={k:sum(r.get(k,0) for r in rows) for k in COUNT_KEYS};d['unique_noncompletions']=d['num_envs']-d['completions'];return d

def format_markdown(text):
 """Improve prose spacing without changing CSV fields, IDs or code spans."""
 replacements={
  'primarycontrol660':'primary control660','policycontrol660':'policy control660',
  'zerogradientupdates':'zero gradient updates','zero gradientupdates':'zero gradient updates',
  '12standard':'12 standard','resetseeds':'reset seeds','resetseed':'reset seed',
  'constructionseeds':'construction seeds','gradientupdates':'gradient updates',
  'firstsecond':'first second','headingfeedback':'heading feedback','yawrate':'yaw rate',
  'rootyawtarget0':'root yaw target 0','lateral-position':'lateral position',
  'footfriction':'foot friction','PDgains':'PD gains','PDscale':'PD scale',
  'massscale':'mass scale','COMoffset':'COM offset','footmaterial':'foot material',
  'Footmaterial':'Foot material','Rootpositions':'Root positions','rootpositions':'root positions',
  'Aggregatepose':'Aggregate pose','Contactmetadata':'Contact metadata',
  'contactmetadata':'contact metadata','physicalreadbacks':'physical readbacks',
  'historybasecontact':'history base contact','historybase':'history base',
  'Historybase':'History base','whole16-case':'whole 16-case',
  'whole16cases':'whole 16 cases','whole6gate':'whole 6-case gate',
  'all16cases':'all 16 cases','all18case':'all 18 case','gatePASS':'gate PASS',
  'gateFAIL':'gate FAIL','matrixFAIL':'matrix FAIL','matrix remainsFAIL':'matrix remains FAIL',
  '32envs':'32 envs','32env':'32 env','16cases':'16 cases','18geometries':'18 geometries',
  '12step':'12 step','6step':'6 step','oneenv':'one env','percase':'per case',
  'tracecadence':'trace cadence','historyages':'history ages','full-duration':'full duration',
  'first-episode':'first episode','zero-failure':'zero failure','failure-free':'failure free',
 }
 def prose(segment):
  for old,new in replacements.items():segment=segment.replace(old,new)
  segment=re.sub(r'\bat(?=\d)', 'at ', segment)
  segment=re.sub(r'(?<![\w.])(\d+(?:\.\d+)?)(m/s|rad/s|Nm|rad|cm|mm|ms|envs|cases|flags|falls|fall|stall|s)\b', r'\1 \2', segment)
  segment=re.sub(r'\b(at least|at most|seeds|Physics|physics|policy)(?=\d)', r'\1 ', segment)
  return segment
 return ''.join(segment if i%2 else prose(segment) for i,segment in enumerate(re.split(r'(`[^`]*`)',text)))

def atomic(path,content,binary=False):
 tmp=Path(str(path)+'.tmp');tmp.write_bytes(content) if binary else tmp.write_text(content);os.replace(tmp,path)

HASHES=[]
for name,path_key,hash_key in [('primary_checkpoint','checkpoint','checkpoint_sha256'),('secondary_checkpoint','secondary_checkpoint','secondary_checkpoint_sha256'),('acceptance','acceptance_file','acceptance_sha256'),('final_geometry','final_geometry_file','final_geometry_sha256'),('heading_geometry','heading_geometry_file','heading_geometry_sha256')]:
 p=ROOT/plan[path_key];actual=sha(p) if p.is_file() else None;HASHES.append({'label':name,'file':relative(p),'expected_sha256':plan[hash_key],'actual_sha256':actual,'matches':actual==plan[hash_key]})
for p,h in plan['implementation_source_sha256'].items():
 actual=sha(ROOT/p) if (ROOT/p).is_file() else None;HASHES.append({'label':'runtime_source','file':p,'expected_sha256':h,'actual_sha256':actual,'matches':actual==h})
assert all(c['matches'] for c in HASHES if c['actual_sha256'] is not None), 'Frozen hash changed; aggregation halted'
frozen_copy=read(FROZEN_COPY)
if frozen_copy is not None:assert frozen_copy==plan, 'Execution plan copy differs from current frozen plan'
FINAL_SPEC=read(ROOT/plan['final_geometry_file']);HEAD_SPEC=read(ROOT/plan['heading_geometry_file'])
SPECS=[]
for speed in [.3,.5]:
 name='frozen-final-speed'+('03' if speed==.3 else '05')
 for role in ['primary','secondary']:
  SPECS.append({'id':f'nominal_{role}_speed{speed:g}','scene':name,'role':role,'speed':speed,'geometry':'final','domain':'none','seed':1,'friction':None,'heading':True,'dynamics':False,'reset_seeds':[101,211,307]})
for label,friction in [('nominal',[.8,.6]),('low',[.45,.35]),('high',[1.,.8])]:
 SPECS.append({'id':f'foot_{label}_primary_speed0.3','scene':f'frozen-foot-{label}-speed03','role':'primary','speed':.3,'geometry':'final','domain':'basic','seed':1,'friction':friction,'heading':True,'dynamics':False,'reset_seeds':[101,211,307]})
for label,heading in [('heading-control',True),('zero-yaw',False)]:
 SPECS.append({'id':f'standard_{label}_primary_speed0.3','scene':f'frozen-standard-{label}','role':'primary','speed':.3,'geometry':'heading','domain':'none','seed':1,'friction':None,'heading':heading,'dynamics':False,'reset_seeds':[401,409,419]})
for seed in [71,73,79]:
 SPECS.append({'id':f'dynamics_seed{seed}_primary_speed0.3','scene':f'frozen-dynamics-seed-{seed}-speed03','role':'primary','speed':.3,'geometry':'final','domain':'robust','seed':seed,'friction':[.8,.6],'heading':True,'dynamics':True,'reset_seeds':[101,211,307]})

def discover(spec):
 dirs=sorted(LOG.glob('*_'+spec['scene']))
 if not dirs:return None,None
 directory=dirs[-1]
 if spec['role']=='secondary':
  paths=sorted(directory.glob('candidates/*/result.json'))
  return (paths[0] if paths else None),directory
 return next((directory/name for name in ['result.json','primary-result.json'] if (directory/name).is_file()),None),directory

def geometry_check(spec,actual):
 src=read(ROOT/spec['geometry_file']) if spec.get('geometry_file') else FINAL_SPEC if spec['geometry']=='final' else HEAD_SPEC
 assert len(src)==len(actual)
 for requested,g in zip(src,actual):
  for r,a,default in [('direction','direction',None),('height','step_height',None),('depth','step_depth',None),('nosing','nosing',0.),('num_steps','num_steps',6),('width','width',1.2)]:
   assert g[a]==requested.get(r,default),(requested,r,g[a])
 return src

def groupdefs(spec,geom):
 n=len(geom);groups={'all':list(range(n))}
 if spec['geometry']=='final':groups.update({'paper_corresponding_4':list(range(4)),'unseen_geometry_8':list(range(4,12)),'long_12_step_2':[12,13],'stretch_23cm_2':[14,15],'nonstretch_14':list(range(14))})
 elif spec['geometry']=='heading':groups['standard_12']=list(range(n))
 elif spec['geometry']=='boundary':groups.update({'height18cm':[i for i,g in enumerate(geom) if g['step_height']==.18],'height20cm':[i for i,g in enumerate(geom) if g['step_height']==.20],'height23cm':[i for i,g in enumerate(geom) if g['step_height']==.23]})
 elif spec['geometry']=='probe':groups.update({'paper_corresponding_2':[0,1],'long_12_step_2':[2,3],'stretch_23cm_2':[4,5]})
 groups.update({name:[i for i,g in enumerate(geom) if g['direction']==direction] for name,direction in [('ascending','asc'),('descending','desc')]})
 return groups

def reevaluate(case,trial):
 n=case['num_envs'];fraction=case['completions']/n if n else 0
 assert abs(case['completion_fraction']-fraction)<1e-7
 fractions={k:case[k]/n for k in ['falls','stalls','lateral_escapes']}
 reasons=[]
 if fraction<acceptance['core_completion_fraction_each_case_each_seed']:reasons.append('completion_fraction')
 if n<acceptance['minimum_environments_per_case_per_seed']:reasons.append('minimum_environments')
 for k,a in [('falls','maximum_fall_fraction_each_case_each_seed'),('stalls','maximum_stall_fraction_each_case_each_seed'),('lateral_escapes','maximum_lateral_escape_fraction_each_case_each_seed')]:
  if fractions[k]>acceptance[a]:reasons.append(k)
 if case['base_contact_envs']>acceptance['maximum_base_contact_envs']:reasons.append('history_base_contact')
 if trial.get('failure_reason') is not None:reasons.append('trial_failure_reason')
 return {'traversal_passed':not reasons,'failure_fractions':fractions,'failed_gate_terms':reasons,'motion_improvement_needed':case['metrics'].get('longest_flight_pause_s',0)>acceptance['smoothness']['long_flight_pause_review_threshold_s']}

def normalized_summary(value):
 if isinstance(value,dict):return {k:normalized_summary(v) for k,v in value.items() if k not in ['samples_first_envs','stage_root_layer_identifier']}
 if isinstance(value,list):return [normalized_summary(v) for v in value]
 return value

def physical_audit(spec,directory):
 audits={}
 for when in ['initial','final']:
  d=read(directory/f'domain-parameters-{when}.json')
  if d is None:
   audits[when]={'status':'pending_readback'};continue
  m=d['foot_material'];expected=spec['friction'] or [.8,.6]
  assert m['status']=='available' and m['body_names']==['FL_foot','FR_foot','RL_foot','RR_foot']
  for label,value in [('static_friction',expected[0]),('dynamic_friction',expected[1]),('restitution',0.)]:
   z=m[label];assert z['finite'] and z['nonfinite_count']==0 and all(abs(z[key]-value)<1e-6 for key in ['min','max'])
  terrain=d['terrain_material'];assert terrain['status']=='available' and terrain['collision_mesh_count']>=1
  terrain_checks=[]
  for mesh in terrain['collision_meshes']:
   binding=mesh['physics_binding'];assert binding['status']=='available'
   attrs=binding['attributes']
   for label,value in [('static_friction',1.),('dynamic_friction',1.),('restitution',0.),('friction_combine_mode','multiply')]:
    assert attrs[label]['status']=='available' and attrs[label]['value']==value
   terrain_checks.append({'mesh':mesh['mesh_prim_path'],'material':binding['material_prim_path'],'static_friction':1.,'dynamic_friction':1.,'restitution':0.,'friction_combine_mode':'multiply'})
  body=d['base_mass_kg']['observed'];assert body['finite'] and body['min']>0
  com=d['base_com']['position_m'];assert com['finite']
  pd=d['actuator_pd']['groups']['base_legs'];k=pd['stiffness']['observed'];kd=pd['damping']['observed'];assert k['finite'] and kd['finite'] and k['min']>0 and kd['min']>0
  summary={field:{key:val for key,val in value.items() if key!='samples_first_envs'} for field,value in [('base_mass_kg',body),('base_com_position_m',com),('pd_stiffness',k),('pd_damping',kd)]}
  if spec['dynamics']:
   summary['base_mass_observed_to_default_ratio']=d['base_mass_kg']['observed_to_default_ratio']
   summary['base_com_default_and_offset']=d['base_com']['default_and_offset']
   summary['pd_stiffness_observed_to_default_ratio']=pd['stiffness']['default'].get('observed_to_default_ratio')
   summary['pd_damping_observed_to_default_ratio']=pd['damping']['default'].get('observed_to_default_ratio')
   ratio=d['base_mass_kg']['observed_to_default_ratio'];assert ratio['status']=='available'
   assert ratio['values']['finite'] and ratio['values']['min']>=.8-1e-6 and ratio['values']['max']<=1.25+1e-6
   offset=d['base_com']['default_and_offset'];assert offset['status']=='available' and offset['offset_m']['finite']
   bounds=[[-.03,.03],[-.02,.02],[-.01,.01]]
   assert all(offset['offset_min_xyz_m'][i]>=v[0]-1e-6 and offset['offset_max_xyz_m'][i]<=v[1]+1e-6 for i,v in enumerate(bounds))
   for field in ['pd_stiffness_observed_to_default_ratio','pd_damping_observed_to_default_ratio']:
    observed_ratio=summary[field];assert observed_ratio and observed_ratio['finite'] and observed_ratio['min']>=.9-1e-6 and observed_ratio['max']<=1.1+1e-6
   inertia=d['base_inertia_kg_m2']['mass_scaled_inertia_check'];assert inertia['status']=='available' and inertia['recompute_inertia'] is True and inertia['max_abs_error_from_default_times_mass_ratio_kg_m2']<1e-6
   summary['mass_scaled_inertia_check']=inertia
  audits[when]={'status':'available_and_verified','foot_names':m['body_names'],'foot_static_dynamic_pair':expected,'foot_restitution':0.,'terrain_authored_materials':terrain_checks,'physical_summary':summary,'scope':'Shape readbacks and authored terrain binding values; not backend effective contact-pair coefficients. Dynamics initial/final summaries may reflect gains after autoresets.'}
 return audits

def sampled_peaks(trials,policy):
 peaks={k:None for k in ['current','history']};active_rows=0
 for t in trials:
  for trace in t['trace']:
   if trace['time_s']<1.:continue
   for j,active in enumerate(trace['active']):
    if not active:continue
    active_rows+=1
    for kind,field in [('current','leg_current_normal_force_norm_n'),('history','leg_history_peak_normal_force_norm_n')]:
     vectors=trace.get(field)
     if vectors is None or vectors[j] is None:continue
     for bi,value in enumerate(vectors[j]):
      if value is not None and (peaks[kind] is None or value>peaks[kind]['force_n']):peaks[kind]={'force_n':value,'body':policy['leg_body_names'][bi],'seed':t['seed'],'case_index':trace['case_ids'][j],'env_id':trace['env_ids'][j],'time_s':trace['time_s']}
 return {'active_post_1s_representative_rows':active_rows,'maximum_sampled_named_leg_normal_force_n':peaks,'trace_stride_policy_steps':5,'trace_cadence_s':.1,'scope':'One representative environment per case/reset seed; these are sparse sampled maxima, not whole-batch peaks, impulse or duration.'}

RAW={};EVAL=[];PENDING=[];CSV=[];ERRORS=[]
for spec in SPECS:
 path,directory=discover(spec)
 if path is None:
  PENDING.append({'evaluation_id':spec['id'],'scene':spec['scene'],'role':spec['role'],'status':'pending'});continue
 try:
  x=read(path);p=x['policy'];ts=p['trials'];cfg=read(directory/'config.json');source=geometry_check(spec,x['geometry'])
  expected_checkpoint=plan['checkpoint' if spec['role']=='primary' else 'secondary_checkpoint']
  result_checkpoint=x.get('checkpoint')
  if result_checkpoint is None:
   assert spec['role']=='primary';result_checkpoint=cfg['checkpoint']
  assert result_checkpoint.removeprefix('/workspace/himloco/')==expected_checkpoint
  assert cfg['checkpoint'].removeprefix('/workspace/himloco/')==plan['checkpoint']
  assert p['command_forward_speed_m_s']==spec['speed'] and sorted(t['seed'] for t in ts)==spec['reset_seeds']
  assert cfg['seed']==spec['seed'] and cfg['num_envs']==len(x['geometry'])*32
  assert cfg['evaluation_seconds']==40 and cfg['physics_dt']==.005 and cfg['policy_decimation']==4
  assert cfg['evaluation_seeds']==spec['reset_seeds'] and cfg['evaluation_randomized'] is True
  assert p['heading_control']['enabled']==spec['heading'] and p['dynamics_randomized']==spec['dynamics']
  assert cfg['evaluation_dynamics_randomized']==spec['dynamics'] and cfg['friction_override']==spec['friction']
  assert cfg['stair_reward']['profile']==plan['reward_profile']
  domain=cfg['domain_randomization'];assert (domain is None)==(spec['domain']=='none')
  if domain is not None:assert domain['profile']==spec['domain']
  a=x['final_acceptance'];assert a['thresholds']=={'completion_fraction':.95,'maximum_failure_fraction':.05,'maximum_flight_pause_s_for_motion_flag':1.,'maximum_base_contact_envs':0}
  assert len(ts)>=acceptance['minimum_distinct_reset_seeds'] and len({t['seed'] for t in ts})==len(ts)
  gates={(g['seed'],g['case_index']):g for g in a['cases']};assert len(gates)==len(ts)*len(source)
  cases=[];failed=[];anomalies={k:sum(t[k] for t in ts) for k in ANOMALIES}
  for ci,geom in enumerate(x['geometry']):
   rows=[t['cases'][ci] for t in ts];seedrows=[];durations=[];times=[]
   for t,r in zip(ts,rows):
    assert r['case_index']==ci and r['num_envs']==32 and r['geometry']==geom and t['requested_duration_s']==40
    g=reevaluate(r,t);saved=gates[t['seed'],ci];assert all(g[k]==saved[k] for k in ['traversal_passed','failure_fractions','motion_improvement_needed'])
    q=t['per_env'];env_ids=range(ci*32,(ci+1)*32)
    for key,rowkey in [('completed','completions'),('fall','falls'),('stall','stalls'),('lateral_escape','lateral_escapes')]:assert sum(bool(q[key][eid]) for eid in env_ids)==r[rowkey]
    for eid in env_ids:
     durations.append(q['first_episode_measured_duration_s'][eid])
     if q['completed'][eid]:times.append(q['completion_time_s'][eid])
     else:failed.append({'seed':t['seed'],'case_index':ci,'env_id':eid,'failure_flags_nonexclusive':[k for k in ['fall','stall','lateral_escape'] if q[k][eid]],'terminal_root_relative_xyz_m':q['last_measured_root_relative_xyz_m'][eid],'terminal_feet_relative_xyz_m':q['last_measured_feet_relative_xyz_m'][eid],'measured_duration_s':q['first_episode_measured_duration_s'][eid]})
    seedrows.append({'seed':t['seed'],**r,'independently_recomputed_final_gate':g})
    group='paper_corresponding_4' if ci<4 else 'unseen_geometry_8' if ci<12 else 'long_12_step_2' if ci<14 else 'stretch_23cm_2'
    if spec['geometry']=='heading':group='standard_12'
    elif spec['geometry']=='boundary':group='height'+str(round(geom['step_height']*100))+'cm'
    elif spec['geometry']=='probe':group='paper_corresponding_2' if ci<2 else 'long_12_step_2' if ci<4 else 'stretch_23cm_2'
    CSV.append({'evaluation_id':spec['id'],'role':spec['role'],'scene':spec['scene'],'speed_m_s':spec['speed'],'construction_seed':spec['seed'],'domain_profile':spec['domain'],'heading_control':spec['heading'],'reset_seed':t['seed'],'case_index':ci,'case_name':source[ci].get('name',str(ci)),'case_group':group,'direction':geom['direction'],'step_height_m':geom['step_height'],'step_depth_m':geom['step_depth'],'nosing_m':geom['nosing'],'num_steps':geom['num_steps'],**{k:r[k] for k in COUNT_KEYS},'unique_noncompletions':32-r['completions'],'final_traversal_passed':g['traversal_passed'],'failed_gate_terms':';'.join(g['failed_gate_terms']),'maximum_pause_s':r['metrics']['longest_flight_pause_s'],**{k:r['metrics'].get(k) for k in METRICS}})
   c=counts(rows)
   cases.append({'case_index':ci,'case_name':source[ci].get('name',str(ci)),'geometry':geom,'counts':c,'completion_counts_by_seed':{str(t['seed']):r['completions'] for t,r in zip(ts,rows)},'minimum_seed_completion_fraction':min(r['completion_fraction'] for r in rows),'all_seed_final_traversal_passed':all(sr['independently_recomputed_final_gate']['traversal_passed'] for sr in seedrows),'full_traversal_without_failure_flags':c['unique_noncompletions']==0 and all(c[k]==0 for k in ['falls','stalls','lateral_escapes','base_contact_envs']),'maximum_pause_s':max(r['metrics']['longest_flight_pause_s'] for r in rows),'metrics_mean_of_seed_aggregates':means(rows),'mean_first_episode_measured_duration_s':avg(durations),'mean_successful_completion_time_s':avg(times),'contact_sample_counts_sum':{k:sum(r['contact_sample_counts'][k] for r in rows) for k in ['environment_samples','history_contact_foot_samples','current_contact_foot_samples']},'seed_rows':seedrows})
  groups={}
  for label,indices in groupdefs(spec,x['geometry']).items():
   rows=[t['cases'][ci] for t in ts for ci in indices]
   groups[label]={'case_indices':indices,'counts':counts(rows),'metrics_macro_mean':means(rows),'minimum_case_seed_completions':min(r['completions'] for r in rows),'minimum_case_seed_completion_fraction':min(r['completion_fraction'] for r in rows),'maximum_pause_s':max(r['metrics']['longest_flight_pause_s'] for r in rows),'all_case_seed_traversal_passed':all(gates[t['seed'],ci]['traversal_passed'] for t in ts for ci in indices),'case_seed_traversal_passes':sum(gates[t['seed'],ci]['traversal_passed'] for t in ts for ci in indices),'case_seed_count':len(rows)}
  assert a['traversal_passed']==groups['all']['all_case_seed_traversal_passed']
  main=read(directory/'primary-result.json') if spec['role']=='primary' and (directory/'result.json').is_file() and (directory/'primary-result.json').is_file() else None
  primary_final_equal=None if main is None else all(main[k]==x[k] for k in ['policy','geometry','final_acceptance','zero_action'])
  assert primary_final_equal is not False
  assert len(failed)==groups['all']['counts']['unique_noncompletions']
  e={'evaluation_id':spec['id'],'specification':spec,'status':'complete','result':relative(path),'result_sha256':sha(path),'checkpoint':expected_checkpoint,'checkpoint_identity_source':'result.json' if x.get('checkpoint') else 'construction config.json (primary-only scene)','checkpoint_sha256':plan['checkpoint_sha256' if spec['role']=='primary' else 'secondary_checkpoint_sha256'],'configuration_source_commit':cfg.get('source_commit'),'configuration_tracked_files_dirty':cfg.get('source_tracked_files_dirty'),'configuration_scope':'Construction config belongs to primary; secondary checkpoint identity is preserved in its own result.json and freeze hash, not inferred from construction config.','configuration_snapshot':cfg,'reported_original_passed':x['passed'],'final_traversal_passed':a['traversal_passed'],'motion_improvement_needed':a['motion_improvement_needed'],'smoothness_verified_by_source':a['smoothness_verified'],'primary_final_payload_equal':primary_final_equal,'groups':groups,'case_metrics':cases,'failure_endpoints':failed,'all_first_episode_anomaly_counts':anomalies,'zero_action_control':{'completion_counts_by_seed':{str(t['seed']):t['completions'] for t in x.get('zero_action',{}).get('trials',[])},'trial_count':len(x.get('zero_action',{}).get('trials',[]))},'policy_protocol_metadata':{k:v for k,v in p.items() if k not in ['trials','geometry']},'sampled_force_review':sampled_peaks(ts,p),'domain_readbacks':{when:read(directory/f'domain-parameters-{when}.json') for when in ['initial','final']},'physics_diagnostic':read(directory/'physics-diagnostic.json'),'physical_readback_audit':physical_audit(spec,directory)}
  EVAL.append(e);RAW[spec['id']]=x
 except (ValueError,KeyError,AssertionError,TypeError) as err:
  ERRORS.append({'evaluation_id':spec['id'],'result':relative(path),'error':repr(err)});raise

BYID={e['evaluation_id']:e for e in EVAL};PAIRS=[]
for label,left,right,perturb in [('nominal_speed0.3','nominal_primary_speed0.3','nominal_secondary_speed0.3','checkpoint'),('nominal_speed0.5','nominal_primary_speed0.5','nominal_secondary_speed0.5','checkpoint'),('foot_low','foot_nominal_primary_speed0.3','foot_low_primary_speed0.3','foot_friction'),('foot_high','foot_nominal_primary_speed0.3','foot_high_primary_speed0.3','foot_friction'),('heading_zero_yaw','standard_heading-control_primary_speed0.3','standard_zero-yaw_primary_speed0.3','heading_command')]:
 if left not in RAW or right not in RAW:continue
 a,b=RAW[left],RAW[right];at,bt=a['policy']['trials'],b['policy']['trials'];bts={t['seed']:t for t in bt}
 ea,eb=BYID[left],BYID[right]
 check={'pair':label,'left':left,'right':right,'deliberate_difference':perturb,'geometry_exact':a['geometry']==b['geometry'],'initial_root_xyz_exact':all(t['per_env']['initial_root_relative_xyz_m']==bts[t['seed']]['per_env']['initial_root_relative_xyz_m'] for t in at),'aggregate_initial_pose_distribution_exact':all(t['initial_reset_distribution']==bts[t['seed']]['initial_reset_distribution'] for t in at),'thresholds_exact':a['policy']['thresholds']==b['policy']['thresholds'] and a['final_acceptance']['thresholds']==b['final_acceptance']['thresholds'],'contact_sampling_exact':a['policy']['contact_sampling']==b['policy']['contact_sampling'],'heading_control_exact':a['policy']['heading_control']==b['policy']['heading_control'],'normalized_physical_readbacks_exact':normalized_summary(ea['domain_readbacks']['initial'])==normalized_summary(eb['domain_readbacks']['initial']),'non_foot_physical_readbacks_exact':normalized_summary({k:v for k,v in (ea['domain_readbacks']['initial'] or {}).items() if k!='foot_material'})==normalized_summary({k:v for k,v in (eb['domain_readbacks']['initial'] or {}).items() if k!='foot_material'}),'per_env_initial_quaternions_recorded':False,'case_comparisons':[]}
 for ca,cb in zip(ea['case_metrics'],eb['case_metrics']):
  check['case_comparisons'].append({'case_index':ca['case_index'],'both_all_seed_gates_passed':ca['all_seed_final_traversal_passed'] and cb['all_seed_final_traversal_passed'],'both_full_failure_free':ca['full_traversal_without_failure_flags'] and cb['full_traversal_without_failure_flags'],'completion_change_right_minus_left':cb['counts']['completions']-ca['counts']['completions'],'maximum_pause_change_right_minus_left_s':cb['maximum_pause_s']-ca['maximum_pause_s'],'metric_changes_right_minus_left':{k:cb['metrics_mean_of_seed_aggregates'][k]-ca['metrics_mean_of_seed_aggregates'][k] if ca['metrics_mean_of_seed_aggregates'][k] is not None and cb['metrics_mean_of_seed_aggregates'][k] is not None else None for k in METRICS}})
 full=[c for c in check['case_comparisons'] if c['both_full_failure_free']]
 check['full_failure_free_case_comparison']={'cases':len(full),'strict_numerical_lower_metric_counts_right_vs_left':{k:sum(c['metric_changes_right_minus_left'][k]<0 for c in full if c['metric_changes_right_minus_left'][k] is not None) for k in METRICS},'interpretation':'Descriptive lower-value counts within jointly competent whole cases; no significance or smoothness calibration, no candidate reselection.'}
 PAIRS.append(check)

INDEPENDENT_MOTION=[]
for tag,speed in [('03',.3),('05',.5)]:
 left=f'nominal_primary_speed{speed:g}';right=f'nominal_secondary_speed{speed:g}'
 if left not in BYID or right not in BYID:continue
 sources=[BYID[k]['result'] for k in [left,right]]
 # Existing CPU analyzer is run in a temporary output directory. No external
 # /tmp artifacts, simulator imports, Torch imports or GPU execution are needed.
 with tempfile.TemporaryDirectory(prefix='him-frozen-motion-') as tempdir:
  output=Path(tempdir)/('motion-speed'+tag)
  command=[sys.executable,'-B',str(ROOT/'reproduction/analyze-stair-motion.py'),*sources,'--acceptance',str(ROOT/plan['acceptance_file']),'--output',str(output)]
  result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,check=True)
  review=read(output.with_suffix('.json'))
 pairs=review['matched_comparisons']
 INDEPENDENT_MOTION.append({'speed_m_s':speed,'tool':'reproduction/analyze-stair-motion.py','source_paths':[r['path'] for r in review['sources']],'matched_case_seed_count':len(pairs),'eligible_from_saved_matching_and_original_case_gates':sum(r['controlled_motion_comparison_eligible_from_saved_evidence'] for r in pairs),'protocol_difference_count':sum(bool(r['protocol_difference_fields']) for r in pairs),'matched_comparisons':pairs,'scope':'Independent standard-library trace review; eligibility includes declared case gates, not a promise of full failure-free traversal or calibrated smoothness.'})

flatdirs=sorted(LOG.glob('*_frozen-stair-policy-flat-regression'));flatdir=flatdirs[-1] if flatdirs else None
flatpath=flatdir/'result.json' if flatdir else None;flat=read(flatpath)
flat_summary={'original_flat_gate_passed':flat.get('passed') if flat else None,'detailed_report':'reproduction/stair-policy-frozen-flat-regression.md' if (ROOT/'reproduction/stair-policy-frozen-flat-regression.md').is_file() else None,'status':'complete' if flat else 'pending','result':relative(flatpath) if flatpath else None,'scope':'Primary frozen stair checkpoint; six prescribed plane commands,64 envs,20s,reset warm start,0 gradient updates. Original flat criteria are separate from staircase completion gates.','payload':flat,'configuration_snapshot':read(flatdir/'config.json') if flatdir else None}
supplement_plan_path=ROOT/'reproduction/stair-material-speed05-supplement-plan.json'
supplement_report_path=ROOT/'reproduction/stair-frozen-material-speed05.json.gz'
supplement_plan=read(supplement_plan_path)
supplement_report=None
if supplement_report_path.is_file():
 with gzip.open(supplement_report_path,'rt') as stream:supplement_report=json.load(stream)
supplement={'scope':'Distinct 0.5m/s foot-only friction supplement; does not change original frozen protocol status or primary selection. No0.5m/s combined-dynamics result is implied.','protocol':relative(supplement_plan_path) if supplement_plan else None,'protocol_sha256':sha(supplement_plan_path) if supplement_plan else None,'status':supplement_report['status'] if supplement_report else 'pending' if supplement_plan else 'not_requested','report':'reproduction/stair-frozen-material-speed05.md' if supplement_report else None,'evaluations_summary':supplement_report.get('evaluations_summary') if supplement_report else None}
ready=len(EVAL)==len(SPECS) and flat is not None and not ERRORS and all(c['matches'] for c in HASHES) and all(e['physical_readback_audit'][when]['status']=='available_and_verified' for e in EVAL for when in ['initial','final'])
all_primary_stair_passed=all(e['final_traversal_passed'] for e in EVAL if e['specification']['role']=='primary') if ready else None
limits=['Frozen primary remains control660 irrespective of final outcomes; secondary slide680 is a nominal two-speed comparator only and is not tested across material, heading or dynamics scenes.',
 'The final control660 versus slide680 comparison is descriptive at checkpoint level: slide680 has feet_slide enabled and20more training updates from the common620 origin. It cannot isolate the effect of the slide reward; matched40-update tuning evidence is separate.',
 'Every final case keeps the original95% case/seed completion and <=5% each fall/stall/lateral-escape,zero history-base-contact gate. With32envs,31 passes completion and30 fails. Nonstretch/stretch labels only stratify results; any failed case fails the whole evaluated matrix.',
 'Paper-corresponding geometry is transferred to Go2/Isaac Lab; geometric success alone does not reproduce every paper claim or establish real-robot transfer.',
 'Reset seeds do not redraw startup material/mass/COM. Three dynamics construction seeds provide new startup draws; PD gains can be redrawn by resets/autoresets. Initial/final distribution summaries are not exact per-env first-episode gain snapshots.',
 'Material and combined dynamics are evaluated only at0.3m/s. Foot-only basic nominal/low/high isolate intended foot-friction changes; domainnone nominal changes material on all robot bodies and cannot serve as the only isolated-foot reference.',
 'Readbacks describe robot shape parameters and actual composed terrain USD authored attributes; they do not measure solver contact-pair coefficients or calibrated real named materials.',
 'Headingcontrol uses rootyawtarget0,gain1,clamp±.5rad/s,no lateral correction. Zero-yaw stress sets ordinary yaw-rate command tozero; policy retains IMU/joint feedback. It is not an open-loop robot test.',
 'Motion metrics are arithmetic means of seed-level case aggregates and then macro means over cases,not pooled trajectory RMS. First episodes are preserved before autoreset; motion excludes firstsecond. Nonexclusive failure flags and unique noncompletions are both retained.',
 'Lower action/contact/jerk on failed or shorter episodes does not prove smoother competent traversal. No pause flag and no single scalar certifies smoothness; complete continuous video review both directions remains separate.',
 'Current/history netnormalforce vector norms include riser normals and exclude tangential friction; current/history leg presence differs from body-count rewards. Slip is foot-link worldXYspeed proxy,not contact-point terrain-tangent slip.',
 'Physics5ms,policy20ms,retainedhistory3 with sample ages0/5/10ms;15ms-old initial substep impact may be lost. Sensor cadence is inferred from config/stepping; runtime timestamps were not measured.',
 'Sparse0.1s traces cover one representative env/case/seed and cannot bound whole-batch force peaks,substep impulse or duration. Full per-env initial orientation/state is not stored.']
primary_scene_gates=[e['final_traversal_passed'] for e in EVAL if e['specification']['role']=='primary']
original_scientific_passed=(all(primary_scene_gates) and flat['passed']) if ready else None
doc={'schema_version':1,'status':'complete' if ready else 'partial_waiting_for_frozen_scenes','generated_local':datetime.now().astimezone().isoformat(),'freeze':{'plan':relative(PLANFILE),'plan_sha256':sha(PLANFILE),'frozen_local':plan['frozen_local'],'execution_copy':str(FROZEN_COPY),'execution_copy_sha256':sha(FROZEN_COPY) if FROZEN_COPY.is_file() else None,'execution_copy_equal':frozen_copy==plan if frozen_copy else None,'primary_checkpoint':plan['checkpoint'],'primary_checkpoint_sha256':plan['checkpoint_sha256'],'secondary_checkpoint':plan['secondary_checkpoint'],'secondary_checkpoint_sha256':plan['secondary_checkpoint_sha256'],'no_retuning_from_final_matrix':True,'driver_changes_allowed':False,'hash_checks':HASHES},'scope':{'stair_scenes_expected':10,'flat_scenes_expected':1,'stair_evaluations_expected_including_secondary':12,'stair_evaluations_completed':len(EVAL),'final_geometry_cases':16,'heading_standard_cases':12,'envs_per_case_seed':32,'material_and_dynamics_speed_scope_m_s':[.3],'secondary_scope':'nominal two speeds only','case_grouping_preserves_all_original_gates':True,'source':plan},'supplementary_material_speed05':supplement,'original_acceptance':acceptance,'scientific_acceptance':'PASS' if original_scientific_passed else 'FAIL' if original_scientific_passed is False or any(not gate for gate in primary_scene_gates) or (flat and flat['passed'] is False) else 'pending','all_primary_stair_scenes_passed':all_primary_stair_passed,'original_suite_gate_failed_from_available_results':any(not e['final_traversal_passed'] for e in EVAL if e['specification']['role']=='primary'),'evaluations':EVAL,'pending':PENDING,'load_errors':ERRORS,'controlled_comparisons':PAIRS,'independent_cpu_motion_review':INDEPENDENT_MOTION,'flat_regression':flat_summary,'master_log':str(MASTER),'master_log_text':MASTER.read_text() if MASTER.is_file() else None,'limits':limits}

md=['# Frozen independent staircase validation','',f"Collection status: {'complete' if ready else 'partial; waiting for remaining frozen scenes'}. Scientific acceptance: {doc['scientific_acceptance']}. Primary control660 and nominal-only secondary slide680 were frozen at {plan['frozen_local']} before independent final outcomes. The selection stays fixed; these results trigger no retuning. Freeze checks: {sum(c['matches'] for c in HASHES)}/{len(HASHES)} verified; pending evaluations: {len(PENDING)}. GPU/driver operations are outside this CPU report.",'',
 'The whole16-case matrix retains the original gate: every case and reset seed must complete at least95%, with each fall/stall/escape fraction at most5% and zero history-base contact. At32envs,31/32 passes completion and30/32 fails. The4 paper-corresponding,8 unseen,2 long and2 stretch groups provide detail; a failing stretch still fails the entire matrix.','',
 '| Evaluation | Completed | Worst case/seed | Fall/stall/escape flags | Base history/current | Whole-matrix gate | Maxpause(s) |',
 '| --- | ---: | ---: | --- | --- | --- | ---: |']
for spec in SPECS:
 e=BYID.get(spec['id'])
 if e is None:md.append(f"| {spec['id']} | pending | — | — | — | pending | — |");continue
 g=e['groups']['all'];c=g['counts'];md.append(f"| {spec['id']} | {c['completions']}/{c['num_envs']} | {g['minimum_case_seed_completions']}/32 | {c['falls']}/{c['stalls']}/{c['lateral_escapes']} | {c['base_contact_envs']}/{c['current_sample_base_contact_envs']} | {'PASS' if e['final_traversal_passed'] else 'FAIL'} | {g['maximum_pause_s']:.2f} |")
if all(k in BYID for k in ['nominal_primary_speed0.3','nominal_primary_speed0.5','nominal_secondary_speed0.3','nominal_secondary_speed0.5']):
 md += ['', 'Primary control660 passes all paper-corresponding and unseen geometry case/seeds at both speeds. At 0.3 m/s it also passes both long cases; the stretch descent fails. At 0.5 m/s the long descent and one stretch-descent reset seed fail. Therefore its whole nominal matrix fails at both speeds. Secondary slide680 fails long descent at both speeds and stretch descent at 0.3 m/s; its reduced slip proxy does not preserve all traversal outcomes. The primary stays fixed.']
md+=['','Flags are nonexclusive; unique noncompletions equal total minus completed. JSON retains every failed endpoint, anomaly count, zero-action control and first-episode exposure; CSV contains one row per case/resetseed. Smoothness remains separate from traversal.','', '## Final geometry strata','', '| Evaluation | Group | Completed | Passed case/seeds | Gate |','| --- | --- | ---: | ---: | --- |']
for e in EVAL:
 if e['specification']['geometry']!='final':continue
 for label in ['paper_corresponding_4','unseen_geometry_8','long_12_step_2','stretch_23cm_2']:
  g=e['groups'][label];c=g['counts'];md.append(f"| {e['evaluation_id']} | {label} | {c['completions']}/{c['num_envs']} | {g['case_seed_traversal_passes']}/{g['case_seed_count']} | {'PASS' if g['all_case_seed_traversal_passed'] else 'FAIL'} |")
md+=['','## Failed case and resetseed gates','', '| Evaluation | Seed | Case | Completed | Fall/stall/escape | Base | Failed gate terms |','| --- | ---: | --- | ---: | --- | ---: | --- |']
for e in EVAL:
 for c in e['case_metrics']:
  for r in c['seed_rows']:
   g=r['independently_recomputed_final_gate']
   if g['traversal_passed']:continue
   md.append(f"| {e['evaluation_id']} | {r['seed']} | {c['case_name']} | {r['completions']}/32 | {r['falls']}/{r['stalls']}/{r['lateral_escapes']} | {r['base_contact_envs']} | {', '.join(g['failed_gate_terms'])} |")
md+=['','## Material, dynamics and heading scope','',
 'Foot-only nominal0.8/0.6,lower0.45/0.35,higher1.0/0.8 use the basic scene with identical prescribed geometry/speed/resetseeds. Terrain authored friction is1/1 with multiply combine mode; shape readbacks do not establish backend contact-pair coefficients. These material scenes test only0.3m/s. Combined dynamics uses three construction seeds71/73/79: startup mass/COM draws and reset PD gains at nominal footfriction,also only0.3m/s; it does not cover calibrated delay or motor strength.','',
 'The12-standard-case heading comparison uses resetseeds401/409/419 at0.3m/s. Normal external headingfeedback requests clamp(-yaw,±0.5)rad/s,with no lateral correction. The paired stress requests zero yawrate while the actor still receives feedback. Per-env initial rootpositions and aggregate pose distributions are compared in JSON; full initial state is not saved.','',
 '| Paired comparison | Geometry | Root positions | Pose distributions | Thresholds | Contact metadata | Heading identical |','| --- | --- | --- | --- | --- | --- | --- |']
for p in PAIRS:md.append(f"| {p['pair']} | {p['geometry_exact']} | {p['initial_root_xyz_exact']} | {p['aggregate_initial_pose_distribution_exact']} | {p['thresholds_exact']} | {p['contact_sampling_exact']} | {p['heading_control_exact']} |")
heading_pair=next((p for p in PAIRS if p['pair']=='heading_zero_yaw'),None)
if heading_pair:
 md += ['', '| Standard12 heading mode | Completed | Escape flags | XY tracking RMSE (m/s) | Yaw tracking MAE (rad/s) | Heading absolute error (rad) | Lateral absolute error (m) |',
  '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
 for id0 in ['standard_heading-control_primary_speed0.3','standard_zero-yaw_primary_speed0.3']:
  e=BYID[id0];g=e['groups']['all'];c=g['counts'];m=g['metrics_macro_mean']
  md.append(f"| {id0} | {c['completions']}/{c['num_envs']} | {c['lateral_escapes']} | {m['xy_tracking_rmse_m_s']:.5f} | {m['yaw_tracking_mae_rad_s']:.5f} | {m['heading_abs_error_rad']:.5f} | {m['lateral_abs_error_m']:.5f} |")
 md += ['', 'The yaw tracking target differs deliberately between modes; compare the outcome and heading/lateral drift alongside the target-relative yaw error, without interpreting lower yaw error as universally better heading.']
md += ['', '## Fixed nominal checkpoint motion comparison', '',
 'The table below keeps only cases with complete traversal and zero failure flags for both frozen checkpoints across all three reset seeds; failed cases remain in every gate/outcome table above. Values count strict numerical reductions for slide680 relative to control660, without significance or smoothness calibration. The checkpoints differ by reward and 20 training updates, so this is not an isolated reward-effect estimate.', '',
 '| Speed (m/s) | Jointly failure-free cases | Current leg contact lower | Action second difference lower | Root jerk lower | Current slip proxy lower | XY tracking error lower | Lateral error lower |',
 '| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
for pair in PAIRS:
 if not pair['pair'].startswith('nominal'):continue
 z=pair['full_failure_free_case_comparison'];v=z['strict_numerical_lower_metric_counts_right_vs_left'];n=z['cases']
 md.append(f"| {BYID[pair['left']]['specification']['speed']} | {n} | {v['current_sample_shank_contact_step_fraction']}/{n} | {v['action_second_delta_rms']}/{n} | {v['linear_jerk_rms_m_s3']}/{n} | {v['current_sample_foot_slip_fraction']}/{n} | {v['xy_tracking_rmse_m_s']}/{n} | {v['lateral_abs_error_m']}/{n} |")
md += ['', '## Actual physical parameter readbacks', '',
 '| Evaluation | Foot static/dynamic | Initial base mass range (kg) | Initial Kp range | Initial Kd range | Initial/final readbacks verified |',
 '| --- | --- | --- | --- | --- | --- |']
for e in EVAL:
 if e['specification']['domain']=='none':continue
 a=e['physical_readback_audit']['initial'];f=e['physical_readback_audit']['final'];z=a['physical_summary']
 span=lambda field:f"{z[field]['min']:.4f}–{z[field]['max']:.4f}"
 md.append(f"| {e['evaluation_id']} | {a['foot_static_dynamic_pair'][0]}/{a['foot_static_dynamic_pair'][1]} | {span('base_mass_kg')} | {span('pd_stiffness')} | {span('pd_damping')} | {a['status']}/{f['status']} |")
md += ['', 'COM offsets, inertia, PD scale ratios and final summaries remain in JSON. Initial/final summaries can reflect gains after automatic resets and cannot be assigned exactly to each recorded first episode. All verified terrain bindings retain authored 1/1 friction and multiply combine mode.']
if supplement_plan:
 md += ['', '## Separate0.5m/s foot-material supplement', '',
  f"Status: {supplement['status']}. The separately recorded protocol adds foot-only nominal/lower/higher friction at0.5m/s, with the same frozen primary, final geometries and original gates. It pairs lower/higher with the0.5m/s basic nominal reference. These additional scenes do not change the original frozen protocol status and do not test0.5m/s combined dynamics. Report: `{supplement['report'] or 'pending'}`."]
 if supplement['evaluations_summary']:
  md += ['', '| Supplement material | Completed | Whole16-case gate |', '| --- | ---: | --- |']
  for e in supplement['evaluations_summary']:
   md.append(f"| {e['material']} | {e['completions']}/{e['num_envs']} | {'PASS' if e['final_traversal_passed'] else 'FAIL'} |")
md+=['','## Flat regression','',f"Status: {flat_summary['status']}. The frozen stairpolicy is tested from reset on six prescribed20s plane commands with64envs and zero gradientupdates. Its original survival/tracking criteria are distinct from staircase completion. Source: `{flat_summary['result'] or 'pending'}`. Original flatgate: {'PASS' if flat and flat['passed'] else 'FAIL' if flat else 'pending'}. Detailed report: `reproduction/stair-policy-frozen-flat-regression.md`."]
if flat:
 md += ['', '| Flat command [vx,vy,yaw] | Survived | First falls | XY MAE (m/s) | Yaw MAE (rad/s) | Upright fraction | Original gate |',
  '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
 for case in flat['cases']:
  command=case['command_m_s_m_s_rad_s'];survivors=round(case['first_episode_survival_fraction']*case['num_envs'])
  md.append(f"| {command} | {survivors}/{case['num_envs']} | {case['first_episode_falls']} | {case['xy_mae_m_s']:.6f} | {case['yaw_mae_rad_s']:.6f} | {case['upright_fraction']:.6f} | {'PASS' if case['passed'] else 'FAIL'} |")
 md += ['', 'The frozen stairpolicy passes3/6 commands: two forwards and positive yaw. Backward and negative yaw commands barely move; lateralcommand has0/64 full-duration survival. Positive yaw passes95% survival with2first-episode falls,so it is not failure-free. Per-axis roll RMS/peak were not recorded. The earlier dedicated flat checkpoint result does not replace this stair-policy regression.']
md += ['', '## Measurement and interpretation limits', '']
md += [f'- {v}' for v in limits]
md += ['','Sources: frozen plan/acceptance/geometry files, raw result/config/physics-diagnostic/domain-parameter files linked in compressedJSON. Raw trajectories remain local in ignored IsaacLab logs; JSONgzip compression is lossless.','']
serialized=json.dumps(doc,indent=2,allow_nan=False).encode();buffer=io.BytesIO()
with gzip.GzipFile(fileobj=buffer,mode='wb',mtime=0) as stream:stream.write(serialized)
assert gzip.decompress(buffer.getvalue())==serialized
atomic(OUT.with_suffix('.json.gz'),buffer.getvalue(),True);atomic(OUT.with_suffix('.md'),format_markdown('\n'.join(md)))
csvbuf=io.StringIO();writer=csv.DictWriter(csvbuf,fieldnames=CSV_FIELDS,lineterminator='\n');writer.writeheader();writer.writerows(CSV);atomic(OUT.with_suffix('.csv'),csvbuf.getvalue())
# Keep heading dependence directly reviewable outside the larger final report.
if heading_pair:
 heading_ids=['standard_heading-control_primary_speed0.3','standard_zero-yaw_primary_speed0.3']
 heading_evaluations=[BYID[k] for k in heading_ids]
 heading_rows=[r for r in CSV if r['evaluation_id'] in heading_ids]
 heading_doc={'schema_version':1,'status':'complete','scope':'Frozen primary control660,12 standard cases,.3m/s,32envs percase/resetseed,seeds401/409/419; ordinary external headingfeedback versus zero yawrate command. No training or candidate reselection.','primary_checkpoint':plan['checkpoint'],'primary_checkpoint_sha256':plan['checkpoint_sha256'],'original_acceptance':acceptance,'evaluations':heading_evaluations,'controlled_comparison':heading_pair,'interpretation':'The primary passes the prescribed heading-feedback standard scene and fails the zero-yaw-rate stress scene. This establishes dependence on the external heading command under these tested conditions. The actor still receives IMU/joint feedback in both modes; neither result establishes open-loop-robot or real-robot readiness.','limits':limits}
 heading_md=['# Frozen policy dependence on external heading commands','',
  'On the12standard cases at0.3m/s, the frozen primary completes1152/1152 with external headingfeedback but1050/1152 with zero yawrate commands. The latter has95 lateral escapes,7 fall flags and2 history-base-contact environments. The normal mode passes every original case/resetseed gate; the zero-yaw stress fails. This is a measured dependency under the tested conditions.','',
  'Normal headingfeedback requests yawrate=clamp(-yaw,−0.5,+0.5)rad/s toward yaw0,with gain1 and no lateral-position correction. The stress requests zero yawrate through the same ordinary command channel. The actor continues to receive proprioceptive feedback in both modes. Full per-env initial orientation/state is not saved; saved initial rootpositions and aggregate pose distributions match exactly.','',
  '| Mode | Completed | Fall/stall/escape | Historybase | Heading absolute error (rad) | Lateral absolute error (m) | XY tracking RMSE (m/s) | Gate |',
  '| --- | ---: | --- | ---: | ---: | ---: | ---: | --- |']
 for e in heading_evaluations:
  g=e['groups']['all'];c=g['counts'];m=g['metrics_macro_mean'];heading_md.append(f"| {e['evaluation_id']} | {c['completions']}/{c['num_envs']} | {c['falls']}/{c['stalls']}/{c['lateral_escapes']} | {c['base_contact_envs']} | {m['heading_abs_error_rad']:.6f} | {m['lateral_abs_error_m']:.6f} | {m['xy_tracking_rmse_m_s']:.6f} | {'PASS' if e['final_traversal_passed'] else 'FAIL'} |")
 heading_md += ['', 'Means average seed-level case aggregates equally; they are not pooled RMS statistics. Flags are nonexclusive; unique noncompletions are preserved separately. Lower force/action values on failed shorter trajectories do not show better competent motion.', '',
  '| Standard case | Normal completed by seed401/409/419 | Zero-yaw completed by seed401/409/419 | Normal all-seed gate | Zero-yaw all-seed gate |',
  '| --- | --- | --- | --- | --- |']
 left,right=heading_evaluations
 for ca,cb in zip(left['case_metrics'],right['case_metrics']):
  show=lambda c:'/'.join(str(c['completion_counts_by_seed'][str(seed)]) for seed in [401,409,419])
  heading_md.append(f"| {ca['case_name']} | {show(ca)} | {show(cb)} | {ca['all_seed_final_traversal_passed']} | {cb['all_seed_final_traversal_passed']} |")
 heading_md += ['', 'The zero-yaw result limits any claim that the actor alone maintains the requested global stairheading. It does not invalidate the explicitly configured heading-feedback result; it documents the condition under which that result was achieved. No thresholds, primary checkpoint or training settings change after these observations.','',
  'Source paths,original gates,physical readbacks,case/resetseed metrics,failed endpoints and deliberate protocol difference are preserved in lossless JSONgzip. CSV uses the same columns as the main frozen report. Sparse traces and numeric pause flags do not certify continuous smoothness.','']
 heading_out=ROOT/'reproduction/stair-frozen-heading-dependence'
 payload=json.dumps(heading_doc,indent=2,allow_nan=False).encode();buf=io.BytesIO()
 with gzip.GzipFile(fileobj=buf,mode='wb',mtime=0) as stream:stream.write(payload)
 atomic(heading_out.with_suffix('.json.gz'),buf.getvalue(),True);atomic(heading_out.with_suffix('.md'),format_markdown('\n'.join(heading_md)))
 cb=io.StringIO();writer=csv.DictWriter(cb,fieldnames=CSV_FIELDS,lineterminator='\n');writer.writeheader();writer.writerows(heading_rows);atomic(heading_out.with_suffix('.csv'),cb.getvalue())
print(json.dumps({'status':doc['status'],'stair_evaluations':len(EVAL),'pending':len(PENDING),'csv_seed_rows':len(CSV),'case_rows':sum(len(e['case_metrics']) for e in EVAL),'hash_checks':len(HASHES),'paired_comparisons':len(PAIRS),'compressed_json_bytes':len(buffer.getvalue()),'flat':flat_summary['status'],'scientific_acceptance':'PASS' if original_scientific_passed else 'FAIL' if original_scientific_passed is False or any(not gate for gate in primary_scene_gates) or (flat and flat['passed'] is False) else 'pending','all_primary_stair_scenes_passed':all_primary_stair_passed,'original_suite_gate_failed_from_available_results':any(not e['final_traversal_passed'] for e in EVAL if e['specification']['role']=='primary')}))
