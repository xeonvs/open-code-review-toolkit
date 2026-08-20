# M5 Bounded Review-Context Contracts

This checkpoint fixed the v0.7.0 production contracts before implementation and remains the engineering-level boundary record. The implementation now exists on the active release branch; production-owner evidence and remaining real-OCR/stable-release limits are recorded in the active plan and test-evidence matrix. Public operator behavior is owned by [Bounded review context](../review-context.md).

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
  "retrieve": ["count", "descriptor", "digest", "expiry", "state", "text", "version"],
  "model": ["descriptor", "text"],
  "publish": ["descriptor"],
  "retain": ["state", "count", "digest", "version", "expiry"]
}
```

The allowed field vocabulary is closed per projection. `model`, `publish`, and `retain` must each be subsets of `retrieve`; retention additionally rejects text, upstream identifiers, URLs, commands, transport data, personal display data, and raw payloads. A policy with neither discussions nor references is invalid.

## Protected rules-path setup outcome

When a validated GitLab merge request introduces its configured repository-owned OCR rules path, the source candidate still cannot become policy. If the exact normalized path is absent at both the immutable diff base and captured protected-target policy commit, but exists at the exact source head as a regular blob within the Git reader's byte limit, `review` stops before OCR and atomically writes `ocr.pre-execution-status/v1`. Source contents are not read or validated for this classification. A path that existed at the diff base, an absolute operator-owned path outside the repository, or a missing, symlink, tree, submodule, oversized, ambiguous, or unavailable source object retains the generic fail-closed outcome.

The owner-only status contains exactly `schema_version`, the closed reason `protected_target_rule_path_pending`, and the diff-base, source, and captured policy SHAs. It contains no path, ref, hostname, provider text, exception, stderr, or display wording. `post` hostile-reads the bounded regular single-link file, verifies the current source and diff-base identities, and renders only toolkit-authored text. It deliberately does not replace the captured policy SHA with a newer target-branch head. Missing, stale, malformed, oversized, permission-unsafe, unknown-version/reason/key, or identity-mismatched state falls back to the generic failure note. `OCR_POST_ERROR_DETAILS` never appends stderr to the recognized setup note; emoji and strict/advisory exit behavior remain under the existing posting settings.

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

Stdio uses a clean environment, isolated owner-only working/home directory, bounded JSONL, one deadline covering request delivery, response read, and child exit, process-group termination, and private bounded redacted stderr. HTTPS uses certificate verification, a redirect-rejecting opener, exact status/content type, bounded streaming, a deadline, and safe closed diagnostics. A separate hard request-attempt cap prevents a stream of unavailable candidates from bypassing the admitted-record budget. Authorization and exact-object deduplication happen before admitted text consumes aggregate budgets; the same canonical object changing version or digest during one acquisition is invalid rather than silently deduplicated.

## Context store and handles

The private artifact is `ocr.context-store/v1`. It is written owner-only through atomic replacement and read back as hostile input. The envelope binds store/run/policy identity, creation/expiry, completeness, records, handle index, and a canonical digest. Symlink, non-regular file, extra hard link, unsafe permissions, oversize, duplicate/colliding key, partial replacement, impossible projection, record/index mismatch, and stale identity fail closed.

A handle is `ctx1_` plus 32 random bytes encoded as unpadded base64url. It is minted only after a completely normalized, retrieval-DLP-checked record is committed. Private mapping binds run, adapter, tenant, canonical object digest, resource class, allowed projections, version/digest, policy digest, expiry, and record. A caller-supplied upstream ID or URL is never accepted as a handle.

## Built-in MCP

`off` and `metadata` expose only `ocr_toolkit_evidence`. `enriched` exposes exactly `ocr_toolkit_evidence`, `context_list`, and `context_get` from the same built-in stdio process.

`context_list` accepts only closed source/resource-class filters, an opaque store-bound cursor, and a bounded page size. It returns minted handles, safe descriptors, per-source completeness, and the next cursor. `context_get` accepts exactly one minted handle and returns only its policy-admitted model projection from the committed local store. Invalid arguments, arbitrary identifiers, wrong-run/policy, expired or missing handles are rejected before record access. Neither tool performs network, subprocess, search, write, or provider operations.

The bootstrap requires a model-recorded `ocr_toolkit_evidence(action=summary)` call before analysis. Toolkit preflight self-query never satisfies this requirement.

## Review execution, publication, and receipt

OCR runs under a fresh owner-only isolated `HOME` containing only toolkit-validated OCR configuration/composition. One exact resolved executable from an absolute search-path entry, outside the reviewed repository, receives one review. Context acquisition finishes before model execution; adapters and forge network paths are unavailable in the model loop. The home, context store, adapter scratch space, and OCR session are removed symlink-safely after success, failure, or interruption. Cleanup uncertainty makes the run non-publishable; v0.7.0 has no debug-retention exception.

Publication validation runs after OCR and cleanup, within the same inode-checked atomic read/replace that attaches receipt v4. It compares both decoded source and rendered approximations against whole forbidden/non-publishable values and normalized contiguous excerpts of at least 24 characters. Closed checks cover nested HTML entities, comments/tags, inline/reference/autolink Markdown destinations, escapes/formatting, configured secrets, formatted-phone/email patterns, controls, and Unicode deception. Bare SHAs, build identifiers, and unformatted digit strings are not classified as phone numbers. A comparison that would exceed the fixed work bound is uncertainty.

The result has two explicit DLP projections. Publication sinks are exactly values the posting owner may render: outcome message, allowlisted finding fields, warnings, displayed tool names, and manifest-failure path/reason fields. If one is unsafe, the raw result is atomically replaced by an explicit safe-partial result containing independently passed findings/warnings plus closed reason, omission, original-coverage, and tool-use facts. Non-rendered OCR metadata is a separate private-retention projection: unsafe keys are removed and unsafe string values receive stable non-reversible placeholders before the result is retained. When that sanitized result still satisfies the OCR result contract, its original status, manifest, and safe findings remain intact; a required structural-field loss falls back to the safe-partial form. Neither path retains the rejected value or its location. GitLab may publish the safe result with a filtered signal, while retaining the previous review, consuming prior matching fingerprints one-for-one, replacing only an earlier toolkit setup-pending note on retry, and blocking approval. This is containment of deterministic exact-output classes, not a claim to detect shorter arbitrary excerpts, arbitrary semantic paraphrase, or undo content already sent to the model.

Receipt schema `ocr.toolkit-receipt/v4` stores only closed review/policy identities, context mode, per-source completeness and degradation counts, admitted-mutable flag, fixed tool usage, publication-DLP result (passed, or filtered with closed reason/retained/omitted/original-coverage counts), and cleanup result. The same filtered counts form an `ocr.publication-dlp-signal/v1` GitLab-summary marker and structured log event; neither is a new network telemetry exporter. The receipt/event never stores rejected text or locations, context text, upstream IDs, URLs, commands, arguments, headers, adapter results, personal display data, or transport diagnostics. v1-v3 remain readable for comments and fail closed for v4 approval guarantees.

Schema versions protect serialized trust boundaries; they are not a database-retention promise. The review result crosses from the review process/job to hostile posting readback, so its version prevents an older field set from inheriting newer approval guarantees. Policy and adapter versions similarly bind independent producers/consumers. Ephemeral evidence/context stores accept only their exact current schema and intentionally have no migration or upgrade path.

Automatic approval preserves every existing manifest, coverage, warning, omission, finding, exact-SHA, author, provider, and self-approval gate. Required-source degradation and any admitted mutable discussion/external record block approval. Optional degradation is visible and cannot prove source absence. A complete enriched run with zero admitted mutable records is not blocked solely because enriched mode was selected.

## Capability decision for OCR 1.9.8

The 1.9.7 and 1.9.8 adjacent releases pass the repository-owned Linux contract probes and official checksum verification. Reviewed changes show additive provider/install behavior in 1.9.7. In 1.9.8, Bedrock/SigV4 is an upstream provider boundary the toolkit does not configure; native severity changes upstream skill guidance while the structured result fields remain compatible; human-audience JSON/SARIF progress moves to stderr while toolkit execution uses agent audience. The checksum-verified Darwin arm64 artifact repeats the required version, flag, preview, result, manifest, budget, target-rule, and session-side-effect probes.

Reviewed Go MCP behavior continues to initialize and discover multiple tools in one review and to persist session material below `HOME/.opencodereview/sessions`. These facts support the fixed multi-tool server and isolated-home design. They do not prove M5 until installed-artifact and real-OCR tests exercise the toolkit production path.

| Release capability | Toolkit consumption | Runtime/CI impact | Required adaptation |
| --- | --- | --- | --- |
| 1.9.7 Gemini provider | Not selected or configured by the toolkit | None | None |
| 1.9.7 mirror-aware upstream installers | Toolkit neither installs nor downloads OCR | Version/checksum pin only | None |
| 1.9.8 Bedrock/SigV4 provider | Not selected or configured by the toolkit | None; no new toolkit credential boundary | None |
| 1.9.8 native severity in upstream skill | Toolkit already consumes tolerant structured severity/category result fields | No schema or posting change | None |
| 1.9.8 JSON/SARIF human-audience progress on stderr | Toolkit invokes `--audience agent` and consumes the result file | No logging or parsing change | None |

This chain therefore has no CI behavior change beyond its OCR version and asset digest pins. A future qualification that changes CI behavior must carry a separate Towncrier entry naming that impact.

The final real feature review used the same checksum-verified OCR 1.9.8 artifact against committed head `c46097901502b494e3add622728f9b0f0422b079`. OCR recorded 44 mandatory evidence calls, advertised the fixed evidence/list/get tool set, produced 21 independently safe findings, and left no context/session artifact after cleanup. It chose zero `context_list` and zero `context_get` calls. The then-current private-result scan also exposed an identifier-as-phone false positive; that observed result and all 21 findings were preserved as remediation input. Per the execution decision, the corrected final tree is qualified with deterministic production-owner fixtures rather than another OCR run. Therefore this run proves real evidence use, tool advertisement, one-pass completion, and success-path cleanup at that pre-remediation head; it does not prove model context reads or the corrected DLP tree.

## GitLab CI inheritance uncertainty qualification

The toolkit-owned GitLab CI rule keeps `allow_failure`, `rules`, `needs`, `image`, `before_script`, `variables`, and `environment` unknown across unresolved `extends` or includes. Only an explicit local override or an admitted bounded effective/compiled fact can prove one of those values. Findings, severity, and replacement suggestions cannot depend on an inferred GitLab default. This changes review guidance only: it adds no include fetch, mutable external reference, cross-repository evidence read, or production compiled-config API.

Four synthetic qualification cases distinguish an unresolved parent, a brokered document fact proving effective `allow_failure: true`, a brokered fact proving `false` under an advisory project policy, and an explicit local `false`. Real stdio adapter/broker tests prove the two compiled facts cross only the fixed M5 document protocol. The exact checksum-verified OCR 1.9.8 Darwin arm64 binary (`ace8544c12992cefecec7f0d22265ff5473078ea062f01d682ca1b08691ff0f9`) completed a synthetic unresolved-parent review and received the full uncertainty rule plus every closed field name in its actual request. A deterministic local model peer selected `task_done`, so the observed zero-finding result proves delivery and compatibility, not reliable model judgment; each expected finding/no-finding outcome remains a qualification expectation rather than a deterministic toolkit guarantee.

## Explicit non-claims

The toolkit cannot make a lying adapter truthful, constrain credentials broader than their service identity, protect same-owner artifacts from a host compromise, reverse model egress, detect arbitrary semantic paraphrase, or make model judgment deterministic. Operator credentials and adapter services must enforce least privilege and auditable object authorization independently.
