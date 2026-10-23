# Execution Plans

## Active Plan: Toolkit 0.13.1 partial review of changes containing gitlinks

plan_schema_version: 2
Status: active
Owner: root
Last Updated: 2026-10-23
Release classification: #268 `release-required`, target v0.13.1.

### Goal

Deliver #268 as a toolkit-only, explicitly partial and non-approvable review of ordinary changes alongside safely separable gitlinks, then publish and independently reconcile stable v0.13.1. Preserve the original immutable review identities and native OCR result truth; keep `.next-version=0.14.0`.

### Plan Origin

`plan_mode_approved`

### Requested Scope

Implement private input planning, OCR 1.13.3-only process-local Git projection, preview/production qualification, typed effective coverage and no-model statuses, shared local/GitLab reporting, safe posting/lifecycle, synthetic/adversarial and real-binary checks, public contracts and Feature notes. Create a v0.13.1 milestone for #268. Reconcile current v0.13.0 status documents against the published release without rewriting its archived plan. Use a plan-only first commit, self-review each logical change, protected feature/release PRs and external stable readback.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Classify full before/after tree shape and immutable review identity; admit only pure gitlink add/update/delete/unambiguous move with no submodule reads or fetches | WQ-02, WQ-06 | pending |
| REQ-002 | Qualify OCR 1.13.3 process-local projection against independent ordinary diff, bounded preview and production manifest; fail closed on drift, diagnostics or mismatch | WQ-03, WQ-06 | pending |
| REQ-003 | Preserve native result truth; version closed toolkit coverage receipt v12 and pre-execution status v6; preserve v11 history | WQ-04, WQ-06 | pending |
| REQ-004 | Report partial/no-supported-work outcomes locally and in GitLab; block unsupported findings, approval and automatic cleanup; retain failure precedence | WQ-04, WQ-05, WQ-06 | pending |
| REQ-005 | Prove pure and hostile shapes with checksum-verified OCR 1.13.3/local stub, focused contracts, complete quality, security and installed-artifact checks | WQ-02–WQ-07 | pending |
| REQ-006 | Update operator, security, decision-flow, compatibility, GitLab and changelog contracts without a new CLI flag or rules-contract change | WQ-06 | pending |
| REQ-007 | Protected feature PR, development artifact readback and protected v0.13.1 release PR with exact metadata and archived plan | WQ-07, WQ-08 | pending |
| REQ-008 | After release merge, verify stable registries, provenance, tag, immutable Release/receipt, #268/milestone, site notification and external state | WQ-09; Post-Close Delivery | out_of_scope |
| REQ-009 | Apply bounded tool-use decisions from prior release-chat audits while preserving mandatory gates | WQ-01–WQ-09 | pending |
| REQ-010 | Correct current status-bearing v0.13.0 docs from live evidence; keep archived prepublication snapshot intact | WQ-06, WQ-08 | pending |

### Explicit Non-Goals

No OCR fork/upstream change, consumer-CI bypass, submodule initialization/fetch/worktree content review, synthetic sanitized repository, new provider/LLM/public flag, automatic approval or cleanup of unsupported changes, related-MR work, or activation of conditional BL-019/BL-025. Qualification fixtures make no paid model call or forge write. Unproven shapes retain the no-model stop.

### Constraints

- Keep original GitLab H/B/T/P, diff version, job, rules and local immutable from/to identities. Unqualified or stale identity never gains publication or approval authority.
- Build a bounded private plan from full tree mode/OID entries, unfiltered submodule inventory, relevant `.gitmodules` blobs and consulted local Git inputs; reject ambiguity, limits and drift. Keep paths, OIDs, URLs and sensitive digests out of public receipts.
- For the OCR child only, scrub conflicting Git environment, set `diff.ignoreSubmodules=all` and exact `submodule.<name>.ignore=all`, and freeze the same args/env/runtime inputs for preview and production. Do not persist Git config, modify refs or execute hooks, external diff, textconv, credentials or submodule helpers.
- Validate whole bounded preview and ordinary-change identities, not only exit code/stderr/counts. Check native manifest against admitted work and disallow reuse here. Native failure, DLP and write errors outrank partial coverage.
- Version exact receipt/status schemas rather than appending fields to v11/v5. `ocr-ci post` independently validates identity-bound facts. Never alter native OCR coverage to claim repository coverage.
- No OCR-selected ordinary work: `ocr-ci review` returns 2; GitLab `post` publishes advisory status and returns 0, or 1 in existing strict mode. Local output carries the same closed reason without model execution.
- Protected release PR is the final repository mutation; external publication/readback remains required post-close delivery.
- Feature PR #269 is an early draft containing only plan commit `db27f37`; implementation commits remain local until final feature push. Before that push, finish the codex-security diff review and then a local review through this toolkit with the configured ChatGPT provider and qualified OCR. Fix findings and repeat invalidated checks. Increase test coverage in every touched runtime/contract/reporting module.

