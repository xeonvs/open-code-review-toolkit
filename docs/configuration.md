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
| `OCR_MAX_TOKENS_BUDGET` | Optional non-negative aggregate input-plus-output token ceiling passed to `ocr review`; `0` (default) is unlimited. |
| `OCR_LLM_VALIDATE_MODEL` | `true`, `false`, or `auto`; defaults to `false`. |
| `OCR_LLM_MODELS_URL` | Explicit `/models` metadata URL. |
| `OCR_LLM_ALLOWED_MODELS` | Optional comma-separated offline allowlist for `auto` validation. |
| `OCR_CONFIG_PATH` | Override the OCR JSON config path. |
| `OCR_REVIEW_CONTEXT_MODE` | Closed review-context selector: empty/`off` (default), `metadata`, or protected-policy `enriched`. |
| `OCR_REVIEW_CONTEXT_ADAPTERS_JSON` | Exact environment-only allowlist for M5 stdio or remote HTTPS context adapters. It is separate from direct MCP configuration. |

## MCP

| Variable | Purpose |
| --- | --- |
| `OCR_MCP_SERVERS_JSON` | JSON object mapping names to bounded stdio or native Streamable HTTP definitions. |
| `OCR_MCP_REPLACE` | Replace configured MCP servers when true; otherwise merge by server name. |

OCR receives every MCP as an independent named entry in its `mcp_servers` registry. The toolkit always installs the fixed `ocr_toolkit_evidence` entry; each configured external MCP is an optional sibling with a non-empty explicit tool-name allowlist. Reserved names and cross-server tool collisions fail closed, so an external server cannot shadow mandatory evidence.

The accepted transport schema depends on an internal execution profile, not on a public CI-detection variable. During a validated GitLab merge-request review, external entries must use `type=remote` with an absolute HTTPS `url`, optional bounded non-secret `headers`, environment-backed secret `headers_from`, and `tools`. `command`, `args`, `env`, `env_from`, and `setup` are rejected. Existing OCR MCP configuration is treated as hostile persisted input and revalidated through the same exact GitLab-MR schema before composition; the fixed toolkit-owned stdio evidence entry is the sole stdio exception. Outside the GitLab-MR provider path, the local profile preserves explicit developer-managed stdio entries with `command`, `args`, literal `env`, `env_from`, `tools`, and optional `setup`. Remote entries reject `setup` in every profile. `headers_from` writes a `$VARIABLE` reference and OCR expands it at connection time; sensitive literal headers are rejected.

A GitLab-MR external server therefore looks like:

```json
{
  "bounded_reference": {
    "type": "remote",
    "url": "https://mcp.synthetic.invalid/v1",
    "headers_from": {"Authorization": "SYNTHETIC_MCP_AUTH_HEADER"},
    "tools": ["read_admitted_record"]
  }
}
```

Generic external MCP is privileged operator configuration, not safe author-triggered reference resolution. The `tools` list authorizes names only: OCR forwards model-generated argument objects to a registered tool, and the toolkit does not authorize the tenant, object, fields, or operation named by those arguments. Each direct server must perform object-level authorization and input validation for every request. Server-authored tool descriptions and schemas enter OCR plan and main model context; the same external tools are exposed in both phases. Text results are returned to the model without a toolkit-configurable response byte/character cap, and OCR session JSONL persists prompts, responses, tool arguments, and results.

Use direct composition only for reviewed narrow read-only tools, dedicated least-privilege credentials, server-enforced resource authorization, bounded server responses, and data acceptable for both model egress and OCR-session retention. A direct tool must be safe in both phases. Do not expose generic search, arbitrary URL/ID fetch, recursive traversal, writes, or broad service credentials to references that merge-request text can select. Treat command, endpoint, environment, headers, setup, descriptions, schemas, arguments, and responses according to their separate executable or untrusted boundaries. Local-profile `setup` runs as operator-owned shell configuration in the analyzed repository; keep it empty unless explicitly reviewed. Do not expose raw endpoint, setup, or credential values through toolkit diagnostics; OCR may emit operator-owned setup or transport details, so keep those values non-sensitive and retain OCR stderr privately.

