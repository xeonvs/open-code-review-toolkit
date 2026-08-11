# GitLab integration

The toolkit's first provider adapter posts review results to GitLab merge requests. The example is intended for trusted contributors because merge-request code and repository guidance are untrusted input even when the posting token is protected. Start with a manual job, validate results, and only then consider automatic execution.

## Installation

Install `open-code-review-toolkit` from PyPI. The example obtains the expected toolkit wheel digest from the matching immutable GitHub Release, then uses pip hash-checking and a local install. Install Open Code Review separately and pin `v1.9.1`; verify the release checksum before making the binary executable. The package never downloads OCR.

Copy and adapt [the synthetic CI example](../examples/gitlab/ocr-review.gitlab-ci.yml). Keep the lint stage before the AI review stage so failed project checks block review. The example downloads a pinned toolkit wheel with bounded retries/timeouts, verifies its SHA-256 before a local `--no-deps` install, generates a private evidence store plus one compact bootstrap, and passes the bootstrap once with `--background-file`.

## Required secrets

- `GITLAB_API_TOKEN`: a dedicated bot token with only the project/API permissions required to read the merge request, create/update its comments, and approve when `OCR_AUTO_APPROVE` is enabled.
- `OCR_LLM_TOKEN`: the LLM gateway credential used by OCR.
- `OCR_SHA256`: the trusted checksum for the pinned OCR binary asset.

Store secrets as masked, protected CI variables. Do not place them in YAML, command arguments, evidence artifacts, or the generated bootstrap. Posting deliberately does not accept a GitLab job token.

`OCR_REVIEW_LANGUAGE` is an optional non-secret OCR configuration setting and defaults to `English`. Set an explicit language name only when localized review output is required; `Russian` is one example.

## Operating model

`ocr-ci preflight` validates the installed OCR version, GitLab access, and configured LLM model. `configure` resolves `OCR_REVIEW_LANGUAGE`. `ocr-ci review` owns evidence collection, private artifacts, compact bootstrap, and the complete MCP registry: the mandatory `ocr_toolkit_evidence` server and every optional configured MCP are independent entries. After OCR succeeds, `review` validates mandatory evidence use and atomically binds a safe schema-versioned per-server MCP-use receipt to the private result. `post` reads that review-time receipt instead of reconstructing configuration, then publishes bounded notes with rollback and ownership safeguards.

`ocr-ci post` also manages conservative automatic approval by default. After all
current notes publish, it waits for GitLab diff and approval synchronization,
verifies the current MR head against the reviewed SHA, submits that exact SHA,
and confirms only the authenticated toolkit user's approval through bounded
readback. Set `OCR_AUTO_APPROVE=false` for a comment-only bot or before upgrading
an integration whose approval rules have not granted the bot permission. This
transaction is add-only: an ineligible or disabled later run never removes an
existing approval. Configure GitLab's own reset or invalidation policy if
approvals must be withdrawn after the source branch changes.

Repeated reviews have a reviewer-controlled lifecycle rather than appending the same notes indefinitely. Untouched OCR-only notes are replaced after a successful run, human-touched discussions are preserved, and `/ocr suppress` or `/ocr resolve` controls future matching findings. Read [GitLab review operations](operations.md) for the complete state machine, deduplication boundaries, posting modes, permissions, limits, and failure semantics.

For a deliberate project-wide tradeoff that should be supplied to every review, add a narrowly scoped entry to `.opencodereview/accepted-decisions.md` in an earlier reviewed merge request. The [configuration reference](configuration.md#accepted-project-decisions) documents its `ocr-accept` marker convention, prompt-level semantics, and self-whitelisting guard.

OCR is configured through its `openai-responses` provider. Run the review through `ocr-ci review` so failed OCR stderr is retained privately and a bounded redacted diagnostic appears in the runner log. This command never posts; `ocr-ci post` remains the explicit GitLab write boundary. MCP tools are supplied with `OCR_MCP_SERVERS_JSON`; treat stdio commands and remote endpoints as privileged configuration.

Use merge-request source and base SHAs, not a merge-result commit, when choosing the reviewed range. Keep the self-test job manual. See [docs/security.md](security.md) for trust boundaries and [docs/configuration.md](configuration.md) for every input.
