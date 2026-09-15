# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

## v0.11.0 governed MCP federation and feature draft

Status: active
Plan Origin: plan_mode_approved
Release classification: release-required
Target stable version: 0.11.0

### Goal

Implement M7 governed model-directed MCP federation, stage-aware publication DLP
diagnostics, OCR compatibility and dependency updates, and deliver a verified
draft feature PR. Stable delivery remains pending after this handoff.

### Requested Scope

All milestone issues #188–#193 and #203, compatibility issues #201/#202/#204, their
dependencies, the full Python/build/dev/Actions dependency stack, and relevant
engineering-workflow 0.9.6 improvements. Qualify OCR through at least v1.12.2;
check for newer stable OCR again near final qualification.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Full plan, signed plan-only push, then local work until final draft | WQ-01, WQ-10 | in_progress |
| REQ-002 | #189 architecture, mandatory internal evidence MCP, M7/M8 reconciliation | WQ-03 | pending |
| REQ-003 | #190 registry and bounded multi-service gateway | WQ-04 | pending |
| REQ-004 | #191 schema/origin/DLP/budget/lifecycle controls | WQ-04, WQ-05 | pending |
| REQ-005 | #192 safe legacy policy migration and public contracts | WQ-05, WQ-07 | pending |
| REQ-006 | #193 content-free receipts, actual-use approval, local/GitLab parity | WQ-06 | pending |
| REQ-007 | #203 stage-aware DLP and source-class accounting | WQ-06 | pending |
| REQ-008 | #201/#202/#204 grouping fix and latest stable OCR qualification/local update | WQ-02, WQ-08 | pending |
| REQ-009 | Dependency updates and pre-commit/pre-push privacy gates | WQ-02, WQ-09 | pending |
| REQ-010 | Independent architecture/security reviews, full acceptance and draft handoff | WQ-03, WQ-09, WQ-10 | pending |
| REQ-011 | Adopt material workflow 0.9.6 improvements preserving canonical owners | WQ-03 | pending |

### Explicit Non-Goals

No merge, auto-merge, stable publication, issue/milestone closure or separate
release PR in this stage. No Codex Security plugin. No crawler, vendor backend,
second model loop, semantic prompt-injection detector, managed OAuth, DNS pinning,
generic MCP conformance campaign or hidden legacy execution switch. New DLP
additions beyond #191/#203 and configured-model qualification belong to the next
environment handoff. Synthetic peers do not prove model quality.

### Constraints

- First repository write is this complete plan. Only root owns plan/backlog/state.
- One initial push containing only the plan; no intermediate implementation
  pushes. Final push only after local implementation, reviews and checks finish.
- Signed logical commits; pre-commit Gitleaks of candidate content and privacy
  checks, plus Gitleaks tree/history before every push, including the plan push.
- Preserve release authorization markers, existing protection, historical evidence
  bytes and unrelated local work. A new remote-CI defect requires explicit
  agreement before another corrective push.
- Use bounded tgrep searches with a private index; fresh filesystem searches for
  final absence claims. No credentials, workstation paths or private deployment
  details in public source, plan, fixtures, output or history.

### Inputs And Sources

- GitHub milestone v0.11.0; issues #188, #189, #190, #191, #192, #193, #201, #202, #203, #204.
- OCR compatibility runs 34852856760 and 34970171113 and upstream OCR releases/consumed contracts.
- AGENTS.md, docs/development.md, docs/release.md, project_principles.md,
  m5_context_contracts.md, review-decision-flow.md and public configuration,
  security, context, operations and local/GitLab contracts.
- Approved conversational plan and subsequent user decisions; installed
  engineering-workflow 0.9.6 and tgrep-search instructions.

### User Decisions And Answers

- Signing-key access is unavailable in this environment. User explicitly permitted
  skipping signing here; use unsigned feature commits without changing global Git
  configuration. Protected-main signature requirements remain a later handoff gate.

- Stop at feature draft, not separate release draft or stable publication.
- Include the entire dependency stack and #203 in current implementation.
- Use official Python MCP SDK v2 and a JSON Schema validator behind an explicit
  runtime package boundary. Support interoperable SDK v1/v2 upstream servers,
  independently negotiating wire protocol on each side; OCR need not use SDK v2.
- Keep internal evidence MCP mandatory and unreplaceable by operator registry.
- No Codex Security; retain independent semantic security and architecture review.
- GPT-6-Astra and GPT-5.6 family are permitted; choose bounded role-appropriate
  model/effort. Future DLP additions and configured OCR qualification are handoff.
- Upgrade local OCR after digest verification and qualification. Include releases
  found at one near-final stable-version checkpoint in the final draft.
- Workflow documentation upgrades are authorized, including substantial necessary
  improvements, while preserving project-owned contracts and scope.

### Completed Baseline State

Read-only planning found no active plan and a clean local main at bf9e0f9.
Remote main was 458d96711aec8f0379327f10cd03ccf3f3da180d; reconcile fresh before
branching. No open PR was observed. Fresh issue readback found seven milestone issues and
three compatibility issues; #204 covers OCR 1.12.2. Current package has zero runtime dependencies.
Compatibility failure is the OCR 1.12 grouping inventory/response change from
path strings to indices, not a broken failure-preservation job. Existing receipt
v8 blocks configured external MCP; local output needs shared federation validation.
Existing Gitleaks wrapper scans committed history only, not candidate content.

