# Environment configuration

Provider selection is an explicit CLI choice: [standalone local review](local.md)
uses `preflight --local` and `review --local`, independently of inherited CI
identity. It preserves the configured LLM and optional external MCP inputs, but
rejects unsupported change-request context channels.

Open Code Review Toolkit uses environment variables for CI/runtime configuration. Empty values are generally treated as absent. Exact defaults and safety caps are enforced by the runtime modules. **Bold variable names are required in the command, mode, example, or declaration scope stated in their `Required` cell.**

OCR behavior below refers to the exact `recommended_version` in the
[compatibility manifest](../compatibility/ocr-support.json) for this toolkit
revision, not arbitrary upstream releases.

## Toolkit runtime variables

These are the complete supported toolkit-owned runtime inputs. `Required` is scoped to the command or mode named in the behavior column; an unrelated command does not require the variable.

| Variable | Source / owner | Required | Exact default | Behavior |
| --- | --- | --- | --- | --- |
| **`OCR_LLM_URL`** | Operator / configure and preflight | Yes for review | None | Absolute credential-free HTTPS API root or compatible terminal inference endpoint; normalized through the shared provider owner. |
| **`OCR_LLM_TOKEN`** | Operator secret / `ocr-ci configure` | Yes for review | None | LLM credential; never written into generated context or receipts. |
| **`OCR_LLM_MODEL`** | Operator / configure and preflight | Yes for review | None | Exact model identifier passed to OCR and optional model validation. |
| `OCR_LLM_PROTOCOL` | Operator / `ocr-ci configure` | No | `openai` | Closed protocol: `openai`, `openai-responses`, or `anthropic`. |
| `OCR_LLM_AUTH_HEADER` | Operator / configure and preflight | No | `Authorization` | Valid HTTP header name used for the bearer credential. |
| `OCR_LLM_EXTRA_HEADERS` | Operator / configure and preflight | No | Empty object | JSON object of additional string headers; cannot duplicate the auth header. |
| `OCR_LLM_EXTRA_BODY` | Operator / `ocr-ci configure` | No | Unset | JSON object merged into the OCR LLM request configuration; completion-cap field conflicts are checked against the dedicated variable. |
| `OCR_LLM_MAX_COMPLETION_TOKENS` | Operator / `ocr-ci configure` | No | Unset (inherits OCR) | Positive decimal integer from `1` through `1000000`; sets the protocol-specific completion/output cap without changing prompt/context or aggregate review budgets. |
| `OCR_LLM_REASONING_EFFORT` | Operator / configure and preflight | No | Unset (no overlay) | Case-insensitive `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, or `max`; explicit `none` is sent, not omitted. Nonempty values require an OpenAI protocol. |
| `OCR_ANTHROPIC_DISABLE_THINKING` | Operator / `ocr-ci configure` | No | `false` | With the Anthropic protocol, exact `true` adds `thinking.type=disabled`. |
| `OCR_REVIEW_LANGUAGE` | Operator / shared language resolver | No | `English` | Allowed language label or BCP-47 tag used for the review. |
| `OCR_REVIEW_EFFORT` | Operator / `ocr-ci configure` | No | `medium` | Closed OCR quality preset: `low`, `medium`, or `high`; maps to one, two, or three review rounds. |
| `OCR_REVIEW_PROGRESS` | Operator / `ocr-ci review` | No | Empty / `false` | Case-insensitive `true` enables toolkit-only phase messages and a 30-second heartbeat on an interactive terminal or explicitly nonblocking embedding stream, capped at 120 messages per run. Conventional CI stderr pipes are deliberately unsupported. |
| `OCR_LLM_VALIDATE_MODEL` | Operator / `ocr-ci preflight` | No | `false` | `true` validates through `/models`; `auto` may use the offline allowlist; false values skip validation. |
| `OCR_LLM_MODELS_URL` | Operator / `ocr-ci preflight` | No | Derived from `OCR_LLM_URL` | Explicit absolute credential-free HTTPS metadata URL when validation is enabled or inference query parameters make derivation ambiguous. |
| `OCR_LLM_ALLOWED_MODELS` | Operator / `ocr-ci preflight` | No | Empty list | Comma-separated exact model identifiers for offline or `auto` validation. |
| `OCR_TELEMETRY_ENABLED` | Operator / `ocr-ci configure` | No | `false` | Exact `true` enables OCR telemetry configuration; OCR spans may include path-derived group keys, model-produced labels, and local grouping decisions. |
| `OCR_TELEMETRY_CONTENT_LOGGING` | Operator / `ocr-ci configure` | No | `false` | Exact `true` enables OCR content logging; keep disabled for private review data. |
| `OCR_TELEMETRY_EXPORTER` | Operator / `ocr-ci configure` | No | Empty string | Exporter name written only when telemetry is enabled. |
| `OCR_TELEMETRY_OTLP_ENDPOINT` | Operator / `ocr-ci configure` | No | Unset | OTLP endpoint written only when telemetry is enabled and the value is non-empty. |
| `OCR_REVIEW_CONTEXT_MODE` | Operator / review launcher | No | `off` | Closed selector: `off`, `metadata`, or protected-policy `enriched`. |
| `OCR_REVIEW_CONTEXT_ADAPTERS_JSON` | Removed legacy input | No | Removed; setting it is an error | Executable context adapters are not supported. Migrate external tools to governed registry v2. |
| `OCR_MCP_SERVERS_JSON` | Operator / governed federation | No | Empty version 2 registry | Strict registry-v2 object. GitLab accepts HTTPS upstreams; local accepts HTTPS or explicit stdio. Unknown fields and legacy shapes fail before OCR. |
| `OCR_MCP_REPLACE` | Removed legacy input | No | Removed; setting it is an error | Replacement/restoration semantics are not supported; the mandatory internal evidence MCP is unreplaceable. |
| `OCR_DLP_ENABLED` | Operator / shared review launcher | No | `true` | Strict boolean: `true`, `1`, `yes`, or `on`; `false`, `0`, `no`, or `off`; case-insensitive. Unset/empty is enabled. False disables context/federation and publication DLP for one run, emits a prominent warning, and makes the run approval-ineligible. Other values fail before OCR. |
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

`OCR_LLM_REASONING_EFFORT` is independent of the existing OCR review effort and
token budgets. Unset or empty leaves the request overlay unchanged. A nonempty
value is normalized to lowercase and sets `reasoning_effort` for `openai`, or
`reasoning.effort` for `openai-responses`, preserving other `reasoning` members.
When the shortcut is set, an equal value at the corresponding path in
`OCR_LLM_EXTRA_BODY` is allowed;
different values, incompatible field types or a non-object Responses `reasoning`
value fail before inference. Manual JSON values must already use the exact
lowercase wire spelling. Nonempty shortcuts are rejected for `anthropic`.

These paths follow the [official OpenAI reasoning contract](https://developers.openai.com/api/docs/guides/reasoning#reasoning-effort).
Supported values and defaults depend on the exact provider/model/protocol;
`none` is an explicit request and is not universally supported. Toolkit parsing
does not prove provider acceptance or application. Qualify unset, explicit `none`
and the intended effort in the deployment; HTTP success alone does not prove
that a gateway applied the setting. The toolkit never silently substitutes an
effort, model or protocol after rejection.

`OCR_LLM_MAX_COMPLETION_TOKENS` is optional and defaults to **unset**, which inherits the qualified OCR version's behavior. It accepts a positive decimal integer from `1` through `1000000` and writes one protocol-specific field:

| `OCR_LLM_PROTOCOL` | Generated `llm.extra_body` field |
| --- | --- |
| `openai` | `max_completion_tokens` |
| `openai-responses` | `max_output_tokens` |
| `anthropic` | `max_tokens` |

If `OCR_LLM_EXTRA_BODY` already owns that field, an exactly equal JSON integer is deduplicated. A different value, or a boolean, string, float, or null at that field, fails configuration with a migration error; remove the duplicate field or keep the same integer in both places. Other `OCR_LLM_EXTRA_BODY` members are preserved. Select an explicit completion cap only from the deployment's provider/model contract when a gateway reserves spending against the requested output cap; the toolkit does not recommend a provider-specific value.

The toolkit does not derive this value from `/models.max_completion_tokens`. That metadata is a model capability boundary, not an account spending limit or proof of how a gateway reserves request cost.

The inherited value is version-owned and may change with a qualified OCR upgrade. The qualified OpenAI request uses `max_completion_tokens=16384` when the variable is unset; [compatibility history](compatibility.md) records earlier values and their exact versions. Grouping requests use the same template-owned cap; an explicit toolkit override still applies to every protocol request. Deployments that require an invariant gateway-specific cap must set `OCR_LLM_MAX_COMPLETION_TOKENS` explicitly rather than depending on an OCR default.

### Review effort

`OCR_REVIEW_EFFORT` defaults to `medium` and is written to OCR's root `effort` configuration key. OCR maps `low`, `medium`, and `high` to one, two, and three review rounds and scales its 15-minute subtask base to 15, 30, or 45 minutes. The environment is operator-owned; merge-request text cannot change it. An explicit caller `--effort` passed after `ocr-ci review --` has normal OCR CLI precedence over the generated config, while an unknown environment value fails configuration before preview or model execution.

`OCR_REVIEW_PROGRESS=true` observes the same review in local and CI execution.
Messages contain only closed toolkit phase names; the observer never reads OCR
results, stderr artifacts or sessions, and does not change the agent audience.
Progress is not copied into results, Markdown, receipts or DLP inputs. The timer
stops on completion, exceptions, signals or the 120-message cap.

For a conventional blocking stderr pipe, including a GitLab runner job-log pipe,
the optional observer disables itself. A short write can still block after a
readiness check, while `dup()` and common `/dev/fd` reopens may share the
caller-owned descriptor's status flags; the toolkit does neither. A full
nonblocking pipe also disables progress rather than blocking the review. This has
no review, admission, output, or exit-status effect and does not suppress normal
final reports or CI logs. The toolkit does not create a tee, FIFO, background
writer, or another process to simulate a logging transport. Values other than
empty, `false` or `true` fail before review execution without echoing their
contents.

OCR may present filter-surviving comments to a later round as previously confirmed, but the toolkit does not accept that wording as validation. Its mandatory background prefix travels with every main request and requires prior/filter-surviving findings to remain unverified until current code, tests, or trusted evidence support them. Survival cannot change severity, suppress or resolve a finding, authorize approval, or enter a receipt as independent validation.

Effort controls review depth, not the prompt/context ceiling, per-call completion cap, aggregate token budget, or per-round tool limit. Semantic grouping and filtering can add requests even at `low`; higher effort can add further rounds until OCR stops early, reaches a coverage/budget boundary, or completes the configured depth.

## GitLab and provider variables

GitLab supplies the `CI_*` values in merge-request pipelines. The operator supplies the dedicated API token.

| Variable | Source / owner | Required | Exact default | Behavior |
| --- | --- | --- | --- | --- |
| **`GITLAB_API_TOKEN`** | Operator secret | Yes for provider reads and posting | None | Dedicated GitLab API credential used with `PRIVATE-TOKEN`. |
| **`CI_API_V4_URL`** | GitLab predefined | One of this or `CI_SERVER_URL` for provider reads | Derived as `${CI_SERVER_URL}/api/v4` | Absolute HTTPS GitLab API v4 root. |
| **`CI_SERVER_URL`** | GitLab predefined | Yes for posting; alternative owner for API root | `https://gitlab.com` in posting only | Absolute HTTPS GitLab server root. GitLab CI normally always defines it. |
| **`CI_PROJECT_ID`** | GitLab predefined | Yes in merge-request mode | None | Bounded numeric project identity used for provider APIs and receipts. |
| **`CI_MERGE_REQUEST_IID`** | GitLab predefined | Yes in merge-request mode | None | Bounded numeric merge-request identity and mode signal. |
| **`CI_MERGE_REQUEST_SOURCE_BRANCH_SHA`** | GitLab predefined | Yes for the recommended review range | Falls back to `CI_COMMIT_SHA` only where explicitly documented | Exact reviewed source head used by the review, receipt, and posting revalidation. |
| **`CI_MERGE_REQUEST_DIFF_BASE_SHA`** | GitLab predefined | Yes for the recommended review range | None | Exact merge-request diff base passed to OCR and evidence collection. |
| `CI_COMMIT_SHA` | GitLab predefined | No | None | Fallback head identity when the MR-specific source SHA is unavailable; it does not replace the diff base. |
| `CI_PIPELINE_ID` | GitLab predefined | No | Omitted | Optional bounded invocation identity stored as non-authoritative evidence. |
| `CI_JOB_ID` | GitLab predefined | No | Omitted | Optional bounded invocation identity stored as non-authoritative evidence. |
| **`CI_PIPELINE_SOURCE`** | GitLab predefined / example rules | Yes for example job selection | None | The public example runs review jobs only for `merge_request_event`. |
| `OCR_GITLAB_TARGET_PROTECTION_MODE` | Operator / GitLab snapshot acquisition | No | `required` | Closed selector: `required` rejects an unprotected target before OCR; `unprotected` permits it only in the constrained mode described below. An explicitly assigned empty, whitespace, mixed-case, malformed, or unknown value fails closed. |

