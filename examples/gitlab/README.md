# GitLab operating modes

[`ocr-review.gitlab-ci.yml`](ocr-review.gitlab-ci.yml) is the complete checksum-pinned pipeline. It defaults to identity-only review and contains the install, preflight, configure, review, and post lifecycle. Copy one mode file below into the pipeline's top-level `variables` mapping, or include exactly one file after reviewing its trust boundary.

| Mode | Recipe | MR text admitted | External access | Automatic approval |
| --- | --- | --- | --- | --- |
| Identity only | [`modes/identity-only.gitlab-ci.yml`](modes/identity-only.gitlab-ci.yml) | None | None | May remain enabled |
| Metadata | [`modes/metadata.gitlab-ci.yml`](modes/metadata.gitlab-ci.yml) | Bounded title, description, labels, and source branch | None | May remain enabled when all receipt gates pass |
| Enriched discussions | [`modes/enriched-discussions.gitlab-ci.yml`](modes/enriched-discussions.gitlab-ci.yml) | Metadata plus protected-policy GitLab discussions and remediation threads | GitLab reads before OCR | Explicitly disabled in the recipe |
| Enriched adapters | [`modes/enriched-adapters.gitlab-ci.yml`](modes/enriched-adapters.gitlab-ci.yml) | Metadata plus policy-selected discussion and adapter records | Fixed pre-OCR adapter protocol | Explicitly disabled in the recipe |
| Direct MCP | [`modes/direct-mcp.gitlab-ci.yml`](modes/direct-mcp.gitlab-ci.yml) | Metadata plus model-selected tool results | Reviewed remote HTTPS MCP during OCR | Always comment-only |

The enriched-discussions mode uses [`context/policy-discussions.json`](context/policy-discussions.json). The enriched-adapters mode uses [`context/policy-adapters.json`](context/policy-adapters.json) plus one matching adapter allowlist. Copy the selected policy to the fixed protected-target path `.opencodereview/review-context-policy.json`. Direct MCP is a different, more privileged boundary: its tool descriptions, schemas, model-chosen arguments, and results enter the OCR session. Do not combine mode files until the resulting union has been reviewed deliberately.

[`accepted-decisions.md`](accepted-decisions.md) shows a target-branch decision document. Merge it as `.opencodereview/accepted-decisions.md` before relying on it in a later merge request; source-branch additions never authorize their own review. The usage walkthrough is in [Accepted project decisions](../../docs/configuration.md#accepted-project-decisions).