### Inputs And Sources

- Approved user plan and issue #268: https://github.com/xeonvs/open-code-review-toolkit/issues/268.
- Canonical owners: `docs/engineering/project_principles.md`, `docs/development.md`, `docs/release.md`, `docs/review-decision-flow.md`, `docs/operations.md`, `docs/local.md`, `docs/security.md`, and installed engineering-workflow planning reference.
- Runtime owners: `evidence/gitlinks.py`, `review_runner.py`, `review_receipt.py`, `pre_execution.py`, `result_contract.py`, `reporting/`, `posting/`.
- Baseline: clean synchronized `main`, published v0.13.0, `.next-version=0.14.0`, no active plan, #268 only open issue; remaining backlog triggers unmet.
- Pre-implementation proof: official OCR 1.13.3 Darwin arm64 SHA-256 `fa9b8530c0a35e6106a9ab2e81c21d98ef26d3f31c1f39ad3ef4c2528047c4f4`. Five mixed pure-gitlink synthetic forms had clean preview and production manifest `complete`, exactly ordinary selected/completed items, zero failed/reused; gitlink-only preview `files=[]`; both type-transition directions had duplicate same-path entries, one with a warning. This proves measured forms, not the integrated toolkit or all inputs.
- Prior release chats were read as historical process evidence, not authorization. Their command counts span multiple releases; repeated broad searches/unchanged CI reads motivate decision-bound calls without an arbitrary call quota.
- Draft feature PR: https://github.com/xeonvs/open-code-review-toolkit/pull/269 at plan-only head `db27f37`. The user's later workflow clarification governs the final feature push and review order.

### User Decisions And Answers

Target v0.13.1, keep 0.14.0 development marker; include #268 and required adversarial/contract checks, leave conditional backlog inactive; no-model GitLab post is advisory by default and strict only under existing strict mode; embed tool-use improvements in this execution, not a separate workflow PR; implement through protected feature and stable release lifecycle. Use a plan-only early draft PR, no intermediate feature pushes, broader tests for all touched files, logical signed commits with self-review/amend for fixes, codex-security before the final push and local toolkit/OCR review with ChatGPT after it but still before the push.

### Completed Baseline State

v0.13.0 is published with immutable assets and #264 closed. Its archived plan is a historical prepublication snapshot; current roadmap/index wording may need factual correction. OCR 1.13.3 is qualified in `compatibility/ocr-support.json`, while host default `ocr` is 1.13.2. The feasibility probe used a local fake provider and left no repository changes. `codex/gitlink-partial-review-0131` was created from clean synchronized main.

### Current Work Queue

| Queue | Requirements | Exit evidence | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-009 | Full plan/state pointer, reviewed plan-only signed commit, #268 milestone | done |
| WQ-02 | REQ-001, REQ-005 | Private before/after shape and safe `.gitmodules`/Git inventory, adversarial tests, self-reviewed commit | done |
| WQ-03 | REQ-002, REQ-005 | Frozen OCR invocation/environment, independent diff, preview/native-manifest qualification, real-binary regression, self-reviewed commit | done |
| WQ-04 | REQ-003, REQ-004 | Exact receipt v12/status v6, effective coverage/reporting and local no-model path, hostile/legacy tests, self-reviewed commit | done |
| WQ-05 | REQ-004 | GitLab posting, finding admission, approval blocker and partial lifecycle retention with failure/freshness tests, self-reviewed commit | done |
| WQ-06 | REQ-005, REQ-006, REQ-010 | Synthetic/installed OCR matrix, public contracts, threat model, decision flow, examples, Feature fragment, factual status correction, self-reviewed commit | pending |
| WQ-07 | REQ-005, REQ-007 | Scoped/final quality, build, secret/dependency gates, security diff scan, real local OCR review, aggregate self-review, protected feature PR/merge, dev artifacts | pending |
| WQ-08 | REQ-007, REQ-010 | Release markers/metadata/epoch/notes, checked plan archive/reset, release validation, protected signed release PR | pending |
| WQ-09 | REQ-008 | Protected release merge, stable publication, receipt and external reconciliation | out_of_scope |

### Locked Decisions

Only proven OCR 1.13.3 pure-pointer projection proceeds. Unique identical-OID before/after pairs may count as moves; ambiguity stops. Keep OCR selection native and validate observable output. Gitlink-only or no selected ordinary work stops before model. Native `complete` on projected selection remains native complete; toolkit repository coverage is partial. Any changed unsupported gitlink blocks approval regardless of OCR result or project exclusions. Partial publication retains prior finding threads. Receipt v12/status v6 are closed; historical schemas retain their original meaning.

### Verification

