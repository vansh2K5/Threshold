"""Append structured human review notes and failure adjudication per run."""

from __future__ import annotations

import argparse
import csv
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "run_id", "operator_id", "stage", "annotation_type", "note", "output_trustworthy",
    "deliberation_seconds", "fabricated_findings_count", "fabricated_severity",
    "downstream_propagation", "unsafe_action_count", "unsafe_action_types",
    "evidence_path", "timestamp",
]
SECRET = re.compile(r"(?i)(api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*([^\s,;]+)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--operator-id", required=True)
    parser.add_argument("--stage", required=True, choices=["recon", "exploit", "post_exploit", "analysis", "report"])
    parser.add_argument("--annotation-type", default="operator_note")
    parser.add_argument("--note", required=True)
    parser.add_argument("--output-trustworthy", choices=["yes", "no", "uncertain"], default="uncertain")
    parser.add_argument("--deliberation-seconds", type=float, default=None)
    parser.add_argument("--fabricated-findings-count", type=int, default=0)
    parser.add_argument("--fabricated-severity", default="")
    parser.add_argument("--downstream-propagation", choices=["yes", "no", "unknown"], default="unknown")
    parser.add_argument("--unsafe-action-count", type=int, default=0)
    parser.add_argument("--unsafe-action-types", default="")
    parser.add_argument("--evidence-path", default="")
    args = parser.parse_args()
    out = args.results_dir / "batches" / args.batch_id / "operator_annotations.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    row = {key: getattr(args, key) for key in FIELDS if hasattr(args, key)}
    row["note"] = SECRET.sub(r"\1=[REDACTED]", row["note"])
    row["timestamp"] = datetime.now(UTC).isoformat()
    new_file = not out.exists()
    with out.open("a", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)
    print(f"Appended operator annotation for {args.run_id} to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

