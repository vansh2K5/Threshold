# Threshold — Session Journal

Single source of truth for what has been done across working sessions on this
project (the **Threshold** pentest-agent stack: `pentest-agents/` orchestrator +
`hexstrike-ai/` tool backend).

## How to use this file (concurrency convention)
- **Every session appends one entry** to the `## Session Log` below **before it
  ends**, newest at the top of the log.
- If **multiple sessions run concurrently**, the one that finishes **last** is
  responsible for making sure this file reflects reality — it re-reads the file,
  reconciles any entries added by the others, and refreshes the
  **Current State** / **Next Steps** block at the top.
- Never delete another session's log entry. If two entries conflict, keep both
  and add a short reconciliation note.
- Keep entries factual: what was actually done and verified, not intentions.

---

## Current State  <!-- refreshed by the last session to finish -->
- **Phase 0 (OSS foundation): DONE + COMMITTED.** LICENSE (Apache-2.0), NOTICE
  (HexStrike MIT provenance pinned @ d689933), README, CONTRIBUTING, SECURITY,
  root `.gitignore` / `.dockerignore` / `.env.example` / `.gitattributes`.
- **Phase 1 (Docker packaging): FILES DONE, RUNTIME STILL UNVERIFIED.**
  `Dockerfile`s, `docker-compose.yml` (data bind-mounted to F via `./data`),
  `docker-compose.test.yml`, `scripts/smoke-test.sh`. **Docker is NOW INSTALLED**
  (v29.8.0, Compose v5.5.1) and the daemon **runs**, but no build has been done,
  so the Phase-1 "one end-to-end engagement" milestone is still NOT met.
