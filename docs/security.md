# Security and trust model

The toolkit bridges repository and forge content, OCR and its LLM provider,
operator configuration, governed MCP upstreams, CI secrets, and publication APIs.
No input becomes safe merely because a trusted pipeline acquired it.

One runner-owned immutable B/H range is proved before range-dependent evidence
and independently matched to native requested/resolved/exact-range fields at
admission. Complete coverage does not prove range identity. Current result
receipts v13/v14 bind that claim; frozen v9-v12 remain historical readback and
pre-execution v5/v6 keep their unchanged embedded review tuples.

The optional [typed diagram](diagrams.md) has a separate run-bound private output
collector. It accepts no destination or provider-write authority. Whole-unit DLP
checks original labels, conditions and paths alongside immutable source validation;
loss of a sensitive condition omits the complete candidate. The renderer accepts
only admitted types and owns all Mermaid syntax. Optional construction, MCP,
source, cleanup and rendering faults cannot change review health or authorize an
action. This recovery does not bypass mandatory evidence/range gates or atomic
rejection of a malformed persisted result. Only validated fixed output-tool
failures can be excluded from approval's auxiliary-read failure count.

## Threat model

Protected assets include immutable review identities (source H, current MR diff,
actual target T, and policy authority P), coverage and finding integrity,
private evidence/context/result/session data, registry and receipts,
forge/LLM/MCP credentials, external-object confidentiality, and publication and
approval state.

A contributor can control repository content, merge-request metadata and
discussion text, including tool-like instructions and crafted references. An MCP
upstream controls its descriptions, schemas and responses. An operator controls
the reviewed registry, credentials and selected protected policy. A compromised
runner or same-user process remains a host-level threat outside the toolkit's
process-isolation guarantees.

The main trust transitions are:

1. Immutable Git objects and authenticated provider identities cross closed
   bounded parsers. The actual MR code target and protected policy authority
   remain separate; a source branch, arbitrary protected branch, or synthetic
   merge commit cannot stand in for either.
2. Optional metadata and protected-policy discussions/remediation/CI outcomes
   cross normalization, stage-specific DLP and owner-only storage.
3. Repository evidence enters the mandatory internal MCP. Operator registry v2
   cannot remove, replace, rename or shadow that server.
4. Optional external tools cross the toolkit-owned federation gateway. OCR sees
   only frozen `server__tool` aliases through a fixed private relay; upstream
   credentials never enter OCR configuration or arguments.
5. OCR output crosses result validation, publication projection, stage-aware DLP,
   cleanup, a versioned review receipt, current-MR freshness checks and the
   provider posting transaction.

Changed Git submodule pointers are a separate repository-coverage boundary.
For qualified OCR 1.13.3 only, the toolkit compares complete before/after Git
trees, the explicit unfiltered diff, and the ordinary-file projection before
the model runs. It reads `.gitmodules` from immutable blobs without using its
URLs, freezes process-local Git overrides for preview and production, then
checks the native manifest against the ordinary files selected by preview.
User and XDG Git attributes are disabled for this projection; repository
attributes remain input-bound across review and posting.
Type transitions, ambiguous moves, unsafe configuration, unknown diagnostics,
drift, reuse, or mismatched manifest evidence stop the review. Neither the
internal evidence MCP nor an external MCP server can grant review coverage for
a skipped gitlink or authorize a finding about its contents. A v14 receipt
states path-free partial repository coverage and blocks automatic approval and
old finding-thread cleanup; the native OCR manifest retains its own meaning.
`post` independently rechecks the original Git trees and selected native work
before a GitLab write. A v6 no-model status contains only closed counts or a
closed unqualified reason, with the authenticated MR identity.
If publication DLP removes a finding or warning, the filtered handoff omits
the native manifest. Only after validating that manifest, the toolkit carries
a path-free selection proof made of item digests and the source-artifact digest;
`post` checks it against immutable Git changes and the original complete
coverage before publishing any retained finding. A missing or altered proof
stops publication. Git diff output is also bounded while the child runs, so
an oversized patch cannot fill temporary storage before the limit is checked.

