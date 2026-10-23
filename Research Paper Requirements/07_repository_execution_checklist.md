# Repository Execution Checklist

This checklist converts the supplied audit into repository work items. Status is based on the project checkout inspected for this requirements package; “present in source” means implemented code, not verified behavior.

## P0 — Evidence before a full-paper Results section

- [ ] Freeze benchmark targets, exact images/digests, isolated scope, reset procedure, expected shell criterion, and per-stage rubric.
- [ ] Finalize the evaluation protocol and matrix, including provider dimension, operator policy, budgets, and exclusions.
- [ ] Run at least 45 main runs (3 targets × 5 repetitions × Manual/Single-agent/Threshold) and 30 minimum ablation runs (3 × 5 × no-gate/no-allowlist), while accounting separately for provider-subset runs if not fully crossed.
- [ ] Execute the complete safety-validation suite with evidence. The current 13-case run is blocked before collection and has zero passes.
- [ ] Run manual and single-agent baselines fairly; the current batch runner supports Threshold only.
- [ ] Independently adjudicate completion and shell; collect raw provider/tool logs and cost/resource data.
- [ ] Generate per-target means, SDs, 95% CIs, paired comparisons/effect sizes, and exclusions from the same registered run IDs.
- [ ] Rewrite the paper’s results and contribution claims only from those generated artifacts.

## P1 — Instrumentation and data quality

- [x] Append-only application telemetry and event-based metric collection are present in source/scripts.
- [x] Batch/environment/resource collection scripts exist; the runner is Threshold-only and requires reset confirmation rather than performing the reset.
- [ ] Confirm complete event coverage on real app executions, including API request, state transition, approvals, provider calls, tools, budgets, process lifecycle, persistence/restarts, concurrency, reports, and resources.
- [ ] Implement or document an equivalent to the requested per-engagement metrics export endpoint. No such API endpoint was confirmed in the current source search.
- [ ] Ensure collection reports unresolved required fields, missing events, invalid event order, and incomplete runs without filling blanks with zero.
- [ ] Add a registered comparison harness for Manual and Single-agent. Preserve exact prompt, schemas, tools, provider/model, scope, budget, and target reset.

## P2 — Specific application hardening and study conditions

- [ ] Inspect/fix the recon prompt so the agent receives only the specific target, not a broader authorized range as a scan suggestion. Add a regression fixture and measure behavior before/after in the authorized lab. The supplied audit reports the bug; repository-only evidence reviewed here does not prove the fix or its absence.
- [ ] Implement a server-side consent/authorization gate or DNS-rebinding protection as the audit recommends; specify threat coverage and dedicated test. The current app does have server-owned scope validation; consent-gate status should be verified separately and not inferred from README language.
- [ ] Add experiment-only no-approval and no-role-allowlist modes behind explicit configuration, isolated-lab safeguards, and telemetry. Current ablation documentation says these switches/runs are absent.
- [ ] Add empty/malformed-output honesty tests, finding severity adjudication, and downstream report propagation evidence.
- [ ] Investigate zero-tool-call recon and broad-range scan behavior from raw prompts/schema/provider/tool logs; record root cause, fix commit, and regression outcome.
- [ ] Validate budget halt, timeout continuation, orphan process termination, durable restart, and concurrent engagements with real process/runtime evidence.

## P3 — Reproducibility and paper artifacts

- [ ] Create `benchmarks/` with target YAML and setup/reset/network documentation.
- [ ] Pin Docker images and Python dependencies; capture exact model/API versions. Current protocol notes mutable `latest` identifiers.
- [ ] Add `scripts/reproduce_paper.sh` that verifies prerequisites and scope and regenerates paper CSV/LaTeX/figures from a registered batch.
- [ ] Add a redacted `docs/incidents/` record only when raw evidence for an actual incident exists. A template exists; no verified incident report was found.
- [ ] Optimize or tier the large recon tool schema only if measured token/free-tier pressure supports it; compare token and parse/tool-call success before and after.
- [ ] Consider an optional dry-run/simulation mode with deterministic fixtures, clearly labeled simulated events, and no presentation of mock output as a live finding.
- [ ] Redraw the architecture figure as editable vector artwork.
- [ ] Add code availability and responsible-use statements tied to the evaluated commit.
- [ ] Verify all cited references against primary publication records and fix the audit’s flagged bibliography entries.

## Exit criteria for paper readiness

The full-evaluation route is ready only when all of the following are true:

1. The exact protocol and target images/reset actions are frozen and represented in batch metadata.
2. Every planned run has one complete or explicitly incomplete row, raw events, and traceable evidence; exclusions are documented.
3. Primary outcomes have independent scoring and shell verification; safety suite rows contain actual pass/fail outcomes rather than environment-blocked states.
4. Main baselines use the same scope, targets, reset policy, budgets, tools and model where applicable; ablations alter only the named control.
5. Every table/figure regenerates from repository result files, with N, uncertainty, per-target results, paired tests, effect size, and exclusions.
6. Every manuscript claim maps to implementation evidence or measured rows. Unsupported claims have been removed or explicitly presented as design intent.
7. The evaluated code commit, dependency/image versions, API model versions, benchmark manifest, and reproduction commands are recorded.

Until these gates pass, the project can support a transparent implementation/design description and a bounded retrospective report summary, not the supplied audit’s minimum publishable quantitative evaluation.
