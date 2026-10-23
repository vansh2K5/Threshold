"""Emit human-readable CSV and LaTeX tables from aggregate outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def escape(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--batch-id", required=True)
    args = parser.parse_args()
    tables = args.results_dir / "tables"
    source = tables / f"{args.batch_id}_descriptive_statistics.csv"
    if not source.exists():
        raise SystemExit(f"Missing aggregate file: {source}; run aggregate.py first.")
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    csv_out = tables / f"{args.batch_id}_paper_summary.csv"
    columns = ["condition", "target", "provider", "metric", "n_observed", "mean", "std_dev", "ci95_low", "ci95_high", "missing_count"]
    with csv_out.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in columns})
    tex_out = tables / f"{args.batch_id}_paper_summary.tex"
    with tex_out.open("w", encoding="utf-8") as stream:
        stream.write("\\begin{tabular}{llllrrrr}\n\\toprule\n")
        stream.write("Condition & Target & Provider & Metric & N & Mean & SD & 95\\% CI \\\\\n\\midrule\n")
        for row in rows:
            ci = ""
            if row.get("ci95_low") and row.get("ci95_high"):
                ci = f"[{row['ci95_low']}, {row['ci95_high']}]"
            cells = [row.get("condition"), row.get("target"), row.get("provider"), row.get("metric"),
                     row.get("n_observed"), row.get("mean"), row.get("std_dev"), ci]
            stream.write(" & ".join(escape(cell) for cell in cells) + r" \\" + "\n")
        stream.write("\\bottomrule\n\\end{tabular}\n")
    print(f"Wrote {csv_out} and {tex_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
