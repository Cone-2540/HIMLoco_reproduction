#!/usr/bin/env python3
"""CPU-only verification in the existing Isaac Lab Python/container environment.

With the project video overlay active, verify exact RGB cache iteration and
libx264 encode/decode ordering using robust binary frame-ID patches. Does not
import Isaac Lab, start a simulator, or access the GPU.
"""

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from moviepy.config import get_setting


def fingerprint(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def decode_id(frame):
    return sum((int(frame[4:20, bit*8+2:bit*8+6].mean()) > 127) << bit for bit in range(11))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not getattr(ImageSequenceClip.iter_frames, "_him_exact_frames_v1", False):
        raise RuntimeError("Exact-video overlay did not activate")
    args.output.mkdir(parents=True, exist_ok=False)
    ffmpeg = get_setting("FFMPEG_BINARY")
    result = {"schema_version": 1, "status": "passed", "scope": "CPU-only integer-cache and libx264 encode/decode frame-ID verification; no renderer, simulator or GPU", "python":sys.version, "numpy":np.__version__, "overlay":fingerprint(importlib.import_module("sitecustomize").__file__), "verifier":fingerprint(__file__), "ffmpeg":fingerprint(ffmpeg), "cases":[]}
    result["moviepy_image_sequence"] = fingerprint(importlib.import_module("moviepy.video.io.ImageSequenceClip").__file__)
    result["moviepy_clip"] = fingerprint(importlib.import_module("moviepy.Clip").__file__)
    for count in (392, 402, 957, 963, 2000):
        frames = []
        for frame_id in range(count):
            frame = np.zeros((24, 96, 3), dtype=np.uint8)
            for bit in range(11):
                frame[:, bit*8:(bit+1)*8] = 255 if frame_id & (1<<bit) else 0
            frames.append(frame)
        clip = ImageSequenceClip(frames, fps=50)
        iterated = [decode_id(frame) for frame in clip.iter_frames(fps=50, logger=None)]
        if iterated != list(range(count)):
            raise AssertionError(f"RGB cache iterator mismatch at N={count}")
        destination = args.output/f"exact-cache-{count}.mp4"
        clip.write_videofile(str(destination), codec="libx264", audio=False, logger=None,
                             threads=2, ffmpeg_params=["-threads", "2"])
        command = [ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-hwaccel","none","-threads","2","-i",str(destination),"-map","0:v:0","-f","rawvideo","-pix_fmt","rgb24","-threads","2","pipe:1"]
        raw = subprocess.run(command,check=True,capture_output=True).stdout
        frame_size = 24*96*3
        if len(raw)%frame_size:
            raise AssertionError("Partial decoded RGB frame")
        decoded = np.frombuffer(raw,dtype=np.uint8).reshape(-1,24,96,3)
        recovered = [decode_id(frame) for frame in decoded]
        if recovered != list(range(count)):
            raise AssertionError(f"Encoded/CPU-decoded frame IDs mismatch at N={count}")
        result["cases"].append({"cache_frames":count,"fps":50,"encoded_decoded_frames":len(decoded),"iterator_each_cache_entry_exactly_once":True,"encoded_decoded_frame_ids_exactly_0_through_n_minus_1":True,"encoded_mp4":fingerprint(destination),"decoded_pixel_stream_sha256":hashlib.sha256(raw).hexdigest(),"frame_id_encoding":"11 binary 8px-wide grayscale bars, mean threshold127 in interior; robust against lossy libx264; 24x96 RGB", "decoded_frame_ids":recovered})
        print(json.dumps({"N":count,"iterator_frames":len(iterated),"decoded_frames":len(decoded),"all_frame_ids_exact":True}),flush=True)
    report = args.output/"verification.json"
    report.write_text(json.dumps(result,indent=2)+"\n")
    print("EXACT_VIDEO_CPU_VERIFICATION " + str(report),flush=True)


if __name__ == "__main__":
    main()
