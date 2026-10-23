"""Create per-target condition plots when matplotlib is installed."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--metric", default="total_wall_clock_seconds")
    args = parser.parse_args()
    batch = args.results_dir / "batches" / args.batch_id
    with (batch / "runs.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    values = [row for row in rows if row.get(args.metric) not in (None, "")]
    if not values:
        print(f"No observed values for {args.metric}; no figure emitted.")
        return 0
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit("matplotlib is needed for figures; add it to the research environment only.") from exc
    targets = sorted({row.get("target_ip") or row.get("target_name") or "unknown" for row in values})
    conditions = sorted({row.get("condition") or "unknown" for row in values})
    fig, axis = plt.subplots(figsize=(max(7, len(targets) * 2.2), 4.5))
    width = 0.8 / max(1, len(conditions))
    for index, condition in enumerate(conditions):
        means = []
        for target in targets:
            group = [row for row in values if (row.get("target_ip") or row.get("target_name") or "unknown") == target and row.get("condition") == condition]
            data = [float(row[args.metric]) for row in group]
            means.append(sum(data) / len(data) if data else 0)
        positions = [i + index * width for i in range(len(targets))]
        axis.bar(positions, means, width=width, label=condition)
    axis.set_xticks([i + width * (len(conditions) - 1) / 2 for i in range(len(targets))], targets, rotation=20, ha="right")
    axis.set_ylabel(args.metric)
    axis.legend()
    fig.tight_layout()
    out = args.results_dir / "tables" / f"{args.batch_id}_{args.metric}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=180)
    plt.close(fig)
    groups, labels = [], []
    for target in targets:
        for condition in conditions:
            data = [float(row[args.metric]) for row in values
                    if (row.get("target_ip") or row.get("target_name") or "unknown") == target
                    and row.get("condition") == condition]
            if data:
                groups.append(data)
                labels.append(f"{target}\n{condition}")
    if groups:
        fig, axis = plt.subplots(figsize=(max(7, len(groups) * 1.2), 4.5))
        axis.boxplot(groups, labels=labels, showmeans=True)
        axis.set_ylabel(args.metric)
        axis.tick_params(axis="x", labelrotation=25)
        fig.tight_layout()
        box_out = args.results_dir / "tables" / f"{args.batch_id}_{args.metric}_boxplot.png"
        fig.savefig(box_out, dpi=180)
        plt.close(fig)
        print(f"Wrote {box_out}")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
