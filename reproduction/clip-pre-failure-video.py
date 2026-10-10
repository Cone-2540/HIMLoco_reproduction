#!/usr/bin/env python3
"""Save explicitly incomplete pre-failure video without ambiguous reset frames.

Reuses only the CPU video/hash/FFmpeg helpers from clip-first-episode-video.py.
It does not relax that helper's completed-episode guard. The terminal rendered
frame and one additional policy frame are excluded; exact terminal physics
therefore cannot be inferred from this diagnostic clip.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("clean_episode_video_helpers",
        Path(__file__).with_name("clip-first-episode-video.py"))
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    run, output = args.run.resolve(), args.output.resolve()
    sidecar = output.with_suffix(".json")
    if output.suffix != ".mp4" or output.exists() or sidecar.exists():
        raise ValueError("Require a new MP4 and new adjacent provenance JSON")
    config = json.loads((run / "config.json").read_text())
    result = json.loads((run / "result.json").read_text())
    if config.get("mode") != "evaluate" or config.get("terrain") != "stairs":
        raise ValueError("Require a recorded staircase evaluation")
    if not config.get("video") or not config.get("video_policy_only"):
        raise ValueError("Require policy-only recording")
    if result.get("zero_action") is not None or result.get("additional_candidates"):
        raise ValueError("Require a single policy phase")
    trials = result["policy"]["trials"]
    if len(trials) != 1:
        raise ValueError("Require one reset seed")
    trial = trials[0]
    env = config["video_environment_index"]
    if isinstance(env, bool) or not isinstance(env, int) or not 0 <= env < trial["num_envs"]:
        raise ValueError("Invalid selected environment")
    outcomes = trial["per_env"]
    flags = {flag: bool(outcomes[flag][env]) for flag in ("fall", "stall", "lateral_escape")}
    if outcomes["completed"][env] or not any(flags.values()):
        raise ValueError("This helper requires an explicitly failed selected first episode")
    duration = float(outcomes["first_episode_measured_duration_s"][env])
    dt = float(config["physics_dt"]) * int(config["policy_decimation"])
    if not math.isfinite(duration) or not math.isfinite(dt) or dt <= 0 or duration <= 2 * dt:
        raise ValueError("Invalid duration or policy dt")
    frames_at_failure = round(duration / dt)
    if not math.isclose(duration / dt, frames_at_failure, abs_tol=1e-3, rel_tol=0):
        raise ValueError("Failure duration does not align with policy steps")
    videos = list((run / "videos").glob("*.mp4"))
    if len(videos) != 1 or output == videos[0].resolve():
        raise ValueError("Require one untouched source video")
    source = videos[0].resolve()
    info = helper.video_info(source, decode=True)
    fps = info["fps"]
    if not math.isclose(fps * dt, 1, abs_tol=1e-5, rel_tol=0):
        raise ValueError("Require one encoded frame per policy step")
    if info["decoded_frame_count"] != min(trial["executed_steps"], config["video_length"]):
        raise ValueError("Recorder source alignment cannot be established")
    retained = frames_at_failure - 2
    if info["decoded_frame_count"] < retained:
        raise ValueError("Recording ends before the prefailure interval")
    for row in trial.get("trace", []):
        if env in row["env_ids"] and row["time_s"] <= retained * dt + dt / 100:
            if not row["active"][row["env_ids"].index(env)]:
                raise ValueError("Inactive/reset interval intersects the diagnostic clip")
    output.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = helper.find_ffmpeg()
    with tempfile.TemporaryDirectory(prefix=".pre-failure-", dir=output.parent) as temp:
        encoded = Path(temp) / "prefailure.mp4"
        command = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-nostdin",
            "-hwaccel", "none", "-threads", "2", "-i", str(source), "-map", "0:v:0",
            "-vf", f"trim=start_frame=0:end_frame={retained},setpts=N/({fps:.12g}*TB)",
            "-frames:v", str(retained), "-r", f"{fps:.12g}", "-fps_mode", "cfr",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-bf", "0",
            "-threads", "2", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(encoded)]
        subprocess.run(command, check=True, capture_output=True, text=True)
        checked = helper.video_info(encoded, decode=True)
        if checked["decoded_frame_count"] != retained or not math.isclose(checked["fps"], fps, abs_tol=1e-5):
            raise ValueError("Encoded diagnostic clip failed complete CPU decode validation")
        doc = {
            "kind": "incomplete_pre_failure_diagnostic",
            "run": str(run), "environment_id": env, "seed": trial["seed"],
            "checkpoint": config["checkpoint"], "selected_environment_completed": False,
            "failure_flags": flags, "measured_first_episode_failure_time_s": duration,
            "source_video": str(source), "output_video": str(output),
            "source_video_sha256": helper.sha256(source), "output_video_sha256": helper.sha256(encoded),
            "config_sha256": helper.sha256(run / "config.json"),
            "result_sha256": helper.sha256(run / "result.json"),
            "source_video_info": info, "output_video_info": checked,
            "policy_dt_s": dt, "retained_frame_count": retained,
            "retained_source_frame_indices_inclusive": [0, retained - 1],
            "nominal_retained_simulation_times_s": [dt, retained * dt],
            "excluded_terminal_duration_s": 2 * dt,
            "terminal_reset_guard": "Exclude the terminal rendered frame and one additional policy frame; this is not the full episode or a view of the exact terminal state.",
            "synchronization_limit": "Encoded PTS + policy dt is nominal simulation time; exact renderer/physics alignment was not separately instrumented.",
            "continuous_video_reviewed": False,
            "encoding": {"hardware_acceleration": "none", "codec": "libx264", "b_frames": 0,
                         "command_with_final_output": command[:-1] + [str(output)]},
        }
        metadata = Path(temp) / "prefailure.json"
        metadata.write_text(json.dumps(doc, indent=2) + "\n")
        encoded.replace(output)
        metadata.replace(sidecar)
    print(json.dumps({"output": str(output), "frames": retained, "failure_flags": flags,
                      "measured_failure_time_s": duration, "terminal_state_shown": False}))


if __name__ == "__main__":
    main()
