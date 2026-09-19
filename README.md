# Threshold

**An LLM-driven, human-in-the-loop penetration-testing orchestrator you run on your own machine.**

Threshold coordinates five AI agents (recon → exploit → post-exploit → analysis →
report) over a large toolbox of real security tools (via [HexStrike](https://github.com/0x4m4/hexstrike-ai)),
pausing for **your approval before every stage**. It is LLM-agnostic (Google
Gemini free tier by default, or Anthropic Claude) and ships as a Docker Compose
stack so anyone can install and run it locally.

> ## ⚠️ Authorized use only
> Threshold actively scans and attacks whatever target you point it at. **Only
> use it against systems you own or have explicit, written permission to test.**
> Unauthorized scanning or exploitation is illegal in most jurisdictions. By
> running Threshold you accept sole responsibility and all liability for its
> actions. See [SECURITY.md](SECURITY.md) and the consent gate.

---

## Status

**Pre-release — under active development.** Phases 0–1 (open-source foundation +
Docker packaging) are authored; the end-to-end run has **not yet been validated**
(see [`session.md`](session.md) for the live status and
[`pentest-agents/.claude/plan/open-source-docker-release.md`](pentest-agents/.claude/plan/open-source-docker-release.md)
for the roadmap). Do not treat it as production-ready until the Phase 4 validation
gate (10× end-to-end + concurrency/restart/budget/scope) passes.

## Requirements

- **Docker** + Docker Compose v2
- A free **Google AI Studio API key** (https://aistudio.google.com/apikey) — no
  card required — or an Anthropic API key.
- ~a few GB of disk for the tool image on first build.

## Quickstart (try it against the bundled target)

```bash
# 1. Configure
cp .env.example .env
# edit .env and set GOOGLE_API_KEY=...

# 2. Bring up the stack + a deliberately vulnerable target (OWASP Juice Shop)
docker compose -f docker-compose.yml -f docker-compose.test.yml up --build

# 3. Open the dashboard
#    http://localhost:8000/dashboard/
#    Start an engagement against:  http://juice-shop:3000/
#    Approve each stage as it is proposed.
```

A scripted single-run smoke test is provided at
[`scripts/smoke-test.sh`](scripts/smoke-test.sh).

## Point it at your own lab

Edit `.env` and set `PENTEST_AGENTS_LAB_CIDR` to the subnet of the authorized
targets you control, then:

```bash
docker compose up --build
```

Threshold refuses any target that does not resolve inside that CIDR.

> **Windows / macOS note:** Docker Desktop runs containers in a Linux VM, so
> `127.0.0.1` inside a container is **not** your host machine. To scan something
> on your host, expose it on a reachable IP or run it as a Compose service (that
> is how the bundled Juice Shop target works). This is why the default authorized
> range targets the Docker network, not loopback.

## Architecture

```
┌────────────────────────┐        MCP (stdio)        ┌──────────────────────────┐
│  orchestrator (thin)   │  hexstrike_mcp.py adapter │  hexstrike (fat)         │
│  FastAPI + LangGraph   │ ───────────────────────▶ │  Flask REST + CLI tools  │
│  5 agents + web UI     │        REST :8888         │  (nmap, sqlmap, nuclei…) │
└──────────┬─────────────┘                           └──────────────────────────┘
           │ durable state + reports on a Docker volume
           ▼
     threshold-data (SQLite* + reports)      * durable state lands in Phase 2
```

- **orchestrator** — the app: agents, approval gate, dashboard. Holds engagement
  state in-process today (single engagement); Phase 2 adds durable, concurrent,
  id-addressed engagements.
- **hexstrike** — the tool backend, built on Kali. `HEXSTRIKE_TOOLSET=curated`
  (default) installs a focused tool subset; `full` installs the whole Kali set.
- Per-role tool scoping is enforced in code (`mcp_client.py`), not by prompting.

## Configuration

See [`.env.example`](.env.example). Key variables:

| Variable | Purpose |
|---|---|
| `GOOGLE_API_KEY` / `ANTHROPIC_API_KEY` | LLM provider credential |
| `PENTEST_AGENTS_MODE` | `dev` (cheap/fast model) or `eval` (stronger) |
| `PENTEST_AGENTS_LAB_CIDR` | The authorized target scope (fail-closed) |
| `HEXSTRIKE_TOOLSET` | `curated` (smaller image) or `full` |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security policy: [SECURITY.md](SECURITY.md).

## License

Threshold is licensed under the [Apache License 2.0](LICENSE). It bundles
[HexStrike AI](https://github.com/0x4m4/hexstrike-ai) (MIT) and installs
third-party CLI tools that each carry their own upstream licenses — see
[NOTICE](NOTICE).
