# Contributing to Threshold

Thanks for your interest. Threshold is an offensive-security tool, so
contributions carry extra responsibility — please read this before opening a PR.

## Ground rules

- **Authorized use only.** Do not include, reference, or test against any target
  you are not authorized to test. PRs, issues, and logs must not contain scan
  data from third-party systems.
- **No secrets in the repo.** Never commit `.env`, API keys, credentials, or
  captured session data. CI runs a secret scan; a hit blocks the PR.
- **Safety is not optional.** Changes to the scope/authorization path
  (`safety.py`, the consent gate) get extra scrutiny and must fail closed.

## Development setup (without Docker)

```bash
cd pentest-agents
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # add GOOGLE_API_KEY
```

## Before you open a PR

```bash
cd pentest-agents
ruff check .
ruff format --check .
pytest -q                 # unit tests (integration tests need -m integration)
```

- Keep changes scoped to one concern; small PRs review faster.
- Match existing style; the code favors self-explanatory names over comments.
- Add or update tests for any behavior change. Anything touching the safety or
  approval path must include tests proving it still fails closed.
- Update [`session.md`](session.md) and the relevant plan under
  `pentest-agents/.claude/plan/` if you change scope or architecture.

## Commit / PR conventions

- Conventional-commit-style subject lines (`feat:`, `fix:`, `docs:`, …).
- Describe what changed, why, and how you verified it. If you could not verify a
  step (for example, no Docker locally), say so explicitly.

## Reporting security issues

Do **not** open a public issue for a vulnerability in Threshold itself. See
[SECURITY.md](SECURITY.md).
