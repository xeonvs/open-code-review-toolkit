# Execution Plans

## Active Plan: Toolkit 0.13.1 partial review of changes containing gitlinks

plan_schema_version: 2
Status: done
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
| REQ-001 | Classify full before/after tree shape and immutable review identity; admit only pure gitlink add/update/delete/unambiguous move with no submodule reads or fetches | WQ-02, WQ-06 | done |
| REQ-002 | Qualify OCR 1.13.3 process-local projection against independent ordinary diff, bounded preview and production manifest; fail closed on drift, diagnostics or mismatch | WQ-03, WQ-06 | done |
| REQ-003 | Preserve native result truth; version closed toolkit coverage receipt v12 and pre-execution status v6; preserve v11 history | WQ-04, WQ-06 | done |
| REQ-004 | Report partial/no-supported-work outcomes locally and in GitLab; block unsupported findings, approval and automatic cleanup; retain failure precedence | WQ-04, WQ-05, WQ-06 | done |
| REQ-005 | Prove pure and hostile shapes with checksum-verified OCR 1.13.3/local stub, focused contracts, complete quality, security and installed-artifact checks | WQ-02–WQ-07 | done |
| REQ-006 | Update operator, security, decision-flow, compatibility, GitLab and changelog contracts without a new CLI flag or rules-contract change | WQ-06 | done |
| REQ-007 | Protected feature PR, development artifact readback and prepared v0.13.1 release candidate with exact metadata and archived plan; protected release PR delivery transfers below | WQ-07, WQ-08; Post-Close Delivery | done |
| REQ-008 | After release merge, verify stable registries, provenance, tag, immutable Release/receipt, #268/milestone, site notification and external state | WQ-09; Post-Close Delivery | out_of_scope |
| REQ-009 | Apply bounded tool-use decisions from prior release-chat audits while preserving mandatory gates | WQ-01–WQ-09 | done |
| REQ-010 | Correct current status-bearing v0.13.0 docs from live evidence; keep archived prepublication snapshot intact | WQ-06, WQ-08 | done |
| REQ-011 | Make the review-found boundary gaps a durable, narrowly routed validation control for future changes | WQ-07 | done |
| REQ-012 | Audit recurring OCR `file_read` failures against toolkit input, failure telemetry and review acceptance; correct only a demonstrated toolkit defect | WQ-07 | done |

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
- Feature PR #269 began as a plan-only draft at `db27f37`, then received one final implementation push after security and local ChatGPT/OCR review. Its reviewed head `1770a0c` was squash-merged as `7d65c3f`; the exact trees match. Preserve that checked feature range rather than repeating its scans for release-only metadata edits.

### Inputs And Sources

- Approved user plan and issue #268: https://github.com/xeonvs/open-code-review-toolkit/issues/268.
- Canonical owners: `docs/engineering/project_principles.md`, `docs/development.md`, `docs/release.md`, `docs/review-decision-flow.md`, `docs/operations.md`, `docs/local.md`, `docs/security.md`, and installed engineering-workflow planning reference.
- Runtime owners: `evidence/gitlinks.py`, `review_runner.py`, `review_receipt.py`, `pre_execution.py`, `result_contract.py`, `reporting/`, `posting/`.
- Baseline: clean synchronized `main`, published v0.13.0, `.next-version=0.14.0`, no active plan, #268 only open issue; remaining backlog triggers unmet.
- Pre-implementation proof: official OCR 1.13.3 Darwin arm64 SHA-256 `fa9b8530c0a35e6106a9ab2e81c21d98ef26d3f31c1f39ad3ef4c2528047c4f4`. Five mixed pure-gitlink synthetic forms had clean preview and production manifest `complete`, exactly ordinary selected/completed items, zero failed/reused; gitlink-only preview `files=[]`; both type-transition directions had duplicate same-path entries, one with a warning. This proves measured forms, not the integrated toolkit or all inputs.
- Prior release chats were read as historical process evidence, not authorization. Their command counts span multiple releases; repeated broad searches/unchanged CI reads motivate decision-bound calls without an arbitrary call quota.
- Merged feature PR: https://github.com/xeonvs/open-code-review-toolkit/pull/269, reviewed head `1770a0c`, protected squash merge `7d65c3f` on `main`.

### User Decisions And Answers

Target v0.13.1, keep 0.14.0 development marker; include #268 and required adversarial/contract checks, leave conditional backlog inactive; no-model GitLab post is advisory by default and strict only under existing strict mode; embed tool-use improvements in this execution, not a separate workflow PR; implement through protected feature and stable release lifecycle. Use a plan-only early draft PR, no intermediate feature pushes, broader tests for all touched files, logical signed commits with self-review/amend for fixes, codex-security before the final push and local toolkit/OCR review with ChatGPT after it but still before the push. After review findings, make a prospective cross-stage validation control in the existing canonical development owner, preserving route-only `AGENTS.md` and a non-normative incident catalogue. Audit repeated native `file_read` failures without conflating built-in OCR tools with the toolkit MCP federation.

