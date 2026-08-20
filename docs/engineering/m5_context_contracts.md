# M5 Bounded Review-Context Contracts

This checkpoint fixes the v0.7.0 production contracts before implementation. It is an engineering contract, not a claim that a named boundary is already proven. Production-path evidence and public operator guidance remain owned by the active plan and the test-evidence matrix.

## Ownership and dependency direction

`ocr_toolkit.context` is independent from `ocr_toolkit.evidence`. Common context contracts and normalization point downward; policy, recognizers, adapters, and persistence depend on those contracts; the broker composes them; `review_runner` alone composes repository evidence and review context into one OCR execution. GitLab discussion acquisition remains a provider owner. The existing built-in MCP process serves both evidence and context, but the stores, budgets, schemas, identifiers, and receipts remain separate.

OCR performs one review and one model loop. The toolkit does not run contextual adjudication, merge a second model result, or expose provider-selected tool schemas.

## Protected policy

The only policy path is `.opencodereview/review-context-policy.json`. It is read as a bounded regular immutable Git blob from the captured protected-target policy SHA. A working-tree or source-branch file, symlink, submodule, missing/unsafe object, invalid UTF-8, duplicate JSON key, oversized input, unknown field/version, or impossible projection is rejected. Explicit `enriched` mode without a valid policy fails before OCR.

