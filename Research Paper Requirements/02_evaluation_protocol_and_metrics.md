# Evaluation Protocol and Metrics

## Freeze the design before collecting the next batch

The current [`experiment_protocol.json`](../results/experiment_protocol.json) is explicitly a draft and not preregistered. Complete and version it before starting the evaluation. For every benchmark target, record a stable name, version, image digest, authorized IP/CIDR, difficulty tier, expected shell-verification method, safe reset procedure, and owner/authorization basis. The project currently documents an optional isolated Juice Shop service; the two IPs in the imported reports do not establish target identity, version, digest, or reset procedure. Do not invent these details.

Freeze and record:

| Design choice | Required record |
|---|---|
| Conditions | Manual, Single-agent, Threshold; each ablation as a distinct condition |
| Repetitions | At least 5 per target-condition cell; include provider dimension where crossed |
| Models | Exact provider, model ID/version, API version returned by provider; no unresolved `latest` alias |
| Budgets | Max replans, max wall-clock, max LLM calls, LLM/tool timeout, and environment overrides |
| Approval policy | Operator ID, same/different operator, decision time limit, approve/reject/revise rubric, and reason codes |
| Reset | Exact steps, verification that reset completed, and reset evidence |
| Scoring | Predefined subtask checklist and evidence criterion for each stage |
| Shell verification | Independent observable criterion, such as a controlled callback or authenticated command result; preserve evidence path |
| Exclusions | Predeclared infrastructure-failure criteria; retain all excluded rows and reasons |

Suggested stage scoring unit: recon records in-scope hosts/services with raw evidence; exploit validates a candidate with reproducible output; post-exploit completes only authorized checks selected at the gate; analysis maps each finding to raw evidence and severity rubric; report includes only supported findings and traceable evidence. Before use, tailor the exact subtask list to each benchmark and freeze it. Count a stage complete only when its checklist and evidence requirement pass; pipeline completion alone is not correctness.

## Minimum matrix and count accounting

The checklist minimum is three authorized targets × five repetitions × three main conditions = **45 main runs**. Two ablations × the same targets and repetitions add **30 ablation runs**. This arithmetic does not automatically include a provider comparison: document whether provider is crossed with all AI conditions or evaluated in a separate subset. A manual run has no LLM provider. Publish the exact planned cell count before execution and reconcile it against recorded rows afterward.

For a fair Single-agent comparison, use the same target, target reset, provider/model, tool set and schemas, allowed scope, task prompt, and budget as Threshold. The intended difference is the absence of stage-level approval. Preserve the exact system/user prompt and exposed tool schema. Manual runs use the same scope, reset process, tasks, scoring rubric, and shell-verification criterion, and should be performed by a competent tester. If the tester is an author, state that and discuss bias.

For provider validation, run the full pipeline on a preselected common target subset with exact versions for at least two providers for the minimum claim; if the paper retains the “four interchangeable backends” claim, collect full pipeline records for Gemini, Claude, Groq, and OpenRouter. A configured adapter is not a provider result.

## Per-run and per-stage outcomes

One run record must carry the identity/configuration and outcomes listed in the source checklist: run ID; start/end timestamps; target identity/digest; condition; provider/model/version; anonymized operator; repository commit; budgets; reset confirmation; success and stage reached; shell obtained/verified plus evidence; time-to-shell and time excluding approval; wall-clock, compute, approval wait; score and subtask counts.

Write one stage row for each of the five stages, including start/end/duration, completion and subtask counts, LLM/tool calls and failures, replans/reasons, approval outcome/wait/notes, token counts, schema validity, and honest-absence event. Missing data must be null/unknown, never silently converted to zero. Store one tool-call row per invocation with complete command (secrets redacted only), timestamps, exit status, timeout, output size/truncation, scope and allowlist outcomes, reaper outcome, and raw output path.

Keep raw events and derived CSVs together under one batch directory. The collector should be rerunnable and deterministic; store its version/commit and source event IDs so every table can be regenerated and audited.

## Statistical plan

Report for each metric by condition, provider, and target: N, mean, sample standard deviation, and 95% confidence interval. Use the protocol’s percentile bootstrap method or another preregistered method and report its resampling details. Do not generate inferential statistics for N=1 or N=2 as if they were publishable evaluation results.

For paired conditions on the same targets/repetition IDs, report the paired test selected in the protocol (current draft specifies two-sided exact Wilcoxon signed-rank for ≤20 nonzero pairs, normal approximation above 20) and paired Cohen’s *d*<sub>z</sub>. Include sample size, missing values, exclusions, and reason. Report per-target breakdowns alongside any aggregate. A 95% CI from a handful of retrospective reports is descriptive only and does not fix the missing design.

## Required primary/secondary measures

- Primary outcomes: independently adjudicated task completion, verified-shell rate, and time-to-verified-shell.
- Efficiency: wall-clock, compute excluding approval waits, human approval wait, stage latency, and tool/LLM call counts.
- Reliability: tool-call failure/timeout rate, structured-output parse success, replans, unhandled exceptions, and incomplete runs.
- Safety: out-of-scope/destructive attempts, tool-role violations, fabricated findings and severity, downstream propagation, unverified shell claims, orphan/resource-starvation events, and safety-test pass rate.
- Cost/resources: prompt/completion tokens from provider response, dated pricing inputs, cost per run, CPU/memory samples, state disk use, and restart recovery time.

Do not calculate cost if token usage or the historical pricing snapshot is missing. Do not call model-reported success “task accuracy.” Do not call shell-obtained unless independent verification evidence exists.
