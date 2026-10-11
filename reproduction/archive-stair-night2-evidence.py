#!/usr/bin/env python3
"""CPU-only, explicit Night2 evidence archive. Default: plan, never pack.

Prepare current round1/2/old-final provenance without reading round3:
  nice -n 10 python3 -B reproduction/archive-stair-night2-evidence.py \
      --manifest reproduction/stair-night2-evaluation-archive-plan.json

Only after the root task supplies completed round3 paths:
  nice -n 10 python3 -B reproduction/archive-stair-night2-evidence.py \
      --round3-development-directory /explicit/completed/dev \
      --round3-final-directory /explicit/completed/final \
      --round3-video-directory /explicit/completed/video \
      --extra-directory /explicit/additional/video-review \
      --manifest reproduction/stair-night2-evaluation-archive-final-manifest.json \
      --create

Output is external. Models, original full videos and frame contact-sheet pages
are not embedded. Every included file has an absolute source, safe archive
member, byte count and SHA256. Original full videos retain external paths/hash.
No GPU/simulator imports, Docker, installation, source edits or deletion.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ROBOTICS = Path("/home/cone/robotics")
REPRODUCTION = ROOT / "reproduction"
OLD_COMPARISONS = [REPRODUCTION / name for name in (
    "stair-night2-round1-development", "stair-night2-round2-development", "stair-night2-final-validation")]
OLD_VIDEO = ROBOTICS / "logs/20261012-050424-486048_night2-video-review"
DEFAULT_OUTPUT = ROBOTICS / "artifacts/night2-20261012-evaluation-data.tar.gz"
METADATA_EXTENSIONS = {".json", ".csv", ".md", ".txt", ".log"}
SIMULATOR_FILES = ("result.json", "primary-result.json", "config.json", "domain-parameters-initial.json",
                   "domain-parameters-final.json", "physics-diagnostic.json", "stair-manifest.json", "terrain-manifest.json")
WRAPPER_FILES = ("launch-record.json", "stdout.log", "gpu-resource.csv")
DIRECTORY_KEYS = {"run", "source_run", "simulator_directory", "simulator_log_dir", "simulator_log_directory", "wrapper_directory", "wrapper"}
FILE_KEYS = {"wrapper_stdout", "launch_record", "geometry_input", "geometry_file", "evaluation_plan", "selection_file",
             "source_proof_file", "training_manifest", "training_config", "training_result", "summary", "training_identity"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def member_for(path: Path, root: Path = ROOT, robotics: Path = ROBOTICS) -> str:
    path = path.absolute()
    if path.is_relative_to(root):
        member = "repo/" + path.relative_to(root).as_posix()
    elif path.is_relative_to(robotics):
        member = "external/robotics/" + path.relative_to(robotics).as_posix()
    else:
        raise ValueError(f"Source outside explicit evidence roots: {path}")
    pure = PurePosixPath(member)
    require(not pure.is_absolute() and ".." not in pure.parts, "Unsafe archive member")
    return member


def snapshot(path: Path, member: str, roles: set[str]) -> dict:
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and not path.is_symlink(), f"Regular file required; symlink refused: {path}")
    checksum = sha256(path)
    after = path.stat()
    require((before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino), f"Source changed during hashing: {path}")
    return {"source": str(path), "member": member, "bytes": before.st_size, "sha256": checksum,
            "roles": sorted(roles), "source_mtime_ns": before.st_mtime_ns}


class Collector:
    def __init__(self):
        self.files: dict[Path, set[str]] = {}
        self.external_videos: dict[Path, set[str]] = {}
        self.directories_seen: set[Path] = set()
        self.metadata_seen: set[Path] = set()
        self.rebuild_commands: list[dict] = []
        self.required_checkpoints: dict[str, str] = {}
        self.absent_optional: set[str] = set()

    def add(self, path: Path | str, role: str, required: bool = True) -> None:
        path = Path(path).expanduser().absolute()
        member_for(path)  # Check allowed roots before reading.
        if not path.is_file():
            if required:
                raise ValueError(f"Required evidence file missing: {path}")
            self.absent_optional.add(str(path))
            return
        require(not path.is_symlink(), f"Evidence symlink refused: {path}")
        self.files.setdefault(path, set()).add(role)

    def metadata(self, path: Path, role: str) -> dict | list:
        self.add(path, role)
        require(path.stat().st_size <= 32 * 1024 * 1024, f"Large raw JSON must not be parsed as metadata: {path}")
        data = json.loads(path.read_text())
        if path not in self.metadata_seen:
            self.metadata_seen.add(path)
            self.references(data, role)
        return data

    def references(self, value, role: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, str) and item.startswith("/home/cone/"):
                    p = Path(item)
                    if key in DIRECTORY_KEYS and p.is_dir():
                        self.wrapper(p, role) if key in {"wrapper_directory", "wrapper"} else self.simulator(p, role)
                    elif key == "material_directory" and p.is_dir():
                        self.video(p, role + ":referenced-materials")
                    elif key in FILE_KEYS and p.suffix in METADATA_EXTENSIONS:
                        # An interrupted video manifest retains planned inputs
                        # for jobs never reached. Record this absence explicitly;
                        # completed comparison raw results remain mandatory.
                        self.add(p, role, required=key != "geometry_input")
                        if key == "launch_record":
                            self.wrapper(p.parent, role)
                elif key == "source_result_paths" and isinstance(item, list):
                    for raw in item:
                        self.add(raw, role + ":raw-result")
                elif key == "source_videos" and isinstance(item, list):
                    for video in item:
                        if isinstance(video, dict) and "path" in video:
                            source = Path(video["path"])
                            member_for(source)
                            require(source.is_file(), f"Explicit original video missing: {source}")
                            self.external_videos.setdefault(source, set()).add(role)
                self.references(item, role)
        elif isinstance(value, list):
            for item in value:
                self.references(item, role)

    def wrapper(self, directory: Path, role: str) -> None:
        for filename in WRAPPER_FILES:
            self.add(directory / filename, role + ":wrapper", required=filename != "gpu-resource.csv")

    def simulator(self, directory: Path, role: str) -> None:
        member_for(directory)
        for filename in SIMULATOR_FILES:
            self.add(directory / filename, role + ":simulator", required=filename in {"result.json", "config.json"})
        videos = directory / "videos"
        if videos.is_dir():
            for source in sorted(videos.iterdir()):
                if source.is_file() and source.suffix == ".mp4":
                    self.external_videos.setdefault(source, set()).add(role + ":original-full-video")

    def comparison(self, directory: Path, role: str) -> None:
        require(directory.is_dir(), f"Explicit comparison directory missing: {directory}")
        completion = self.metadata(directory / "comparison-completion.json", role + ":completion")
        require(isinstance(completion, dict) and completion.get("records"), "Completed comparison records required")
        require("completed" in completion.get("status", ""), "Only completed comparison evidence may enter the final archive")
        self.add(directory / "immutable-manifest.json", role + ":immutable-manifest")
        self.metadata(directory / "immutable-manifest.json", role + ":immutable-manifest")
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.suffix in METADATA_EXTENSIONS:
                self.add(path, role + ":summary-metadata")
        for policy in completion.get("policies", []):
            identity_path = directory / Path(policy["training_identity"]).name
            sidecar = self.metadata(identity_path, role + ":identity")
            self.required_checkpoints[sidecar["identity"]["checkpoint"]] = sidecar["identity"]["checkpoint_sha256"]
            results = sidecar["source_result_paths"]
            for result in results:
                self.add(result, role + ":raw-result")
            stage = "development" if "development" in role else "final"
            label = sidecar["identity"]["label"]
            self.rebuild_commands.append({"scope": role, "label": label, "argv_relative_to_extract_root": [
                "python3", "repo/reproduction/summarize-stair-night2.py", *[member_for(Path(x)) for x in results],
                "--stage", stage, "--plan", "repo/reproduction/" + ("stair-night2-round3-evaluation-proposal.json" if role.startswith("round3") else "stair-night2-evaluation-plan.json"),
                "--output", f"rebuilt/{role}/{label}"]})

    def video(self, directory: Path, role: str) -> None:
        member_for(directory)
        require(directory.is_dir(), f"Explicit video directory missing: {directory}")
        require(any(directory.iterdir()), f"Explicit video directory empty: {directory}")
        if directory in self.directories_seen:
            return
        self.directories_seen.add(directory)
        # Descend only within this explicitly named directory. Never import old
        # frame pages, source videos or policy model files through a broad glob.
        for base, dirs, names in os.walk(directory):
            dirs[:] = sorted(d for d in dirs if d not in {"videos", "selected-all-frames", "all-frames", "__pycache__"} and not d.endswith("-all-frames"))
            for name in sorted(names):
                path = Path(base) / name
                if path.suffix in METADATA_EXTENSIONS:
                    self.add(path, role + ":video-metadata")
                    if path.suffix == ".json" and path.stat().st_size <= 32 * 1024 * 1024:
                        self.metadata(path, role + ":video-metadata")
                elif path.suffix == ".mp4" and ("first-episode" in name or "prefailure" in name) and "allframes" not in name:
                    self.add(path, role + ":first-episode-clip")

    def plan(self, args) -> dict:
        supplied = [args.round3_development_directory, args.round3_final_directory, args.round3_video_directory]
        scope_complete = all(path is not None for path in supplied)
        entries = [snapshot(path, member_for(path), roles) for path, roles in sorted(self.files.items(), key=lambda p: member_for(p[0]))]
        video_entries = [snapshot(path, member_for(path), roles) for path, roles in sorted(self.external_videos.items())]
        unique_sizes = {}
        for entry in entries:
            unique_sizes.setdefault(entry["sha256"], entry["bytes"])
        return {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
                "status": "complete_explicit_sources_plan" if scope_complete else "PRELIMINARY_round3_paths_not_all_supplied_no_final_archive",
                "complete_requested_scope": scope_complete,
                "cpu_only": True, "compression": "gzip level1, one streaming process, nice+10 best effort",
                "output_path": str(args.output),
                "source_roots": {"repo": str(ROOT), "external/robotics": str(ROBOTICS)},
                "round3_explicit_directories": {"development": str(args.round3_development_directory) if args.round3_development_directory else None,
                                               "final": str(args.round3_final_directory) if args.round3_final_directory else None,
                                               "video": str(args.round3_video_directory) if args.round3_video_directory else None},
                "included_files": entries, "external_original_full_videos_not_embedded": video_entries,
                "included_file_count": len(entries), "logical_source_bytes": sum(e["bytes"] for e in entries),
                "unique_content_bytes_before_gzip": sum(unique_sizes.values()),
                "identical_content_deduplication": "Tar hardlink to first included content SHA256; every original member mapping remains extractable.",
                "excluded": ["policy models/checkpoints: already separately archived/Git", "all frame contact-sheet pages/images", "original full raw MP4 videos: external source/hash references only"],
                "optional_files_absent": sorted(self.absent_optional),
                "rebuild_commands": self.rebuild_commands,
                "required_checkpoint_models_not_embedded": self.required_checkpoints,
                "rebuild_model_requirement": "Restore matching Git artifacts checkpoint directories under extracted repo/artifacts before summary regeneration: the existing summarizer independently hashes actual model files.",
                "video_claim_limits": "Preserve old MoviePy/NumPy2 repeated/skipped frame evidence and original claims unchanged. Encoding/coverage is not certified by archival hashes.",
                "no_original_sources_deleted_or_changed": True}


def populate(args) -> Collector:
    collector = Collector()
    for directory in OLD_COMPARISONS:
        role = "round1-development" if "round1" in directory.name else "round2-development" if "round2" in directory.name else "old-final"
        collector.comparison(directory, role)
    collector.video(OLD_VIDEO, "old-video-review")
    for filename in ("stair-night2-video-interruption-and-recovery.json", "stair-night2-selected-flat-regression.json"):
        collector.metadata(REPRODUCTION / filename, "old-review-flat")
    for filename in ("summarize-stair-night2.py", "summarize-stair-night2-selected-flat.py", "summarize-stair-night2-round3-flat.py",
                     "stair-night2-evaluation-plan.json", "stair-night2-development-geometries.json", "stair-night2-final-geometries.json",
                     "stair-night2-selected-final-freeze.json", "stair-night2-motion-review-last-seven.json", "stair-night2-motion-review-last-seven_zh.md",
                     "stair-night2-selected-flat-regression.csv", "stair-night2-selected-flat-regression.md"):
        collector.add(REPRODUCTION / filename, "rebuild-and-small-review")
    for directory, role in ((args.round3_development_directory, "round3-development"), (args.round3_final_directory, "round3-final")):
        if directory is not None:
            collector.comparison(directory, role)
    if args.round3_video_directory is not None:
        collector.video(args.round3_video_directory, "round3-video-review")
    for directory in args.extra_directory:
        collector.video(directory, "explicit-extra-review")
    for filename in ("stair-night2-round3-evaluation-proposal.json", "stair-night2-round3-reserved-geometries.json"):
        if args.round3_development_directory is not None or args.round3_final_directory is not None:
            collector.add(REPRODUCTION / filename, "round3-rebuild")
    for path in args.extra_file:
        collector.add(path, "explicit-extra-file")
    return collector


class HashingReader:
    def __init__(self, handle):
        self.handle = handle
        self.h = hashlib.sha256()
    def read(self, size=-1):
        data = self.handle.read(size)
        self.h.update(data)
        return data


def tar_info(member: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(member)
    info.size, info.mode, info.mtime = size, 0o644, 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def write_archive(manifest: dict, output: Path) -> dict:
    require(manifest["complete_requested_scope"], "Final archive forbidden until root supplies all three round3 directories")
    require(not output.exists(), "Existing final archive is never overwritten")
    temporary = Path(str(output) + ".partial")
    require(not temporary.exists(), "Existing partial is preserved; choose a new output path")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()
    readme = ("Night2 evaluation evidence\n\nExtract into a NEW directory with tar -xzf.\n"
              "repo/ members preserve repository-relative paths; external/robotics/ preserves external relative paths.\n"
              "ARCHIVE_MANIFEST.json records original absolute paths, member mappings, all sizes/hashes and explicit rebuild argv.\n"
              "Run rebuild argv from this extraction root; create the named rebuilt output directories first.\n"
              "Source JSON keeps original paths; explicit argv inputs avoid requiring original absolute result locations.\n"
              "Restore matching Git artifacts checkpoint directories under repo/artifacts BEFORE rebuilding summaries.\n"
              "The manifest lists expected model hashes; existing summarizers require actual checkpoints for identity verification.\n"
              "Full original videos are external referenced only; first-episode/prefailure clips are embedded when present.\n"
              "No frame contact-sheet pages or weights are embedded. A hash archive is not evidence of video physics synchronization.\n"
              "Old MoviePy/NumPy2 video omissions/repetitions remain disclosed; original reports/results are unchanged.\n").encode()
    linked = {}
    with temporary.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=1, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as archive:
                for member, data in (("ARCHIVE_MANIFEST.json", manifest_bytes), ("ARCHIVE_README.txt", readme)):
                    archive.addfile(tar_info(member, len(data)), io.BytesIO(data))
                for entry in manifest["included_files"]:
                    path = Path(entry["source"])
                    require(path.stat().st_size == entry["bytes"] and path.stat().st_mtime_ns == entry["source_mtime_ns"], f"Source changed since frozen manifest: {path}")
                    info = tar_info(entry["member"], entry["bytes"])
                    if entry["sha256"] in linked:
                        require(sha256(path) == entry["sha256"], f"Deduplicated source SHA changed: {path}")
                        info.type, info.linkname, info.size = tarfile.LNKTYPE, linked[entry["sha256"]], 0
                        archive.addfile(info)
                    else:
                        with path.open("rb") as handle:
                            reader = HashingReader(handle)
                            archive.addfile(info, reader)
                            require(reader.h.hexdigest() == entry["sha256"], f"Source SHA changed during packing: {path}")
                        linked[entry["sha256"]] = entry["member"]
    # No rename onto existing destination: preserve both prior archives and a
    # failed partial. Hardlink creation publishes the complete bytes atomically.
    os.link(temporary, output)
    # Deliberately keep the .partial hardlink as a recoverable completed staging
    # file; no deletion is performed. This consumes no second data allocation.
    return {"path": str(output), "bytes": output.stat().st_size, "sha256": sha256(output),
            "completed_staging_hardlink_preserved": str(temporary), "embedded_file_count": len(manifest["included_files"]),
            "manifest_embedded_sha256": hashlib.sha256(manifest_bytes).hexdigest()}


def verify_archive(path: Path) -> dict:
    hashed = {}
    expected = None
    with tarfile.open(path, mode="r|gz") as archive:
        for item in archive:
            pure = PurePosixPath(item.name)
            require(not pure.is_absolute() and ".." not in pure.parts, "Unsafe archived path")
            if item.name == "ARCHIVE_MANIFEST.json":
                expected = json.load(archive.extractfile(item))
                continue
            if item.name == "ARCHIVE_README.txt":
                continue
            if item.islnk():
                require(item.linkname in hashed, "Hardlink target missing or not previously verified")
                hashed[item.name] = hashed[item.linkname]
            else:
                require(item.isfile(), "Unexpected non-file archive member")
                handle = archive.extractfile(item)
                h, size = hashlib.sha256(), 0
                for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                    h.update(block)
                    size += len(block)
                hashed[item.name] = (h.hexdigest(), size)
    require(expected is not None, "Embedded manifest missing")
    entries = expected["included_files"]
    require(set(hashed) == {e["member"] for e in entries}, "Manifest/member set differs")
    for entry in entries:
        require(hashed[entry["member"]] == (entry["sha256"], entry["bytes"]), f"Archived content differs: {entry['member']}")
    return {"verified": True, "verified_member_count": len(entries), "scope": "Streaming decompression and SHA/size of every stored or hardlinked evidence member; no extraction or GPU."}


class ArchiveChecks(unittest.TestCase):
    def test_mapping_safety_and_no_final_without_round3(self):
        self.assertEqual(member_for(ROOT / "reproduction/x.json"), "repo/reproduction/x.json")
        with self.assertRaises(ValueError): member_for(Path("/etc/passwd"))
        with tempfile.TemporaryDirectory(prefix="himloco-night2-archive-fixture-") as tmp:
            out = Path(tmp) / "fixture.tar.gz"
            with self.assertRaises(ValueError): write_archive({"complete_requested_scope": False}, out)
            self.assertFalse(out.exists())

    def test_complete_fixture_archive_hash_mapping_dedup_and_change_guard(self):
        with tempfile.TemporaryDirectory(prefix="himloco-night2-archive-fixture-") as tmp:
            base = Path(tmp)
            a, b = base / "a.json", base / "b.json"
            a.write_text('{"synthetic_only":true}\n')
            b.write_bytes(a.read_bytes())
            entries = [snapshot(a, "repo/synthetic/a.json", {"fixture"}), snapshot(b, "external/robotics/synthetic/b.json", {"fixture"})]
            m = {"complete_requested_scope": True, "included_files": entries, "synthetic_fixture_not_robot_evidence": True}
            output = base / "fixture.tar.gz"
            result = write_archive(m, output)
            self.assertEqual(result["sha256"], sha256(output))
            self.assertTrue(verify_archive(output)["verified"])
            with tarfile.open(output) as archive:
                self.assertTrue(archive.getmember(entries[1]["member"]).islnk())
            with self.assertRaises(ValueError): write_archive(m, output)
            a.write_text("changed")
            with self.assertRaises(ValueError): write_archive(m, base / "changed.tar.gz")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--round3-development-directory", type=Path)
    parser.add_argument("--round3-final-directory", type=Path)
    parser.add_argument("--round3-video-directory", type=Path)
    parser.add_argument("--extra-directory", type=Path, action="append", default=[])
    parser.add_argument("--extra-file", type=Path, action="append", default=[])
    parser.add_argument("--manifest", type=Path, default=REPRODUCTION / "stair-night2-evaluation-archive-plan.json")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--create", action="store_true", help="Final packing only when all round3 directories explicitly supplied; existing archive/manifest never overwritten")
    parser.add_argument("--verify", type=Path, help="CPU verify an existing archive by streaming all member SHA/size; no extraction")
    parser.add_argument("--self-test", action="store_true", help="Synthetic temporary CPU-only archive guards/roundtrip; no real robot artifacts")
    args = parser.parse_args()
    if args.self_test:
        return 0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ArchiveChecks)).wasSuccessful() else 1
    try:
        os.nice(10)
    except OSError:
        pass
    if args.verify:
        print(json.dumps(verify_archive(args.verify)))
        return 0
    require(not args.manifest.exists(), "New manifest path required; previous source index never overwritten")
    if args.create:
        require(all((args.round3_development_directory, args.round3_final_directory, args.round3_video_directory)), "Root-supplied completed round3 dev/final/video paths required before creating final archive")
    manifest = populate(args).plan(args)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("x") as handle:
        handle.write(json.dumps(manifest, indent=2) + "\n")
    response = {"manifest": str(args.manifest), "manifest_sha256": sha256(args.manifest), "status": manifest["status"],
                "files": manifest["included_file_count"], "logical_source_bytes": manifest["logical_source_bytes"],
                "unique_content_bytes_before_gzip": manifest["unique_content_bytes_before_gzip"], "archive_created": False}
    if args.create:
        archive = write_archive(manifest, args.output)
        archive["verification"] = verify_archive(args.output)
        receipt = Path(str(args.manifest) + ".receipt.json")
        with receipt.open("x") as handle:
            handle.write(json.dumps({"source_manifest": str(args.manifest), "source_manifest_sha256": sha256(args.manifest), "archive": archive}, indent=2) + "\n")
        response.update(archive_created=True, archive=archive, receipt=str(receipt))
    print(json.dumps(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
