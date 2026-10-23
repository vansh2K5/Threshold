# Reproducibility, Benchmark, Ethics, and References

## Benchmark artifact

The supplied audit asks for a `benchmarks/` directory and a YAML manifest. No `benchmarks/` directory exists in the current checkout. Add one before claiming a defined target set. For each target specify:

```yaml
name: <stable identifier>
version: <release/tag>
image: <registry/image:exact-tag>
image_digest: <sha256 digest>
authorized_scope: <exact IP/CIDR in isolated lab>
difficulty: <predefined tier and rationale>
expected_shell_method: <observable verification criterion or not applicable>
reset:
  procedure: <commands/steps>
  verification: <how clean state is confirmed>
network: <Compose network name and isolation properties>
```

Include only targets owned by the authors or explicitly authorized for this study. Document Compose setup, ports, network boundaries, scope entry, target readiness checks, reset commands, and teardown. The project documents optional OWASP Juice Shop at `172.30.255.10` on an internal Docker network, but the full benchmark set, pinned image digest, and repeatable reset are not yet established in the protocol. Do not infer those from the address alone.

## Batch reproducibility package

For every batch, store `batch_metadata.json` with UTC start/end, batch ID, protocol version/hash, repository commit, host OS/kernel, Docker/Compose/Python versions, dependency lockfiles, exact Compose file, all image digests, provider/API/model versions, resolved budgets, authorized scope, target reset state, operator policy, manual config changes, and collection-script version. Copy exact dependency files and Compose configuration into the batch directory. Store API-reported model/version strings where available; a configured name or `latest` alias is not enough.

Pin exact Docker tags/digests and dependency versions in the project. Preserve historic lockfiles per evaluated release. Tag the evaluated artifact only after the code and validation state are frozen; record the commit/tag in every result and the paper.

Suggested repository reproduction entrypoint from the audit is `scripts/reproduce_paper.sh`: start the isolated Compose environment, verify images/targets, execute only the registered matrix, collect event/resource data, calculate costs from a dated price file, generate CSV/LaTeX/figures, and stop the lab. It must fail closed if scope, model version, target reset confirmation, or required dependencies are missing. Do not make a script silently imply it ran conditions that are not implemented.

## Responsible use and ethics

Paper and artifact instructions should state that Threshold performs active scanning and exploitation; experiments are restricted to owned or explicitly authorized, isolated lab assets; no public or third-party target is in scope; and scope validation is server-side. Describe safeguards for raw prompts, outputs, commands, credentials, IPs, and incident evidence. Redact secrets before sharing artifacts while retaining enough evidence to reproduce each result. Explain any disclosure obligations for vulnerabilities found in systems beyond the benchmark.

The current project README contains an authorized-use warning and describes a local isolated Juice Shop setup. That is relevant implementation context, but it does not prove each experiment was isolated or authorized; record the actual batch configuration.

## Citation and bibliography audit

The supplied audit flags reference [5] author/title alignment, a truncated title for [10], a likely paraphrase for [11], and a total of about 15 references. The bibliography was not present in the repository files reviewed, so these are **audit-reported verification tasks**, not corrections already confirmed. Before submission:

1. Check every citation against the paper/PDF or publisher record, including exact author order, title, year, venue, pages/DOI or stable identifier, and current publication status.
2. Resolve [5], [10], and [11] against their primary publication records; do not guess corrections from the audit’s description.
3. Check whether cited preprints have a later peer-reviewed version and cite the version actually consulted.
4. Add relevant primary sources for human-in-the-loop security, LLM agent evaluation methods, OWASP Juice Shop if used, HexStrike if citable, LangGraph, FastAPI, safety/least-privilege tool use, and recent work directly relevant to autonomous penetration testing.
5. Expand the related-work coverage to the venue-appropriate depth; the audit’s 25–35 range is a recommendation, not a validated venue rule. Prefer direct comparison dimensions over broad, potentially unfair one-phrase limitations.
6. Ensure every bibliography entry is cited in text and every in-text citation resolves to one exact entry.

No outside reference was looked up for this repository package. Bibliographic fact-checking remains a manuscript task and should use primary sources when authors perform it.
