# Bounded review context

Open Code Review Toolkit can enrich one validated forge review with bounded merge-request metadata, discussions, verified remediation history, and records resolved by operator-managed adapters. GitLab is the current provider implementation; acquisition normalizes into provider-neutral broker views before storage. Enrichment is a single pre-OCR phase. OCR remains the only review engine, and its model loop can read only committed local handles through the toolkit's existing built-in MCP process.

## Modes and lifecycle

`OCR_REVIEW_CONTEXT_MODE` is a closed selector:

- Empty or `off` validates immutable review and posting identities but does not normalize or persist mutable merge-request text.
- `metadata` additionally admits bounded title, description, labels, and source-branch text.
- `enriched` requires a validated GitLab merge-request environment and a valid protected-target policy. It includes the same metadata projection, a stable bounded GitLab discussion snapshot, verified toolkit-owned remediation threads, and policy-recognized external records when selected. Missing or invalid policy stops the review before OCR.

The lifecycle is fixed: capture the protected-target SHA; load policy from that immutable object; acquire and authorize records; normalize, DLP-check, and atomically commit the private context store; run one OCR review in an isolated home; serve only local handles; remove session, adapter, and context artifacts; then validate/project the complete OCR result and attach receipt v5 through one inode-checked atomic replacement. A cleanup or publication-validation failure blocks ordinary result publication.

## Protected-target policy

The only policy path is `.opencodereview/review-context-policy.json`. The toolkit reads it as a bounded regular Git blob from the captured protected-target policy SHA. A source-branch or working-tree copy has no authority. Missing, symlink, submodule, oversized, invalid UTF-8, duplicate-key, unknown-field, unknown-version, or impossible-projection input fails closed.

The following complete v2 policy selects generic GitLab discussions, verified toolkit remediation threads, and issue keys with protected prefix `DEMO`:

```json
{
  "schema_version": "ocr.review-context-policy/v2",
  "budgets": {
    "max_records": 32,
    "max_chars": 48000,
    "max_bytes": 96000,
    "max_lines": 1200,
    "timeout_ms": 15000
  },
  "forge_discussions": {
    "required": false,
    "account_classes": ["automation", "user"],
    "include_resolved": false,
    "include_outdated": false,
    "max_age_seconds": 2592000,
    "max_threads": 20,
    "max_replies_per_thread": 10,
    "max_items": 100,
    "budgets": {
      "max_chars": 12000,
      "max_bytes": 24000,
      "max_lines": 300
    },
    "projections": {
      "retrieve": ["descriptor", "digest", "expiry", "state", "text", "version"],
      "model": ["descriptor", "state", "text"],
      "publish": ["descriptor", "state"],
      "retain": ["digest", "expiry", "state", "version"]
    }
  },
  "remediation_threads": {
    "required": false,
    "account_classes": ["automation", "system", "user"],
    "include_resolved": false,
    "include_outdated": false,
    "max_age_seconds": 2592000,
    "max_threads": 20,
    "max_replies_per_thread": 10,
    "max_items": 100,
    "budgets": {
      "max_chars": 12000,
      "max_bytes": 24000,
      "max_lines": 300
    }
  },
  "references": [
    {
      "adapter": "tracker",
      "tenant": "engineering",
      "resource_class": "issue",
      "recognizer": {"type": "issue_key", "prefix": "DEMO"},
      "required": true,
      "max_records": 8,
      "max_age_seconds": 31536000,
      "budgets": {
        "max_chars": 4000,
        "max_bytes": 8000,
        "max_lines": 100
      },
      "projections": {
        "retrieve": ["descriptor", "digest", "expiry", "state", "text", "version"],
        "model": ["descriptor", "state", "text"],
        "publish": ["descriptor", "state"],
        "retain": ["digest", "expiry", "state", "version"]
      }
    }
  ]
}
```

