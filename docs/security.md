# Security and trust model

The toolkit bridges four trust domains: repository content, OCR and its LLM/MCP providers, CI secrets, and the GitLab API. None of the first three should be assumed safe merely because a job runs in a trusted project.

## Preserved safety properties

- Repository reads are bounded, rooted, symlink-aware, and exclude common dependency/build trees.
- Review-invocation metadata is provider-normalized from a closed allowlist. GitLab evidence includes only bounded numeric project, pipeline, job, and merge-request identifiers; URLs, refs, tokens, and arbitrary environment values are not collected. Invocation facts carry a distinct trust class and are not treated as repository or toolkit assertions.
- Generated Markdown escapes control characters and neutralizes GitLab quick actions.
- Secrets and credential-shaped values are redacted before operational output.
- OCR result and provider response reads have byte limits.
- GitLab notes enforce both UTF-8 byte limits and Python character limits.
- Non-idempotent API writes are not blindly retried.
- Markers, fingerprints, snapshots, and rollback logic constrain repeated runs.
- Human replies are ownership boundaries: automation must not rewrite or resolve a discussion after a human takes part.
- Merge-request source SHA and merge-result SHA remain distinct.

The evidence engine reads exact base/head Git objects without checkout, refuses symlinks and submodules, stores redacted typed records in owner-only files, and exposes them through a closed read-only MCP tool with bounded requests, responses, filters, and pagination. Target/base guidance may describe policy; changed source/head guidance and accepted decisions cannot authorize the review that introduces them. The compact bootstrap carries only refs, coverage, counts, diagnostics, and MCP usage instructions; detailed values remain in the evidence store.

Ansible Galaxy requirement includes use the same immutable-object boundary. Relative includes may only resolve to YAML blobs inside the authenticated tree; absolute, home-relative, root-escaping, symlink, and submodule targets are rejected. Include depth, file count, graph edges, parser items, and emitted diagnostics have independent limits so adversarial manifests degrade visibly without expanding unbounded work.

## Deployment guidance

Use a dedicated bot identity and least-privilege `GITLAB_API_TOKEN`. Protect and mask credentials. Do not expose secrets to pipelines for untrusted forks. Begin with manual execution for trusted contributors, review generated notes, and enable automatic posting only after the repository's threat model is accepted.

Pin Open Code Review `v1.8.8` and verify its checksum. Pin Python dependencies through `uv.lock` and GitHub Actions by immutable commit SHA. MCP stdio commands and remote endpoints are privileged configuration; allow only reviewed servers and tools.
The [OCR compatibility policy](compatibility.md) requires double-source asset digest verification, bounded downloads, an executed Linux contract probe, and protected PR/release gates; qualification automation never writes directly to `main` or promotes an ambiguous release.

Remote MCP is HTTPS-only, forbids URL userinfo and fragments, and never logs endpoint URLs or header values. Put credentials in protected/masked CI variables and reference them through `headers_from`; literal credential-like headers fail closed. OCR expands the resulting `$VARIABLE` at connection time. Full browser OAuth, PKCE, refresh-token persistence, tenant binding, and revocation remain outside 0.3.1; use a reviewed stdio OAuth proxy when those flows are required.

All toolkit-owned Git plumbing ignores process-level repository/object-store overrides, global and system Git configuration, and replacement refs before it derives evidence or remaps an inline finding. Existing OCR configuration is treated as hostile persisted input: reads are descriptor-based, single-link, and byte-bounded before JSON parsing.

The repository runs Bandit as a bounded SAST gate over `src/ocr_toolkit` at medium-or-higher severity and confidence. Narrow `# nosec B108` annotations are permitted only beside fixed CI temporary paths whose isolation or containment is explained in the adjacent source comment; tests, examples, and broad plugin suppressions are not part of that exception policy.

## Repository security posture

Protected `main` requires pull requests, signed commits, a current branch, resolved review threads, and the complete CI, package-build, dependency, secret, and CodeQL check set. The project currently has one maintainer, so it cannot truthfully require an independent human approval for maintainer-authored changes. This is an explicit residual risk: automated review does not replace a second human. External contributions still receive maintainer review, and independent approval will become mandatory when a second active maintainer can provide it without blocking security fixes.

OpenSSF Scorecard findings are interpreted as supply-chain posture signals rather than vulnerability reports. Repository-age and historical-coverage checks improve only with time and repeated runs; the owner-attested OpenSSF Best Practices record is public and passing; a useful fuzzing integration requires native fuzz targets and infrastructure rather than a workflow added only to satisfy a scanner. Actionable repository-owned findings are fixed through normal signed pull requests.

The detailed environment contract is in [configuration.md](configuration.md). Vulnerability reporting is in [SECURITY.md](../SECURITY.md).