### Current Work Queue

| Item | Work and acceptance | Status |
| --- | --- | --- |
| WQ-01 | Materialize/fidelity-check plan, synchronize base, plan-only commit and push | in_progress |
| WQ-02 | Privacy gates, dependency inventory/updates, forward-only grouping probe and OCR through 1.12.2 | pending |
| WQ-03 | Freeze architecture/protocol/limits, independent design review, workflow and M7/M8 owners | pending |
| WQ-04 | Registry v2, SDK transport, schema/DLP admission, bounded gateway/cache/lifecycle | pending |
| WQ-05 | Integrate mandatory evidence/local/GitLab lifecycle; remove direct/adapter execution; migrate policy | pending |
| WQ-06 | Versioned federation receipt/actual-use approval and #203 stage-aware source attribution | pending |
| WQ-07 | Public configuration/migration/security/operations/examples/decision-flow and evidence matrix | pending |
| WQ-08 | Near-final latest OCR check, adjacent-chain qualification, verified local binary update and pins | pending |
| WQ-09 | Independent security/architecture review, remediation, full local quality/package/privacy acceptance | pending |
| WQ-10 | Final signed commits/push, draft feature PR, exact-head CI readback and next-environment handoff | pending |

### Locked Decisions

#### Architecture and configuration

OCR is the only model loop. Built-in evidence MCP remains mandatory with usage
and completeness gates; context store stays separate. One federation stdio gateway
mediates explicit upstreams. Configuration owns strict registry/preflight; a
federation package owns transport, admission, dispatch/cache and content-free
receipts; review_runner coordinates lifecycle, not transport. Shared reporting
and receipt validation serve local and GitLab without fabricated local forge claims.

Registry version 2 supports HTTPS for GitLab, HTTPS/explicit stdio for local,
environment-backed authentication through token_from and headers_from, explicit tool allowlists,
advisory default and operator-only review_read assurance. Reject unknown fields,
old shapes, missing secrets, aliases with ambiguous separators/collisions and
missing allowlisted tools before model execution. Freeze bounded schemas and
inventory; untrusted annotations, notifications, policy and content cannot expand
tools or authority. Operator registry cannot remove/replace built-in evidence MCP.

Official SDK v2 plus JSON Schema validator are the documented dependency exception.
Negotiate protocol independently with OCR and upstream peers. Qualify v1/v2 SDK
servers and mixed runs. Enforce bytes while reading, before deserialization;
prove supported transport hooks and teardown before gateway implementation.

#### Safety, cache and lifecycle

Validate bounded schemas/arguments, nested URL origins, outbound DLP, call/run
budgets, deadlines and concurrency. Reuse existing inbound DLP and ForbiddenMatcher.
Bound discovery, schemas, notifications, response bytes/characters/items and run
totals. No partial rejected/truncated content, link dereference or unsupported
resource/media projection. Redirects disabled. Stdio uses no shell setup, bounded
environment and owned child-process cleanup. No secret values in OCR config/argv.

Exact cache/single-flight is run-local and bounded, keyed by server/tool/canonical
arguments. Cache only admitted successes; every caller has one attempt and one
terminal outcome, with delivery budgets applied per return. Cancelling one waiter
does not silently cancel other waiters. Cleanup precedes final admission.

#### Migration, receipts and approval

Remove passthrough, adapter execution, OCR_MCP_REPLACE and restoration switches.
Legacy policy v1/v2/v3 retains safe non-reference discussions/remediation/CI,
budgets/rules/guidance/decisions. Emit one private warning and at most one bounded
Technical-details warning per accepted legacy policy. Optional references skip;
required references degrade/comment-only, including references-only policies.

Use a closed versioned federation receipt and update strict toolkit receipt schema.
Reconcile independently observed OCR/gateway attempts per exported alias. Malformed
arguments rejected inside OCR before dispatch produce a mismatch, never fabricated
gateway counts. Finalized known denied/failed calls may be comment-only; missing,
corrupt/unfinalized receipt or uncertain cleanup blocks normal publication.
Unused services and successful review_read do not independently block approval;
used advisory does. Preserve all existing gates and Technical-details fields.

#### Stage-aware DLP (#203)

Keep OCR coverage, publication projection and posting outcomes independent. Full
OCR coverage remains full after DLP omissions. Preserve previous comments with
the actual incomplete-stage reason. Posting counters describe admitted findings;
show DLP omissions separately. Register forbidden values with closed source class:
forge_discussions, remediation_threads, ci_outcomes, external_context,
operator_secret, other. Each rejected item counts each matching class at most once;
class counts may overlap and do not sum to omitted-item totals. Never infer classes
later by retaining/reprocessing rejected text. Version changed public markers and
receipts; preserve strict readback and existing DLP rejection behavior.

#### Compatibility and dependency evolution

