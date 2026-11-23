# Execution Plans

## Active Plan: Toolkit 0.15.2 — CI outcome DLP, forward OCR qualification and Analysis

plan_schema_version: 2
Status: active
Release classification: release-required
Target release: 0.15.2
Next development marker: 0.16.0
Last Updated: 2026-11-23

### Goal

Deliver issue #324 and qualify the six stable OCR releases through 1.14.2, exposing Behavior/Impact Analysis as an explicit toolkit option.

### Plan Origin

plan_mode_approved

### Requested Scope

Repair CI policy selector registration, qualify future stable versions by consumed behavior, update the operator documentation, and ship through the protected feature and release process.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Public CI policy selectors no longer filter findings or private results | WQ-01 | active |
| REQ-002 | Behavioral qualification, candidate disposition, safe batching and promotion | WQ-02 | active |
| REQ-003 | Private opt-in Analysis and accurate operator documentation | WQ-03 | active |
| REQ-004 | Hosted qualification, installed regressions, review and mandatory draft pause | WQ-04 | pending |
| REQ-005 | Protected delivery and immutable receipt readback | WQ-05 | pending |

### Explicit Non-Goals

Published historical evidence remains immutable. No automatic promotion of a new minor line.

### Constraints

The user requires a stop immediately after opening the draft feature PR. Resume later release steps only on explicit instruction.

### Inputs And Sources

Toolkit issues #324–330, upstream releases 1.13.11 through 1.14.2, compatibility run 45148738452, repository development and release contracts.

### User Decisions And Answers

Runtime support moves to the qualified patches of the new line. Integrate optional Analysis now. Target the requested 0.15 patch line.

### Completed Baseline State

Toolkit 0.15.1 is released with OCR 1.13.10. Hosted evidence exists for all three newer 1.13 patches. All three 1.14 jobs stopped on the first hardcoded rule glob.

### Current Work Queue

1. WQ-01: Fix DLP at its source, verify mixed provenance and review/post output.
2. WQ-02: Replace brittle live expectations, qualify and aggregate all outcomes, validate progression and packaged handoffs.
3. WQ-03: Integrate Analysis execution, admission, privacy and reporting. Update docs and release fragments.
4. WQ-04: Verify branch qualification, promote exact evidence, run applicable checks, inspect combined diff and open draft feature PR. Pause.
5. WQ-05: After explicit resume, merge protected feature PR, verify dev distribution, prepare release PR and verify external publication.

### Locked Decisions

Keep credential and integrity errors operational failures. Real incompatibility blocks promotion. Analysis has an independent budget and cannot grant approval.

### Verification

Exercise synthetic GitLab review/post, controlled model, installed wheel and actual GitHub candidates. Run quality, secret and dependency gates. Review each logical commit and the combined change.

### Latest Validation Results

Hosted run 45148738452 produced compatible evidence for 1.13.11–13. Root retrieved those three artifacts before expiry.

### Risks And Recovery

Bound qualification to v1.14.2. If a candidate fails, inspect its closed phase and disposition before retry. Keep stale or incomplete evidence out of promotion.

### Resume Point

Complete WQ-01–03 on the feature branch before final validation and the draft pause.

### Plan Fidelity Check

All seven open issues are covered by WQ-01 and WQ-02. The new runtime capability and operator migration are covered by WQ-03.

### Reconciliation Check

Update this plan at each material checkpoint. Verify issue and milestone closure only after release receipt.

### Closure Gate

Archive in the protected release PR. Verify the immutable release and close the delivery objective after external readback.

### Post-Close Delivery

Release CI owns registry and attestation verification and issue closure.

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
