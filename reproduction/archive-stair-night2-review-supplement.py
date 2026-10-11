#!/usr/bin/env python3
"""CPU-only small supplement for explicitly frozen notes after the raw archive."""
import argparse
import importlib.util
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-receipt", type=Path, required=True)
    parser.add_argument("--file", type=Path, action="append", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("night2_raw_archive", here / "archive-stair-night2-evidence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        os.nice(10)
    except OSError:
        pass
    receipt_path = args.base_receipt.expanduser().absolute()
    receipt = json.loads(receipt_path.read_text())
    module.require(receipt["archive"]["verification"]["verified"] is True, "Base raw archive must already be fully verified")
    module.require(not args.manifest.exists(), "Never overwrite an earlier supplement manifest")
    module.require(Path(receipt["archive"]["path"]).stat().st_size == receipt["archive"]["bytes"], "Verified base archive size changed")
    inputs = sorted({p.expanduser().absolute() for p in args.file} | {Path(__file__).resolve()})
    module.require(all(p.suffix in module.METADATA_EXTENSIONS or p.suffix == ".py" for p in inputs), "Only explicit small review/source files allowed")
    module.require(all(p.stat().st_size < 32*1024*1024 for p in inputs), "Large raw data belongs in the base package")
    entries = [module.snapshot(p, module.member_for(p), {"explicit-root-frozen-late-review-supplement"}) for p in inputs]
    manifest = {
        "schema_version": 1,
        "status": "complete_explicit_small_review_supplement_to_verified_raw_package",
        "cpu_only": True,
        "complete_requested_scope": True,
        "base_raw_archive": {"path": receipt["archive"]["path"], "bytes": receipt["archive"]["bytes"], "sha256": receipt["archive"]["sha256"],
                             "verified_members": receipt["archive"]["verification"]["verified_member_count"],
                             "receipt": str(receipt_path), "receipt_sha256": module.sha256(receipt_path),
                             "source_manifest_sha256": receipt["source_manifest_sha256"]},
        "included_files": entries,
        "included_file_count": len(entries),
        "logical_source_bytes": sum(e["bytes"] for e in entries),
        "scope": "Explicit completed late visual notes and CPU summaries only; raw base package and its frozen manifest remain unchanged.",
        "limits": ["SHA/size verification certifies archival consistency only, not smoothness or physical deployment.",
                   "Original GPU exit status and failed/partial evidence remain preserved in the base package."]
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("x") as handle:
        handle.write(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
    archive = module.write_archive(manifest, args.output)
    archive["verification"] = module.verify_archive(args.output)
    response = {"source_manifest": str(args.manifest), "source_manifest_sha256": module.sha256(args.manifest), "archive": archive}
    with Path(str(args.manifest)+".receipt.json").open("x") as handle:
        handle.write(json.dumps(response, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(response, ensure_ascii=False))


if __name__ == "__main__":
    main()
