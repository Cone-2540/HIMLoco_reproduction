#!/usr/bin/env python3
"""Preserve local overnight config/result JSON in a verified portable archive.

CPU/filesystem only. Original logs are read, never moved or modified. The
archive is shared outside the checkout; Git stores its manifest, not gigabytes
of simulation data. Incomplete attempts remain part of the archive.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tarfile


def file_hash(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    repo = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=repo)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    target = args.archive.resolve()
    if target.exists():
        raise ValueError("Require a new archive; do not overwrite an existing backup")
    sources = sorted(path for path in (repo/"isaaclab/logs").rglob("*.json")
                     if path.name in ("config.json", "result.json", "primary-result.json")
                     and path.relative_to(repo/"isaaclab/logs").parts[0].startswith("2026-10-11_"))
    if not sources:
        raise ValueError("No overnight JSON outcomes/configuration found")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name+".partial")
    if temporary.exists():
        raise ValueError("Partial archive already exists; inspect it before retrying")
    manifest = []
    with tarfile.open(temporary, "w:gz", compresslevel=1) as archive:
        for number, source in enumerate(sources, 1):
            stat = source.stat()
            digest = file_hash(source)
            name = str(source.relative_to(repo))
            archive.add(source, arcname=name, recursive=False)
            if source.stat().st_size != stat.st_size or source.stat().st_mtime_ns != stat.st_mtime_ns:
                raise ValueError(f"Source changed during archive: {name}")
            manifest.append({"path":name,"bytes":stat.st_size,"sha256":digest})
            if number % 20 == 0:
                print(f"Archived {number}/{len(sources)} source files", flush=True)
    expected = {item["path"]:item for item in manifest}
    verified = set()
    with tarfile.open(temporary, "r|gz") as archive:
        for member in archive:
            if not member.isfile() or member.name not in expected or member.name in verified:
                raise ValueError(f"Unexpected/duplicate archive member: {member.name}")
            value = hashlib.sha256()
            stream = archive.extractfile(member)
            for chunk in iter(lambda: stream.read(4*1024*1024), b""):
                value.update(chunk)
            if member.size != expected[member.name]["bytes"] or value.hexdigest() != expected[member.name]["sha256"]:
                raise ValueError(f"Archive data differs: {member.name}")
            verified.add(member.name)
            if len(verified) % 20 == 0:
                print(f"Verified {len(verified)}/{len(sources)} archive members", flush=True)
    if verified != set(expected):
        raise ValueError("Archive missing source members")
    temporary.rename(target)
    document = {"created_local":datetime.now().astimezone().isoformat(),
                "repo_root_observed":str(repo),"archive":str(target),"archive_bytes":target.stat().st_size,
                "archive_sha256":file_hash(target),"source_count":len(manifest),
                "source_bytes":sum(item["bytes"] for item in manifest),
                "all_archived_members_verified":True,"sources":manifest,
                "scope":"Every available 2026-10-11 HIMLoco simulation config/result/primary-result JSON, including tuning and failed/incomplete collection attempts. Not all directories contain a saved outcome.",
                "excluded":"Simulator binaries, checkpoints, TensorBoard, stdout/Kit logs, video, frame PNG, system configuration and credentials.",
                "restore":"Extract into a separate checkout with tar -xzf ARCHIVE -C CHECKOUT. Relative isaaclab/logs paths are preserved. Existing model/runtime/freeze files are still required for CPU rebuild. Avoid overwriting a checkout that already contains results."}
    output = repo/"reproduction/overnight-evaluation-archive-manifest.json"
    output.write_text(json.dumps(document,indent=2)+"\n")
    print(json.dumps({key:document[key] for key in ("archive","archive_bytes","archive_sha256","source_count","all_archived_members_verified")}),flush=True)


if __name__ == "__main__":
    main()
