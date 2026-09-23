# Execution Plans

<!-- engineering-workflow:upgrade-plan:start -->
## Active Plan: Engineering Workflow Upgrade 0.9.8

Status: ready_for_closure
Owner: root
Last Updated: 2026-09-23
plan_schema_version: 2

### Goal

Upgrade only the target repository workflow layer to engineering-workflow 0.9.8 while preserving repository-owned documentation and configuration.

### Plan Origin

direct_execution

### Requested Scope

- Materialize the full migration plan before any other target write.
- Add missing canonical workflow structure, exact ownership state, and optional agent configuration only when explicitly selected.

### Requirement Traceability

| Requirement | Complete outcome | Source | Work queue | Acceptance or validation | Status |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | Full migration plan is the first target write. | engineering-workflow contract | WQ-01 | Plan schema validates. | done |
| REQ-002 | Workflow owners, instruction graph, archive indexes, and manifest reach 0.9.8 while preserving protected prose. | migration report | WQ-02 | Instruction and plan checks pass; marker-only protected changes are reviewed. | done |
| REQ-003 | Runtime agent configuration follows the explicit selection. | user invocation | WQ-03 | Config and generated profiles parse and name available GPT-6 models. | done |
| REQ-004 | Deliver the migration through the protected v0.11.1 feature PR. | user request | WQ-04 | Exact-head CI and reviewed merge complete. | done |

### Explicit Non-Goals

- Do not rewrite product, domain, architecture, operations, QA, release, security, or external-tracker prose. Existing owner headings may receive the exact markers needed by instruction contract v3.

### Constraints

- Unknown ownership remains protected; no shared file is replaced wholesale; rollback must remain bounded.
- The user explicitly authorized a one-time bypass of the skill migration privacy hard block; do not expose scanner candidates or apply this exception to publication checks.

### Inputs And Sources

- Canonical source: https://github.com/xeonvs/codex-engineering-workflow
- Read-only target audit and migration report generated before apply.

### User Decisions And Answers

- Runtime agent configuration requested: yes.
- User explicitly authorized temporary bypass of the migration privacy hard block for this update.

### Completed Baseline State

- [x] WQ-00 — Target topology, ownership, conflicts, privacy signals, and proposed changes were audited without executing repository code.

### Current Work Queue

- [x] WQ-01 — Materialize this full plan for REQ-001 as the first write. `done`
- [x] WQ-02 — Apply and validate canonical workflow/manifest changes for REQ-002. `done`
- [x] WQ-03 — Preserve or structurally merge runtime configuration for REQ-003. `done`
- [x] WQ-04 — Deliver the reviewed migration with the v0.11.1 feature PR for REQ-004. `done`

### Locked Decisions

- Protected and unknown files remain untouched unless a later explicit decision changes ownership.

### Verification

- REQ-001: structural plan validation.
- REQ-002: manifest, ownership, privacy, and protected-file checks.
- REQ-003: TOML parse and exact configuration diff when selected.
- REQ-004: exact-head protected CI and merge evidence.

### Latest Validation Results

- 2026-09-23: instruction contract v3 and archive/plan checks pass; all new TOML profiles parse. Repository public-content and Gitleaks gates passed. Protected PR #216 passed exact-head CI and merged as 0b589f0; its development TestPyPI workflow 35831251267 succeeded. The migration upgrader's broad privacy scan returned a hard block on pre-existing source/fixture categories; the user authorized a one-time manual migration. Publication secret gates remain required.

### Risks And Recovery

- Risk: partial migration. Recovery: restore captured file snapshots in reverse mutation order and record the exact failure.

### Resume Point

- Migration requirements are complete. Preserve this plan until the v0.11.1 release PR reconciles the active plan into execution history; continue at the first unfinished release work item below.

### Plan Fidelity Check

- [x] Outcomes, source URL, invocation decision, constraints, queue, validation, recovery, and resume state are preserved without compression.

### Reconciliation Check

- [x] Requirements, queue, validation, working tree, manifest, and statuses agree; completed text has no stale next-work state.

### Closure Gate

- [x] Every migration requirement and queue item is terminal, validation is current, and no promoted backlog or index state is stale.
- [x] Resume Point contains no unfinished migration work; closure will accompany release-plan reconciliation.

### Post-Close Delivery

- The migration is carried by the v0.11.1 protected feature PR; stable publication remains owned by the release plan below.

### Handoff Notes

- Continue only from the first unfinished queue item after reconciling target state.
<!-- engineering-workflow:upgrade-plan:end -->

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

