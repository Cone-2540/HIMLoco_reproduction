#!/usr/bin/env python3
"""Prepare or execute fixed first-episode videos with existing CPU review tools.

Default prints the manifest and commands; only --execute starts simulation.
Execution requires a matching frozen selection JSON, refuses a busy simulator,
and delegates deadline/cleanup to run-stair-night2-job.py. All 14 declared
cases keep env 0 and seed 907 even on failure. No software is installed.

  python3 -B reproduction/run-stair-night2-video-review.py \
    --checkpoint artifacts/selected/model.pt --profile contact_vertical
  # Add --selection-file FREEZE.json --execute after candidate freeze.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
import fcntl
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DEADLINE = datetime.fromisoformat("2026-10-12T07:20:00+08:00")
GEOMETRIES = ROOT / "reproduction/stair-night2-final-geometries.json"
PLAN = ROOT / "reproduction/stair-night2-evaluation-plan.json"
PROFILES = ("faithful", "contact", "contact_vertical", "contact_clearance")
CASES = (
    ("core-five-asc-speed03", 0, .3), ("core-five-desc-speed03", 1, .3),
    ("core-six16-asc-speed03", 2, .3), ("core-six16-desc-speed03", 3, .3),
    ("core-six16-asc-speed05", 2, .5), ("core-six16-desc-speed05", 3, .5),
    ("core-six17-asc-speed03", 4, .3), ("core-six17-desc-speed03", 5, .3),
    ("core-six17-asc-speed05", 4, .5), ("core-six17-desc-speed05", 5, .5),
    ("moderate-nosing-asc-speed03", 8, .3), ("moderate-nosing-desc-speed03", 9, .3),
    ("long12-asc-speed03", 12, .3), ("long12-desc-speed03", 13, .3),
)
SOURCE_PATHS = (
    "isaaclab/run.py", "isaaclab/run.sh", "isaaclab/stair_terrain.py",
    "isaaclab/stair_evaluation.py", "isaaclab/stair_rewards.py", "isaaclab/adapter.py",
    "reproduction/run-stair-night2-job.py", "reproduction/clip-first-episode-video.py",
    "reproduction/clip-pre-failure-video.py", "reproduction/inspect-first-episode-frames.py",
    "reproduction/inspect-pre-failure-frames.py", "reproduction/run-stair-night2-video-review.py",
)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def source_hashes():
    return {name: digest(ROOT / name) for name in SOURCE_PATHS}


def selected_jobs(labels=()):
    geometries = read_json(GEOMETRIES)
    wanted = set(labels)
    unknown = wanted - {label for label, _, _ in CASES}
    if unknown:
        raise ValueError("Unknown case labels: " + ", ".join(sorted(unknown)))
    jobs = []
    for label, index, speed in CASES:
        spec = deepcopy(geometries[index])
        jobs.append({"label": label, "final_case_index": index, "geometry": spec,
                     "speed_m_s": speed, "selected": not wanted or label in wanted,
                     "num_envs": 32, "camera_environment_id": 0, "reset_seed": 907,
                     "heading_control": "existing external yaw feedback, no lateral correction",
                     "seconds": 40, "fps": 50, "video_length_policy_steps": 2000,
                     "dense_trace_stride_policy_steps": 1})
    return jobs


def validate_selection(path, checkpoint, profile):
    if path is None:
        return {"file": None, "sha256": None, "status": "not_supplied; dry_run_only"}
    path = Path(path).expanduser().resolve()
    selected = read_json(path)
    frozen_path = selected.get("checkpoint", selected.get("selected_checkpoint"))
    frozen_hash = selected.get("checkpoint_sha256", selected.get("selected_checkpoint_sha256"))
    frozen_profile = selected.get("reward_profile", selected.get("selected_reward_profile",
                                selected.get("profile")))
    if not all(isinstance(item, str) and item for item in (frozen_path, frozen_hash, frozen_profile)):
        raise ValueError("Selection JSON needs checkpoint, checkpoint_sha256 and reward_profile fields")
    if frozen_path.startswith("/workspace/himloco/"):
        frozen_path = str(ROOT / frozen_path[len("/workspace/himloco/"):])
    resolved = Path(frozen_path)
    if not resolved.is_absolute():
        resolved = ROOT / resolved
    if resolved.resolve() != checkpoint or frozen_hash != digest(checkpoint) or frozen_profile != profile:
        raise ValueError("Selection checkpoint path/hash/profile does not match requested video candidate")
    return {"file": str(path), "sha256": digest(path), "status": "identity_matched",
            "scope": "Identity guard only; selection rationale and scientific acceptance require separate review"}


def wrapper_command(checkpoint, profile, job, geometry_path, suffix, max_seconds):
    return [sys.executable, str(ROOT / "reproduction/run-stair-night2-job.py"),
            "--name", f"night2-video-{job['label']}-{suffix}", "--max-seconds", str(max_seconds),
            "--", "evaluate", "--terrain", "stairs", "--reward_profile", profile,
            "--checkpoint", str(checkpoint), "--stair_batch", str(geometry_path),
            "--num_envs", "32", "--eval_seconds", "40", "--speed", str(job["speed_m_s"]),
            "--eval_randomized", "--eval_seed", "907", "--seed", "1", "--domain_profile", "none",
            "--eval_trace_stride", "1", "--video", "--video_policy_only", "--video_length", "2000",
            "--video_isolate_env", "--video_env_index", "0", "--video_eye", "2.4", "2.4", "1.7",
            "--video_lookat", "0", "0", "0.3"]


def assert_idle():
    script = """import json, os
