#!/usr/bin/env python3
"""Reproduce the fixed frozen stretch-descent association report on CPU.

Run from any working directory with Python, NumPy and Matplotlib installed.
Input runs are explicitly named in SPECS; original result/config/material files
must exist under the repository isaaclab/logs directory. Reads primary policy
case15 only, including all96episode outcomes and only active representative
traces. Writes stair-stretch-association-review data, figures and report.
Never launches Isaac Lab, changes runtime source, or performs Git operations.
"""
from pathlib import Path
import json, csv, hashlib, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
REPO = Path(__file__).resolve().parents[1]
OUT = REPO / 'reproduction'
PREFIX = 'stair-stretch-association-review'
SPECS = [('none_nominal_speed03', 'none nominal 0.3', '2026-10-11_05-48-09_frozen-final-speed03', '#4169a1'), ('none_nominal_speed05', 'none nominal 0.5', '2026-10-11_05-52-29_frozen-final-speed05', '#d58128'), ('basic_nominal_speed03', 'basic nominal 0.3', '2026-10-11_05-56-41_frozen-foot-nominal-speed03', '#4a9864'), ('basic_low_speed03', 'basic low 0.3', '2026-10-11_05-58-39_frozen-foot-low-speed03', '#a95391')]
METRICS = ['current_sample_contact_foot_horizontal_speed_m_s', 'current_sample_foot_slip_fraction', 'current_sample_shank_contact_step_fraction', 'pitch_rms_rad', 'peak_contact_force_n', 'longest_flight_pause_s']
LEGS = ['FL_thigh', 'FR_thigh', 'RL_thigh', 'RR_thigh', 'FL_calf', 'FR_calf', 'RL_calf', 'RR_calf']

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda : f.read(1024 * 1024), b''):
            h.update(c)
    return h.hexdigest()

def stat(a):
    a = np.array(a, dtype=float)
    return {'n': int(a.size), 'min': float(a.min()) if a.size else None, 'median': float(np.median(a)) if a.size else None, 'max': float(a.max()) if a.size else None}

def savefig(fig, suffix=''):
    replacements = {'stretch23cm/20cm': '23 cm / 20 cm', '96episodes': '96 episodes', 'Case15': 'Case 15', 'all96env': 'all 96 environments', '>0.10m/s': '> 0.10 m/s', 'after1s': 'after 1 s', 'env480': 'env 480', 'seed307': 'seed 307', 'seed101': 'seed 101', 'active100ms': 'active 100 ms', 'nearrootx1.19m': 'near root x 1.19 m', 'plateau11.62': 'plateau 11.62', '11.62–13.92s': '11.62–13.92 s', 'rootx≈1.843m': 'root x ≈ 1.843 m', 'pitch≈.602rad': 'pitch ≈ 0.602 rad', 'FRcalf≈69N': 'FR calf ≈ 69 N', 'FRfoot gatefalse': 'FR foot gate false', 'completed11.64s': 'completed 11.64 s', 'FRcalf': 'FR calf', 'FRfoot': 'FR foot'}
    for label in fig.findobj(matplotlib.text.Text):
        txt = label.get_text()
        for (old, new) in replacements.items():
            txt = txt.replace(old, new)
        label.set_text(txt)
    for extension in ['png', 'pdf']:
        fig.savefig(OUT / (PREFIX + suffix + '.' + extension), dpi=170, bbox_inches='tight')
    plt.close(fig)