An unavailable optional server or tool/protocol error can degrade while OCR continues. Check the private OCR stderr and result rather than assuming configured context was used. Receipt v5 stores the complete bounded configured capability inventory (server, `builtin|stdio|remote` transport, and allowlisted tool names) plus positive per-server use counts. It never stores commands, URLs, headers, setup, arguments, results, or repository/provider content. A count proves only that OCR recorded a call; it does not prove object authorization, completeness, content safety, response use, or correct model judgment. The mandatory evidence MCP remains independently required. Every configured direct external MCP makes a review comment-only even when unused; server-authored tool annotations are not an enforceable same-session read-only guarantee. Direct external MCP remains privileged operator configuration. M5 external records use the separate toolkit-owned broker described in [Bounded review context](review-context.md), so provider schemas and arbitrary arguments never enter OCR.

### Review-context selector

`OCR_REVIEW_CONTEXT_MODE` is parsed before provider acquisition or OCR execution. Missing, empty, and `off` select identity-only acquisition: the provider still validates the source SHA, protected target identity, and positive merge-request author ID needed by policy and approval, but title, description, labels, and source branch are not normalized or stored. `metadata` requires a validated GitLab merge-request environment and admits only the existing bounded title, description, label, and optional source-branch projection. Every field reports a closed status; metadata is `complete` only when every selected field is absent or admitted. Invalid, over-limit, collision, redaction-limit, or partial states are `degraded`.

`enriched` requires a validated GitLab merge request and a valid `.opencodereview/review-context-policy.json` read only from the captured protected-target policy SHA. It adds policy-selected GitLab discussions and adapter records through a separate private store and fixed `context_list`/`context_get` tools. A source policy cannot expand access; missing or invalid protected policy fails before OCR. `OCR_REVIEW_CONTEXT_ADAPTERS_JSON` is an exact operator allowlist, and protected policy may only narrow it. See [Bounded review context](review-context.md) for the complete policy, stdio/HTTPS proxy protocol, projections, handles, DLP, completeness, receipt, and cleanup contracts.

Complete metadata remains untrusted invocation evidence but does not independently block approval. Degraded metadata does. Required enriched-source degradation and every admitted mutable discussion or external record also block approval; optional degradation remains visible and cannot prove absence. A complete enriched run with zero admitted mutable records may pass the remaining gates. No context mode can change policy, suppression, posting authority, credentials, or approval thresholds.

## GitLab CI inputs

Posting requires `GITLAB_API_TOKEN`, `CI_SERVER_URL`, `CI_PROJECT_ID`, and `CI_MERGE_REQUEST_IID`. Inline discussions additionally use GitLab diff refs and merge-request source/base SHA variables. `CI_COMMIT_SHA` remains distinct from the merge-request source SHA and is never assumed to identify the reviewed branch head.

## Posting controls

`OCR_POST_MODE`, `OCR_STRICT_POSTING`, `OCR_EXIT_CODE`, `OCR_MAX_POST_COMMENTS`, `OCR_MAX_RESULT_BYTES`, `OCR_POST_ERROR_DETAILS`, `OCR_POST_EMOJI`, `OCR_POST_BADGES`, and `OCR_AUTO_APPROVE` control write behavior and bounded error reporting. Human replies to bot-created discussions prevent automated ownership actions on that discussion.

`OCR_POST_EMOJI` defaults to `true`. Set it to `false`, `0`, `no`, or `off` to disable every emoji added by the toolkit to GitLab review-health and aggregate severity/category summaries. Inline severity/category fields remain text-only in both modes. This does not rewrite emoji already contained in upstream OCR finding text.

`OCR_MAX_TOKENS_BUDGET` is an operator-owned cost ceiling for one diff review,
not a quality profile or telemetry setting. The synthetic GitLab example passes
it directly to the recommended OCR's `--max-tokens-budget`; leave it at `0` for
unlimited review. When a positive ceiling stops dispatch, OCR preserves completed
findings and reports the unreviewed files as budget-attributed failed coverage.
The toolkit publishes that run as partial and never treats it as clean or eligible
for automatic approval. The cap is approximate because already-running work may
finish and OCR accounts the provider-reported input plus output tokens.

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
partial/budget outcomes, any receipt other than v5, degraded selected metadata, any configured direct external MCP, required context degradation, admitted mutable context,
and findings omitted by `OCR_MAX_POST_COMMENTS`. For receipt v5, complete metadata, complete zero-record enrichment, private-only sanitization, and the built-in evidence/context MCP are not blockers. GitLab posting also revalidates the receipt-bound source SHA and author ID, and skips without writing when the author changed or the toolkit user authored the merge request. There are intentionally no
environment variables for policy thresholds or category lists in this release.