## Example-local variables

These names belong to `examples/gitlab/ocr-review.gitlab-ci.yml`; they are shell or pipeline controls, not additional toolkit configuration.

| Variable | Source / owner | Required | Exact default | Behavior |
| --- | --- | --- | --- | --- |
| **`OCR_VERSION`** | Example pipeline | Yes | `v` + manifest `recommended_version` | Exact binary release pinned with its asset checksum in the [pipeline](../examples/gitlab/ocr-review.gitlab-ci.yml); not resolved dynamically. |
| **`OCR_SHA256`** | Example pipeline | Yes | Manifest SHA-256 for `opencodereview-linux-amd64` | Exact digest pinned alongside `OCR_VERSION` in the pipeline; must belong to the same release entry. |
| **`OCR_TOOLKIT_VERSION`** | Example pipeline | Yes | `0.11.0` | Exact toolkit wheel release installed by the current published example. |
| **`OCR_TOOLKIT_CHECKSUMS_URL`** | Example pipeline | Yes | Release URL derived from `OCR_TOOLKIT_VERSION` | Toolkit `SHA256SUMS` URL. |
| `OCR_TOOLKIT_WHEEL` | Example shell | Computed | `open_code_review_toolkit-${OCR_TOOLKIT_VERSION}-py3-none-any.whl` | Exact wheel filename selected from the release. |
| `OCR_TOOLKIT_WHEEL_SHA256` | Example shell | Computed | Matching value from `SHA256SUMS` | Digest checked before installing the toolkit wheel. |
| `OCR_MAX_TOOLS` | Example pipeline / OCR CLI | No | `0` | OCR uses template default `100`; `1-49` reports normalization to `50` but remains effectively `100`, and only a value above `100` raises the cap. |
| `OCR_MAX_TOKENS_BUDGET` | Example pipeline / OCR CLI | No | `0` | Non-negative aggregate OCR token ceiling; `0` is unlimited. |

