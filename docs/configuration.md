# Environment configuration

Open Code Review Toolkit uses environment variables for CI/runtime configuration. Empty values are generally treated as absent. Exact defaults and safety caps are enforced by the runtime modules.

## Toolkit runtime variables

These are the complete supported toolkit-owned runtime inputs. `Required` is scoped to the command or mode named in the behavior column; an unrelated command does not require the variable.

| Variable | Source / owner | Required | Exact default | Behavior |
| --- | --- | --- | --- | --- |
| `OCR_LLM_URL` | Operator / configure and preflight | Yes for review | None | Absolute credential-free HTTPS API root or compatible terminal inference endpoint; normalized through the shared provider owner. |
| `OCR_LLM_TOKEN` | Operator secret / `ocr-ci configure` | Yes for review | None | LLM credential; never written into generated context or receipts. |
| `OCR_LLM_MODEL` | Operator / configure and preflight | Yes for review | None | Exact model identifier passed to OCR and optional model validation. |
| `OCR_LLM_PROTOCOL` | Operator / `ocr-ci configure` | No | `openai` | Closed protocol: `openai`, `openai-responses`, or `anthropic`. |
| `OCR_LLM_AUTH_HEADER` | Operator / configure and preflight | No | `Authorization` | Valid HTTP header name used for the bearer credential. |
| `OCR_LLM_EXTRA_HEADERS` | Operator / configure and preflight | No | Empty object | JSON object of additional string headers; cannot duplicate the auth header. |
| `OCR_LLM_EXTRA_BODY` | Operator / `ocr-ci configure` | No | Unset | JSON object merged into the OCR LLM request configuration; completion-cap field conflicts are checked against the dedicated variable. |
| `OCR_LLM_MAX_COMPLETION_TOKENS` | Operator / `ocr-ci configure` | No | Unset (inherits OCR) | Positive decimal integer from `1` through `1000000`; sets the protocol-specific completion/output cap without changing prompt/context or aggregate review budgets. |
| `OCR_ANTHROPIC_DISABLE_THINKING` | Operator / `ocr-ci configure` | No | `false` | With the Anthropic protocol, exact `true` adds `thinking.type=disabled`. |
| `OCR_REVIEW_LANGUAGE` | Operator / shared language resolver | No | `English` | Allowed language label or BCP-47 tag used for the review. |
| `OCR_LLM_VALIDATE_MODEL` | Operator / `ocr-ci preflight` | No | `false` | `true` validates through `/models`; `auto` may use the offline allowlist; false values skip validation. |
| `OCR_LLM_MODELS_URL` | Operator / `ocr-ci preflight` | No | Derived from `OCR_LLM_URL` | Explicit absolute credential-free HTTPS metadata URL when validation is enabled or inference query parameters make derivation ambiguous. |
| `OCR_LLM_ALLOWED_MODELS` | Operator / `ocr-ci preflight` | No | Empty list | Comma-separated exact model identifiers for offline or `auto` validation. |
| `OCR_TELEMETRY_ENABLED` | Operator / `ocr-ci configure` | No | `false` | Exact `true` enables OCR telemetry configuration. |
| `OCR_TELEMETRY_CONTENT_LOGGING` | Operator / `ocr-ci configure` | No | `false` | Exact `true` enables OCR content logging; keep disabled for private review data. |
| `OCR_TELEMETRY_EXPORTER` | Operator / `ocr-ci configure` | No | Empty string | Exporter name written only when telemetry is enabled. |
| `OCR_TELEMETRY_OTLP_ENDPOINT` | Operator / `ocr-ci configure` | No | Unset | OTLP endpoint written only when telemetry is enabled and the value is non-empty. |
| `OCR_REVIEW_CONTEXT_MODE` | Operator / review launcher | No | `off` | Closed selector: `off`, `metadata`, or protected-policy `enriched`. |
| `OCR_REVIEW_CONTEXT_ADAPTERS_JSON` | Operator / context broker | No | Empty list | Exact allowlist of bounded stdio or remote HTTPS context adapters. |
| `OCR_MCP_SERVERS_JSON` | Operator / MCP composition | No | Empty object | JSON mapping of direct bounded stdio or Streamable HTTP MCP definitions. |
| `OCR_MCP_REPLACE` | Operator / MCP composition | No | `false` | Boolean; replace inherited OCR MCP entries instead of merging by name. |
| `OCR_POST_MODE` | Operator / posting | No | `draft` | `draft` is normal transactional publication; `direct` is the emergency fallback. |
| `OCR_STRICT_POSTING` | Operator / posting | No | `false` | Boolean; make posting failures fail the job when enabled. |
| `OCR_POST_EMOJI` | Operator / formatting | No | `true` | Boolean; controls toolkit-added emoji only. |
| `OCR_POST_BADGES` | Operator / formatting | No | `text` | `text` or `shields`; invalid values fail back to private-safe `text`. |
| `OCR_AUTO_APPROVE` | Operator / approval | No | `true` | Boolean; invalid values fail closed to disabled. Receipt and evidence gates remain authoritative. |
| `OCR_MAX_POST_COMMENTS` | Operator / posting | No | `50` | Non-negative individual-comment limit, capped at `200`. |
| `OCR_MAX_RESULT_BYTES` | Operator / result loader | No | `2000000` | Positive result byte limit, capped at `20000000`. |
| `OCR_POST_ERROR_DETAILS` | Operator / posting | No | Unset (disabled) | Only exact `1` admits the bounded redacted OCR stderr excerpt into a failure note. |
| `OCR_EXIT_CODE` | Review job handoff / posting | No | `0` | OCR process exit code passed from `ocr-ci review` to `ocr-ci post`. |

