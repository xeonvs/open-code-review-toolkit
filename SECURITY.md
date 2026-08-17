# Security Policy

## Supported versions

Before 1.0, only the newest published release receives security fixes.

## Security review context

The canonical runtime [threat model](docs/security.md#threat-model) treats repository content, OCR/LLM/MCP output, provider responses, inherited process state, and persisted artifacts as hostile data. Security reviews should prioritize contributor-reachable paths that can:

- execute or import repository-controlled content;
- forge immutable identity, provenance, trust, applicability, coverage, approval, or release authorization;
- escape acquisition/output bounds or let one exhausted domain suppress unrelated evidence;
- inject active Markdown or protocol control syntax across a trust boundary;
- turn untrusted review metadata into arbitrary remote-image requests;
- expose credentials or private repository/provider material;
- treat a tool-name allowlist, prompt, schema, host, tenant, or successful authentication as object authorization;
- let untrusted context expand tools, traversal, model egress, publication, retention, suppression, or approval authority;
- retain model prompts, tool arguments/results, or external records outside the documented containment boundary; or
- perform an ambiguous or unguarded provider mutation with security impact.

Calibrate findings to demonstrated reachability and impact. Prompt-like text without a privileged action path is not code execution. Same-owner modification of owner-only local artifacts is not an ordinary contributor escalation unless a lower-privilege writer is established. OpenSSF posture signals, repository age, and the documented single-maintainer review limitation are not vulnerability findings on their own. Safe bounded read-only diagnostics and synthetic reproduction are in scope; do not require live credentials, private source, or provider mutation to validate a report.

## Reporting a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/xeonvs/open-code-review-toolkit/security/advisories/new) for this repository. Do not open a public issue or attach live credentials, proprietary source, or production provider responses. Include a minimal synthetic reproducer, impact, affected version, and suggested mitigation when available.

Maintainers will acknowledge a report within five business days, privately validate severity and affected versions, and coordinate disclosure only after a fix or documented mitigation is available. Critical fixes are released as soon as practical; reporters receive status updates at least every ten business days while investigation remains open.

The runtime trust model and deployment guidance are documented in [docs/security.md](docs/security.md).