The `auto` fallback is sensitive to wrong-project source substitution,
retargeting, default-branch or protection changes, stale diff versions,
cross-job handoff replacement, and policy object replacement. It requires
authenticated same-project IDs and bounded provider/Git reads; a locally
available SHA or CI declaration alone is
not authority. A forged persisted receipt cannot fill missing v13 authority
fields from older versions. Configured federation still carries
confused-deputy and object/tenant authorization risk: DLP and origin checks do
not repair an overprivileged upstream service. These controls do not secure an
untrusted CI job or runner, or an already exposed CI credential.

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

The content-free `ocr.federation/v2` receipt records closed per-alias counts,
argument/result DLP gate and reason counts, and cleanup state. Legacy v1
receipts remain readable but do not identify the rejection boundary or reason.
Receipt v13 reconciles OCR attempts independently with gateway
attempts and terminal outcomes. Used advisory tools, known denied/failed calls,
or accounting mismatch make the run comment-only. Missing, malformed,
unfinalized or cleanup-uncertain federation evidence blocks normal publication.
Result-gate DLP denial means the external context was unavailable to the
review; it is never recast as an OCR finding or public omission.
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
Source policy and MR discussion text cannot grant tools, credentials or consent.
The missing `OCR_GITLAB_TARGET_PROTECTION_MODE` setting now selects `auto`: an
actually unprotected target can use the authenticated same-project protected
default branch P for Rules, context policy and governed federation. The review
still uses the actual `B..H` MR diff, keeps target T separate, and remains
comment-only. Bounded target-snapshot facts at T are untrusted code context;
they carry no policy, completeness, tool, posting or approval authority. The
explicit `unprotected` setting retains the earlier limited
`off|metadata`, exact-target Rules and no-enrichment/federation profile;
`required` rejects an unprotected target. Malformed values fail before OCR.
Neither protected P nor a clean current-MR review proves the unprotected target
is safe to merge into P. An actually unprotected target cannot reach the
approval executor for a new approval write.

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
`ocr.publication-dlp-signal/v4`, Technical details and receipt v13 expose only
bounded states and counts. Publication `ocr.publication/v2` separates omitted
public fields and reasons from private-only sanitized fields and reasons; OCR
coverage and provider posting counts remain independent.

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
  `suggestion_code`. HTML-like syntax in those fields additionally requires
  exact immutable reviewed-head source proof and safe code rendering. All
  other sensitive-data checks still run on the original text; unproved code
  and prose retain the HTML restriction.
- The mandatory evidence MCP requires reconciled attempted/completed action
  accounting and a completed summary. Federation cannot satisfy or replace it.
- Built-in evidence search reads only the already DLP-admitted store and exposes
  stable IDs plus closed metadata. Arguments, queries, scopes, IDs and results
  remain private.
- OCR runs under a fresh owner-only home. Gateway sessions, sockets, caches,
  context stores and owned child processes must clean up before final admission.
  Optional local ChatGPT authentication exposes only OCR's validated native
  private auth directory through a link in that home. Persistent host/account
  state, refresh and locking stay OCR-owned; credentials are not copied into
  toolkit artifacts. GitLab rejects this option before auth-store access.
- Automatic approval binds exact source, actual target/diff, policy authority,
  protection and author identity, skips self-approval, and accepts only exact
  receipt v13 with enabled DLP and every existing eligibility gate satisfied.
  The toolkit never removes an existing approval; a prior bot approval may
  remain after retargeting under GitLab's approval-reset policy.
- Provider identity, diff, authority and lifecycle are revalidated before normal
  publication and again before an eligible approval. Code-tuple movement and
  changed or unverifiable authority stop the write. Only a proven same protected
  default-policy branch fast-forward may finish against captured P. A v13 result
  whose MR became terminal is not newly published; the prior review remains.
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

Authenticated reads before GitLab publication and approval reduce stale writes,
but they are not mutation-time guards. A provider-side change between the final
read and write remains a residual race. GitLab's merge/approval policy and reset
settings remain the final authorities.

Local ChatGPT authentication is optional; custom API providers remain the
default locally and in GitLab. Native browser login and plan consent authorize
OCR's access under the selected account. Structural preflight does not prove
consent, eligibility, expiry or quota, and an auth failure cannot enable API
billing fallback. The native auth directory remains sensitive persistent state;
keep it private on the trusted host. Filesystem checks do not defend against
same-user host compromise or a malicious native executable.

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
