# Threshold Implementation Plan

Target: take Threshold from "core pipeline works and is live-tested" to "pre-release complete," and add the evaluation/benchmark harness that backs the paper's claims.

This plan is written for Claude Code. It is organised as phases with goals and acceptance criteria, not line-by-line steps. Each phase ends at an acceptance gate; do not advance past a gate until every item under it is green.

Snapshot this plan was written against: HEAD `e03f7b8` (2026-10-04), 498 tests passing, ruff clean.

---

## How to use this plan

1. Read `PROJECT_CONTEXT.md` and `CODEBASE_ANALYSIS.md` in full before writing any code. They are the source of truth for the current state; where they disagree with the code, trust the code and `git log`.
2. Work the phases in order. The ordering is deliberate: cheap reliability fixes first, then the two safety gaps, then the evaluation harness, then the formal validation gate, then docs.
3. Treat each phase as one focused change set. Prefer one commit per phase with a short journal entry in `session.md`.
4. At every acceptance gate, `pytest -q` must pass and `ruff check .` must be clean. New code ships with its own tests.
5. If a decision is genuinely ambiguous (see "Decisions to confirm" at the end), stop and ask the maintainer rather than guessing. This is security tooling; a wrong assumption in the safety layer is not a cosmetic bug.

---

## Ground rules (non-negotiable)

- **Authorized use only.** The safety layer is a guardrail, not authorization. Nothing in this plan weakens it.
- **Safety controls may only be strengthened, never bypassed,** including to make a test or a benchmark run pass. If a safety check blocks a benchmark target, fix the target or the scope config, never the check.
- **Preserve the honesty property.** Findings come from real tool output or are reported as absent. Never let a change allow a fabricated finding to pass downstream.
- **Preserve the LLM-agnostic seam.** No change may hard-code a single provider. All five providers (`claude`, `gemini`, `groq`, `openrouter`, `openai`) stay behind the `LLMProvider` protocol.
- **Scope and consent are server-side only.** Never read an authorized scope, a pinned IP, or a consent record from a client request.
- **Rebuild, then verify the running image.** After any code change, recreate the affected container (`docker compose ... up -d --force-recreate <svc>`), then confirm the running image matches the tagged image before testing. The stale-image footgun has already burned this project once.
- **Windows runners:** Docker Desktop must be up; prefix `docker exec` with `MSYS_NO_PATHCONV=1`.

---

## Scope of this plan

In scope:
- Recon reliability and scope-in-prompt hardening (open items 5 and 6)
- Phase 3c: DNS-rebinding resolve-and-pin (open item 1, the top safety gap)
- Phase 3d: server-side consent gate (open item 2)
- Evaluation and benchmark harness: success rate, time-to-shell, task-completion accuracy, with baselines
- The repo's Phase 4 validation gate and an unattended `smoke-test.sh` pass (open items 3 and 4)
- Documentation refresh (open item 7)

Explicitly out of scope for this plan (future work, do not start without a new plan):
- GUI/screenshot (non-textual) input handling
- New or deeper post-exploitation modules beyond what exists
- A memory-store redesign

---

## Phase 0: Preflight and baseline

**Goal.** Establish a known-good starting point so later changes are attributable.

**Work.**
- Bring the stack up with the test overlay against Juice Shop and confirm one full engagement runs end to end through all five stages with approvals.
- Run `pytest -q` and `ruff check .` and record the exact pass count.
- Confirm the running orchestrator and hexstrike images match their tags.

**Acceptance gate.**
- Baseline test count recorded and matches the snapshot (or the delta is explained).
- One live end-to-end engagement completes with status `done`.
- Clean `ruff`.

---

## Phase 1: Recon reliability and scope-in-prompt hardening

Covers open items 5 (recon prompt names the full CIDR; models have scanned the whole `/12`) and 6 (recon made zero tool calls and reported missing output).