- Tree/`.gitmodules`/config: add/update/delete/unique move/multiple/unchanged, absent target objects/worktrees, sparse/shallow sufficient/insufficient evidence, file/executable/symlink/directory transitions, collisions, malformed mappings/includes/hostile names, limits and drift.
- Preview: independent unfiltered/projected diff identity, `.gitmodules ignore=none`, conflicting inherited config, ordinary rename/deletion, generated/ignored/excluded/binary/large cases, malformed/oversized/duplicate preview, diagnostics and zero selected ordinary work.
- Result/publication: native complete plus effective partial; failed/partial/budget/DLP precedence; wrong refs/manifest/reuse; stale/cross-job receipt; old v11; omitted-path findings; reports/approval/thread retention; failed writes and later complete reconciliation.
- Installed checksum-verified OCR 1.13.3 with deterministic local fake provider must reproduce original refs and ordinary selected/completed manifest for proven forms, without paid model or forge writes.
- Focused suites per change; Ruff format check and staged Gitleaks before commits; final `scripts/quality.sh check`, installed wheel/sdist boundary, tree/history Gitleaks/dependency audit before push, security diff scan, one correctly invoked local OCR review and protected PR/release gates. Rerun affected checks when inputs change or evidence is incomplete.

### Latest Validation Results

2026-10-23 pre-implementation OCR 1.13.3 probe passed for mixed update/add/delete/move/multiple pure gitlinks and demonstrated no-model gitlink-only preview plus unsafe type transitions. Digest matches the pinned manifest. The signed plan-only commit is `db27f37`; plan-lifecycle and instruction-contract checks and staged Gitleaks passed. Milestone v0.13.1 (#22) tracks #268. Draft feature PR #269 has only the plan commit at its remote head. Local WQ-02 commit `203a50e` and WQ-03 commit `827fc3b` are not pushed. WQ-03 has bounded unfiltered/projected Git inventory, original patch fingerprints and line counts, one frozen OCR child environment, exact preview and native manifest/source-artifact comparison, and before/after drift checks. WQ-04/05 add closed v12 effective coverage and v6 no-model status while preserving v11/v5, local/GitLab partial notices, independent post readback of original trees and native selected work, an approval blocker, and prior finding-thread retention. The checksum-verified OCR 1.13.3 and local fake provider passed add/update/delete/mixed ordinary rename/add/delete/gitlink move forms. Current focused runner/gitlink/coverage suite passed 269 tests; focused GitLab posting suite passed 364 tests and 299 subtests. Ruff, formatter and mypy passed. Toolkit-wide integrated production validation and final gates remain pending.

### Risks And Recovery

Git configuration precedence or local input drift can hide ordinary changes: revalidate consulted inputs and independent diff; stop on uncertainty. False-complete receipt could launder approval/cleanup: exact parsing, original identity binding, independent approval blocker and thread retention. If installed proof fails for a proposed safe form, narrow it and test the fallback; if core mixed behavior cannot be proved, keep the plan active/blocked and do not publish. External publication failures resume only through exact-artifact documented recovery after readback.

### Resume Point

WQ-06: extend the installed-toolkit matrix and hostile shape checks, update operator/security/decision-flow/example contracts, add the Feature fragment, and reconcile status-bearing v0.13.0 documents. Preserve the draft feature PR's plan-only remote head until the final security and local OCR reviews.

### Plan Fidelity Check

- [x] User outcomes, issue acceptance, version and release lifecycle map to REQ and ordered WQ items.
- [x] Non-goals preserve conditional backlog and prevent unqualified/upstream expansion.
- [x] Feasibility results are distinguished from pending integrated qualification; each acceptance family has a verification owner.
- [x] Constraints, failure precedence, external owner, recovery and exact first safe action are recorded.
- [x] Decisions on version, bundle, advisory status and process optimization are retained.

### Reconciliation Check

- [x] Clean baseline, published v0.13.0, open #268 and OCR pin were checked before activation.
- [ ] Reconcile changed implementation, test, PR and release facts before dependent transitions and archive.

### Closure Gate

- [ ] All in-scope repository requirements and queue items are terminal with validation evidence; external delivery is classified below.
- [ ] No current issue, document, backlog, PR or release candidate state contradicts the result.
- [ ] Checked lifecycle archives the full plan and resets active state in the release PR.

### Post-Close Delivery

Required after repository-plan closure: merge exact protected release PR; verify stable TestPyPI/PyPI distributions, provenance, attestations, annotated tag, immutable Release and v2 receipt; close #268/milestone only after receipt readback; confirm site notification/live state; independently compare external facts with receipt and Actions-owned issue comments. No extra repository closure PR.

### Handoff Notes

Active on `codex/gitlink-partial-review-0131`; first commit contains only this plan and its active-plan pointer. Keep private probe/model logs out of commits/issues. Before each tool call identify the decision and preserve status/errors; batch only known independent reads/checks, and use completion-driven waits for long tests and CI.

## Recently Completed

- [x] 2026-10-23: Completed Toolkit 0.13.0 protected default-policy fallback for single-MR review; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-0-protected-default-policy-fallback-for-single-mr-review.md).
