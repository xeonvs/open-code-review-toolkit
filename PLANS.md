# Execution Plans

## Active Plan: Toolkit 0.15.2 — CI outcome DLP, OCR qualification, Analysis and local telemetry

plan_schema_version: 2
Status: active
Release classification: release-required
Target release: 0.15.2
Next development marker: 0.16.0
Last Updated: 2026-11-25

### Goal

Deliver issue #324, qualify the eight stable OCR releases through 1.14.4, expose opt-in Behavior/Impact Analysis and deliver private bilingual offline reports for GitLab MR telemetry.

### Plan Origin

plan_mode_approved

### Requested Scope

Repair CI policy selector registration, qualify future stable versions by consumed behavior, integrate local GitLab collection and reporting, update the operator documentation, and pause at the draft feature PR.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Public CI policy selectors no longer filter findings or private results | WQ-01 | done |
| REQ-002 | Behavioral qualification, candidate disposition, safe batching and promotion | WQ-02 | done |
| REQ-003 | Private opt-in Analysis and accurate operator documentation | WQ-03 | done |
| REQ-004 | Hosted qualification, installed regressions, review and mandatory draft pause | WQ-04 | done |
| REQ-005 | Protected delivery and immutable receipt readback | WQ-05 | pending |
| REQ-006 | Private GitLab collection, current and historical toolkit publication contracts, offline English and Russian reports | WQ-06 | done |

### Explicit Non-Goals

Published historical evidence remains immutable. No automatic promotion of a new minor line.

### Constraints

The user requires a stop at the draft feature PR. For the telemetry update, review the committed feature range locally with the installed toolkit before push. Verify an admitted model-generated diagram and include that Mermaid in draft #331. Resume later release steps only on explicit instruction. Ordinary operator guidance references the versioned manifest or example. Keep concrete versions where they identify a migration, artifact or release-specific behavior.

### Inputs And Sources

Toolkit issues #324–330, upstream releases 1.13.11 through 1.14.4, compatibility run 45148738452, repository development and release contracts.

### User Decisions And Answers

Runtime support moves to the qualified patches of the new line. Integrate optional Analysis now. Target the requested 0.15 patch line.

### Completed Baseline State

Toolkit 0.15.1 is released with OCR 1.13.10. Hosted evidence exists for all three newer 1.13 patches. All three 1.14 jobs stopped on the first hardcoded rule glob.

### Current Work Queue

1. WQ-01: Fix DLP at its source, verify mixed provenance and review/post output.
2. WQ-02: Replace brittle live expectations, qualify and aggregate all outcomes, validate progression and packaged handoffs.
3. WQ-03: Integrate Analysis execution, admission, privacy and reporting. Update docs and release fragments.
4. WQ-04: Verify branch qualification, promote exact evidence, run applicable checks, inspect combined diff and open draft feature PR. Pause.
5. WQ-05: After explicit resume, merge the protected feature PR, verify the development distribution and prepare the release PR with the archived plan.
6. WQ-06: Extend draft #331 before WQ-05. Characterize report calculations with synthetic inputs, verify current GitLab producer contracts, modularize collection and rendering, and validate installed online/offline boundaries.

### Locked Decisions

Keep credential and integrity errors operational failures. Real incompatibility blocks promotion. Analysis has an independent budget and cannot grant approval.

### Verification

Exercise synthetic GitLab review/post, controlled model, installed wheel and actual GitHub candidates. Run quality, secret and dependency gates. Review each logical commit and the combined change.

### Latest Validation Results

Hosted run 45148738452 produced compatible evidence for 1.13.11–13. Root retrieved those three artifacts before expiry. The CI-selector regression failed on the old code and passed after the source fix, with 239 tests in the surrounding suites. Posting tests cover a current operational partial, budget-only failure, missing receipt, wrong exit and terminal failure. All 305 posting tests and 205 subtests passed. Installed wheel review and post preserved both findings with and without CI records. The private discussion control omitted one finding from publication and attributed the omission to forge discussions alone.