The top-level aggregate budget limits independent record, character, UTF-8 byte, physical-line, and wall-time dimensions. Each source has its own text, age, item, and provider-specific limits. Hitting one limit does not silently relabel the source complete.

Discussion account classes are the closed set `user`, `automation`, `system`, and `toolkit_bot`. GitLab classifies accounts before storage and replaces display identity with a run-local pseudonym. Remediation reply classes cannot include `toolkit_bot`; the separately verified root owns the toolkit-bot role. Name, username, email, avatar/profile URL, and raw provider IDs are never model fields.

### Choosing a discussion policy

The runtime always reads the fixed protected-target path `.opencodereview/review-context-policy.json`; the filenames under `examples/gitlab/context/` are templates to copy to that path, not alternative runtime paths.

| Review need | Start from | Keep these selectors | Adapter configuration |
| --- | --- | --- | --- |
| Ordinary MR conversation only | `policy-discussions.json` | `forge_discussions`; remove `remediation_threads` | `OCR_REVIEW_CONTEXT_ADAPTERS_JSON=[]` |
| Earlier OCR finding plus human remediation replies only | `policy-discussions.json` | `remediation_threads`; remove `forge_discussions` | `OCR_REVIEW_CONTEXT_ADAPTERS_JSON=[]` |
| Both ordinary conversation and remediation history | `policy-discussions.json` | Keep both selectors | `OCR_REVIEW_CONTEXT_ADAPTERS_JSON=[]` |
| Discussions plus authorized issue/document records | `policy-adapters.json` | Keep the needed discussion selectors and references | Supply one matching reviewed adapter allowlist |

Use policy v1 unchanged only when an existing project needs generic discussions or references and does not need remediation history. Choose policy v2 for any `remediation_threads` selector; v2 may also select generic discussions and references.

Start each discussion source with `required: false`. Set it to `true` only when the review must treat an unavailable, mutated, DLP-rejected, or bounded-partial source as a blocking loss of required evidence. `required` does not mean that at least one matching thread must exist: a stable complete snapshot with zero selected threads is still complete. `include_resolved` and `include_outdated` should remain false unless historical or stale anchors are intentionally relevant. Keep `account_classes` to the smallest set needed; `remediation_threads.account_classes` applies to replies and cannot include `toolkit_bot`.

Generic `forge_discussions` can include non-toolkit conversations and its policy-controlled model projection. `remediation_threads` includes only roots verified against the live bot ID and toolkit marker/fingerprint, then returns the root and ordered replies through a fixed non-configurable model projection. A verified remediation root is excluded from generic discussions even when both selectors are enabled.

Safely admitted generic discussions do not independently disable automatic approval. Any admitted remediation thread does, because its text is historical review evidence rather than proof that current code is fixed. Any DLP rejection blocks approval regardless of `required`; optional non-DLP degradation stays visible but cannot prove absence. The public enriched mode recipes set `OCR_AUTO_APPROVE=false` while operators qualify these distinctions.

References bind one operator-configured adapter, tenant alias, `issue` or `document` resource class, required/optional semantics, bounds, projections, and one toolkit-authored recognizer:

- `{"type":"issue_key","prefix":"DEMO"}` recognizes keys such as `DEMO-42` with the exact protected prefix.
- `{"type":"https_url","origin":"https://docs.example.invalid","path_prefix":"/published/"}` recognizes only HTTPS URLs at that exact origin and path prefix.
- `{"type":"explicit"}` recognizes `[[context:issue:rollout-record]]` or `[[context:document:architecture-note]]` for the matching resource class.

Candidates are extracted only from admitted merge-request metadata and admitted discussion bodies. Recognition grants no access; every candidate still crosses adapter authorization. Configurable regular expressions, repository-wide search, arbitrary URLs, and arbitrary identifiers are not supported.

Projection fields are sorted unique lists. `model`, `publish`, and `retain` must each be subsets of `retrieve`. Retention is limited to `state`, `count`, `digest`, `version`, and `expiry`; it cannot retain text, upstream identifiers, URLs, commands, transport data, or personal display data. Retrieval, model egress, publication, and retention are deliberately separate decisions.

