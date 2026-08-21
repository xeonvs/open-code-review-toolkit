# Bounded review context

Open Code Review Toolkit can enrich one validated GitLab merge-request review with bounded merge-request metadata, GitLab discussions, and records resolved by operator-managed adapters. Enrichment is a single pre-OCR acquisition phase. OCR remains the only review engine, and its model loop can read only committed local handles through the toolkit's existing built-in MCP process.

## Modes and lifecycle

`OCR_REVIEW_CONTEXT_MODE` is a closed selector:

- Empty or `off` validates immutable review and posting identities but does not normalize or persist mutable merge-request text.
- `metadata` additionally admits bounded title, description, labels, and source-branch text. This preserves the v0.6.3 behavior.
- `enriched` requires a validated GitLab merge-request environment and a valid protected-target policy. It includes the same metadata projection, a stable bounded GitLab discussion snapshot when selected, and policy-recognized external records. Missing or invalid policy stops the review before OCR.

The lifecycle is fixed: capture the protected-target SHA; load policy from that immutable object; acquire and authorize records; normalize, DLP-check, and atomically commit the private context store; run one OCR review in an isolated home; serve only local handles; remove session, adapter, and context artifacts; then validate/project the complete OCR result and attach receipt v5 through one inode-checked atomic replacement. A cleanup or publication-validation failure blocks ordinary result publication.

## Protected-target policy

The only policy path is `.opencodereview/review-context-policy.json`. The toolkit reads it as a bounded regular Git blob from the captured protected-target policy SHA. A source-branch or working-tree copy has no authority. Missing, symlink, submodule, oversized, invalid UTF-8, duplicate-key, unknown-field, unknown-version, or impossible-projection input fails closed.

The following complete synthetic policy selects GitLab discussions and issue keys with protected prefix `DEMO`:

```json
{
  "schema_version": "ocr.review-context-policy/v1",
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

Discussion account classes are the closed set `user`, `automation`, `system`, and `toolkit_bot`. GitLab classifies accounts before storage and replaces display identity with a run-local pseudonym. Name, username, email, avatar/profile URL, and raw provider IDs are never model fields.

References bind one operator-configured adapter, tenant alias, `issue` or `document` resource class, required/optional semantics, bounds, projections, and one toolkit-authored recognizer:

- `{"type":"issue_key","prefix":"DEMO"}` recognizes keys such as `DEMO-42` with the exact protected prefix.
- `{"type":"https_url","origin":"https://docs.example.invalid","path_prefix":"/published/"}` recognizes only HTTPS URLs at that exact origin and path prefix.
- `{"type":"explicit"}` recognizes `[[context:issue:synthetic-record]]` or `[[context:document:synthetic-record]]` for the matching resource class.

Candidates are extracted only from admitted merge-request metadata and admitted discussion bodies. Recognition grants no access; every candidate still crosses adapter authorization. Configurable regular expressions, repository-wide search, arbitrary URLs, and arbitrary identifiers are not supported.

Projection fields are sorted unique lists. `model`, `publish`, and `retain` must each be subsets of `retrieve`. Retention is limited to `state`, `count`, `digest`, `version`, and `expiry`; it cannot retain text, upstream identifiers, URLs, commands, transport data, or personal display data. Retrieval, model egress, publication, and retention are deliberately separate decisions.

`schema_version` is not a database migration feature. Reviews and stores are ephemeral. It is retained because policy, adapter frames, private stores, pre-execution status, and review receipts cross independently produced or hostile-read serialized boundaries. The exact discriminator prevents an old or different field set from inheriting current authorization or approval meaning. Ephemeral M5 policy/store/protocol readers accept only their current exact schema and provide no upgrade path; only historical result receipts remain readable for safe comment compatibility.

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
    "env_from": ["SYNTHETIC_ADAPTER_TOKEN"]
  }
]
```

The toolkit uses no shell or setup hook. It starts the exact executable with a clean allowlisted environment and an isolated owner-only working directory/home, exchanges one bounded JSONL request and response, enforces one deadline across request delivery, response acquisition, and process exit, terminates the process group on failure, and retains only private bounded redacted stderr while the run is active.

A remote entry uses one absolute HTTPS endpoint and maps HTTP header names to environment variable names:

