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

OCR receives every MCP as an independent named entry in its `mcp_servers` registry. The toolkit always installs `ocr_toolkit_evidence` as one mandatory entry; each configured local or remote MCP is a separate optional sibling entry and is started or contacted by OCR independently. Omitting `type` selects backward-compatible `stdio`. Stdio accepts `command`, `args`, literal `env`, `env_from`, `tools`, and `setup`. A `remote` entry accepts an absolute HTTPS `url`, non-secret `headers`, secret `headers_from`, `tools`, and `setup`. Every optional server requires a non-empty explicit `tools` allowlist so its discovered tool set cannot shadow the mandatory evidence tool. `headers_from` maps a header name to a CI variable and writes `$VARIABLE` into OCR config, so the recommended OCR release resolves it only when connecting. Sensitive header families such as `Authorization`, cookies, API keys, and tokens are rejected in literal `headers`.

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

`OCR_POST_MODE`, `OCR_STRICT_POSTING`, `OCR_EXIT_CODE`, `OCR_MAX_POST_COMMENTS`, `OCR_MAX_RESULT_BYTES`, `OCR_POST_ERROR_DETAILS`, `OCR_POST_EMOJI`, `OCR_POST_BADGES`, and `OCR_AUTO_APPROVE` control write behavior and bounded error reporting. Human replies to bot-created discussions prevent automated ownership actions on that discussion.

`OCR_POST_EMOJI` defaults to `true`. Set it to `false`, `0`, `no`, or `off` to disable every emoji added by the toolkit to GitLab review-health and aggregate severity/category summaries. Inline severity/category fields remain text-only in both modes. This does not rewrite emoji already contained in upstream OCR finding text.

`OCR_POST_BADGES` controls only category/severity presentation on individual
findings. The default `text` mode renders local Markdown labels and makes no
external image request. Set it to `shields` to render one static Shields.io
image whose URL, color, and alt text are built only from toolkit-normalized OCR
category/severity enums. Missing or malformed metadata is omitted, and an
invalid setting falls back to `text` without logging its value. The image alt
text retains the normalized label when images are blocked, but displaying a
remote image may let a browser, GitLab proxy, or network intermediary contact a
third party. Keep `text` where that request or its viewer/network metadata is
not acceptable. This setting does not change summary outcomes, fingerprints,
suppression, approval, limits, or posting transactions.

`OCR_AUTO_APPROVE` defaults to `true` and adds a formal GitLab approval after a
complete review publishes. It accepts `true`, `1`, `yes`, or `on`; set `false`,
`0`, `no`, or `off` to disable the approval attempt for that run. An empty value
uses the enabled default. Any other value fails closed to disabled and emits a
bounded diagnostic without printing the value. The toolkit never removes an
existing approval. Ineligible, partial, skipped, legacy, and disabled runs make
no approval write, so project-owned reset and invalidation rules remain the only
mechanism for withdrawing an earlier approval.

The initial policy is fixed: zero findings, or at most three findings whose
severity is exactly `low` and category is exactly `style`, `documentation`, or
`maintainability`, are eligible. Missing, unknown, differently cased, or
non-string metadata blocks approval, as do warnings, failed or waived coverage,
partial/budget outcomes, legacy results without a supported coverage manifest,
and findings omitted by `OCR_MAX_POST_COMMENTS`. There are intentionally no
environment variables for policy thresholds or category lists in this release.

`ocr-ci review --result PATH --stderr PATH -- ...` executes OCR without posting, creates private artifacts, and prints a bounded redacted stderr excerpt to the CI log when OCR fails. It accepts only a regular, single-link result artifact and, after a successful OCR process, atomically replaces that artifact with an owner-only copy containing the toolkit's bounded MCP-use receipt. `OCR_POST_ERROR_DETAILS=1` separately opts into including the same safe stderr excerpt in the GitLab failure note; leave it unset when diagnostics should remain runner-only.

## Repository evidence

`ocr-ci review` owns this lifecycle. Before OCR starts it collects the exact immutable `--from`/`--to` refs (or the parent/commit pair selected by `--commit`), writes bounded redacted schema-versioned evidence, builds OCR's MCP registry with the mandatory evidence entry plus each independently configured optional server, reads the registry back, self-queries the evidence summary/list/get contract, and supplies the matching compact bootstrap to OCR. Callers may add inline OCR `--background` text, but cannot replace the toolkit-owned background file. A completed OCR review is accepted only when structured `tool_calls.by_tool` proves at least one `ocr_toolkit_evidence` call; a legitimately skipped no-supported-files review remains exempt.

