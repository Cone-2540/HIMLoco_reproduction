#!/usr/bin/env python3
"""Summarize frozen stair-policy plane regression without simulator/GPU imports.

Defaults to this script’s repository from any working directory. Missing ignored
flat logs print pending; recorded results preserve original CSV fields and gates.
No gradient updates, retuning or driver changes are performed.
"""
import argparse,csv,gzip,hashlib,io,json,math,os,re
from datetime import datetime
from pathlib import Path
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

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1])
args=parser.parse_args()
R=args.repo_root.expanduser().resolve();O=R/'reproduction/stair-policy-frozen-flat-regression'
plan=json.loads((R/'reproduction/stair-final-evaluation-plan.json').read_text());dirs=sorted((R/'isaaclab/logs').glob('*_frozen-stair-policy-flat-regression'))
if not dirs or not (dirs[-1]/'result.json').is_file():print('{"status":"pending_flat_result"}');raise SystemExit(0)
d=dirs[-1];p=d/'result.json';x=json.loads(p.read_text());cfg=json.loads((d/'config.json').read_text())
assert cfg['mode']=='evaluate' and cfg['terrain']=='flat' and cfg['num_envs']==64
assert cfg['checkpoint'].removeprefix('/workspace/himloco/')==plan['checkpoint']
assert hashlib.sha256((R/plan['checkpoint']).read_bytes()).hexdigest()==plan['checkpoint_sha256']
assert cfg['evaluation_seconds']==20 and cfg['evaluation_include_zero_action'] in (None,True)
# Flat config leaves the optional stair-oriented zero-action flag unset; the
# actual six zero_action_cases below provide the evidence that controls ran.
assert cfg['requested_additional_training_updates'] is None and cfg['physics_dt']==.005 and cfg['policy_decimation']==4
assert x['thresholds']=={'xy_mae_m_s':.2,'yaw_mae_rad_s':.3,'first_episode_survival_fraction':.95,'minimum_duration_s':20.,'minimum_num_envs':64}
commands=plan['flat_regression']['commands'];assert len(x['cases'])==6 and len(x['zero_action_cases'])==6
assert [r['command_m_s_m_s_rad_s'] for r in x['cases']]==commands
assert [r['command_m_s_m_s_rad_s'] for r in x['zero_action_cases']]==commands
rows=[];audits=[]
for role,key in [('policy','cases'),('zero_action','zero_action_cases')]:
 for case in x[key]:
  t=x['thresholds'];sample=case['num_envs']>=t['minimum_num_envs'] and case['requested_duration_s']+1e-6>=t['minimum_duration_s'] and case['executed_steps']==1000
  assert case['sample_eligible']==sample and case['warmup_steps']==100
  terms=[]
  if not sample:terms.append('sample_eligibility')
  if case['failure_reasons']:terms.append('failure_reasons')
  if case['xy_mae_m_s'] is None or case['xy_mae_m_s']>=t['xy_mae_m_s']:terms.append('XY_MAE')
  if case['yaw_mae_rad_s'] is None or case['yaw_mae_rad_s']>=t['yaw_mae_rad_s']:terms.append('yaw_MAE')
  if case['first_episode_survival_fraction']<t['first_episode_survival_fraction']:terms.append('first_episode_survival')
  assert case['passed']==(not terms)
  survivors=round(case['first_episode_survival_fraction']*case['num_envs']);assert abs(survivors/case['num_envs']-case['first_episode_survival_fraction'])<1e-7
  audits.append({'role':role,'command':case['command_m_s_m_s_rad_s'],'survivors_full_requested_duration':survivors,'independent_gate_passed':not terms,'failed_gate_terms':terms})
  vx,vy,yaw=case['command_m_s_m_s_rad_s'];mv=case['mean_measured_vx_vy_yaw'] or [None]*3
  rows.append({'controller':role,'command_vx_m_s':vx,'command_vy_m_s':vy,'command_yaw_rad_s':yaw,'num_envs':case['num_envs'],'requested_duration_s':case['requested_duration_s'],'survived':survivors,'first_episode_survival_fraction':case['first_episode_survival_fraction'],'first_episode_falls':case['first_episode_falls'],'first_episode_timeouts':case['first_episode_timeouts'],'passed':case['passed'],'failed_gate_terms':';'.join(terms),'xy_mae_m_s':case['xy_mae_m_s'],'xy_rmse_m_s':case['xy_rmse_m_s'],'yaw_mae_rad_s':case['yaw_mae_rad_s'],'yaw_rmse_rad_s':case['yaw_rmse_rad_s'],'mean_measured_vx_m_s':mv[0],'mean_measured_vy_m_s':mv[1],'mean_measured_yaw_rad_s':mv[2],'mean_root_height_m':case['mean_root_height_m'],'upright_fraction':case['upright_fraction'],'nominal_height_fraction':case['nominal_height_fraction'],'roll_rms_rad':None,'roll_peak_rad':None,'tracking_samples':case['tracking_samples'],'height_tracking_samples':case['height_tracking_samples'],'mean_first_episode_duration_s':case['mean_first_episode_duration_s'],'finite_physics':case['finite_physics'],'all_episode_falls':case['all_episode_falls'],'all_episode_timeouts':case['all_episode_timeouts']})