**Goal.** Make the recon stage reliably call tools and never induce a whole-range scan from the prompt.

**Approach.**
- In the recon agent prompt (`agents/recon.py`), state only the specific target, never the full authorized CIDR. The authorized scope stays server-side in the safety layer; the model does not need it and must not be handed it. This is the cheap fix and should land first.
- For tool-calling reliability, add a bounded retry on the tool-assisted step when a tool-bearing stage produces zero tool calls: re-prompt once with an explicit instruction to call at least one tool, and if it still makes none, record an honest "no tool calls made" outcome and route to re-plan rather than silently continuing. Do not fabricate findings to fill the gap.
- Capture enough structured telemetry on recon runs (which provider, tool-call count, parse outcome) to tell a model/tool-binding problem from a prompt problem later. This also feeds Phase 4.

**Acceptance gate.**
- The recon prompt contains the target but not the authorized CIDR (assert in a test).
- A simulated "LLM returns no tool calls" path re-prompts once, then routes to re-plan, and never emits a fabricated finding (unit test).
- A live recon run on Juice Shop issues at least one tool call and produces a typed result.
- `pytest` green, `ruff` clean.

---

## Phase 2: DNS-rebinding resolve-and-pin (Phase 3c)

The top safety gap. Today `safety.assert_in_scope` resolves the hostname at check time, but tools re-resolve at execution time, so a rebinding domain can pass the check and then point tool execution at an out-of-scope or internal address. The fix is the standard resolve-once, validate-all, pin pattern.

**Goal.** Close the time-of-check-to-time-of-use window so every tool in an engagement acts only on the exact IP that was validated, with no second resolution.

**Recommended approach.**
1. **Resolve once, validate every answer.** Change the scope check so it resolves the target hostname a single time and validates *every* returned A/AAAA record against the authorized scope. If any resolved address is out of scope, private, or otherwise dangerous, refuse the whole engagement (split-horizon defense: one bad answer kills it). An IP-literal target needs no pin; an unresolvable host is refused.
2. **Pin at engagement creation.** Store the single validated IP as a `pinned_ip` on the engagement in `state.py` and the engagements table, written once when the engagement is created. It is server-side only and immutable for the life of the engagement. Never re-resolve during the engagement.
3. **Enforce the pin where tools run.** The tools execute in the hexstrike container, so the pin must travel there and be enforced at execution. Use defense in depth, not a single mechanism:
   - Pass the pinned IP to tools that target by address (most network tools) instead of the hostname.
   - For tools that need the hostname (web tools needing Host header, TLS SNI, or vhost routing), inject a per-engagement hostname-to-pinned-IP mapping that libc-resolving tools will honor (for example a scoped hosts-file entry in the hexstrike container), plus tool-specific resolve flags where available.
   - As a backstop for tools that run their own resolver, re-validate at execution time in the hexstrike MCP client: before a tool call, confirm the target host still maps only to the pinned IP; if it resolves to anything else, refuse the call. This closes the window even if a tool would otherwise re-resolve.
4. **Fail closed everywhere.** Missing pin, pin mismatch, or resolution drift refuses the tool call with a clear error code, consistent with the existing `SCOPE_VIOLATION` / `MALFORMED_TARGET` shapes in `api.py`.

**Acceptance gate.**
- Unit tests cover the four resolution outcomes: all-safe IPs pin, any-dangerous answer refuses, IP literal skips the pin, unresolvable host refuses.
- A rebinding simulation (resolution returns a safe IP at check time and a different IP at execution time) results in a refused tool call, not a connection to the second IP.
- The pin is written once and never mutated; a test asserts no re-resolution happens during an engagement.
- The existing scope and `MALFORMED_TARGET` tests still pass; the vulnweb hard-pin workaround in the test overlay can be removed or documented as redundant.
- `pytest` green, `ruff` clean.

---

## Phase 3: Server-side consent gate (Phase 3d)