During Draft qualification, install the toolkit artifact built from the reviewed
commit. The example's toolkit-version pin becomes usable after the later stable
release publication; toolkit 0.11.0 supports the qualified OCR runtime.

## Dynamic adapter and MCP inputs

The adapter names are removed runtime inputs documented above; this table lists
only credential names dynamically referenced by current registry v2.

| Variable | Source / owner | Required | Exact default | Behavior |
| --- | --- | --- | --- | --- |
| **Names declared by MCP `env_from`** | Operator / `OCR_MCP_SERVERS_JSON` | Yes when declared | None | Inject a local-profile stdio MCP environment value by exact variable name. |
| **Names declared by MCP `token_from`** | Operator / `OCR_MCP_SERVERS_JSON` | Yes when declared | None | Supply an HTTPS bearer token to the toolkit-owned gateway without storing the secret in registry JSON or OCR configuration. |
| **Names declared by MCP `headers_from`** | Operator / `OCR_MCP_SERVERS_JSON` | Yes when declared | None | Supply an HTTPS header value to the toolkit-owned gateway without storing the secret in registry JSON or OCR configuration. |

## Governed MCP federation and trust boundary

The toolkit always installs the fixed `ocr_toolkit_evidence` server and requires successful evidence use independently of federation. Operator configuration cannot remove, replace, rename, or shadow it. External upstreams are not passed through to OCR. The toolkit starts one bounded federation gateway, discovers and freezes each explicit allowlist, and exposes only `server__tool` aliases through a fixed private relay. The gateway owns schema and argument validation, URL origins, outbound and inbound DLP, byte/item/time/call budgets, cache accounting, and cleanup.