`ocr-ci review --result PATH --stderr PATH -- ...` executes OCR without posting, creates private artifacts, and prints a bounded redacted stderr excerpt to the CI log when OCR fails. It accepts only a regular, single-link result artifact and, after a successful OCR process, atomically replaces that artifact with an owner-only copy containing the toolkit's bounded MCP-use receipt. `OCR_POST_ERROR_DETAILS=1` separately opts into including the same safe stderr excerpt in the GitLab failure note; leave it unset when diagnostics should remain runner-only.

## Repository evidence

`ocr-ci review` owns this lifecycle. Before OCR starts it collects the exact immutable `--from`/`--to` refs (or the parent/commit pair selected by `--commit`), writes bounded redacted schema-versioned evidence, builds OCR's MCP registry with the mandatory evidence entry plus each independently configured optional server, reads the registry back, self-queries the evidence summary/list/get contract, and supplies the matching compact bootstrap to OCR. Those parent-process preflight calls are not counted as model use. During OCR, the built-in MCP atomically records only completed `summary`, `list`, and `get` counts without arguments, IDs, paths, results, or content. The parent reads and removes that private receipt before cleanup and exposes the breakdown only when its total exactly matches OCR's `tool_calls.by_tool.ocr_toolkit_evidence`; missing, malformed, raced, or mismatched attribution is explicitly unavailable rather than zero. OCR 1.9.9 gives `--background-file` precedence over inline `--background`, so `ocr-ci review` rejects caller forms of both options, including split and `--option=value` syntax, and remains the sole owner of the bootstrap input. A completed OCR review is accepted only when structured `tool_calls.by_tool` proves at least one `ocr_toolkit_evidence` call; a legitimately skipped no-supported-files review remains exempt.

The private `.review-context/evidence.json`, `.review-context/bootstrap.md`, repository-policy `.review-context/policy-rules.json`, and count-only evidence-action receipt/lock are internal implementation details, not public path configuration. Keep `.review-context/` ignored. The directory is mode `0700`, regular files are mode `0600`, and symlink, hard-link, non-regular, or unexpectedly permissive receipt targets are rejected. In GitLab MR pipelines, the provider adapter captures the current protected target SHA, fetches that exact immutable object when needed, and materializes only an in-repository `--rule` blob from it; explicit absolute rules outside the repository remain operator-owned. OCR still reviews the original forge diff-base-to-source-head range. The collector reads Git objects without checkout, does not follow repository symlinks or submodules, never executes repository content, and treats source-ref policy changes as untrusted.

The compact bootstrap contains the same safe inventory of independent server/tool entries that was written to OCR configuration. The mandatory built-in server exposes `ocr_toolkit_evidence`, with `summary`, paginated/filterable `list`, and stable-ID `get` actions. An explicit `kind=repository.evidence_delta` list query returns redacted base/head changes; `delta_kind` narrows them by their original fact kind, and their stable IDs can be passed to `get`. A unique semantic fact retains the established compact before/after value. If one semantic identity has multiple sources, or moves between sources, the value becomes a deterministic list of `source_path` and `fact` objects so no accepted record is overwritten. The ordinary unfiltered list remains facts and scoped coverage only. It has no mutation action, network access, or shell execution. Optional MCP entries expose their own allowlisted tools; they can coexist with but cannot remove or shadow the mandatory entry.

Evidence-store schema v2 includes closed `framework.detected` (`repository.framework-evidence/v1`) and `template.file` (`repository.template-evidence/v1`) facts from package-owned static plugins. Current plugins cover Jinja2, Echo/Fiber, Symfony/Twig, and React/Next with related gRPC, TypeScript, and Vite declarations. Plugins consume only already bounded immutable manifest/tree evidence: they cannot execute repository commands, load repository code, use network access, or start a second MCP server. Framework versions use the ecosystem's deterministic source: lock files for Python, Composer, and JavaScript, but the direct requirement or effective replacement in `go.mod` for Go. Local Go replacements remain explicit partial evidence rather than being mistaken for the replaced module version. Templates and configuration paths belong to the nearest manifest-root component; conventional Ansible-role templates retain the role root. The exact component `.` denotes the repository root, while names such as `repository` are ordinary top-level paths; the same identities filter facts, coverage, and deltas through `ocr_toolkit_evidence`. Detailed declarations, resolutions, effective replacements, configuration/template paths, component scopes, and redacted base/head deltas remain available through its summary/list/get actions.

