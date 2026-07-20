# GitLab integration

The toolkit's first provider adapter posts review results to GitLab merge requests. The example is intended for trusted contributors because merge-request code and repository guidance are untrusted input even when the posting token is protected. Start with a manual job, validate results, and only then consider automatic execution.

## Installation

Install `open-code-review-toolkit` from PyPI. The example obtains the expected toolkit wheel digest from the matching immutable GitHub Release, then uses pip hash-checking and a local install. Install Open Code Review separately and pin `v1.7.13`; verify the release checksum before making the binary executable. The package never downloads OCR.

Copy and adapt [the synthetic CI example](../examples/gitlab/ocr-review.gitlab-ci.yml). Keep the lint stage before the AI review stage so failed project checks block review. The example downloads a pinned toolkit wheel with bounded retries/timeouts, verifies its SHA-256 before a local `--no-deps` install, generates one background file, and passes it once with `--background-file`.

## Required secrets

- `GITLAB_API_TOKEN`: a dedicated bot token with only the project/API permissions required to read the merge request and create/update its comments.
- `OCR_LLM_TOKEN`: the LLM gateway credential used by OCR.
- `OCR_SHA256`: the trusted checksum for the pinned OCR binary asset.

Store secrets as masked, protected CI variables. Do not place them in YAML, command arguments, artifacts, or generated context. Posting deliberately does not accept a GitLab job token.

`OCR_REVIEW_LANGUAGE` is an optional non-secret setting shared by OCR configuration and generated context. It defaults to `English`; set `Russian` for Russian review output.

## Operating model

`ocr-ci preflight` validates the installed OCR version, GitLab access, and configured LLM model. `configure` and `context` resolve the same `OCR_REVIEW_LANGUAGE` value, so the OCR system prompt and review background cannot disagree. `configure` and `mcp-config` write OCR configuration without invoking a config subprocess. `context` creates bounded Markdown. `post` interprets a JSON artifact and publishes bounded notes with rollback and ownership safeguards.

OCR is configured through its `openai-responses` provider. Optional stdio bridge tools are supplied with `OCR_MCP_SERVERS_JSON`; treat every configured MCP command as privileged code.

Use merge-request source and base SHAs, not a merge-result commit, when choosing the reviewed range. Keep the self-test job manual. See [docs/security.md](security.md) for trust boundaries and [docs/configuration.md](configuration.md) for every input.
