# Environment configuration

Open Code Review Toolkit uses environment variables for CI/runtime configuration. Empty values are generally treated as absent. Exact defaults and safety caps are enforced by the runtime modules.

## OCR and LLM

| Variable | Purpose |
| --- | --- |
| `OCR_LLM_URL` | OpenAI-compatible chat or responses endpoint. |
| `OCR_LLM_MODEL` | Exact model identifier passed to OCR. |
| `OCR_REVIEW_LANGUAGE` | Single review language used by OCR configuration. Defaults to `English`; another explicit language such as `Russian` is optional. |
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
| `OCR_MCP_SERVERS_JSON` | JSON object mapping names to bounded stdio or native Streamable HTTP definitions. |
| `OCR_MCP_REPLACE` | Replace configured MCP servers when true; otherwise merge by server name. |

Omitting `type` selects backward-compatible `stdio`. Stdio accepts `command`, `args`, literal `env`, `env_from`, `tools`, and `setup`. A `remote` entry accepts an absolute HTTPS `url`, non-secret `headers`, secret `headers_from`, `tools`, and `setup`. Every external server requires a non-empty explicit `tools` allowlist so its discovered tool set cannot shadow the mandatory built-in evidence tool. `headers_from` maps a header name to a CI variable and writes `$VARIABLE` into OCR config, so OCR 1.8.0 resolves it only when connecting. Sensitive header families such as `Authorization`, cookies, API keys, and tokens are rejected in literal `headers`.

```json
{
  "documentation": {
    "type": "remote",
    "url": "https://mcp.synthetic.invalid/v1/mcp",
    "headers_from": {"Authorization": "SYNTHETIC_MCP_TOKEN"},
    "tools": ["search"]
  },
  "oauth_proxy": {
    "command": "synthetic-mcp-proxy",
    "args": ["--read-only"],
    "tools": ["read_page"]
  }
}
```

Treat stdio executables, remote endpoints, arguments, environment, output, headers, and tool access as privileged configuration. Native remote MCP is preferred when static environment-backed headers suffice. Keep stdio for local tools and OAuth-owning proxies.

## GitLab CI inputs

Posting requires `GITLAB_API_TOKEN`, `CI_SERVER_URL`, `CI_PROJECT_ID`, and `CI_MERGE_REQUEST_IID`. Inline discussions additionally use GitLab diff refs and merge-request source/base SHA variables. `CI_COMMIT_SHA` remains distinct from the merge-request source SHA and is never assumed to identify the reviewed branch head.

## Posting controls

`OCR_POST_MODE`, `OCR_STRICT_POSTING`, `OCR_EXIT_CODE`, `OCR_MAX_POST_COMMENTS`, `OCR_MAX_RESULT_BYTES`, `OCR_POST_ERROR_DETAILS`, and `OCR_POST_EMOJI` control write behavior and bounded error reporting. Invalid numeric or boolean values fail closed or fall back to conservative defaults as documented in command output. Human replies to bot-created discussions prevent automated ownership actions on that discussion.

`OCR_POST_EMOJI` defaults to `true`. Set it to `false`, `0`, `no`, or `off` to disable every emoji added by the toolkit to GitLab status summaries and structured severity/category tags. This does not rewrite emoji already contained in upstream OCR finding text.

`ocr-ci review --result PATH --stderr PATH -- ...` executes OCR without posting, creates private artifacts, and prints a bounded redacted stderr excerpt to the CI log when OCR fails. `OCR_POST_ERROR_DETAILS=1` separately opts into including that same safe excerpt in the GitLab failure note; leave it unset when diagnostics should remain runner-only.

## Repository evidence

`ocr-ci review` owns this lifecycle. Before OCR starts it collects the exact immutable `--from`/`--to` refs (or the parent/commit pair selected by `--commit`), writes bounded redacted schema-versioned evidence, composes the mandatory built-in MCP server with validated external servers, and supplies the matching compact bootstrap to OCR. Callers may add inline OCR `--background` text, but cannot replace the toolkit-owned background file.

The private `.review-context/evidence.json` store and `.review-context/bootstrap.md` projection are internal implementation artifacts, not public path configuration. Keep `.review-context/` ignored. The directory is mode `0700`, files are mode `0600`, and symlink or non-regular-file targets are rejected. The collector reads Git objects without checkout, does not follow repository symlinks or submodules, never executes repository content, and treats source-ref policy changes as untrusted.

The compact bootstrap contains the same safe server/tool capability inventory that was written to OCR configuration. The mandatory built-in tool is `ocr_toolkit_evidence`, with `summary`, paginated/filterable `list`, and stable-ID `get` actions. It has no mutation action, network access, or shell execution; validated external MCP definitions can add capabilities but cannot remove or shadow it.

### Accepted project decisions

Use `.opencodereview/accepted-decisions.md` for a reviewed, project-wide decision that OCR would otherwise report repeatedly. Each entry should have a stable slug, a concise rationale, an explicit scope, and an inline marker that ties the decision to the relevant code or configuration:

```markdown
## generated-client-timeout

The generated client keeps the provider's 90-second timeout so regenerated
code remains reproducible. Do not report that timeout in `src/client/generated.py`.

Look for `# ocr-accept: generated-client-timeout` at the configured value.
```

```python
REQUEST_TIMEOUT = 90  # ocr-accept: generated-client-timeout
```

`ocr-accept` is a human-readable convention, not a source-code parser or blanket linter suppression. The complete, byte-bounded Markdown file is sanitized, redacted, and included under `Accepted project decisions` in the generated review background; OCR is instructed not to raise matching findings. Keep the rationale narrow and name the affected paths or behavior so unrelated findings remain reviewable.

The decision file must already exist on the target branch and pass normal review. If the current merge request changes `.opencodereview/accepted-decisions.md`, or changed-file discovery fails, the toolkit omits all accepted decisions for that run to prevent self-whitelisting. A decision reduces repeated model findings but is not a deterministic static-analysis exemption: reviewers should still use `/ocr suppress` or `/ocr resolve` for a concrete GitLab discussion, and should update or remove stale decisions when the underlying tradeoff changes.

Use the default `OCR_POST_MODE=draft` for normal CI so all current notes are created as drafts before they are published and replaceable notes from the previous run are removed. Draft publication is sequential rather than atomic; the previous review is preserved unless every current draft publishes. Set `OCR_STRICT_POSTING=true` when the review job is a required merge gate; keep the default `false` only for advisory pipelines where GitLab posting availability must not block the pipeline. Reviewer commands and the complete repeated-run contract are documented in [GitLab review operations](operations.md).

Run `ocr-ci --help` and each subcommand's help for command arguments. Secret values are redacted from operational error text.