`OCR_MCP_SERVERS_JSON` accepts only the closed version-2 registry. Server and tool names use ASCII letters, digits, underscore or hyphen, begin with a letter, and cannot contain `__`; aliases cannot collide with toolkit tools. Each tool policy defaults to `assurance: "advisory"`; use explicit `review_read` only after the operator has established that the tool is a bounded read whose successful use may remain approval-eligible. This assurance is operator policy, not a server annotation.

A GitLab-MR external server therefore looks like:

```json
{"version":2,"servers":{"review_evidence":{"transport":{"type":"https","url":"https://review-evidence.example.invalid/v1/mcp"},"auth":{"scheme":"Bearer","token_from":"REVIEW_EVIDENCE_MCP_TOKEN"},"tools":{"read_review_evidence":{"assurance":"advisory","resource_origins":["https://review-evidence.example.invalid"]}}}}}
```

GitLab accepts only `{type:"https",url:...}`. Local review also accepts `{type:"stdio",command:...,args:[...],env_from:{...}}` with an absolute operator-selected executable, no shell or setup hook, and owned child-process cleanup. HTTPS secrets use `auth.token_from` or `headers_from`; missing variables fail preflight. Literal secrets, redirects, ambient proxy trust, arbitrary link retrieval, resource/media projection, server-directed headers, sampling, roots, elicitation and OAuth are not supported.