The exact top-level schema is:

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
  "forge_discussions": {},
  "references": []
}
```

`forge_discussions` is optional and exact-schema. When present it contains `required`, `account_classes`, `include_resolved`, `include_outdated`, `max_age_seconds`, `max_threads`, `max_replies_per_thread`, `max_items`, source `budgets`, and `projections`. Account classes are the closed set `user`, `automation`, `system`, and `toolkit_bot`; an unknown class makes that record unavailable.

Each reference entry contains `adapter`, `tenant`, `resource_class`, `recognizer`, `required`, `max_records`, `max_age_seconds`, source text budgets, and `projections`. Resource classes are `issue` and `document`. Recognizers are exact toolkit grammars: protected-prefix issue keys, exact protected HTTPS origin/path prefix, or an explicit bounded reference form. User-configurable regular expressions and repository-wide text search are absent.

Every source uses the exact projection object:

```json
{
  "retrieve": ["descriptor", "text"],
  "model": ["descriptor", "text"],
  "publish": ["descriptor"],
  "retain": ["state", "count", "digest", "version", "expiry"]
}
```

The allowed field vocabulary is closed per projection. `model`, `publish`, and `retain` must each be subsets of `retrieve`; retention additionally rejects text, upstream identifiers, URLs, commands, transport data, personal display data, and raw payloads. A policy with neither discussions nor references is invalid.

## Recognizers and candidates

Candidates are extracted only from admitted merge-request title/description and admitted discussion bodies. A candidate carries only its policy-source identity, tenant alias, resource class, recognizer kind, and bounded candidate string. It grants no authority. Normalization is NFC, strips unsupported controls, rejects ambiguity/collision, and applies character, UTF-8 byte, physical-line, item, source, aggregate, and time limits independently.

## Operator adapter configuration

`OCR_REVIEW_CONTEXT_ADAPTERS_JSON` is an environment-only exact array. Common fields are `name`, `type`, `tenants`, and `resource_classes`.

- `stdio` additionally requires absolute `command`, bounded `args`, and environment variable names in `env_from`. It rejects shell execution, setup, inherited working directory, literal secrets, and inherited environment outside the closed child baseline plus selected names.
- `remote` additionally requires an absolute HTTPS `url` and environment-backed `headers_from`. It rejects URL credentials/fragments, literal secret headers, redirects, non-TLS endpoints, and ambient proxy traversal.

Protected policy can select and narrow an operator entry; it cannot create an adapter, command, endpoint, tenant, resource class, credential, or field permission.

## Fixed adapter protocol

The broker sends exactly one `ocr.context-adapter-request/v1` object per candidate with operation `authorize_and_resolve`, random request identity, run identity, adapter/tenant/resource class, bounded candidate, requested fields, and hard limits. The adapter returns one `ocr.context-adapter-response/v1` object with matching request/run identity and either:

- `status=admitted`, canonical object digest, immutable version/digest, expiry, and exact projected record; or
- `status=unavailable` and a closed reason class.

Denied, missing, foreign-tenant, and unauthorized objects share one externally visible `unavailable` class. Unknown keys/statuses, mismatched identity, partial/multiple frames, excess bytes, invalid UTF-8, authorization ambiguity, version replacement, deadline, or transport failure reject the entire record. Adapter descriptions and schemas never enter OCR.

Stdio uses a clean environment, isolated owner-only working/home directory, bounded JSONL, a deadline, process-group termination, and private bounded redacted stderr. HTTPS uses certificate verification, a redirect-rejecting opener, exact status/content type, bounded streaming, a deadline, and safe closed diagnostics.

## Context store and handles

The private artifact is `ocr.context-store/v1`. It is written owner-only through atomic replacement and read back as hostile input. The envelope binds store/run/policy identity, creation/expiry, completeness, records, handle index, and a canonical digest. Symlink, non-regular file, extra hard link, unsafe permissions, oversize, duplicate/colliding key, partial replacement, impossible projection, record/index mismatch, and stale identity fail closed.

A handle is `ctx1_` plus 32 random bytes encoded as unpadded base64url. It is minted only after a completely normalized, retrieval-DLP-checked record is committed. Private mapping binds run, adapter, tenant, canonical object digest, resource class, allowed projections, version/digest, policy digest, expiry, and record. A caller-supplied upstream ID or URL is never accepted as a handle.

## Built-in MCP

`off` and `metadata` expose only `ocr_toolkit_evidence`. `enriched` exposes exactly `ocr_toolkit_evidence`, `context_list`, and `context_get` from the same built-in stdio process.

`context_list` accepts only closed source/resource-class filters, an opaque store-bound cursor, and a bounded page size. It returns minted handles, safe descriptors, per-source completeness, and the next cursor. `context_get` accepts exactly one minted handle and returns only its policy-admitted model projection from the committed local store. Invalid arguments, arbitrary identifiers, wrong-run/policy, expired or missing handles are rejected before record access. Neither tool performs network, subprocess, search, write, or provider operations.

The bootstrap requires a model-recorded `ocr_toolkit_evidence(action=summary)` call before analysis. Toolkit preflight self-query never satisfies this requirement.

## Review execution, publication, and receipt

OCR runs under a fresh owner-only isolated `HOME` containing only toolkit-validated OCR configuration/composition. The exact resolved OCR executable receives one review. Context acquisition finishes before model execution; adapters and forge network paths are unavailable in the model loop. The home, context store, adapter scratch space, and OCR session are removed symlink-safely after success, failure, or interruption. Cleanup uncertainty makes the run non-publishable; v0.7.0 has no debug-retention exception.

Publication validation runs after OCR and before result acceptance. It compares exact and normalized forbidden/non-publishable context, configured secret values, closed PII patterns, controls, Markdown destinations, and Unicode deception. Uncertain projection state or a match blocks ordinary comments and permits only a static toolkit-authored failure. This is containment of deterministic output classes, not a claim to detect arbitrary semantic paraphrase or undo content already sent to the model.

Receipt schema `ocr.toolkit-receipt/v4` stores only closed review/policy identities, context mode, per-source completeness and degradation counts, admitted-mutable flag, fixed tool usage, publication-DLP result, and cleanup result. It never stores context text, upstream IDs, URLs, commands, arguments, headers, results, personal display data, or transport diagnostics. v1-v3 remain readable for comments and fail closed for v4 approval guarantees.

Automatic approval preserves every existing manifest, coverage, warning, omission, finding, exact-SHA, author, provider, and self-approval gate. Required-source degradation and any admitted mutable discussion/external record block approval. Optional degradation is visible and cannot prove source absence. A complete enriched run with zero admitted mutable records is not blocked solely because enriched mode was selected.

## Capability decision for OCR 1.9.8

The 1.9.7 and 1.9.8 adjacent releases pass the repository-owned Linux contract probes and official checksum verification. Reviewed changes show additive provider/install behavior in 1.9.7. In 1.9.8, Bedrock/SigV4 is an upstream provider boundary the toolkit does not configure; native severity changes upstream skill guidance while the structured result fields remain compatible; human-audience JSON/SARIF progress moves to stderr while toolkit execution uses agent audience. The checksum-verified Darwin arm64 artifact repeats the required version, flag, preview, result, manifest, budget, target-rule, and session-side-effect probes.

Reviewed Go MCP behavior continues to initialize and discover multiple tools in one review and to persist session material below `HOME/.opencodereview/sessions`. These facts support the fixed multi-tool server and isolated-home design. They do not prove M5 until installed-artifact and real-OCR tests exercise the toolkit production path.

## Explicit non-claims

The toolkit cannot make a lying adapter truthful, constrain credentials broader than their service identity, protect same-owner artifacts from a host compromise, reverse model egress, detect arbitrary semantic paraphrase, or make model judgment deterministic. Operator credentials and adapter services must enforce least privilege and auditable object authorization independently.
