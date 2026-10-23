# Manuscript Structure and Editorial Requirements

The items in this document come from the supplied draft audit. The editable paper was not found in the project files reviewed, so verify its exact section numbers, wording, figure, tables, and references against the source manuscript before making revisions.

## Recommended full-evaluation structure

1. Introduction: problem, narrow research gap, contributions, responsible-use summary, paper organization.
2. Related Work: compare relevant work on human involvement, access control, evaluation setting, and post-exploitation coverage; avoid unsupported limitation labels.
3. Threat Model: adversary goals/capabilities, prompt injection through tool output, hallucinated commands/findings, scope escape, resource exhaustion, trust boundaries, and explicitly out-of-scope threats.
4. Design Goals and System Design: state goals (for example, fail-closed scope, least privilege per role, human veto at capability transitions, bounded execution, evidence-grounded reporting) and map each to a mechanism and validation test.
5. Implementation: concrete software, state machine, APIs, provider interfaces, tool dispatch, persistence, dependencies and version pins. Separate implementation details from intended design.
6. Evaluation Methodology: targets, conditions, providers, matrix, reset, budgets, approval protocol, scoring, shell verification, data collection and statistics.
7. Results and Discussion: only measured data; primary outcomes, per-target comparisons, ablations, safety tests, provider behavior, failure modes, incidents, and operator observations tied to counts/evidence.
8. Threats to Validity: target representativeness, operator effects, small sample, lab-only setting, model/provider drift, scoring/review bias, missingness and infrastructure exclusions.
9. Ethics and Responsible Use: explicitly state authorization and lab containment; discuss target handling and disclosure process.
10. Conclusion, Code Availability and Reproducibility: evaluated commit, artifact location, reproducibility instructions, limitations and next work.

This is a template, not evidence that the current manuscript already has or lacks each section.

## Required claim edits

- Contribution #4 must describe an achieved, measured result if the paper is positioned as an evaluation. Use a precise statement with outcome, comparison, N, and uncertainty only after the data exist. Until then, call the benchmark/evaluation plan a planned artifact, not a contribution demonstrating efficacy.
- Narrow the gap to a defensible question: whether code-enforced per-stage human approval plus per-role tool restrictions changes safety outcomes and human/compute cost under a controlled, same-target comparison. Do not assert no prior framework does this unless the literature review supports it.
- Move anecdotes currently called “Observations from Live Runs” into Discussion and link each to a run, quantified frequency, and evidence. Unverified stories should be described as design motivation or omitted.
- Replace limitations that merely confess no evaluation with completed-study limitations only after the study is done. If not done, choose a work-in-progress venue and say so clearly.
- Add an ethics/responsible-disclosure paragraph that states tests use only owned/explicitly authorized lab targets and describes data handling. The repository README already warns that the tool actively scans/attacks and is for authorized use; the paper needs its own statement.
- Add a code/artifact availability statement naming the exact evaluated commit and release/artifact location. Do not cite a floating branch as the evaluated version.

## Style and consistency pass

Check all items reported by the audit:

- Correct “allowist” to “allowlist.”
- Use “post-exploitation” in prose and `post_exploit` only for code/stage identifiers.
- Repair missing spaces after section/subsection labels (`III. SYSTEM ARCHITECTURE`, `IV. PROPOSED SYSTEM`, `D. HTTP API`, `A. Provider Interface`, etc.) and remove merged/duplicated headings.
- Keep design description present tense and implementation/report of completed work past tense, consistently.
- Remove unnecessary first-person phrasing and use “the framework” rather than “our framework” if the chosen style is impersonal.
- Trim abstract to the venue limit (audit recommends about 200 words); define “large language model (LLM)” and “Open Worldwide Application Security Project (OWASP)” on first use if retained. Avoid unexplained abbreviations.
- Refine Index Terms toward specific searchable concepts, for example human-in-the-loop security, LLM agent orchestration, safety-gated automation, penetration testing, and tool allowlisting.
- Update the Introduction’s paper-organization paragraph to match actual final sections; do not say “evaluation plan” when the section reports results.

## Figure and tables

Redraw Figure 1 as vector artwork (TikZ, draw.io SVG/PDF, or equivalent) with consistent typography and explicit arrows for agent-to-tool calls, state flow, and approval gates. Preserve source/editable form and export a publication-quality PDF/SVG. Do not use a low-resolution UI screenshot as the architecture diagram.

Every results table/figure must be generated from the stored batch data, identify N and missing/excluded runs, report uncertainty, and be regenerable with the repository scripts. Keep per-target results; do not show only pooled averages. Do not use the retrospective report table as a substitute for experimental comparison.