Covers open item 2. The per-stage approval gate answers "proceed now." The consent gate answers a different, stronger question up front: "is the operator authorized to test this scope at all," recorded and enforced server-side before anything touches the target.

**Goal.** No engagement may run any tool-bearing stage without a valid, server-side, immutable consent record bound to its exact scope.

**Recommended approach.**
- Require an explicit operator consent to start an engagement: the operator acknowledges the authorization statement and the exact target/scope, server-side. Validate and store this as an immutable, timestamped consent record in the engagements table, bound to the engagement id and the resolved scope.
- Enforce it as a precondition for any tool execution (recon/exploit/post_exploit). If the consent record is missing, expired, or its scope does not match the engagement's scope, refuse before the first tool runs, with a dedicated error code.
- Keep it strictly server-side, like the scope check. A client must not be able to fabricate or supply a consent record.
- Keep it distinct from and additional to the approval gate. Both are required: consent once up front, approval at each stage.

**Acceptance gate.**
- Starting an engagement without consent is refused before any tool runs (test).
- A consent whose scope does not match the engagement's scope is refused (test).
- The consent record is immutable and timestamped; an attempt to mutate it is refused (test).
- Consent cannot be supplied or overridden from a client request (test).
- `pytest` green, `ruff` clean.

---

## Phase 4: Evaluation and benchmark harness

This is the paper's measurable contribution: success rate, time-to-shell, and task-completion accuracy, against a manual and a single-agent baseline. Design it so results are reproducible and externally comparable.

**Goal.** A repeatable harness that runs Threshold against a fixed target set and reports the three metrics with per-stage breakdowns and baseline comparisons.

**Recommended approach.**
- **Target set.** A fixed, version-pinned set of intentionally vulnerable lab targets. Start from what is already wired: Juice Shop and the authorized vulnweb practice sites. Each target carries a manifest of expected milestones (see below). Confirm the final target list with the maintainer (see "Decisions to confirm").
- **Metrics (define them precisely and record all three per run):**
  - *Success rate:* fraction of targets on which the engagement reaches the target's defined objective (for example a confirmed shell or a captured flag).
  - *Time-to-shell:* wall-clock from engagement start to the first confirmed shell, where applicable. Reuse the existing shell-verification logic from the exploit stage so a "shell" means the same thing the pipeline already means.
  - *Task-completion accuracy:* fraction of the target's defined milestones that were hit. Model milestones on the established approach: per-target *command milestones* (specific actions expected) and *stage milestones* aligned to the pipeline (recon, exploit, post_exploit, analysis, report), so results are comparable to published benchmarks rather than bespoke.
- **Runner.** A script or module that starts N engagements per target with a scripted, reproducible approval policy (a non-interactive approver that auto-approves or follows a fixed policy, so runs are deterministic and unattended), records metrics to a structured results file (JSON or CSV), and tolerates per-run failure without aborting the batch.
- **Baselines.** Run the same target set under (a) a single-agent or direct-LLM mode as the automated baseline, and (b) a recorded manual-timing baseline, so the speed-and-efficiency claim is a comparison, not an assertion. The human-in-the-loop configuration is Threshold's own mode; report it against both baselines.
- **Reproducibility.** Pin target versions and model tiers, record the provider and model per run, and make the harness re-runnable to produce a comparable results file. Run it only against the authorized lab scope; the safety layer, pin, and consent gate all stay in force during evaluation.

**Acceptance gate.**
- The harness runs unattended end to end over the target set and writes a structured results file with all three metrics plus per-stage breakdown.
- Milestone manifests exist for every target and are version-pinned.
- At least one baseline (single-agent/direct-LLM) runs through the same harness for comparison.
- A documented command reproduces an evaluation run.
- `pytest` green, `ruff` clean.

---

## Phase 5: Validation gate and unattended smoke test

