# Execution Plans

## Active Plan: Toolkit 0.15.1 — evidence diagnostics and rejection cleanup

plan_schema_version: 2
Status: active
Release classification: release-required
Target release: 0.15.1
Next development marker: 0.16.0
Last Updated: 2026-11-16

### Goal

Publish and independently verify v0.15.1: diagnose issue #321 without guessing
whether telemetry was absent, preserve rejection cleanup when stderr fails,
and qualify the changed real OCR consumer boundary on Darwin and Linux.

### Plan Origin

plan_mode_approved

This complete approved plan is the first repository write.

### Requested Scope

Implement the approved evidence-diagnostic and cleanup hotfix, its regression
and real-binary tests, public diagnostic contracts and RCA. Check new stable
OCR releases before freezing composition and integrate qualified candidates.
Carry delivery through protected feature/release PRs and immutable receipt readback.
The owner requests an efficient release rather than repeating the 0.15.0 cycle.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Full plan, bounded scope and current release inventory | WQ-01 | done |
| REQ-002 | Distinct missing, malformed and unconfirmed evidence diagnostics | WQ-02 | done |
| REQ-003 | Closed early facts, actual exit code and independent summary counters | WQ-02 | done |
| REQ-004 | Cleanup and original rejection survive failed diagnostic output | WQ-02 | done |
| REQ-005 | Accurate RCA, operations/decision flow and bugfix notes | WQ-02 | done |
| REQ-006 | Synthetic, real subprocess, Darwin/Linux and installed acceptance | WQ-03 | done |
| REQ-007 | Integrate any newly released and qualified stable OCR chain | WQ-01, WQ-03 | done |
| REQ-008 | Final semantic/security/own-tool review and quality gates | WQ-03 | done |
| REQ-009 | Protected feature merge and development TestPyPI readback | WQ-04 | in_progress |
| REQ-010 | Release markers, notes, contracts and checked plan archival | WQ-05 | pending |
| REQ-011 | Stable registries, provenance, immutable receipt and issue/main readback | WQ-06 | pending |

### Explicit Non-Goals

No weakened evidence/approval admission, synthetic preflight attribution,
automatic model retries, new public CLI/configuration/receipt schema, raw CI
debug retention, speculative prompt changes, unrelated dependency upgrades,
historical evidence rewriting or post-publication closure PR.

### Constraints

- Python 3.12–3.15 and existing privacy, signing, coverage and protected checks apply.
- Root owns plan/release state. Ordinary CLI commands run directly.
- Use existing controlled peers; keep private diagnostics and credentials untracked.
- Semantic self-review, formatter and staged secret scan precede each commit.
- Freeze composition before expensive reviews; reuse successful unchanged checks.
- Publication is authorized by the release request; delivery is not complete at merge.

### Inputs And Sources

- Approved conversation plan and explicit implementation/release authorization.
- https://github.com/xeonvs/open-code-review-toolkit/issues/321
- AGENTS.md; development, release, local-review and project-principle owners.
- Installed engineering-workflow planning/lifecycle reference.
- review_runner finalization, review_rejection tests, evidence action receipts.
- Official OCR v1.13.10 output writer and checksum-verified controlled runs.

### User Decisions And Answers

- Release 0.15.*; selected next patch 0.15.1 after immutable 0.15.0.
- Release with the proven RCA and an explicit unknown for the lost CI evidence;
  do not wait indefinitely for an unavailable original JSON.
- Implement the refined plan; keep the release cycle proportionate and efficient.
- Include useful closed cause details in failure logs; never raw diagnostic text.

### Completed Baseline State

Clean main dc81f717e96c795da7fbf8f8e23a8e4ab321fab9, immutable v0.15.0.
No open PRs; OCR recommendation/installed official Darwin asset is 1.13.10.
The same 408/408 rejection log is reproduced for missing telemetry and valid
213 native-only calls. Original CI telemetry absence is therefore unproven.
Official Darwin clean results retain tool_calls with positive or zero calls.
The stderr-failure probe leaves raw JSON and replaces ReviewRejected with OSError.
The initial 24 rejection tests and three focused counterexample tests pass.
Linux Docker is available; no tracked changes preceded this plan.

