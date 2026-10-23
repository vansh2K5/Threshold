"""Interactive, human-approved Threshold batch runner.

This runner only supports the production Threshold condition. Manual,
single-agent, and ablation conditions need separate harnesses; it rejects
those labels instead of silently running the wrong system under them.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = {"claude", "gemini", "groq", "openrouter"}
SENSITIVE_KEY = re.compile(r"(?i)(api[_-]?key|access[_-]?token|password|passwd|secret)")


def redact_config(value):
    if isinstance(value, dict):
        return {key: "[REDACTED]" if SENSITIVE_KEY.search(str(key)) else redact_config(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [redact_config(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"(?i)(api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*([^\s,;]+)", r"\1=[REDACTED]", value)
    return value


def request_json(url: str, payload: dict, timeout: float = 180.0) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def decide_at_gate(base_url: str, state: dict) -> dict:
    pending = state.get("pending_action") or {}
    stage = pending.get("stage") or state.get("current_stage")
    print(f"\nEngagement {state.get('id')} paused for {stage} approval")
    print(pending.get("summary") or "No summary supplied")
    options = pending.get("test_options") or []
    for option in options:
        print(f"  {option.get('id')}: {option.get('label')} ({option.get('evidence')})")
    if pending.get("test_options_note"):
        print(pending["test_options_note"])
    decision = input("Decision [approved/rejected/revise]: ").strip().lower()
    while decision not in {"approved", "rejected", "revise"}:
        decision = input("Enter approved, rejected, or revise: ").strip().lower()
    selected = []
    if decision == "approved" and options:
        raw = input("Selected test ids (comma separated; blank skips these checks): ").strip()
        selected = [part.strip() for part in raw.split(",") if part.strip()]
    note = input("Operator note (reason/trust/surprises; blank if none): ").strip() or None
    return request_json(
        f"{base_url}/api/engagement/{state['id']}/approvals",
        {"stage": stage, "decision": decision, "selected_tests": selected, "note": note},
    )


def start_resource_sampler(batch_dir: Path, results_dir: Path, batch_id: str, run_id: str):
    stop_file = batch_dir / f".stop_resources_{run_id}"
    if stop_file.exists():
        stop_file.unlink()
    log_path = batch_dir / "raw_logs" / f"resources_{run_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_stream = log_path.open("a", encoding="utf-8")
    command = [
        sys.executable,
        str(ROOT / "scripts" / "collect_resources.py"),
        "--run-id", run_id,
        "--batch-id", batch_id,
        "--results-dir", str(results_dir),
        "--stop-file", str(stop_file),
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log_stream,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
    except OSError as exc:
        log_stream.close()
        print(f"Resource sampling unavailable; continuing the engagement: {exc}", file=sys.stderr)
        return None
    return process, stop_file, log_stream


def stop_resource_sampler(sampler) -> None:
    if not sampler:
        return
    process, stop_file, log_stream = sampler
    stop_file.touch()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.terminate()
        process.wait(timeout=5)
    finally:
        log_stream.close()
        try:
            stop_file.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix", type=Path, help="JSON experiment matrix")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    config = json.loads(args.matrix.read_text(encoding="utf-8"))
    conditions = config.get("conditions", ["threshold"])
    unsupported = sorted(set(conditions) - {"threshold"})
    if unsupported:
        print(
            "This application runner cannot execute these conditions: "
            + ", ".join(unsupported)
            + ". No runs were started; use separately implemented baseline/ablation harnesses.",
            file=sys.stderr,
        )
        return 2
    providers = config.get("providers", ["gemini"])
    invalid = sorted(set(providers) - PROVIDERS)
    if invalid:
        print(f"Unsupported providers: {', '.join(invalid)}", file=sys.stderr)
        return 2
    targets = config.get("targets") or []
    repetitions = int(config.get("repetitions", 1))
    if not targets or repetitions < 1:
        print("Matrix must define at least one target and repetitions >= 1.", file=sys.stderr)
        return 2
    operator_id = config.get("operator_id") or input("Operator ID (anonymized): ").strip()
    batch = config.get("batch_id") or datetime.now(UTC).strftime("%Y-%m-%d_threshold")
    batch_dir = args.results_dir / "batches" / batch
    batch_dir.mkdir(parents=True, exist_ok=True)
    capture_log = batch_dir / "raw_logs" / "environment_capture.log"
    capture_log.parent.mkdir(parents=True, exist_ok=True)
    capture = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "capture_environment.py"),
         "--results-dir", str(args.results_dir), "--batch-id", batch,
         "--config-notes", str(config.get("manual_config_changes") or "")],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    capture_log.write_text(capture.stdout, encoding="utf-8")
    try:
        captured_metadata = json.loads((batch_dir / "batch_metadata.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        captured_metadata = {}
    repo_commit = captured_metadata.get("repo_commit_hash_at_capture")
    worktree_diff_sha256 = captured_metadata.get("tracked_worktree_diff_sha256_at_capture")
    metadata = {
        "batch_id": batch,
        "planned_at": datetime.now(UTC).isoformat(),
        "conditions_requested": conditions,
        "conditions_executed_by_this_script": ["threshold"],
        "repetitions_per_target_provider": repetitions,
        "providers_requested": providers,
        "operator_id": operator_id,
        "repo_commit_hash_at_run_request": repo_commit,
        "worktree_diff_sha256_at_run_request": worktree_diff_sha256,
        "approval_protocol": config.get("approval_protocol"),
        "target_reset_policy": config.get("target_reset_policy"),
        "scoring_rubric": config.get("scoring_rubric"),
        "shell_verification_method": "unavailable in current application; no shell will be marked verified",
        "budget_config": config.get("budget_config"),
        "matrix": redact_config(config),
        "planned_run_count": len(targets) * repetitions * len(providers),
        "warning": "Only Threshold runs are supported by this application runner. Manual, single-agent, and ablation conditions are not executed here.",
        "environment_capture_exit_code": capture.returncode,
    }
    metadata_path = batch_dir / "batch_metadata.json"
    if metadata_path.exists():
        existing = json.loads(metadata_path.read_text(encoding="utf-8"))
        existing.update(metadata)
        metadata = existing
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    run_count = 0
    skipped_reset_count = 0
    start_request_count = 0
    start_request_failures = 0
    for target in targets:
        reset_instructions = target.get("reset_procedure") or config.get("target_reset_policy") or "No reset procedure recorded"
        for repetition in range(1, repetitions + 1):
            for provider in providers:
                print(f"\nBatch {batch}; target {target.get('name') or target['target']}; repetition {repetition}; provider {provider}")
                print(f"Reset procedure: {reset_instructions}")
                reset_answer = input("Confirm the target has been reset now? [yes/no]: ").strip().lower()
                if reset_answer != "yes":
                    print("Skipped run because reset was not confirmed.", file=sys.stderr)
                    skipped_reset_count += 1
                    continue
                evaluation = {
                    "condition": "threshold",
                    "batch_id": batch,
                    "experiment_run_id": str(uuid.uuid4()),
                    "repetition": repetition,
                    "operator_id": operator_id or None,
                    "target_name": target.get("name"),
                    "target_version": target.get("version"),
                    "target_image_digest": target.get("image_digest"),
                    "target_difficulty_tier": target.get("difficulty_tier"),
                    "target_reset_done": True,
                    "repo_commit_hash": repo_commit,
                    "worktree_diff_sha256": worktree_diff_sha256,
                }
                sampler = start_resource_sampler(
                    batch_dir, args.results_dir, batch, evaluation["experiment_run_id"]
                )
                try:
                    start_request_count += 1
                    state = request_json(
                        f"{args.api.rstrip('/')}/api/engagement",
                        {
                            "message": f"Run the authorized assessment against {target['target']}",
                            "llm_provider": provider,
                            "evaluation": evaluation,
                        },
                    )
                    while state.get("status") == "paused":
                        state = decide_at_gate(args.api.rstrip("/"), state)
                    print(f"Engagement {state.get('id')} ended with status {state.get('status')}")
                    run_count += 1
                except (OSError, RuntimeError, urllib.error.URLError) as exc:
                    start_request_failures += 1
                    print(f"Run request failed: {exc}", file=sys.stderr)
                finally:
                    stop_resource_sampler(sampler)
    metadata["submitted_threshold_run_count"] = run_count
    metadata["start_request_count"] = start_request_count
    metadata["start_request_failures"] = start_request_failures
    metadata["skipped_reset_unconfirmed_count"] = skipped_reset_count
    metadata["submission_finished_at"] = datetime.now(UTC).isoformat()
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Submitted {run_count} Threshold run(s). Application telemetry is written to the selected batch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