### Completed Baseline State

v0.13.0 is published with immutable assets and #264 closed. Its archived plan is a historical prepublication snapshot; current roadmap/index wording now reflects live release evidence. OCR 1.13.3 is qualified in `compatibility/ocr-support.json`, while host default `ocr` is 1.13.2. The feasibility probe used a local fake provider and left no repository changes. `codex/gitlink-partial-review-0131` was created from clean synchronized main.

### Current Work Queue

| Queue | Requirements | Exit evidence | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-009 | Full plan/state pointer, reviewed plan-only signed commit, #268 milestone | done |
| WQ-02 | REQ-001, REQ-005 | Private before/after shape and safe `.gitmodules`/Git inventory, adversarial tests, self-reviewed commit | done |
| WQ-03 | REQ-002, REQ-005 | Frozen OCR invocation/environment, independent diff, preview/native-manifest qualification, real-binary regression, self-reviewed commit | done |
| WQ-04 | REQ-003, REQ-004 | Exact receipt v12/status v6, effective coverage/reporting and local no-model path, hostile/legacy tests, self-reviewed commit | done |
| WQ-05 | REQ-004 | GitLab posting, finding admission, approval blocker and partial lifecycle retention with failure/freshness tests, self-reviewed commit | done |
| WQ-06 | REQ-005, REQ-006, REQ-010 | Synthetic/installed OCR matrix, public contracts, threat model, decision flow, examples, Feature fragment, factual status correction, self-reviewed commit | done |
| WQ-07 | REQ-005, REQ-007, REQ-011, REQ-012 | Scoped/final quality, boundary-validation process correction, native failed-tool audit, build, secret/dependency gates, security diff scan, real local OCR review, aggregate self-review, protected feature PR/merge, dev artifacts | done |
| WQ-08 | REQ-007, REQ-010 | Release markers/metadata/epoch/notes, checked plan archive/reset and release candidate ready for signed commit; protected PR delivery follows below | done |
| WQ-09 | REQ-008 | Protected release PR/merge, stable publication, receipt and external reconciliation; required Post-Close Delivery | out_of_scope |

### Locked Decisions

Only proven OCR 1.13.3 pure-pointer projection proceeds. Unique identical-OID before/after pairs may count as moves; ambiguity stops. Keep OCR selection native and validate observable output. Gitlink-only or no selected ordinary work stops before model. Native `complete` on projected selection remains native complete; toolkit repository coverage is partial. Any changed unsupported gitlink blocks approval regardless of OCR result or project exclusions. Partial publication retains prior finding threads. Receipt v12/status v6 are closed; historical schemas retain their original meaning.

### Verification

- Tree/`.gitmodules`/config: add/update/delete/unique move/multiple/unchanged, absent target objects/worktrees, sparse/shallow sufficient/insufficient evidence, file/executable/symlink/directory transitions, collisions, malformed mappings/includes/hostile names, limits and drift.
- Preview: independent unfiltered/projected diff identity, `.gitmodules ignore=none`, conflicting inherited config, ordinary rename/deletion, generated/ignored/excluded/binary/large cases, malformed/oversized/duplicate preview, diagnostics and zero selected ordinary work.
- Result/publication: native complete plus effective partial; failed/partial/budget/DLP precedence; wrong refs/manifest/reuse; stale/cross-job receipt; old v11; omitted-path findings; reports/approval/thread retention; failed writes and later complete reconciliation.
- Installed checksum-verified OCR 1.13.3 with deterministic local fake provider must reproduce original refs and ordinary selected/completed manifest for proven forms, without paid model or forge writes.
- Focused suites per change; Ruff format check and staged Gitleaks before commits; final `scripts/quality.sh check`, installed wheel/sdist boundary, tree/history Gitleaks/dependency audit before push, security diff scan, one correctly invoked local OCR review and protected PR/release gates. Rerun affected checks when inputs change or evidence is incomplete.

### Latest Validation Results

