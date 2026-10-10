"""Read-only hardware/resource log for an unattended simulation campaign."""

import argparse
import csv
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--hours", type=float, default=7.0)
args = parser.parse_args()
args.output.parent.mkdir(parents=True, exist_ok=True)
end = time.monotonic() + args.hours * 3600
with args.output.open("a", buffering=1) as stream:
    while time.monotonic() < end:
        result = subprocess.run([
            "nvidia-smi", "--query-gpu=memory.used,utilization.gpu,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)
        row = next(csv.reader(result.stdout.splitlines()), [])
        memory = {line.split(":")[0]: int(line.split()[1])
                  for line in Path("/proc/meminfo").read_text().splitlines()
                  if line.startswith(("MemAvailable:", "MemTotal:"))}
        stream.write(json.dumps({"utc": datetime.now(timezone.utc).isoformat(),
                                "gpu_memory_mib_util_percent_temp_c_power_w": row,
                                "host_memory_kib": memory,
                                "query_returncode": result.returncode}) + "\n")
        time.sleep(20)
