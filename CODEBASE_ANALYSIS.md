# Threshold — Full Codebase Analysis

Snapshot at HEAD `e03f7b8` (2026-10-04). Working tree: one untracked file (`.claude/settings.json`). Where this document and the code disagree, trust the code and `git log`.

---

## 1. What the project is

An LLM-driven, human-in-the-loop penetration-testing **orchestrator** for authorized security testing. Five AI agents run in sequence — **recon → exploit → post_exploit → analysis → report** — each pausing for operator approval, driving real security tooling through a backend called HexStrike. Self-hosted, ships as a Docker Compose stack.

It is a substantial project: ~11 commits of real, live-debugged engineering. Many bugs were found only by running the live stack, not by inspection.

**Authorized use only.** The safety layer is a guardrail, not a substitute for written authorization to test a target.

---

## 2. Architecture (two-container split)

```
orchestrator (FastAPI + LangGraph, :8000)  ──MCP stdio──▶  hexstrike (Flask REST, :8888)
   5 agents, approval gate, dashboard           hexstrike_mcp.py       real CLI tools (nmap, nuclei, sqlmap, msf…)
         │ bind-mount ./data → /data
         ▼  threshold.db (SQLite checkpoints) · reports/ · chroma/
```

- The "thin" orchestrator (pure Python app logic) is kept separate from the "fat" Kali-based tool image.
- They communicate over MCP; the orchestrator spawns `hexstrike_mcp.py` as a subprocess that bridges to the REST backend.
- Tool access is scoped **in code** (`ROLE_TOOLS` allowlist per role in `tools/mcp_client.py`), not by prompting.
- State persists to a bind-mounted `./data` volume, so it survives container restart/recreation.

---

## 3. Tech stack (what is actually used)

### Orchestrator (`pentest-agents/requirements.txt`, pinned exactly)

| Package | Version | Role |
|---|---|---|
| `langgraph` | 1.2.11 | Pipeline state machine |
| `langgraph-checkpoint-sqlite` | 3.1.1 | Durable checkpointing |
| `aiosqlite` | 0.22.1 | Async SQLite driver |
| `langchain-anthropic` | 1.7.2 | Claude provider |
| `langchain-google-genai` | 4.4.0 | Gemini provider |
| `langchain-groq` | 1.1.3 | Groq provider |
| `langchain-openai` | 1.6.2 | OpenAI + OpenRouter providers |
| `langchain-mcp-adapters` | 0.3.2 | MCP tool bridge |
| `chromadb` | 1.5.9 | Memory store |
| `pydantic` | 2.13.5 | State model |
| `Jinja2` | 3.1.6 | Report rendering |
| `fastapi` | 0.141.1 | API + dashboard host |
| `uvicorn[standard]` | 0.53.0 | ASGI server |
| `python-dotenv` | 1.2.3 | Env loading |
| `pytest` / `pytest-cov` | 9.1.1 / 7.1.0 | Tests |
| `httpx` | 0.28.1 | Test client |
| `ruff` | 0.16.8 | Lint |

### HexStrike backend (`hexstrike-ai/requirements.txt`)

- `flask`, `requests`, `psutil`, `fastmcp` — core
- `msgpack` — **new**, the Metasploit RPC wire format (`msfrpc_client.py`)
- `beautifulsoup4`, `selenium`, `webdriver-manager` — web automation
- `aiohttp`, `mitmproxy` — networking / proxy
- `pwntools`, `angr==9.2.120` (exact pin — avoids a documented 5-minute pip backtrack), `bcrypt==4.0.1` — binary analysis
- The 150+ actual security tools come from the Kali apt layer in the Dockerfile, not pip. `HEXSTRIKE_TOOLSET=curated|full` controls which get installed.

### Dashboard

Vanilla HTML/CSS/JS, no framework: `web/index.html`, `web/app.js`, `web/styles.css`.

---

## 4. The pipeline

### Stages (`state.py`)

```python
Stage = Literal["recon", "exploit", "post_exploit", "analysis", "report"]
STAGE_ORDER = ["recon", "exploit", "post_exploit", "analysis", "report"]
```

| Stage | Tool access | Purpose |
|---|---|---|
| recon | Yes (~44 tools) | Open ports, services, subdomains |
| exploit | Yes | Attempt exploitation; verifies a claimed shell exists in tool output |
| post_exploit | Yes | Only if a shell was obtained; per-command session scope guard |
| analysis | None | Reasons over collected findings |
| report | None | Writes a Markdown report from state (Jinja2) |

Each stage is wrapped in `_safe_stage_node` (`coordinator.py`): an unhandled exception halts the engagement cleanly (`halted_reason`) rather than leaving it stuck.

### Approval gate

After each stage the graph interrupts for an operator decision: `approved`, `rejected`, or `revise`. `approved` on the final stage → `done`; `revise` → re-run (increments `replan_count`); non-final `approved` → next stage.

### Tool-assisted step (`agents/_common.py`)

Shared loop for recon/exploit/post_exploit: LLM chooses tools → tools execute for real (with timeouts) → LLM synthesizes a typed Pydantic result. Missing tool output is reported honestly, never fabricated; failure raises `FindingsParseError` (routes to re-plan).

