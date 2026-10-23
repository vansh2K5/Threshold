"""Import only reports under data/reports as a clearly limited evidence set."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "reports"
DEFAULT_BATCH = "2026-10-21_existing_reports"
STAGES = ["recon", "exploit", "post_exploit", "analysis", "report"]

RUN_COLUMNS = [
    "run_id", "timestamp_start", "timestamp_end", "target_name", "target_version", "repetition",
    "target_image_digest", "target_ip", "authorized_scope", "condition", "provider",
    "model_name", "model_version", "operator_id", "repo_commit_hash", "budget_config",
    "target_reset_done", "success", "application_status", "stage_reached", "shell_obtained",
    "shell_verified", "shell_verification_evidence", "time_to_shell_seconds",
    "time_to_shell_excluding_approval_seconds", "total_wall_clock_seconds",
    "total_compute_seconds", "total_human_approval_wait_seconds", "task_completion_score",
    "subtasks_completed", "subtasks_attempted", "llm_call_count", "tool_call_count",
    "approval_count", "approval_approved_count", "reported_exploit_success",
    "reported_severity", "observed_since_first_approval_seconds", "report_path",
    "evidence_quality",
]
STAGE_COLUMNS = [
    "run_id", "stage", "stage_start_ts", "stage_end_ts", "stage_duration_seconds",
    "stage_completed", "stage_subtasks_completed", "stage_subtasks_total", "num_llm_calls",
    "num_tool_calls", "num_tool_calls_failed", "num_replans_triggered", "replan_reasons",
    "approval_decision", "approval_wait_seconds", "approval_notes", "prompt_tokens",
    "completion_tokens", "total_tokens", "output_schema_valid", "honest_absence_triggered",
    "evidence_path",
]
TOOL_COLUMNS = [
    "run_id", "stage", "tool_name", "command_issued", "start_ts", "end_ts", "exit_code",
    "timed_out", "output_size_bytes", "output_truncated", "target_in_scope",
    "allowlist_permitted", "orphan_reaped", "raw_output_path", "evidence_path",
]
PROVIDER_COLUMNS = [
    "run_id", "stage", "provider", "model_name", "model_version", "api_version",
    "operation", "latency_seconds", "prompt_tokens", "completion_tokens", "total_tokens",
    "schema_valid", "success", "rate_limit_event", "cost_usd", "evidence_path",
]
FAILURE_COLUMNS = [
    "run_id", "failure_mode", "count", "stage", "model_name", "tool_name",
    "duration_seconds", "evidence_path", "evidence_type", "notes",
]


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_report(path: Path, batch_dir: Path) -> tuple[dict, list[dict], list[dict]]:
    text = path.read_text(encoding="utf-8")
    target = re.search(r"^\*\*Target:\*\*\s*(.+)$", text, re.MULTILINE)
    scope = re.search(r"^\*\*Authorized scope:\*\*\s*(.+)$", text, re.MULTILINE)
    provider = re.search(r"^\*\*LLM backend:\*\*\s*(.+)$", text, re.MULTILINE)
    generated = re.search(r"^\*\*Generated:\*\*\s*(.+)$", text, re.MULTILINE)
    exploit_text = section(text, "Exploitation")
    post_text = section(text, "Post-Exploitation")
    analysis_text = section(text, "Analysis")
    success_match = re.search(r"(?:\*\*)?Success:?(?:\*\*)?\s*(True|False)", exploit_text, re.IGNORECASE)
    shell_match = re.search(r"(?:\*\*)?Shell obtained:?(?:\*\*)?\s*(True|False)", exploit_text, re.IGNORECASE)
    severity_match = re.search(r"\b(low|medium|high|critical)\s+severity\b", analysis_text, re.IGNORECASE)

    ip = target.group(1).strip() if target else "unknown"
    timestamp_end = generated.group(1).strip() if generated else ""
    parsed_end = None
    try:
        parsed_end = datetime.fromisoformat(timestamp_end.replace("Z", "+00:00"))
    except ValueError:
        pass
    approvals = []
    for stage, decision, at in re.findall(
        r"-\s+\*\*([\w_]+)\*\*\s*[—-]\s*(approved|rejected|revise)\s*\(([^)]+)\)",
        text,
        re.IGNORECASE,
    ):
        approvals.append((stage, decision.lower(), at.strip()))
    first_approval = None
    if approvals:
        try:
            first_approval = datetime.fromisoformat(approvals[0][2].replace("Z", "+00:00"))
        except ValueError:
            pass
    observed_window = (
        (parsed_end - first_approval).total_seconds()
        if parsed_end and first_approval
        else None
    )

    run_id = "report_" + re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem)
    raw_dir = batch_dir / "raw_reports"
    raw_dir.mkdir(parents=True, exist_ok=True)
    copied = raw_dir / path.name
    shutil.copy2(path, copied)
    evidence_path = copied.relative_to(batch_dir).as_posix()
    status = "report_generated_status_unknown"
    run = {
        "run_id": run_id,
        "timestamp_start": "",
        "timestamp_end": timestamp_end,
        "target_name": "unknown_from_report",
        "target_version": "",
        "repetition": "",
        "target_image_digest": "",
        "target_ip": ip,
        "authorized_scope": scope.group(1).strip() if scope else "",
        "condition": "threshold_report_evidence",
        "provider": provider.group(1).strip().lower() if provider else "",
        "model_name": "",
        "model_version": "",
        "operator_id": "",
        "repo_commit_hash": "",
        "budget_config": "",
        "target_reset_done": "",
        "success": "",
        "application_status": status,
        "stage_reached": "report",
        "shell_obtained": shell_match.group(1).lower() == "true" if shell_match else "",
        "shell_verified": False,
        "shell_verification_evidence": "",
        "time_to_shell_seconds": "",
        "time_to_shell_excluding_approval_seconds": "",
        "total_wall_clock_seconds": "",
        "total_compute_seconds": "",
        "total_human_approval_wait_seconds": "",
        "task_completion_score": "",
        "subtasks_completed": "",
        "subtasks_attempted": "",
        "llm_call_count": "",
        "tool_call_count": "",
        "approval_count": len(approvals),
        "approval_approved_count": sum(decision == "approved" for _, decision, _ in approvals),
        "reported_exploit_success": success_match.group(1).lower() == "true" if success_match else "",
        "reported_severity": severity_match.group(1).lower() if severity_match else "",
        "observed_since_first_approval_seconds": observed_window if observed_window is not None else "",
        "report_path": evidence_path,
        "evidence_quality": "report_only_missing_raw_execution_events",
    }

    stage_rows = []
    for stage in STAGES:
        approval = next((d for s, d, _ in reversed(approvals) if s == stage), "")
        header = {
            "recon": "Recon Findings",
            "exploit": "Exploitation",
            "post_exploit": "Post-Exploitation",
            "analysis": "Analysis",
            "report": "Limitations",
        }[stage]
        stage_rows.append(
            {
                "run_id": run_id,
                "stage": stage,
                "stage_start_ts": "",
                "stage_end_ts": "",
                "stage_duration_seconds": "",
                "stage_completed": bool(section(text, header)) if stage != "report" else copied.exists(),
                "stage_subtasks_completed": "",
                "stage_subtasks_total": "",
                "num_llm_calls": "",
                "num_tool_calls": "",
                "num_tool_calls_failed": "",
                "num_replans_triggered": "",
                "replan_reasons": "",
                "approval_decision": approval,
                "approval_wait_seconds": "",
                "approval_notes": "",
                "prompt_tokens": "",
                "completion_tokens": "",
                "total_tokens": "",
                "output_schema_valid": "",
                "honest_absence_triggered": "",
                "evidence_path": evidence_path,
            }
        )

    failure_rows = []
    payload_issue = re.search(
        r"(?:incompatible payload|payload incompatibility|not a compatible payload)",
        text,
        re.IGNORECASE,
    )
    if payload_issue:
        failure_rows.append(
            {
                "run_id": run_id,
                "failure_mode": "tool_configuration_mismatch",
                "count": 1,
                "stage": "exploit",
                "model_name": "",
                "tool_name": "metasploit_run",
                "duration_seconds": "",
                "evidence_path": evidence_path,
                "evidence_type": "report_narrative_not_raw_tool_log",
                "notes": "Report narrative describes an incompatible payload; command, exit status, and raw output are absent.",
            }
        )
    return run, stage_rows, failure_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", default=DEFAULT_BATCH)
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    files = sorted(REPORTS.glob("*.md"))
    batch_dir = args.results_dir / "batches" / args.batch_id
    if not files:
        print(f"No markdown reports found under {REPORTS}", file=sys.stderr)
        return 2
    runs, stages, failures = [], [], []
    for report in files:
        run, stage_rows, failure_rows = parse_report(report, batch_dir)
        runs.append(run)
        stages.extend(stage_rows)
        failures.extend(failure_rows)

    write_csv(batch_dir / "runs.csv", RUN_COLUMNS, runs)
    write_csv(batch_dir / "stages.csv", STAGE_COLUMNS, stages)
    write_csv(batch_dir / "tool_calls.csv", TOOL_COLUMNS, [])
    write_csv(batch_dir / "provider_calls.csv", PROVIDER_COLUMNS, [])
    write_csv(batch_dir / "failure_modes.csv", FAILURE_COLUMNS, failures)
    (batch_dir / "approval_notes").mkdir(parents=True, exist_ok=True)
    for run in runs:
        approved = run["approval_approved_count"]
        (batch_dir / "approval_notes" / f"{run['run_id']}.md").write_text(
            "# Approval evidence from report\n\n"
            f"Source: [{Path(run['report_path']).name}]({run['report_path']})\n\n"
            f"Approval decisions visible in report: {run['approval_count']} total, {approved} approved.\n\n"
            "Operator identity, deliberation time, decision rationale, and any revise/reject notes were not present in the source report.\n",
            encoding="utf-8",
        )

    counts = Counter(run["provider"] for run in runs)
    target_count = len({run["target_ip"] for run in runs})
    shell_count = sum(run["shell_obtained"] is True for run in runs)
    success_true = sum(run["reported_exploit_success"] is True for run in runs)
    metadata = {
        "batch_id": args.batch_id,
        "evidence_scope": "retrospective extraction from in-project generated Markdown reports only",
        "imported_at": datetime.now(UTC).isoformat(),
        "source_directory": "data/reports",
        "source_report_count": len(files),
        "target_count_observed": target_count,
        "providers_observed": dict(counts),
        "repetitions_per_target_condition_provider": "not established",
        "execution_commit_hash": None,
        "execution_environment": "not preserved with these reports",
        "limitations": [
            "No raw orchestrator logs, tool-call logs, model responses, token use, API version, image digest, or resource metrics were found in the project report directory.",
            "Report generation timestamps do not establish engagement start or full wall-clock duration.",
            "Report success field is the exploit result's reported boolean and is not equivalent to verified compromise or task completion.",
            "Shell verification is not implemented in the current application; all three reports say no shell was obtained.",
            "This batch is not the full experimental matrix and does not establish statistical significance or provider interchangeability.",
        ],
        "current_importer_commit_hash": None,
    }
    try:
        metadata["current_importer_commit_hash"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    (batch_dir / "batch_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

    summary = [
        {"metric": "reports", "value": len(runs), "denominator": len(runs), "interpretation": "in-project report files imported"},
        {"metric": "distinct_target_ips", "value": target_count, "denominator": len(runs), "interpretation": "target identity only; target names/digests absent"},
        {"metric": "provider_openrouter", "value": counts.get("openrouter", 0), "denominator": len(runs), "interpretation": "provider named in reports; model/version absent"},
        {"metric": "shell_obtained_reported", "value": shell_count, "denominator": len(runs), "interpretation": "reports state no shell; no independent shell verification"},
        {"metric": "exploit_success_reported_true", "value": success_true, "denominator": len(runs), "interpretation": "ambiguous report field; not a verified compromise measure"},
        {"metric": "approved_decisions_visible", "value": sum(run["approval_approved_count"] for run in runs), "denominator": sum(run["approval_count"] for run in runs), "interpretation": "approval log entries only; deliberation time and reasons absent"},
        {"metric": "raw_tool_call_records", "value": 0, "denominator": "not observable", "interpretation": "CSV intentionally contains header only; report prose is not a raw invocation log"},
        {"metric": "token_usage_records", "value": 0, "denominator": "not observable", "interpretation": "provider calls are not recoverable from Markdown reports"},
    ]
    observed_windows = [float(run["observed_since_first_approval_seconds"]) for run in runs
                        if run["observed_since_first_approval_seconds"] != ""]
    summary.append({
        "metric": "first_visible_approval_to_report_seconds_mean",
        "value": round(mean(observed_windows), 3) if observed_windows else "",
        "denominator": len(observed_windows),
        "interpretation": "report-window proxy only; excludes time before first recorded approval and is not total wall-clock",
    })
    summary.append({
        "metric": "first_visible_approval_to_report_seconds_sample_sd",
        "value": round(stdev(observed_windows), 3) if len(observed_windows) > 1 else "",
        "denominator": len(observed_windows),
        "interpretation": "descriptive SD across report windows; not a CI or publishable per-condition timing estimate",
    })
    write_csv(args.results_dir / "tables" / "report_import_summary.csv", list(summary[0]), summary)
    print(f"Imported {len(files)} in-project reports into {batch_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
