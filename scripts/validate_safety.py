"""Run the repository's isolated safety/control tests and preserve evidence.

This suite invokes only the named pytest cases. Those cases use stub nodes,
test IP ranges, and mocked HexStrike HTTP responses; they do not scan a live
target. The orphan-reaping case is marked partial because mocked termination
does not prove that a real process disappeared from the host process table.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "pentest-agents"
CASES = [
    ("scope_outside_cidr", "fail_closed_scope", "test_safety.py::test_ip_outside_scope_is_blocked", "engagement/tool dispatch blocked", "unit"),
    ("scope_empty", "fail_closed_scope", "test_safety.py::test_empty_allowed_scopes_is_blocked", "no-scope dispatch blocked", "unit"),
    ("scope_ambiguous_dns", "fail_closed_scope", "test_safety.py::test_hostname_with_ambiguous_resolution_is_blocked_even_if_all_in_scope", "ambiguous hostname rejected", "unit_mocked_dns"),
    ("server_scope_override", "server_side_scope", "test_api.py::test_client_cannot_widen_server_configured_scope", "server-configured scope remains authoritative", "api_test_client"),
    ("malformed_target", "input_validation", "test_api.py::test_engagement_rejects_embedded_userinfo", "reject with MALFORMED_TARGET", "api_test_client"),
    ("recon_allowlist", "per_role_allowlist", "test_agents_common.py::test_recon_request_for_msfconsole_is_not_dispatched", "msfconsole is not executed by recon", "fake_model_tool_call"),
    ("analysis_allowlist", "per_role_allowlist", "test_mcp_client.py::test_analysis_and_report_roles_get_no_direct_tools", "analysis receives no tools", "mocked_tool_catalog"),
    ("replan_budget", "budget_enforcement", "test_coordinator.py::test_replan_budget_halts_the_run_after_max_replans", "halt after configured replan ceiling", "stub_graph"),
    ("wall_clock_budget", "budget_enforcement", "test_coordinator.py::test_wall_clock_budget_halts_after_approval_when_limit_is_exceeded", "halt after a simulated wall-clock limit", "stub_graph_short_limit"),
    ("tool_timeout", "per_call_timeout", "test_agents_common.py::test_slow_tool_call_times_out_into_transcript_not_a_halt", "tool timeout recorded and synthesis continues", "slow_fake_tool"),
    ("orphan_reaping", "orphan_reaping", "test_mcp_client.py::test_reap_timed_out_processes_kills_only_stale_running_ones", "stale process termination requested", "partial_mock_no_host_ps"),
    ("restart_durability", "restart_durability", "test_db.py::test_engagement_survives_a_simulated_restart", "saved engagement resumes after store reopen", "partial_simulated_store_reopen"),
    ("concurrency_3", "concurrency", "test_registry.py::test_three_concurrent_engagements_keep_independent_state", "three engagement states remain isolated", "three_stub_engagements"),
]
FIELDS = ["test_id", "batch_id", "control", "input", "expected", "actual", "pass", "evidence_path", "timestamp", "validation_level"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--case", action="append", choices=[case[0] for case in CASES])
    args = parser.parse_args()
    batch = args.batch_id or datetime.now(UTC).strftime("%Y-%m-%d_safety")
    selected = [case for case in CASES if not args.case or case[0] in args.case]
    evidence_dir = args.results_dir / "safety_validation" / "evidence" / batch
    evidence_dir.mkdir(parents=True, exist_ok=True)
    output_csv = args.results_dir / "safety_validation" / "tests.csv"
    rows = []
    if output_csv.exists():
        with output_csv.open(encoding="utf-8-sig", newline="") as stream:
            rows.extend(
                row for row in csv.DictReader(stream)
                if not (row.get("batch_id") == batch and row.get("test_id", "").endswith(tuple(case[0] for case in selected)))
            )

    env = os.environ.copy()
    env["PENTEST_AGENTS_BATCH_ID"] = batch
    env["PENTEST_AGENTS_RESULTS_DIR"] = str(args.results_dir.resolve())
    env.setdefault("PENTEST_AGENTS_LAB_CIDR", "192.168.56.0/24")
    for case_id, control, pytest_node, expected, level in selected:
        evidence = evidence_dir / f"{case_id}.log"
        command = [sys.executable, "-m", "pytest", "-q", f"tests/{pytest_node}"]
        completed = subprocess.run(
            command,
            cwd=APP,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        evidence.write_text(completed.stdout, encoding="utf-8")
        passed = completed.returncode == 0
        blocked = completed.returncode != 0 and "No module named pytest" in completed.stdout
        # A mocked kill call is not proof of no orphaned host process.
        recorded_pass = "" if blocked or (level.startswith("partial_") and passed) else passed
        rows.append(
            {
                "test_id": f"{batch}_{case_id}",
                "batch_id": batch,
                "control": control,
                "input": pytest_node,
                "expected": expected,
                "actual": (
                    "passed" if passed else
                    "blocked: pytest is not installed in the active Python environment" if blocked else
                    f"failed (exit {completed.returncode})"
                ),
                "pass": recorded_pass,
                "evidence_path": evidence.relative_to(args.results_dir).as_posix(),
                "timestamp": datetime.now(UTC).isoformat(),
                "validation_level": level,
            }
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Recorded {len(selected)} safety cases in {output_csv}")
    latest = rows[-len(selected):] if selected else []
    if any(row.get("actual", "").startswith("failed") for row in latest):
        return 1
    if any(row.get("actual", "").startswith("blocked:") for row in latest):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
