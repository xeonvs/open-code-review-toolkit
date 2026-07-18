# Security and trust model

The toolkit bridges four trust domains: repository content, OCR and its LLM/MCP providers, CI secrets, and the GitLab API. None of the first three should be assumed safe merely because a job runs in a trusted project.

## Preserved safety properties

- Repository reads are bounded, rooted, symlink-aware, and exclude common dependency/build trees.
- Generated Markdown escapes control characters and neutralizes GitLab quick actions.
- Secrets and credential-shaped values are redacted before operational output.
- OCR result and provider response reads have byte limits.
- GitLab notes enforce both UTF-8 byte limits and Python character limits.
- Non-idempotent API writes are not blindly retried.
- Markers, fingerprints, snapshots, and rollback logic constrain repeated runs.
- Human replies are ownership boundaries: automation must not rewrite or resolve a discussion after a human takes part.
- Merge-request source SHA and merge-result SHA remain distinct.

## Deployment guidance

Use a dedicated bot identity and least-privilege `GITLAB_API_TOKEN`. Protect and mask credentials. Do not expose secrets to pipelines for untrusted forks. Begin with manual execution for trusted contributors, review generated notes, and enable automatic posting only after the repository's threat model is accepted.

Pin Open Code Review `v1.7.12` and verify its checksum. Pin Python dependencies through `uv.lock` and GitHub Actions by immutable commit SHA. MCP servers are privileged child processes; allow only reviewed commands and tools.

The detailed environment contract is in [configuration.md](configuration.md). Vulnerability reporting is in [SECURITY.md](../SECURITY.md).
