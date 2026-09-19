# Security and trust model

The toolkit bridges repository and forge content, OCR and its LLM provider,
operator configuration, governed MCP upstreams, CI secrets, and publication APIs.
No input becomes safe merely because a trusted pipeline acquired it.

## Threat model

Protected assets include immutable review identities, coverage and finding
integrity, private evidence/context/result/session data, registry and receipts,
forge/LLM/MCP credentials, external-object confidentiality, and publication and
approval state.

A contributor can control repository content, merge-request metadata and
discussion text, including tool-like instructions and crafted references. An MCP
upstream controls its descriptions, schemas and responses. An operator controls
the reviewed registry, credentials and protected-target policy. A compromised
runner or same-user process remains a host-level threat outside the toolkit's
process-isolation guarantees.

The main trust transitions are:

1. Immutable Git objects and provider identities cross closed bounded parsers.
2. Optional metadata and protected-policy discussions/remediation/CI outcomes
   cross normalization, stage-specific DLP and owner-only storage.
3. Repository evidence enters the mandatory internal MCP. Operator registry v2
   cannot remove, replace, rename or shadow that server.
4. Optional external tools cross the toolkit-owned federation gateway. OCR sees
   only frozen `server__tool` aliases through a fixed private relay; upstream
   credentials never enter OCR configuration or arguments.
5. OCR output crosses result validation, publication projection, stage-aware DLP,
   cleanup, receipt v9 and the provider posting transaction.

## Governed federation boundary

`OCR_MCP_SERVERS_JSON` accepts only a closed version-2 registry. Unknown fields,
legacy passthrough shapes, ambiguous aliases, missing environment-backed secrets,
unsupported schemas, missing allowlisted tools and collisions fail before model
execution. GitLab permits HTTPS upstreams only. Local review may also use an
absolute operator-selected stdio executable with bounded arguments and an
allowlisted environment; there is no shell or setup hook.

The gateway discovers and freezes the inventory before OCR, validates the
admitted JSON Schema profile, URL-shaped argument origins, arguments, response
kinds, and all byte/item/depth/time/call/run bounds. Outbound arguments and
inbound descriptions, schemas and results cross DLP when enabled. HTTPS disables
redirects, cookies and ambient proxy trust; stdio uses toolkit-owned bounded
framing and child-process cleanup. Returned links remain inert. Sampling, roots,
elicitation, OAuth, server-directed headers, generic link retrieval, writes and
resource/media projection are unsupported.

The official Python MCP SDK v2 is the primary integration boundary, while the
wire protocol is negotiated independently for OCR and each upstream. Explicitly
qualified SDK v1/v2 peers are supported; SDK major is not a protocol revision.
Unsupported revisions or capabilities fail explicitly.

Upstream services still own tenant/object/field authorization. A tool allowlist,
TLS connection, schema validation, origin allowlist, or `review_read` assurance
does not make an overprivileged credential safe or a lying service truthful. Use
dedicated least-privilege service identities and data suitable for model egress
and OCR-session retention.

The content-free `ocr.federation/v1` receipt records only closed per-alias counts
and cleanup state. Receipt v9 reconciles OCR attempts independently with gateway
attempts and terminal outcomes. Used advisory tools, known denied/failed calls,
or accounting mismatch make the run comment-only. Missing, malformed,
unfinalized or cleanup-uncertain federation evidence blocks normal publication.
Unused services and successful `review_read` use do not independently block
approval. Commands, URLs, arguments, results, credentials, paths, identifiers and
raw errors never enter the receipt.

## Review context and legacy migration

The public [bounded review-context contract](review-context.md) defines the
current policy, store, handle, receipt, and cleanup behavior in detail.

The context selector is closed to `off|metadata|enriched`. Current protected
policy v4 supports bounded GitLab discussions, verified remediation threads and
same-revision CI outcomes. The private context store exposes only committed local
handles through fixed internal `context_list` and `context_get`; neither tool has
network, subprocess, arbitrary URL/identifier, search, traversal or write access.

Policy v1-v3 remains parse-only for migration. Safe selectors and budgets still
apply, but legacy `references` never execute. Optional references are skipped;
required references, including references-only policies, create required
degradation and make the run comment-only. The removed adapter environment,
command/HTTPS proxy protocol, `OCR_MCP_REPLACE`, and direct OCR passthrough cannot
be restored by legacy configuration.

An admitted remediation thread remains historical evidence and blocks automatic
approval. A CI pass is scoped context, never suppression or approval authority.
Source policy cannot grant tools or credentials. An actually unprotected target
allows only `off|metadata`, mandatory immutable evidence and exact-target Rules as
untrusted guidance; enriched context and external federation are rejected.
`OCR_GITLAB_TARGET_PROTECTION_MODE=unprotected` is the sole explicit operator
opt-in; the required default and malformed values fail closed before OCR.
An actually unprotected target cannot reach the approval executor.

## DLP and publication