The official Python MCP SDK v2 is the primary toolkit integration boundary. SDK major versions do not select the wire protocol: the gateway negotiates each upstream independently and supports the explicitly qualified SDK v1/v2 peers and protocol revisions. Unsupported capabilities or revisions fail explicitly.

Receipt v9 embeds a content-free `ocr.federation/v1` receipt and independently reconciles OCR attempts with gateway terminal outcomes for every exported alias. Used advisory tools, known denied/failed calls, or an accounting mismatch make the run comment-only. Missing, corrupt, unfinalized or cleanup-uncertain federation evidence blocks normal publication. Configured-but-unused services and successful `review_read` use do not independently block approval. Commands, URLs, arguments, results, credentials, paths, identifiers and raw errors never enter the receipt.

### DLP escape hatch

`OCR_DLP_ENABLED` is resolved once before acquisition. It accepts the strict boolean families `true|1|yes|on` and `false|0|no|off`, case-insensitively; unset or empty defaults to enabled. False bypasses context/federation ingress and egress DLP plus publication DLP for that run. Schema, size, origin, time, identity, cleanup, evidence, posting-transaction and other non-DLP gates remain enforced. The run is always comment-only, even if no unsafe value is observed.

Disabled DLP can send sensitive material to an upstream MCP or the model and can write it to local Markdown or publish it to GitLab. Re-enabling DLP cannot retract data already sent or published. Diagnose suspected false positives locally with `--preserve-private-artifacts` before using this escape hatch, inspect retained material only on the trusted host, and remove it after diagnosis. Local Markdown and GitLab use the same resolved setting and warning formatter; logs and Technical details disclose the mode and risk without copying protected values.

### GitLab target-protection selector

`OCR_GITLAB_TARGET_PROTECTION_MODE` is operator-owned and parsed before policy acquisition or OCR execution. If it is unset, `required` preserves the secure default: GitLab must report the captured target branch as protected. The exact opt-in `unprotected` permits an unprotected target; it does not force limited behavior when GitLab reports that target as protected. Explicit empty strings and every value other than exact lowercase `required` or `unprotected` fail closed.

When the opt-in meets an actually unprotected target, the toolkit binds the exact source SHA, target SHA, and `unprotected` state in receipt v9 and enforces a constrained review. Context `off` and bounded untrusted `metadata` are allowed. `enriched`, legacy adapter configuration, governed federation, and inherited external OCR MCP configuration are rejected before OCR. The toolkit-owned immutable repository-evidence MCP remains mandatory. Repository Rules are required and are read only as bounded untrusted model guidance from the exact captured target SHA; source Rules cannot authorize their own review. Structured target guidance and accepted decisions are omitted. No target-derived input can enable tools, external acquisition, suppression, posting authority, or approval.

An unprotected receipt is structurally automatic-approval-ineligible regardless of `OCR_AUTO_APPROVE`; the approval executor and GitLab approval endpoint are not reached. A fully validated receipt alone adds *The target branch was not protected in GitLab. This review ran in limited, comment-only mode.* immediately after the normal primary status line. The line does not make complete coverage partial and does not alter clean, findings, warning, partial, budget-stopped, failed, or publication-filtered outcome semantics. A protected target running under the permissive setting keeps normal protected-policy behavior and does not show the line. Missing, malformed, legacy, or contradictory receipt state cannot authorize it.

### Review-context selector

`OCR_REVIEW_CONTEXT_MODE` is parsed before provider acquisition or OCR execution. Missing, empty, and `off` select identity-only acquisition: the provider still validates the source SHA, protected target identity, and positive merge-request author ID needed by policy and approval, but title, description, labels, and source branch are not normalized or stored. `metadata` requires a validated GitLab merge-request environment and admits only the existing bounded title, description, label, and optional source-branch projection. Every field reports a closed status; metadata is `complete` only when every selected field is absent or admitted. Invalid, over-limit, collision, redaction-limit, or partial states are `degraded`.