groups = []
configs = []
params = []
raws = []
csvrows = []
for (key, label, dirname, color) in SPECS:
    run = REPO / 'isaaclab/logs' / dirname
    c = json.loads((run / 'config.json').read_text())
    r = json.loads((run / 'result.json').read_text())
    d = json.loads((run / 'domain-parameters-initial.json').read_text())
    configs.append(c)
    raws.append(r)
    params.append(d)
    assert c['evaluation_trace_stride_policy_steps'] == 5 and (not c['evaluation_dynamics_randomized'])
    episodes = []
    trials = []
    reps = []
    for t in r['policy']['trials']:
        case = t['cases'][15]
        assert case['num_envs'] == 32
        g = case['geometry']
        assert g['direction'] == 'desc' and g['step_height'] == 0.23 and (g['step_depth'] == 0.2) and (g['num_steps'] == 6)
        ids = [e for (e, caseid) in zip(t['trace'][0]['env_ids'], t['trace'][0]['case_ids']) if caseid == 15]
        assert ids == [480]
        for e in range(480, 512):
            pe = t['per_env']
            outcome = 'completed' if pe['completed'][e] else 'fall' if pe['fall'][e] else 'stall' if pe['stall'][e] else 'escape' if pe['lateral_escape'][e] else 'other'
            episode = {'group': key, 'seed': t['seed'], 'environment_id': e, 'outcome': outcome, 'initial_root_xyz_m': pe['initial_root_relative_xyz_m'][e], 'last_measured_root_xyz_m': pe['last_measured_root_relative_xyz_m'][e], 'last_measured_feet_xyz_m': pe['last_measured_feet_relative_xyz_m'][e], 'duration_s': pe['first_episode_measured_duration_s'][e], 'longest_flight_pause_s': pe['longest_flight_pause_s'][e], 'maximum_root_x_m': pe['maximum_root_relative_x_m'][e], 'max_progress_m': pe['max_progress_m'][e]}
            episodes.append(episode)
            csvrows.append({'group': key, 'seed': t['seed'], 'environment_id': e, 'outcome': outcome, 'initial_root_x_m': episode['initial_root_xyz_m'][0], 'initial_root_y_m': episode['initial_root_xyz_m'][1], 'terminal_root_x_m': episode['last_measured_root_xyz_m'][0], 'terminal_root_y_m': episode['last_measured_root_xyz_m'][1], 'terminal_root_z_m': episode['last_measured_root_xyz_m'][2], 'duration_s': episode['duration_s'], 'longest_flight_pause_s': episode['longest_flight_pause_s'], 'maximum_root_x_m': episode['maximum_root_x_m']})
        trials.append({'seed': t['seed'], 'num_envs': case['num_envs'], 'completions': case['completions'], 'falls': case['falls'], 'stalls': case['stalls'], 'lateral_escapes': case['lateral_escapes'], 'metrics': {k: case['metrics'][k] for k in METRICS}, 'contact_sample_counts': case['contact_sample_counts']})
        rep = []
        fields = ['root_relative_xyz', 'root_linear_velocity_w', 'yaw_roll_pitch', 'feet_relative_xyz', 'foot_horizontal_speed_m_s', 'contacts', 'current_sample_contacts', 'action_delta_rms', 'action_second_delta_rms', 'flight_paused', 'base_force_n', 'shank_force_n', 'current_sample_base_force_n', 'current_sample_shank_force_n', 'leg_current_normal_force_norm_n', 'leg_history_peak_normal_force_norm_n', 'leg_current_normal_force_w_n', 'command_vx_vy_yaw']
        for z in t['trace']:
            k = z['env_ids'].index(480)
            if z['active'][k]:
                rep.append({'time_s': z['time_s'], **{name: z[name][k] for name in fields}})
        ep = next((x for x in episodes if x['seed'] == t['seed'] and x['environment_id'] == 480))
        assert all((rep[j]['time_s'] < rep[j + 1]['time_s'] for j in range(len(rep) - 1)))
        assert rep[-1]['time_s'] <= ep['duration_s'] + 1e-05
        reps.append({'seed': t['seed'], 'environment_id': 480, 'outcome': ep['outcome'], 'duration_s': ep['duration_s'], 'terminal_root_xyz_m': ep['last_measured_root_xyz_m'], 'active_trace_sample_count': len(rep), 'last_trace_time_s': rep[-1]['time_s'], 'terminal_trace_gap_s': ep['duration_s'] - rep[-1]['time_s'], 'samples': rep})
    counts = {name: sum((x['outcome'] == name for x in episodes)) for name in ['completed', 'fall', 'stall', 'escape', 'other']}
    assert counts['completed'] == sum((t['completions'] for t in trials))
    failedstats = {}
    for outcome in ['fall', 'stall']:
        eps = [x for x in episodes if x['outcome'] == outcome]
        xx = np.array([x['last_measured_root_xyz_m'][0] for x in eps])
        failedstats[outcome] = {'terminal_root_x_m': stat(xx), 'first_tread_root_interval_1p0_to_1p2_count': int(((xx >= 1) & (xx < 1.2)).sum()), 'first_tread_edge_neighborhood_1p15_to_1p25_count': int(((xx >= 1.15) & (xx <= 1.25)).sum()), 'longest_flight_pause_s': stat([x['longest_flight_pause_s'] for x in eps])}
    groups.append({'key': key, 'label': label, 'color': color, 'run': str(run), 'hashes': {name: sha(run / name) for name in ['config.json', 'result.json', 'domain-parameters-initial.json']}, 'checkpoint': c['checkpoint'], 'source_commit': c['source_commit'], 'source_tracked_files_dirty': c['source_tracked_files_dirty'], 'domain_profile': None if c['domain_randomization'] is None else c['domain_randomization']['profile'], 'evaluation_dynamics_randomized': c['evaluation_dynamics_randomized'], 'speed_m_s': r['policy']['command_forward_speed_m_s'], 'friction_override': c['friction_override'], 'readback_static_friction': d['foot_material']['static_friction'], 'readback_dynamic_friction': d['foot_material']['dynamic_friction'], 'geometry': g, 'counts': counts, 'per_seed': trials, 'seed_mean_metrics': {k: float(np.mean([x['metrics'][k] for x in trials])) for k in METRICS}, 'failed_endpoint_statistics': failedstats, 'episodes': episodes, 'representative_env480': reps})