Policy `ocr.review-context-policy/v1` remains accepted for existing protected configurations and supports aggregate budgets, `forge_discussions`, and references. Policy `ocr.review-context-policy/v2` is additive and permits the optional `remediation_threads` selector; v1 rejects that field instead of interpreting it with weaker semantics. New examples use v2. This compatibility is for reviewed policy documents, not persisted runtime state: reviews and stores are ephemeral, and the private store accepts only `ocr.context-store/v2`. Adapter frames and receipt v5 likewise require their exact schema. Discriminators prevent an old or different field set from inheriting current authorization or approval meaning; there is no store or receipt migration path.

## Operator adapter allowlist

`OCR_REVIEW_CONTEXT_ADAPTERS_JSON` is an environment-only JSON array. Protected policy may select and narrow an entry, but it cannot create a command, endpoint, tenant, resource class, credential, or field permission.

A stdio entry has exact common fields plus an absolute command, bounded arguments, and names of environment variables to copy:

```json
[
  {
    "name": "tracker",
    "type": "stdio",
    "tenants": ["engineering"],
    "resource_classes": ["issue"],
    "command": "/opt/ocr-context-proxy/bin/ocr-context-proxy",
    "args": ["--stdio"],
    "env_from": ["TRACKER_CONTEXT_TOKEN"]
  }
]
```

The toolkit uses no shell or setup hook. It starts the exact executable with a clean allowlisted environment and an isolated owner-only working directory/home, exchanges one bounded JSONL request and response, enforces one deadline across request delivery, response acquisition, and process exit, terminates the process group on failure, and retains only private bounded redacted stderr while the run is active.

A remote entry uses one absolute HTTPS endpoint and maps HTTP header names to environment variable names:

```json
[
  {
    "name": "tracker",
    "type": "remote",
    "tenants": ["engineering"],
    "resource_classes": ["issue"],
    "url": "https://context-proxy.example.invalid/v1/authorize-and-resolve",
    "headers_from": {"Authorization": "TRACKER_CONTEXT_AUTHORIZATION"}
  }
]
```

Remote transport verifies TLS, disables ambient proxies and redirects, rejects credentials in URLs and literal secret headers, validates status and content type, streams within a byte bound, and applies the aggregate deadline. Both transports implement the same toolkit-owned protocol. Do not point this setting at an arbitrary MCP or vendor API; place any issue tracker, wiki/document service, or read-only MCP bridge behind a proxy that implements the fixed protocol and enforces object authorization.

## Fixed adapter protocol

The only operation is `authorize_and_resolve`. A request has exact schema `ocr.context-adapter-request/v1` and fields `operation`, `request_id`, `run_id`, `adapter`, `tenant`, `resource_class`, `candidate`, `requested_fields`, and `limits` (`max_chars`, `max_bytes`, `max_lines`, `max_age_seconds`, `deadline_ms`).

An admitted response has exact schema `ocr.context-adapter-response/v1`, matching `request_id` and `run_id`, `status: "admitted"`, `canonical_object`, immutable `version`, `expiry`, and a `record` whose keys exactly equal `requested_fields`. A non-admitted response contains only the matching identities, `status: "unavailable"`, and `reason: "unavailable"`. Missing, denied, foreign-tenant, and unauthorized objects deliberately share that result.

Unknown fields/statuses, mismatched identities, changed version/expiry, partial or multiple frames, invalid UTF-8, excess bytes, timeout, redirect, or transport failure make the record unavailable and mint no handle. The adapter's own schema, description, endpoint, command, headers, diagnostics, and upstream identifiers never enter the model context or receipt.

## GitLab discussions, handles, and completeness