`enriched` requires a validated GitLab merge request and a valid `.opencodereview/review-context-policy.json` read only from the captured protected-target policy SHA. Current policy v4 adds policy-selected generic GitLab discussions, verified remediation threads, and protected same-revision CI outcomes through a separate private store and fixed `context_list`/`context_get` tools. A source policy cannot expand access; missing or invalid protected policy fails before OCR. Policy v1-v3 remains parse-only for migration: safe selectors continue, optional references are skipped, and required references create required degradation. See [Bounded review context](review-context.md) for exact migration, handles, DLP, completeness, receipt, and cleanup contracts.

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

`OCR_MAX_TOOLS` is independent of all three token controls. Leave the example
default at `0` so OCR uses its embedded template limit of `100` per subtask.
OCR reports values `1-49` as normalized to the minimum `50`, but both
that target and explicit `50` remain below the template default and therefore
remain effectively `100`. Use `101` or greater only when deliberately raising
the loop cap. A recognized normalization
is emitted only as a toolkit-authored CI notice; its raw stderr is not added to
findings, result warnings, receipts, DLP inputs, telemetry, or
automatic-approval signals.

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
partial/budget outcomes, any receipt other than v9, an unprotected target, disabled DLP, degraded selected metadata, used advisory federation tools or uncertain federation accounting, required context degradation, a DLP-rejected selected source, admitted remediation context,
and findings omitted by `OCR_MAX_POST_COMMENTS`. For receipt v9 on a protected target, complete metadata, complete non-remediation enrichment, private-only sanitization, unused federation services, successful `review_read` use, and the built-in evidence/context MCP are not blockers. GitLab posting also revalidates the receipt-bound source SHA and author ID, and skips without writing when the author changed or the toolkit user authored the merge request. There are intentionally no
environment variables for policy thresholds or category lists in this release.

`ocr-ci review --result PATH --stderr PATH -- ...` executes OCR without posting, creates private artifacts, and prints a bounded redacted stderr excerpt to the CI log when OCR fails. It accepts only a regular, single-link result artifact and atomically replaces it with the admitted owner-only copy. A validated GitLab merge-request review receives receipt v9; a local review remains receipt-less because local Git state cannot establish GitLab protection. The compatible receipt-less posting path cannot use receipt-derived federation status, the unprotected-target limitation, or automatic approval. For local diagnosis, `--preserve-private-artifacts` retains owner-only private review material without a posting receipt. Inspect it locally before considering `OCR_DLP_ENABLED=false`, never upload or post it, and remove it afterward. The validated GitLab profile rejects this flag before OCR execution. Disabling DLP can expose sensitive content through model/service egress, local Markdown or GitLab and cannot retract prior disclosure. `OCR_POST_ERROR_DETAILS=1` separately opts into the bounded safe stderr excerpt in a GitLab failure note.

## Repository evidence

`ocr-ci review` owns this lifecycle. Before OCR starts it collects the exact immutable `--from`/`--to` refs (or the parent/commit pair selected by `--commit`), validates the exact GitLab MR identity and lifecycle, writes bounded redacted schema-versioned evidence, builds OCR's MCP registry with the mandatory evidence entry plus each independently configured optional server, reads the registry back, self-queries the evidence summary/list/get contract, and supplies the matching compact bootstrap to OCR. An already `merged` or `closed` MR stops before evidence and OCR with only an identity-bound `ocr.pre-execution-status/v3`; `post` upserts the corresponding static toolkit note. Those parent-process preflight calls are not counted as model use. The same preflight-qualified OCR executable first receives the exact production refs, rules, selection options, and background under `review --preview`; there is no toolkit threshold setting or duplicated OCR threshold constant. An exact recognized OCR soft background diagnostic becomes a toolkit-authored numeric `ocr.toolkit-advisory/v1` value only after publication DLP and appears in the bounded CI log plus GitLab Technical details. It is not an OCR warning, receipt or DLP input, coverage signal, telemetry field, or approval blocker. An exact recognized hard character/file-size rejection stops before model execution and leaves only an identity-bound numeric `ocr.pre-execution-status/v3` outcome for static GitLab reporting; the private path and raw OCR diagnostic are not published. Unknown preview failures fail closed through the generic diagnostic path, and the actual review independently revalidates the background. During OCR, the built-in MCP records count-only attempted and completed `summary`, `list`, `get`, `search`, and `coverage` actions without arguments, queries, IDs, paths, results, or content. Unknown or malformed MCP-dispatched primary-tool actions increment only a closed `unattributed` attempt counter. OCR also counts a dynamic tool request before parsing its JSON arguments; a parse failure never reaches the MCP owner, so receipt finalization adds only that count-only by-tool residual to `unattributed`. The parent reads and removes private action receipt v3 before cleanup. Receipt v9 is approval-valid only when MCP-received attempts do not exceed OCR's authoritative `tool_calls.by_tool` entries and every residual OCR attempt is accounted as unattributed; failed or malformed attempts cannot satisfy the mandatory completed `summary`, become successful evidence use, or authorize approval. Missing, malformed, raced, or mismatched attribution fails review finalization before a normal publishable result exists. OCR `--background-file` takes precedence over inline `--background`, so `ocr-ci review` rejects caller forms of both options, including split and `--option=value` syntax, and remains the sole owner of the bootstrap input; caller `--preview` is likewise rejected because the toolkit owns this gate. OCR provides `--output`, but `ocr-ci review` rejects its long, equals, short, and attached forms because the toolkit must remain the sole owner of the private result descriptor, atomic parsing, cleanup, and posting handoff. The stage-grouped OCR terminal retry report remains private and does not enter toolkit telemetry, receipts, DLP, findings, severity, outcomes, or approval. A completed OCR review is accepted only when structured `tool_calls.by_tool` proves at least one `ocr_toolkit_evidence` attempt and action receipt v3 proves a completed summary; a legitimately skipped no-supported-files review remains exempt.

