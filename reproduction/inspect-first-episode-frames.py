#!/usr/bin/env python3
"""Reproduce complete first-episode sheets and paired recorded telemetry on CPU.

From the repository root:
  python3 -B reproduction/inspect-first-episode-frames.py --verify-only
  python3 -B reproduction/inspect-first-episode-frames.py --overwrite
  python3 -B reproduction/inspect-first-episode-frames.py clip-first-episode.mp4

With no clip arguments, use the four frozen control660 clips beside this file.
Clips and adjacent provenance JSON are produced by clip-first-episode-video.py.
Saved run config.json/result.json must remain available at the provenance path.
Requires existing OpenCV, Pillow, NumPy and Matplotlib. Never starts a simulator.
Generation creates every chronological frame sheet, CSV, summary JSON and plot;
verification decodes every clip and checks existing sheet coverage/hashes and
all CSV values against the saved selected-environment first-episode trace.

Full sheets use a fixed crop for readability. Frame PTS plus one policy dt is
only the nominal simulation timing convention. This tool does not watch real
continuous playback or certify smoothness, slip or absence of limb scraping.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
LEGS = ['FL_thigh', 'FR_thigh', 'RL_thigh', 'RR_thigh', 'FL_calf', 'FR_calf', 'RL_calf', 'RR_calf']
FEET = ['FL', 'FR', 'RL', 'RR']
CROP = (360, 300, 1000, 660)
DEFAULT_PREFIXES = ['frozen-control660-16cm-asc', 'frozen-control660-16cm-desc', 'frozen-control660-long12-asc', 'frozen-control660-long12-desc']

def require(condition, message):
    if not condition:
        raise ValueError(message)

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda : f.read(1024 * 1024), b''):
            h.update(c)
    return h.hexdigest()

def stats(a):
    a = np.asarray(a, dtype=float)
    if not a.size:
        return {'sample_count': 0}
    return {'sample_count': int(a.size), 'mean': float(a.mean()), 'median': float(np.median(a)), 'p95': float(np.percentile(a, 95)), 'max': float(a.max()), 'min': float(a.min())}

def paired_rows(trial, env, N, dt, fps, config):
    """Pair each frame with exactly one active dense trace and flatten all values."""
    selected = []
    for r in trial['trace']:
        if env not in r['env_ids']:
            continue
        k = r['env_ids'].index(env)
        if r['time_s'] <= N * dt + dt / 100:
            selected.append({key: value if key == 'time_s' else value[k] for (key, value) in r.items()})
    require(len(selected) == N, (len(selected), N))
    for (i, r) in enumerate(selected):
        require(r['active'], i)
        require(math.isclose(r['time_s'], (i + 1) * dt, rel_tol=0, abs_tol=1e-06), (i, r['time_s']))
    rows = []
    for (i, r) in enumerate(selected):
        require(len(r['actions']) == len(config['joint_names']) == 12, f'Unexpected action count at frame {i}')
        for field in ['root_relative_xyz', 'root_linear_velocity_w', 'yaw_roll_pitch', 'command_vx_vy_yaw']:
            require(len(r[field]) == 3, f'Unexpected {field} shape at frame {i}')
        for field in ['feet_relative_xyz', 'foot_horizontal_speed_m_s', 'contacts', 'current_sample_contacts']:
            require(len(r[field]) == 4, f'Unexpected {field} foot count at frame {i}')
        require(all(len(v) == 3 for v in r['feet_relative_xyz']), f'Unexpected foot position shape at frame {i}')
        for field in ['leg_current_normal_force_norm_n', 'leg_history_peak_normal_force_norm_n', 'leg_current_normal_force_w_n', 'leg_link_pos_w_m', 'leg_link_quat_w_xyzw']:
            require(len(r[field]) == 8, f'Unexpected {field} body count at frame {i}')
        for field, size in [('leg_current_normal_force_w_n', 3), ('leg_link_pos_w_m', 3), ('leg_link_quat_w_xyzw', 4)]:
            require(all(len(v) == size for v in r[field]), f'Unexpected {field} shape at frame {i}')
        d = {'frame_index': i, 'encoded_pts_s': i / fps, 'nominal_simulation_time_s': (i + 1) * dt, 'trace_time_s': r['time_s'], 'environment_id': env, 'case_id': r['case_ids'], 'active': int(r['active'])}
        for (key, suffixes) in [('root_relative_xyz', ['x_m', 'y_m', 'z_m']), ('root_linear_velocity_w', ['x_m_s', 'y_m_s', 'z_m_s']), ('yaw_roll_pitch', ['yaw_rad', 'roll_rad', 'pitch_rad']), ('command_vx_vy_yaw', ['vx_m_s', 'vy_m_s', 'yaw_rate_rad_s'])]:
            for (suffix, val) in zip(suffixes, r[key]):
                d[key + '_' + suffix] = val
        for (k, foot) in enumerate(FEET):
            for (axis, val) in zip('xyz', r['feet_relative_xyz'][k]):
                d[foot + '_foot_relative_' + axis + '_m'] = val
            d[foot + '_foot_horizontal_speed_m_s'] = r['foot_horizontal_speed_m_s'][k]
            d[foot + '_foot_history_contact'] = int(r['contacts'][k])
            d[foot + '_foot_current_contact'] = int(r['current_sample_contacts'][k])
        for (j, (name, val)) in enumerate(zip(config['joint_names'], r['actions'])):
            d['action_' + str(j) + '_' + name] = val
        for key in ['action_delta_rms', 'action_second_delta_rms', 'base_force_n', 'shank_force_n', 'current_sample_base_force_n', 'current_sample_shank_force_n']:
            d[key] = r[key]
        d['flight_paused'] = int(r['flight_paused'])
        for (k, leg) in enumerate(LEGS):
            for (key, label) in [('leg_current_normal_force_norm_n', 'current_normal_force_norm_n'), ('leg_history_peak_normal_force_norm_n', 'history_peak_normal_force_norm_n')]:
                d[leg + '_' + label] = r[key][k]
            for (key, label, axes) in [('leg_current_normal_force_w_n', 'current_normal_force_w', 'xyz'), ('leg_link_pos_w_m', 'link_position_w', 'xyz'), ('leg_link_quat_w_xyzw', 'link_quaternion_w', 'xyzw')]:
                for (axis, val) in zip(axes, r[key][k]):
                    d[leg + '_' + label + '_' + axis + ('_n' if 'force' in label else '_m' if 'position' in label else '')] = val
        require(all((math.isfinite(v) for v in d.values())), i)
        rows.append(d)
    return (selected, rows)

def write_sheets(clip, meta, font_path):
    """Decode every frame once into labeled chronological 60-frame pages."""
    stem = clip.stem.replace('-first-episode', '')
    dest = clip.parent / (stem + '-all-frames')
    dest.mkdir(exist_ok=True)
    font = ImageFont.truetype(str(font_path), 14)
    headerfont = ImageFont.truetype(str(font_path), 18)
    crop = CROP
    cols = 6
    rows = 10
    perpage = cols * rows
    tw = 320
    th = 180
    label = 18
    head = 32
    cap = cv2.VideoCapture(str(clip))
    n = meta['retained_frame_count']
    fps = meta['output_video_info']['fps']
    dt = meta['policy_dt_s']
    pages = []
    decoded = 0
    for start in range(0, n, perpage):
        end = min(n, start + perpage)
        page = Image.new('RGB', (cols * tw, head + rows * (th + label)), (22, 22, 22))
        d = ImageDraw.Draw(page)
        d.text((10, 6), f'{stem} | frames {start:04d}-{end - 1:04d} | sim {(start + 1) * dt:.2f}-{end * dt:.2f}s | crop {crop}', font=headerfont, fill='white')
        for i in range(start, end):
            (ok, frame) = cap.read()
            require(ok, (i, n))
            decoded += 1
            im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).crop(crop).resize((tw, th), Image.LANCZOS)
            x = (i - start) % cols * tw
            y = head + (i - start) // cols * (th + label)
            page.paste(im, (x, y))
            d.text((x + 4, y + th + 1), f'f{i:04d}  PTS {i / fps:6.2f}s  sim {(i + 1) * dt:6.2f}s', font=font, fill='white')
        out = dest / f'page-{len(pages) + 1:02d}.png'
        page.save(out)
        pages.append({'page': len(pages) + 1, 'path': str(out), 'frame_indices_inclusive': [start, end - 1], 'frame_count': end - start, 'encoded_pts_s_inclusive': [start / fps, (end - 1) / fps], 'nominal_simulation_time_s_inclusive': [(start + 1) * dt, end * dt], 'sha256': digest(out)})
        print(json.dumps(pages[-1]), flush=True)
    require(not cap.read()[0], 'Material verification invariant failed')
    cap.release()
    require(decoded == n, 'Material verification invariant failed')
    index = {'clip': str(clip), 'clip_sha256': digest(clip), 'provenance': str(clip.with_suffix('.json')), 'run': meta['run'], 'environment_id': meta['environment_id'], 'frame_count': n, 'fully_cpu_decoded': True, 'coverage': 'Every retained frame exactly once, chronological row-major; no sampling.', 'crop_original_pixels_xyxy_exclusive': list(crop), 'original_dimensions': [meta['output_video_info']['width'], meta['output_video_info']['height']], 'thumbnail_dimensions': [tw, th], 'page_dimensions': [cols * tw, head + rows * (th + label)], 'grid_columns': cols, 'grid_rows': rows, 'frames_per_full_page': perpage, 'timing_note': meta['synchronization_limit'], 'continuous_video_reviewed': False, 'pages': pages}
    indexpath = clip.parent / (stem + '-all-frames.json')
    indexpath.write_text(json.dumps(index, indent=2) + '\n')
    print('INDEX ' + str(indexpath), flush=True)

def write_telemetry(clip, m):
    """Write dense selected-episode CSV, descriptive summary and full-episode plot."""
    run = Path(m['run'])
    config = json.loads((run / 'config.json').read_text())
    result = json.loads((run / 'result.json').read_text())
    trial = result['policy']['trials'][0]
    env = m['environment_id']
    N = m['retained_frame_count']
    dt = m['policy_dt_s']
    fps = m['output_video_info']['fps']
    stem = clip.stem.replace('-first-episode', '')
    (selected, rows) = paired_rows(trial, env, N, dt, fps, config)
    csvpath = clip.parent / (stem + '-frame-telemetry.csv')
    with csvpath.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    t = np.array([r['time_s'] for r in selected])
    pos = np.array([r['root_relative_xyz'] for r in selected])
    vel = np.array([r['root_linear_velocity_w'] for r in selected])
    angles = np.array([r['yaw_roll_pitch'] for r in selected])
    feet = np.array([r['feet_relative_xyz'] for r in selected])
    speed = np.array([r['foot_horizontal_speed_m_s'] for r in selected])
    cur = np.array([r['current_sample_contacts'] for r in selected], dtype=bool)
    hist = np.array([r['contacts'] for r in selected], dtype=bool)
    legcur = np.array([r['leg_current_normal_force_norm_n'] for r in selected])
    leghist = np.array([r['leg_history_peak_normal_force_norm_n'] for r in selected])
    delta = np.array([r['action_delta_rms'] for r in selected])
    second = np.array([r['action_second_delta_rms'] for r in selected])
    base = np.array([r['current_sample_base_force_n'] for r in selected])
    shank = np.array([r['current_sample_shank_force_n'] for r in selected])
    paused = np.array([r['flight_paused'] for r in selected], dtype=bool)
    maxima = []
    for (k, name) in enumerate(LEGS):
        j = int(legcur[:, k].argmax())
        maxima.append({'body': name, 'current_peak_force_n': float(legcur[j, k]), 'frame_index': j, 'trace_time_s': float(t[j]), 'encoded_pts_s': j / fps, 'force_w_xyz_n': selected[j]['leg_current_normal_force_w_n'][k], 'history_peak_force_n_over_episode': float(leghist[:, k].max())})
    footstats = {name: {'all_horizontal_speed_m_s': stats(speed[:, k]), 'current_contact_horizontal_speed_m_s': stats(speed[cur[:, k], k]), 'history_contact_horizontal_speed_m_s': stats(speed[hist[:, k], k]), 'current_contact_frame_count': int(cur[:, k].sum()), 'history_contact_frame_count': int(hist[:, k].sum())} for (k, name) in enumerate(FEET)}
    summary = {'run': str(run), 'clip': str(clip), 'environment_id': env, 'case_id': selected[0]['case_ids'], 'reset_seed': trial['seed'], 'completed': bool(trial['per_env']['completed'][env]), 'fall': bool(trial['per_env']['fall'][env]), 'stall': bool(trial['per_env']['stall'][env]), 'lateral_escape': bool(trial['per_env']['lateral_escape'][env]), 'frame_count': N, 'csv_rows': len(rows), 'csv_columns': len(rows[0]), 'csv': str(csvpath), 'csv_sha256': digest(csvpath), 'trace_complete_for_retained_frames': True, 'trace_all_active': True, 'trace_step_s': dt, 'trace_times_inclusive_s': [float(t[0]), float(t[-1])], 'encoded_pts_inclusive_s': [0, (N - 1) / fps], 'source_commit': config['source_commit'], 'source_tracked_files_dirty': config['source_tracked_files_dirty'], 'root_start_after_first_step_xyz_m': pos[0].tolist(), 'root_end_xyz_m': pos[-1].tolist(), 'root_velocity_w_m_s': {axis: stats(vel[:, k]) for (k, axis) in enumerate('xyz')}, 'body_angle_rad': {axis: stats(angles[:, k]) for (k, axis) in enumerate(['yaw', 'roll', 'pitch'])}, 'action_delta_rms': stats(delta), 'action_second_delta_rms': stats(second), 'current_base_force_n': stats(base), 'current_shank_force_n': stats(shank), 'leg_force_peaks': maxima, 'foot_horizontal_speed': footstats, 'flight_paused_frame_count': int(paused.sum()), 'zero_current_foot_contact_frame_count': int((~cur.any(axis=1)).sum()), 'zero_history_foot_contact_frame_count': int((~hist.any(axis=1)).sum()), 'continuous_video_reviewed': False, 'timing_limit': m['synchronization_limit'], 'measurement_limit': 'Selected recorded environment only. Foot world-XY link speed with a normal-force contact gate is a proxy; it is not measured contact-point tangential slip. History contact and peak force include retained sensor samples. Raw action deltas and body motion do not certify smooth locomotion. Link positions are world coordinates; root and feet relative positions use the recorded course frame.'}
    sp = clip.parent / (stem + '-frame-telemetry-summary.json')
    sp.write_text(json.dumps(summary, indent=2) + '\n')
    (fig, axs) = plt.subplots(3, 2, figsize=(16, 11), sharex=True)
    ax = axs[0, 0]
    ax.plot(t, pos[:, 0], label='root x')
    ax.plot(t, pos[:, 2], label='root z')
    for (k, name) in enumerate(FEET):
        ax.plot(t, feet[:, k, 2], lw=0.7, alpha=0.65, label=name + ' foot z')
    ax.set_ylabel('Course position (m)')
    ax.legend(ncol=3, fontsize=8)
    ax = axs[0, 1]
    for (k, name) in enumerate('xyz'):
        ax.plot(t, vel[:, k], label='v' + name)
    ax.plot(t, [r['command_vx_vy_yaw'][0] for r in selected], 'k--', lw=0.8, label='cmd vx')
    ax.set_ylabel('World velocity (m/s)')
    ax.legend(ncol=4, fontsize=8)
    ax = axs[1, 0]
    for (k, name) in enumerate(['yaw', 'roll', 'pitch']):
        ax.plot(t, np.degrees(angles[:, k]), label=name)
    ax.set_ylabel('Body angle (deg)')
    ax.legend(ncol=3, fontsize=8)
    ax = axs[1, 1]
    for (k, name) in enumerate(FEET):
        ax.scatter(t[cur[:, k]], speed[cur[:, k], k], s=3, label=name)
    ax.set_ylabel('Foot XY speed during current contact (m/s)')
    ax.legend(ncol=4, fontsize=8)
    ax = axs[2, 0]
    for (k, name) in enumerate(LEGS):
        ax.plot(t, legcur[:, k], lw=0.8, label=name)
    ax.plot(t, leghist.max(axis=1), 'k:', lw=0.8, label='history max')
    ax.set_ylabel('Leg normal-force norm (N)')
    ax.legend(ncol=3, fontsize=7)
    ax = axs[2, 1]
    ax.plot(t, delta, label='action delta RMS')
    ax.plot(t, second, label='action second delta RMS')
    ax.scatter(t[paused], delta[paused], s=12, c='r', label='flight pause')
    ax.set_ylabel('Action delta')
    ax.legend(fontsize=8)
    for ax in axs.flat:
        ax.grid(alpha=0.2)
        ax.set_xlabel('Recorded simulation time (s)')
        ax.set_xlim(t[0], t[-1])
    fig.suptitle(f'{stem}: selected env {env}, {N} dense 20 ms samples; every clipped frame paired\nNominal video PTS + 20 ms; whole-episode descriptive proxies, continuous playback not reviewed', fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    plot = clip.parent / (stem + '-frame-telemetry.png')
    fig.savefig(plot, dpi=150)
    plt.close(fig)
    print(json.dumps({'csv': str(csvpath), 'rows': len(rows), 'columns': len(rows[0]), 'summary': str(sp), 'plot': str(plot), 'env': env, 'frames': N}), flush=True)

def read_inputs(clip):
    """Verify immutable input hashes and selected clean completion metadata."""
    meta = json.loads(clip.with_suffix('.json').read_text())
    require(digest(clip) == meta['output_video_sha256'], f'Clip hash changed: {clip}')
    run = Path(meta['run'])
    for name in ['config', 'result']:
        require(digest(run / (name + '.json')) == meta[name + '_sha256'], f'{name} hash changed: {run}')
    config = json.loads((run / 'config.json').read_text())
    result = json.loads((run / 'result.json').read_text())
    require(len(result['policy']['trials']) == 1, 'Require one recorded trial')
    require(result.get('zero_action') is None and (not result.get('additional_candidates')), 'Require one policy-only phase')
    require(config['video'] and config['video_policy_only'], 'Require policy-only video recording')
    require(config['evaluation_trace_stride_policy_steps'] == 1, 'Require one dense trace row per policy step')
    require(result['policy']['foot_body_names'] == [name + '_foot' for name in FEET], 'Unexpected foot ordering')
    require(result['policy']['leg_body_names'] == LEGS, 'Unexpected thigh/calf ordering')
    require(len(config['joint_names']) == 12, 'Require 12 named action joints')
    trial = result['policy']['trials'][0]
    env = meta['environment_id']
    require(env == config['video_environment_index'], 'Recorded environment mismatch')
    pe = trial['per_env']
    require(pe['completed'][env] and (not any((pe[flag][env] for flag in ['fall', 'stall', 'lateral_escape']))), 'Selected episode did not complete cleanly')
    dt = float(config['physics_dt']) * int(config['policy_decimation'])
    fps = float(meta['output_video_info']['fps'])
    N = int(meta['retained_frame_count'])
    require(math.isclose(dt * fps, 1.0, abs_tol=1e-06), 'Require one video frame per policy step')
    require(math.isclose(meta['policy_dt_s'], dt, abs_tol=1e-9), 'Provenance policy dt mismatch')
    require(meta['checkpoint'] == config['checkpoint'] and meta['seed'] == trial['seed'], 'Checkpoint/seed provenance mismatch')
    require(N == round(pe['first_episode_measured_duration_s'][env] / dt), 'Episode frame boundary mismatch')
    require(pe['first_episode_measured_duration_s'][env] < config['episode_length_s'] - dt / 2, 'Ambiguous timeout-ending episode')
    return (meta, config, trial)

def decode_info(clip, meta):
    """Decode the entire clip using OpenCV's CPU FFmpeg backend."""
    cap = cv2.VideoCapture(str(clip), cv2.CAP_FFMPEG)
    require(cap.isOpened(), f'Cannot open clip: {clip}')
    fps = cap.get(cv2.CAP_PROP_FPS)
    count = 0
    dimensions = None
    while True:
        (success, frame) = cap.read()
        if not success:
            break
        count += 1
        dimensions = [frame.shape[1], frame.shape[0]]
    cap.release()
    info = meta['output_video_info']
    require(count == meta['retained_frame_count'] == info['decoded_frame_count'], 'Full CPU decode frame count mismatch')
    require(math.isclose(fps, info['fps'], abs_tol=1e-06), 'Decoded frame rate mismatch')
    require(dimensions == [info['width'], info['height']], 'Decoded dimensions mismatch')
    require(0 <= CROP[0] < CROP[2] <= dimensions[0] and 0 <= CROP[1] < CROP[3] <= dimensions[1], 'Crop outside source dimensions')
    return count

