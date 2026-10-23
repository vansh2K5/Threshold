"""Calculate run cost only from complete observed tokens and pinned rates."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def as_float(value: object) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--batch-id", required=True)
    args = parser.parse_args()
    batch = args.results_dir / "batches" / args.batch_id
    runs = read_csv(batch / "runs.csv")
    calls = read_csv(batch / "provider_calls.csv")
    rates = read_csv(args.results_dir / "provider_pricing.csv")
    by_run: dict[str, list[dict]] = {}
    for call in calls:
        by_run.setdefault(call.get("run_id", ""), []).append(call)
    output = []
    for run in runs:
        run_id = run.get("run_id", "")
        run_calls = by_run.get(run_id, [])
        cost = 0.0
        expected_calls = run.get("llm_call_count")
        complete = bool(run_calls) or expected_calls == "0" or expected_calls == 0
        sources = set()
        for call in run_calls:
            call_model = call.get("model_name") or run.get("model_name")
            prompt_tokens = as_float(call.get("prompt_tokens"))
            completion_tokens = as_float(call.get("completion_tokens"))
            if prompt_tokens is None or completion_tokens is None:
                complete = False
                continue
            run_day = (run.get("timestamp_start") or "")[:10]
            matching = []
            for rate in rates:
                if rate.get("provider") != call.get("provider") or rate.get("model_name") != call_model:
                    continue
                valid_from = rate.get("valid_from") or ""
                if run_day and valid_from and valid_from > run_day:
                    continue
                if as_float(rate.get("prompt_usd_per_million_tokens")) is None or as_float(rate.get("completion_usd_per_million_tokens")) is None:
                    continue
                matching.append(rate)
            if not matching:
                complete = False
                continue
            rate = sorted(matching, key=lambda item: item.get("valid_from") or "")[-1]
            cost += prompt_tokens * float(rate["prompt_usd_per_million_tokens"]) / 1_000_000
            cost += completion_tokens * float(rate["completion_usd_per_million_tokens"]) / 1_000_000
            sources.add(rate.get("source_url", ""))
        output.append({
            "run_id": run_id,
            "provider": run.get("provider"),
            "model_name": run.get("model_name"),
            "llm_call_count": len(run_calls),
            "cost_usd": round(cost, 8) if complete else "",
            "status": "priced_complete" if complete else "incomplete_tokens_or_missing_pinned_rate",
            "pricing_sources": ";".join(sorted(filter(None, sources))),
        })
    path = args.results_dir / "tables" / f"{args.batch_id}_run_costs.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        fields = ["run_id", "provider", "model_name", "llm_call_count", "cost_usd", "status", "pricing_sources"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)
    print(f"Wrote per-run cost estimates to {path}; no live prices were fetched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