pairs = []
for (a, b) in [(0, 1), (2, 3), (0, 2)]:
    (ga, gb) = (groups[a], groups[b])
    (pa, pb) = (params[a], params[b])
    ea = {(x['seed'], x['environment_id']): x for x in ga['episodes']}
    eb = {(x['seed'], x['environment_id']): x for x in gb['episodes']}
    assert ea.keys() == eb.keys()
    transitions = {}
    for (k, x) in ea.items():
        y = eb[k]
        term = x['outcome'] + ' -> ' + y['outcome']
        transitions[term] = transitions.get(term, 0) + 1
    pairs.append({'groups': [ga['key'], gb['key']], 'all96_initial_root_xyz_equal': all((ea[k]['initial_root_xyz_m'] == eb[k]['initial_root_xyz_m'] for k in ea)), 'readback_structure_exact_equal': {field: pa[field] == pb[field] for field in ['base_mass_kg', 'base_inertia_kg_m2', 'base_com', 'actuator_pd', 'terrain_material']}, 'terrain_readback_equal_excluding_anonymous_stage_identifier': {k: v for (k, v) in pa['terrain_material'].items() if k != 'stage_root_layer_identifier'} == {k: v for (k, v) in pb['terrain_material'].items() if k != 'stage_root_layer_identifier'}, 'foot_static_readback_exact_equal': pa['foot_material']['static_friction'] == pb['foot_material']['static_friction'], 'foot_dynamic_readback_exact_equal': pa['foot_material']['dynamic_friction'] == pb['foot_material']['dynamic_friction'], 'paired_outcome_transitions': transitions})
