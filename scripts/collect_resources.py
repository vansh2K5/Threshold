"""Sample Docker CPU and memory for an explicitly named experiment run."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_bytes(value: str) -> int | None:
    match = re.fullmatch(r"\s*([\d.]+)\s*([KMGT]?i?B)?\s*", value, re.IGNORECASE)
    if not match:
        return None
    amount = float(match.group(1))
    unit = (match.group(2) or "B").upper()
    scale = {"B": 1, "KB": 1000, "KIB": 1024, "MB": 1000**2, "MIB": 1024**2,
             "GB": 1000**3, "GIB": 1024**3, "TB": 1000**4, "TIB": 1024**4}.get(unit)
    return int(amount * scale) if scale else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--duration-seconds", type=int, default=3600)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--stop-file", type=Path, default=None)
    args = parser.parse_args()
    out = args.results_dir / "batches" / args.batch_id / "resources.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    columns = ["run_id", "timestamp", "container", "cpu_percent", "memory_usage_bytes",
               "memory_limit_bytes", "memory_percent", "sample_error"]
    new_file = not out.exists()
    with out.open("a", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        if new_file:
            writer.writeheader()
        deadline = time.monotonic() + args.duration_seconds
        while time.monotonic() < deadline and not (args.stop_file and args.stop_file.exists()):
            started = time.monotonic()
            try:
                output = subprocess.check_output(
                    ["docker", "stats", "--no-stream", "--format", "{{json .}}"],
                    text=True,
                    stderr=subprocess.STDOUT,
                )
                for line in output.splitlines():
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    mem = str(item.get("MemUsage", ""))
                    used, _, limit = mem.partition("/")
                    used_bytes, limit_bytes = parse_bytes(used), parse_bytes(limit)
                    writer.writerow({
                        "run_id": args.run_id,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "container": item.get("Name") or item.get("Container"),
                        "cpu_percent": str(item.get("CPUPerc", "")).rstrip("%"),
                        "memory_usage_bytes": used_bytes,
                        "memory_limit_bytes": limit_bytes,
                        "memory_percent": str(item.get("MemPerc", "")).rstrip("%"),
                        "sample_error": "",
                    })
            except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
                writer.writerow({
                    "run_id": args.run_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "container": "",
                    "cpu_percent": "",
                    "memory_usage_bytes": "",
                    "memory_limit_bytes": "",
                    "memory_percent": "",
                    "sample_error": f"{type(exc).__name__}: {exc}",
                })
            stream.flush()
            time.sleep(max(0.0, args.interval_seconds - (time.monotonic() - started)))
    print(f"Appended Docker resource samples to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