---

## 5. What is present (and working)

- **Five-provider LLM seam** — `claude`, `gemini`, `groq`, `openrouter`, `openai` (gpt-5-mini dev / gpt-5 eval). One `LLMProvider` protocol; operator-selectable per engagement via API and dashboard dropdown.
- **Durable, concurrent engagements** — id-addressed (engagement id == LangGraph thread_id), AsyncSqliteSaver checkpoints in WAL mode, orphan reconciliation on startup. Verified to survive container recreation.
- **Safety layer** — fail-closed scope check: comma-separated CIDR allowlist, all entries validated up front, DNS multi-resolution refused, empty scope refused, URL userinfo rejected (`422 MALFORMED_TARGET`). Server-side only.
- **Budget/runaway guards** — max replans (3), wall-clock ceiling (3600s), max LLM calls (40), per-LLM-call timeout (120s hard halt), per-tool-call timeout (300s swallowed). Orphan-process reaping after a real zombie-`masscan` incident.
- **Live Metasploit sessions (newest commit)** — persistent `msfrpcd` (bound to 127.0.0.1, per-container password) with `msf_session_{list,run_command,kill}` MCP tools and a parsed session table. `metasploit_run` no longer hangs the full 300s. Exploit stage downgrades a claimed shell not present in tool output.
- **Test suite** — 498 passing per the last commit (raw `def test_` count ~146; the dispatch-matrix and status-endpoint tests are heavily parametrized). `ruff` clean. Covers safety, coordinator, registry, db, budget, API, all providers, MCP client, per-tool dispatch matrix, MSF session parser.

---

## 6. What is lacking / open

1. **Phase 3c (DNS-rebinding resolve-and-pin)** — *not implemented*. Targets are resolved at check time, not pinned for execution. The most important safety gap; it is why vulnweb's IPs are hard-pinned in the test overlay as a workaround.
2. **Phase 3d (server-side consent gate)** — designed, not built.
3. **Phase 4 validation gate** — the 10× end-to-end + concurrency/restart/budget/scope proof has never been run. The gate between "works in testing" and "pre-release done."
4. **Unattended `scripts/smoke-test.sh` pass** — never recorded clean. Was blocked on Gemini quota; now runnable with groq/claude/openai.
5. **Recon prompt over-broad scope** — the prompt names the full CIDR alongside the target; models have twice scanned the whole `/12`. Cheap fix, not yet done.
6. **Recon tool-calling reliability** — in a live run Gemini made zero tool calls twice and reported "Tool output is missing, empty, or unusable". Never root-caused; extra providers are partly a hedge.
7. **Documentation drift** — `README.md` lists only Gemini/Claude; `session.md` "Current State" block is self-admittedly stale; the two newest commits have no journal entry. `PROJECT_CONTEXT.md` is the current snapshot.

---

## 7. Status summary

| Area | Status |
|---|---|
| Core pipeline (5 stages + approval) | Working, run end-to-end live |
| Durable / concurrent state | Working, live-verified |
| LLM providers (5) | Wired, all present |
| Live MSF sessions | New, landed `e03f7b8` |
| Safety scope check | Working; DNS-rebind gap open |
| Budgets / timeouts / reaping | Working |
| Tests | 498 passing, ruff clean |
| Docker daemon (at time of writing) | Down — start Docker Desktop to run |
| Phase 3c / 3d hardening | Not implemented |
| Phase 4 validation | Not started |
| Docs | Stale (except PROJECT_CONTEXT.md and this file) |

**Bottom line:** the hard parts — durable state, provider abstraction, in-code tool scoping, live MSF integration, budget guards — are done and live-tested. What stands between this and "pre-release complete" is the DNS-rebinding fix (3c), the consent gate (3d), running the Phase 4 validation gate, and a documentation refresh. Nothing in the open list is a dead-end; it is the known, planned remainder.

---

## 8. Commit history

| Commit | Summary |
|---|---|
| `e761b52` | Initial: Phase 0–1, OSS foundation + Docker packaging |
| `85be2f2` | Phase 2b (async pipeline) + 2d (replan/wall-clock budget) |
| `506a2dd` | Phase 2a (EngagementRegistry, id-addressed API) + 2c (durable SQLite) + 3 live fixes |
| `7e66e98` | status_for_state correctness, report template fix, smoke-test retry |
| `34edf04` | Groq provider + dashboard picker, Phase 2d Part A, Phase 3a/3b scope hardening |
| `57eb0c5` | Stage-node exceptions halt gracefully |
| `a862f0b` | Dashboard remembers active engagement across reloads |
| `ad170a1` | Dashboard stops showing stale actionable card after completion |
| `6e0a530` | Reap orphaned HexStrike processes on tool timeout |
| `f004d67` | Metasploit added to curated toolset; vulnweb.com authorized |
| `ab98b22` | Per-tool dispatch test matrix, live tool-status panel, OpenRouter provider |
| `e03f7b8` | Live MSF sessions (msfrpcd), OpenAI provider, tool-status & scope fixes |

Authors in history: `Chaitanya Sawant` (local) and `Vansh`.