stallrep = groups[2]['representative_env480'][0]
ss = [x for x in stallrep['samples'] if x['time_s'] >= 11.62]
last = ss[-1]
stall_evidence = {'group': groups[2]['key'], 'seed': 101, 'environment_id': 480, 'outcome': 'stall', 'episode_duration_s': stallrep['duration_s'], 'recorded_plateau_interval_s': [ss[0]['time_s'], ss[-1]['time_s']], 'plateau_sample_count': len(ss), 'plateau_root_x_m': stat([x['root_relative_xyz'][0] for x in ss]), 'plateau_abs_vx_max_m_s': max((abs(x['root_linear_velocity_w'][0]) for x in ss)), 'plateau_pitch_rad': stat([x['yaw_roll_pitch'][2] for x in ss]), 'plateau_FR_calf_current_force_norm_n': stat([x['leg_current_normal_force_norm_n'][5] for x in ss]), 'plateau_FR_foot_current_contact_count': sum((x['current_sample_contacts'][1] for x in ss)), 'plateau_FL_RL_RR_current_contact_all_count': sum((all((x['current_sample_contacts'][k] for k in [0, 2, 3])) for x in ss)), 'plateau_base_current_force_max_n': max((x['current_sample_base_force_n'] for x in ss)), 'last_sample': last, 'interpretation': 'Low forward progress coincides with persistent FR-calf load, absent FR-foot current contact, three other current foot contacts and very small action changes. This is consistent with a stable supported configuration and does not identify the measured contact location or the cause of the stall.'}
manifest = {'schema_version': 1, 'scope': 'Read-only CPU association analysis of existing frozen primary-control660 first episodes; only primary policy phases, case15 six-step23cm/20cm descent, seeds101/211/307,32env each. No simulator runs or additional parameter selection.', 'primary_checkpoint_sha256': sha(REPO / 'artifacts/go2-stairs-control660/model_660.pt'), 'groups': groups, 'paired_checks': pairs, 'stall_association': stall_evidence, 'measurement_limits': ['Full 96-environment outcome/terminal-root/terminal-feet records per condition; detailed trace only env480 for each seed, sampled every5policy steps (~100ms). Active first-episode rows only; inactive post-completion/reset samples excluded.', 'Terminal root x localizes the robot, not the limb/collider contact point. Root may straddle multiple treads. Stored current/history normal-force vectors do not identify exact collision location or geometry; no stretch-condition video was recorded.', 'Recorded contact-gated world-XY foot link speed and >0.10m/s fraction are slip proxies. History includes retained sensor samples; stride5 misses transients.', 'Per-case metrics are pooled over eligible active first-episode samples after1s; different success/failure durations affect their denominators. Table and marker means are arithmetic across three seed reports, not newly pooled statistics.', 'The conditions share saved initial XYZ and matching reported non-friction readbacks, but these are not all simulator state variables. none and basic nominal produce different outcomes despite those equal readbacks. Do not attribute differences to randomized mass/COM: eval dynamics randomized was false.', 'Associations between commanded speed, material settings, contact support and completion do not establish a general causal mechanism, an optimum speed/friction, reduced scraping or smoothness. Effective solver contact-pair friction coefficients were not read back.']}
jsonpath = OUT / (PREFIX + '.json')
jsonpath.write_text(json.dumps(manifest, indent=2) + '\n')
csvpath = OUT / (PREFIX + '.csv')
with csvpath.open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(csvrows[0]), lineterminator='\n')
    w.writeheader()
    w.writerows(csvrows)
(fig, axs) = plt.subplots(2, 2, figsize=(15, 10))
labels = [g['label'] for g in groups]
xx = np.arange(4)
bottom = np.zeros(4)
for (outcome, color) in [('completed', '#5a9e6f'), ('fall', '#bb5555'), ('stall', '#d1a751')]:
    vals = np.array([g['counts'][outcome] for g in groups])
    axs[0, 0].bar(xx, vals, bottom=bottom, color=color, label=outcome)
    for (x, v, b) in zip(xx, vals, bottom):
        if v:
            axs[0, 0].text(x, b + v / 2, str(v), ha='center', va='center', fontsize=9)
    bottom += vals
axs[0, 0].set_xticks(xx)
axs[0, 0].set_xticklabels(labels, rotation=18, ha='right')
axs[0, 0].set_ylabel('Episodes /96')
axs[0, 0].set_ylim(0, 104)
axs[0, 0].legend(ncol=3, fontsize=8)
axs[0, 0].set_title('Case15 first-episode outcomes')
ax = axs[0, 1]
for (k, g) in enumerate(groups):
    for (outcome, marker, clr) in [('fall', 'x', '#b44f4f'), ('stall', 's', '#bd9330')]:
        eps = [e for e in g['episodes'] if e['outcome'] == outcome]
        for (seedidx, seed) in enumerate([101, 211, 307]):
            es = [e for e in eps if e['seed'] == seed]
            jitter = np.linspace(-0.035, 0.035, len(es)) if es else []
            ax.scatter([e['last_measured_root_xyz_m'][0] for e in es], k + (seedidx - 1) * 0.14 + np.asarray(jitter), marker=marker, s=24, color=clr, alpha=0.8, label=outcome if k == 0 and seedidx == 0 else None)
