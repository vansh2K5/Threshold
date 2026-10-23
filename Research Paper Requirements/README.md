# Research Paper Requirements

This folder turns the supplied **Deep Analysis of the Updated Draft** into a repository-grounded work plan for the Threshold paper. It covers the application, its controls and evaluation, the manuscript, and the artifacts needed to reproduce claims.

## Evidence boundary

Only evidence already inside this project was used. The paper draft itself was not found among the repository files reviewed, so comments about its wording, sections, figures, and references are recorded as items from the supplied audit that still need checking against the editable manuscript. No outside reports or citations were used.

Status labels used below:

- **Verified in project** — directly supported by repository source or stored execution artifact.
- **Observed, limited** — present in the three generated reports, but not a controlled or repeated experiment.
- **Audit-reported** — stated by the supplied paper audit; the underlying manuscript/source artifact was not available for independent checking.
- **Required / unverified** — necessary work without supporting execution evidence yet.

## Current evidence at a glance

- The source describes a five-stage agent workflow, human approval gates, four provider adapters, tool-role restrictions, server-owned scope checks, budget controls, persistent state, and concurrent engagement support. These establish implementation scope, not efficacy.
- Three in-project reports cover two target IPs and OpenRouter. All three report no shell; two mark exploit success true. That success field is not independently scored task completion. The reports show 12 of 12 recorded approval decisions approved.
- The 80.947 s, 88.018 s, and 142.137 s intervals from the first visible approval timestamp to report generation average 103.701 s (sample SD 33.474 s). They are only timestamp-window proxies, not end-to-end latency, compute time, or human approval wait.
- The checklist minimum is unmet. No same-target repeated baseline comparison, verified-shell result, provider comparison, or executed ablation is available. A 13-case safety-suite attempt was blocked before test collection because pytest was unavailable; it produced no passes and no product assertion failures.

## Documents

1. [01 — Audit findings and paper decision](01_audit_findings_and_paper_decision.md): fatal evaluation gap, claim boundaries, and paper-track decision.
2. [02 — Evaluation protocol and metrics](02_evaluation_protocol_and_metrics.md): master design, minimum matrix, rubric, timing, statistics, and procedures.
3. [03 — Application-wide evidence and telemetry](03_application_wide_evidence_and_telemetry.md): what must be measured across the whole application and how to preserve it.
4. [04 — Safety validation and ablations](04_safety_validation_and_ablations.md): test cases, current blocked result, ablation plan, and evidence criteria.
5. [05 — Manuscript structure and editorial requirements](05_manuscript_structure_and_editorial_requirements.md): section changes, contribution wording, prose/format cleanup, and figure requirements.
6. [06 — Reproducibility, benchmark, ethics, and references](06_reproducibility_benchmark_ethics_and_references.md): artifact, target, citation, and responsible-use requirements.
7. [07 — Repository execution checklist](07_repository_execution_checklist.md): prioritized implementation and paper-readiness gates.

## Project evidence to consult

- [Application-wide evidence status](../results/status_report.md)
- [Experiment protocol draft](../results/experiment_protocol.json)
- [Application findings register](../results/application_findings.csv)
- [Requirement coverage matrix](../results/coverage_matrix.csv)
- [Existing-report batch data](../results/batches/2026-10-21_existing_reports/)
- [Safety-suite attempt summary](../results/safety_validation/attempt_summary.md)
- [Repository README and release status](../README.md)

These documents are a requirements and evidence map. They do not substitute for running the missing experiments, independently verifying safety behavior, or checking the original manuscript and bibliography.
