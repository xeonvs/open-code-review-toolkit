# Environment configuration

Open Code Review Toolkit uses environment variables only in v0.1. Empty values are generally treated as absent. Exact defaults and safety caps are enforced by the runtime modules.

## Upstream OCR and LLM

| Variable | Purpose |
| --- | --- |
| `OCR_LLM_URL` | OpenAI-compatible chat or responses endpoint. |
| `OCR_LLM_MODEL` | Exact model identifier passed to OCR. |
| `OCR_LLM_TOKEN` | LLM credential. Never written into generated context. |
| `OCR_LLM_AUTH_HEADER` | Optional authorization header name; defaults to `Authorization`. |
| `OCR_LLM_EXTRA_HEADERS` | Optional JSON object of additional string headers. |
| `OCR_LLM_SUPPORTS_FUNCTION_CALLING` | Boolean capability flag. |
| `OCR_LLM_SUPPORTS_REASONING` | Boolean capability flag. |
| `OCR_LLM_MAX_TOKENS` | Optional positive completion-token limit. |
| `OCR_LLM_VALIDATE_MODEL` | `true`, `false`, or `auto`; defaults to `false`. |
| `OCR_LLM_MODELS_URL` | Explicit `/models` metadata URL. |
| `OCR_LLM_ALLOWED_MODELS` | Optional comma-separated offline allowlist for `auto` validation. |
| `OCR_CONFIG_PATH` | Override the upstream OCR JSON config path. |

## MCP

| Variable | Purpose |
| --- | --- |
| `OCR_MCP_SERVERS_JSON` | JSON object mapping server names to command, arguments, environment, and optional tool allowlists. |
| `OCR_MCP_REPLACE` | Replace configured MCP servers when true; otherwise merge by server name. |

MCP commands run as child processes of upstream OCR. Treat their executable, arguments, environment, output, and tool access as privileged configuration.

## GitLab CI inputs

Posting requires `GITLAB_API_TOKEN`, `CI_SERVER_URL`, `CI_PROJECT_ID`, and `CI_MERGE_REQUEST_IID`. Inline discussions additionally use GitLab diff refs and merge-request source/base SHA variables. `CI_COMMIT_SHA` remains distinct from the merge-request source SHA and is never assumed to identify the reviewed branch head.

## Posting controls

`OCR_POST_MODE`, `OCR_STRICT_POSTING`, `OCR_EXIT_CODE`, `OCR_MAX_POST_COMMENTS`, `OCR_MAX_RESULT_BYTES`, and `OCR_POST_ERROR_DETAILS` control write behavior and bounded error reporting. Invalid numeric or boolean values fail closed or fall back to conservative defaults as documented in command output. Human replies to bot-created discussions prevent automated ownership actions on that discussion.

## Context controls

The `OCR_CONTEXT_*` family bounds files, bytes, changed paths, instructions, manifest content, dependency output, and generated background size. The default output is `.review-context/dependencies.md`. The generator rejects symlink escapes and prunes common vendor/build directories.

Run `ocr-ci --help` and each subcommand's help for command arguments. Secret values are redacted from operational error text.