assert x['passed']==all(r['passed'] for r in x['cases']) and x['moving_command_tested'] is True
for compare,a,b in zip(x['baseline_comparison'],x['cases'],x['zero_action_cases']):
 for metric,key in [('xy_mae_m_s','xy_mae_improvement_m_s'),('yaw_mae_rad_s','yaw_mae_improvement_rad_s')]:
  delta=b[metric]-a[metric] if a[metric] is not None and b[metric] is not None else None;assert compare[key]==delta
limits=['This is the unchanged frozen stair checkpoint evaluated on a plane, with zero gradient updates. It is separate from the earlier dedicated flat checkpoint selection and does not replace that historical result.',
 'One nominal reset seed and six command cases are used, not a material/dynamics or randomized-reset flat robustness test.',
 'Tracking excludes the first 2s warmup; survival includes startup and the terminal step. Only each environment’s first episode contributes, and pre-reset terminal velocities remain included.',
 'XY MAE is mean Euclidean XY velocity error; XY RMSE is sqrt(mean squared XY-vector error). Flat tracking uses the ordinary body-frame velocity commands, unlike external stair heading feedback.',
 'Upright fraction tests projected gravity_z<-0.8, combining roll and pitch. The flat evaluator does not save roll RMS/peak or a posture trace; this report cannot infer per-axis roll from the upright fraction.',
 'Height statistics omit done rows because post-step root state has already reset; terminal upright observations remain included. Minimum/maximum height diagnostic uses post-step states across the loop, including later reset episodes.',
 'Requested-timeout terminations are expected at 20s and can coexist with full survival; a fall on a timeout step still counts as a fall. All-episode counters are preserved separately and do not inflate first-episode survival.',
 'Source flat criteria remain strict XY MAE<0.2m/s,yaw MAE<0.3rad/s,survival>=95%,>=64envs,>=20s,no source failure reason. Height/upright are descriptive and introduce no new acceptance gate.',
 'These nominal simulation tests do not establish real-robot readiness.']