Since 0.8.0, `OCR_USE_ANTHROPIC` is not a compatibility alias. Any presence fails configuration with an explicit request to set `OCR_LLM_PROTOCOL=anthropic`, preventing a stale false value from silently selecting the default OpenAI protocol.

`OCR_LLM_AUTH_TOKEN`, `OPENAI_API_KEY`, and `ANTHROPIC_API_KEY` are redaction sentinels, not supported toolkit configuration. They stay in secret filtering so inherited process values cannot leak. `HOME` and `PATH` are process inputs used only for the isolated OCR home and binary lookup; `LANG`, `LC_ALL`, and `TMPDIR` are child-process mechanics set by the toolkit rather than public configuration.

### Provider endpoint and completion-cap contract

`OCR_LLM_PROTOCOL` is authoritative; the URL never selects a protocol. `OCR_LLM_URL` accepts an API root or the matching terminal endpoint: `/chat/completions` for `openai`, `/responses` for `openai-responses`, and `/v1/messages` for `anthropic`. Configure and preflight use the same normalized API root, reject a terminal endpoint belonging to another protocol, and reject credentials or fragments embedded in either provider URL. A query is preserved for inference. Because copying it to an auxiliary endpoint is ambiguous, model validation with a queried inference URL requires an explicit `OCR_LLM_MODELS_URL`.

`OCR_LLM_MAX_COMPLETION_TOKENS` is optional and defaults to **unset**, which inherits the qualified OCR version's behavior. It accepts a positive decimal integer from `1` through `1000000` and writes one protocol-specific field:

| `OCR_LLM_PROTOCOL` | Generated `llm.extra_body` field |
| --- | --- |
| `openai` | `max_completion_tokens` |
| `openai-responses` | `max_output_tokens` |
| `anthropic` | `max_tokens` |

If `OCR_LLM_EXTRA_BODY` already owns that field, an exactly equal JSON integer is deduplicated. A different value, or a boolean, string, float, or null at that field, fails configuration with a migration error; remove the duplicate field or keep the same integer in both places. Other `OCR_LLM_EXTRA_BODY` members are preserved. For example, set `OCR_LLM_MAX_COMPLETION_TOKENS=4096` when a gateway accepts short probes but rejects a full review before generation because it reserves spending against the requested output cap.

Toolkit 0.8.1 does not derive this value from `/models.max_completion_tokens`. That metadata is a model capability boundary, not an account spending limit or proof of how a gateway reserves request cost.

## GitLab and provider variables

GitLab supplies the `CI_*` values in merge-request pipelines. The operator supplies the dedicated API token.

