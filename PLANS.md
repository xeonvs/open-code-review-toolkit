# Execution Plans

Use this file for active or blocked work. Stable releases require indexing in
[execution history](docs/engineering/execution_history/README.md).

## Active Plan: Toolkit v0.12.1 issue fixes and stable delivery

plan_schema_version: 2
Status: active
Last Updated: 2026-10-22
Release classification: release-required; target stable version v0.12.1.

### Goal

Fix GitHub issues #248-#253 without weakening review trust boundaries, publish and independently verify v0.12.1, then verify the real release notification and v0.12.1 content on the live site.

### Plan Origin

plan_mode_approved

### Requested Scope

Implement all six open issues, a narrow documentation-only CI gate, one protected feature PR, a protected release PR and stable artifact process, and a final external-reconciliation PR. Audit all project documentation, agent instructions, and routes; fix findings in a separate commit before final reviews. The first feature commit contains only this plan and its active-plan state. Review each logical commit before making it. Run Codex Security before the final feature push, then one correctly invoked local OCR/toolkit review to completion; fix any findings.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | #252 protects remediation content without poisoning ordinary text | WQ-02 | done |
| REQ-002 | #248 distinguishes technical numbers from phone PII | WQ-03 | done |
| REQ-003 | #251 distinguishes proven pure credential references and empty YAML values from literals | WQ-03 | done |
| REQ-004 | #253 publishes proven, safely rendered optional code syntax | WQ-04 | done |
| REQ-005 | #249 gives an explicit truthful gitlink outcome | WQ-05 | done |
| REQ-006 | #250 reports stage-specific outcomes and disjoint DLP accounting | WQ-05, WQ-06 | done |
| REQ-007 | Documentation-only changes avoid unnecessary code/build work without bypassing required checks | WQ-07 | done |
| REQ-008 | Feature commits, review, security scan, one local OCR review and protected merge are verified | WQ-01, WQ-08, WQ-09 | pending |
| REQ-009 | v0.12.1 stable artifacts, immutable receipt, tracked issues and milestone are verified | WQ-10, WQ-11 | pending |
| REQ-010 | Live site displays v0.12.1 after the real release notification | WQ-12 | pending |
| REQ-011 | Exact external facts are archived through a protected closure PR | WQ-13 | pending |
| REQ-012 | Documentation and agent instructions are complete, consistent, deduplicated, and correctly routed | WQ-08 | done |

### Explicit Non-Goals

No OCR upstream change, global DLP allowlist, arbitrary source execution, second model review, separate fresh-clone/host QA, manual replacement of immutable release objects, or speculative reconstruction of historical rejected content.

### Constraints

- Keep producer-owned identity, evidence, DLP, preview, posting and approval boundaries distinct. Unknown diagnostics fail closed. Keep private paths, values, stderr, model text and tool arguments out of public diagnostics.
- #249 uses a toolkit-owned unsupported/degraded outcome tied to immutable Git mode evidence; it cannot claim ordinary-file coverage without proof or follow submodules.
- #253 applies only to optional code units proven against reviewed immutable source and safe for each output sink. Mandatory prose stays conservative.
- A pure reference or technical number never suppresses another secret, forbidden value, PII match, laundering signal, control character or work limit in the same unit.
- The approved site-launch plan is already archived by #256. Site verification for this objective occurs after v0.12.1 publication through the real site release refresh.
- Preserve all protected GitHub checks, signed linear delivery and the release workflow's trusted-base authorization. A documentation-only classifier fails open to full checks when paths or provenance are uncertain.

### Inputs And Sources

