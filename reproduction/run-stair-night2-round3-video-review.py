#!/usr/bin/env python3
"""Prepare or execute fixed first-episode videos with existing CPU review tools.

Default prints the manifest and commands; only --execute starts simulation.
Execution requires a matching frozen selection JSON, refuses a busy simulator,
and delegates deadline/cleanup to run-stair-night2-job.py. All 14 declared
round3 reserved cases keep env 0 and reset seed 1301 even on failure. No software is installed.

  python3 -B reproduction/run-stair-night2-round3-video-review.py \
    --selection-file reproduction/stair-night2-round3-selected-final-freeze.json
  # Add --execute after root freezes and commits the candidate/workflow.
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
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DEADLINE = datetime.fromisoformat("2026-10-12T07:20:00+08:00")
GEOMETRIES = ROOT / "reproduction/stair-night2-round3-reserved-geometries.json"
PLAN = ROOT / "reproduction/stair-night2-round3-evaluation-proposal.json"
ENCODING_PROOF = ROOT / "reproduction/stair-night2-exact-video-cache-cpu.json"
PROFILES = ("faithful", "contact_light")
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
    "isaaclab/video_compat/sitecustomize.py", "isaaclab/video_compat/launch_exact_video.py",
    "reproduction/verify-exact-video-cache.py", "reproduction/stair-night2-exact-video-cache-cpu.json",
    "isaaclab/stair_evaluation.py", "isaaclab/stair_rewards.py", "isaaclab/adapter.py",
    "reproduction/run-stair-night2-job.py", "reproduction/clip-first-episode-video.py",
    "reproduction/clip-pre-failure-video.py", "reproduction/inspect-first-episode-frames.py",
    "reproduction/inspect-pre-failure-frames.py", "reproduction/run-stair-night2-video-review.py",
    "reproduction/run-stair-night2-round3-video-review.py",
    "reproduction/run-stair-night2-round3-comparison.py", "reproduction/audit-stair-night2-round3-source.py",
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
                     "num_envs": 32, "camera_environment_id": 0, "reset_seed": 1301,
                     "heading_control": "existing external yaw feedback, no lateral correction",
                     "seconds": 40, "fps": 50, "video_length_policy_steps": 2000,
                     "dense_trace_stride_policy_steps": 1})
    return jobs


def round3_backend():
    spec = importlib.util.spec_from_file_location("round3_video_guard", ROOT / "reproduction/run-stair-night2-round3-comparison.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_selection(path, checkpoint, profile):
    if path is None:
        return {"file": None, "sha256": None, "status": "not_supplied; dry_run_only"}
    path = Path(path).expanduser().resolve(strict=True)
    selection = read_json(path)
    round3 = round3_backend()
    proof_path = round3.explicit_file(selection["source_proof_file"])
    proof = read_json(proof_path)
    round3.validate_proof(proof)
    baseline, selected = round3.validate_selection(selection, proof_path, proof)
    if (ROOT / selected["checkpoint"]).resolve() != checkpoint or selected["checkpoint_sha256"] != digest(checkpoint) or selected["training_reward_profile"] != profile:
        raise ValueError("Full round3 selection does not match requested checkpoint/training profile")
    return {"file": str(path), "sha256": digest(path), "status": "full_round3_freeze_identity_source_protocol_verified",
            "source_proof_file": str(proof_path), "source_proof_sha256": digest(proof_path),
            "actual_training_identity": selected,
            "scope": "Full independent round3 freeze and complete development identity; no selection from final or video, no performance certification"}


def wrapper_command(checkpoint, profile, job, geometry_path, suffix, max_seconds):
    return [sys.executable, str(ROOT / "reproduction/run-stair-night2-job.py"),
            "--name", f"night2-round3-video-{job['label']}-{suffix}", "--max-seconds", str(max_seconds),
            "--", "evaluate", "--terrain", "stairs", "--reward_profile", "faithful",
            "--checkpoint", str(checkpoint), "--stair_batch", str(geometry_path),
            "--num_envs", "32", "--eval_seconds", "40", "--speed", str(job["speed_m_s"]),
            "--eval_randomized", "--eval_seed", "1301", "--seed", "1", "--domain_profile", "none",
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
    if validate_encoding_proof(manifest["source_sha256"]) != manifest["video_encoding_proof"]:
        raise ValueError("Real CPU cache index encoding evidence changed after video freeze")
    for key, hash_key in (("geometry_file", "geometry_sha256"), ("evaluation_plan", "evaluation_plan_sha256")):
        if digest(Path(manifest[key])) != manifest[hash_key]:
            raise ValueError("Protocol file changed after video manifest freeze: " + manifest[key])
    selection = manifest["selection"]
    if selection["file"]:
        if digest(Path(selection["file"])) != selection["sha256"]:
            raise ValueError("Selection JSON changed after video manifest freeze")
        current = validate_selection(selection["file"], Path(manifest["checkpoint"]), manifest["actual_training_reward_profile"])
        if current != selection:
            raise ValueError("Full round3 selection changed after video manifest freeze")


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


def materialize(run, directory, identity=None, encoding=None):
    config = read_json(run / "config.json")
    result = read_json(run / "result.json")
    trials = result["policy"]["trials"]
    if len(trials) != 1 or trials[0]["seed"] != 1301 or config["video_environment_index"] != 0:
        raise ValueError("Recorded phase/seed/environment differs from the declared selection")
    if identity is not None and ((ROOT / identity["checkpoint"]).resolve() != Path(config["checkpoint"].replace("/workspace/himloco/", str(ROOT) + "/")).resolve()
                                 or config.get("stair_reward", {}).get("profile") != "faithful"):
        raise ValueError("Video checkpoint or faithful scene construction differs from frozen identity")
    if trials[0]["num_envs"] != 32:
        raise ValueError("Recorded phase/seed/environment differs from the declared selection")
    trial = trials[0]
    per_env = trial["per_env"]
    flags = {name: bool(per_env[name][0]) for name in ("fall", "stall", "lateral_escape")}
    record = {"selected_environment_id": 0, "selected_reset_seed": 1301,
              "selected_environment_completed": bool(per_env["completed"][0]), "failure_flags": flags,
              "population": {name: trial.get(name) for name in ("num_envs", "completions", "falls", "stalls",
                            "lateral_escapes", "base_contact_envs", "current_sample_base_contact_envs", "failure_reason")},
              "source_run": str(run), "config_sha256": digest(run / "config.json"),
              "result_sha256": digest(run / "result.json"), "cpu_steps": [], "continuous_video_reviewed": False,
              "shared_scene_construction_reward_profile": "faithful",
              "actual_selected_training_identity": identity,
              "exact_rgb_cache_encoding": encoding,
              "training_profile_scope": "Actual profile/weights come from the full round3 freeze/archive identity; faithful construction rewards never identify training reward."}
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


def host_path(path):
    value = str(path)
    if value.startswith("/workspace/himloco/"):
        return (ROOT / value[len("/workspace/himloco/"):]).resolve()
    return Path(value).resolve()


def validate_encoding_proof(frozen_sources):
    """Require the exact current overlay/dependencies to have passed real CPU IDs."""
    if digest(ENCODING_PROOF) != frozen_sources["reproduction/stair-night2-exact-video-cache-cpu.json"]:
        raise ValueError("CPU RGB cache proof changed after source freeze")
    proof = read_json(ENCODING_PROOF)
    if proof.get("schema_version") != 1 or proof.get("status") != "passed":
        raise ValueError("Real CPU RGB cache encoding verification did not pass")
    for key, relative in (("overlay", "isaaclab/video_compat/sitecustomize.py"),
                          ("verifier", "reproduction/verify-exact-video-cache.py")):
        if (proof.get(key, {}).get("sha256") != frozen_sources[relative]
                or host_path(proof.get(key, {}).get("path", "")) != (ROOT / relative).resolve()):
            raise ValueError("CPU encoding proof source differs from frozen " + key)
    dependencies = {key: proof.get(key) for key in ("moviepy_image_sequence", "moviepy_clip", "ffmpeg")}
    if any(not isinstance(value, dict) or not value.get("path")
           or not re.fullmatch(r"[0-9a-f]{64}", value.get("sha256", "")) for value in dependencies.values()):
        raise ValueError("CPU encoding proof lacks actual writer dependency fingerprints")
    cases = proof.get("cases", [])
    if [case.get("cache_frames") for case in cases] != [392, 402, 957, 963, 2000]:
        raise ValueError("CPU encoding proof does not cover all five preregistered cache lengths")
    evidence = []
    for case in cases:
        count = case["cache_frames"]
        if (case.get("fps") != 50 or case.get("encoded_decoded_frames") != count
                or case.get("iterator_each_cache_entry_exactly_once") is not True
                or case.get("encoded_decoded_frame_ids_exactly_0_through_n_minus_1") is not True
                or case.get("decoded_frame_ids") != list(range(count))):
            raise ValueError("CPU encoding proof lost, duplicated or reordered a RGB cache entry")
        mp4 = case.get("encoded_mp4", {})
        artifact = host_path(mp4.get("path", ""))
        if not artifact.is_relative_to(ROOT / "isaaclab/logs") or digest(artifact) != mp4.get("sha256"):
            raise ValueError("CPU encoding frame-ID fixture artifact changed or is missing")
        evidence.append({"cache_frames": count, "all_decoded_frame_ids_verified": True,
                         "encoded_mp4": str(artifact), "encoded_mp4_sha256": digest(artifact)})
    return {"status": "real_CPU_encoding_decoding_all_index_IDs_verified",
            "file": str(ENCODING_PROOF), "sha256": digest(ENCODING_PROOF),
            "overlay": proof["overlay"], "verifier": proof["verifier"],
            "environment": {key: proof[key] for key in ("python", "numpy")},
            "writer_dependencies": dependencies, "cases": evidence,
            "scope": "Actual existing container CPU RGB cache index and libx264 ordering proof; no GPU/locomotion acceptance"}


def verify_exact_encoding(run, wrapper_directory, frozen_sources, encoding_proof):
    """Bind actual cache iterator markers to source hashes and full CPU decode.

    Frame counts alone cannot prove that MoviePy did not skip/duplicate cache
    entries. Require the separately CPU-validated integer-index writer to have
    been activated and fully exhausted in this exact recording.
    """
    stdout = Path(wrapper_directory) / "stdout.log"
    records = {"active": [], "emitted": [], "wrote": []}
    prefixes = (("active", "HIM_VIDEO_COMPAT_ACTIVE "),
                ("emitted", "HIM_VIDEO_COMPAT_EMITTED "))
    with stdout.open(errors="replace") as stream:
        for line in stream:
            for segment in line.split("\r"):
                segment = segment.strip()
                for key, prefix in prefixes:
                    if segment.startswith(prefix):
                        records[key].append(json.loads(segment[len(prefix):]))
                match = re.fullmatch(r"\[INFO\]: \[VideoRecorder\] Wrote (\d+) frames to (.+)", segment)
                if match:
                    records["wrote"].append({"frames": int(match[1]), "video": match[2]})
    if any(len(values) != 1 for values in records.values()):
        raise ValueError("Require exactly one ACTIVE, EMITTED and Lab Wrote record for this RGB video")
    active, emitted, wrote = (records[key][0] for key in ("active", "emitted", "wrote"))
    if any(record.get("schema_version") != 1 or record.get("method") != "integer_index_rgb_v1"
           for record in (active, emitted)) or active.get("patched") is not True:
        raise ValueError("Exact RGB cache encoding marker method/activation differs")
    for key, relative in (("overlay", "isaaclab/video_compat/sitecustomize.py"),
                          ("launcher", "isaaclab/video_compat/launch_exact_video.py")):
        expected = frozen_sources[relative]
        if (active.get(key + "_sha256") != expected or active.get(key, {}).get("sha256") != expected
                or host_path(active.get(key, {}).get("path", "")) != (ROOT / relative).resolve()):
            raise ValueError("Actual video compatibility source differs from frozen " + key)
    if emitted.get("overlay_sha256") != frozen_sources["isaaclab/video_compat/sitecustomize.py"]:
        raise ValueError("Emitted RGB cache marker overlay hash differs")
    if encoding_proof.get("status") != "real_CPU_encoding_decoding_all_index_IDs_verified":
        raise ValueError("Actual RGB recorder lacks validated real CPU encoding proof")
    for key, expected in encoding_proof["writer_dependencies"].items():
        if active.get(key) != expected:
            raise ValueError("Actual video writer dependency differs from verified CPU " + key)
    if {key: active.get(key) for key in ("python", "numpy")} != encoding_proof["environment"]:
        raise ValueError("Actual video Python/NumPy environment differs from verified CPU writer")
    cfg, result = read_json(run / "config.json"), read_json(run / "result.json")
    trials = result.get("policy", {}).get("trials", [])
    if len(trials) != 1 or result.get("zero_action") is not None or result.get("additional_candidates"):
        raise ValueError("Exact video coverage requires one policy phase/trial only")
    executed, length = trials[0].get("executed_steps"), cfg.get("video_length")
    if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in (executed, length)):
        raise ValueError("Exact video requires positive executed steps and recorder length")
    expected_count = min(executed, length)
    if any(isinstance(v, bool) or not isinstance(v, int) or v != expected_count
           for v in (emitted.get("cache_frame_count"), emitted.get("frames_yielded"), wrote["frames"])):
        raise ValueError("Exact RGB cache/yielded/Lab Wrote count differs from executed steps")
    videos = sorted((run / "videos").glob("*.mp4"))
    if len(videos) != 1 or host_path(wrote["video"]) != videos[0].resolve():
        raise ValueError("Lab Wrote path differs from the unique actual source video")
    spec = importlib.util.spec_from_file_location("round3_exact_video_decode", ROOT / "reproduction/clip-first-episode-video.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    info = helper.video_info(videos[0], decode=True)
    if info["decoded_frame_count"] != expected_count:
        raise ValueError("CPU decoded source count differs from actual RGB cache/executed steps")
    policy_dt = float(cfg["physics_dt"]) * int(cfg["policy_decimation"])
    if (not math.isclose(float(emitted.get("fps", 0)), 50., rel_tol=0, abs_tol=1e-9)
            or not math.isclose(float(cfg.get("video_fps", 0)), 50., rel_tol=0, abs_tol=1e-9)
            or not math.isclose(info["fps"], 50., rel_tol=0, abs_tol=1e-5)
            or not math.isclose(policy_dt, .02, rel_tol=0, abs_tol=1e-9)):
        raise ValueError("RGB cache/source/configured fps or policy cadence differs from 50Hz")
    return {"status": "actual_integer_index_rgb_cache_and_full_CPU_source_decode_verified",
            "active": active, "emitted": emitted, "lab_wrote": wrote,
            "actual_container_CPU_encoding_proof": encoding_proof,
            "stdout": str(stdout), "stdout_sha256": digest(stdout),
            "source_video": str(videos[0]), "source_video_sha256": digest(videos[0]),
            "source_video_info": info, "expected_source_frames": expected_count,
            "cache_indices_inclusive": [0, expected_count - 1],
            "scope": "Actual isolated integer-index encoder source and exhaustion markers plus full source CPU decode; preserves every RGB cache entry. This alone does not certify policy smoothness."}


def verify_recorded_identity(run, job, identity):
    cfg, result = read_json(run / "config.json"), read_json(run / "result.json")
    checkpoint = cfg.get("checkpoint", "")
    if checkpoint.startswith("/workspace/himloco/"):
        checkpoint = str(ROOT / checkpoint[len("/workspace/himloco/"):])
    elif not Path(checkpoint).is_absolute():
        checkpoint = str(ROOT / checkpoint)
    if Path(checkpoint).resolve() != (ROOT / identity["checkpoint"]).resolve():
        raise ValueError("Recorded checkpoint differs from full round3 freeze")
    if (cfg.get("mode") != "evaluate" or cfg.get("terrain") != "stairs" or cfg.get("num_envs") != 32
            or cfg.get("seed") != 1 or cfg.get("evaluation_seconds") != 40
            or cfg.get("evaluation_trace_stride_policy_steps") != 1
            or cfg.get("video_environment_index") != 0 or cfg.get("video_policy_only") is not True
            or cfg.get("stair_reward", {}).get("profile") != "faithful"):
        raise ValueError("Recorded video construction/coverage differs from declared job")
    policy = result["policy"]
    trials = policy.get("trials", [])
    if len(trials) != 1 or trials[0].get("seed") != 1301 or trials[0].get("num_envs") != 32:
        raise ValueError("Recorded video reset seed/population differs")
    if policy.get("heading_control", {}).get("enabled") is not True or policy.get("command_forward_speed_m_s") != job["speed_m_s"]:
        raise ValueError("Recorded video speed/controller differs")
    geometry_spec = importlib.util.spec_from_file_location("round3_video_geometry_guard", ROOT / "reproduction/summarize-stair-night2.py")
    geometry_helper = importlib.util.module_from_spec(geometry_spec)
    geometry_spec.loader.exec_module(geometry_helper)
    if [geometry_helper.geometry_key(g) for g in policy.get("geometry", [])] != [geometry_helper.geometry_key(job["geometry"])]:
        raise ValueError("Recorded video geometry differs from the reserved case")
    return {"status": "recorded_round3_checkpoint_scene_geometry_seed_camera_verified",
            "result_sha256": digest(run / "result.json"), "config_sha256": digest(run / "config.json"),
            "actual_training_profile_from_freeze": identity["training_reward_profile"],
            "scene_construction_profile": "faithful"}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checkpoint", type=Path, help="Dry-run candidate, or must match full selected freeze")
    parser.add_argument("--profile", choices=PROFILES, help="Actual training profile, derived from freeze when supplied")
    parser.add_argument("--selection-file", type=Path, help="Full independently validated round3 freeze, mandatory for execute")
    parser.add_argument("--labels", nargs="+", choices=[item[0] for item in CASES], default=[], help="Explicit subset; repeat an item only in a new output directory, prior evidence is preserved")
    parser.add_argument("--output-dir", type=Path, help="New directory for manifest/clips/CPU materials; default shared robotics logs")
    parser.add_argument("--max-seconds-per-job", type=float, default=900)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if args.selection_file:
            declared = read_json(args.selection_file)["selected"]
            args.checkpoint = args.checkpoint or ROOT / declared["checkpoint"]
            args.profile = args.profile or declared["training_reward_profile"]
        if args.checkpoint is None or args.profile is None:
            raise ValueError("Supply full round3 selection or dry-run checkpoint/profile")
        checkpoint = args.checkpoint.expanduser().resolve()
        if not checkpoint.is_file() or not checkpoint.is_relative_to(ROOT):
            raise ValueError("Checkpoint must be an existing file within this repository")
        if args.max_seconds_per_job <= 0 or not math.isfinite(args.max_seconds_per_job):
            raise ValueError("max-seconds-per-job must be finite and positive")
        if args.execute and args.selection_file is None:
            raise ValueError("--execute requires a frozen --selection-file")
        selection = validate_selection(args.selection_file, checkpoint, args.profile)
        frozen_sources = source_hashes()
        encoding_proof = validate_encoding_proof(frozen_sources)
        stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
        output = (args.output_dir or Path.home() / "robotics/logs" / (stamp + "_night2-round3-video-review")).expanduser().resolve()
        inputs = ROOT / "isaaclab/logs" / (stamp + "_night2-round3-video-inputs")
        jobs = selected_jobs(args.labels)
        for job in jobs:
            job["geometry_input"] = str(inputs / (job["label"] + ".json"))
            job["command"] = wrapper_command(checkpoint, args.profile, job, Path(job["geometry_input"]),
                                              stamp.replace("-", ""), args.max_seconds_per_job)
            job["status"] = "prepared" if job["selected"] else "not_selected_by_explicit_subset"
        manifest = {"schema_version": 1, "round": 3, "created_local": datetime.now().astimezone().isoformat(),
                    "execute": args.execute, "status": "dry_run_no_GPU_or_container_calls",
                    "checkpoint": str(checkpoint), "checkpoint_sha256": digest(checkpoint),
                    "actual_training_reward_profile": args.profile, "scene_construction_reward_profile": "faithful", "selection": selection,
                    "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                    "source_sha256": frozen_sources, "video_encoding_proof": encoding_proof,
                    "geometry_file": str(GEOMETRIES), "geometry_sha256": digest(GEOMETRIES),
                    "evaluation_plan": str(PLAN), "evaluation_plan_sha256": digest(PLAN),
                    "declared_case_count": 14, "selected_case_count": sum(job["selected"] for job in jobs),
                    "deadline_local": DEADLINE.isoformat(), "output_directory": str(output), "jobs": jobs,
                    "selection_rule": "Fixed env0/seed1301 for each declared single-case32env scene; never reselect after failure",
                    "scene_scope": "Independent32env single-case videos; reset draws and physical layout differ fromreserved16-case512env round3 final matrix",
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
                # New video/clip workflow must be committed before actual recording.
                dirty = subprocess.check_output(["git", "status", "--porcelain", "--", *SOURCE_PATHS], cwd=ROOT, text=True)
                if dirty.strip():
                    raise ValueError("Commit video/clip workflow before execution")
                for name, expected in manifest["source_sha256"].items():
                    committed = subprocess.check_output(["git", "show", manifest["source_commit"] + ":" + name], cwd=ROOT)
                    if hashlib.sha256(committed).hexdigest() != expected:
                        raise ValueError("Video source differs from declared commit: " + name)
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
                    expected_name = job["command"][job["command"].index("--name") + 1]
                    expected_source = {n: manifest["source_sha256"][n] for n in round3_backend().backend.SOURCE_FILES}
                    if launch.get("name") != expected_name or launch.get("status") != "exited" or launch.get("exit_code") != 0 or launch.get("source_sha256") != expected_source:
                        raise ValueError("Recorded wrapper completion or exact runtime source differs")
                    run = Path(launch["simulator_log_dir"])
                    try:
                        job["recorded_identity"] = verify_recorded_identity(run, job, selection["actual_training_identity"])
                        job["exact_rgb_cache_encoding"] = verify_exact_encoding(run, record_path.parent, manifest["source_sha256"], manifest["video_encoding_proof"])
                        job["materials"] = materialize(run, directory, selection["actual_training_identity"], job["exact_rgb_cache_encoding"])
                        job["status"] = job["materials"]["materials_status"]
                    except (ValueError, OSError, KeyError, IndexError, TypeError) as error:
                        job["status"] = "recorded_but_material_validation_error; original_video_preserved"
                        job["processing_error"] = str(error)
                    job["post_recording_idle_readback"] = assert_idle()
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
        parser.exit(2, "night2-round3-video-review: " + str(error) + "\n")


if __name__ == "__main__":
    main()
