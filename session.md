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
- **Phase 0 (OSS foundation): DONE (files authored, not yet committed).** LICENSE
  (Apache-2.0), NOTICE, README, CONTRIBUTING, SECURITY, root `.gitignore` /
  `.dockerignore` / `.env.example` created.
- **Phase 1 (Docker packaging): FILES DONE, RUNTIME UNVERIFIED.** `Dockerfile`
  (orchestrator + hexstrike), `docker-compose.yml`, `docker-compose.test.yml`,
  `scripts/smoke-test.sh` created. **Not built/run — Docker is not installed on
  this dev machine**, so the Phase-1 "one end-to-end engagement" milestone is
  NOT yet met.
- Plans live in `pentest-agents/.claude/plan/`. Governing plan:
  `open-source-docker-release.md`.

## Next Steps (in order)
1. On a machine **with Docker**: `docker compose -f docker-compose.yml -f docker-compose.test.yml up --build`,
   then run `scripts/smoke-test.sh` → confirm ONE engagement completes against the
   bundled Juice Shop. This is the Phase-1 gate.
2. Decide the **publish repo structure** (currently root is not a git repo;
   `pentest-agents/` and `hexstrike-ai/` are separate nested repos). Recommended:
   umbrella repo with HexStrike as a pinned submodule/fork. Then make the first
   commit. (Deferred deliberately — it is a publishing decision.)
3. Phase 2 (correctness refactor): kill `api.py` global `_store`, fix
   `asyncio.run` in `mcp_client.py`, `AsyncSqliteSaver`, budget guard.
4. Phase 3 (scope hardening + consent), then Phase 4 (10× READY gate).

---

## Session Log

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
