#!/usr/bin/env python3
"""Materialize explicitly incomplete pre-failure clips on CPU.

Pass existing MP4 clips with adjacent clip-pre-failure-video.py provenance.
Every retained frame is written to chronological 60-frame pages. Dense
telemetry is paired only when the exact recorded environment is present;
missing selected-environment traces never borrow a neighboring environment.
The failure guard is independent of the clean-completion helper. Neither the
full failed episode nor its exact terminal state is shown. No simulator runs.

  python3 -B reproduction/inspect-pre-failure-frames.py clip-prefailure.mp4
  python3 -B reproduction/inspect-pre-failure-frames.py --verify-only clip-prefailure.mp4
"""
import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    'cpu_frame_material_helpers', Path(__file__).with_name('inspect-first-episode-frames.py'))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
require, digest = helper.require, helper.digest


def validate_failure(meta, config, trial):
    """Validate the selected failed first episode and conservative frame bound."""
    require(meta['kind'] == 'incomplete_pre_failure_diagnostic', 'Require incomplete pre-failure provenance')
    require(config.get('mode') == 'evaluate' and config.get('terrain') == 'stairs', 'Require recorded staircase evaluation')
    require(config.get('video') and config.get('video_policy_only'), 'Require policy-only recording')
    env = meta['environment_id']
    require(isinstance(env, int) and not isinstance(env, bool) and 0 <= env < trial['num_envs'], 'Invalid selected environment')
    require(env == config['video_environment_index'], 'Recorded environment mismatch')
    pe = trial['per_env']
    flags = {flag: bool(pe[flag][env]) for flag in ['fall', 'stall', 'lateral_escape']}
    require(not pe['completed'][env] and any(flags.values()), 'Require explicitly failed selected first episode')
    require(meta['selected_environment_completed'] is False and meta['failure_flags'] == flags, 'Failure provenance mismatch')
    require(meta['checkpoint'] == config['checkpoint'] and meta['seed'] == trial['seed'], 'Checkpoint/seed provenance mismatch')
    dt = float(config['physics_dt']) * int(config['policy_decimation'])
    duration = float(pe['first_episode_measured_duration_s'][env])
    require(math.isfinite(dt) and dt > 0 and math.isfinite(duration) and duration > 2 * dt, 'Invalid failure duration or dt')
    failure_steps = round(duration / dt)
    require(math.isclose(duration / dt, failure_steps, abs_tol=1e-3, rel_tol=0), 'Failure duration is not policy-step aligned')
    require(math.isclose(meta['measured_first_episode_failure_time_s'], duration, abs_tol=1e-9, rel_tol=0), 'Failure time provenance mismatch')
    require(math.isclose(meta['policy_dt_s'], dt, abs_tol=1e-9, rel_tol=0), 'Policy dt provenance mismatch')
    n = meta['retained_frame_count']
    require(isinstance(n, int) and not isinstance(n, bool) and 0 < n <= failure_steps - 2, 'Retained clip must exclude terminal frame and one additional policy frame')
    require(meta['retained_source_frame_indices_inclusive'] == [0, n - 1], 'Require consecutive source frames starting at zero')
    require(all(math.isclose(a, b, abs_tol=1e-9, rel_tol=0) for a, b in zip(meta['nominal_retained_simulation_times_s'], [dt, n * dt])) and len(meta['nominal_retained_simulation_times_s']) == 2, 'Nominal retained times mismatch')
    require(math.isclose(meta['excluded_terminal_duration_s'], (failure_steps - n) * dt, abs_tol=1e-9, rel_tol=0), 'Excluded terminal interval mismatch')
    fps = float(meta['output_video_info']['fps'])
    require(math.isclose(dt * fps, 1, abs_tol=1e-6, rel_tol=0), 'Require one video frame per policy step')
    require(meta['output_video_info']['decoded_frame_count'] == n, 'Decoded count provenance mismatch')
    require(meta['source_video_info']['decoded_frame_count'] == min(trial['executed_steps'], config['video_length']), 'Source recorder count mismatch')
    require(meta['source_video_info']['decoded_frame_count'] >= n, 'Source ends before retained interval')
    require(math.isclose(meta['source_video_info']['fps'], fps, abs_tol=1e-6, rel_tol=0), 'Source/clip frame rate mismatch')
    require(meta['encoding']['hardware_acceleration'] == 'none' and meta['encoding']['b_frames'] == 0, 'Require CPU encoding without reordered frames')
    require(meta['continuous_video_reviewed'] is False, 'Material generation does not establish playback review')
    trace = trial.get('trace', [])
    present = [row for row in trace if env in row['env_ids']]
    for row in present:
        require(row['env_ids'].count(env) == 1, 'Duplicate selected environment in trace row')
    available = bool(present)
    if available:
        require(config['evaluation_trace_stride_policy_steps'] == 1, 'Selected telemetry must be dense')
        # Incomplete, inactive, nonfinite or misaligned selected traces are errors,
        # not grounds to silently replace them with an unavailable annotation.
        helper.paired_rows(trial, env, n, dt, fps, config)
    return available


