#!/usr/bin/env python3
"""Create CPU-only locator figures for the three incomplete failure clips.

Eight frames locate phases; these summaries are not a complete visual review.
The complete frame sheets and independent review remain separate evidence.
"""
import hashlib
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont


BASE = Path(__file__).resolve().parent
PICKS = {
    "long12-desc": [0, 105, 179, 299, 399, 469, 514, 535],
    "stretch-desc": [0, 119, 149, 169, 189, 204, 214, 220],
    "highfriction-lip-asc": [0, 119, 149, 179, 219, 259, 309, 354],
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    for name, picks in PICKS.items():
        stem = "frozen-failure-" + name + "-prefailure"
        clip = BASE / (stem + ".mp4")
        meta = json.loads(clip.with_suffix(".json").read_text())
        assert digest(clip) == meta["output_video_sha256"]
        cap = cv2.VideoCapture(str(clip), cv2.CAP_FFMPEG)
        assert cap.isOpened()
        selected = {}
        count = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if count in picks:
                selected[count] = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            count += 1
        cap.release()
        assert count == meta["retained_frame_count"] and sorted(selected) == picks
        canvas = Image.new("RGB", (1920, 664), (24, 24, 24))
        draw = ImageDraw.Draw(canvas)
        flags = ", ".join(key for key, value in meta["failure_flags"].items() if value)
        draw.text((12, 8), f"{stem} | env {meta['environment_id']}, seed {meta['seed']} | source outcome: {flags}", fill="white", font=font)
        draw.text((12, 36), "Locator frames only; final 40 ms excluded. No exact terminal state or continuous playback certification.", fill="white", font=small)
        for index, frame_id in enumerate(picks):
            x = (index % 4) * 480
            y = 64 + (index // 4) * 300
            thumb = selected[frame_id].crop((360, 300, 1000, 660)).resize((480, 270), Image.LANCZOS)
            canvas.paste(thumb, (x, y))
            draw.text((x + 8, y + 274), f"frame {frame_id} | nominal sim {(frame_id + 1) * meta['policy_dt_s']:.2f} s", fill="white", font=small)
        output = BASE / (stem + "-overview.png")
        canvas.save(output)
        doc = {
            "clip": str(clip), "clip_sha256": digest(clip), "overview": str(output),
            "overview_sha256": digest(output), "selected_frame_indices": picks,
            "nominal_simulation_times_s": [(f + 1) * meta["policy_dt_s"] for f in picks],
            "cpu_decode_count": count, "source_episode_completed": False,
            "continuous_video_reviewed": False, "terminal_state_shown": False,
            "scope": "Eight locator frames; does not replace full chronological frame-sequence review.",
        }
        output.with_suffix(".json").write_text(json.dumps(doc, indent=2) + "\n")
        print(str(output))


if __name__ == "__main__":
    main()
