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

## Quickstart

```bash
# 1. Configure
cp .env.example .env
# edit .env and set GOOGLE_API_KEY=...

# 2. Bring up the app; the local target stays off until you enable it
docker compose up --build -d

# 3. Open the dashboard
#    http://127.0.0.1:8000/dashboard/
```

In **Authorized IP scope**, enter the IP address or CIDR ranges you own or have
permission to assess, then save. The setting is stored in the local SQLite data
directory and is used by the server for every new engagement. Changing scope is
blocked while an engagement is active. The app binds to `127.0.0.1` so the scope
editor is not exposed to other devices on your network.

### Optional isolated web lab

The OWASP Juice Shop target is disabled by default. Enable it when you want a
local practice target:

```bash
docker compose --profile lab up -d juice-shop-web
```

From the host, open `http://127.0.0.1:3000`. In Threshold, first add
`172.30.255.10/32` to the authorized scope, then enter `172.30.255.10` as the
target. Juice Shop lives on an internal Docker network without outbound access.
A small Nginx proxy publishes its web page on host loopback only.

Turn the lab off with:

```bash
docker compose --profile lab stop juice-shop-web juice-shop
```

## Point it at your own lab

Set the scope in the dashboard to the IP address or CIDR range of targets you
control. You can also use `PENTEST_AGENTS_LAB_CIDR` in `.env` to seed the scope
on a fresh install; once saved in the dashboard, the persisted setting takes
precedence:

```bash
docker compose up --build
```

Threshold refuses any target that does not resolve inside that CIDR.

> **Windows / macOS note:** Docker Desktop runs containers in a Linux VM, so
> `127.0.0.1` inside a container is **not** your host machine. To scan a service
> running on your host, use a host IP reachable from Docker and include that IP
> in the dashboard scope. Host firewalls may need to allow the connection. The
> optional Juice Shop service avoids that routing issue by running on the
> private Compose network.

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
| `PENTEST_AGENTS_LAB_CIDR` | Initial authorized scope (dashboard setting persists afterward) |
| `HEXSTRIKE_TOOLSET` | `curated` (smaller image) or `full` |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security policy: [SECURITY.md](SECURITY.md).

## License

Threshold is licensed under the [Apache License 2.0](LICENSE). It bundles
[HexStrike AI](https://github.com/0x4m4/hexstrike-ai) (MIT) and installs
third-party CLI tools that each carry their own upstream licenses — see
[NOTICE](NOTICE).