def read_inputs(clip):
    meta = json.loads(clip.with_suffix('.json').read_text())
    require(digest(clip) == meta['output_video_sha256'], 'Clip hash changed')
    require(Path(meta['output_video']).resolve() == clip, 'Output path provenance mismatch')
    source = Path(meta['source_video'])
    require(source.resolve() != clip and digest(source) == meta['source_video_sha256'], 'Source video hash/path mismatch')
    run = Path(meta['run'])
    for name in ['config', 'result']:
        require(digest(run / (name + '.json')) == meta[name + '_sha256'], name + ' hash changed')
    config = json.loads((run / 'config.json').read_text())
    result = json.loads((run / 'result.json').read_text())
    require(len(result['policy']['trials']) == 1, 'Require one recorded reset seed')
    require(result.get('zero_action') is None and not result.get('additional_candidates'), 'Require single policy phase')
    require(result['policy']['foot_body_names'] == [name + '_foot' for name in helper.FEET], 'Unexpected foot ordering')
    require(result['policy']['leg_body_names'] == helper.LEGS, 'Unexpected leg ordering')
    require(len(config['joint_names']) == 12, 'Require 12 named action joints')
    trial = result['policy']['trials'][0]
    available = validate_failure(meta, config, trial)
    return meta, config, trial, available


def scope_fields(meta, trial, available):
    env = meta['environment_id']
    pe = trial['per_env']
    endpoint = {key: value[env] for key, value in pe.items()
                if isinstance(value, list) and len(value) == trial['num_envs']}
    return {
        'kind': 'incomplete_pre_failure_diagnostic',
        'telemetry_available': available,
        'telemetry_environment_id': env if available else None,
        'telemetry_unavailable_reason': None if available else 'Selected recorded environment is absent from saved trace; no neighboring environment was substituted.',
        'selected_environment_completed': False,
        'failure_flags': meta['failure_flags'],
        'measured_first_episode_failure_time_s': meta['measured_first_episode_failure_time_s'],
        'nominal_retained_simulation_times_s': meta['nominal_retained_simulation_times_s'],
        'excluded_terminal_duration_s': meta['excluded_terminal_duration_s'],
        'terminal_reset_guard': meta['terminal_reset_guard'],
        'full_failed_episode_shown': False,
        'exact_terminal_state_shown': False,
        'selected_environment_endpoint_from_result': endpoint,
        'endpoint_scope': 'Saved first-episode endpoint from the exact selected environment; this terminal measurement is not a paired retained video frame.',
        'continuous_video_reviewed': False,
    }


def material_stem(clip):
    # Keep the failure suffix so these outputs cannot collide with success ones.
    return clip.stem


