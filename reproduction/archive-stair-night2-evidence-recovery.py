#!/usr/bin/env python3
"""CPU-only adapter for the explicitly recovered Round3 development metadata.

The recovered directory contains summaries/completion but no launch manifest.
Read the original GPU directory's unchanged immutable manifest in its place;
also archive that original directory's metadata, including the failure record.
No missing manifest is fabricated/copied into the recovery directory. Existing
tracked archive source and simulator/global tracked worktree remain unchanged.

All other options pass through to archive-stair-night2-evidence.py.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--round3-original-development-directory", type=Path, required=True)
    parser.add_argument("--round3-development-directory", type=Path, required=True)
    parser.add_argument("--defer-file", type=Path, action="append", default=[])
    adapter_args, forwarded = parser.parse_known_args()
    original = adapter_args.round3_original_development_directory.expanduser().absolute()
    recovered = adapter_args.round3_development_directory.expanduser().absolute()
    deferred = {p.expanduser().absolute() for p in adapter_args.defer_file}
    original_manifest = original / "immutable-manifest.json"
    if not original_manifest.is_file():
        parser.error("Explicit original immutable launch manifest is missing")
    here = Path(__file__).resolve().parent
    source = here / "archive-stair-night2-evidence.py"
    spec = importlib.util.spec_from_file_location("night2_evidence_archive", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    absent_recovery_manifest = recovered / "immutable-manifest.json"
    original_add = module.Collector.add
    original_metadata = module.Collector.metadata
    original_comparison = module.Collector.comparison
    original_plan = module.Collector.plan
    def mapped_path(path):
        path = Path(path).expanduser().absolute()
        return original_manifest if path == absent_recovery_manifest else path
    def add(self, path, role, required=True):
        if Path(path).expanduser().absolute() in deferred:
            return
        return original_add(self, mapped_path(path), role, required)
    def metadata(self, path, role):
        if Path(path).expanduser().absolute() in deferred:
            return {}
        return original_metadata(self, mapped_path(path), role)
    def comparison(self, directory, role):
        if Path(directory).absolute() != recovered:
            return original_comparison(self, directory, role)
        completion = self.metadata(recovered / "comparison-completion.json", role + ":CPU-recovery-completion")
        module.require(completion.get("status") == "development_collection_and_separate_cpu_summaries_recovered_without_new_gpu", "Explicit recovered development status required")
        records = completion.get("records", [])
        module.require(len(records) == 2 and {r["speed_m_s"] for r in records} == {0.3, 0.5}, "Both saved development speed jobs required")
        module.require(module.sha256(original_manifest) == completion["original_immutable_manifest_sha256"], "Original immutable launch manifest differs from recovery provenance")
        for record in records:
            launch = Path(record["wrapper_directory"]) / "launch-record.json"
            value = json.loads(launch.read_text())
            module.require(value.get("status") == "exited" and value.get("exit_code") == 0, "Recovered summaries require actual saved GPU job exits0")
            module.require(module.sha256(launch) == record["launch_record_sha256"], "Recovered GPU launch record SHA differs")
        self.metadata(original_manifest, role + ":original-immutable-manifest")
        for path in sorted(recovered.iterdir()):
            if path.is_file() and path.suffix in module.METADATA_EXTENSIONS:
                self.add(path, role + ":recovered-summary-metadata")
        module.require(len(completion.get("policies", [])) == 2, "Two explicit recovered policy identities required")
        for policy in completion["policies"]:
            sidecar = self.metadata(recovered / Path(policy["training_identity"]).name, role + ":identity")
            identity = sidecar["identity"]
            self.required_checkpoints[identity["checkpoint"]] = identity["checkpoint_sha256"]
            results = sidecar["source_result_paths"]
            for result in results:
                self.add(result, role + ":raw-result")
            self.rebuild_commands.append({"scope": role, "label": identity["label"], "argv_relative_to_extract_root": [
                "python3", "repo/reproduction/summarize-stair-night2.py", *[module.member_for(Path(x)) for x in results],
                "--stage", "development", "--plan", "repo/reproduction/stair-night2-round3-evaluation-proposal.json",
                "--output", f"rebuilt/{role}/{identity['label']}"]})
    def plan(self, args):
        value = original_plan(self, args)
        value["round3_development_cpu_recovery"] = {
            "recovered_directory": str(recovered), "original_gpu_directory": str(original),
            "original_immutable_manifest": str(original_manifest),
            "preserved_status": "development_collection_and_separate_cpu_summaries_recovered_without_new_gpu",
            "both_original_gpu_wrapper_exit0_and_launch_hashes_verified": True,
            "no_missing_manifest_fabricated_or_original_status_changed": True,
        }
        value["rebuild_git_history_requirement"] = (
            "Clone Cone-2540/HIMLoco_reproduction with full Git history into the extraction root's repo/ first, "
            "checkout the final night2 branch/commit, then extract this archive in the parent directory. "
            "Restore the required_checkpoint_models_not_embedded at their repo-relative paths. "
            "The summarizer uses git ls-tree to verify that different documentary commits have identical runtime trees; "
            "an extracted directory containing only scripts and model weights is insufficient for mixed-commit comparisons."
        )
        value["deferred_small_review_files_not_in_this_frozen_raw_package"] = sorted(str(p) for p in deferred)
        value["deferred_small_review_file_handling"] = (
            "Root explicitly froze completed GPU/raw/material evidence. Final newly written visual notes and long100 summary "
            "are excluded and may be published in a separate verified small supplement after completion; no active notes read or frozen."
        )
        return value
    module.Collector.add = add
    module.Collector.metadata = metadata
    module.Collector.comparison = comparison
    module.Collector.plan = plan
    sys.argv = [str(source), *forwarded,
                "--round3-development-directory", str(recovered),
                "--extra-directory", str(original),
                "--extra-file", str(Path(__file__).resolve())]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