### Current Work Queue

| Item | Work | Requirements | Status |
| --- | --- | --- | --- |
| WQ-01 | Materialize/fidelity-check plan; freeze release/OCR/PR inventory | REQ-001, REQ-007 | done |
| WQ-02 | Implement diagnostic/cleanup owners, regressions, docs and RCA; self-review | REQ-002, REQ-003, REQ-004, REQ-005 | done |
| WQ-03 | Real consumers/installed gates, final quality, Security and own-tool acceptance | REQ-006, REQ-007, REQ-008 | done |
| WQ-04 | Signed feature PR, required checks, protected merge and development publication | REQ-009 | in_progress |
| WQ-05 | Release PR, final contracts and checked plan archival with delivery pending | REQ-010 | pending |
| WQ-06 | Stable publication and independent external readback/cleanup | REQ-011 | pending |

### Locked Decisions

- A missing primary by_tool key means zero reported primary calls when aggregate
  telemetry is valid; it does not prove whether the model or OCR caused omission.
- Missing tool_calls for evidence-required work uses unexpected-result-contract /
  missing-tool-calls. Existing failed/skipped and malformed-telemetry rules remain.
- Collect bounded known-key/status/manifest facts inside the atomic transformer
  before range/telemetry validation; retain primary error precedence.
- Only validated total/primary/summary counters enter diagnostics. Unknown keys
  become a count, unavailable action receipts never become zero or authority.
- Cleanup executes despite diagnostic sink failure and preserves the original error.
- No new stable OCR means retain 1.13.10; no unbounded or unreleased-main promotion.

### Verification

- Missing/null/malformed/zero/native-only/context/search-only and positive-summary
  cases across legacy/native outcomes; include the exact 408/408 counterexample.
- Hostile root keys/status/values and early manifest failures disclose only closed facts.
- Real child exit code reaches finalization; stderr OSError/BrokenPipeError/closed
  stream cannot retain unadmitted output, admit a report, publish or approve.
- Existing controlled native peers exercise no-findings, zero/native/evidence calls,
  default/agent audience and grouped work on verified Darwin/Linux binaries.
- Scoped tests, full scripts/quality.sh check once, format/lint/types, secret and
  dependency gates; installed wheel/sdist checks at their existing CI owners.
- One aggregate Security diff scan, then real own-tool review with budget 0 and
  admitted model diagram; investigate material warnings, reads and raw filtered findings.
- Protected CI, development publishing, final release contracts and immutable receipt.

### Latest Validation Results

Runtime commit 53537b0 passes the complete quality gate: 5780 tests, 80 opt-in
skips, 357 subtests and 91% rounded branch-aware coverage; every group floor passes.
Six checksum-verified native scenarios pass on both Darwin and Linux/Python 3.12
across five actual groups, default/agent audience and zero/native/evidence activity.
The first two-file fixture was correctly bundled and enlarged to test groups.
Dependency audit and staged/tree/history secret scans pass. Installed wheel/sdist
consumers are covered by the full gate and remain independently owned by PR CI.

Security scan cc451728-4630-46d6-b43d-df25218fafef sealed dc81f71..53537b0 with
complete coverage of all three changed runtime files and no findings. Real native
ChatGPT own-tool acceptance on that same exact range completed 8/8 selected files,
zero findings/warnings/failed tools, confirmed mandatory summary, passed DLP and
an admitted model-generated diagram. Three test paths are native-selection exclusions
and receive direct semantic review and automated tests. Two unchanged large uv.lock
source omissions are non-material: no dependency inputs changed and the audit passes.
The advisory 2259-character background was accepted by OCR. No filtered raw findings.
Stable upstream remains 1.13.10; no open dependency PRs. Composition is frozen.

### Risks And Recovery

The original CI artifact is unavailable: report uncertainty rather than inventing
an upstream or model cause. Independent action counts diagnose but cannot override
OCR telemetry. Linux tests need the Docker socket/network boundary. Gate failures
block their dependent action; fix narrowly and repeat affected checks only.
Recover interrupted external operations by reading their exact provider identity
before retrying. Never rewrite a published tag, artifact or immutable release.