```json
[
  {
    "name": "knowledge",
    "type": "remote",
    "tenants": ["published"],
    "resource_classes": ["document"],
    "url": "https://context-proxy.example.invalid/v1/authorize-and-resolve",
    "headers_from": {"Authorization": "SYNTHETIC_ADAPTER_AUTHORIZATION"}
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

The private `ocr.context-store/v1` is independent from the repository evidence store and its budgets. It is atomically written owner-only and hostile-read before OCR. Only a fully normalized and DLP-checked committed record receives a `ctx1_` handle containing 32 random bytes encoded as unpadded base64url. The private mapping binds run, policy digest, adapter, tenant, canonical object, resource class, projections, version/digest, and expiry. It is not an encoded upstream ID.

In `off` and `metadata`, the built-in MCP exposes only `ocr_toolkit_evidence`. In `enriched`, it exposes exactly `ocr_toolkit_evidence`, `context_list`, and `context_get`:

- `context_list` accepts only optional `resource_class`, admitted `source`, `page_size` from 1 through 20, and an opaque cursor. It returns safe descriptors, minted handles, expiry, mutability, per-source completeness, and a next cursor.
- `context_get` accepts exactly one listed `ctx1_` handle and returns only the record's protected `model` projection.

Both tools read the already committed local store. They have no network, subprocess, search, arbitrary URL/ID, traversal, or write path. Invalid, expired, wrong-run, wrong-policy, missing, or non-minted handles fail before record access. OCR must still record at least one `ocr_toolkit_evidence(action=summary)` call; context calls do not satisfy that requirement.

## Publication, receipt, approval, and cleanup

After OCR exits, the toolkit applies separate publication-sink and private-retention projections against forbidden/non-publishable context, configured secrets, closed PII patterns, controls, Markdown destinations, and Unicode/HTML/Markdown laundering forms. Publication sinks are exactly the result values the posting owner can render: finding fields, warnings, outcome message, displayed tool names, and manifest failure path/reason fields. Other OCR metadata remains private but is independently scanned and sanitized before persistence; it cannot make safe publication sinks partial merely because an opaque SHA, UUID, item identity, or bare build number resembles a phone number. The checks compare whole values and normalized contiguous excerpts of at least 24 characters; a work-bound uncertainty filters or sanitizes the affected unit. This does not claim detection of shorter arbitrary excerpts or semantic paraphrases, and it cannot reverse data already sent to the model.

An unsafe result is neither retained raw nor discarded wholesale. In the same inode-checked atomic transformation used to attach the receipt, unsafe publication content produces a safe `completed_with_errors` projection with independently passed finding/warning fields, fixed tool-use counters, original closed coverage counts, and closed DLP reason/retained/omitted counts. Unsafe `content` removes its finding; an unsafe optional finding field is removed without discarding safe finding content. When every publication sink is safe and only private result metadata fails retention DLP, the unsafe private fields are replaced with static non-sensitive values while the original valid status, manifest, warnings, and findings remain. Unsafe values and their locations are never retained. Receipt v5 calls this `private-sanitized` only when a pure canonical publication/approval projection is byte-equivalent before and after sanitization; normal approval evaluation then applies. Any changed, malformed, or incomparable projection is `publication-filtered`, preserves the previous review, emits only closed counts, and cannot automatically approve.

The summary contains distinct private-sanitization and publication-filtering details with an exact `ocr.publication-dlp-signal/v2` HTML marker containing only low-cardinality counts. The posting command emits the same JSON as an `OCR toolkit telemetry event` log line so CI log collectors can alert without a new runtime network/exporter path. OCR remains authoritative for provider/token/request telemetry; v0.7.1 does not add an OTLP client, arbitrary telemetry endpoint, raw value/path, or mandatory external export. There is no raw-result or secure-debug retention switch.

Receipt v5 stores only closed review/policy identities, context mode, per-source completeness and degradation counts, admitted-mutable state, fixed evidence/context tool-use counts, publication-DLP result, and cleanup result. It does not store context text, provider IDs, URLs, commands, arguments, headers, adapter results, personal display data, or transport diagnostics. Receipt v1-v4 is rejected; ephemeral results have no migration path.

Every existing manifest, coverage, warning, omission, finding, source-SHA, author, provider, and self-approval gate remains. Required-source degradation and any admitted mutable discussion or external record make the run ineligible. Optional degradation is visible and cannot prove absence. A complete enriched run with zero admitted mutable records is not blocked solely by the selected mode. Direct operator MCP is a separate privileged boundary and remains comment-only.

OCR runs under a fresh owner-only isolated `HOME` containing only validated toolkit-generated configuration. Context acquisition is complete before that process starts; adapter/provider network paths are not exposed through its model tools. The toolkit removes OCR session/configuration, context store, and adapter scratch data after success, failure, or interruption. Termination is deferred across cleanup and atomic result projection so a completed raw result cannot replace the validated partial-result/receipt boundary. v0.7.0 has no raw debug-retention exception.

## Deployment boundary and non-claims

Use dedicated least-privilege service identities and an AI-readable corpus. The proxy must enforce tenant, object, operation, and field authorization for every request; successful authentication or an allowlisted hostname is insufficient. The toolkit cannot make a lying adapter truthful, constrain a broader upstream credential, protect same-owner artifacts from host compromise, reverse model egress, detect arbitrary semantic paraphrase, or make model judgment deterministic.

The complete synthetic files under [`examples/context/`](../examples/context/) are safe starting points. Direct external MCP and brokered adapters are different trust boundaries: direct MCP exposes provider-owned tool schemas and model-selected arguments, while M5 adapters acquire records before OCR and expose only toolkit-minted local handles.