for boundary in np.arange(1, 2.201, 0.2):
    ax.axvline(boundary, color='.55', lw=0.7, alpha=0.4)
ax.set_yticks(xx)
ax.set_yticklabels(labels)
ax.set_xlim(0.95, 2.42)
ax.set_xlabel('Last measured root x (m); verticals are stair boundaries')
ax.set_title('Failure positions, all96env per condition')
ax.legend(fontsize=8)
ax = axs[1, 0]
for g in groups:
    for p in g['per_seed']:
        ax.scatter(p['metrics']['current_sample_foot_slip_fraction'], p['completions'] / 32, color=g['color'], s=45, alpha=0.8)
    ax.scatter(g['seed_mean_metrics']['current_sample_foot_slip_fraction'], g['counts']['completed'] / 96, color=g['color'], marker='D', s=85, label=g['label'], edgecolor='black', lw=0.4)
ax.set_xlabel('Current contact-gated foot XY speed >0.10m/s fraction')
ax.set_ylabel('Completion fraction')
ax.set_title('More completions coexist with higher slip proxy')
ax.legend(fontsize=8)
ax.grid(alpha=0.2)
ax = axs[1, 1]
for g in groups:
    for p in g['per_seed']:
        ax.scatter(p['metrics']['pitch_rms_rad'], p['completions'] / 32, color=g['color'], s=45, alpha=0.8)
    ax.scatter(g['seed_mean_metrics']['pitch_rms_rad'], g['counts']['completed'] / 96, color=g['color'], marker='D', s=85, label=g['label'], edgecolor='black', lw=0.4)
ax.set_xlabel('Whole-first-episode body pitch RMS (rad, after1s)')
ax.set_ylabel('Completion fraction')
ax.set_title('Completion gain is not a smaller pitch claim')
ax.grid(alpha=0.2)
fig.suptitle('Frozen control660: stretch23cm/20cm descent associations\n96episodes per condition; dots=seed reports, diamonds=three-seed mean; recorded proxies are not causality', fontsize=13)
fig.tight_layout(rect=(0, 0, 1, 0.94))
savefig(fig)
(fig, axs) = plt.subplots(2, 2, figsize=(15, 10))
for g in groups:
    rep = next((x for x in g['representative_env480'] if x['seed'] == 307))
    z = rep['samples']
    x = np.array([s['root_relative_xyz'][0] for s in z])
    t = np.array([s['time_s'] for s in z])
    pitch = np.array([s['yaw_roll_pitch'][2] for s in z])
    vx = np.array([s['root_linear_velocity_w'][0] for s in z])
    f = np.array([max(s['leg_current_normal_force_norm_n']) for s in z])
    base = np.array([s['current_sample_base_force_n'] for s in z])
    footmean = np.array([np.mean(np.array(s['foot_horizontal_speed_m_s'])[np.array(s['current_sample_contacts'], dtype=bool)]) if any(s['current_sample_contacts']) else np.nan for s in z])
    label = g['label'] + '; ' + rep['outcome']
    color = g['color']
    axs[0, 0].plot(t, x, label=label, color=color)
    axs[0, 0].plot(t[-1], x[-1], 'o', color=color, ms=4)
    axs[0, 1].plot(x, pitch, label=label, color=color)
    axs[1, 0].plot(x, vx, color=color, label=label)
    axs[1, 1].plot(x, f, color=color, label=g['label'] + ' calf/thigh max')
    axs[1, 1].scatter(x[base > 1], base[base > 1], color=color, marker='x', s=40, label=g['label'] + ' base >1N' if any(base > 1) else None)