The private `.review-context/evidence.json` store and `.review-context/bootstrap.md` projection are internal implementation artifacts, not public path configuration. Keep `.review-context/` ignored. The directory is mode `0700`, files are mode `0600`, and symlink or non-regular-file targets are rejected. The collector reads Git objects without checkout, does not follow repository symlinks or submodules, never executes repository content, and treats source-ref policy changes as untrusted.

The compact bootstrap contains the same safe inventory of independent server/tool entries that was written to OCR configuration. The mandatory built-in server exposes `ocr_toolkit_evidence`, with `summary`, paginated/filterable `list`, and stable-ID `get` actions. An explicit `kind=repository.evidence_delta` list query returns redacted base/head changes; `delta_kind` narrows them by their original fact kind, and their stable IDs can be passed to `get`. A unique semantic fact retains the established compact before/after value. If one semantic identity has multiple sources, or moves between sources, the value becomes a deterministic list of `source_path` and `fact` objects so no accepted record is overwritten. The ordinary unfiltered list remains facts and scoped coverage only. It has no mutation action, network access, or shell execution. Optional MCP entries expose their own allowlisted tools; they can coexist with but cannot remove or shadow the mandatory entry.

Evidence-store schema v2 includes closed `framework.detected` (`repository.framework-evidence/v1`) and `template.file` (`repository.template-evidence/v1`) facts from package-owned static plugins. Current plugins cover Jinja2, Echo/Fiber, Symfony/Twig, and React/Next with related gRPC, TypeScript, and Vite declarations. Plugins consume only already bounded immutable manifest/tree evidence: they cannot execute repository commands, load repository code, use network access, or start a second MCP server. Framework versions use the ecosystem's deterministic source: lock files for Python, Composer, and JavaScript, but the direct requirement or effective replacement in `go.mod` for Go. Local Go replacements remain explicit partial evidence rather than being mistaken for the replaced module version. Templates and configuration paths belong to the nearest manifest-root component; conventional Ansible-role templates retain the role root. The exact component `.` denotes the repository root, while names such as `repository` are ordinary top-level paths; the same identities filter facts, coverage, and deltas through `ocr_toolkit_evidence`. Detailed declarations, resolutions, effective replacements, configuration/template paths, component scopes, and redacted base/head deltas remain available through its summary/list/get actions.

Implementation-wise, package and automation metadata is normalized by the internal `ocr_toolkit.evidence.ecosystems` source-adapter layer before framework plugins consume it. This is not a user-configurable runtime plugin namespace: adapter registration, bounded immutable reads, storage, and MCP serving remain toolkit-owned closed contracts.

The synthetic GitLab `rules.json` uses additive `include` entries for `.j2`, `.jinja`, `.jinja2`, `.twig`, and conventional Ansible-role template paths because the [recommended OCR](compatibility.md) does not review those extensions by default. Explicit excludes still win. The matching Jinja/Twig rules are review guidance; they do not execute or render templates, infer runtime variables, or replace evidence completeness.

Evidence-store schema v3 retains `repository.evidence-coverage/v1` records and adds exact structured policy records keyed by component, domain, scope, immutable ref, and commit. Structured records are bound again on hostile readback to the atomic base/head snapshots and their changed-path applicability; schema v3 does not accept text-only policy records. Exact schema-v2 text-only records remain readable with explicit legacy counts and their original ref/trust instead of being relabelled as target policy. Framework plugins publish `framework.declaration`, `framework.resolution`, `framework.configuration`, and `template.inventory` scopes. Supported malformed or omitted manifests, source-item limits, configuration/template output limits, unsafe template object types, local Go replacements, and isolated provider failures all prevent a false completeness claim. Only `complete` coverage permits a missing positive fact to support an absence claim; absent, `partial`, `runtime-dependent`, and `unavailable` coverage mean unknown. Schema-v1 stores remain readable but are explicitly treated as having unknown completeness. The Ansible adopter recognizes static, plugin-based, and executable inventory sources without execution and models the recursive role `defaults/main/` and `vars/main/` loader surface verified for ansible-core 2.17 through the current 2.x loader contract. Unsupported later loader behavior or bounded read/parser failures degrade coverage rather than becoming false completeness.