| Variable | Source / owner | Required | Exact default | Behavior |
| --- | --- | --- | --- | --- |
| `GITLAB_API_TOKEN` | Operator secret | Yes for provider reads and posting | None | Dedicated GitLab API credential used with `PRIVATE-TOKEN`. |
| `CI_API_V4_URL` | GitLab predefined | One of this or `CI_SERVER_URL` for provider reads | Derived as `${CI_SERVER_URL}/api/v4` | Absolute HTTPS GitLab API v4 root. |
| `CI_SERVER_URL` | GitLab predefined | Yes for posting; alternative owner for API root | `https://gitlab.com` in posting only | Absolute HTTPS GitLab server root. GitLab CI normally always defines it. |
| `CI_PROJECT_ID` | GitLab predefined | Yes in merge-request mode | None | Bounded numeric project identity used for provider APIs and receipts. |
| `CI_MERGE_REQUEST_IID` | GitLab predefined | Yes in merge-request mode | None | Bounded numeric merge-request identity and mode signal. |
| `CI_MERGE_REQUEST_SOURCE_BRANCH_SHA` | GitLab predefined | Yes for the recommended review range | Falls back to `CI_COMMIT_SHA` only where explicitly documented | Exact reviewed source head used by the review, receipt, and posting revalidation. |
| `CI_MERGE_REQUEST_DIFF_BASE_SHA` | GitLab predefined | Yes for the recommended review range | None | Exact merge-request diff base passed to OCR and evidence collection. |
| `CI_COMMIT_SHA` | GitLab predefined | No | None | Fallback head identity when the MR-specific source SHA is unavailable; it does not replace the diff base. |
| `CI_PIPELINE_ID` | GitLab predefined | No | Omitted | Optional bounded invocation identity stored as non-authoritative evidence. |
| `CI_JOB_ID` | GitLab predefined | No | Omitted | Optional bounded invocation identity stored as non-authoritative evidence. |
| `CI_PIPELINE_SOURCE` | GitLab predefined / example rules | Yes for example job selection | None | The public example runs review jobs only for `merge_request_event`. |

## Example-local variables

These names belong to `examples/gitlab/ocr-review.gitlab-ci.yml`; they are shell or pipeline controls, not additional toolkit configuration.

| Variable | Source / owner | Required | Exact default | Behavior |
| --- | --- | --- | --- | --- |
| `OCR_VERSION` | Example pipeline | Yes | `v1.9.10` | Checksum-pinned recommended OCR binary release for toolkit 0.8.1. |
| `OCR_SHA256` | Example pipeline | Yes | `359e5bafda1438a47ef389399f4994350e1016371eac1dc17a2c428acb228e6c` | Expected Linux AMD64 OCR binary digest. |
| `OCR_TOOLKIT_VERSION` | Example pipeline | Yes | `0.8.1` | Exact toolkit wheel release installed by the current published example. |
| `OCR_TOOLKIT_CHECKSUMS_URL` | Example pipeline | Yes | Release URL derived from `OCR_TOOLKIT_VERSION` | Toolkit `SHA256SUMS` URL. |
| `OCR_TOOLKIT_WHEEL` | Example shell | Computed | `open_code_review_toolkit-${OCR_TOOLKIT_VERSION}-py3-none-any.whl` | Exact wheel filename selected from the release. |
| `OCR_TOOLKIT_WHEEL_SHA256` | Example shell | Computed | Matching value from `SHA256SUMS` | Digest checked before installing the toolkit wheel. |
| `OCR_MAX_TOOLS` | Example pipeline / OCR CLI | No | `30` | Positive maximum OCR tool-request rounds per file; the example keeps the OCR 1.9.10 default and passes it explicitly. |
| `OCR_MAX_TOKENS_BUDGET` | Example pipeline / OCR CLI | No | `0` | Non-negative aggregate OCR token ceiling; `0` is unlimited. |

## Dynamic adapter and MCP inputs

| Variable | Source / owner | Required | Exact default | Behavior |
| --- | --- | --- | --- | --- |
| Names declared by adapter `env_from` | Operator / `OCR_REVIEW_CONTEXT_ADAPTERS_JSON` | Yes when declared | None | Inject an adapter environment value by exact variable name; missing names fail closed. |
| Names declared by adapter `headers_from` | Operator / `OCR_REVIEW_CONTEXT_ADAPTERS_JSON` | Yes when declared | None | Supply a remote adapter header without persisting its secret value in configuration. |
| Names declared by MCP `env_from` | Operator / `OCR_MCP_SERVERS_JSON` | Yes when declared | None | Inject a local-profile stdio MCP environment value by exact variable name. |
| Names declared by MCP `headers_from` | Operator / `OCR_MCP_SERVERS_JSON` | Yes when declared | None | Supply a remote MCP header by reference for OCR expansion at connection time. |

