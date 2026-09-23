# Agent Execution Pitfalls

incident_schema_version: 1

This is a diagnostic catalogue of recurring incident classes. Current requirements live with each linked canonical owner; routes make them reachable and guards identify the control. Entry fields and lifecycle follow the installed `engineering-workflow` instruction lifecycle.

### INC-001 Delivery closed at readiness

- Symptom: A feature merge or development package was treated as delivery while stable users still received the old contract.
- Cause: missing_rule
- Invariant: release.delivery-lifecycle
- Owner: docs/release.md#release-required-changes
- Route: release-lifecycle
- Guard: release_gate:.github/workflows/release.yml
- Evidence: [0.2.0 process correction](../engineering/execution_history/releases.md#plan-toolkit-0-2-0). Prior control: release authorization, receipt, immutable-release, registry, provenance, install, and issue-closure checks in `.github/workflows/release.yml` and their release test suites. Historical cause: implementation and stable delivery were modelled as separate objectives.
- Status: guarded
- Retirement: Retire when this historical class no longer improves diagnosis and its owner, route, and guard remain established.

### INC-002 Candidate supplied its own release authorizer

- Symptom: Candidate code could decide whether its own tree, metadata, and checks authorized publication.
- Cause: unguarded_rule
- Invariant: release.protected-authorization
- Owner: docs/release.md#stable-release
- Route: release-lifecycle
- Guard: release_gate:.github/workflows/release.yml
- Evidence: [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7). Prior control: `.github/workflows/release.yml` checks out the protected reviewed base for authorization; `tests/test_release_authorization.py` binds that checkout separately from candidate inspection. Historical cause: exact-tree validation did not establish the trust source of the validator.
- Status: guarded
- Retirement: Retire when this historical class no longer improves diagnosis and its owner, route, and guard remain established.

### INC-003 Status representations drifted from current state

- Symptom: Implemented scope remained in the backlog or status tables, diagrams, and narrative current-state prose disagreed.
- Cause: unreachable_rule
- Invariant: development.status-reconciliation
- Owner: docs/development.md#planning-and-documentation-lifecycle
- Route: development-validation
- Guard: manual_review:compare status documents with current implementation
- Evidence: [execution-history index](../engineering/execution_history/README.md). Prior control: logical-commit and release-PR self-review reconcile current code, roadmap table and diagram, backlog, strategy, and README before changing milestone state. Historical cause: the implementation changed without selecting every status-bearing representation owned by the milestone.
- Status: guarded
- Retirement: Retire when this historical class no longer improves diagnosis and its owner, route, and guard remain established.

### INC-004 A completed plan remained in the active registry

- Symptom: `PLANS.md` retained an externally reconciled release cycle and became a second release-history database.
- Cause: conflicting_rule
- Invariant: release.external-reconciliation
- Owner: docs/release.md#external-reconciliation-and-plan-archiving
- Route: release-lifecycle
- Guard: manual_review:reconcile current archive and external receipts
- Evidence: [M2 archive correction](../engineering/execution_history/releases.md#plan-toolkit-0-5-0). Prior control: ordinary release-PR documentation review follows the canonical lifecycle; no archive-specific executable gate is needed. Historical cause: active-state and archive lifecycle descriptions prescribed different retention points.
- Status: guarded
- Retirement: Retire when this historical class no longer improves diagnosis and its owner, route, and guard remain established.

### INC-005 Unpublished history reached the remote secret scan first

- Symptom: Tip validation passed, but a secret-shaped synthetic value in an intermediate commit failed the hosted feature-range scan after push.
- Cause: unguarded_rule
- Invariant: boundary.public-source-disclosure
- Owner: docs/engineering/project_principles.md#public-source-and-disclosure
- Route: trust-boundary
- Guard: lint:scripts/gitleaks.sh
- Evidence: [M2 rewritten-range gate](../engineering/execution_history/releases.md#plan-toolkit-0-5-0). Prior control: `scripts/gitleaks.sh` fails closed on the pinned engine and complete unpublished feature range; `tests/test_quality_script.py` protects that range construction. Historical cause: local validation did not reproduce the pinned scanner and complete first-parent range.
- Status: guarded
- Retirement: Retire when this historical class no longer improves diagnosis and its owner, route, and guard remain established.

### INC-006 A post-hoc limit was called bounded I/O

- Symptom: A complete subprocess, Git, HTTP, configuration, or protocol payload was captured before its byte, line, record, or time limit was checked.
- Cause: unguarded_rule
- Invariant: boundary.bounded-data-lifecycle
- Owner: docs/engineering/project_principles.md#bounded-data-lifecycle
- Route: trust-boundary
- Guard: test:scripts/quality.sh check
- Evidence: [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7). Prior control: boundary-specific tests exercise over-limit producers, multibyte units, missing terminators, descriptor growth, timeout/termination, and retained prior state. Historical cause: ordinary fixtures tested the final value rather than acquisition at the boundary.
- Status: guarded
- Retirement: Retire when this historical class no longer improves diagnosis and its owner, route, and guard remain established.

### INC-007 Persisted state bypassed hostile readback

- Symptom: A toolkit-created artifact bypassed exact schema, redaction, size, or cross-reference checks when loaded again.
- Cause: unguarded_rule
- Invariant: boundary.persisted-atomic-state
- Owner: docs/engineering/project_principles.md#persisted-and-atomic-state
- Route: trust-boundary
- Guard: test:scripts/quality.sh check
- Evidence: [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7). Prior control: hostile reload tests reject unknown nested fields, replaced or linked artifacts, oversized values, invalid references, and partial state. Historical cause: file ownership was mistaken for future content integrity.
- Status: guarded
- Retirement: Retire when this historical class no longer improves diagnosis and its owner, route, and guard remain established.

### INC-008 A bounded HTTP response became trusted too early

- Symptom: A size-limited response crossed into trusted state before endpoint, redirects, authentication, transfer status, and atomic replacement all committed.
- Cause: unguarded_rule
- Invariant: boundary.network-acquisition
- Owner: docs/engineering/project_principles.md#network-acquisition
- Route: trust-boundary
- Guard: test:scripts/quality.sh check
- Evidence: [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7). Prior control: bounded HTTP tests reject unknown endpoints, unsafe authentication redirects, failed status or transfer, partial output, and non-atomic replacement. Historical cause: a byte limit was treated as the complete trust decision.
- Status: guarded
- Retirement: Retire when this historical class no longer improves diagnosis and its owner, route, and guard remain established.

### INC-009 Git identity was isolated in only one caller

- Symptom: A sibling Git helper, repository configuration, object-store override, or replacement ref changed which object a reviewed SHA named.
- Cause: unguarded_rule
- Invariant: boundary.immutable-git-identity
- Owner: docs/engineering/project_principles.md#immutable-git-identity
- Route: trust-boundary
- Guard: test:scripts/quality.sh check
- Evidence: [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7). Prior control: real-repository tests cover process, global/system, repository, object-store, replacement-ref, path-record, and sibling-caller behavior. Historical cause: isolation was implemented as a local environment checklist rather than one object-identity invariant.
- Status: guarded
- Retirement: Retire when this historical class no longer improves diagnosis and its owner, route, and guard remain established.

### INC-010 Destructive provider write lacked a mutation-time guard

- Symptom: Automation read an expected SHA, then deleted, reset, withdrew, or invalidated state through an endpoint that could not bind that SHA.
- Cause: unguarded_rule
- Invariant: boundary.provider-mutation-identity
- Owner: docs/engineering/project_principles.md#provider-mutation-identity
- Route: trust-boundary
- Guard: test:scripts/quality.sh check
- Evidence: [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7). Prior control: provider transaction tests assert exact-SHA guarded write endpoints and absence of unsupported destructive operations. Historical cause: preflight and readback were treated as a substitute for mutation-time identity.
- Status: guarded
- Retirement: Retire when this historical class no longer improves diagnosis and its owner, route, and guard remain established.

### INC-011 One fixture spelling stood in for a parser contract

- Symptom: Equivalent valid key order, indentation, scalar/mapping, marker, URL, digest, or status forms failed despite one canonical fixture passing.
- Cause: unguarded_rule
- Invariant: boundary.external-format-parsing
- Owner: docs/engineering/project_principles.md#external-format-parsing
- Route: trust-boundary
- Guard: test:scripts/quality.sh check
- Evidence: [M2 framework parser corrections](../engineering/execution_history/releases.md#plan-toolkit-0-5-0). Prior control: semantic-variant matrices exercise equivalent forms, malformed optional values, and bounded degradation that preserves unrelated facts. Historical cause: tests mirrored implementation structure instead of the external grammar.
- Status: guarded
- Retirement: Retire when this historical class no longer improves diagnosis and its owner, route, and guard remain established.

### INC-012 Mocks stood in for installed integration

- Symptom: Unit tests passed while the built artifact failed under the real protocol client, restricted `PATH`, permissions, or hostile working directory.
- Cause: unguarded_rule
- Invariant: boundary.integration-proof
- Owner: docs/engineering/project_principles.md#test-doubles-and-integration-proof
- Route: trust-boundary
- Guard: manual_review:verify clean built artifacts and real external boundary evidence
- Evidence: [M2 release-grade installed-artifact checkpoint](../engineering/execution_history/releases.md#plan-toolkit-0-5-0). Prior control: clean wheel/sdist, hostile-shadow, restricted-environment, private-permission, and real-protocol E2E tests. Historical cause: function behavior was mistaken for installation and process-lifecycle proof.
- Status: guarded
- Retirement: Retire when this historical class no longer improves diagnosis and its owner, route, and guard remain established.

### INC-013 A relevant boundary rule lived only in secondary context

- Symptom: A typical parser, provider, or subprocess change passed routine checks but repeated a known failure class that was described only in a long incident document not selected for the change.
- Cause: unreachable_rule
- Invariant: development.boundary-validation
- Owner: docs/development.md#local-validation
- Route: development-validation
- Guard: test:scripts/quality.sh check
- Evidence: [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7). Prior control: the active plan identifies changed boundaries and focused behavioral tests before the complete quality gate; the incident catalogue is consulted only to diagnose a matching failure. Historical cause: applicability depended on an agent remembering to reread an accumulating secondary rule set.
- Status: guarded
- Retirement: Retire when this historical class no longer improves diagnosis and its owner, route, and guard remain established.

### INC-014 Outcome branches disagreed about the same run

- Symptom: Clean, skipped, warning, or error branches omitted mandatory evidence or described inconsistent completion state.
- Cause: unguarded_rule
- Invariant: boundary.outcome-consistency
- Owner: docs/engineering/project_principles.md#outcome-consistency
- Route: trust-boundary
- Guard: test:scripts/quality.sh check
- Evidence: [0.4.7 final OCR correction](../engineering/execution_history/releases.md#plan-toolkit-0-4-7). Prior control: table-driven result and posting tests cover skipped, clean, warning, error, finding, partial, and zero-value cases through shared contracts. Historical cause: outcomes were assembled independently and tests asserted prose rather than one result invariant.
- Status: guarded
- Retirement: Retire when this historical class no longer improves diagnosis and its owner, route, and guard remain established.
