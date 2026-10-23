# Application-Wide Evidence and Telemetry

The study concerns the entire Threshold application, not only its generated engagement reports. Instrument and validate the end-to-end path from a request entering the API through target/scope validation, provider/model calls, orchestration, approval decisions, tool dispatch, timeout/budget handling, persistent state, report generation, and resource collection.

## Application surfaces and evidence

| Surface | Evidence to capture for every relevant run | Paper interpretation |
|---|---|---|
| Request/input validation | Sanitized request, validation result/error code, server-selected scope, engagement-started flag | Fail-closed behavior requires dedicated tests, not a report narrative |
| Orchestrator/stages | State transitions with timestamps, stage IDs, start/end/completion, retry/replan reason | Derives stage latency and partial completion |
| Approval UI/API | Stage, proposed action/checks, decision, operator ID, decision timestamps, rationale, wait | Measures human cost and decision distribution |
| LLM provider adapters | Provider/model/API version, request/response IDs, call latency, token metadata, parse/tool-call validity, status/rate limit/retry | Supports provider comparison only when all required calls are observed |
| Tool/MCP dispatch | Agent role, tool schema/name, command, scope result, role allowlist result, timestamps, exit code, timeout, output bytes and output path | Verifies actual execution and policy enforcement |
| Budgets/timeouts | Budget values at run start, checks, halt reason, call timeout, continuation state | Supports enforcement and resource-bound claims |
| Process lifecycle | Process/container identifiers, timeout, terminate/reap status, host process evidence where required | A mocked reaper result is not proof an orphan process exited |
| Durable state/restart | Engagement ID/thread ID before and after restart, state checkpoint, restart timestamp, resumed gate and recovery latency | Supports durability only after a real orchestrator restart test |
| Concurrency | Three or more independent engagement IDs, interleaved events, state separation and result checks | Supports concurrent-safety claim after controlled test |
| Report/finding pipeline | Finding IDs, evidence lineage, severity adjudication, missing-output routing, report propagation | Measures fabricated finding rate and downstream impact |
| Resources/environment | 1-second Docker CPU/memory samples, disk use, image digests, OS/kernel, Docker/Python versions, dependencies, commit | Reproducibility and resource analysis |

## Collection implementation in this checkout

Repository source includes append-only per-run telemetry and a collection workflow: `pentest-agents/pentest_agents/telemetry.py`, `scripts/run_batch.py`, `scripts/collect_metrics.py`, `scripts/calculate_costs.py`, `scripts/aggregate.py`, `scripts/make_tables.py`, `scripts/make_figures.py`, `scripts/capture_environment.py`, and `scripts/collect_resources.py`. The project README describes event JSONL, prompt/raw output retention, environment capture, and one-second Docker sampling. The current batch runner drives the Threshold application only; it refuses to relabel that execution as a manual, single-agent, or ablation condition.

The supplied audit specifically asks for a metrics export endpoint such as `/engagements/{id}/metrics`. A source search found telemetry and batch export scripts but no such endpoint in the API. Mark this endpoint **not confirmed/required** until implemented or explicitly replaced by an equally complete, documented export interface. Verify the endpoint in code and with a live API call before claiming it exists.

Runtime telemetry is a collection capability, not itself an experiment. Collect actual runs, inspect event completeness, reconcile event counts with source logs, and preserve event/collector versions. Include interrupted starts so lost or incomplete calls cannot vanish from analysis. Preserve raw provider/tool material with credential redaction and access controls; the paper package should contain only authorized, appropriately redacted evidence.

An optional dry-run/simulation mode could make the artifact safer for reviewers to exercise. If added, it must clearly distinguish simulated tool results from live execution in every event and report, provide deterministic mock fixtures, and never claim simulated results as target findings. Treat it as a usability/reproducibility feature, not a substitute for the authorized live evaluation.

## Required event-to-table chain

1. Every request receives a stable `run_id`, `engagement_id`, batch ID, condition, repetition, target ID, and resolved model identity.
2. Persist timestamped events before and after each provider/tool call and at each stage/state transition. Record failure/timeout events even when there is no completion event.
3. Store raw prompts, provider replies, tool stdout/stderr, exceptions, approval notes, and resource samples in the batch directory; reference them from CSV rows.
4. Run the collector and reject inconsistent event sequences, duplicated IDs, missing terminal states, invalid timestamps, and unknown required fields. Never fill unknown historical data with zeros.
5. Run cost/statistics/table/figure generators from that batch and record the exact command, package versions, input hashes, and output hashes.
6. Review all paper numbers against generated source rows before submission.

## Event coverage checklist

At minimum, events must distinguish: run started/ended, stage started/completed, approval requested/decided, provider call started/completed/failed, tool call started/completed/failed, timeout, replan, budget halt, scope check, allowlist denial, structured-output parse result, honest absence, finding creation/adjudication/report propagation, exception, restart recovery, and resource sample. Include timestamps and run/stage/call correlation IDs. Provider returned token usage is authoritative; missing token usage stays missing.

The retrospective report import in `results/batches/2026-10-21_existing_reports/` cannot reconstruct these application events. Keep its “report evidence” condition separate from prospective telemetry-backed runs.