## MCP composition and trust boundary

OCR receives every MCP as an independent named entry in its `mcp_servers` registry. The toolkit always installs the fixed `ocr_toolkit_evidence` entry; each configured external MCP is an optional sibling with a non-empty explicit tool-name allowlist. Reserved names and cross-server tool collisions fail closed, so an external server cannot shadow mandatory evidence.

The accepted transport schema depends on an internal execution profile, not on a public CI-detection variable. During a validated GitLab merge-request review, external entries must use `type=remote` with an absolute HTTPS `url`, optional bounded non-secret `headers`, environment-backed secret `headers_from`, and `tools`. `command`, `args`, `env`, `env_from`, and `setup` are rejected. Existing OCR MCP configuration is treated as hostile persisted input and revalidated through the same exact GitLab-MR schema before composition; the fixed toolkit-owned stdio evidence entry is the sole stdio exception. Outside the GitLab-MR provider path, the local profile preserves explicit developer-managed stdio entries with `command`, `args`, literal `env`, `env_from`, `tools`, and optional `setup`. Remote entries reject `setup` in every profile. `headers_from` writes a `$VARIABLE` reference and OCR expands it at connection time; sensitive literal headers are rejected.

A GitLab-MR external server therefore looks like:

```json
{
  "review_evidence": {
    "type": "remote",
    "url": "https://review-evidence.example.invalid/v1/mcp",
    "headers_from": {"Authorization": "REVIEW_EVIDENCE_MCP_AUTHORIZATION"},
    "tools": ["read_review_evidence"]
  }
}
```

Generic external MCP is privileged operator configuration, not safe author-triggered reference resolution. The `tools` list authorizes names only: OCR forwards model-generated argument objects to a registered tool, and the toolkit does not authorize the tenant, object, fields, or operation named by those arguments. Each direct server must perform object-level authorization and input validation for every request. Server-authored tool descriptions and schemas enter OCR plan and main model context; the same external tools are exposed in both phases. Text results are returned to the model without a toolkit-configurable response byte/character cap, and OCR session JSONL persists prompts, responses, tool arguments, and results.

Use direct composition only for reviewed narrow read-only tools, dedicated least-privilege credentials, server-enforced resource authorization, bounded server responses, and data acceptable for both model egress and OCR-session retention. A direct tool must be safe in both phases. Do not expose generic search, arbitrary URL/ID fetch, recursive traversal, writes, or broad service credentials to references that merge-request text can select. Treat command, endpoint, environment, headers, setup, descriptions, schemas, arguments, and responses according to their separate executable or untrusted boundaries. Local-profile `setup` runs as operator-owned shell configuration in the analyzed repository; keep it empty unless explicitly reviewed. Do not expose raw endpoint, setup, or credential values through toolkit diagnostics; OCR may emit operator-owned setup or transport details, so keep those values non-sensitive and retain OCR stderr privately.

An unavailable optional server or tool/protocol error can degrade while OCR continues. Check the private OCR stderr and result rather than assuming configured context was used. Receipt v5 stores the complete bounded configured capability inventory (server, `builtin|stdio|remote` transport, and allowlisted tool names) plus positive per-server use counts. It never stores commands, URLs, headers, setup, arguments, results, or repository/provider content. A count proves only that OCR recorded a call; it does not prove object authorization, completeness, content safety, response use, or correct model judgment. The mandatory evidence MCP remains independently required. Every configured direct external MCP makes a review comment-only even when unused; server-authored tool annotations are not an enforceable same-session read-only guarantee. Direct external MCP remains privileged operator configuration. M5 external records use the separate toolkit-owned broker described in [Bounded review context](review-context.md), so provider schemas and arbitrary arguments never enter OCR.

### Review-context selector

`OCR_REVIEW_CONTEXT_MODE` is parsed before provider acquisition or OCR execution. Missing, empty, and `off` select identity-only acquisition: the provider still validates the source SHA, protected target identity, and positive merge-request author ID needed by policy and approval, but title, description, labels, and source branch are not normalized or stored. `metadata` requires a validated GitLab merge-request environment and admits only the existing bounded title, description, label, and optional source-branch projection. Every field reports a closed status; metadata is `complete` only when every selected field is absent or admitted. Invalid, over-limit, collision, redaction-limit, or partial states are `degraded`.

