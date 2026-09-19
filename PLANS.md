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

All milestone issues #188–#193 and #203, compatibility issues #201/#202/#204–#207, their
dependencies, the full Python/build/dev/Actions dependency stack, and relevant
engineering-workflow 0.9.6 improvements. Qualify OCR through at least v1.12.2;
check for newer stable OCR again near final qualification.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Full plan, plan-only push, then local work until final draft | WQ-01, WQ-10 | in_progress |
| REQ-002 | #189 architecture, mandatory internal evidence MCP, M7/M8 reconciliation | WQ-03 | done |
| REQ-003 | #190 registry and bounded multi-service gateway | WQ-04 | done |
| REQ-004 | #191 schema/origin/DLP/budget/lifecycle controls | WQ-04, WQ-05 | done |
| REQ-005 | #192 safe legacy policy migration and public contracts | WQ-05, WQ-07 | done |
| REQ-006 | #193 content-free receipts, actual-use approval, local/GitLab parity | WQ-06 | done |
| REQ-007 | #203 stage-aware DLP and source-class accounting | WQ-06 | done |
| REQ-008 | #201/#202/#204–#207 latest stable OCR qualification/local update | WQ-02, WQ-08 | done |
| REQ-009 | Dependency updates and pre-commit/pre-push privacy gates | WQ-02, WQ-09 | done |
| REQ-010 | Independent architecture/security reviews, full acceptance and draft handoff | WQ-03, WQ-09, WQ-10 | in_progress |
| REQ-012 | Rolling runtime support of verified OCR versions, two active lines plus one deprecated | WQ-08 | done |
| REQ-013 | Explicit CI-controlled DLP disable mode with risk warnings and local/GitLab parity | WQ-06, WQ-07 | done |
| REQ-011 | Adopt material workflow 0.9.6 improvements preserving canonical owners | WQ-03 | done |

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

- GitHub milestone v0.11.0; issues #188, #189, #190, #191, #192, #193, #201, #202, #203, #204, #205, #206 and #207.
- OCR compatibility runs 34852856760 and 34970171113 and upstream OCR releases/consumed contracts.
- AGENTS.md, docs/development.md, docs/release.md, project_principles.md,
  m5_context_contracts.md, review-decision-flow.md and public configuration,
  security, context, operations and local/GitLab contracts.
- Approved conversational plan and subsequent user decisions; installed
  engineering-workflow 0.9.6 and tgrep-search instructions.

### User Decisions And Answers

- Remote execution was not authorized. The user explicitly objected after root
  contacted an existing SSH alias to seek a Linux qualification environment.
  All remote access, including cleanup/readback, is stopped. Continue only in
  the local workspace and local Docker. Ask before any future environment change.
  Retained worker evidence reports source/compatibility snapshots transferred to
  remote scratch, disposable amd64/proot Docker experiments, then scratch removal
  before the stop. Removal of pulled image tags/named containers was attempted but
  not verified. No credentials or agent forwarding were transferred. No further
  remote readback/cleanup is authorized. Include this residual uncertainty in handoff.

- Runtime accepts qualified exact patches within the rolling last three stable
  major/minor lines: newest two supported, oldest deprecated. For 1.12 this means
  1.11/1.12 supported, 1.10 warning, below 1.10 rejected. monitoring_floor remains
  discovery-only; unqualified patches are not silently accepted. Historical
  evidence remains readable without granting current runtime support.
- OCR is the primary integration point for SDK selection. SDK v2 is the basis
  once actual OCR integration qualifies it; upstream sessions independently
  negotiate any explicitly supported wire revision.
- Toolkit DLP remains enabled by default. `OCR_DLP_ENABLED=false` explicitly
  disables inbound/outbound context and publication DLP for that run, emits a
  prominent private log warning plus bounded Technical-details warning, and makes
  the run comment-only. Invalid values fail before OCR. The receipt records the
  effective state. Local Markdown may contain sensitive model output when disabled;
  documentation must recommend local `--preserve-private-artifacts` diagnosis before
  this escape hatch and explain that disabling cannot retract data already sent or
  published. GitLab and local use the same resolved setting and formatter.

- The initial already-pushed plan commit remains unsigned under the user's explicit
  waiver. Signing keys are now loaded; all later local feature commits must be signed.
  Do not rewrite the published plan commit.

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
| WQ-01 | Materialize/fidelity-check plan, synchronize base, plan-only commit and push | done |
| WQ-02 | Privacy gates, dependency inventory/updates, forward-only grouping probe and OCR through 1.12.7 | done |
| WQ-03 | Freeze architecture/protocol/limits, independent design review, workflow and M7/M8 owners | done |
| WQ-04 | Registry v2, SDK transport, schema/DLP admission, bounded gateway/cache/lifecycle | done |
| WQ-05 | Integrate mandatory evidence/local/GitLab lifecycle; remove direct/adapter execution; migrate policy | done |
| WQ-06 | Versioned federation receipt/actual-use approval and #203 stage-aware source attribution | done |
| WQ-07 | Public configuration/migration/security/operations/examples/decision-flow and evidence matrix | done |
| WQ-08 | Near-final latest OCR check, adjacent-chain qualification, verified local binary update and pins | done |
| WQ-09 | Independent security/architecture review, remediation, full local quality/package/privacy acceptance | done |
| WQ-10 | Final signed commits/push, draft feature PR, exact-head CI readback and next-environment handoff | in_progress |

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
fallback. Qualify adjacent OCR releases through at least 1.12.7. Near final review,
query stable releases once, pin the observed upper bound and qualify the adjacent
chain; do not continuously chase releases. Promote only compatible evidence and
semantically reviewed changes. Verify local platform binary/checksums and keep
recovery available. Review consumed preview/language changes and update examples,
support manifest, fragments and affected qualification.