for ax in [axs[0, 1], axs[1, 0], axs[1, 1]]:
    ax.set_xlim(0.8, 2.4)
    for b in np.arange(1, 2.201, 0.2):
        ax.axvline(b, color='.6', lw=0.7, alpha=0.3)
    ax.set_xlabel('Recorded root x (m), not contact-point location')
    ax.grid(alpha=0.15)
axs[0, 0].set_xlabel('Simulation time (s)')
axs[0, 0].set_ylabel('Root x (m)')
axs[0, 0].legend(fontsize=8)
axs[0, 0].grid(alpha=0.2)
axs[0, 1].set_ylabel('Pitch (rad)')
axs[1, 0].set_ylabel('Root world vx (m/s)')
axs[1, 1].set_ylabel('Current normal force norm (N)')
axs[1, 1].legend(fontsize=7, ncol=2)
fig.suptitle('Representative env480, reset seed307: first-drop failure versus continued descent\nOnly active100ms samples; .3 nominal episodes end nearrootx1.19m; successful conditions pass that position with calf contacts', fontsize=13)
fig.tight_layout(rect=(0, 0, 1, 0.94))
savefig(fig, '-representative-traces')
(fig, axs) = plt.subplots(3, 2, figsize=(15, 11), sharex=True)
for g in [groups[2], groups[3]]:
    rep = next((x for x in g['representative_env480'] if x['seed'] == 101))
    z = rep['samples']
    t = np.array([s['time_s'] for s in z])
    c = g['color']
    label = g['label'] + '; ' + rep['outcome']
    axs[0, 0].plot(t, [s['root_relative_xyz'][0] for s in z], color=c, label=label)
    axs[0, 1].plot(t, [s['root_linear_velocity_w'][0] for s in z], color=c, label=label)
    axs[1, 0].plot(t, [s['yaw_roll_pitch'][2] for s in z], color=c, label=label)
    axs[1, 1].plot(t, [s['leg_current_normal_force_norm_n'][5] for s in z], color=c, label=g['label'] + ' FRcalf current')
    axs[1, 1].plot(t, [s['leg_history_peak_normal_force_norm_n'][5] for s in z], color=c, linestyle=':', lw=0.8, alpha=0.7, label=g['label'] + ' FRcalf history')
    axs[2, 0].step(t, [sum(s['current_sample_contacts']) for s in z], where='mid', color=c, label=g['label'] + ' current count')
    axs[2, 0].step(t, [int(s['current_sample_contacts'][1]) for s in z], where='mid', color=c, linestyle='--', alpha=0.7, label=g['label'] + ' FRfoot current')
    axs[2, 1].plot(t, [s['action_delta_rms'] for s in z], color=c, label=label)
for ax in axs.flat:
    ax.axvspan(11.62, 13.92, color=groups[2]['color'], alpha=0.07)
    ax.set_xlim(7, 14.05)
    ax.grid(alpha=0.2)
    ax.legend(fontsize=7)
    ax.set_xlabel('Simulation time (s)')
for (ax, label) in zip(axs.flat, ['Root x (m)', 'Root world vx (m/s)', 'Pitch (rad)', 'FR calf normal-force norm (N)', 'Current foot contact count / FR contact bool', 'Action delta RMS']):
    ax.set_ylabel(label)
axs[0, 0].axhline(1.843, color='.4', ls=':', lw=0.8)
axs[0, 1].axhline(0.05, color='.4', ls=':', lw=0.8)
fig.suptitle('Representative env480, seed101: nominal material stall support association\nNominal recorded plateau11.62–13.92s: rootx≈1.843m, pitch≈.602rad, FRcalf≈69N, FRfoot gatefalse; low material episode completed11.64s', fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.94))
savefig(fig, '-stall')
lines = ['# Stretch descent association review', '', 'Saved first episodes show higher completion at **0.5m/s** for nominal materials and at **lower foot-material coefficients** for the0.3m/s material probe. The same data show persistent calf contacts, higher contact-gated foot speeds in the higher-completion conditions, and failures concentrated near the first23cm drop. These are condition-specific associations, not evidence for an optimum speed/friction or smoother motion.', '', '| Condition | Completed /96 | Falls | Stalls | Current foot XYspeed (m/s) | Current slip proxyfraction | Pitch RMS (rad) |', '|---|---:|---:|---:|---:|---:|---:|']
for g in groups:
    m = g['seed_mean_metrics']
    co = g['counts']
    lines.append(f"| {g['label']} | {co['completed']} | {co['fall']} | {co['stall']} | {m['current_sample_contact_foot_horizontal_speed_m_s']:.3f} | {m['current_sample_foot_slip_fraction']:.3f} | {m['pitch_rms_rad']:.3f} |")