The review step maps OCR's structured `tool_calls.by_tool` counters onto the exact validated registry used for that invocation and stores only positive per-server counts in a schema-versioned `_ocr_toolkit` receipt inside the private result. The later GitLab posting step reads that receipt instead of rebuilding MCP configuration from a possibly changed environment. Its summary omits configured-but-unused servers and all zero counters; the receipt never stores server URLs, commands, arguments, headers, tool inputs, tool results, or repository contents.

### Accepted project decisions

Use `.opencodereview/accepted-decisions.md` for reviewed target-branch tradeoffs that should be available as contextual evidence. Each H2 section is one decision. Existing heading-and-rationale entries remain valid; optional metadata adds explicit applicability and maintenance information:

```markdown
## generated-client-timeout

The generated client keeps the provider timeout so regeneration stays reproducible.

- Scope: src/client/generated/**
- Category: compatibility
- Owner: client-platform
- Review after: 2026-12-01
```

`Scope` may repeat and uses case-sensitive repository-relative POSIX globs. `*` and `?` stay within one path segment; `**` is recursive only as its own segment. Absolute paths, traversal, backslashes, negation, bracket/brace patterns, extglobs, empty segments, embedded `**`, and adjacent recursive segments are rejected. Repeated scopes are OR alternatives; an entry without Scope is project-wide. Unknown metadata remains ordinary rationale and does not gain authority. Invalid metadata or one malformed or oversized entry cannot invalidate unrelated decisions. Each complete structured value is also bounded by its canonical UTF-8 representation before storage, after recursive redaction, and again on readback, so multibyte text or a size-expanding redaction cannot cross the evidence-MCP response boundary unexpectedly.

The optional inline convention `# ocr-accept: generated-client-timeout` can still connect a rationale to code for human readers, but it is not a source-code parser or marker authority. Accepted decisions are not static-analysis exemptions, unconditional suppression, or permission to ignore unrelated findings. `Category` and `Owner` are descriptive. `Review after` is a strict ISO date: the decision is surfaced as stale from that UTC date but remains visible until maintainers review or remove it.

Only the immutable target/base document is policy evidence. Source-branch edits never create authority. The compact bootstrap contains bounded summaries only for applicable decisions; full redacted rationale, provenance, scope, applicability, and staleness remain queryable through the built-in `ocr_toolkit_evidence` MCP. Reviewers should continue to use `/ocr suppress` or `/ocr resolve` for a concrete GitLab discussion.

### Target project guidance

The evidence engine discovers target/base `AGENTS.md` and `CLAUDE.md` files at repository root and in ancestor directories of changed files. Root `AGENTS.md` and `CLAUDE.md` remain global even when the invocation has no changed-path identity; nested documents still require a matching descendant path. Guidance outside every changed path's ancestor chain is neither read nor stored. Applicable guidance is presented from root toward the changed file, with `AGENTS.md` before `CLAUDE.md` in one directory, and has a separate bounded document budget so unrelated tree shape cannot evict later evidence domains. Root-only `PR_REVIEW.md`, `.cursorrules`, and `.github/copilot-instructions.md` remain global bounded guidance.

Guidance added, changed, deleted, or renamed by the current merge request is excluded; both sides of a rename count as changed. Symlinks, submodules, non-blob objects, oversized documents, and invalid UTF-8 are rejected. The compact bootstrap contains only normalized target paths, scopes, and toolkit-generated applicability hints. Full redacted target text is available on demand through `ocr_toolkit_evidence` and is always untrusted evidence: it cannot override system policy, grant tool permissions, change posting behavior, suppress findings unconditionally, or authorize actions.

Use the default `OCR_POST_MODE=draft` for normal CI so all current notes are created as drafts before they are published and replaceable notes from the previous run are removed. Draft publication is sequential rather than atomic; the previous review is preserved unless every current draft publishes. Set `OCR_STRICT_POSTING=true` when the review job is a required merge gate; keep the default `false` only for advisory pipelines where GitLab posting availability must not block the pipeline. Reviewer commands and the complete repeated-run contract are documented in [GitLab review operations](operations.md).

Run `ocr-ci --help` and each subcommand's help for command arguments. Secret values are redacted from operational error text.
