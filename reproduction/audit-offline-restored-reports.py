#!/usr/bin/env python3
"""Rebuild and validate reports in a restored tree while denying original reads.

Requires a separately restored Git source tree plus both data archives. This
standard-library helper writes only the restored reports and a new evidence
directory. It never launches simulators, trains, installs packages or uses Git.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


PREFIXES = (
    "stair-frozen-final-validation", "stair-policy-frozen-flat-regression",
    "stair-frozen-heading-dependence", "stair-frozen-material-speed05",
    "stair-frozen-speed-probe", "stair-frozen-calf-sensitivity",
    "stair-frozen-height-depth-probe", "stair-frozen-dynamics-speed05",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restore-root", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--original-repo-root", type=Path, required=True)
    parser.add_argument("--original-run-log-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.restore_root.resolve()
    evidence = args.evidence_root.resolve()
    blocked = (str(args.original_repo_root.resolve()),
               str(args.original_run_log_root.resolve()))
    for target in (root, evidence):
        for original in map(Path, blocked):
            if target == original or original in target.parents or target in original.parents:
                raise ValueError("Restore/evidence directories must not overlap original source/data roots")
    if evidence.exists():
        raise ValueError("Require a separate restored tree and a new evidence directory")
    if not (root / "restored-launchlogs/frozen-validation/frozen-evaluation-plan.json").is_file():
        raise ValueError("Both outcome and supplemental archives must be restored first")
    for prefix in PREFIXES:
        for suffix in (".md", ".csv", ".json.gz"):
            if (root / "reproduction" / (prefix + suffix)).exists():
                raise ValueError("Remove generated copies from the new clean tree before auditing")
    evidence.mkdir(parents=True)
    guard = evidence / "guard"
    guard.mkdir()
    guard_code = '''import os, sys
if os.environ.get("HIMLOCO_OFFLINE_RESTORE_GUARD") != "enabled":
    raise RuntimeError("Offline restore guard must be enabled")
_BLOCKED = BLOCKED_VALUE
def _guard(event, args):
    if event in ("open", "os.listdir", "os.scandir") and args:
        value = args[0]
        if isinstance(value, (str, bytes, os.PathLike)):
            path = os.path.realpath(os.fsdecode(value))
            if any(path == root or path.startswith(root + os.sep) for root in _BLOCKED):
                raise PermissionError("Offline restore prohibits reading original source/data: " + path)
    if event == "import" and args and isinstance(args[0], str):
        name = args[0].split(".")[0]
        if name in ("torch", "numpy", "isaacgym", "isaaclab", "omni"):
            raise RuntimeError("CPU-only report rebuild prohibits simulator/GPU import: " + args[0])
sys.addaudithook(_guard)
'''.replace("BLOCKED_VALUE", repr(blocked))
    guard_path = guard / "sitecustomize.py"
    guard_path.write_text(guard_code)
    env = dict(os.environ)
    env.update(PYTHONPATH=str(guard), PYTHONDONTWRITEBYTECODE="1",
               HIMLOCO_OFFLINE_RESTORE_GUARD="enabled")
    records = []

    def execute(label, command):
        started = datetime.now().astimezone().isoformat()
        before = time.monotonic()
        process = subprocess.run(command, cwd=root, env=env, text=True,
                                 capture_output=True)
        output = evidence / (label + ".log")
        output.write_text(process.stdout + process.stderr)
        record = {"label": label, "command": command, "cwd": str(root),
                  "started_local": started, "elapsed_seconds": time.monotonic() - before,
                  "exit_code": process.returncode, "stdout_stderr": str(output),
                  "stdout_stderr_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                  "guard_enabled": True}
        try:
            record["summary"] = json.loads(process.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            pass
        print(json.dumps({"label": label, "exit_code": process.returncode,
                          "summary": record.get("summary")}), flush=True)
        return record

    negative_code = '''import json, pathlib, sitecustomize
targets = NEGATIVE_TARGETS
denied = []
for target in targets:
    try:
        pathlib.Path(target).read_bytes()
    except PermissionError:
        denied.append(target)
    else:
        raise RuntimeError("Original read was unexpectedly allowed: " + target)
try:
    __import__("torch")
except RuntimeError as error:
    if "prohibits simulator/GPU import" not in str(error):
        raise
else:
    raise RuntimeError("GPU library import unexpectedly allowed")
print(json.dumps({"original_file_reads_denied": denied, "torch_import_denied": True}))
'''.replace("NEGATIVE_TARGETS", repr([
        str(args.original_repo_root.resolve() / "reproduction/stair-final-evaluation-plan.json"),
        str(args.original_run_log_root.resolve() / "frozen-validation-master.log")]))
    records.append(execute("guard-negative-controls", [sys.executable, "-B", "-c", negative_code]))
    if records[-1]["exit_code"]:
        raise RuntimeError("File/import guard negative controls failed")
    common = ["--repo-root", str(root)]
    launch = ["--run-log-root", str(root / "restored-launchlogs")]
    jobs = [("rebuild-flat", "summarize-frozen-flat-regression.py", [], False),
            ("rebuild-material05", "summarize-frozen-material-speed05.py", [], True)]
    jobs += [("rebuild-" + kind, "summarize-frozen-stair-diagnostics.py",
              ["--kind", kind], True) for kind in ("speed", "calf", "geometry", "dynamics05")]

    def rebuild(job):
        label, script, options, has_launch = job
        return execute(label, [sys.executable, "-B", str(root / "reproduction" / script),
                               *common, *(launch if has_launch else []), *options])

    with ThreadPoolExecutor(max_workers=3) as executor:
        records.extend(executor.map(rebuild, jobs))
    if any(r["exit_code"] for r in records):
        (evidence / "command-results.json").write_text(json.dumps(records, indent=2) + "\n")
        raise RuntimeError("A prerequisite report rebuild failed; see evidence logs")
    records.append(execute("rebuild-main-heading", [sys.executable, "-B",
        str(root / "reproduction/summarize-frozen-stair-validation.py"), *common, *launch]))
    if records[-1]["exit_code"]:
        (evidence / "command-results.json").write_text(json.dumps(records, indent=2) + "\n")
        raise RuntimeError("Main/heading rebuild failed")
    checks = [("validate-original", []), ("validate-material05", ["--supplement"])]
    checks += [("validate-" + kind, ["--diagnostic", kind])
               for kind in ("speed", "calf", "geometry", "dynamics05")]

    def validate(job):
        label, options = job
        return execute(label, [sys.executable, "-B",
            str(root / "reproduction/validate-frozen-stair-validation.py"), *common, *options])

    with ThreadPoolExecutor(max_workers=3) as executor:
        records.extend(executor.map(validate, checks))
    document = {"completed_local": datetime.now().astimezone().isoformat(),
                "status": "complete" if all(r["exit_code"] == 0 for r in records) else "failed",
                "restore_root": str(root), "run_log_root": str(root / "restored-launchlogs"),
                "evidence_root": str(evidence), "guard": str(guard_path),
                "guard_sha256": hashlib.sha256(guard_path.read_bytes()).hexdigest(),
                "blocked_original_roots": list(blocked),
                "guard_scope": "Python file open/listdir/scandir audit denial inherited by motion subprocess; GPU/simulator imports denied. Saved absolute strings may remain as provenance.",
                "commands": records}
    (evidence / "command-results.json").write_text(json.dumps(document, indent=2) + "\n")
    if document["status"] != "complete":
        raise RuntimeError("Restored validation failed; see preserved command evidence")
    print(json.dumps({"status": document["status"], "commands": len(records),
                      "evidence": str(evidence / "command-results.json")}), flush=True)


if __name__ == "__main__":
    main()
