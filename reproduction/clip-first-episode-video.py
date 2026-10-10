#!/usr/bin/env python3
"""Clip a completed staircase episode using exact video frame boundaries.

Example:
    python3 reproduction/clip-first-episode-video.py RUN --output clip.mp4

Uses existing OpenCV and a local FFmpeg executable; never starts a simulator.
The pinned recorder writes one frame after each policy step, starting at step
one. Encoded PTS zero therefore corresponds nominally to simulation time dt.
Only a clean completion before the environment timeout is accepted: the saved
metadata cannot distinguish a terminal pre-reset measurement from a video
frame captured after automatic reset for failed or timeout-ending episodes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import cv2


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_ffmpeg(explicit=None):
    candidates = [explicit] if explicit is not None else [shutil.which("ffmpeg")]
    if explicit is None:
        for binaries in (
            Path.home() / "isaaclab/data/python-extras/video/imageio_ffmpeg/binaries",
            Path("/workspace/isaaclab/data_storage/python-extras/video/imageio_ffmpeg/binaries"),
        ):
            candidates.extend(sorted(binaries.glob("ffmpeg-*")))
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser().resolve()
            if path.is_file() and os.access(path, os.X_OK):
                return path
    raise ValueError("No existing FFmpeg executable found; supply its local path with --ffmpeg")


def video_info(path, *, decode=False):
    capture = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG)
    if not capture.isOpened():
        raise ValueError(f"Cannot open video: {path}")
    try:
        info = {
            "fps": float(capture.get(cv2.CAP_PROP_FPS)),
            "reported_frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
            "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        }
        if not math.isfinite(info["fps"]) or info["fps"] <= 0 or info["reported_frame_count"] <= 0:
            raise ValueError(f"Invalid video metadata: {path}")
        if decode:
            count = 0
            while True:
                success, _ = capture.read()
                if not success:
                    break
                count += 1
            info["decoded_frame_count"] = count
            if count != info["reported_frame_count"]:
                raise ValueError(f"Video frame count disagrees with complete CPU decode: {path} "
                                 f"(reported {info['reported_frame_count']}, decoded {count})")
        return info
    finally:
        capture.release()


def frame_plan(config, result, source_info):
    if not config.get("video") or not config.get("video_policy_only"):
        raise ValueError("Require a recorded policy-only run")
    if config.get("mode") != "evaluate" or config.get("terrain") != "stairs":
        raise ValueError("Require a staircase evaluation run")
    if result.get("zero_action") is not None or result.get("additional_candidates"):
        raise ValueError("Require a single policy phase without zero-action controls or candidate phases")
    trials = result.get("policy", {}).get("trials", [])
    if len(trials) != 1:
        raise ValueError("Require exactly one evaluation trial/reset seed in the recorded run")
    trial = trials[0]
    env_id = config.get("video_environment_index", config.get("video_env_index"))
    if ("video_environment_index" in config and "video_env_index" in config
            and config["video_environment_index"] != config["video_env_index"]):
        raise ValueError("Conflicting recorded environment indices")
    if isinstance(env_id, bool) or not isinstance(env_id, int) or not 0 <= env_id < trial["num_envs"]:
        raise ValueError("Missing or invalid recorded video environment index")
    per_env = trial["per_env"]
    if not per_env["completed"][env_id] or any(
            per_env[flag][env_id] for flag in ("fall", "stall", "lateral_escape")):
        raise ValueError("Selected environment did not complete cleanly; its terminal video frame may contain an automatic reset")
    duration = float(per_env["first_episode_measured_duration_s"][env_id])
    completion_time = float(per_env["completion_time_s"][env_id])
    dt = float(config["physics_dt"]) * int(config["policy_decimation"])
    horizon = float(config["episode_length_s"])
    fps = source_info["fps"]
    if not all(math.isfinite(v) and v > 0 for v in (duration, completion_time, dt, horizon)):
        raise ValueError("Require finite positive episode duration, completion time, policy dt and horizon")
    if duration >= horizon - dt / 2:
        raise ValueError("Episode ends at the environment timeout; the last rendered frame may follow automatic reset")
    if not math.isclose(duration, completion_time, abs_tol=dt/100, rel_tol=0):
        raise ValueError("First-episode duration and completion time disagree")
    if not math.isclose(fps * dt, 1.0, abs_tol=1e-5, rel_tol=0):
        raise ValueError("Require one encoded frame per policy step; video fps and policy dt disagree")
    if not math.isclose(float(config.get("video_fps", fps)), fps, abs_tol=1e-5, rel_tol=0):
        raise ValueError("Configured and encoded video frame rates disagree")
    steps_float = duration / dt
    frames = round(steps_float)
    # Float32 episode durations can lie just below an integer step boundary.
    if frames <= 0 or not math.isclose(steps_float, frames, abs_tol=1e-3, rel_tol=0):
        raise ValueError("First-episode duration does not align with a policy step")
    source_frames = source_info["reported_frame_count"]
    executed = int(trial["executed_steps"])
    expected_source_frames = min(executed, int(config.get("video_length", executed)))
    if source_frames != expected_source_frames:
        raise ValueError("Source frame count does not match recorder length/executed steps; cannot verify phase alignment")
    if source_frames < frames:
        raise ValueError(f"Video ends before the selected episode: need {frames} frames, recorded {source_frames}")
    traced = [(row["time_s"], row["active"][row["env_ids"].index(env_id)])
              for row in trial.get("trace", []) if env_id in row["env_ids"]]
    for when, active in traced:
        if when <= frames * dt + dt/100 and not active:
            raise ValueError("Saved trace marks the selected environment inactive inside the requested clip")
    return {
        "environment_id": env_id, "seed": trial["seed"], "completed": True,
        "first_episode_measured_duration_s": duration, "completion_time_s": completion_time,
        "policy_dt_s": dt, "retained_frame_count": frames,
        "retained_source_frame_indices_inclusive": [0, frames-1],
        "discarded_trailing_frame_count": source_frames-frames,
        "encoded_duration_s": frames/fps, "last_encoded_frame_pts_s": (frames-1)/fps,
        "nominal_simulation_frame_times_s": [dt, frames*dt],
        "environment_timeout_s": horizon,
        "boundary_rule": "Keep source frames 0 through round(first_episode_duration/policy_dt)-1 inclusive; the next frame starts the selected environment's post-completion phase.",
        "terminal_reset_guard": "Selected environment completed without fall/stall/escape, before its environment timeout; ambiguous failed or timeout-ending episodes are rejected.",
        "trace_samples_for_selected_environment": len(traced),
        "trace_last_active_time_s": max((t for t, active in traced if active), default=None),
        "trace_first_inactive_time_s": min((t for t, active in traced if not active), default=None),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="Directory containing config.json, result.json and one recorded MP4")
    parser.add_argument("--output", type=Path, required=True, help="Local output MP4; adjacent JSON records provenance")
    parser.add_argument("--ffmpeg", type=Path, help="Use this existing local FFmpeg executable")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing output MP4 and provenance JSON")
    args = parser.parse_args()
    try:
        run, output = args.run.expanduser().resolve(), args.output.expanduser().resolve()
        if output.suffix.lower() != ".mp4":
            raise ValueError("Output must have the .mp4 extension")
        sidecar = output.with_suffix(".json")
        videos = sorted((run / "videos").glob("*.mp4"))
        if len(videos) != 1:
            raise ValueError("Require exactly one source video in the run's videos directory")
        source = videos[0].resolve()
        if output == source or sidecar in (run/"config.json", run/"result.json"):
            raise ValueError("Output must not replace source video or run metadata")
        if not args.overwrite and (output.exists() or sidecar.exists()):
            raise ValueError("Output or provenance already exists; choose another path or use --overwrite")
        config = json.loads((run/"config.json").read_text())
        result = json.loads((run/"result.json").read_text())
        source_info = video_info(source, decode=True)
        plan = frame_plan(config, result, source_info)
        ffmpeg = find_ffmpeg(args.ffmpeg)
        version = subprocess.run([str(ffmpeg), "-hide_banner", "-version"], check=True,
                                 capture_output=True, text=True).stdout.splitlines()[0]
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".first-episode-", dir=output.parent) as temp:
            encoded = Path(temp)/"clip.mp4"
            command = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-nostdin",
                       "-hwaccel", "none", "-threads", "2", "-i", str(source),
                       "-map", "0:v:0", "-vf",
                       f"trim=start_frame=0:end_frame={plan['retained_frame_count']},setpts=N/({source_info['fps']:.12g}*TB)",
                       "-frames:v", str(plan["retained_frame_count"]), "-r", f"{source_info['fps']:.12g}",
                       "-fps_mode", "cfr",
                       "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                       "-bf", "0", "-threads", "2", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(encoded)]
            subprocess.run(command, check=True, capture_output=True, text=True)
            output_info = video_info(encoded, decode=True)
            if (output_info["decoded_frame_count"] != plan["retained_frame_count"]
                    or not math.isclose(output_info["fps"], source_info["fps"], abs_tol=1e-5)
                    or (output_info["width"], output_info["height"]) != (source_info["width"], source_info["height"])):
                raise ValueError("CPU-decoded output frame count, frame rate or dimensions failed verification")
            provenance = {
                "schema_version": 1, "run": str(run), "checkpoint": config.get("checkpoint"),
                "source_video": str(source), "output_video": str(output),
                "source_video_sha256": sha256(source), "output_video_sha256": sha256(encoded),
                "config_sha256": sha256(run/"config.json"), "result_sha256": sha256(run/"result.json"),
                "source_video_info": source_info, "output_video_info": output_info, **plan,
                "encoding": {"ffmpeg": str(ffmpeg), "version": version, "codec": "libx264",
                             "hardware_acceleration": "none", "audio": "removed", "b_frames": 0,
                             "timestamp_rule": "Rebase retained frame n to n/source_fps; encode constant frame rate without B frames.",
                             "command_with_final_output": command[:-1]+[str(output)]},
                "synchronization_limit": "Nominal simulation time is encoded frame PTS plus one policy dt (20 ms in the pinned 50 fps runs). Exact renderer/physics synchronization was not independently instrumented.",
                "continuous_video_reviewed": False,
                "scope": "Complete selected first episode by recorded frame boundaries; excludes subsequent zero-action/post-completion frames. Frame-count verification does not certify locomotion smoothness or visual contact points.",
            }
            metadata = Path(temp)/"clip.json"
            metadata.write_text(json.dumps(provenance, indent=2)+"\n")
            encoded.replace(output)
            metadata.replace(sidecar)
        print(json.dumps({"output": str(output), "provenance": str(sidecar),
                          "frames": plan["retained_frame_count"], "fps": output_info["fps"],
                          "duration_s": plan["encoded_duration_s"],
                          "discarded_trailing_frames": plan["discarded_trailing_frame_count"]}))
    except (ValueError, OSError, KeyError, IndexError, TypeError, subprocess.CalledProcessError) as error:
        detail = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
        parser.exit(2, f"clip-first-episode-video: {detail}\n")


if __name__ == "__main__":
    main()