The final hosted run [45200392627](https://github.com/xeonvs/open-code-review-toolkit/actions/runs/45200392627) assessed the full chain at 2247999. Every candidate was compatible. Promotion recorded reviewed conclusions for all six, recommended 1.14.2, and limited runtime admission to 1.14.0–2. The independent verified Darwin 1.14.2 probe passed numeric, Analysis, native-auth, gitlink and diagram checks.

Before telemetry, the draft at `30f375e` passed the full quality gate with 5809 tests, 358 subtests, 80 skipped tests and 90.61% coverage. The instruction contract passed. The dependency audit reported no known vulnerabilities in audited dependencies.

The installed local self-review of `f6126e6..5712b0a` completed all 112 selected files and generated an admitted change diagram. All 88 findings were triaged. Repairs cover GitLab host selection, incremental observation and timestamp accuracy, price availability, artifact paths, Analysis cleanup, partial publication and qualification evidence. The isolated installed CLI collected and updated through paginated GitLab fixtures. Both wheel builds rendered four EN/RU reports offline with an active network tripwire. The live corporate GitLab and private pricing endpoint require operator access.

Local DLP audit replay independently admitted all four public selector units and rejected all four private controls. The installed GitLab review/post scenario verifies the source registration behind #324.

New GitLab notes record the model when the native selection agrees with the run configuration and the value passes DLP. For older notes, the exact visible default-scope project `OCR_LLM_MODEL` can supply a dated estimate. When the setting or prices are unavailable the report retains token coverage. Both installed distribution forms distinguished the run model ($0.336) from a current project default ($0.168) using synthetic prices.

A second own-tool pass reviewed the amended feature against its published parent: 90 of 93 files completed and 55 findings were triaged. A separate exact selection completed the three files affected by provider errors without findings.

At `444ebce` the complete quality gate passed with 6,068 tests, 360 subtests, 80 skips and 90.06% coverage. [Hosted qualification run 45264920134](https://github.com/xeonvs/open-code-review-toolkit/actions/runs/45264920134) rechecked the three supported OCR releases on Linux. All candidates and the chain assessment succeeded. The manifest references their schema-5 receipts and preserves the original evidence files.

The model-specific own-tool review covered five files across its initial pass and two-file provider retry. Review corrections preserve explicit zero usage, reject unsupported estimates, and bind the optional public label to both the receipt and available native model. The scoped threat-model review identified excess GitLab settings reads. Collection now limits the optional request to projects with usable historical usage that actually needs a model. The canonical security guide documents publication visibility, credential destinations, plaintext state and the limits of anonymization.

[The single-tag qualification](https://github.com/xeonvs/open-code-review-toolkit/actions/runs/45652414177) passed all native candidate probes for 1.14.3 against 1.14.2. Aggregation exposed single-artifact extraction directly into the download root. The workflow selects the destination from the actual uploaded candidates, including a single surviving artifact from a partial matrix. The [single-artifact hosted recheck](https://github.com/xeonvs/open-code-review-toolkit/actions/runs/45660885585) passed candidate qualification and final aggregation.

### Risks And Recovery

[Issue #333 qualification](https://github.com/xeonvs/open-code-review-toolkit/actions/runs/46124170477) passed for OCR 1.14.4 against 1.14.3, including chain assessment. Reviewed the C/C++ selection change and promoted the candidate. Bound qualification to v1.14.4. If a candidate fails, inspect its closed phase and disposition before retry. Keep stale or incomplete evidence out of promotion.

### Resume Point

The feature and refreshed hosted receipts are at the draft checkpoint. Wait for the owner's explicit resume instruction before WQ-05. The Codex Security diff scan rejected the branch checkout and its independent clone during startup. Resolve the missing scan before marking ready.

### Plan Fidelity Check

All seven open issues are covered by WQ-01 and WQ-02. The new runtime capability and operator migration are covered by WQ-03.

### Reconciliation Check

Update this plan at each material checkpoint. Verify issue and milestone closure only after release receipt.

### Closure Gate

Archive in the protected release PR. Verify the immutable release and close the delivery objective after external readback.

### Post-Close Delivery

Release CI owns registry and attestation verification and issue closure. After publication, independently read back the release, registry, attestations and issue state against the archived plan. After verified publication, inventory project build and review scratch directories and Docker containers, images and build caches created for this release. Remove disposable release-owned resources, preserve private reports still needed for review and shared Docker resources, then verify the checkout and remaining Docker inventory.

### Handoff Notes

Draft PR creation is the owner's review checkpoint.

## Recently Completed

- [x] 2026-11-16: Completed Toolkit 0.15.1 — evidence diagnostics and rejection cleanup; [full archived plan](docs/engineering/execution_history/plans/2026-11-16-toolkit-0-15-1-evidence-diagnostics-and-rejection-cleanup.md).
- [x] 2026-11-16: Completed Toolkit 0.15.0 — complete evidence, .NET and numeric DLP; [full archived plan](docs/engineering/execution_history/plans/2026-11-16-toolkit-0-15-0-complete-evidence-net-and-numeric-dlp.md).
- [x] 2026-11-12: Completed Toolkit 0.14.8 — OCR 1.13.8, provider HTTP and first integration; [full archived plan](docs/engineering/execution_history/plans/2026-11-12-toolkit-0-14-8-ocr-1-13-8-provider-http-and-first-integration.md).
- [x] 2026-11-10: Completed Toolkit 0.14.7 — OCR 1.13.7, recoverable diagrams and private diagnostics; [full archived plan](docs/engineering/execution_history/plans/2026-11-10-toolkit-0-14-7-ocr-1-13-7-recoverable-diagrams-and-private-diagnostics.md).
- [x] 2026-11-06: Completed Internal engineering cycle corrections; [full archived plan](docs/engineering/execution_history/plans/2026-11-06-internal-engineering-cycle-corrections.md).
- [x] 2026-11-06: Completed Toolkit 0.14.6 — OCR 1.13.6, DLP precision and efficient delivery; [full archived plan](docs/engineering/execution_history/plans/2026-11-06-toolkit-0-14-6-ocr-1-13-6-dlp-precision-and-efficient-delivery.md).
- [x] 2026-11-04: Completed Toolkit 0.14.5 — DLP precision, OCR qualification and maintenance quality; [full archived plan](docs/engineering/execution_history/plans/2026-11-04-toolkit-0-14-5-dlp-precision-ocr-qualification-and-maintenance-quality.md).
- [x] 2026-10-31: Completed Toolkit 0.14.4 systematic DLP corrections and diagram source validation; [full archived plan](docs/engineering/execution_history/plans/2026-10-31-toolkit-0-14-4-systematic-dlp-corrections-and-diagram-source-validation.md).
- [x] 2026-10-30: Completed Toolkit 0.14.3 source-aware DLP and private corpus audits; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-3-source-aware-dlp-and-private-corpus-audits.md).
- [x] 2026-10-30: Completed Toolkit 0.14.2 compact bootstrap, diagram-only reports and DLP corrections; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-2-compact-bootstrap-diagram-only-reports-and-dlp-corrections.md).
