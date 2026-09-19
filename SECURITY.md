# Security Policy

## The nature of this tool

Threshold is a **dual-use offensive-security tool**. It automates active scanning
and exploitation. Used against systems you are authorized to test, it is a
legitimate assessment tool. Used against anything else, it is likely a crime.

### Your responsibilities as an operator

- Only run Threshold against targets you **own** or have **explicit, written
  authorization** to test.
- Scope is enforced fail-closed by `PENTEST_AGENTS_LAB_CIDR`, but that is a
  safety net, not permission — the legal authorization is yours to hold.
- Scan results contain sensitive vulnerability data about the target. Store and
  dispose of them responsibly; do not commit them or share them publicly.

## Reporting a vulnerability in Threshold itself

If you find a security issue in Threshold (for example, a way to bypass the scope
check or the consent gate, or a way for a target to compromise the operator):

- **Do not open a public GitHub issue.**
- Report it privately to the maintainers (open a GitHub security advisory, or use
  the contact listed on the repository).
- Include reproduction steps and affected versions. Please give a reasonable
  disclosure window before publishing.

We will acknowledge, investigate, and credit reporters who follow responsible
disclosure.

## Known security-relevant limitations (pre-release)

These are tracked in the roadmap
(`pentest-agents/.claude/plan/open-source-docker-release.md`) and are **not yet
fully mitigated**:

- **DNS rebinding / TOCTOU:** the target is resolved at the scope check but tools
  may re-resolve at run time. Resolve-and-pin is planned for Phase 3.
- **Redirect re-validation:** a cross-host redirect from an in-scope target is
  not yet re-checked against scope. Planned for Phase 3.
- **Consent enforcement:** the server-side consent gate is planned for Phase 3;
  until then, authorization rests entirely on the operator and the CIDR scope.

Do not rely on Threshold as a hardened boundary until the Phase 4 validation gate
has passed.