- GitHub issues [#248](https://github.com/xeonvs/open-code-review-toolkit/issues/248), [#249](https://github.com/xeonvs/open-code-review-toolkit/issues/249), [#250](https://github.com/xeonvs/open-code-review-toolkit/issues/250), [#251](https://github.com/xeonvs/open-code-review-toolkit/issues/251), [#252](https://github.com/xeonvs/open-code-review-toolkit/issues/252), and [#253](https://github.com/xeonvs/open-code-review-toolkit/issues/253), including complete acceptance examples.
- `docs/engineering/project_principles.md`, `docs/development.md`, `docs/release.md`, `docs/engineering/governed_federation_contracts.md`, `docs/review-context.md`, `docs/review-decision-flow.md`, and current runtime/tests are contract owners. M5 context contracts are historical.
- Current `main` is `c313362`; prior site plan was archived in `docs/engineering/execution_history/2026-10-22-toolkit-site-launch-and-release-notification.md` by #256.

### User Decisions And Answers

The owner chose v0.12.1, all six issues, toolkit-owned truthful gitlink degradation instead of OCR upstream modification, and no extra fresh clone or host checks. Mandatory CI and published-package smoke still apply. Fixes come first; verify the live site only after the actual v0.12.1 release dispatch. A documentation-only CI gate was approved, but workflow changes themselves require full checks. The feature PR begins with a reviewed plan-only commit; before every later commit perform self-review. Run Codex Security and then one correct local OCR review before the final feature push. Formulate and set the goal after execution begins.

### Completed Baseline State

v0.12.0 is the latest stable release. The six target issues are open and no v0.12.1 milestone exists. The site-launch plan is separately archived and current main has no active plan. Local checkout was clean when this branch was created.

### Current Work Queue

| Queue | Requirements | Exit evidence | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-008 | Review this complete plan, commit only plan/state files, set goal, create milestone and feature PR | done |
| WQ-02 | REQ-001 | Producer registry and production enrichment tests for protected versus structural values | done |
| WQ-03 | REQ-002, REQ-003 | Narrow numeric/reference classifiers, whole-unit controls and ingress/publication tests | done |
| WQ-04 | REQ-004 | Reviewed-source proof before projection and both-sink rendering tests | done |
| WQ-05 | REQ-005, REQ-006 | Installed OCR gitlink qualification, typed preview/stale handoff and protected posting tests | done |
| WQ-06 | REQ-006 | Versioned federation, DLP, result and reporting contracts with exact producer counts | done |
| WQ-07 | REQ-007 | Closed path classifier and required-check-preserving documentation-only workflow branches | done |
| WQ-08 | REQ-008, REQ-012 | Towncrier and current contracts, separate documentation/instruction audit commit, focused and full gates, aggregate changed-range review, staged/history secret scans | in_progress |
| WQ-09 | REQ-008 | Codex Security scan, one local OCR review, finding fixes, final push and checked feature merge | pending |
| WQ-10 | REQ-009 | Verify development build; prepare and merge exact protected release/v0.12.1 PR | pending |
| WQ-11 | REQ-009 | Verify stable CI, registry hashes/provenance/installs, tag, immutable Release, issue receipts/milestone | pending |
| WQ-12 | REQ-010 | Verify real site dispatch, build and live v0.12.1 content | pending |
| WQ-13 | REQ-011 | Protected documentation-only external-reconciliation PR and final archive/marker readback | pending |

### Locked Decisions

Keep the repository release sequence in `docs/release.md`. Use source-bound optional-code DLP rather than global HTML relaxation. Keep conservative diagnostic redaction separate from semantic DLP. Version changed public receipts instead of changing existing field meanings. Treat legacy attribution as unavailable. Use a single correct local OCR command and wait for terminal result; inspect persisted artifacts before any retry after uncertain execution.

### Verification

Run focused production-boundary regression suites per issue, including immutable Git mode-160000 add/update/delete with the installed OCR, stale GitLab-head races, federation schema/argument/result admission, local and GitLab code renderers, DLP mixed positives, omission accounting, old/malformed receipts and approval preservation. Run `scripts/quality.sh check`, package/installed smoke at applicable boundaries, `scripts/gitleaks.sh --staged` before every commit and complete tree/history gates before push. Verify docs-only and code/workflow CI branches preserve the live ruleset's required check names. Perform exact scoped self-review before every commit, an aggregate final review, Codex Security diff scan, then one correct local OCR/toolkit range review before final feature push. Let required PR/release CI and external readback own supported-platform and registry checks.

### Latest Validation Results

- 2026-10-22: First plan-only signed commit `b72b295`, draft feature PR #257, active goal and milestone v0.12.1 with all six issues assigned.
- 2026-10-22: #252 field-aware registration passes production enrichment composition for current/outdated and complete/partial records, with safe prose/code, protected text, omission and operator-secret controls (5 focused tests). Broader quality matrix remains pending.
- 2026-10-22: #248/#251 narrow syntax classifiers pass 85 focused DLP, publication, ingress and federation tests, including mixed PII/secret/forbidden controls. Broader quality matrix remains pending.
- 2026-10-22: Documentation-only classifier and required-check-preserving CI branches pass 18 focused classifier/workflow tests. Workflow changes themselves remain on the full validation path.
- 2026-10-22: #253 source-bound optional-code proof passes 8 helper tests and 6 publication/renderer tests; opaque DLP retains independent mixed secret, PII, HTML-comment, destination and control checks. Broader quality matrix remains pending.
- 2026-10-22: #249 immutable mode-160000 add/update/delete were qualified against installed OCR 1.13.2 and close before model launch with a typed status; #250 versioned pre-execution, federation, publication and posting contracts have focused stage/race/legacy tests. Full pytest completed with 2019 passed, five skipped and one stale CI-matrix assertion, which was corrected and retested; final quality gate remains pending.
- 2026-10-22: Public v0.12.1 contract documentation and Towncrier fragments committed as `cccb7f3`; 49 affected documentation/CI tests passed. Separate read-only audits inventoried documentation and instruction routes: one broken anchor, current receipt-version drift, historical/current M5 ownership, and an unguarded agent-configuration route. The audit commit archives the M5 design and evidence migration records, gives the current governed federation contract a milestone-neutral name, and corrects the other findings. Instruction lint and documentation tests pass; final gates remain pending.
- 2026-10-22: Initial full quality run reached 86.35% coverage with 2019 passing tests, five skips and one stale public-contract assertion after the documentation renames. The assertion and a historically worded strategy sentence were corrected and the affected test passed; rerun of the full gate remains pending.

### Risks And Recovery

- DLP relaxations may admit sensitive content: only narrow proven syntax with independent whole-unit checks is acceptable; otherwise retain rejection and a closed diagnostic.
- OCR gitlink preview can misstate selection: use immutable Git mode proof and fail closed on unknown/multiple/path-injected diagnostics; never silently skip ordinary files.
- Versioned receipts and GitHub lifecycle races can alter publication decisions: test old/unknown/foreign states and recheck exact current identity before any provider mutation.
- A failed local OCR or security run is not a clean result. Preserve bounded owner-only evidence, diagnose the exact cause and do not blindly repeat a side-effectful run.
- Release or site refresh failure leaves the immutable release facts unchanged; recover through the owner workflow and record exact pending external steps rather than claiming completion.

### Resume Point

WQ-08: reconcile public contract documents and Towncrier fragments, run the full quality and secret gates, review the complete changed range, then perform Codex Security and one local OCR review before the final feature push.

### Plan Fidelity Check

- [x] Every requested outcome and constraint maps to a stable requirement and queue item.
- [x] Issue sources, owner contracts, decisions, non-goals, checks, risks and recovery are retained.
- [x] The first safe action and external publication boundary are explicit.

### Reconciliation Check

- [x] Baseline repository and GitHub issue/site-plan state were read immediately before execution.
- [ ] Reconcile implementation, final commit range, exact CI and external receipts as they arrive.

### Closure Gate

- [ ] All requirements and queue items are terminal with evidence for the final delivered commits.
- [ ] Stable artifacts, issue/milestone receipts, site refresh and protected closure PR are independently read back.
- [ ] Release archive and active-plan reset follow `docs/release.md` without prematurely asserting external publication.

### Post-Close Delivery

Report the feature/release/closure PRs, exact v0.12.1 Release and receipt, issue/milestone closure, site URL/version readback, review/security outcomes and any factual limitations.

### Handoff Notes

Use the ordered WQ table and current Resume Point. Do not treat feature merge, development build or release-PR preparation as objective completion; consult current provider state before retrying external writes.

## Recently Completed

- [x] 2026-10-22: Completed Toolkit site launch and release notification; [full archived plan](docs/engineering/execution_history/2026-10-22-toolkit-site-launch-and-release-notification.md).