The GitLab owner reads the exact validated project and merge request with bounded pagination. It does not fetch another page after the protected thread bound is filled; a provider-declared next page becomes a visible omission. It reads the ordered snapshot twice and admits records only when the identity and digest match. Reordering, edits, changed pages, invalid identity/classification, unsupported notes, or limit exhaustion remains visible as `mutated`, `partial`, or `unavailable`; it is never treated as proof that no record exists.

A remediation bundle begins only at a toolkit-owned root whose author ID equals the live authenticated bot and whose body contains a valid toolkit marker and finding fingerprint. That root and its selected human/automation/system replies become one opaque record. Recognized slash or live-username mention commands are lifecycle control and are excluded from model text. A verified root selected as remediation is not duplicated in generic discussions, and none of its replies participates in external-reference discovery. Remediation text can locate a claim for re-checking against current code and tests; it cannot change severity, prove a fix, suppress or resolve a finding, issue a command, or authorize approval.

The private `ocr.context-store/v2` is independent from the repository evidence store and its budgets. It is atomically written owner-only and hostile-read before OCR. Only a fully normalized and DLP-checked committed record receives a `ctx1_` handle containing 32 random bytes encoded as unpadded base64url. The private mapping binds run, policy digest, adapter, tenant, canonical object, resource class, projections, version/digest, and expiry. It is not an encoded upstream ID.

In `off` and `metadata`, the built-in MCP exposes only `ocr_toolkit_evidence`. In `enriched`, it exposes exactly `ocr_toolkit_evidence`, `context_list`, and `context_get`:

- `context_list` accepts only optional `resource_class`, admitted `source`, `page_size` from 1 through 20, and an opaque cursor. Resource classes are `issue`, `document`, and `remediation_thread`. It returns safe descriptors, minted handles, expiry, mutability, per-source completeness, and a next cursor.
- `context_get` accepts exactly one listed `ctx1_` handle and returns only the record's protected `model` projection. A remediation record contains one DLP-checked root, safe anchor state, ordered pseudonymized replies, closed completeness, and reply/resolved/outdated counts. It never contains a raw provider identity or object.

Both tools read the already committed local store. They have no network, subprocess, search, arbitrary URL/ID, traversal, or write path. Invalid, expired, wrong-run, wrong-policy, missing, or non-minted handles fail before record access. OCR must still record at least one `ocr_toolkit_evidence(action=summary)` call; context calls do not satisfy that requirement.

## Publication, receipt, approval, and cleanup

After OCR exits, the toolkit applies separate publication-sink and private-retention projections against forbidden/non-publishable context, configured secrets, closed PII patterns, controls, Markdown destinations, and Unicode/HTML/Markdown laundering forms. Publication sinks are exactly the result values the posting owner can render: finding fields, warnings, outcome message, displayed tool names, and manifest failure path/reason fields. Other OCR metadata remains private but is independently scanned and sanitized before persistence; it cannot make safe publication sinks partial merely because an opaque SHA, UUID, item identity, or bare build number resembles a phone number. The conservative detector can still classify a separator-bearing technical identifier as phone-like. Ordinary receipts intentionally expose only closed aggregate counts; an explicit local preservation run adds a private value-free path/subtype/size/hash decision sidecar so the operator can diagnose that false-positive class against the separately retained raw result without weakening the filter or disclosing the value. The checks compare whole values and normalized contiguous excerpts of at least 24 characters; a work-bound uncertainty filters or sanitizes the affected unit. This does not claim detection of shorter arbitrary excerpts or semantic paraphrases, and it cannot reverse data already sent to the model.