`enriched` requires a validated GitLab merge request and a valid `.opencodereview/review-context-policy.json` read only from the captured protected-target policy SHA. It adds policy-selected generic GitLab discussions, verified remediation threads, and adapter records through a separate private store and fixed `context_list`/`context_get` tools. A source policy cannot expand access; missing or invalid protected policy fails before OCR. `OCR_REVIEW_CONTEXT_ADAPTERS_JSON` is an exact operator allowlist, and protected policy may only narrow it. See [Bounded review context](review-context.md) for policy v1/v2 compatibility, the stdio/HTTPS proxy protocol, fixed remediation projection, handles, DLP, completeness, receipt, and cleanup contracts.

Complete DLP-admitted metadata, generic discussions, and dynamic records remain untrusted evidence but do not independently block approval. Degraded metadata, any DLP rejection, required enriched-source degradation, and every admitted remediation thread do block approval; optional non-DLP degradation remains visible and cannot prove absence. A complete enriched run without admitted remediation may pass the remaining receipt and evidence gates. No context mode can change policy, suppression, posting authority, credentials, or approval thresholds.

## GitLab CI inputs

Posting requires `GITLAB_API_TOKEN`, `CI_SERVER_URL`, `CI_PROJECT_ID`, and `CI_MERGE_REQUEST_IID`. Inline discussions additionally use GitLab diff refs and merge-request source/base SHA variables. `CI_COMMIT_SHA` remains distinct from the merge-request source SHA and is never assumed to identify the reviewed branch head.

## Token controls

Three independent controls must not be substituted for one another:

- `OCR_LLM_MAX_COMPLETION_TOKENS` sets the provider request's per-call completion/output cap through `llm.extra_body`; its default is unset and it does not reduce prompt input.
- OCR's own `max_tokens`/`--max-tokens` controls its prompt/context ceiling. The toolkit does not add an environment alias or change that OCR-owned default.
- `OCR_MAX_TOKENS_BUDGET` is an operator-owned cost ceiling for the aggregate diff review, not a quality profile or per-request limit.

`OCR_MAX_TOKENS_BUDGET` is an operator-owned cost ceiling for one diff review,
not a quality profile or telemetry setting. The complete GitLab pipeline passes
it directly to the recommended OCR's `--max-tokens-budget`; leave it at `0` for
unlimited review. When a positive ceiling stops dispatch, OCR preserves completed
findings and reports the unreviewed files as budget-attributed failed coverage.
The toolkit publishes that run as partial and never treats it as clean or eligible
for automatic approval. The cap is approximate because already-running work may
finish and OCR accounts the provider-reported input plus output tokens.

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
partial/budget outcomes, any receipt other than v5, degraded selected metadata, any configured direct external MCP, required context degradation, a DLP-rejected selected source, admitted remediation context,
and findings omitted by `OCR_MAX_POST_COMMENTS`. For receipt v5, complete metadata, complete non-remediation enrichment, private-only sanitization, and the built-in evidence/context MCP are not blockers. GitLab posting also revalidates the receipt-bound source SHA and author ID, and skips without writing when the author changed or the toolkit user authored the merge request. There are intentionally no
environment variables for policy thresholds or category lists in this release.

`ocr-ci review --result PATH --stderr PATH -- ...` executes OCR without posting, creates private artifacts, and prints a bounded redacted stderr excerpt to the CI log when OCR fails. It accepts only a regular, single-link result artifact and, after a successful ordinary OCR process, atomically replaces that artifact with an owner-only copy containing the toolkit's bounded MCP-use receipt. For a local diagnosis only, `--preserve-private-artifacts` retains the owner-only isolated OCR home and repository-local review artifacts and leaves the OCR result without a posting receipt. It also writes `.review-context/private-dlp-decisions.json` using schema `ocr.private-dlp-decisions/v1`: up to 1,000 rejected keys or values have only their bounded JSON path, scope/action, public reason, detector subtype, value type, character/byte/line counts, and SHA-256; `truncated` plus `omitted_decisions` report any remaining decisions. The sidecar never contains the rejected value, replaces unsafe key names with `<rejected-key>`, collapses excessive path depth to `<truncated-path>`, and can correlate repeated technical values by digest so a local operator can distinguish likely false positives from genuine PII, secret, limit, or laundering detections. The retained result and other paths can still contain repository, provider, model, tool-argument, tool-result, and credential-adjacent data: inspect them locally, never upload or post them, and delete them after diagnosis. Ordinary execution removes a stale sidecar and never creates a new one. A validated GitLab merge-request profile rejects this flag before OCR execution; CI detection variables do not authorize it. `OCR_POST_ERROR_DETAILS=1` separately opts into including the same safe stderr excerpt in the GitLab failure note; leave it unset when diagnostics should remain runner-only.