## v0.11.1 complete delivery

Status: active
Plan Origin: plan_mode_approved
Release classification: release-required
Target stable version: 0.11.1

### Goal and requested scope

Deliver #214, repair the OCR qualification environment and failure diagnostics,
qualify adjacent OCR releases through v1.12.9 (check once for a newer stable near
qualification), and publish v0.11.1 through draft feature and release PRs.
Deliver the requested engineering-workflow 0.9.8 documentation and GPT-6 profile
activation as the first slice of the same protected feature PR.

### Requirements and decisions

- R1: Generate one frozen runtime lock without default groups; install hashed
  binary dependencies, the verified wheel, and run pip check plus real MCP probes.
- R2: Preserve exactly two registry distributions. Add runtime-requirements.txt
  as an attested auxiliary GitHub asset and receipt-v2 digest; bind recovery,
  immutable inventory and checksum readback to the same bytes.
- R3: Install locked runtime dependencies in qualification; persist bounded safe
  status on unexpected harness errors. Missing mcp_types is an environment bug,
  not evidence of upstream incompatibility.
- R4: Qualify upstream rules, exclusions and path contracts; preserve historical
  evidence and freeze the prior epoch if current probes change.
- R5: Complete draft -> ready -> protected merge -> dev publication -> release
  PR -> stable publication -> issue/milestone closure -> no-release closure PR.
- R7: Pause scheduled OCR qualification indefinitely from 2026-10-01 UTC;
  preserve manual dispatch and complete this release's current qualification.
- R6: CI owns published-artifact hashes, provenance, receipts and install checks.
  Root checks workflow outcomes/assets/closure through APIs, without redundant
  local downloads or installs of the published artifacts.

### Inputs and boundaries

Issues #214, #217, and #218 in milestone v0.11.1; failed historical qualification
runs 35609962907 and 35728150883; successful bounded run 35831453766 owns
adjacent v1.12.8–v1.12.9 evidence. docs/release.md and docs/development.md own
lifecycle/validation.
Trust inputs: registry and GitHub metadata, downloaded assets, hashes, installed
package metadata, OCR binary behavior and receipt recovery state. Preserve
closed schemas, bounded acquisition, exact reviewed commits and fail-closed
publication; never replace already-published versions or immutable assets.

### Work queue and ownership

1. Done locally: integrate receipt v2, artifact ownership, workflow delivery,
   example and docs; incorporate the v0.9.8 workflow migration and GPT-6 profiles.
2. Done locally: qualification environment, safe failure status including setup
   failure, forward-only contracts and frozen historical evidence; scheduled
   pause starts 2026-10-01 UTC while manual dispatch remains available.
3. Done locally: official recipe and real installed-artifact helper/probes,
   including a negative clean-install control.
4. Done: aggregate review, signed feature commit, Gitleaks, draft PR #216,
   exact-head CI, protected merge 0b589f0, and successful development workflow
   35831251267.
5. Current: inspect compatible evidence from hosted run 35831453766 and
   adjacent source; prepare and merge a protected OCR promotion PR for issues
   #217 and #218. Then prepare/merge draft release PR, monitor CI publication,
   and reconcile closure.

### Validation and efficiency

Run focused tests while editing and one final local quality gate on integrated
implementation. Reuse successful checks for unchanged inputs. CI owns Linux
3.12 first and the remaining supported matrix, candidate qualification and
published-artifact verification. Review every logical slice and final diff;
Gitleaks before commits and each push. Keep logs private and return bounded
summaries. No remote host, no Codex Security plugin, no unrelated upgrades.

### Risks and recovery

Missing dependency setup can fail before status exists; retain a safe harness
failure receipt and make issue/artifact steps report it. Schema evolution must
not silently accept v1 receipts for a v2 release. Recover only exact reviewed
artifacts; conflicting published hashes stop delivery. New upstream behavior
requires human source review, not a weaker qualification gate.

### Current state and resume

Feature implementation is merged into current main as 0b589f0; all protected
feature checks passed and development publication succeeded. Hosted OCR evidence
for 1.12.8 and 1.12.9 is compatible with a human-review-required chain; adjacent
source review found consumed F# Rules/selection and exclusion changes, with no
additional toolkit adaptation indicated. Next safe action: on the new branch
from main, promote the exact reviewed evidence and pins, include the Rules
changelog, then review/test and open its protected draft PR. User has authorized
ready/merge/publication after gates; no separate draft approval pause.