`OCR_DLP_ENABLED` is a strict boolean that defaults to `true`. The effective value
is resolved once before acquisition and is shared by local and GitLab execution.
With DLP enabled, context and federation ingress/egress plus publication sinks
cross the shared detector. Private retention is checked separately.

A parsed false value bypasses those DLP checks for one run, emits a prominent warning in
private logs and bounded Technical details, and always blocks automatic approval.
Schema, byte/item/time/origin, identity, evidence, cleanup and posting-transaction
gates remain active. Disabling DLP can expose sensitive data to an upstream MCP,
the model, local Markdown, or GitLab. Re-enabling it cannot retract prior egress
or publication. Operators should diagnose locally with
`--preserve-private-artifacts` before using this escape hatch and must keep those
owner-only artifacts off shared storage.

Publication accounting keeps OCR coverage, DLP projection and provider posting
separate. DLP omission cannot relabel complete OCR coverage as partial. Previous
comments are preserved with the actual incomplete-stage reason. Posting counters
cover admitted findings; DLP omissions are separate.

Forbidden values carry one or more closed source classes registered before
rejection: `forge_discussions`, `remediation_threads`, `ci_outcomes`,
`external_context`, `operator_secret`, or `other`. Each rejected item counts each
matching class once. Counts may overlap and need not sum to total omitted items.
Rejected text is not retained or reprocessed later to infer attribution.
`ocr.publication-dlp-signal/v3`, Technical details and receipt v9 expose only
bounded states and counts.

## Preserved controls

- Repository reads use immutable objects, fixed roots and bounds, reject unsafe
  symlinks/submodules, and never execute repository content.
- Unknown, malformed, unavailable, or mismatched provider data fails closed
  before a publication mutation. On a validated provider failure, one separate local line may contain closed protocol detail and bounded aggregate counters;
  raw response text, identifiers, URLs, paths and stderr remain private and cannot
  become a receipt, DLP, telemetry, severity, finding, or approval signal.
- Result and provider reads are byte-bounded; Markdown neutralizes controls and
  GitLab quick actions. Suggestions require exact reviewed-head source proof.
- Publication DLP admits horizontal tab only in `existing_code` and
  `suggestion_code`; unsupported controls remain blocking everywhere else.
- The mandatory evidence MCP requires reconciled attempted/completed action
  accounting and a completed summary. Federation cannot satisfy or replace it.
- Built-in evidence search reads only the already DLP-admitted store and exposes
  stable IDs plus closed metadata. Arguments, queries, scopes, IDs and results
  remain private.
- OCR runs under a fresh owner-only home. Gateway sessions, sockets, caches,
  context stores and owned child processes must clean up before final admission.
- Automatic approval binds exact source, target protection and author identity,
  skips self-approval, never removes an existing approval, and accepts only exact
  receipt v9 with enabled DLP and every existing eligibility gate satisfied.
- Provider lifecycle state is revalidated before publication. A terminal MR keeps
  admitted findings and DLP semantics but cannot approve.
- Ambiguous inline creates use one author-bound readback without retry. Rollback deletes only recorded IDs absent from the baseline; marker text cannot claim
  ownership of another note.
- Secrets and raw transport diagnostics remain outside public notes, fixtures,
  receipts and release artifacts.

## Deployment guidance and residual risks

Use a dedicated bot, protected/masked secrets, least-privilege upstream identities,
and exact pinned OCR/toolkit artifacts. Begin comment-only and enable approval only
after qualifying the selected context and federation behavior. Keep OCR telemetry
off unless its high-cardinality path/group/session data and exporter retention are
accepted.

Pin the exact recommended Open Code Review release and checksum from the
[qualification manifest](../compatibility/ocr-support.json); do not treat an
unlisted patch as compatible merely because its minor line is supported.

The toolkit cannot reverse model or service egress, detect every semantic
paraphrase, make model judgment deterministic, protect data after same-user host
compromise, or prove an upstream's internal authorization. Local stdio process
groups are lifecycle ownership, not a sandbox against a malicious executable or
compromised host.

Optional remote finding images add a separate disclosure boundary. External finding images are disabled by default. Enabling them does not send finding prose,
repository paths, project identifiers, or arbitrary OCR metadata in the image URL,
but viewer and network metadata can reach the image service. Keep text badges when
a third-party image request is unacceptable. GitLab rules, Code
Owners, protected branches and eligible approver policy remain authoritative.

Bandit scans runtime source at medium-or-higher severity and confidence. A narrow
`# nosec B108` temporary-path suppression requires adjacent containment rationale.

The controls align with [MCP authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization), [MCP security best practices](https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices), [OAuth resource indicators](https://www.rfc-editor.org/rfc/rfc8707), [OAuth best current practice](https://www.rfc-editor.org/rfc/rfc9700), and [OWASP API BOLA](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/). References inform the design; they do not prove the implementation.

Repository contribution and vulnerability reporting requirements are in
[SECURITY.md](../SECURITY.md).