## Repository evidence

`ocr-ci review` owns this lifecycle. Before OCR starts it collects the exact immutable `--from`/`--to` refs (or the parent/commit pair selected by `--commit`), writes bounded redacted schema-versioned evidence, builds OCR's MCP registry with the mandatory evidence entry plus each independently configured optional server, reads the registry back, self-queries the evidence summary/list/get contract, and supplies the matching compact bootstrap to OCR. Those parent-process preflight calls are not counted as model use. The same preflight-qualified OCR executable first receives the exact production refs, rules, selection options, and background under `review --preview`; there is no toolkit threshold setting or duplicated OCR threshold constant. An exact recognized OCR soft background warning is copied into the bounded CI log and the atomically finalized result `warnings`, which also blocks automatic approval. An exact recognized hard character/file-size rejection stops before model execution and leaves only an identity-bound numeric `ocr.pre-execution-status/v2` outcome for static GitLab reporting; the private path and raw OCR diagnostic are not published. Unknown preview failures fail closed through the generic diagnostic path, and the actual review independently revalidates the background. During OCR, the built-in MCP atomically records only completed `summary`, `list`, and `get` counts without arguments, IDs, paths, results, or content. The parent reads and removes that private receipt before cleanup and exposes the breakdown only when its total exactly matches OCR's `tool_calls.by_tool.ocr_toolkit_evidence`; missing, malformed, raced, or mismatched attribution is explicitly unavailable rather than zero. Since OCR 1.9.9, `--background-file` takes precedence over inline `--background`, so `ocr-ci review` rejects caller forms of both options, including split and `--option=value` syntax, and remains the sole owner of the bootstrap input; caller `--preview` is likewise rejected because the toolkit owns this gate. Toolkit 0.8.0 requires OCR 1.9.10; its stage-grouped terminal retry report does not enter toolkit telemetry, receipts, DLP, findings, severity, outcomes, or approval. A completed OCR review is accepted only when structured `tool_calls.by_tool` proves at least one `ocr_toolkit_evidence` call; a legitimately skipped no-supported-files review remains exempt.

The private `.review-context/evidence.json`, `.review-context/bootstrap.md`, repository-policy `.review-context/policy-rules.json`, and count-only evidence-action receipt/lock are internal implementation details, not public path configuration. Keep `.review-context/` ignored. The directory is mode `0700`, regular files are mode `0600`, and symlink, hard-link, non-regular, or unexpectedly permissive receipt targets are rejected. In GitLab MR pipelines, the provider adapter captures the current protected target SHA, fetches that exact immutable object when needed, and materializes only an in-repository `--rule` blob from it; explicit absolute rules outside the repository remain operator-owned. OCR still reviews the original forge diff-base-to-source-head range. The collector reads Git objects without checkout, does not follow repository symlinks or submodules, never executes repository content, and treats source-ref policy changes as untrusted.

The compact bootstrap contains the same safe inventory of independent server/tool entries that was written to OCR configuration. The mandatory built-in server exposes `ocr_toolkit_evidence`, with `summary`, paginated/filterable `list`, and stable-ID `get` actions. An explicit `kind=repository.evidence_delta` list query returns redacted base/head changes; `delta_kind` narrows them by their original fact kind, and their stable IDs can be passed to `get`. A unique semantic fact retains the established compact before/after value. If one semantic identity has multiple sources, or moves between sources, the value becomes a deterministic list of `source_path` and `fact` objects so no accepted record is overwritten. The ordinary unfiltered list remains facts and scoped coverage only. It has no mutation action, network access, or shell execution. Optional MCP entries expose their own allowlisted tools; they can coexist with but cannot remove or shadow the mandatory entry.

