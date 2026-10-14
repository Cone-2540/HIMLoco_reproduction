#!/usr/bin/env python3
"""Decode entire actual-physics recordings and make uniformly sampled sheets.

Sheets are review aids, not evidence of a new rollout or automatic visual
approval. Failed recordings remain in the manifest and are not filtered out.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import imageio.v2 as imageio
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error("Require a finite positive sampling interval")
    source = json.loads(args.manifest.read_text())
    output = args.manifest.parent / "review"
    output.mkdir(exist_ok=False)
    sources = [("isaac-" + row["terrain"], Path(video), None)
               for row in source["isaac"] for video in row["videos"]]
    sources += [("mujoco-" + row["terrain"] + "-side" + str(row["azimuth"]),
                 Path(row["video"]), row["success"]) for row in source["mujoco"]]
    report = {"source_manifest": str(args.manifest.resolve()),
              "source_manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
              "policy_sha256": source["policy_sha256"], "videos": [],
              "scope": "Complete video decoding; uniformly sampled physical-rollout frames. No failure exclusion or visual approval."}
    for label, path, success in sources:
        reader = imageio.get_reader(path)
        fps = float(reader.get_meta_data()["fps"])
        stride = max(1, round(fps * args.interval))
        retained = []
        count = 0
        try:
            for index, frame in enumerate(reader):
                count += 1
                if index % stride == 0:
                    retained.append((index, Image.fromarray(frame).resize((320, 180))))
        finally:
            reader.close()
        if not retained:
            raise RuntimeError(f"Empty video: {path}")
        sheet = Image.new("RGB", (5 * 320, 48 + math.ceil(len(retained) / 5) * 204), "#eeeeee")
        draw = ImageDraw.Draw(sheet)
        draw.text((8, 8), f"{label} | actual physics | full decode {count} frames at {fps:g} fps", fill="black")
        draw.text((8, 25), "Uniform sampling across entire video; original recording preserved", fill="black")
        for tile, (index, frame) in enumerate(retained):
            x, y = (tile % 5) * 320, 48 + (tile // 5) * 204
            sheet.paste(frame, (x, y))
            draw.text((x + 6, y + 183), f"t={index / fps:.2f}s | frame {index}", fill="black")
        sheet_path = output / (label + ".jpg")
        sheet.save(sheet_path, quality=95)
        report["videos"].append({"label": label, "source": str(path),
                                 "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                 "sheet": str(sheet_path), "decoded_frames": count, "fps": fps,
                                 "duration_s": count / fps, "success_if_available": success,
                                 "sampled_frame_indices": [i for i, _ in retained]})
    path = output / "decode-report.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(path)


if __name__ == "__main__":
    main()
