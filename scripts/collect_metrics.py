"""Convert application JSONL telemetry into run/stage/tool/provider CSVs."""

from __future__ import annotations

import argparse
import csv
import ipaddress
import json
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUN_FIELDS = [
    "run_id", "timestamp_start", "timestamp_end", "target_name", "target_version", "repetition",
    "target_image_digest", "target_ip", "authorized_scope", "target_difficulty_tier", "condition", "provider",
    "model_name", "model_version", "provider_api_version", "operator_id", "repo_commit_hash", "worktree_diff_sha256", "budget_config",
    "target_reset_done", "success", "application_status", "stage_reached", "shell_obtained",
    "shell_verified", "shell_verification_evidence", "time_to_shell_seconds",
    "time_to_shell_excluding_approval_seconds", "total_wall_clock_seconds", "total_compute_seconds",
    "total_human_approval_wait_seconds", "task_completion_score", "subtasks_completed",
    "subtasks_attempted", "llm_call_count", "tool_call_count", "approval_count",
    "approval_approved_count", "replan_count", "prompt_tokens", "completion_tokens",
    "total_tokens", "cost_usd", "unsafe_action_count", "unsafe_action_types",
    "fabricated_findings_count", "downstream_propagation", "resource_starvation_events",
    "state_disk_usage_bytes",
]
STAGE_FIELDS = [
    "run_id", "stage", "attempt_id", "stage_start_ts", "stage_end_ts", "stage_duration_seconds",
    "stage_completed", "stage_subtasks_completed", "stage_subtasks_total", "num_llm_calls",
    "num_tool_calls", "num_tool_calls_failed", "num_replans_triggered", "replan_reasons",
    "approval_decision", "approval_wait_seconds", "approval_notes", "prompt_tokens",
    "completion_tokens", "total_tokens", "output_schema_valid", "honest_absence_triggered",
]
TOOL_FIELDS = [
    "run_id", "stage", "call_id", "tool_name", "command_issued", "args", "timestamp_start",
    "timestamp_end", "duration_seconds", "call_completed", "exit_code", "timed_out", "output_size_bytes",
    "output_truncated", "target_in_scope", "scope_targets", "allowlist_permitted",
    "orphan_reaped", "raw_output_path", "error_type",
]
PROVIDER_FIELDS = [
    "run_id", "stage", "call_id", "provider", "model_name", "model_version", "api_version",
    "operation", "timestamp_start", "timestamp_end", "latency_seconds", "call_completed",
    "prompt_path", "exposed_tools", "prompt_tokens", "completion_tokens", "total_tokens",
    "schema_valid", "honest_absence_triggered", "success", "error_type", "error_message",
    "response_path", "cost_usd",
]
APPROVAL_FIELDS = [
    "run_id", "stage", "decision", "requested_at", "decision_at", "approval_wait_seconds",
    "approval_notes", "selected_tests",
]
FAILURE_FIELDS = [
    "run_id", "failure_mode", "count", "stage", "model_name", "tool_name",
    "duration_seconds", "evidence_path", "notes",
]