Update stable compatible Python/build/dev/Actions dependencies, lock and immutable
SHA pins while preserving Python 3.12–3.14, permissions and publication authority.

#### DLP operator escape hatch

`OCR_DLP_ENABLED` is a strict boolean owned by the public configuration contract;
unset is enabled. The effective state is resolved once before acquisition and passed
to context/federation admission, publication projection, receipt and local/GitLab
reporting. Disabled mode bypasses DLP checks only; schema, byte/item/time/origin,
cleanup, identity, result and posting transaction gates remain enforced. It never
changes upstream authorization, resource allowlists, evidence completeness or
mandatory internal MCP use. Disabled mode is approval-ineligible even when no unsafe
content is observed. Logs and Technical details disclose only the mode/risk, not
protected values. Tests must cover false/true/unset/invalid values, input and output
bypass, retained non-DLP bounds, local Markdown warning, GitLab summary warning,
receipt hostile readback and approval denial.

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
- DLP toggle: default byte-equivalent enforcement, strict invalid-value rejection,
  disabled inbound/publication behavior with non-DLP gates retained, warning parity,
  receipt binding and unconditional comment-only approval result.
- Final scripts/quality.sh check with scoped coverage, dependency audit, lock,
  manifest/evidence, installed wheel/sdist, actual checksum-verified OCR with
  synthetic peers, documentation/example validation and rendered decision-flow.
- Independent semantic security and architecture reviews, then overall self-review;
  remediate findings and rerun affected gates. No Codex Security plugin.
- Read exact final remote head and every required CI job; distinguish local
  qualification from hosted compatibility evidence and configured-model quality.

### Latest Validation Results

Plan-only commit 4369ca9 was pushed after candidate/tree/history Gitleaks and plan
privacy checks. Its unsigned state remains under the explicit waiver; keys are now
loaded for later signed commits. No implementation push has occurred.

OCR v1.12.0 through v1.12.7 passed the adjacent native Darwin arm64 and local
Docker linux/amd64 matrix with official asset/checksum verification. The manifest,
GitLab pin and local binary now select v1.12.7; the prior v1.12.6 binary is retained
in the owner-only local backup. Upstream MCP/LLM protocol sources and Go MCP SDK
v1.7.0 did not change from v1.12.2 through v1.12.7. Issues #201/#202/#204–#207
remain open; no separate v1.12.6 or v1.12.7 issue existed at the checkpoints.

Registry v2, SDK-v2-primary federation, independent SDK-v1/v2 peer negotiation,
mandatory evidence separation, receipt v9, legacy-policy migration, stage-aware DLP
and the default-on DLP escape hatch are implemented with current public contracts.
The final feature gate passed with 1761 tests, two skips and 339 subtests, 86.17%
total coverage and all scoped coverage floors. The compatibility/public-contract
scope passed 273 tests and 40 subtests, and the opt-in actual OCR/SDK-v1/v2
federation matrix passed 53 tests against the installed binary. Fresh wheel and
sdist builds pass Twine validation. Ruff, mypy, Bandit, pip-audit, tree Gitleaks,
public-content privacy and diff checks are green from their latest applicable
runs. Independent full-diff architecture/security review found five issues in
test discovery, HTTPS cleanup accounting, hostile receipt parsing, reserved-name
admission and isolated-child DLP propagation; all were remediated and the reviewer
verified the affected 92 tests and 40 subtests clean. No actionable findings remain.

Workflow 0.9.6 improvements were adopted through existing project owners: bounded
long-running logs, explicit boundary evidence, staged/tree privacy gates and
post-commit truth. No competing plan/archive lifecycle was introduced.

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

WQ-10: inspect and stage the final tree, run candidate-content privacy gates,
create the signed implementation commit, then perform the one final push, open the
draft feature PR, read back its exact head/checks and record the next-environment
handoff. All implementation remains local until that push.

### Plan Fidelity Check

- [x] All requested issues, dependencies and additions map to requirements/queue.
- [x] User decisions, publication boundaries and non-goals are explicit.
- [x] Architecture, risks, acceptance and recovery retain approved plan meaning.
- [x] Exact first safe action and handoff boundary are recorded.

### Reconciliation Check

- [x] Planning baseline and implementation-not-started truth are separated.
- [x] Release delivery remains pending; no external completion is claimed.
- [x] Base remains 458d967; only the plan commit is remote and all implementation
  remains unpushed until the final signed checkpoint.
- [ ] Retain exact final-head evidence after authorized publication.

### Closure Gate

- [x] All current implementation requirements and local acceptance checks pass.
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