### Resume Point

WQ-04: push the signed feature head, open the protected PR with the exact admitted
diagram, wait for required checks, merge and verify development TestPyPI. All
runtime acceptance is complete; later bookkeeping changes need scoped guards only.

### Plan Fidelity Check

- [x] Full approved outcomes, constraints and user decisions retained.
- [x] Every requirement maps to an ordered queue item and verification.
- [x] Non-goals preserve the requested release and investigation outcome.
- [x] Inputs, recovery, exact resume point and external delivery are explicit.

### Reconciliation Check

- [x] Baseline Git, issue and historical behavior inspected during planning.
- [x] No backlog activation or workflow migration is required.
- [ ] Final implementation, documentation, queue and evidence agree.

### Closure Gate

- [ ] All repository requirements and checks complete on the final reviewed tree.
- [ ] Protected feature merge and development delivery verified.
- [ ] Release candidate archives the full plan through the checked lifecycle.
- [ ] Unverified publication is retained as required Post-Close Delivery.

### Post-Close Delivery

Stable v0.15.1 publication, registry/provenance/install/tag/immutable-receipt
readback, Actions-owned issue/milestone closure, synchronized main and task-owned
cleanup are required and pending. In the release PR, move only this external
delivery outside the closed repository plan; do not assert it happened early.

### Handoff Notes

Keep one release objective through external reconciliation. Do not infer missing
tool_calls from the old unavailable wording. Do not publish private debug,
copied project source, operator paths or model credentials.

## Recently Completed

- [x] 2026-11-16: Completed Toolkit 0.15.0 — complete evidence, .NET and numeric DLP; [full archived plan](docs/engineering/execution_history/plans/2026-11-16-toolkit-0-15-0-complete-evidence-net-and-numeric-dlp.md).
- [x] 2026-11-12: Completed Toolkit 0.14.8 — OCR 1.13.8, provider HTTP and first integration; [full archived plan](docs/engineering/execution_history/plans/2026-11-12-toolkit-0-14-8-ocr-1-13-8-provider-http-and-first-integration.md).
- [x] 2026-11-10: Completed Toolkit 0.14.7 — OCR 1.13.7, recoverable diagrams and private diagnostics; [full archived plan](docs/engineering/execution_history/plans/2026-11-10-toolkit-0-14-7-ocr-1-13-7-recoverable-diagrams-and-private-diagnostics.md).
- [x] 2026-11-06: Completed Internal engineering cycle corrections; [full archived plan](docs/engineering/execution_history/plans/2026-11-06-internal-engineering-cycle-corrections.md).
- [x] 2026-11-06: Completed Toolkit 0.14.6 — OCR 1.13.6, DLP precision and efficient delivery; [full archived plan](docs/engineering/execution_history/plans/2026-11-06-toolkit-0-14-6-ocr-1-13-6-dlp-precision-and-efficient-delivery.md).
- [x] 2026-11-04: Completed Toolkit 0.14.5 — DLP precision, OCR qualification and maintenance quality; [full archived plan](docs/engineering/execution_history/plans/2026-11-04-toolkit-0-14-5-dlp-precision-ocr-qualification-and-maintenance-quality.md).
- [x] 2026-10-31: Completed Toolkit 0.14.4 systematic DLP corrections and diagram source validation; [full archived plan](docs/engineering/execution_history/plans/2026-10-31-toolkit-0-14-4-systematic-dlp-corrections-and-diagram-source-validation.md).
- [x] 2026-10-30: Completed Toolkit 0.14.3 source-aware DLP and private corpus audits; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-3-source-aware-dlp-and-private-corpus-audits.md).
- [x] 2026-10-30: Completed Toolkit 0.14.2 compact bootstrap, diagram-only reports and DLP corrections; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-2-compact-bootstrap-diagram-only-reports-and-dlp-corrections.md).
- [x] 2026-10-29: Completed Toolkit 0.14.1 grouped diagrams and private debug qualification; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-1-grouped-diagrams-and-private-debug-qualification.md).