busy=[]
for entry in os.listdir('/proc'):
    if not entry.isdigit() or int(entry)==os.getpid(): continue
    try:
        args=[item.decode(errors='replace') for item in open('/proc/'+entry+'/cmdline','rb').read().split(b'\\0') if item]
        if any(item.endswith('/isaaclab/run.py') for item in args):
            name=args[args.index('--run_name')+1] if '--run_name' in args else 'unnamed'
            busy.append({'pid':int(entry),'run_name':name})
    except (OSError, IndexError): pass
print(json.dumps(busy))
"""
    result = subprocess.run(["docker", "exec", "-e", "CUDA_VISIBLE_DEVICES=", "isaaclab-local-lab-1",
                             "/isaac-sim/kit/python/bin/python3", "-c", script],
                            capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise ValueError("Cannot establish simulator idle state: " + result.stderr.strip())
    busy = json.loads(result.stdout)
    if busy:
        raise ValueError("Simulator busy; no video started: " + json.dumps(busy))
    return {"status": "no_live_run_py_process", "checked_local": datetime.now().astimezone().isoformat()}


def assert_frozen(manifest):
    if digest(Path(manifest["checkpoint"])) != manifest["checkpoint_sha256"]:
        raise ValueError("Checkpoint changed after video manifest freeze")
    for name, expected in manifest["source_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("Source changed after video manifest freeze: " + name)
    for key, hash_key in (("geometry_file", "geometry_sha256"), ("evaluation_plan", "evaluation_plan_sha256")):
        if digest(Path(manifest[key])) != manifest[hash_key]:
            raise ValueError("Protocol file changed after video manifest freeze: " + manifest[key])
    selection = manifest["selection"]
    if selection["file"] and digest(Path(selection["file"])) != selection["sha256"]:
        raise ValueError("Selection JSON changed after video manifest freeze")


def run_cpu(command, directory, label):
    output = directory / (label + ".stdout.log")
    with output.open("x") as stream:
        result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    record = {"command": command, "exit_code": result.returncode,
              "stdout": str(output), "stdout_sha256": digest(output), "scope": "CPU only"}
    if result.returncode:
        raise ValueError("CPU artifact step failed; original video preserved: " + label)
    return record


def preview_artifacts(clip, directory):
    """CPU-decode every retained frame, create a smaller continuous MP4 and fixed overview."""
    import cv2
    from PIL import Image, ImageDraw
    spec = importlib.util.spec_from_file_location("night2_clip_helpers", ROOT / "reproduction/clip-first-episode-video.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    provenance = read_json(clip.with_suffix(".json"))
    frames = provenance["retained_frame_count"]
    fps = provenance["output_video_info"]["fps"]
    output = directory / (clip.stem + "-allframes-640.mp4")
    ffmpeg = helper.find_ffmpeg()
    command = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-nostdin", "-hwaccel", "none",
               "-threads", "2", "-i", str(clip), "-map", "0:v:0", "-vf", "scale=640:-2",
               "-frames:v", str(frames), "-r", str(fps), "-fps_mode", "cfr", "-an", "-c:v", "libx264",
               "-preset", "veryfast", "-crf", "24", "-bf", "0", "-threads", "2", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise ValueError("CPU low-resolution encoding failed: " + result.stderr.strip())
    checked = helper.video_info(output, decode=True)
    if checked["decoded_frame_count"] != frames or not math.isclose(checked["fps"], fps, abs_tol=1e-5):
        raise ValueError("Low-resolution video lost frames or changed cadence")
    selected = sorted({round((frames-1)*fraction) for fraction in (0., .2, .4, .6, .8, 1.)})
    canvas = Image.new("RGB", (960, 2 * 204 + 36), (18, 18, 18))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 8), "Fixed overview only; every-frame continuous clip preserved", fill="white")
    capture = cv2.VideoCapture(str(output))
    index, decoded = 0, 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if decoded in selected:
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((320, 180))
                x, y = index % 3 * 320, index // 3 * 204 + 36
                canvas.paste(image, (x, y))
                draw.text((x + 4, y + 184), f"frame {decoded} | PTS {decoded/fps:.2f}s", fill="white")
                index += 1
            decoded += 1
    finally:
        capture.release()
    if decoded != frames or index != len(selected):
        raise ValueError("CPU overview decode coverage disagrees")
    overview = directory / (clip.stem + "-overview.png")
    canvas.save(overview)
    record = {"kind": "CPU_visual_review_materials", "source_clip": str(clip), "source_clip_sha256": digest(clip),
              "low_resolution_continuous_video": str(output), "low_resolution_video_sha256": digest(output),
              "low_resolution_video_info": checked, "all_source_frames_retained": True,
              "overview": str(overview), "overview_sha256": digest(overview), "overview_frame_ids": selected,
              "continuous_video_reviewed": False,
              "scope": "Complete retained sequence decoded and re-encoded; no human or real-time viewing, no smoothness certification",
              "encoding_command": command}
    write_json(directory / (clip.stem + "-preview.json"), record)
    return record


def materialize(run, directory):
    config = read_json(run / "config.json")
    result = read_json(run / "result.json")
    trials = result["policy"]["trials"]
    if len(trials) != 1 or trials[0]["seed"] != 907 or config["video_environment_index"] != 0:
        raise ValueError("Recorded phase/seed/environment differs from the declared selection")
    trial = trials[0]
    per_env = trial["per_env"]
    flags = {name: bool(per_env[name][0]) for name in ("fall", "stall", "lateral_escape")}
    record = {"selected_environment_id": 0, "selected_reset_seed": 907,
              "selected_environment_completed": bool(per_env["completed"][0]), "failure_flags": flags,
              "population": {name: trial.get(name) for name in ("num_envs", "completions", "falls", "stalls",
                            "lateral_escapes", "base_contact_envs", "current_sample_base_contact_envs", "failure_reason")},
              "source_run": str(run), "config_sha256": digest(run / "config.json"),
              "result_sha256": digest(run / "result.json"), "cpu_steps": [], "continuous_video_reviewed": False}
    videos = list((run / "videos").glob("*.mp4"))
    record["source_videos"] = [{"path": str(path), "sha256": digest(path)} for path in videos]
    if len(videos) != 1:
        raise ValueError("Require exactly one recorded source video; all sources preserved")
    clean = record["selected_environment_completed"] and not any(flags.values())
    failed = not record["selected_environment_completed"] and any(flags.values())
    if not clean and not failed:
        record["materials_status"] = "uncompleted_or_invalid; original_video_preserved_no_clean_or_failure_clip"
        write_json(directory / "materials.json", record)
        return record
    clip = directory / ("selected-first-episode.mp4" if clean else "selected-prefailure.mp4")
    clip_script = "clip-first-episode-video.py" if clean else "clip-pre-failure-video.py"
    inspect_script = "inspect-first-episode-frames.py" if clean else "inspect-pre-failure-frames.py"
    try:
        record["cpu_steps"].append(run_cpu([sys.executable, "-B", str(ROOT / "reproduction" / clip_script),
                                            str(run), "--output", str(clip)], directory, "clip"))
        record["cpu_steps"].append(run_cpu([sys.executable, "-B", str(ROOT / "reproduction" / inspect_script),
                                            str(clip)], directory, "all-frames"))
        record["cpu_steps"].append(run_cpu([sys.executable, "-B", str(ROOT / "reproduction" / inspect_script),
                                            "--verify-only", str(clip)], directory, "verify-all-frames"))
        record["preview"] = preview_artifacts(clip, directory)
        record["materials_status"] = "complete_clean_first_episode_materials" if clean else "incomplete_prefailure_materials"
    except (ValueError, OSError, KeyError, ImportError) as error:
        record["materials_status"] = "CPU_processing_error; original_video_preserved"
        record["processing_error"] = str(error)
    write_json(directory / "materials.json", record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--selection-file", type=Path, help="Frozen JSON with checkpoint, checkpoint_sha256, reward_profile")
    parser.add_argument("--case-label", action="append", choices=[item[0] for item in CASES], default=[])
    parser.add_argument("--output-dir", type=Path, help="New directory for manifest/clips/CPU materials; default shared robotics logs")
    parser.add_argument("--max-seconds-per-job", type=float, default=900)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        checkpoint = args.checkpoint.expanduser().resolve()
        if not checkpoint.is_file() or not checkpoint.is_relative_to(ROOT):
            raise ValueError("Checkpoint must be an existing file within this repository")
        if args.max_seconds_per_job <= 0 or not math.isfinite(args.max_seconds_per_job):
            raise ValueError("max-seconds-per-job must be finite and positive")
        if args.execute and args.selection_file is None:
            raise ValueError("--execute requires a frozen --selection-file")
        selection = validate_selection(args.selection_file, checkpoint, args.profile)
        stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
        output = (args.output_dir or Path.home() / "robotics/logs" / (stamp + "_night2-video-review")).expanduser().resolve()
        inputs = ROOT / "isaaclab/logs" / (stamp + "_night2-video-inputs")
        jobs = selected_jobs(args.case_label)
        for job in jobs:
            job["geometry_input"] = str(inputs / (job["label"] + ".json"))
            job["command"] = wrapper_command(checkpoint, args.profile, job, Path(job["geometry_input"]),
                                              stamp.replace("-", ""), args.max_seconds_per_job)
            job["status"] = "prepared" if job["selected"] else "not_selected_by_explicit_subset"
        manifest = {"schema_version": 1, "created_local": datetime.now().astimezone().isoformat(),
                    "execute": args.execute, "status": "dry_run_no_GPU_or_container_calls",
                    "checkpoint": str(checkpoint), "checkpoint_sha256": digest(checkpoint),
                    "reward_profile": args.profile, "selection": selection,
                    "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                    "source_sha256": source_hashes(), "geometry_file": str(GEOMETRIES), "geometry_sha256": digest(GEOMETRIES),
                    "evaluation_plan": str(PLAN), "evaluation_plan_sha256": digest(PLAN),
                    "declared_case_count": 14, "selected_case_count": sum(job["selected"] for job in jobs),
                    "deadline_local": DEADLINE.isoformat(), "output_directory": str(output), "jobs": jobs,
                    "selection_rule": "Fixed env0/seed907 for each declared single-case32env scene; never reselect after failure",
                    "scene_scope": "Independent32env single-case videos; reset draws and physical layout differ from16-case512env final matrix",
                    "population_claim": "Video runs and env0 do not replace frozen final statistical matrix",
                    "continuous_video_reviewed": False, "scientific_acceptance": "NOT_ASSESSED"}
        if not args.execute:
            print(json.dumps(manifest, indent=2, allow_nan=False))
            return
        if datetime.now().astimezone() >= DEADLINE:
            raise ValueError("User-authorized deadline passed; no GPU job started")
        output.mkdir(parents=True, exist_ok=False)
        manifest_path = output / "video-review-manifest.json"
        write_json(manifest_path, manifest)
        lock_path = Path.home() / "robotics/logs/night2-video-review.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("Another video review runner holds the execution lock")
            try:
                manifest["initial_idle_readback"] = assert_idle()
                inputs.mkdir(parents=True, exist_ok=False)
                manifest["status"] = "executing_sequential_recordings"
                write_json(manifest_path, manifest)
                print("VIDEO_MANIFEST: " + str(manifest_path), flush=True)
                for job in jobs:
                    if not job["selected"]:
                        continue
                    if datetime.now().astimezone() >= DEADLINE:
                        job["status"] = "not_executed_deadline"
                        break
                    assert_frozen(manifest)
                    job["idle_readback"] = assert_idle()
                    geometry = Path(job["geometry_input"])
                    write_json(geometry, [job["geometry"]])
                    job["geometry_input_sha256"] = digest(geometry)
                    directory = output / job["label"]
                    directory.mkdir(exist_ok=False)
                    job["status"] = "recording_started"
                    job["started_local"] = datetime.now().astimezone().isoformat()
                    write_json(manifest_path, manifest)
                    wrapper_log = directory / "job-wrapper.stdout.log"
                    with wrapper_log.open("x") as stream:
                        process = subprocess.run(job["command"], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
                    job["wrapper_exit_code"] = process.returncode
                    job["wrapper_stdout"] = str(wrapper_log)
                    text = wrapper_log.read_text(errors="replace")
                    handles = [line[len("JOB_LOG: "):].strip() for line in text.splitlines() if line.startswith("JOB_LOG: ")]
                    if len(handles) != 1:
                        raise ValueError("Cannot identify exact job log; no new recording started")
                    record_path = Path(handles[0]) / "launch-record.json"
                    job["launch_record"] = str(record_path)
                    launch = read_json(record_path)
                    job["launch_record_sha256"] = digest(record_path)
                    if launch.get("simulator_log_dir"):
                        job["simulator_log_dir"] = launch["simulator_log_dir"]
                    if process.returncode or "simulator_log_dir" not in launch:
                        job["status"] = "recording_runtime_failed; partial_logs_preserved"
                        write_json(manifest_path, manifest)
                        raise ValueError("Recording runtime failed; review saved logs before restarting")
                    run = Path(launch["simulator_log_dir"])
                    try:
                        job["materials"] = materialize(run, directory)
                        job["status"] = job["materials"]["materials_status"]
                    except (ValueError, OSError, KeyError, IndexError, TypeError) as error:
                        job["status"] = "recorded_but_material_validation_error; original_video_preserved"
                        job["processing_error"] = str(error)
                    job["ended_local"] = datetime.now().astimezone().isoformat()
                    write_json(manifest_path, manifest)
                for job in jobs:
                    if job["selected"] and job["status"] == "prepared":
                        job["status"] = "not_executed_after_deadline_or_prior_stop"
                manifest["status"] = "recording_sequence_finished; manual_visual_review_and_statistical_acceptance_pending"
                manifest["ended_local"] = datetime.now().astimezone().isoformat()
                write_json(manifest_path, manifest)
                print(json.dumps({"manifest": str(manifest_path), "status": manifest["status"],
                                  "jobs": [{"label": job["label"], "status": job["status"]} for job in jobs]}, indent=2), flush=True)
            except (ValueError, OSError, subprocess.SubprocessError, KeyboardInterrupt) as error:
                manifest["status"] = "stopped_with_evidence_preserved"
                manifest["error"] = str(error)
                for job in jobs:
                    if job["selected"] and job["status"] == "prepared":
                        job["status"] = "not_executed_after_error_or_busy_guard"
                write_json(manifest_path, manifest)
                raise
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        parser.exit(2, "night2-video-review: " + str(error) + "\n")


if __name__ == "__main__":
    main()