2026-10-23 pre-implementation OCR 1.13.3 probe passed for mixed update/add/delete/move/multiple pure gitlinks and demonstrated no-model gitlink-only preview plus unsafe type transitions. Digest matches the pinned manifest. The signed plan-only commit is `db27f37`; plan-lifecycle and instruction-contract checks and staged Gitleaks passed. Milestone v0.13.1 (#22) tracks #268. Draft feature PR #269 has only the plan commit at its remote head. Local WQ-02 commit `203a50e`, WQ-03 commit `827fc3b`, and WQ-04/05 commit `7f17a3f` are not pushed. WQ-03 has bounded unfiltered/projected Git inventory, original patch fingerprints and line counts, one frozen OCR child environment, exact preview and native manifest/source-artifact comparison, and before/after drift checks. WQ-04/05 add closed v12 effective coverage and v6 no-model status while preserving v11/v5, local/GitLab partial notices, independent post readback of original trees and native selected work, an approval blocker, and prior finding-thread retention. The checksum-verified OCR 1.13.3 and local fake provider passed add/update/delete/mixed ordinary rename/add/delete/gitlink move forms. The integrated local toolkit test also passed an ordinary-plus-gitlink review through the real OCR binary and mandatory evidence MCP, and a gitlink-only no-model case; its loopback fake-provider HTTP allowance exists only inside the test process, with product HTTPS validation intact. Focused runner/gitlink/coverage suite passed 269 tests before this integrated addition; focused GitLab posting suite passed 364 tests and 299 subtests. Towncrier rendered the 0.13.1 Feature draft and plan lifecycle check passed. The first full quality run reached 86.25% coverage but found 10 stale documentation/v5/v11 test expectations; corrected targeted contracts passed 98/98. The corrected-tree full `scripts/quality.sh check` then passed. The checksum-verified installed OCR matrix passed 49/49 including integrated toolkit proof. Final build, secret/dependency and review gates remain pending.

The first local ChatGPT OCR review of `bdf5832..4183c1d` completed with a native complete manifest (14 selected/completed, no reuse/failure/waiver), DLP admission, and six actionable findings. This is correction evidence, not an approval of the range. The local follow-up fixes preserve a path-free selected-work proof when publication DLP removes unsafe findings, reject unhashable v12/v6 fields, remove or privately mark raw output on post-model drift, and bound Git patch output during execution. Focused runner/gitlink/coverage/status tests passed 296 with 10 environment-gated skips; the installed OCR gitlink suite passed 52/52. These edits change the reviewed range, so final quality, security diff scan and local OCR review must be repeated before push.

The signed correction commit `9f5de34` passed full quality (2369 tests, 12 skipped, 357 subtests, 86.35% total coverage), installed wheel/sdist MCP execution, real OCR gitlink tests, Gitleaks and dependency audit. Codex Security diff scan of `bdf5832..9f5de34` sealed with zero findings and no deferred files. The second local ChatGPT OCR review completed with native complete coverage (14 selected/completed, zero reuse/failure/waiver), 8 internal evidence-MCP calls and two actionable findings: post-model input read/timeouts missed result disposal, and user Git attributes could differ between temporary review HOME and normal posting HOME. The local correction now catches all three verification failure classes before/after execution, disables user attributes in the projected Git child and tests a changed HOME with hostile attributes; 63/63 real-OCR gitlink tests passed. The external governed federation was not part of this local review. No feature implementation has been pushed after the plan-only draft PR.

Native OCR generated four invalid `file_read` requests in the first model review and one in the second (bad path or out-of-range lines). Toolkit code does not construct those requests. Its existing bounded failure telemetry records them privately, strips arguments/details from published results and blocks automatic approval for verified failures; focused telemetry tests passed 10/10. The missing operational control was accepting a local complete manifest without assessing material auxiliary read failures. The local review route now requires that assessment. A proposed bootstrap instruction was rejected: the clean installed wheel/sdist test showed that it displaced higher-priority project guidance under the existing 2,300-character cap. The canonical development validation owner now calls for a small changed-handoff map and integrated mixed/error fixtures; existing incident classes cover the observed causes. Instruction-contract validation passed. The initial quality run on the oversized-bootstrap commit failed only the installed-artifact test (2375 passed, 12 skipped, 357 subtests, 86.35% coverage); the bootstrap addition was removed before final validation.

The signed `f65d519` correction passed full quality, installed wheel/sdist execution, real OCR gitlink tests, secret and dependency gates. Codex Security completed `bdf5832..f65d519` with zero findings. A third local ChatGPT OCR run completed natively with 14/14 selected files and six internal evidence-MCP calls; its JSON identified two valid Git input gaps: a BOM-prefixed local config include and direct `config.worktree`. The local Markdown delivery failed because the operator supplied a symlinked `/tmp` report parent, repeating the v0.12.1 mistake despite the documented physical-path example. The current correction pins and rejects those Git inputs, and rejects unsafe local report parents before model execution while rechecking at publication. New tests cover real Git parsing, input drift, pre-model rejection, and the host's actual `/tmp` alias state. The checksum-verified real OCR suite passed 65/65; local artifact tests passed 20/20; full quality passed 2380 tests with 12 environment-gated skips, 357 subtests and 86.35% total coverage. This third review is finding evidence, not an accepted final review; a corrected physical-path local review remains required.

Final signed feature head `1770a0c` passed the aggregate self-review and all ten protected PR checks, plus macOS Python 3.12/3.14 diagnostics. Codex Security completed the correction delta `f65d519..1770a0c` with zero findings; the earlier base..`f65d519` scan also had zero findings. The final local toolkit/OCR ChatGPT review of the correction delta used a physical private output path and exited successfully: native complete, 2/2 selected and completed, zero failed/reused/waived, DLP admitted, two internal evidence-MCP calls, no material tool failures or findings. All eight feature commits were signed. Protected PR #269 merged as `7d65c3f` on 2026-10-23 with exact tree equality to `1770a0c`. Main-bound TestPyPI run `40027515567` completed all build, publication, provenance and installed-artifact verification jobs for `0.14.0.dev124`; independent TestPyPI readback found exactly wheel SHA-256 `221e27a53622ffaa8a5a05806e03cf374eeaa1bdd4546a05eb5a1ce40da5551b` and sdist SHA-256 `2792261d955512373b2a54c1451364ab69033bbadcd3654c21eabe255ae7eeb0`.

The release candidate uses feature merge commit time `1792791144` as its deterministic source epoch, authorizes only issue `[268]`, retains `.next-version=0.14.0`, advances the stable marker and GitLab example/default table to 0.13.1, and renders the Towncrier Feature section. The focused release/documentation suite passed 74 tests; its sole remaining case requires the plan archive that the checked lifecycle creates. The release index now points to the exact planned archive path. After the lifecycle transition, rerun that case and the scoped suite on the final candidate before the signed commit; protected PR CI remains a required external gate. This is a prepublication handoff, not a claim of stable artifacts or issue closure.

### Risks And Recovery

Git configuration precedence or local input drift can hide ordinary changes: revalidate consulted inputs and independent diff; stop on uncertainty. False-complete receipt could launder approval/cleanup: exact parsing, original identity binding, independent approval blocker and thread retention. If installed proof fails for a proposed safe form, narrow it and test the fallback; if core mixed behavior cannot be proved, keep the plan active/blocked and do not publish. External publication failures resume only through exact-artifact documented recovery after readback.

### Resume Point

No unfinished in-scope repository work remains. The checked lifecycle archives this prepared candidate now; the focused test that requires the archive, final diff and secret/dependency gates, signed commit, protected release PR and external delivery are explicitly required in Post-Close Delivery.

### Plan Fidelity Check

- [x] User outcomes, issue acceptance, version and release lifecycle map to REQ and ordered WQ items.
- [x] Non-goals preserve conditional backlog and prevent unqualified/upstream expansion.
- [x] Feasibility results are distinguished from pending integrated qualification; each acceptance family has a verification owner.
- [x] Constraints, failure precedence, external owner, recovery and exact first safe action are recorded.
- [x] Decisions on version, bundle, advisory status and process optimization are retained.

### Reconciliation Check

- [x] Clean baseline, published v0.13.0, open #268 and OCR pin were checked before activation.
- [x] Reconciled reviewed feature tree, hosted checks, merge, development artifacts and release candidate metadata; protected release PR facts remain post-close delivery.

### Closure Gate

- [x] All in-scope repository requirements and queue items are terminal with available validation evidence; the archive-dependent focused check and external delivery are classified below.
- [x] No current issue, document, backlog, PR or release candidate state contradicts the prepared prepublication result.
- [x] The checked lifecycle archives the full plan and resets active state in the release PR; unverified external facts remain outside this archive.

### Post-Close Delivery

Required outside the closed repository plan: rerun the archive-dependent focused test and release-documentation suite, inspect the final candidate and run applicable secret/dependency/release checks, then sign, push and pass the exact protected `Release v0.13.1` PR before squash merge. Verify stable TestPyPI/PyPI distributions, provenance, attestations, annotated tag, immutable Release and v2 receipt; close #268/milestone only after receipt readback; confirm site notification/live state; independently compare external facts with receipt and Actions-owned issue comments. No extra repository closure PR.

### Handoff Notes

The candidate is based on protected main `7d65c3f`; feature PR #269 and development artifact verification are complete. No in-scope repository work remains. The archive is a historical prepublication handoff; immutable external receipts and Actions-owned issue comments own later proof. Private probe/model logs remain outside commits and issues.

## Recently Completed

- [x] 2026-10-23: Completed Toolkit 0.13.0 protected default-policy fallback for single-MR review; [full archived plan](2026-10-23-toolkit-0-13-0-protected-default-policy-fallback-for-single-mr-review.md).