The private `.review-context/evidence.json`, `.review-context/bootstrap.md`, repository-policy `.review-context/policy-rules.json`, and count-only evidence-action receipt/lock are internal implementation details, not public path configuration. Keep `.review-context/` ignored. The directory is mode `0700`, regular files are mode `0600`, and symlink, hard-link, non-regular, or unexpectedly permissive receipt targets are rejected. In GitLab MR pipelines, the provider adapter captures the current protected target SHA, fetches that exact immutable object when needed, and materializes only an in-repository `--rule` blob from it; explicit absolute rules outside the repository remain operator-owned. OCR still reviews the original forge diff-base-to-source-head range. The collector reads Git objects without checkout, does not follow repository symlinks or submodules, never executes repository content, and treats source-ref policy changes as untrusted.

The compact bootstrap contains the same safe inventory of independent server/tool entries that was written to OCR configuration. Start with `ocr_toolkit_evidence(action=summary)` once. Use its paginated/filterable `list` for a known kind or delta and stable-ID `get` only for selected records. Use `ocr_toolkit_evidence_search` only when a location or identity is unknown: its NFKC/case-folded query accepts 1–128 characters and at most eight literal tokens, rejects regex/wildcards/operators/control and bidi/format characters, searches only DLP-admitted paths, identities, and per-kind allowlisted scalars, and returns stable IDs plus closed metadata without echoing the query or matched value. Search and list use the same delta contract: `kind=repository.evidence_delta` selects base/head deltas, optional `delta_kind` narrows their original fact kind, and a ref filter is not accepted for those cross-ref records. Before a negative claim, call `ocr_toolkit_evidence_coverage` with an exact kind/domain and base/head ref. Exact component and path are required for `absence_authoritative=true`; an omitted scope is a broad discovery query and remains `unknown`. Only applicable complete coverage, zero matches, and no store-admission or response truncation produces authoritative absence; missing, partial, runtime-dependent, unavailable, broad, mismatched, or truncated scope is `unknown`. Stop once the required evidence is sufficient. Stable IDs returned by list or search can be passed to `get`. A unique semantic fact retains the established compact before/after value. If one semantic identity has multiple sources, or moves between sources, the value becomes a deterministic list of `source_path` and `fact` objects so no accepted record is overwritten. The ordinary unfiltered list remains facts and scoped coverage only. All three tools read the same committed store and have no mutation, network, arbitrary file, or shell path. Optional MCP entries can coexist with but cannot remove or shadow the mandatory server.