Update one live grouping parser and stub to indices, retaining final path/group
assertions. Freeze prior evidence epoch without changing bytes; no old live-parser
fallback. Qualify adjacent OCR releases through at least 1.12.2. Near final review,
query stable releases once, pin the observed upper bound and qualify the adjacent
chain; do not continuously chase releases. Promote only compatible evidence and
semantically reviewed changes. Verify local platform binary/checksums and keep
recovery available. Review consumed preview/language changes and update examples,
support manifest, fragments and affected qualification.

Update stable compatible Python/build/dev/Actions dependencies, lock and immutable
SHA pins while preserving Python 3.12–3.14, permissions and publication authority.

### Verification

- Per commit: format, focused tests, full diff/self-review, repository Ruff format
  check, git diff --check, candidate-content Gitleaks and path/privacy scan.
- Per push: current public tree and complete unpublished history Gitleaks, privacy
  review and exact commit-set verification. Scanner output stays redacted.
- Gateway integration: actual TLS/stdio/process boundaries, SDK v1/v2/mixed peers,
  mandatory internal MCP, malformed-before-dispatch, collisions, missing tools,
  cache/single-flight with cancellation, streaming bounds, DLP, origins, cleanup,
  hostile/unfinalized receipts and local/GitLab formatter parity.
- Migration: one warning, references-only/optional/required policies, preserved
  discussions/remediation/CI/approval/terminal-MR contracts and no legacy execution.
- #203: full OCR plus filtered discussion finding; private sanitization vs public
  filtering; DLP vs posting omissions; multiple source classes; preservation text;
  no protected content/paths/IDs/URLs/raw errors in public or telemetry output.
- Final scripts/quality.sh check with scoped coverage, dependency audit, lock,
  manifest/evidence, installed wheel/sdist, actual checksum-verified OCR with
  synthetic peers, documentation/example validation and rendered decision-flow.
- Independent semantic security and architecture reviews, then overall self-review;
  remediate findings and rerun affected gates. No Codex Security plugin.
- Read exact final remote head and every required CI job; distinguish local
  qualification from hosted compatibility evidence and configured-model quality.

### Latest Validation Results

Plan materialized; base synchronized to 458d967 and feature branch created.
Candidate plan, public tree and history passed pinned Gitleaks 8.24.3; plan privacy
scan passed. Signed commit failed because configured signing key is locked and
absent from the agent. No commit or push occurred. User was asked to unlock the
configured key locally; automatic Keychain retrieval also failed.
No implementation tests run. Clean baseline observed; installed
engineering-workflow 0.9.6 read. Historical 0.9.5 cache is no longer available;
use current canonical owners rather than an unavailable cache diff.

### Risks And Recovery

SDK ingress/lifecycle hooks, protocol skew, OCR attempts unseen by gateway, cache
cancellation and hostile receipts are high-risk boundaries. Resolve by exact-peer
tests before integration, independent review and fail-closed admission. Preserve
forbidden-source attribution through normalization/deduplication without leaking
content. Do not weaken gates to obtain green tests. Preserve prior OCR binary for
rollback, old evidence bytes and user files. On repeated equivalent failure,
change diagnostic approach. If external CI fails after final push, record exact
failure and request the bounded additional push rather than claiming completion.

### Resume Point

WQ-01: user permitted skipping signing in this environment. Rescan updated plan
and tree, commit only PLANS.md without signing, scan history and push the branch.
Then begin independent implementation slices; signature reconciliation is handoff.

### Plan Fidelity Check

- [x] All requested issues, dependencies and additions map to requirements/queue.
- [x] User decisions, publication boundaries and non-goals are explicit.
- [x] Architecture, risks, acceptance and recovery retain approved plan meaning.
- [x] Exact first safe action and handoff boundary are recorded.

### Reconciliation Check

- [x] Planning baseline and implementation-not-started truth are separated.
- [x] Release delivery remains pending; no external completion is claimed.
- [x] Base refreshed to 458d967; only the plan is changed, no commit/push exists.
- [ ] Retain exact final-head evidence after authorized publication.

### Closure Gate

- [ ] All current implementation requirements and acceptance checks pass.
- [ ] Reviews are resolved and final draft/exact-head CI evidence is recorded.
- [ ] Handoff preserves outstanding DLP/configured-OCR and stable-delivery work.
- [ ] No issues/milestone or stable release are falsely closed at feature draft.

### Post-Close Delivery

Current authorization ends at feature draft. Continue the same draft in an
environment with configured OCR/model provider for new DLP additions and external
qualification. Later: feature merge, TestPyPI development verification, separate
release PR, stable publication and independent receipts under docs/release.md.
Keep the release-required plan active at this checkpoint rather than closing it.

### Handoff Notes

Provide draft URL, exact SHA, package hashes, OCR tag/binary identity, protocol
matrix, reproducible commands, tests/review evidence and explicit remaining work.
Root owns shared state. Use bounded self-contained worker packets and durable
artifacts rather than reconstructing transcripts after context loss. Model roles:
Terra medium for exploration, Sol/Astra medium for isolated implementation, Astra
high for risky independent reviews; up to three workers with disjoint write sets.