Implementation-wise, package and automation metadata is normalized by the internal `ocr_toolkit.evidence.ecosystems` source-adapter layer before framework plugins consume it. This is not a user-configurable runtime plugin namespace: adapter registration, bounded immutable reads, storage, and MCP serving remain toolkit-owned closed contracts.

The synthetic GitLab `rules.json` uses additive `include` entries for `.j2`, `.jinja`, `.jinja2`, `.twig`, and conventional Ansible-role template paths because the [recommended OCR](compatibility.md) does not review those extensions by default. Explicit excludes still win. The matching Jinja/Twig rules are review guidance; they do not execute or render templates, infer runtime variables, or replace evidence completeness.

Evidence-store schema v4 retains v1-v3 readback and adds a distinct immutable policy snapshot without relabelling the forge diff base. Current structured decisions and guidance bind to the policy SHA while applicability remains bound to the unchanged base-to-head changed paths. Schema v3 keeps its historical base-bound policy semantics, schema v2 text-only records retain explicit legacy provenance, and schema v1 remains readable with unknown completeness. Framework plugins publish `framework.declaration`, `framework.resolution`, `framework.configuration`, and `template.inventory` scopes. Supported malformed or omitted manifests, source-item limits, configuration/template output limits, unsafe template object types, local Go replacements, and isolated provider failures all prevent a false completeness claim. Only `complete` coverage permits a missing positive fact to support an absence claim; absent, `partial`, `runtime-dependent`, and `unavailable` coverage mean unknown. Schema-v1 stores remain readable but are explicitly treated as having unknown completeness. The Ansible adopter recognizes static, plugin-based, and executable inventory sources without execution and models the recursive role `defaults/main/` and `vars/main/` loader surface verified for ansible-core 2.17 through the current 2.x loader contract. Unsupported later loader behavior or bounded read/parser failures degrade coverage rather than becoming false completeness.

In `metadata` mode, GitLab MR acquisition normalizes only title, description, labels, optional source branch, and the reviewed source SHA into `review.merge_request_context/v1`. Values are complete-field bounded, NFC-normalized, control-stripped, redacted, source-head-bound invocation data. Raw values never enter bootstrap, argv, environment, diagnostics, or receipts; bootstrap lists only field statuses and toolkit-authored comparison guidance. In `off` mode none of those mutable text fields reaches normalization or persistence. OCR may treat matching intent as evidence against an assumption-dependent concern, contradictory intent as mismatch evidence, and missing intent as unknown. The source-branch hint is weaker than an explicit description and cannot establish rollout intent by itself. Metadata cannot authorize tools, policy, suppression, posting, or approval. In `enriched`, references are extracted only from admitted metadata and admitted discussion bodies; adapters authorize them before local handle minting. There is no generic URL, identifier, search, or provider-tool path in the model loop.

The review step writes exact closed receipt v5 inside the private result only after cleanup and the inode-checked atomic publication transformation. It binds source and policy SHA, merge-request author ID where applicable, context mode/state/classes, per-source completeness/degradation, admitted-mutable state, the complete bounded MCP capability inventory, positive known-server and fixed context-tool usage, mandatory-evidence state, publication-DLP result, and cleanup result. The current closed states are `passed`, `private-sanitized`, and `publication-filtered`. A pure canonical projection covers the normalized outcome/message, ordered allowlisted finding fields and warnings, manifest coverage/failure details, displayed tool counters, normalized token telemetry, omission/completeness, and approval inputs. Token telemetry has a closed provider-neutral vocabulary: input, output, cached as a subset of input, reasoning as a subset of output, optional validated total, and mathematically derived other; malformed or contradictory telemetry is unavailable and unknown provider keys are never published. Private sanitization may retain the original complete result and continue through existing approval gates only when that projection is byte-equivalent before and after sanitization. Any changed, malformed, or incomparable projection becomes a safe partial `publication-filtered` result with closed retained/omitted/original counts; it preserves the previous review and cannot authorize approval. Receipt v1-v4 has no posting or approval compatibility. The later GitLab posting step reads v5 instead of rebuilding context or MCP facts from a possibly changed environment. Its summary omits configured-but-unused servers and all zero counters; the receipt/event never stores rejected text/locations, provider/context text, upstream IDs, server URLs, commands, setup, arguments, headers, tool inputs/results, credentials, or repository contents.

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