Evidence-store schema v2 includes closed `framework.detected` (`repository.framework-evidence/v1`) and `template.file` (`repository.template-evidence/v1`) facts from package-owned static plugins. Current plugins cover Jinja2, Echo/Fiber, Symfony/Twig, and React/Next with related gRPC, TypeScript, and Vite declarations. Plugins consume only already bounded immutable manifest/tree evidence: they cannot execute repository commands, load repository code, use network access, or start a second MCP server. Framework versions use the ecosystem's deterministic source: lock files for Python, Composer, and JavaScript, but the direct requirement or effective replacement in `go.mod` for Go. Local Go replacements remain explicit partial evidence rather than being mistaken for the replaced module version. Templates and configuration paths belong to the nearest manifest-root component; conventional Ansible-role templates retain the role root. The exact component `.` denotes the repository root, while names such as `repository` are ordinary top-level paths; the same identities filter facts, coverage, and deltas through `ocr_toolkit_evidence`. Detailed declarations, resolutions, effective replacements, configuration/template paths, component scopes, and redacted base/head deltas remain available through its summary/list/get actions.

Implementation-wise, package and automation metadata is normalized by the internal `ocr_toolkit.evidence.ecosystems` source-adapter layer before framework plugins consume it. This is not a user-configurable runtime plugin namespace: adapter registration, bounded immutable reads, storage, and MCP serving remain toolkit-owned closed contracts.

The GitLab `rules.json` example uses additive `include` entries for `.j2`, `.jinja`, `.jinja2`, `.twig`, and conventional Ansible-role template paths because the [recommended OCR](compatibility.md) does not review those extensions by default. Explicit excludes still win. The matching Jinja/Twig rules are review guidance; they do not execute or render templates, infer runtime variables, or replace evidence completeness.

Evidence-store schema v4 retains v1-v3 readback and adds a distinct immutable policy snapshot without relabelling the forge diff base. Current structured decisions and guidance bind to the policy SHA while applicability remains bound to the unchanged base-to-head changed paths. Schema v3 keeps its historical base-bound policy semantics, schema v2 text-only records retain explicit legacy provenance, and schema v1 remains readable with unknown completeness. Framework plugins publish `framework.declaration`, `framework.resolution`, `framework.configuration`, and `template.inventory` scopes. Supported malformed or omitted manifests, source-item limits, configuration/template output limits, unsafe template object types, local Go replacements, and isolated provider failures all prevent a false completeness claim. Only `complete` coverage permits a missing positive fact to support an absence claim; absent, `partial`, `runtime-dependent`, and `unavailable` coverage mean unknown. Schema-v1 stores remain readable but are explicitly treated as having unknown completeness. The Ansible adopter recognizes static, plugin-based, and executable inventory sources without execution and models the recursive role `defaults/main/` and `vars/main/` loader surface verified for ansible-core 2.17 through the current 2.x loader contract. Unsupported later loader behavior or bounded read/parser failures degrade coverage rather than becoming false completeness.

In `metadata` mode, GitLab MR acquisition normalizes only title, description, labels, optional source branch, and the reviewed source SHA into `review.merge_request_context/v1`. Values are complete-field bounded, NFC-normalized, control-stripped, redacted, source-head-bound invocation data. Raw values never enter bootstrap, argv, environment, diagnostics, or receipts; bootstrap lists only field statuses and toolkit-authored comparison guidance. In `off` mode none of those mutable text fields reaches normalization or persistence. OCR may treat matching intent as evidence against an assumption-dependent concern, contradictory intent as mismatch evidence, and missing intent as unknown. The source-branch hint is weaker than an explicit description and cannot establish rollout intent by itself. Metadata cannot authorize tools, policy, suppression, posting, or approval. In `enriched`, references are extracted only from admitted metadata and admitted discussion bodies; adapters authorize them before local handle minting. There is no generic URL, identifier, search, or provider-tool path in the model loop.

For a validated GitLab merge-request profile, the review step writes exact closed receipt v9 only after cleanup and the inode-checked atomic publication transformation. It binds source/policy/target identities, actual target protection, author, context and legacy-policy state, DLP mode, per-source completeness, mandatory evidence, content-free federation reconciliation, stage-aware publication accounting and cleanup. Receipt v1-v8 cannot authorize current posting or approval. A present incomplete or invalid receipt is rejected before prior review state or findings are read; only a genuinely absent receipt selects the compatible receipt-less path. The receipt never stores queries, scopes, rejected text or locations, provider/context text, upstream IDs, URLs, commands, arguments, headers, credentials, tool inputs/results, or repository contents.

The public projection may be incomplete while its validated original manifest
still proves complete OCR coverage. Posting reports those dimensions separately
and never feeds filtered warnings into legacy failed-item inference.

Publication DLP admits horizontal tab only in the closed `existing_code` and
`suggestion_code` finding fields, after every other size, secret, PII,
forbidden-value and laundering check passes. Horizontal tab in any other field,
and every other unsupported control/format character, remains blocking.

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
