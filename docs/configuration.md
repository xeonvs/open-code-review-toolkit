# Environment configuration

Open Code Review Toolkit uses environment variables only in v0.1. Empty values are generally treated as absent. Exact defaults and safety caps are enforced by the runtime modules.

## OCR and LLM

| Variable | Purpose |
| --- | --- |
| `OCR_LLM_URL` | OpenAI-compatible chat or responses endpoint. |
| `OCR_LLM_MODEL` | Exact model identifier passed to OCR. |
| `OCR_REVIEW_LANGUAGE` | Single review language used by OCR config and generated context. Defaults to `English`; set `Russian` for Russian review output. |
| `OCR_LLM_TOKEN` | LLM credential. Never written into generated context. |
| `OCR_LLM_AUTH_HEADER` | Optional authorization header name; defaults to `Authorization`. |
| `OCR_LLM_EXTRA_HEADERS` | Optional JSON object of additional string headers. |
| `OCR_LLM_SUPPORTS_FUNCTION_CALLING` | Boolean capability flag. |
| `OCR_LLM_SUPPORTS_REASONING` | Boolean capability flag. |
| `OCR_LLM_MAX_TOKENS` | Optional positive completion-token limit. |
| `OCR_LLM_VALIDATE_MODEL` | `true`, `false`, or `auto`; defaults to `false`. |
| `OCR_LLM_MODELS_URL` | Explicit `/models` metadata URL. |
| `OCR_LLM_ALLOWED_MODELS` | Optional comma-separated offline allowlist for `auto` validation. |
| `OCR_CONFIG_PATH` | Override the OCR JSON config path. |

## MCP

| Variable | Purpose |
| --- | --- |
| `OCR_MCP_SERVERS_JSON` | JSON object mapping server names to command, arguments, environment, and optional tool allowlists. |
| `OCR_MCP_REPLACE` | Replace configured MCP servers when true; otherwise merge by server name. |

MCP commands run as child processes of OCR. Treat their executable, arguments, environment, output, and tool access as privileged configuration.

## GitLab CI inputs

Posting requires `GITLAB_API_TOKEN`, `CI_SERVER_URL`, `CI_PROJECT_ID`, and `CI_MERGE_REQUEST_IID`. Inline discussions additionally use GitLab diff refs and merge-request source/base SHA variables. `CI_COMMIT_SHA` remains distinct from the merge-request source SHA and is never assumed to identify the reviewed branch head.

## Posting controls

`OCR_POST_MODE`, `OCR_STRICT_POSTING`, `OCR_EXIT_CODE`, `OCR_MAX_POST_COMMENTS`, `OCR_MAX_RESULT_BYTES`, and `OCR_POST_ERROR_DETAILS` control write behavior and bounded error reporting. Invalid numeric or boolean values fail closed or fall back to conservative defaults as documented in command output. Human replies to bot-created discussions prevent automated ownership actions on that discussion.

## Context controls

The `OCR_CONTEXT_*` family bounds files, bytes, changed paths, instructions, manifest content, dependency output, and generated background size. `OCR_BACKGROUND_MAX_CHARS` defaults to and is capped at `7950`; `OCR_BACKGROUND_MAX_BYTES` independently enforces the UTF-8 byte budget. The default output is `.review-context/dependencies.md`. The generator rejects symlink escapes and prunes common vendor/build directories.

Use the default `OCR_POST_MODE=draft` for normal CI so all current notes are created as drafts before they are published and replaceable notes from the previous run are removed. Draft publication is sequential rather than atomic; the previous review is preserved unless every current draft publishes. Set `OCR_STRICT_POSTING=true` when the review job is a required merge gate; keep the default `false` only for advisory pipelines where GitLab posting availability must not block the pipeline. Reviewer commands and the complete repeated-run contract are documented in [GitLab review operations](operations.md).

Run `ocr-ci --help` and each subcommand's help for command arguments. Secret values are redacted from operational error text.
