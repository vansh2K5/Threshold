# Audit Findings and Paper Decision

## Decision gate

**Current status: do not present the work as a completed quantitative systems evaluation.** The repository contains application source, an evaluation collection pipeline, and three retrospective engagement reports, but not the repeated comparative data, independent scoring, verified shell evidence, or completed safety suite required by the supplied audit.

Use one of these routes:

1. **Full systems-evaluation paper:** first run the registered target × condition × repetition matrix, complete safety validation, and regenerate every reported result from stored records.
2. **Work-in-progress/design paper:** if experiments cannot be completed, remove all language that implies measured comparative effectiveness and target only a venue that explicitly accepts incomplete evaluation. This is a venue decision to be verified by the authors; it does not make the current evidence a quantitative evaluation.

Do not keep both framings in the same draft. The abstract, contributions, Section VI, conclusion, and code-availability statement must all agree with the chosen route.

## Fatal issues in the supplied audit

The supplied audit reports that the draft calls its evaluation a plan, labels Section VI.B “Evaluation Plan,” calls contribution #4 an evaluation plan, and says the formal validation gate has not passed. The draft was not present in the repository files reviewed, so confirm these exact quotations and headings against the source document before editing. If accurate:

- Replace “evaluation plan” as a claimed contribution with a measured result only after the result exists. Until then, describe the evaluation infrastructure as an artifact or planned study, not an empirical contribution.
- Rename Section VI to “Results and Discussion” only after actual results have been collected. Otherwise explicitly use a work-in-progress/design framing.
- Remove circular wording that treats selected metrics or an evaluation plan as proof of a speed or efficiency claim.
- Do not claim validation readiness while the end-to-end, concurrency, restart, budget, and scope validation remains incomplete.

## What current project evidence can support

The existing report import contains three reports, two target IPs (`172.30.255.10`: one record; `192.168.1.33`: two records), and OpenRouter for all three. The reports say no shell was obtained in all three. Two reports mark the exploit result `Success: True`; this is a model/report field and is not an independently adjudicated task-success score. The reports contain four approval decisions each, all approved (12/12 total), but do not identify the operator, decision rules, or deliberation time.

The visible first-approval-to-report-generation intervals are 80.947, 88.018, and 142.137 seconds (mean 103.701 s; sample SD 33.474 s). These must be called a **report timestamp window**. They do not establish engagement start, total wall-clock, compute time, or human wait. Two report narratives mention incompatible Metasploit payloads, but raw commands and tool outputs were not found, so this is a lead for investigation, not a verified failure count.

The source supports implementation statements about a five-stage workflow (recon, exploit, post-exploit, analysis, report), approval gates, four provider adapters, server-owned scope enforcement, per-role tool allowlists, budget controls, durable engagement state, and concurrent engagement support. Cite these as code-level design/implementation facts, not as measured effectiveness or validated safety claims.

For the authoritative tables and missing-data details, use [the status report](../results/status_report.md), [the findings register](../results/application_findings.csv), [the imported run rows](../results/batches/2026-10-21_existing_reports/runs.csv), and [the descriptive statistics](../results/tables/2026-10-21_existing_reports_descriptive_statistics.csv).

## Claims that must remain out of the Results until measured

- Threshold improves success, task completion, or time-to-shell versus a baseline.
- Approval gates reduce unsafe actions or incur a quantified time cost.
- Allowlisting, honest-absence routing, budgets, scope enforcement, or orphan reaping pass validation or prevent a measured number of incidents.
- The system is provider-agnostic or interchangeable across Gemini, Claude, Groq, and OpenRouter.
- A target was compromised or a shell was obtained based only on the model-reported exploit-success field.
- Cost, token efficiency, restart recovery, resource use, or concurrency reliability based on absent logs.

Every paper claim should point to a code artifact, a raw execution artifact, or a generated table row. If none exists, qualify it as a design intention or remove it.

## Manuscript availability and decision record

No editable paper draft (`.docx`, `.tex`, `.bib`) was found among the repository files reviewed. Treat the detailed editorial items in [05](05_manuscript_structure_and_editorial_requirements.md) as a change checklist derived from the supplied audit, not as edits already made. Record the selected publication route and a commit-pinned draft location before final revision.