Covers open items 3 (the repo's Phase 4 validation gate) and 4 (a clean `scripts/smoke-test.sh` pass). This is the gate between "works in testing" and "pre-release done."

**Goal.** Prove the system holds up under repetition and stress, and record a clean unattended smoke test.

**Work.**
- Run the validation gate: 10x end-to-end engagements plus concurrency, restart, budget, and scope checks. Fix what it surfaces.
- Get `scripts/smoke-test.sh` to a clean unattended pass, now runnable with groq, claude, or openai (it was blocked earlier on Gemini quota).
- Record results (pass counts, timings, any flakes and their resolution) in the journal.

**Acceptance gate.**
- 10x end-to-end runs complete with the expected terminal statuses; no engagement stuck.
- Concurrency, restart, budget, and scope checks pass and are documented.
- `smoke-test.sh` passes unattended at least once on record, with the provider noted.
- `pytest` green, `ruff` clean.

---

## Phase 6: Documentation refresh

Covers open item 7.

**Goal.** Docs match the code as of this work.

**Work.**
- `README.md`: list all five providers; add the rebuild/recreate step to the quickstart.
- `session.md`: refresh the "Current State" block; add journal entries for the commits that lack them and for every phase in this plan.
- Update `PROJECT_CONTEXT.md` to reflect 3c, 3d, the evaluation harness, and the validation results.
- Document the evaluation harness: how to run it, the target set and milestone manifests, and how to read the results file.

**Acceptance gate.**
- No doc claims a capability the code lacks or omits one it has (spot-check against the code).
- A new contributor can bring up the stack, run an engagement, and run the evaluation harness from the docs alone.

---

## Definition of done (pre-release complete)

- [ ] Recon no longer receives the full CIDR; recon tool-calling has a bounded-retry-then-replan path.
- [ ] DNS-rebinding resolve-and-pin implemented and enforced across tool execution, with the rebinding simulation test passing.
- [ ] Server-side consent gate enforced before any tool-bearing stage, immutable and scope-bound.
- [ ] Evaluation harness produces reproducible success-rate, time-to-shell, and task-completion-accuracy results with at least one baseline.
- [ ] Validation gate (10x plus concurrency/restart/budget/scope) passed; `smoke-test.sh` clean unattended pass on record.
- [ ] Docs refreshed and accurate.
- [ ] Full test suite green and `ruff` clean at each phase gate.

---

## Decisions to confirm with the maintainer

Surface these rather than assume:
1. **Benchmark target set.** Is Juice Shop plus the authorized vulnweb sites the intended evaluation set, or should specific additional lab targets (for example particular VulnHub or local vulnerable-container images) be included? Each added target needs an authorization confirmation and a milestone manifest.
2. **Consent mechanism form.** Should operator consent be a typed acknowledgment of the authorization statement and scope, or a stronger token-based consent? Both can be server-side and immutable; the choice affects the operator workflow.
3. **Single-agent baseline.** Should the automated baseline be a stripped single-agent mode built inside Threshold, or an external reference such as a published benchmark figure? The former is more directly comparable but is extra build work.
4. **Pin enforcement for self-resolving tools.** Confirm whether the hexstrike container may use a per-engagement hosts-file override, or whether the pin must be enforced purely by passing IPs plus execution-time re-validation. This affects how airtight the pin is for Go-based or custom-resolver tools.

---

## References for the recommended approaches

- DNS-rebinding resolve-and-pin (the TOCTOU pattern and fix): see the write-ups on pinning the validated IP via a connection-level pin and refusing on any dangerous resolved answer, e.g. the ContextForge DNS TOCTOU advisory and the CURLOPT_RESOLVE pinning ADR.
- Benchmark design and milestone-based scoring: AutoPenBench (Gioacchini et al.), which defines command and stage milestones and reports 21% success for autonomous agents versus 64% for human-assisted agents, a useful comparison point for Threshold's human-in-the-loop mode. https://github.com/lucagioacchini/auto-pen-bench