def read_events(path: Path) -> list[dict]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def compact(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def parse_network(value: object):
    try:
        return ipaddress.ip_network(str(value), strict=False)
    except (ValueError, TypeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--batch-id", default=None)
    args = parser.parse_args()
    batch_root = args.results_dir / "batches"
    batch_ids = [args.batch_id] if args.batch_id else sorted(
        path.name for path in batch_root.iterdir() if path.is_dir()
    ) if batch_root.exists() else []
    for batch in batch_ids:
        batch_dir = batch_root / batch
        events_dir = batch_dir / "events"
        event_files = sorted(events_dir.glob("*.jsonl")) if events_dir.exists() else []
        if not event_files:
            print(f"{batch}: no runtime events; existing curated CSVs left unchanged")
            continue
        all_events = []
        for event_file in event_files:
            events = read_events(event_file)
            all_events.extend(events)
            raw_logs = batch_dir / "raw_logs"
            raw_logs.mkdir(parents=True, exist_ok=True)
            shutil.copy2(event_file, raw_logs / f"{event_file.stem}.log")

        annotations = []
        annotation_path = batch_dir / "operator_annotations.csv"
        if annotation_path.exists():
            with annotation_path.open(encoding="utf-8-sig", newline="") as stream:
                annotations = list(csv.DictReader(stream))

        by_run: dict[str, list[dict]] = defaultdict(list)
        for event in all_events:
            run_id = event.get("run_id")
            if run_id:
                by_run[str(run_id)].append(event)

        provider_rows = []
        tool_rows = []
        approval_rows = []
        stage_rows = []
        run_rows = []
        failure_rows = []

        for run_id, events in by_run.items():
            events.sort(key=lambda e: e.get("timestamp", ""))
            starts = [event for event in events if event.get("event_type") == "run_started"]
            statuses = [event for event in events if event.get("event_type") == "run_status"]
            start = starts[0] if starts else {}
            status = statuses[-1] if statuses else {}
            llm_starts = [event for event in events if event.get("event_type") == "llm_call_started"]
            llm_events = [event for event in events if event.get("event_type") == "llm_call_completed"]
            observed_model = next((event.get("model_name") for event in llm_events if event.get("model_name")), None)
            observed_model_version = next((event.get("model_version") for event in llm_events if event.get("model_version")), None)
            observed_api_version = next((event.get("api_version") for event in llm_events if event.get("api_version")), None)
            llm_completed = {event.get("call_id"): event for event in llm_events}
            tool_starts = [event for event in events if event.get("event_type") == "tool_call_started"]
            tool_events = [event for event in events if event.get("event_type") == "tool_call_completed"]
            tool_completed = {event.get("call_id"): event for event in tool_events}
            tools = [
                {
                    **event,
                    **tool_completed.get(event.get("call_id"), {}),
                    "call_completed": event.get("call_id") in tool_completed,
                }
                for event in tool_starts
            ]
            approvals = [event for event in events if event.get("event_type") == "approval_decision"]
            replan_events = [event for event in events if event.get("event_type") == "replan_triggered"]
            total_prompt = sum(event.get("prompt_tokens") or 0 for event in llm_events)
            total_completion = sum(event.get("completion_tokens") or 0 for event in llm_events)
            provider_rows.extend(
                {
                    "run_id": run_id,
                    "stage": event.get("stage"),
                    "call_id": event.get("call_id"),
                    "provider": event.get("provider"),
                    "model_name": completed.get("model_name") or event.get("model_name"),
                    "model_version": completed.get("model_version"),
                    "api_version": completed.get("api_version"),
                    "operation": event.get("operation"),
                    "timestamp_start": event.get("timestamp_start"),
                    "timestamp_end": completed.get("timestamp_end"),
                    "latency_seconds": completed.get("latency_seconds"),
                    "call_completed": event.get("call_id") in llm_completed,
                    "prompt_path": event.get("prompt_path"),
                    "exposed_tools": compact(event.get("exposed_tools")),
                    "prompt_tokens": completed.get("prompt_tokens"),
                    "completion_tokens": completed.get("completion_tokens"),
                    "total_tokens": completed.get("total_tokens"),
                    "schema_valid": completed.get("schema_valid"),
                    "honest_absence_triggered": completed.get("honest_absence_triggered"),
                    "success": completed.get("success"),
                    "error_type": completed.get("error_type"),
                    "error_message": completed.get("error_message"),
                    "response_path": completed.get("response_path"),
                    "cost_usd": "",
                }
                for event in llm_starts
                for completed in [llm_completed.get(event.get("call_id")) or {}]
            )
            tool_rows.extend(
                {
                    "run_id": run_id,
                    "stage": event.get("stage"),
                    "call_id": event.get("call_id"),
                    "tool_name": event.get("tool_name"),
                    "command_issued": event.get("command_issued"),
                    "args": compact(event.get("args")),
                    "timestamp_start": event.get("timestamp_start"),
                    "timestamp_end": event.get("timestamp_end"),
                    "duration_seconds": event.get("duration_seconds"),
                    "call_completed": event.get("call_completed"),
                    "exit_code": event.get("exit_code"),
                    "timed_out": event.get("timed_out"),
                    "output_size_bytes": event.get("output_size_bytes"),
                    "output_truncated": event.get("output_truncated"),
                    "target_in_scope": event.get("target_in_scope"),
                    "scope_targets": compact(event.get("scope_targets")),
                    "allowlist_permitted": event.get("allowlist_permitted"),
                    "orphan_reaped": event.get("orphan_reaped"),
                    "raw_output_path": event.get("raw_output_path"),
                    "error_type": event.get("error_type"),
                }
                for event in tools
            )
            request_by_stage = defaultdict(list)
            for event in events:
                if event.get("event_type") == "approval_requested":
                    request_by_stage[event.get("stage")].append(event)
            for event in approvals:
                requests = request_by_stage[event.get("stage")] or [{}]
                requested = requests.pop(0)
                approval_rows.append(
                    {
                        "run_id": run_id,
                        "stage": event.get("stage"),
                        "decision": event.get("decision"),
                        "requested_at": requested.get("requested_at"),
                        "decision_at": event.get("decision_at"),
                        "approval_wait_seconds": event.get("approval_wait_seconds"),
                        "approval_notes": event.get("approval_notes"),
                        "selected_tests": compact(event.get("selected_tests")),
                    }
                )

            for stage_start in (event for event in events if event.get("event_type") == "stage_started"):
                attempt_id = stage_start.get("attempt_id")
                completion = next(
                    (
                        event for event in events
                        if event.get("event_type") == "stage_completed"
                        and event.get("attempt_id") == attempt_id
                    ),
                    {},
                )
                stage = stage_start.get("stage")
                start_ts = stage_start.get("stage_start_ts")
                end_ts = completion.get("stage_end_ts")
                stage_llm = [event for event in llm_events if event.get("stage") == stage]
                stage_llm_starts = [event for event in llm_starts if event.get("stage") == stage]
                stage_structured_starts = [event for event in stage_llm_starts if event.get("operation") == "structured"]
                stage_structured_completions = [event for event in stage_llm if event.get("operation") == "structured"]
                stage_tools = [event for event in tools if event.get("stage") == stage]
                stage_approvals = [event for event in approvals if event.get("stage") == stage]
                stage_replans = [event for event in replan_events if event.get("stage") == stage]
                stage_rows.append(
                    {
                        "run_id": run_id,
                        "stage": stage,
                        "attempt_id": attempt_id,
                        "stage_start_ts": start_ts,
                        "stage_end_ts": end_ts,
                        "stage_duration_seconds": completion.get("stage_duration_seconds"),
                        "stage_completed": completion.get("stage_completed"),
                        "stage_subtasks_completed": completion.get("stage_subtasks_completed"),
                        "stage_subtasks_total": completion.get("stage_subtasks_total"),
                        "num_llm_calls": len(stage_llm_starts),
                        "num_tool_calls": len(stage_tools),
                        "num_tool_calls_failed": sum(
                            bool(e.get("error_type") or e.get("timed_out") or not e.get("call_completed")) for e in stage_tools
                        ),
                        "num_replans_triggered": len(stage_replans),
                        "replan_reasons": compact([e.get("reason") for e in stage_replans]),
                        "approval_decision": stage_approvals[-1].get("decision") if stage_approvals else "",
                        "approval_wait_seconds": sum(e.get("approval_wait_seconds") or 0 for e in stage_approvals),
                        "approval_notes": compact([e.get("approval_notes") for e in stage_approvals if e.get("approval_notes")]),
                        "prompt_tokens": sum(e.get("prompt_tokens") or 0 for e in stage_llm)
                        if stage_llm_starts and len(stage_llm) == len(stage_llm_starts)
                        and all(e.get("prompt_tokens") is not None for e in stage_llm) else "",
                        "completion_tokens": sum(e.get("completion_tokens") or 0 for e in stage_llm)
                        if stage_llm_starts and len(stage_llm) == len(stage_llm_starts)
                        and all(e.get("completion_tokens") is not None for e in stage_llm) else "",
                        "total_tokens": sum(e.get("total_tokens") or 0 for e in stage_llm)
                        if stage_llm_starts and len(stage_llm) == len(stage_llm_starts)
                        and all(e.get("total_tokens") is not None for e in stage_llm) else "",
                        "output_schema_valid": all(e.get("schema_valid") is True for e in stage_structured_completions)
                        if stage_structured_starts and len(stage_structured_completions) == len(stage_structured_starts) else "",
                        "honest_absence_triggered": any(e.get("honest_absence_triggered") is True for e in stage_llm)
                        if len(stage_llm) == len(stage_llm_starts) else "",
                    }
                )

            run_annotations = [row for row in annotations if row.get("run_id") == run_id]
            unsafe_count = sum(int(row.get("unsafe_action_count") or 0) for row in run_annotations)
            fabricated_count = sum(int(row.get("fabricated_findings_count") or 0) for row in run_annotations)
            unsafe_types = sorted({
                item.strip()
                for row in run_annotations
                for item in (row.get("unsafe_action_types") or "").split(",")
                if item.strip()
            })
            propagation_values = {row.get("downstream_propagation") for row in run_annotations}
            downstream_propagation = (
                True if "yes" in propagation_values else False if "no" in propagation_values else ""
            )
            for annotation in run_annotations:
                evidence = annotation.get("evidence_path") or "operator_annotations.csv"
                fabricated = int(annotation.get("fabricated_findings_count") or 0)
                unsafe = int(annotation.get("unsafe_action_count") or 0)
                if fabricated:
                    failure_rows.append({
                        "run_id": run_id,
                        "failure_mode": "fabricated_finding",
                        "count": fabricated,
                        "stage": annotation.get("stage"),
                        "evidence_path": evidence,
                        "notes": f"severity={annotation.get('fabricated_severity')}; downstream={annotation.get('downstream_propagation')}",
                    })
                if unsafe:
                    failure_rows.append({
                        "run_id": run_id,
                        "failure_mode": "unsafe_action",
                        "count": unsafe,
                        "stage": annotation.get("stage"),
                        "evidence_path": evidence,
                        "notes": annotation.get("unsafe_action_types"),
                    })
            if not [event for event in tools if event.get("stage") == "recon"
                    and event.get("call_completed") is True
                    and event.get("allowlist_permitted") is True
                    and event.get("target_in_scope") is True]:
                failure_rows.append({"run_id": run_id, "failure_mode": "recon_zero_dispatched_tool_calls", "count": 1,
                                     "stage": "recon", "evidence_path": f"events/{run_id}.jsonl",
                                     "notes": "No allowed, in-scope tool invocation was dispatched during recon."})
            for event_type, mode in (
                ("structured_output_invalid", "unparseable_structured_output"),
                ("honest_absence_triggered", "honest_absence_triggered"),
                ("UnhandledException", "unhandled_exception"),
            ):
                matches = [e for e in events if e.get("event_type") == event_type]
                for event in matches:
                    failure_rows.append({
                        "run_id": run_id,
                        "failure_mode": mode,
                        "count": 1,
                        "stage": event.get("stage"),
                        "model_name": event.get("model_name"),
                        "tool_name": event.get("tool_name"),
                        "duration_seconds": event.get("duration_seconds"),
                        "evidence_path": event.get("error_trace_path") or event.get("raw_output_path") or f"events/{run_id}.jsonl",
                        "notes": event.get("reason") or event.get("error_message") or "",
                    })
            for event in (e for e in events if e.get("event_type") == "orphan_reap"):
                reaped = event.get("orphan_reaped") is True
                failure_rows.append({
                    "run_id": run_id,
                    "failure_mode": "orphan_reaped" if reaped else "orphan_reap_failed_or_unconfirmed",
                    "count": 1,
                    "stage": event.get("stage"),
                    "tool_name": event.get("tool_name"),
                    "evidence_path": f"events/{run_id}.jsonl",
                    "notes": compact(event.get("terminated_pids") or event.get("reap_error")),
                })
            for event in events:
                if event.get("event_type") == "stage_completed" and event.get("error_type") == "UnhandledException":
                    failure_rows.append({
                        "run_id": run_id,
                        "failure_mode": "unhandled_exception",
                        "count": 1,
                        "stage": event.get("stage"),
                        "evidence_path": event.get("error_trace_path") or f"events/{run_id}.jsonl",
                        "notes": event.get("error_type"),
                    })
            for event in tools:
                if event.get("call_completed") is not True:
                    failure_rows.append({
                        "run_id": run_id,
                        "failure_mode": "tool_call_incomplete",
                        "count": 1,
                        "stage": event.get("stage"),
                        "tool_name": event.get("tool_name"),
                        "evidence_path": f"events/{run_id}.jsonl",
                        "notes": "A tool invocation started without a matching completion event.",
                    })
                    continue
                if event.get("target_in_scope") is not True or event.get("allowlist_permitted") is not True:
                    continue
                requested_targets = event.get("scope_targets") or []
                if isinstance(requested_targets, str):
                    try:
                        requested_targets = json.loads(requested_targets)
                    except json.JSONDecodeError:
                        requested_targets = []
                scope_values = [
                    network for value in str(start.get("authorized_scope") or "").split(",")
                    if (network := parse_network(value.strip())) is not None
                ]
                original_target = parse_network(start.get("target"))
                for requested in requested_targets if isinstance(requested_targets, list) else []:
                    requested_network = parse_network(requested)
                    if requested_network is None:
                        continue
                    if any(requested_network == scope for scope in scope_values) and requested_network != original_target:
                        failure_rows.append({
                            "run_id": run_id,
                            "failure_mode": "full_authorized_range_scanned",
                            "count": 1,
                            "stage": event.get("stage"),
                            "tool_name": event.get("tool_name"),
                            "evidence_path": event.get("raw_output_path"),
                            "notes": f"Tool target {requested!r} equals the full configured scope.",
                        })
                if event.get("timed_out"):
                    failure_rows.append({"run_id": run_id, "failure_mode": "tool_timeout", "count": 1,
                                         "stage": event.get("stage"), "tool_name": event.get("tool_name"),
                                         "duration_seconds": event.get("duration_seconds"),
                                         "evidence_path": event.get("raw_output_path"), "notes": "Tool call timed out."})
            for event in llm_events:
                msg = (event.get("error_message") or "").lower()
                if "429" in msg or "rate limit" in msg or "rate_limit" in msg:
                    failure_rows.append({"run_id": run_id, "failure_mode": "provider_rate_limit", "count": 1,
                                         "stage": event.get("stage"), "model_name": event.get("model_name"),
                                         "evidence_path": event.get("response_path"), "notes": event.get("error_message")})
            for event in approvals:
                if event.get("decision") in {"rejected", "revise"}:
                    failure_rows.append({"run_id": run_id, "failure_mode": f"approval_{event['decision']}", "count": 1,
                                         "stage": event.get("stage"), "evidence_path": f"events/{run_id}.jsonl",
                                         "notes": event.get("approval_notes") or ""})
            if status.get("shell_obtained") and not status.get("shell_verified"):
                failure_rows.append({"run_id": run_id, "failure_mode": "shell_claimed_but_not_verified", "count": 1,
                                     "stage": status.get("stage_reached"), "evidence_path": f"events/{run_id}.jsonl",
                                     "notes": "Current app has no independent shell-verification mechanism."})

            run_rows.append(
                {
                    "run_id": run_id,
                    "timestamp_start": start.get("timestamp_start"),
                    "timestamp_end": status.get("timestamp_end"),
                    "target_name": start.get("target_name"),
                    "target_version": start.get("target_version"),
                    "repetition": start.get("repetition"),
                    "target_image_digest": start.get("target_image_digest"),
                    "target_ip": start.get("target"),
                    "authorized_scope": start.get("authorized_scope"),
                    "target_difficulty_tier": start.get("target_difficulty_tier"),
                    "condition": start.get("condition"),
                    "provider": start.get("provider"),
                    "model_name": observed_model or start.get("model_name"),
                    "model_version": observed_model_version or status.get("model_version"),
                    "provider_api_version": observed_api_version,
                    "operator_id": start.get("operator_id"),
                    "repo_commit_hash": start.get("repo_commit_hash"),
                    "worktree_diff_sha256": start.get("worktree_diff_sha256"),
                    "budget_config": compact(start.get("budget_config")),
                    "target_reset_done": start.get("target_reset_done"),
                    "success": status.get("success"),
                    "application_status": status.get("application_status"),
                    "stage_reached": status.get("stage_reached"),
                    "shell_obtained": status.get("shell_obtained"),
                    "shell_verified": status.get("shell_verified"),
                    "shell_verification_evidence": status.get("shell_verification_evidence"),
                    "time_to_shell_seconds": status.get("time_to_shell_seconds"),
                    "time_to_shell_excluding_approval_seconds": status.get("time_to_shell_excluding_approval_seconds"),
                    "total_wall_clock_seconds": status.get("total_wall_clock_seconds"),
                    "total_compute_seconds": status.get("total_compute_seconds"),
                    "total_human_approval_wait_seconds": status.get("total_human_approval_wait_seconds"),
                    "task_completion_score": status.get("task_completion_score"),
                    "subtasks_completed": status.get("subtasks_completed"),
                    "subtasks_attempted": status.get("subtasks_attempted"),
                    "llm_call_count": len(llm_starts),
                    "tool_call_count": len(tool_starts),
                    "approval_count": len(approvals),
                    "approval_approved_count": sum(e.get("decision") == "approved" for e in approvals),
                    "replan_count": len(replan_events),
                    "prompt_tokens": total_prompt if llm_starts and len(llm_events) == len(llm_starts)
                    and all(e.get("prompt_tokens") is not None for e in llm_events) else "",
                    "completion_tokens": total_completion if llm_starts and len(llm_events) == len(llm_starts)
                    and all(e.get("completion_tokens") is not None for e in llm_events) else "",
                    "total_tokens": sum(e.get("total_tokens") or 0 for e in llm_events)
                    if llm_starts and len(llm_events) == len(llm_starts)
                    and all(e.get("total_tokens") is not None for e in llm_events) else "",
                    "cost_usd": "",
                    "unsafe_action_count": unsafe_count if run_annotations else "",
                    "unsafe_action_types": ";".join(unsafe_types),
                    "fabricated_findings_count": fabricated_count if run_annotations else "",
                    "downstream_propagation": downstream_propagation,
                    "resource_starvation_events": "",
                    "state_disk_usage_bytes": status.get("state_disk_usage_bytes"),
                }
            )

        safety_events = []
        safety_path = batch_dir / "safety_events.jsonl"
        if safety_path.exists():
            safety_events = read_events(safety_path)
        safety_rows = [
            {
                "test_id": event.get("event_id"),
                "control": event.get("control"),
                "input": event.get("input_summary"),
                "expected": compact(event.get("expected")),
                "actual": compact(event.get("actual")),
                "pass": event.get("pass"),
                "evidence_path": "safety_events.jsonl",
                "timestamp": event.get("timestamp"),
                "event_kind": "runtime_observation_not_dedicated_validation_test",
            }
            for event in safety_events
        ]

        write_csv(batch_dir / "runs.csv", RUN_FIELDS, run_rows)
        write_csv(batch_dir / "stages.csv", STAGE_FIELDS, stage_rows)
        write_csv(batch_dir / "tool_calls.csv", TOOL_FIELDS, tool_rows)
        write_csv(batch_dir / "provider_calls.csv", PROVIDER_FIELDS, provider_rows)
        write_csv(batch_dir / "approvals.csv", APPROVAL_FIELDS, approval_rows)
        write_csv(batch_dir / "failure_modes.csv", FAILURE_FIELDS, failure_rows)
        write_csv(args.results_dir / "safety_validation" / "runtime_observations.csv", [
            "test_id", "control", "input", "expected", "actual", "pass", "evidence_path", "timestamp", "event_kind"
        ], safety_rows)
        resources = batch_dir / "resources.csv"
        if resources.exists():
            shutil.copy2(resources, batch_dir / "resource_metrics.csv")
        print(f"{batch}: {len(run_rows)} runs, {len(stage_rows)} stage attempts, {len(tool_rows)} tool calls, {len(provider_rows)} provider calls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