doc={'schema_version':1,'status':'passed' if x['passed'] else 'failed','generated_local':datetime.now().astimezone().isoformat(),'result':str(p.relative_to(R)),'result_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'checkpoint':plan['checkpoint'],'checkpoint_sha256':plan['checkpoint_sha256'],'freeze_time':plan['frozen_local'],'no_retuning':True,'gradient_updates':0,'warm_start':'reset','scope':plan['flat_regression'],'configuration_snapshot':cfg,'source_report':x,'independent_gate_audits':audits,'roll_specific_metrics':{'status':'not_recorded_by_flat_evaluator','roll_rms_rad':None,'roll_peak_rad':None,'available_posture_metric':'upright_fraction (projected gravity_z<-0.8; combined roll/pitch tilt)'},'limits':limits}
md=['# Frozen stair-policy flat regression','',f"The frozen control660 stair checkpoint {'passes' if x['passed'] else 'fails'} the original six-command nominal plane regression. It receives zero gradient updates and starts from reset. This preserves the stair selection and remains separate from the earlier dedicated flat-policy evaluation.",'',
 'Each command uses 64 environments for 20s, with tracking after 2s warmup and survival measured from startup through the terminal step. The unchanged gate requires XY MAE <0.2m/s, yaw MAE <0.3rad/s, survival >=95%, and eligible finite source data. Upright/height diagnostics add no gate.','',
 '| Command [vx,vy,yaw] | Survival | First falls | XY MAE / RMSE (m/s) | Yaw MAE / RMSE (rad/s) | Mean observed [vx,vy,yaw] | Upright fraction | Gate |',
 '| --- | ---: | ---: | --- | --- | --- | ---: | --- |']
for r in rows[:6]:
 f=lambda v:f'{v:.5f}' if v is not None else 'unavailable'
 md.append(f"| [{r['command_vx_m_s']},{r['command_vy_m_s']},{r['command_yaw_rad_s']}] | {r['survived']}/64 | {r['first_episode_falls']} | {f(r['xy_mae_m_s'])}/{f(r['xy_rmse_m_s'])} | {f(r['yaw_mae_rad_s'])}/{f(r['yaw_rmse_rad_s'])} | [{f(r['mean_measured_vx_m_s'])},{f(r['mean_measured_vy_m_s'])},{f(r['mean_measured_yaw_rad_s'])}] | {f(r['upright_fraction'])} | {'PASS' if r['passed'] else 'FAIL: '+r['failed_gate_terms']} |")
md+=['','The source records no roll RMS/peak or flat posture trace. Upright fraction uses combined roll/pitch tilt and cannot identify roll specifically. Height and full-duration exposure are retained below.','',
 '| Command | Mean height (m) | Nominal-height fraction | Mean first-episode duration (s) | First requested timeouts | Tracking / height samples | Finite physics |','| --- | ---: | ---: | ---: | ---: | --- | --- |']
for r in rows[:6]:md.append(f"| [{r['command_vx_m_s']},{r['command_vy_m_s']},{r['command_yaw_rad_s']}] | {r['mean_root_height_m']:.5f} | {r['nominal_height_fraction']:.5f} | {r['mean_first_episode_duration_s']:.2f} | {r['first_episode_timeouts']} | {r['tracking_samples']}/{r['height_tracking_samples']} | {r['finite_physics']} |")
md+=['','## Matching zero-action controls','', '| Command | Survival | XY MAE (m/s) | Yaw MAE (rad/s) | Gate |','| --- | ---: | ---: | ---: | --- |']
for r in rows[6:]:md.append(f"| [{r['command_vx_m_s']},{r['command_vy_m_s']},{r['command_yaw_rad_s']}] | {r['survived']}/64 | {r['xy_mae_m_s']:.5f} | {r['yaw_mae_rad_s']:.5f} | {'PASS' if r['passed'] else 'FAIL: '+r['failed_gate_terms']} |")
md+=['','## Limits','']+[f'- {s}' for s in limits]+['',f"Raw source: `{str(p.relative_to(R))}`; checkpoint SHA-256 `{plan['checkpoint_sha256']}`. Lossless compressedJSON preserves the complete original report, configuration and independently recomputed gates; CSV contains policy and zero-action rows.",'']
serialized=json.dumps(doc,indent=2,allow_nan=False).encode();buf=io.BytesIO()
with gzip.GzipFile(fileobj=buf,mode='wb',mtime=0) as stream:stream.write(serialized)
assert gzip.decompress(buf.getvalue())==serialized
for suffix,content in [('.json.gz',buf.getvalue()),('.md',format_markdown('\n'.join(md))),('.csv',None)]:
 if suffix=='.csv':
  cs=io.StringIO();writer=csv.DictWriter(cs,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows);content=cs.getvalue()
 dest=O.with_suffix(suffix);tmp=Path(str(dest)+'.tmp');tmp.write_bytes(content) if isinstance(content,bytes) else tmp.write_text(content);os.replace(tmp,dest)
print(json.dumps({'status':doc['status'],'policy_commands':6,'zero_action_commands':6,'policy_passed_commands':sum(r['passed'] for r in x['cases']),'flat_posture_roll_available':False,'output':str(O)}))
for r in rows[:6]:print(json.dumps(r))