def verify_materials(clip, meta, config, trial):
    """Cross-check every generated frame and every saved CSV scalar."""
    count = decode_info(clip, meta)
    stem = clip.stem.replace('-first-episode', '')
    index = json.loads((clip.parent / (stem + '-all-frames.json')).read_text())
    require(index['clip_sha256'] == digest(clip), 'Sheet clip hash mismatch')
    require(index['frame_count'] == count and index['crop_original_pixels_xyxy_exclusive'] == list(CROP), 'Sheet count/crop mismatch')
    covered = []
    for page in index['pages']:
        path = Path(page['path'])
        require(digest(path) == page['sha256'], f'Sheet hash mismatch: {path}')
        with Image.open(path) as im:
            require(list(im.size) == index['page_dimensions'], f'Sheet dimensions mismatch: {path}')
        (lo, hi) = page['frame_indices_inclusive']
        require(hi - lo + 1 == page['frame_count'], 'Invalid sheet frame range')
        covered.extend(range(lo, hi + 1))
    require(covered == list(range(count)), 'Sheets omit or duplicate retained frames')
    (_, expected) = paired_rows(trial, meta['environment_id'], count, meta['policy_dt_s'], meta['output_video_info']['fps'], config)
    csvpath = clip.parent / (stem + '-frame-telemetry.csv')
    with csvpath.open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == list(expected[0]), 'CSV schema/order mismatch')
        saved = list(reader)
    require(len(saved) == len(expected), 'CSV missing or extra rows')
    for (i, (actual, wanted)) in enumerate(zip(saved, expected)):
        for (key, value) in wanted.items():
            number = float(actual[key])
            require(math.isfinite(number) and number == value, f'CSV scalar mismatch at frame {i}, {key}')
    summary = json.loads((clip.parent / (stem + '-frame-telemetry-summary.json')).read_text())
    require(summary['csv_sha256'] == digest(csvpath), 'CSV summary hash mismatch')
    require(summary['frame_count'] == summary['csv_rows'] == count and summary['csv_columns'] == len(expected[0]), 'CSV summary coverage mismatch')
    print(json.dumps({'clip': str(clip), 'verified_frames': count, 'pages': len(index['pages']), 'csv_rows': len(saved), 'csv_columns': len(expected[0]), 'all_csv_scalars_match_dense_trace_and_frame_metadata': True}), flush=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('clips', nargs='*', type=Path, help='Completed first-episode MP4 clips with adjacent provenance JSON')
    parser.add_argument('--verify-only', action='store_true', help='Fully CPU-decode and verify existing sheets/CSV without rewriting artifacts')
    parser.add_argument('--overwrite', action='store_true', help='Explicitly regenerate existing material files')
    parser.add_argument('--font', type=Path, default=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'), help='Existing TrueType font for chronological sheet labels')
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    clips = args.clips or [base / (stem + '-first-episode.mp4') for stem in DEFAULT_PREFIXES]
    try:
        for path in clips:
            clip = path.expanduser().resolve()
            (meta, config, trial) = read_inputs(clip)
            if not args.verify_only:
                stem = clip.stem.replace('-first-episode', '')
                outputs = [clip.parent / (stem + ending) for ending in ['-all-frames', '-all-frames.json', '-frame-telemetry.csv', '-frame-telemetry-summary.json', '-frame-telemetry.png']]
                require(args.overwrite or not any((path.exists() for path in outputs)), 'Material output exists; use --verify-only or --overwrite')
                decode_info(clip, meta)
                write_sheets(clip, meta, args.font)
                write_telemetry(clip, meta)
            verify_materials(clip, meta, config, trial)
    except (ValueError, OSError, KeyError, IndexError, TypeError, AssertionError) as error:
        parser.exit(2, 'inspect-first-episode-frames: ' + str(error) + '\n')
if __name__ == '__main__':
    main()
