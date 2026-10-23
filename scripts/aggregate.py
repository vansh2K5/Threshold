"""Compute per-target descriptive statistics and paired comparisons."""

from __future__ import annotations

import argparse
import csv
import itertools
import math
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS = [
    "success", "shell_obtained", "shell_verified", "time_to_shell_seconds",
    "total_wall_clock_seconds", "total_compute_seconds", "total_human_approval_wait_seconds",
    "task_completion_score", "subtasks_completed", "subtasks_attempted", "llm_call_count",
    "tool_call_count", "prompt_tokens", "completion_tokens", "total_tokens", "cost_usd",
    "state_disk_usage_bytes",
    "reported_exploit_success", "approval_count", "approval_approved_count",
    "observed_since_first_approval_seconds",
]


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def number(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return 1.0 if value.strip().lower() == "true" else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def sample_sd(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    avg = mean(values)
    return math.sqrt(sum((value - avg) ** 2 for value in values) / (len(values) - 1))


def bootstrap_ci(values: list[float], seed: str, iterations: int = 5000) -> tuple[float | None, float | None]:
    if len(values) < 2:
        return None, None
    rng = random.Random(seed)
    samples = sorted(
        mean([rng.choice(values) for _ in values])
        for _ in range(iterations)
    )
    low = samples[int(0.025 * iterations)]
    high = samples[min(iterations - 1, int(0.975 * iterations))]
    return low, high


def wilcoxon_signed_rank(differences: list[float]) -> tuple[float | None, float | None, str]:
    nonzero = [difference for difference in differences if difference != 0]
    n = len(nonzero)
    if n < 2:
        return None, None, "not_estimable"
    ranked = sorted((abs(value), value) for value in nonzero)
    ranks = [0.0] * n
    ties = []
    index = 0
    while index < n:
        end = index + 1
        while end < n and ranked[end][0] == ranked[index][0]:
            end += 1
        rank = (index + 1 + end) / 2
        for pos in range(index, end):
            ranks[pos] = rank
        if end - index > 1:
            ties.append(end - index)
        index = end
    positive_rank_sum = sum(rank for rank, (_, value) in zip(ranks, ranked) if value > 0)
    expected = n * (n + 1) / 4
    variance = n * (n + 1) * (2 * n + 1) / 24
    variance -= sum(tie * (tie * tie - 1) for tie in ties) / 48
    if n <= 20:
        signed_sums = (
            sum(rank for rank, sign in zip(ranks, signs) if sign)
            for signs in itertools.product((False, True), repeat=n)
        )
        observed_distance = abs(positive_rank_sum - expected)
        extreme = sum(abs(value - expected) >= observed_distance - 1e-12 for value in signed_sums)
        return positive_rank_sum, extreme / (2**n), "exact_two_sided"
    if variance <= 0:
        return positive_rank_sum, None, "normal_approximation"
    z = (abs(positive_rank_sum - expected) - 0.5) / math.sqrt(variance)
    p = math.erfc(max(0.0, z) / math.sqrt(2.0))
    return positive_rank_sum, min(1.0, p), "normal_approximation"


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - position) + ordered[high] * (position - low)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--baseline-condition", action="append", default=[])
    args = parser.parse_args()
    batch_dir = args.results_dir / "batches" / args.batch_id
    runs = read_csv(batch_dir / "runs.csv")
    cost_rows = read_csv(args.results_dir / "tables" / f"{args.batch_id}_run_costs.csv")
    costs = {row.get("run_id"): row.get("cost_usd") for row in cost_rows}
    for run in runs:
        if run.get("run_id") in costs:
            run["cost_usd"] = costs[run.get("run_id")]
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for run in runs:
        groups[(run.get("condition") or "unknown", run.get("target_ip") or run.get("target_name") or "unknown",
                run.get("provider") or "unknown")].append(run)

    summary_rows = []
    for (condition, target, provider), group in sorted(groups.items()):
        for metric in METRICS:
            values = [value for run in group if (value := number(run.get(metric))) is not None]
            low, high = bootstrap_ci(values, f"{args.batch_id}|{condition}|{target}|{provider}|{metric}")
            summary_rows.append(
                {
                    "condition": condition,
                    "target": target,
                    "provider": provider,
                    "metric": metric,
                    "n_observed": len(values),
                    "n_total_runs": len(group),
                    "mean": mean(values),
                    "std_dev": sample_sd(values),
                    "ci95_method": "percentile bootstrap" if len(values) > 1 else "not estimable",
                    "ci95_low": low,
                    "ci95_high": high,
                    "missing_count": len(group) - len(values),
                    "exclusions": "none removed; missing values omitted per metric",
                }
            )
    write_csv(
        args.results_dir / "tables" / f"{args.batch_id}_descriptive_statistics.csv",
        summary_rows,
        ["condition", "target", "provider", "metric", "n_observed", "n_total_runs", "mean", "std_dev",
         "ci95_method", "ci95_low", "ci95_high", "missing_count", "exclusions"],
    )

    compare_rows = []
    if args.baseline_condition:
        by_key = {}
        for run in runs:
            key = (run.get("target_ip") or run.get("target_name"), run.get("repetition"), run.get("provider"), run.get("condition"))
            by_key[key] = run
        targets = sorted({run.get("target_ip") or run.get("target_name") or "unknown" for run in runs})
        providers = sorted({run.get("provider") or "unknown" for run in runs})
        for baseline in args.baseline_condition:
            for target in targets:
                for provider in providers:
                    for metric in METRICS:
                        pairs = []
                        for key, threshold in by_key.items():
                            t_target, repetition, t_provider, condition = key
                            if t_target != target or t_provider != provider or condition != "threshold" or repetition in (None, ""):
                                continue
                            other = by_key.get((t_target, repetition, t_provider, baseline))
                            if other is None:
                                continue
                            t_value, b_value = number(threshold.get(metric)), number(other.get(metric))
                            if t_value is not None and b_value is not None:
                                pairs.append((float(t_value), float(b_value)))
                        differences = [threshold - comparison for threshold, comparison in pairs]
                        avg_diff = mean(differences)
                        sd_diff = sample_sd(differences)
                        d_z = avg_diff / sd_diff if avg_diff is not None and sd_diff else None
                        w, p, wilcoxon_method = wilcoxon_signed_rank(differences)
                        compare_rows.append(
                            {
                                "threshold_condition": "threshold",
                                "baseline_condition": baseline,
                                "target": target,
                                "provider": provider,
                                "metric": metric,
                                "n_pairs": len(pairs),
                                "mean_paired_difference_threshold_minus_baseline": avg_diff,
                                "cohens_dz": d_z,
                                "wilcoxon_W_plus": w,
                                "wilcoxon_p_value": p,
                                "wilcoxon_method": wilcoxon_method,
                                "note": "paired by target, provider, repetition; exact two-sided p for n<=20; missing pair means no estimate",
                            }
                        )
    write_csv(
        args.results_dir / "tables" / f"{args.batch_id}_paired_comparisons.csv",
        compare_rows,
        ["threshold_condition", "baseline_condition", "target", "provider", "metric", "n_pairs",
         "mean_paired_difference_threshold_minus_baseline", "cohens_dz", "wilcoxon_W_plus",
         "wilcoxon_p_value", "wilcoxon_method", "note"],
    )
    provider_calls = read_csv(batch_dir / "provider_calls.csv")
    tool_calls = read_csv(batch_dir / "tool_calls.csv")
    failures = read_csv(batch_dir / "failure_modes.csv")
    provider_keys = sorted(
        {(row.get("provider") or "unknown", row.get("model_name") or "unknown") for row in provider_calls}
        | {(row.get("provider") or "unknown", row.get("model_name") or "unknown") for row in runs}
    )
    provider_rows = []
    for provider, model in provider_keys:
        provider_run_rows = [row for row in runs if (row.get("provider") or "unknown", row.get("model_name") or "unknown") == (provider, model)]
        calls = [row for row in provider_calls if (row.get("provider") or "unknown", row.get("model_name") or "unknown") == (provider, model)]
        latencies = [value for row in calls if (value := number(row.get("latency_seconds"))) is not None]
        structured = [row for row in calls if row.get("operation") == "structured"]
        parsed = [row for row in structured if str(row.get("schema_valid", "")).lower() in {"true", "1"}]
        related_runs = {row.get("run_id") for row in provider_run_rows} | {row.get("run_id") for row in calls}
        tools_for_provider = [row for row in tool_calls if row.get("run_id") in related_runs]
        valid_tools = [row for row in tools_for_provider if
                       str(row.get("allowlist_permitted", "")).lower() in {"true", "1"}
                       and str(row.get("target_in_scope", "")).lower() in {"true", "1"}
                       and not row.get("error_type")
                       and str(row.get("timed_out", "")).lower() not in {"true", "1"}]
        rate_limit_count = sum(
            row.get("failure_mode") == "provider_rate_limit" and row.get("run_id") in related_runs
            for row in failures
        )
        unique_failures = sorted({row.get("failure_mode", "") for row in failures if row.get("run_id") in related_runs})
        run_costs = [value for row in runs if row.get("run_id") in related_runs
                     if (value := number(row.get("cost_usd"))) is not None]
        provider_rows.append({
            "provider": provider,
            "model_name": model,
            "run_count": len(related_runs),
            "llm_call_count": len(calls) if calls else "",
            "latency_mean_seconds": mean(latencies),
            "latency_p50_seconds": percentile(latencies, 0.50),
            "latency_p95_seconds": percentile(latencies, 0.95),
            "structured_calls": len(structured) if calls else "",
            "structured_parse_successes": len(parsed) if calls else "",
            "structured_parse_success_rate": len(parsed) / len(structured) if structured else None,
            "rate_limit_events": rate_limit_count if calls else "",
            "tool_calls_issued": len(tools_for_provider) if calls else "",
            "tool_calls_valid": len(valid_tools) if calls or tools_for_provider else "",
            "tool_call_reliability": len(valid_tools) / len(tools_for_provider) if tools_for_provider else None,
            "mean_cost_usd_per_run": mean(run_costs),
            "unique_failure_modes": ";".join(unique_failures),
        })
    write_csv(
        args.results_dir / "tables" / f"{args.batch_id}_provider_metrics.csv",
        provider_rows,
        ["provider", "model_name", "run_count", "llm_call_count", "latency_mean_seconds",
         "latency_p50_seconds", "latency_p95_seconds", "structured_calls", "structured_parse_successes",
         "structured_parse_success_rate", "rate_limit_events", "tool_calls_issued", "tool_calls_valid",
         "tool_call_reliability", "mean_cost_usd_per_run", "unique_failure_modes"],
    )
    print(f"Wrote descriptive statistics for {len(groups)} condition-target-provider groups")
    if not args.baseline_condition:
        print("No paired tests requested; supply --baseline-condition for each baseline condition.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