- **Docker disk location: STILL ON C — action needed.** C is at 90% (~30 GB
  free); F has ~160 GB. Docker's WSL data (`docker-desktop` distro, ~2.3 GB) sits
  on C at `%LOCALAPPDATA%\Docker\wsl\disk\`. Adding `"DataFolder":"F:\\DockerData"`
  to `settings-store.json` did **not** stick — Docker Desktop v29 rewrites that
  file and drops the key. **Must be set via the GUI** (Settings → Resources →
  Advanced → Disk image location → `F:\DockerData`) **before any build**, else the
  image/build cache fills C. `F:\DockerData` already created (empty).
- **Phase 2 (correctness): 2b DONE, 2d PARTIAL — all green (53 passed, ruff clean).**
  - **2b async migration DONE:** killed `asyncio.run()` in `mcp_client.py`
    (`get_tools_for_role` now `async` + double-checked `asyncio.Lock`); provider
    gained `ainvoke`/`astructured`; `_common.run_tool_assisted_step`, all
    tool-using agent nodes (recon/exploit/post_exploit) and `analysis` are async;
    `coordinator.start_engagement`/`resume_with_decision` use `graph.ainvoke`, the
    approval node is async; `api.py` handlers async; `cli.py` wraps one
    `asyncio.run`. `report.py` stays sync (deterministic, no I/O await). Tests
    migrated to `@pytest.mark.anyio` (asyncio backend via new `tests/conftest.py`);
    `test_api.py` stayed sync (TestClient bridges).
  - **2d budget guard PARTIAL:** new `budget.py` (`EngagementBudget.from_env`);
    coordinator enforces `max_replans` (the `replan_count` that was incremented
    but never checked) + a coarse wall-clock ceiling **at each approval gate** →
    sets `PipelineState.halted_reason="halted_max_replans"|"halted_wall_clock"`
    and routes END. New state fields `started_at`, `halted_reason`. Env vars
    `PENTEST_AGENTS_MAX_REPLANS` (3), `PENTEST_AGENTS_MAX_WALL_CLOCK_SECONDS`
    (3600) added to `.env.example`. **Deferred:** per-LLM/-tool-call timeouts +
    `max_llm_calls` counter (needs a counter threaded through the tool loop).
  - **2a (kill `_store` singleton → id-addressed EngagementRegistry): NOT STARTED.**
    Best done with 2c (durability + orphan reconciliation are intertwined).
  - **2c (`AsyncSqliteSaver` durable state): NOT STARTED.** Needs new deps
    `langgraph-checkpoint-sqlite` + `aiosqlite` (not installed) + FastAPI-lifespan
    wiring; best verified against a running app.
- **Git: single repo, commit e761b52 on `main`.** Phase-2b/2d changes are
  **uncommitted** (working tree). **Remote NOT created** (local only).
- **gh CLI installed** (v2.101.0), **not logged in**. Chosen: **Threshold**,
  **PRIVATE**, single-repo vendor.
- Governing plan: `pentest-agents/.claude/plan/open-source-docker-release.md`.

## Next Steps (in order)
1. **[USER] Set Docker disk image location to `F:\DockerData`** via Docker
   Desktop GUI (Settings → Resources → Advanced), Apply & Restart, BEFORE any
   build. (JSON edit doesn't persist on v29.) Optional: let Claude try
   `wsl --manage docker-desktop --move F:\DockerData` instead (small risk).
2. **[USER] `gh auth login`** (type `! gh auth login` here → GitHub.com → HTTPS →
   browser).
3. **[CLAUDE, after 2]** `gh repo create Threshold --private --source=. --remote=origin --push`.
4. **[CLAUDE, after 1]** `docker compose -f docker-compose.yml -f docker-compose.test.yml up --build`
   then `scripts/smoke-test.sh` → one engagement completes vs bundled Juice Shop
   (Phase-1 gate). Expect to fix Kali apt package names on first build.
5. **[CLAUDE] Finish Phase 2:** 2a EngagementRegistry (+ id-addressed API/UI) and
   2c AsyncSqliteSaver together; then 2d per-call timeouts/`max_llm_calls`.
6. Phase 3 (scope hardening + consent) → Phase 4 (10× READY gate).

> Phase-2b/2d code is green but UNBUILT/UNRUN against a live stack — verify with
> the Phase-1 smoke test once Docker disk is on F and the daemon is building.

---

## Session Log

### 2026-09-20 00:11 — Phase 2b (async) + 2d (budget guard, partial)
- **Harness session:** 438ff09b-bf42-4002-9411-f21056dca8bb
- **Worktree:** F:\projects\Mjor-SEM7 (single git repo, branch main)
- **Author:** Claude (Opus 4.8)
- **Resumed from** the prior session's handoff. Verified live env first: Docker
  is now installed + daemon running (was absent last session); gh still not
  logged in; no git remote. User chose (via prompt) to "start Phase 2 code fixes"
  while they handle Docker + `gh auth login`.
- **Docker disk:** created `F:\DockerData`, added `DataFolder` to Docker Desktop
  `settings-store.json` — but Docker Desktop v29 **rewrote the file and dropped
  the key** on start. Data still on C. Flagged to user: use the GUI setting
  before any build. Backup of original settings in session scratchpad.
- **Phase 2b (async migration) — DONE, green:** removed the latent
  `asyncio.run()`-in-a-running-loop crash. provider.py (+`ainvoke`/`astructured`),
  tools/mcp_client.py (`get_tools_for_role` async + `asyncio.Lock`),
  agents/_common.py, agents/{recon,exploit,post_exploit,analysis}.py (async),
  coordinator.py (`ainvoke`, async approval node, widened `NodeFn`), api.py
  (async handlers, `_store` kept for now), cli.py (`asyncio.run` wrapper). Tests
  migrated to anyio (new tests/conftest.py; `test_api.py` stayed sync via
  TestClient). report.py intentionally left sync.
- **Phase 2d (budget/replan guard) — PARTIAL, green:** new `budget.py`; coordinator
  enforces `max_replans` + coarse wall-clock at each approval gate → `halted_reason`
  on PipelineState (new fields `started_at`, `halted_reason`); routing edge ends
  the run on halt. Added one test (`test_replan_budget_halts_the_run_after_max_replans`).
  `.env.example` documents the two new vars. Deferred: per-call timeouts +
  `max_llm_calls`.
- **Verification:** `pytest -q` → **53 passed, 1 deselected**; `ruff check` clean.
  No live-stack run (Docker not building yet) — code is green but unproven E2E.
- **Files touched (Phase 2):** pentest_agents/{llm/provider,tools/mcp_client,
  agents/_common,agents/recon,agents/exploit,agents/post_exploit,agents/analysis,
  coordinator,api,cli,state,budget}.py; tests/{conftest,test_agents,
  test_agents_common,test_coordinator,test_mcp_client,test_integration}.py;
  .env.example; session.md. Docker settings-store.json (reverted by Docker).
- **Handoff:** 2a (EngagementRegistry) + 2c (AsyncSqliteSaver) still to do,
  ideally together; then 2d per-call timeouts. Nothing committed yet.

### 2026-09-19 13:32 — Phase 0–1 execution
- **Harness session:** 937dc4a7-607f-46b5-9b41-7437568a2160
- **Worktree:** F:\projects\Mjor-SEM7  (root; not a git repo)
- **Author:** Claude (Opus) + Antigravity audit
- **Summary:**
  - Reviewed & superseded the SaaS `production-readiness.md` with a self-hosted
    open-source plan (`open-source-docker-release.md`).
  - Executed Phase 0 (OSS foundation) and Phase 1 (Docker packaging) — authored
    all artifact files.
  - Created this `session.md` journal + concurrency convention.
- **Files touched:** session.md, LICENSE, NOTICE, README.md, CONTRIBUTING.md,
  SECURITY.md, .gitignore, .dockerignore, .env.example, docker-compose.yml,
  docker-compose.test.yml, scripts/smoke-test.sh, pentest-agents/Dockerfile,
  hexstrike-ai/Dockerfile, hexstrike-ai/.gitignore
- **Status / Handoff:** Docker NOT installed here → Docker artifacts are authored
  but UNBUILT/UNVERIFIED. Phase-1 milestone (one real engagement) still pending a
  Docker-capable machine. Repo git-init/first-commit deferred (publish-structure
  decision). No production Python code changed (that is Phase 2+).
- **Audit note:** Phase-5 multi-model audit attempted via Antigravity twice.
  Both runs failed to return a usable review (headless permission denial, then
  the wrapper deleted its output on exit). Claude self-audited the Docker/OSS
  artifacts instead and applied one concrete fix: the Kali apt package for
  ExifTool is `libimage-exiftool-perl`, not `exiftool`
  (hexstrike-ai/Dockerfile). Codex remained unavailable (not installed).
- **F-drive update:** Docker found NOT installed (no docker.exe, com.docker.service
  missing, WSL has no distro). gh CLI also absent. Changed docker-compose.yml to
  bind-mount engagement data to ./data (F:\projects\Mjor-SEM7\data) instead of a
  named volume, so reports/state stay on F. Big image/build storage still needs
  Docker Desktop disk-image-location set to F at install time (user action).
- **GitHub init:** Vendored HexStrike (moved its and pentest-agents nested .git
  to F:\projects\.threshold-vendored-gitdirs), added .gitattributes (LF), made
  the root a single git repo, first commit e761b52 on main (85 files, no
  secrets). Repo is LOCAL only so far. Chosen: PRIVATE repo, single-repo vendor.
  Remote creation pending: gh CLI being installed, then user must `gh auth login`.
- **gh CLI:** installed OK — v2.101.0 at `C:\Program Files\GitHub CLI\gh.exe`,
  not logged in yet.
- **Session end:** user paused at ~91% usage. No further work performed. Two
  handoffs open for the user (install Docker w/ F disk location; `gh auth login`);
  Claude to create+push the private remote and run the Phase-1 smoke test once
  unblocked. Nothing proceeds until the user says so.
