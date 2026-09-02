# Review signal ownership

This matrix records the completed BL-017 audit and its narrow toolkit 0.8.5
operator-diagnostic reconciliation. It separates provider/review telemetry from
the toolkit's deterministic control-plane receipts. It is an ownership map, not
a new telemetry API.

## Source-to-signal matrix

| Signal | Authoritative source | Toolkit projection | Privacy and authority boundary |
| --- | --- | --- | --- |
| Provider/model identity, request/session correlation, retries, latency, HTTP outcome, and cost | OCR and its configured provider telemetry | One closed provider-failure class for static GitLab text; on failure, at most one local toolkit-authored line may add closed protocol detail, one shared HTTP status, and non-zero bounded retry counters | Raw identities, request IDs, response text, provider codes, URLs, paths, warnings, and stderr do not enter the projection, GitLab notes, receipt v7, DLP signals, toolkit telemetry, or approval. HTTP detail does not prove a provider business cause. |
| Prompt, completion, cached, reasoning, and total tokens | OCR result and OCR telemetry | Closed non-negative provider-neutral token buckets in the result summary and canonical publication comparison | Unknown fields are ignored; malformed or contradictory counters are unavailable. Token counts never authorize approval or automatic routing. |
| Review effort and executed rounds | Operator-owned root `effort` config and OCR runtime | `OCR_REVIEW_EFFORT` writes one closed `low`, `medium`, or `high` setting; the toolkit does not publish inferred round telemetry | Merge-request content cannot select effort. Budget or incomplete coverage remains approval-ineligible through the existing result contract. |
| Semantic grouping, group file membership, per-group spans, and filter activity | OCR runtime and OCR telemetry | Additive private result fields may be DLP-sanitized; no group or round field enters receipt v7, GitLab text, fingerprints, severity, lifecycle commands, toolkit telemetry, or approval | Group labels are model-produced. Group keys are sorted changed paths, so both are untrusted and potentially high-cardinality. |
| Tool requests and MCP use | OCR result for aggregate tool calls; each toolkit MCP owner for verified local use | Bounded known-server counts and mandatory exact action-receipt-v2 attribution in receipt v7 and the summary | Tool names and counts are closed; arguments, paths, IDs, results, headers, and content are excluded. |
| Selection, completed/reused/failed/waived coverage, and aggregate-budget stop | OCR run manifest | Closed result outcome, summary, receipt validation, and approval blockers | Incomplete, malformed, failed, waived, or budget-stopped coverage fails closed; no duplicate toolkit budget metric is needed. |
| Findings, severity, fingerprints, suppression, resolution, and repeated discussions | OCR findings plus toolkit-owned posting snapshots and human commands | GitLab discussions, summary, exact fingerprints, and closed lifecycle state | Remediation text and additive group metadata cannot change severity, prove resolution, suppress findings, or issue commands. |
| Context admission, degradation, mutation, and evidence use | Toolkit broker/store and fixed MCP receipts | Count-only receipt-v7 context/evidence state | Raw merge-request title, description, discussions, CI provider identities/payloads, rejected text, and record contents do not enter the receipt or telemetry event. |
| Publication DLP and posting transaction state | Toolkit result projection and GitLab transaction owner | Receipt-v5 publication state, one parseable summary marker, and one local count-only log event | `private-sanitized` can preserve approval only when the canonical projection is unchanged; `publication-filtered` makes the public projection incomplete and blocks approval without relabelling independently complete OCR coverage. No rejected value or location is emitted. |
| OCR compatibility qualification | Compatibility workflow and checksum-pinned evidence | Canonical issue plus bounded success or failure artifact | Public failure status contains only closed phase/reason/version/run fields. Raw qualification exceptions stay in the job log. |

## OCR telemetry privacy

OCR telemetry remains opt-in. The toolkit defaults both
`OCR_TELEMETRY_ENABLED` and `OCR_TELEMETRY_CONTENT_LOGGING` to `false` and adds
no exporter of its own.

OCR 1.10.0 constructs group span names from sorted changed paths and attaches
group path keys, model-produced labels, file counts, round numbers, churn, and
filter counters to upstream spans and events. Disabling content logging must not
be treated as removing those identifiers: operators who enable OCR telemetry
must regard the configured exporter as receiving repository-derived,
high-cardinality data and apply their own retention, access, and redaction
policy. The toolkit does not ingest those spans or turn them into receipt,
approval, routing, or quality signals.

## Audit conclusion

The established owners already cover provider operations, completeness,
evidence use, context degradation, publication safety, posting, and approval.
The remaining data is either provider-specific telemetry already owned by OCR
or untrusted high-cardinality group data that should not be duplicated.
Therefore BL-017 concludes `no-new-layer`: the toolkit adds no exporter,
metric schema, context telemetry implementation, or automatic routing. The
bounded failure-only operator line does not reopen that conclusion.

No safe stable objective currently supports automatic profile routing or a
generic review-quality score. BL-016 remains parked, BL-018 remains conditional
on an owner-approved objective and representative evidence, and BL-019 and
BL-020 retain their existing activation requirements.
