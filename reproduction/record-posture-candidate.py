#!/usr/bin/env python3
"""Record a diagnostic candidate in idle Isaac/MuJoCo; never promote a policy."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CPU = Path.home() / "robotics/envs/himloco-mujoco-py311/bin/python"


def assert_idle():
    script = """import os,json
busy=[]
for name in os.listdir('/proc'):
 if not name.isdigit() or int(name)==os.getpid():continue
 try:
  args=open('/proc/'+name+'/cmdline','rb').read().split(b'\\0')
  if any(a.endswith(b'/isaaclab/run.py') for a in args):busy.append(int(name))
 except OSError:pass
print(json.dumps(busy))
"""
    result = subprocess.run(["docker", "exec", "-e", "CUDA_VISIBLE_DEVICES=", "isaaclab-local-lab-1",
                             "/isaac-sim/kit/python/bin/python3", "-c", script],
                            capture_output=True, text=True, check=True, timeout=20)
    if json.loads(result.stdout.strip().splitlines()[-1]):
        raise RuntimeError("Isaac GPU process is live; recording refused")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--tag", required=True)
    p.add_argument("--execute", action="store_true")
    a = p.parse_args()
    if any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in a.tag):
        p.error("Use lowercase recording tag")
    for path in (a.checkpoint, a.policy, a.config):
        if not path.is_file():
            p.error(f"Missing candidate file: {path}")
    folder = Path.home() / "robotics/logs" / ("posture-" + a.tag + "-videos")
    plan = {"checkpoint": str(a.checkpoint.resolve()), "policy": str(a.policy.resolve()),
            "config": str(a.config.resolve()), "output": str(folder),
            "scope": "diagnostic actual-physics recordings; one displayed seed per scene; no automatic selection/promotion"}
    if not a.execute:
        print(json.dumps(plan, indent=2))
        return
    assert_idle()
    folder.mkdir(exist_ok=False)
    manifest_path = folder / "manifest.json"
    manifest = {**plan, "started_local": datetime.now().astimezone().isoformat(),
                "checkpoint_sha256": hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
                "policy_sha256": hashlib.sha256(a.policy.read_bytes()).hexdigest(),
                "isaac": [], "mujoco": []}
    def save():
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    save()
    for terrain in ("flat", "asc", "desc"):
        assert_idle()
        label = "posture-" + a.tag + "-isaac-video-" + terrain
        args = ["evaluate", "--terrain", "flat" if terrain == "flat" else "stairs",
                "--reward_profile", "faithful", "--checkpoint", str(a.checkpoint.resolve()),
                "--num_envs", "8", "--eval_seconds", "25", "--eval_seed", "2000", "--seed", "2000",
                "--eval_trace_stride", "1", "--video", "--video_length", "1250",
                "--video_isolate_env", "--video_env_index", "0", "--video_eye", "0", "2", ".9",
                "--video_lookat", "0", "0", ".25"]
        if terrain == "flat":
            args += ["--warm_start", "reset", "--command", ".3", "0", "0"]
        else:
            args += ["--stair_direction", terrain, "--stair_height", ".16", "--stair_depth", ".27",
                     "--speed", ".3", "--video_policy_only"]
        console = folder / ("isaac-" + terrain + "-console.txt")
        with console.open("x") as stream:
            subprocess.run([sys.executable, "reproduction/run-posture-job.py", "--name", label,
                            "--max-seconds", "900", "--", *args], cwd=ROOT,
                           stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=1000)
        log = [line[9:] for line in console.read_text().splitlines() if line.startswith("JOB_LOG: ")][-1]
        record = json.loads((Path(log) / "launch-record.json").read_text())
        manifest["isaac"].append({"terrain": terrain, "job": record,
                                  "videos": [str(p) for p in Path(record["simulator_log_dir"]).rglob("*.mp4")]})
        save()
    env = dict(os.environ, MUJOCO_GL="egl")
    for terrain, azimuth in (("flat", 90), ("flat", 270), ("asc", 270), ("desc", 270)):
        assert_idle()
        out = folder / f"mujoco-{terrain}-side{azimuth}"
        args = [str(CPU), "sim2sim/run.py", "--policy", str(a.policy.resolve()), "--config", str(a.config.resolve()),
                "--output", str(out), "--terrain", terrain, "--seconds", "25", "--seed", "2000",
                "--initial-joint-noise", ".03", "--record-policy-input", "--record-leg-contacts",
                "--video", "--video-azimuth", str(azimuth), "--video-distance", "1.4",
                "--video-elevation", "-10"]
        if terrain != "flat":
            args += ["--heading-feedback"]
        with (folder / f"mujoco-{terrain}-side{azimuth}-console.txt").open("x") as stream:
            subprocess.run(args, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT,
                           check=True, timeout=300)
        result = json.loads((out / "result.json").read_text())
        manifest["mujoco"].append({"terrain": terrain, "azimuth": azimuth, "video": str(out / "video.mp4"),
                                   "success": result["success"], "reason": result["reason"],
                                   "result": str(out / "result.json"), "policy_sha256": result["policy_sha256"]})
        save()
    manifest["status"] = "recorded_needs_decode_and_visual_review"
    manifest["ended_local"] = datetime.now().astimezone().isoformat()
    save()
    print(manifest_path)


if __name__ == "__main__":
    main()