lines += ['', 'Counts sum three reset seeds101/211/307 ×32environments, case15 only. Numeric proxy columns are arithmetic means of the three per-seed case reports; they are not a newly pooled estimate. They use valid active first-episode samples after1s, and episode duration differs between successful and failed runs. “Slip proxy” means current normal-force-gated foot world-XY link speed>0.10m/s, not measured contact-point tangential slip.', '', 'For nominal0.3m/s with the `none` configuration,33/34falls end with rootx in[1.0,1.2)m; the six-step geometry begins atx1.0 and its first tread ends atx1.2. All8stalls end atrootx1.424–2.128m. For basic nominal0.3m/s,25/31falls lie in that first-tread interval and7stalls end at1.238–2.083m. The two remaining nominal0.5m/s falls lie atrootx≈1.2001m. Low material0.3m/s has4falls and0stalls. Root endpoints localize the robot, not a measured limb/collider contact point.', '', 'Representative env480, seed307, falls at0.3m/s with nominal materials in both configurations: `none` ends att4.42s/rootx1.1904m; `basic` ends att4.44s/rootx1.1895m. Their recorded pitch near the end is about+0.42rad. At the last `none` sample the base current-force norm is12.3N; fall classification includes a>1N base-force gate, so a large pitch angle is not required for a fall label. The basic trace ends20ms before its terminal result and cannot identify the exact terminal trigger. In this same seed/env, nominal0.5m/s and basic low0.3m/s complete, despite continuing calf contacts and sometimes larger pitch angles through the flight.', '', f"Representative basic nominal0.3m/s, seed101/env480, stalls at{stallrep['duration_s']:.2f}s. Its recorded plateau from11.62–13.92s holds rootx≈1.843m, |vx|≤{stall_evidence['plateau_abs_vx_max_m_s']:.4f}m/s and pitch≈0.602rad. FRcalf current-force norm remains{stall_evidence['plateau_FR_calf_current_force_norm_n']['min']:.1f}–{stall_evidence['plateau_FR_calf_current_force_norm_n']['max']:.1f}N; FRfoot current-contact isfalse in all{len(ss)}plateau samples while FL/RL/RR gates aretrue. At13.92s the FRcalf force vector is[4.33,0.0044,69.32]N, base currentforce iszero and action-delta RMS is8.8e−5. Low material in that seed/env completes11.64s. This supports a persistent calf-supported low-progress configuration as an observed stall mode; it does not locate the contact or prove that friction causes the support state.", '', 'The reported base mass/inertia, COM and actuator PD readback objects match exactly across all four conditions, as do all96stored initial root XYZ positions for each paired comparison. Evaluated dynamics randomization wasfalse even for the `basic`-profile launches. `none` nominal and `basic` nominal both read back foot coefficients0.8static/0.6dynamic; low reads back0.45/0.35. The profile label must not be described as a tested mass/COM randomization in this comparison. Initial XYZ and readback agreement do not include every simulator state variable: `none` and `basic` nominal still differ54vs58completions. Solver contact-pair effective friction was unavailable.', '', 'Higher completion does not coincide with lower slip proxy: nominal speed0.5 averages0.281vs0.234 at0.3; low material0.3 averages0.330vs0.232 forbasic nominal. Pitch RMS isalso higher fornominal0.5. Contact timing, support and progression may be involved, but the saved data cannot isolate a causal mechanism or demonstrate less scraping.', '', 'Detailed traces cover only env480 in each seed, with100ms sample spacing; all96per-condition first-episode endpoints and outcomes are used in the population plots. Inactive post-episode/reset rows were excluded. No stretch-condition video or exact collision-point measurement is available. The successful16cm/long12videos are different geometries and do not visually certify these stretch failures.', '', 'Only existing primary-policy phases were read; secondary candidates and zero-action phases were excluded. Frozen primary checkpoint SHA256 is`' + manifest['primary_checkpoint_sha256'] + '`. Source provenance remains as recorded in the linked configs, including dirty state. No GPU launch, runtime/protocol change, or Git operation was performed.', '', 'Artifacts: [all-condition associations](stair-stretch-association-review.png), [seed307representative traces](stair-stretch-association-review-representative-traces.png), [seed101stall support](stair-stretch-association-review-stall.png), [machine-readable evidence](stair-stretch-association-review.json), [384first-episode endpoints](stair-stretch-association-review.csv). Eachfigure also has a PDF. Rawrun directories and SHA256config/result/material hashes are retained in the JSON.', '']
import re
text = '\n'.join(lines)
text = re.sub('(?<=[a-zA-Z])(?=\\d)', ' ', text)
text = re.sub('(?<=\\d)(?=[a-zA-Z])', ' ', text)
for filename in [PREFIX + '.png', PREFIX + '-representative-traces.png', PREFIX + '-stall.png', PREFIX + '.json', PREFIX + '.csv']:
    text = text.replace(filename.replace('307', ' 307 ').replace('101', ' 101 '), filename)