An unsafe result is neither retained raw nor discarded wholesale. In the same inode-checked atomic transformation used to attach the receipt, unsafe publication content produces a safe `completed_with_errors` projection with independently passed finding/warning fields, fixed tool-use counters, original closed coverage counts, and closed DLP reason/retained/omitted counts. Unsafe `content` removes its finding; an unsafe optional finding field is removed without discarding safe finding content. Horizontal tab is permitted only in `existing_code` and `suggestion_code`, where a whitespace-normalized checking copy still passes every secret, PII, forbidden-value, laundering, and budget detector before the original code value is retained. When every publication sink is safe and only private result metadata fails retention DLP, the unsafe private fields are replaced with static non-sensitive values while the original valid status, manifest, warnings, and findings remain. Unsafe values and their locations are never retained. Receipt v5 calls this `private-sanitized` only when a pure canonical publication/approval projection is byte-equivalent before and after sanitization; normal approval evaluation then applies. Any changed, malformed, or incomparable projection is `publication-filtered`, preserves the previous review, emits only closed counts, and cannot automatically approve. Its public projection is incomplete, but posting uses the validated original coverage kind/counts so complete OCR coverage is not relabelled as partial and filtered warnings cannot synthesize failed items.

The summary contains distinct private-sanitization and publication-filtering details with an exact `ocr.publication-dlp-signal/v2` HTML marker containing only low-cardinality counts. The posting command emits the same JSON as an `OCR toolkit telemetry event` log line so CI log collectors can alert without a new runtime network/exporter path. OCR remains authoritative for provider/token/request telemetry; the toolkit does not add an OTLP client, arbitrary telemetry endpoint, raw value/path, or mandatory external export. The explicit local `ocr-ci review --preserve-private-artifacts` diagnostic retains owner-only raw session/context state, adds a value-free `ocr.private-dlp-decisions/v1` path/reason/detector/size/hash attribution sidecar, and deliberately emits no posting receipt. It is local evidence for investigating conservative false positives, not a CI or publication artifact; the validated GitLab MR profile rejects it.

Receipt v5 stores only closed review/policy identities, context mode, per-source completeness and degradation counts, admitted-mutable state, fixed evidence/context tool-use counts, publication-DLP result, and cleanup result. It does not store context text, provider IDs, URLs, commands, arguments, headers, adapter results, personal display data, or transport diagnostics. Receipt v1-v4 is rejected; ephemeral results have no migration path.

Every existing manifest, coverage, warning, omission, finding, source-SHA, author, provider, and self-approval gate remains. Degraded selected metadata, a DLP-rejected selected source, required-source degradation, and any admitted remediation record make the run ineligible. DLP-clean generic discussions and adapter records do not independently block approval; optional non-DLP degradation remains visible and cannot prove absence. A complete enriched run without admitted remediation is not blocked solely by the selected mode. Direct operator MCP is a separate privileged boundary and remains comment-only.

OCR runs under a fresh owner-only isolated `HOME` containing only validated toolkit-generated configuration. Context acquisition is complete before that process starts; adapter/provider network paths are not exposed through its model tools. Ordinary runs remove OCR session/configuration, context store, adapter scratch data, and any stale private DLP decision sidecar after success, failure, or interruption. Termination is deferred across cleanup and atomic result projection so a completed raw result cannot replace the validated partial-result/receipt boundary. A local operator may explicitly retain these owner-only artifacts and the value-free DLP attribution sidecar for diagnosis, but that run has no receipt and cannot cross the posting boundary; validated GitLab MR execution rejects the exception before OCR starts.

## Deployment boundary and non-claims

Use dedicated least-privilege service identities and an AI-readable corpus. The proxy must enforce tenant, object, operation, and field authorization for every request; successful authentication or an allowlisted hostname is insufficient. The toolkit cannot make a lying adapter truthful, constrain a broader upstream credential, protect same-owner artifacts from host compromise, reverse model egress, detect arbitrary semantic paraphrase, or make model judgment deterministic.

The complete files under [`examples/gitlab/context/`](../examples/gitlab/context/) are safe starting points with placeholder hosts and credential names. Direct external MCP and brokered adapters are different trust boundaries: direct MCP exposes provider-owned tool schemas and model-selected arguments, while adapters acquire records before OCR and expose only toolkit-minted local handles.