Evidence-store schema v2 includes closed `framework.detected` (`repository.framework-evidence/v1`) and `template.file` (`repository.template-evidence/v1`) facts from package-owned static plugins. Current plugins cover Jinja2, Echo/Fiber, Symfony/Twig, and React/Next with related gRPC, TypeScript, and Vite declarations. Plugins consume only already bounded immutable manifest/tree evidence: they cannot execute repository commands, load repository code, use network access, or start a second MCP server. Framework versions use the ecosystem's deterministic source: lock files for Python, Composer, and JavaScript, but the direct requirement or effective replacement in `go.mod` for Go. Local Go replacements remain explicit partial evidence rather than being mistaken for the replaced module version. Templates and configuration paths belong to the nearest manifest-root component; conventional Ansible-role templates retain the role root. The exact component `.` denotes the repository root, while names such as `repository` are ordinary top-level paths; the same identities filter facts, coverage, and deltas through `ocr_toolkit_evidence`. Detailed declarations, resolutions, effective replacements, configuration/template paths, component scopes, and redacted base/head deltas remain available through its summary/list/get actions.

Implementation-wise, package and automation metadata is normalized by the internal `ocr_toolkit.evidence.ecosystems` source-adapter layer before framework plugins consume it. This is not a user-configurable runtime plugin namespace: adapter registration, bounded immutable reads, storage, and MCP serving remain toolkit-owned closed contracts.

The GitLab `rules.json` example uses additive `include` entries for `.j2`, `.jinja`, `.jinja2`, `.twig`, and conventional Ansible-role template paths because the [recommended OCR](compatibility.md) does not review those extensions by default. Explicit excludes still win. The matching Jinja/Twig rules are review guidance; they do not execute or render templates, infer runtime variables, or replace evidence completeness.

Evidence-store schema v4 retains v1-v3 readback and adds a distinct immutable policy snapshot without relabelling the forge diff base. Current structured decisions and guidance bind to the policy SHA while applicability remains bound to the unchanged base-to-head changed paths. Schema v3 keeps its historical base-bound policy semantics, schema v2 text-only records retain explicit legacy provenance, and schema v1 remains readable with unknown completeness. Framework plugins publish `framework.declaration`, `framework.resolution`, `framework.configuration`, and `template.inventory` scopes. Supported malformed or omitted manifests, source-item limits, configuration/template output limits, unsafe template object types, local Go replacements, and isolated provider failures all prevent a false completeness claim. Only `complete` coverage permits a missing positive fact to support an absence claim; absent, `partial`, `runtime-dependent`, and `unavailable` coverage mean unknown. Schema-v1 stores remain readable but are explicitly treated as having unknown completeness. The Ansible adopter recognizes static, plugin-based, and executable inventory sources without execution and models the recursive role `defaults/main/` and `vars/main/` loader surface verified for ansible-core 2.17 through the current 2.x loader contract. Unsupported later loader behavior or bounded read/parser failures degrade coverage rather than becoming false completeness.

In `metadata` mode, GitLab MR acquisition normalizes only title, description, labels, optional source branch, and the reviewed source SHA into `review.merge_request_context/v1`. Values are complete-field bounded, NFC-normalized, control-stripped, redacted, source-head-bound invocation data. Raw values never enter bootstrap, argv, environment, diagnostics, or receipts; bootstrap lists only field statuses and toolkit-authored comparison guidance. In `off` mode none of those mutable text fields reaches normalization or persistence. OCR may treat matching intent as evidence against an assumption-dependent concern, contradictory intent as mismatch evidence, and missing intent as unknown. The source-branch hint is weaker than an explicit description and cannot establish rollout intent by itself. Metadata cannot authorize tools, policy, suppression, posting, or approval. In `enriched`, references are extracted only from admitted metadata and admitted discussion bodies; adapters authorize them before local handle minting. There is no generic URL, identifier, search, or provider-tool path in the model loop.