def write_failure_plot(clip, meta, selected):
    """Plot only the retained interval with explicit failure-specific scope."""
    np, plt = helper.np, helper.plt
    t = np.array([r['time_s'] for r in selected])
    pos = np.array([r['root_relative_xyz'] for r in selected])
    vel = np.array([r['root_linear_velocity_w'] for r in selected])
    angles = np.array([r['yaw_roll_pitch'] for r in selected])
    feet = np.array([r['feet_relative_xyz'] for r in selected])
    speed = np.array([r['foot_horizontal_speed_m_s'] for r in selected])
    contact = np.array([r['current_sample_contacts'] for r in selected], dtype=bool)
    force = np.array([r['leg_current_normal_force_norm_n'] for r in selected])
    history = np.array([r['leg_history_peak_normal_force_norm_n'] for r in selected])
    fig, axs = plt.subplots(3, 2, figsize=(16, 11), sharex=True)
    for k, name in [(0, 'root x'), (2, 'root z')]:
        axs[0, 0].plot(t, pos[:, k], label=name)
    for k, name in enumerate(helper.FEET):
        axs[0, 0].plot(t, feet[:, k, 2], lw=.7, alpha=.65, label=name + ' foot z')
        axs[1, 1].scatter(t[contact[:, k]], speed[contact[:, k], k], s=3, label=name)
    axs[0, 0].set_ylabel('Course position (m)')
    axs[1, 1].set_ylabel('Foot XY speed during current contact (m/s)')
    for k, name in enumerate('xyz'):
        axs[0, 1].plot(t, vel[:, k], label='v' + name)
    axs[0, 1].plot(t, [r['command_vx_vy_yaw'][0] for r in selected], 'k--', lw=.8, label='cmd vx')
    axs[0, 1].set_ylabel('World velocity (m/s)')
    for k, name in enumerate(['yaw', 'roll', 'pitch']):
        axs[1, 0].plot(t, np.degrees(angles[:, k]), label=name)
    axs[1, 0].set_ylabel('Body angle (deg)')
    for k, name in enumerate(helper.LEGS):
        axs[2, 0].plot(t, force[:, k], lw=.8, label=name)
    axs[2, 0].plot(t, history.max(axis=1), 'k:', lw=.8, label='history max')
    axs[2, 0].set_ylabel('Leg normal-force norm (N)')
    axs[2, 1].plot(t, [r['action_delta_rms'] for r in selected], label='action delta RMS')
    axs[2, 1].plot(t, [r['action_second_delta_rms'] for r in selected], label='action second delta RMS')
    paused = np.array([r['flight_paused'] for r in selected], dtype=bool)
    delta = np.array([r['action_delta_rms'] for r in selected])
    axs[2, 1].scatter(t[paused], delta[paused], s=12, c='r', label='flight pause')
    axs[2, 1].set_ylabel('Action delta')
    for ax in axs.flat:
        ax.legend(ncol=3, fontsize=7)
        ax.grid(alpha=.2)
        ax.set_xlabel('Recorded simulation time (s)')
        ax.set_xlim(t[0], t[-1])
    fig.suptitle(f'{material_stem(clip)}: env {meta["environment_id"]}, {len(selected)} retained dense samples\n'
                 f'Incomplete pre-failure interval; final {meta["excluded_terminal_duration_s"]:.2f}s excluded; exact terminal state absent', fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(clip.parent / (material_stem(clip) + '-frame-telemetry.png'), dpi=150)
    plt.close(fig)


def write_materials(clip, meta, config, trial, available, font):
    helper.decode_info(clip, meta)
    helper.write_sheets(clip, meta, font)
    indexpath = clip.parent / (material_stem(clip) + '-all-frames.json')
    index = json.loads(indexpath.read_text())
    index.update(scope_fields(meta, trial, available))
    index['provenance_sha256'] = digest(clip.with_suffix('.json'))
    indexpath.write_text(json.dumps(index, indent=2) + '\n')
    if not available:
        return
    helper.write_telemetry(clip, meta)
    selected, rows = helper.paired_rows(trial, meta['environment_id'], meta['retained_frame_count'], meta['policy_dt_s'], meta['output_video_info']['fps'], config)
    csvpath = clip.parent / (material_stem(clip) + '-frame-telemetry.csv')
    with csvpath.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    summarypath = clip.parent / (material_stem(clip) + '-frame-telemetry-summary.json')
    summary = json.loads(summarypath.read_text())
    summary.update(scope_fields(meta, trial, available))
    summary['csv_sha256'] = digest(csvpath)
    summary['csv_line_ending'] = 'LF'
    summary['root_end_of_retained_interval_xyz_m'] = summary.pop('root_end_xyz_m')
    summary['measurement_limit'] = ('Retained pre-failure interval only; the terminal frame and one additional policy frame are excluded. '
                                    'The saved endpoint is a separate result measurement, not a retained video/trace pair. ' + summary['measurement_limit'])
    for peak in summary['leg_force_peaks']:
        peak['history_peak_force_n_over_retained_interval'] = peak.pop('history_peak_force_n_over_episode')
    summarypath.write_text(json.dumps(summary, indent=2) + '\n')
    write_failure_plot(clip, meta, selected)


def verify_materials(clip, meta, config, trial, available):
    count = helper.decode_info(clip, meta)
    stem = material_stem(clip)
    indexpath = clip.parent / (stem + '-all-frames.json')
    index = json.loads(indexpath.read_text())
    require(index['clip_sha256'] == digest(clip) and index['provenance_sha256'] == digest(clip.with_suffix('.json')), 'Sheet input hash mismatch')
    require(index['frame_count'] == count and index['crop_original_pixels_xyxy_exclusive'] == list(helper.CROP), 'Sheet count/crop mismatch')
    for key, value in scope_fields(meta, trial, available).items():
        require(index[key] == value, 'Failure scope mismatch: ' + key)
    covered = []
    for page in index['pages']:
        path = Path(page['path'])
        require(digest(path) == page['sha256'], 'Sheet hash mismatch: ' + str(path))
        with helper.Image.open(path) as im:
            require(list(im.size) == index['page_dimensions'], 'Sheet dimensions mismatch')
        lo, hi = page['frame_indices_inclusive']
        require(hi - lo + 1 == page['frame_count'] <= 60, 'Invalid sheet frame range')
        covered.extend(range(lo, hi + 1))
    require(covered == list(range(count)), 'Sheets omit or duplicate retained frames')
    telemetry_paths = [clip.parent / (stem + suffix) for suffix in ['-frame-telemetry.csv', '-frame-telemetry-summary.json', '-frame-telemetry.png']]
    if available:
        helper.verify_materials(clip, meta, config, trial)
        summary = json.loads(telemetry_paths[1].read_text())
        for key, value in scope_fields(meta, trial, available).items():
            require(summary[key] == value, 'Telemetry scope mismatch: ' + key)
        require('root_end_xyz_m' not in summary and summary['root_end_of_retained_interval_xyz_m'] == helper.paired_rows(trial, meta['environment_id'], count, meta['policy_dt_s'], meta['output_video_info']['fps'], config)[0][-1]['root_relative_xyz'], 'Retained endpoint scope mismatch')
        require(b'\r' not in telemetry_paths[0].read_bytes(), 'Require LF CSV line endings')
        require(telemetry_paths[2].is_file(), 'Missing retained telemetry plot')
    else:
        require(not any(path.exists() for path in telemetry_paths), 'Unavailable selected telemetry must not have substitute artifacts')
    print(json.dumps({'clip': str(clip), 'verified_frames': count, 'pages': len(index['pages']), 'telemetry_available': available, 'csv_rows': count if available else 0, 'full_failed_episode_shown': False, 'exact_terminal_state_shown': False}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('clips', nargs='+', type=Path, help='Explicit incomplete pre-failure MP4 clips with adjacent provenance')
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--font', type=Path, default=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    args = parser.parse_args()
    try:
        for path in args.clips:
            clip = path.expanduser().resolve()
            meta, config, trial, available = read_inputs(clip)
            if not args.verify_only:
                outputs = [clip.parent / (material_stem(clip) + suffix) for suffix in ['-all-frames', '-all-frames.json', '-frame-telemetry.csv', '-frame-telemetry-summary.json', '-frame-telemetry.png']]
                require(args.overwrite or not any(path.exists() for path in outputs), 'Output exists; use --verify-only or --overwrite')
                write_materials(clip, meta, config, trial, available, args.font)
            verify_materials(clip, meta, config, trial, available)
    except (ValueError, OSError, KeyError, IndexError, TypeError, AssertionError) as error:
        parser.exit(2, 'inspect-pre-failure-frames: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
