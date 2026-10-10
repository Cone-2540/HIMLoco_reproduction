"""Extract evenly spaced frames without extending past the measured episode.

The output is a visual review aid; completion/smoothness comes from the
associated evaluation and continuous video, not these sparse frames alone.
Uses the host's existing OpenCV/Pillow and never starts a simulator.
"""

import argparse
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    videos = sorted((args.run / "videos").glob("*.mp4"))
    if len(videos) != 1:
        parser.error("Require exactly one video; choose a single-scene policy-only run")
    config = json.loads((args.run / "config.json").read_text())
    result = json.loads((args.run / "result.json").read_text())
    if not config.get("video_policy_only") or len(result["policy"]["trials"]) != 1:
        parser.error("Require a policy-only video and exactly one reset seed")
    trial = result["policy"]["trials"][0]
    environment_id = config.get("video_environment_index", 0)
    duration = trial["per_env"]["first_episode_measured_duration_s"][environment_id]
    capture = cv2.VideoCapture(str(videos[0]))
    fps = capture.get(cv2.CAP_PROP_FPS)
    count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if fps <= 0 or count <= 0:
        raise ValueError("Unreadable video metadata")
    end = min(count - 1, max(0, int(duration * fps) - 1))
    ids = [round(end * fraction) for fraction in (0.06, 0.25, 0.44, 0.63, 0.82, 1.0)]
    width, height, label_height = 640, 360, 36
    board = Image.new("RGB", (width * 3, (height + label_height) * 2), "white")
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
    draw = ImageDraw.Draw(board)
    for i, frame_id in enumerate(ids):
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        success, frame = capture.read()
        if not success:
            raise ValueError(f"Could not read video frame {frame_id}")
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((width, height))
        x, y = (i % 3) * width, (i // 3) * (height + label_height)
        board.paste(image, (x, y))
        draw.text((x + 8, y + height + 6), f"frame {frame_id} | {frame_id / fps:.2f} s", fill="black", font=font)
    capture.release()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    board.save(args.output)
    metadata = {
        "run": str(args.run), "checkpoint": config["checkpoint"],
        "video": str(videos[0]), "fps": fps, "recorded_frames": count,
        "first_episode_measured_duration_s": duration, "selected_frame_ids": ids,
        "environment_id": environment_id, "completed": trial["per_env"]["completed"][environment_id],
        "scope": "Sparse visual aid within the measured first episode; does not certify smoothness",
    }
    args.output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata))


if __name__ == "__main__":
    main()