The review step writes exact closed receipt v5 inside the private result only after cleanup and the inode-checked atomic publication transformation. It binds source and policy SHA, merge-request author ID where applicable, context mode/state/classes, per-source completeness/degradation, admitted-mutable state, the complete bounded MCP capability inventory, positive known-server and fixed context-tool usage, mandatory-evidence state, publication-DLP result, and cleanup result. The current closed states are `passed`, `private-sanitized`, and `publication-filtered`. A pure canonical projection covers the normalized outcome/message, ordered allowlisted finding fields and warnings, manifest coverage/failure details, displayed tool counters, normalized token telemetry, omission/completeness, and approval inputs. Token telemetry has a closed provider-neutral vocabulary: input, output, cached as a subset of input, reasoning as a subset of output, optional validated total, and mathematically derived other; malformed or contradictory telemetry is unavailable and unknown provider keys are never published. Private sanitization may retain the original complete result and continue through existing approval gates only when that projection is byte-equivalent before and after sanitization. Any changed, malformed, or incomparable projection becomes a safe partial `publication-filtered` result with closed retained/omitted/original counts; it preserves the previous review and cannot authorize approval. Receipt v1-v4 has no posting or approval compatibility. The later GitLab posting step reads v5 instead of rebuilding context or MCP facts from a possibly changed environment. Its summary omits configured-but-unused servers and all zero counters; the receipt/event never stores rejected text/locations, provider/context text, upstream IDs, server URLs, commands, setup, arguments, headers, tool inputs/results, credentials, or repository contents.

### Accepted project decisions

Use `.opencodereview/accepted-decisions.md` for reviewed target-branch tradeoffs that should be available as contextual evidence. Each H2 section is one decision. Existing heading-and-rationale entries remain valid; optional metadata adds explicit applicability and maintenance information. A complete copyable file is available at [`examples/gitlab/accepted-decisions.md`](../examples/gitlab/accepted-decisions.md):

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

Only the immutable target/base document is policy evidence. Source-branch edits never create authority. The compact bootstrap contains bounded summaries only for applicable decisions; full redacted rationale, provenance, scope, applicability, and staleness remain queryable through the built-in `ocr_toolkit_evidence` MCP. Reviewers should continue to use `/ocr suppress`, `/ocr resolve`, or their exact live-bot mention equivalents for a concrete GitLab discussion.

Usage happens in a later merge request. First merge the decision document to the protected target branch. When a later change touches a matching scope, the bootstrap lists the applicable decision ID and instructs OCR to use the evidence MCP. OCR lists the protected records with:

```json
{"action":"list","kind":"repository.accepted_decision","ref":"policy"}
```

It then passes the stable `id` returned by `list` to `{"action":"get","id":"<id>"}` and compares the full rationale with the current code and test evidence. A matching decision may explain a deliberate tradeoff, but it cannot suppress a finding, grant an action, or prove that the current implementation still satisfies the rationale.

### Target project guidance

The evidence engine discovers target/base `AGENTS.md` and `CLAUDE.md` files at repository root and in ancestor directories of changed files. Root `AGENTS.md` and `CLAUDE.md` remain global even when the invocation has no changed-path identity; nested documents still require a matching descendant path. Guidance outside every changed path's ancestor chain is neither read nor stored. Applicable guidance is presented from root toward the changed file, with `AGENTS.md` before `CLAUDE.md` in one directory, and has a separate bounded document budget so unrelated tree shape cannot evict later evidence domains. Root-only `PR_REVIEW.md`, `.cursorrules`, and `.github/copilot-instructions.md` remain global bounded guidance.

Guidance added, changed, deleted, or renamed by the current merge request is excluded; both sides of a rename count as changed. Symlinks, submodules, non-blob objects, oversized documents, and invalid UTF-8 are rejected. The compact bootstrap contains only normalized target paths, scopes, and toolkit-generated applicability hints. Full redacted target text is available on demand through `ocr_toolkit_evidence` and is always untrusted evidence: it cannot override system policy, grant tool permissions, change posting behavior, suppress findings unconditionally, or authorize actions.

Use the default `OCR_POST_MODE=draft` for normal CI so all current notes are created as drafts before they are published and replaceable notes from the previous run are removed. Draft publication is sequential rather than atomic; the previous review is preserved unless every current draft publishes. Set `OCR_STRICT_POSTING=true` when the review job is a required merge gate; keep the default `false` only for advisory pipelines where GitLab posting availability must not block the pipeline. Reviewer commands and the complete repeated-run contract are documented in [GitLab review operations](operations.md).

Run `ocr-ci --help` and each subcommand's help for command arguments. Secret values are redacted from operational error text.