readable = {'XYspeed': 'XY speed', 'proxyfraction': 'proxy fraction', '×32': '× 32', ',33/34': ', 33/34', ',25/31': ', 25/31', 'rootx': 'root x', 'in[1.0,1.2)m': 'in [1.0, 1.2) m', 'atx': 'at x', 'atroot': 'at root', 'att ': 'at t ', 'about+': 'about +', 'a>1': 'a > 1', 'speed>': 'speed > ', 'FRcalf': 'FR calf', 'FRfoot': 'FR foot', 'isfalse': 'is false', 'aretrue': 'are true', 'is[4.33,0.0044,69.32]N': 'is [4.33, 0.0044, 69.32] N', 'currentforce': 'current force', 'iszero': 'is zero', '8.8 e−5': '8.8e−5', 'wasfalse': 'was false', 'forbasic': 'for basic', 'isalso': 'is also', 'fornominal': 'for nominal', 'Eachfigure': 'Each figure', 'Rawrun': 'Raw run', '16 cm/long 12': '16 cm / long 12'}
for (old, new) in readable.items():
    text = text.replace(old, new)
text = text.replace('SHA 256', 'SHA256')
text = text.replace(manifest['primary_checkpoint_sha256'].replace('', ''), manifest['primary_checkpoint_sha256']) if False else text
start = text.index('Frozen primary checkpoint SHA256 is`')
end = text.index('`.', start)
text = text[:start] + 'Frozen primary checkpoint SHA256 is `' + manifest['primary_checkpoint_sha256'] + text[end:]
text = text.replace('Solver contact-pair effective friction was unavailable.', 'Terrain material readbacks also match after excluding the anonymous USD stage identifier, the only differing terrain-readback field. Solver contact-pair effective friction was unavailable.')
text = text.replace('Higher completion does not coincide with lower slip proxy:', 'Matched episode labels also show reversals: nominal 0.3→0.5 has 42 failed episodes become successful and two previously successful episodes fall; basic nominal→low has 36 failed episodes become successful and two previously successful episodes fall. Even with matching stored initial positions, these observations do not establish universal improvement.\n\nHigher completion does not coincide with lower slip proxy:')
(OUT / (PREFIX + '.md')).write_text(text)
print(json.dumps({'json': str(jsonpath), 'report': str(OUT / (PREFIX + '.md')), 'csv': str(csvpath), 'population_episodes': len(csvrows), 'representative_trajectories': sum((len(g['representative_env480']) for g in groups)), 'paired': pairs, 'stall_plateau': {k: v for (k, v) in stall_evidence.items() if k != 'last_sample'}}, indent=2))
