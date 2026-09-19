# Bounded review context

Review context is selected by `OCR_REVIEW_CONTEXT_MODE`: `off`, `metadata`, or
`enriched`. OCR remains the only review/model loop. Repository evidence always
uses the mandatory internal MCP; operator configuration cannot replace or remove
it. Optional external tools use the separate governed federation described in
[configuration](configuration.md#governed-mcp-federation-and-trust-boundary).

## Modes and lifecycle

`off` retains only the validated review identities needed for execution and
publication. `metadata` adds bounded merge-request title, description, labels,
and source branch. `enriched` additionally reads the protected-target policy and
can acquire generic GitLab discussions, verified remediation threads, and exact
same-revision CI outcomes before OCR starts.

All selected text is untrusted. Acquisition, model projection, publication, and
retention are separate stages with separate limits and DLP decisions. Context
cannot add tools, authorize credentials, change review policy, suppress findings,
issue lifecycle commands, or grant approval. The private context store exposes
only committed records through fixed `context_list` and `context_get` tools on
the mandatory internal MCP; neither tool has network, subprocess, arbitrary URL,
arbitrary identifier, search, traversal, or write authority.

## Protected-target policy v4

The toolkit reads only `.opencodereview/review-context-policy.json` from the
captured target-policy commit. New policy documents use
`ocr.review-context-policy/v4`. V4 retains the bounded aggregate budgets,
`forge_discussions`, `remediation_threads`, and `ci_outcomes` selectors from the
established contracts. It does not accept `references`: external acquisition is
now governed by operator registry v2 rather than policy-selected executable
adapters.

Discussion selectors define account classes, resolved/outdated selection, age,
item and text limits, required/optional behavior, and closed projections. A
verified remediation bundle begins only at a toolkit-owned root whose author and
marker/fingerprint match the live review identity; its ordered replies remain
historical evidence, never proof that current code is fixed. Any admitted
remediation record makes the review comment-only.

CI outcomes select exact job names and truthful path prefixes. The GitLab edge
reads bounded pipeline/job metadata twice for the exact reviewed SHA. It never
downloads logs or artifacts. A unique current passing job can challenge a narrow
runtime claim for a declared path, but it cannot suppress a finding, establish a
clean review, change severity/lifecycle, or authorize approval.

Start optional selectors with `required: false`. A stable complete snapshot with
zero selected records is complete. When `required: true`, unavailable, mutated,
DLP-rejected, or bounded-partial acquisition is required degradation and makes the
run comment-only; it still does not fabricate evidence.

Complete private-safe examples are in
[`examples/gitlab/context/`](../examples/gitlab/context/).

## Legacy policy v1-v3 migration

Policy v1, v2, and v3 remain parse-only compatibility inputs. Their safe native
selectors continue to work: v1 discussions, v2 remediation threads, v3 CI
outcomes, plus their established budgets, rules and guidance. The toolkit emits
one private migration warning and at most one bounded Technical-details warning
for an accepted legacy policy.

Legacy `references` are never executed. No command, endpoint, adapter protocol,
credential, candidate identifier, or legacy result is passed to OCR or converted
implicitly into registry v2.

- Optional legacy references are marked unavailable and skipped. Other safe
  selectors can still produce a review, subject to their normal gates.
- Any required legacy reference makes the context required-degraded and the run
  comment-only.
- A policy whose only selected work is legacy references follows the same rule:
  optional references produce no external records; required references degrade
  the run. It never restores legacy execution.

Migrate by moving reviewed external services into the operator-owned
`OCR_MCP_SERVERS_JSON` registry v2 and then removing `references` while advancing
the protected policy to v4. Registry tools are model-directed federation tools;
they are not a field-for-field replacement for the old pre-OCR adapter records.
Reassess schemas, origins, assurance and credentials rather than copying an old
adapter definition.

`OCR_REVIEW_CONTEXT_ADAPTERS_JSON`, adapter request/response frames, executable
adapter examples, `OCR_MCP_REPLACE`, and legacy direct-passthrough registry shapes
are removed. Their presence fails closed with migration guidance.

## Handles and completeness

The private `ocr.context-store/v2` is independent from repository evidence. It is
written atomically with owner-only permissions and read back as hostile input
before OCR. Only a normalized, bounded, DLP-admitted record receives a random
run-bound `ctx1_` handle. The mapping binds the run, policy digest, source,
projection, version/digest and expiry without encoding an upstream identifier.

`context_list` accepts only closed filters, a bounded page size and an opaque
cursor. `context_get` accepts one previously listed handle and returns only its
model projection. Invalid, expired, wrong-run, wrong-policy, missing or forged
handles fail before record access. Context calls never satisfy the independent
mandatory evidence-summary requirement.

Completeness is per selected source. Optional non-DLP degradation is visible and
cannot support an absence claim. Required degradation, selected-source DLP
rejection, or malformed state cannot be hidden by successful records from another
source.

## DLP, publication and source accounting

With the default `OCR_DLP_ENABLED=true`, selected context and federation content
cross DLP before model egress, and every renderable result crosses publication
DLP. Private retention is checked separately. Publication filtering does not
rewrite OCR coverage: a complete OCR manifest remains complete while omitted
public fields and findings are reported as publication omissions.

Forbidden values are registered with a closed source class at acquisition:
`forge_discussions`, `remediation_threads`, `ci_outcomes`, `external_context`,
`operator_secret`, or `other`. Each rejected item counts each matching class at
most once. Classes may overlap, so source-class counts do not need to sum to the
total omitted-item count. The toolkit never retains rejected text merely to infer
its class later.

Previous review comments are preserved with the actual incomplete publication
reason. Posting counters describe admitted findings only; DLP omissions are shown
separately. The `ocr.publication-dlp-signal/v3` marker and receipt v9 carry only
closed counts and state, never protected content, paths, identifiers, URLs, or raw
errors.

`OCR_DLP_ENABLED=false` is a strict operator escape hatch. It disables context,
federation and publication DLP for that run, adds a prominent local/GitLab warning,
and always blocks automatic approval. Sensitive data may leave through service
egress, local Markdown, or GitLab publication, and enabling DLP later cannot
retract it. Use local `--preserve-private-artifacts` diagnosis before considering
this setting; non-DLP schema, size, origin, identity, cleanup, evidence and posting
transaction gates remain enforced.

## Receipt and cleanup

Receipt v9 binds review identities, context mode and per-source state, legacy
policy state, DLP mode, stage-aware publication accounting, mandatory evidence,
governed federation reconciliation, and cleanup. It is content-free. Receipt
v1-v8 cannot authorize current posting or approval; ephemeral results have no
migration path.

`OCR_GITLAB_TARGET_PROTECTION_MODE` defaults to `required`. Exact `unprotected`
permits only the bounded comment-only contract described above; missing target
Rules, enriched context, or federation still fails closed before OCR.
The static unprotected-target limitation does not change result completeness or status.

A federation receipt records configured aliases and closed attempt/completion/
denial/failure/timeout/DLP/oversize/cache/single-flight counts. OCR attempts are
reconciled independently. Used advisory tools, known failed or denied calls, and
accounting mismatch are comment-only; missing/corrupt/unfinalized receipts or
uncertain cleanup block normal publication. Unused services and successful
`review_read` use are not independent approval blockers.

Ordinary runs remove OCR sessions, the context store, gateway sockets, caches,
and owned child processes before final admission. Unknown cleanup blocks
publication. Local diagnostic retention is owner-only, produces no posting-
eligible receipt, and must never be uploaded as a public artifact.

## Deployment boundary

Use dedicated least-privilege identities. Upstream services remain responsible
for tenant and object authorization; a valid registry and successful TLS do not
make a broader credential safe. The toolkit cannot make a lying service truthful,
protect same-owner memory after host compromise, reverse model or service egress,
detect arbitrary semantic paraphrase, or make model judgment deterministic.
