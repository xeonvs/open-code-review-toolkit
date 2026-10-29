# Execution Plans

## Active Plan: Toolkit 0.14.2 compact bootstrap and diagram-only reports

plan_schema_version: 2
Status: active
Owner: root
Last Updated: 2026-10-29

Release classification: release-required; target v0.14.2 because the documented report presentation changes.

### Goal

Publish v0.14.2 with one compact immutable-ref block in the model bootstrap and diagrams without the unsolicited textual node/edge listing in ordinary reports. Complete feature validation, protected delivery and independent stable readback without a later plan-closure PR.

### Plan Origin

`direct_execution`

### Requested Scope

Remove the complete text equivalent from ordinary GitLab and standalone local reports in every diagram mode. Retain the existing private candidate/debug data, without adding another debug artifact. Consolidate identical SHA text in bootstrap, preserve explicit role mapping and truncation safety, and remove redundant range lines from human reports. Keep every machine identity and admission/publication boundary unchanged. Follow the established plan-first draft PR, local development, self-review, security, own-tool review and release procedure. No promotional-site chat handoff is requested.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Mermaid-only ordinary reports; no textual listing, including GitLab on/spoiler and local | WQ-02 | pending |
| REQ-002 | A single protected bootstrap refs block; identical SHA values printed once with deterministic role aliases | WQ-02 | pending |
| REQ-003 | Human report range details avoid duplicate endpoint/commit lines; legacy and distinct identities remain explicit | WQ-02 | pending |
| REQ-004 | Preserve MCP, evidence records, receipts, persisted schema, immutable Git identity, DLP, findings and optional failure behavior | WQ-02, WQ-03 | pending |
| REQ-005 | Update current public contracts and relevant tests; retain historical evidence unchanged | WQ-02, WQ-03 | pending |
| REQ-006 | Signed draft feature PR, reviewed local development, protected feature merge and verified development publication | WQ-01, WQ-04 | in_progress |
| REQ-007 | Deliver v0.14.2 with plan archived in its release PR and independent external reconciliation | WQ-05, WQ-06 | pending |

### Explicit Non-Goals

No new settings, diagram types, model pass, graph scope changes, debug artifacts, dependencies, native OCR changes, machine-contract/schema changes or token-accounting study. No promotional-site messaging or manual website work. Do not rewrite published release objects or archived acceptance facts. The existing automatic release notification is unchanged.

### Constraints

- First repository write is this full plan; feature branch uses codex/ and the first signed push opens a draft PR.
- Keep implementation local until all work and acceptance checks are complete. Review every logical commit before staging, run formatting and staged secret checks, and use local amend when appropriate.
- Consolidation is presentation only: role, trust and authority remain distinct even when commits are equal. Missing snapshots are never aliases.
- Required evidence navigation and refs must survive line/byte clipping together; reject a bound that cannot retain required content rather than silently dropping identity.
- Ordinary reports render admitted Mermaid and the bounded-summary caveat, without node/edge/source-reference prose. Existing private diagram.json preserves candidate/reference diagnostics.
- Reporting remains pure; no Git, environment, MCP, DLP orchestration or provider writes enter it.
- Use one aggregate Codex Security diff scan after the aggregate semantic review. Focused corrections and documentation updates do not trigger another aggregate scan.
- Real own-tool acceptance uses qualified OCR, native ChatGPT high, diagram local, --max-tokens-budget 0 and private physical paths. The previous corrective allowance of four successful runs has one consumed; do not reset it. Aim for one run and inspect warnings, auxiliary reads, the actual output tool call and admitted diagram.
- No private artifact paths, internal conversation identifiers or raw diagnostics enter public source or PRs.
- The release PR owns all repository closure; external publication/readback remains truthful post-close delivery.

### Inputs And Sources

Owner-approved analysis and corrections; tracking issue #279 and milestone v0.14.2; AGENTS.md; project principles; development, local-review, diagram and release guides; installed planning/lifecycle reference; production bootstrap, shared renderer, local and GitLab adapters; existing regression/property/native/installed tests. Current artifacts demonstrate repeated base/head text in bootstrap and report; they are private diagnostic evidence, not public fixtures.

### User Decisions And Answers

Remove the textual equivalent from normal output rather than collapse it. It may remain in debug, but no new debug text is required. Exact token savings need not be measured; the layout must be logical and justified. Do not change MCP or persisted identities. Proceed under the normal delivery procedure without a landing-page chat handoff.

### Completed Baseline State

Clean synchronized main contains published v0.14.1. Current diagram rendering appends a text equivalent in both adapters. Bootstrap repeats base/head inside the protected diagram instruction and the lower refs section; equal policy/target commits may repeat further. Human reports repeat endpoints in exact range and Reviewed commit. No implementation changes made yet.

### Current Work Queue

| Item | Requirements | Work | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-006 | Materialize and critique full plan; set active-plan state; signed plan commit, privacy/dependency gates, initial push and draft PR | in_progress |
| WQ-02 | REQ-001, REQ-002, REQ-003, REQ-004, REQ-005 | Implement compact protected refs, Mermaid-only reports and range-line consolidation with focused regression/property/native tests and documentation | pending |
| WQ-03 | REQ-004, REQ-005 | Aggregate semantic review, full quality, one security diff scan, qualified actual own-tool acceptance; fix findings and rerun affected checks | pending |
| WQ-04 | REQ-006 | Final reviewed feature push, protected CI and merge; verify development TestPyPI workflow | pending |
| WQ-05 | REQ-007 | Signed release/v0.14.2 PR: metadata, changelog, notes, issue authorization and full checked plan archival; protected CI and merge | pending |
| WQ-06 | REQ-007 | External stable workflow, immutable receipt/release/tag, registries, installed/provenance CI evidence, issue/milestone and clean main readback | pending |

### Locked Decisions

Use the existing provider-neutral renderer; remove obsolete text-renderer helpers instead of leaving unused production code. Consolidate refs in a deterministic pure bootstrap projection with aliases pointing only to earlier explicit full values. Keep the unified refs block inside the protected prefix. For verified human reports show the full exact range once; retain Reviewed commit when range is absent or the value differs, and preserve distinct MR head/policy context. Keep existing JSON contracts byte-for-byte in shape and meaning. No extra model phase or candidate synthesis.

### Verification

- Both diagram variants in local and GitLab on/spoiler: no Text equivalent or node/edge listing; Mermaid, escaping, bounded caveat and optional omission behavior retained.
- Refs matrix: all distinct, policy/base equal, target/base equal, target/head equal, equal base/head, absent/legacy snapshots, deterministic aliases and malicious/Unicode surrounding content.
- Clipping: ordinary and tight char/UTF-8 limits, long MR/context navigation and unsupported tiny bounds; complete protected navigation and refs or explicit failure.
- Range display: verified, legacy/unverified, distinct reviewed and MR heads, skipped/failed/filtered paths.
- Producer/consumer coverage: actual native grouped bootstrap delivery, stdio candidate/admission, private artifacts and both report paths; installed wheel/sdist checks from the existing suite/CI owner.
- Focused pytest and Hypothesis plus final scripts/quality.sh check; public-contract/navigation/instruction guards, staged/tree/history Gitleaks and pre-push dependency audit.
- Aggregate semantic review, one security scan and at least one qualified real own-tool acceptance under the remaining allowance. No budget/tool/context-exhaustion warnings; inspect auxiliary reads and real diagram output.
- Feature/release protected checks and existing development/stable registry, provenance, supported-Python install and immutable receipt gates.

### Latest Validation Results

Baseline read-only analysis confirms the current shared renderer and GitLab caller publish both Mermaid and text. The protected diagram instruction contains the duplicate SHA pair; the lower refs block is outside the protected prefix. Saved-plan critique confirms scope, boundaries, review allowance and closure ownership. Initial lifecycle validation caught missing schema/origin metadata and non-explicit queue mappings; these were corrected before implementation. Instruction-contract validation passes.

### Risks And Recovery

Moving refs without preserving the clipping boundary can lose identity; protect the unified block and test impossible bounds explicitly. Aliases can obscure roles or chain through unavailable values; permit only deterministic references to an earlier concrete equal SHA. Removing prose must not remove the bounded-summary caveat or alter DLP/admission; assert both adapters and failure paths. Report de-duplication must not hide mismatched/legacy identities. On failed checks preserve the evidence, repair the narrow owner and rerun affected checks before committing. On external publication failure use the existing receipt-bound recovery path; never move tags or replace artifacts.

### Resume Point

WQ-01: critique this saved plan, reconcile release target and active-plan state, then create the signed plan-first draft feature PR after the required pre-push gates.

### Plan Fidelity Check

- [x] All owner outcomes, corrections and boundaries mapped to requirements and queue items.
- [x] Presentation, model context and machine identity have separate owners and acceptance evidence.
- [x] No exact token measurement, unsolicited debug addition or website coordination added.
- [x] Failure/clipping/legacy cases, review allowance, release classification and recovery are explicit.
- [x] First safe unfinished action and complete delivery/closure sequence are retained.
- [x] Owner's additional coverage request is included: strengthen affected branches and bounded fuzzing, especially alias equivalence, clipping and both report adapters.

### Reconciliation Check

- [x] Baseline matches current main and archived prior work remains historical.
- [x] No unrelated backlog or roadmap work activated.
- [ ] Final diff, docs, checks and plan describe the same completed scope.

### Closure Gate

- [ ] All implementation requirements and applicable verification complete on the final runtime head.
- [ ] Security and real own-tool findings resolved with truthful acceptance evidence.
- [ ] Protected feature merge and development publication verified.
- [ ] Release PR contains authorization, version markers, notes and checked full plan archive.
- [ ] No unfinished repository work or follow-up closure PR remains; external delivery is classified below.

### Post-Close Delivery

Required: after release-PR merge, verify the exact stable workflow, TestPyPI/PyPI artifacts and supported-Python/provenance evidence, annotated tag, immutable Release/receipt and issue/milestone closure. Confirm clean synchronized main independently. These external facts are not yet complete and are not claimed by the prepublication archive.

### Handoff Notes

Continue at the Resume Point. Keep private diagnostic material out of public artifacts. Do not message a website chat or create a later repository closure PR.

## Recently Completed

- [x] 2026-10-29: Completed Toolkit 0.14.1 grouped diagrams and private debug qualification; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-1-grouped-diagrams-and-private-debug-qualification.md).
- [x] 2026-10-29: Completed Toolkit 0.14.0 range identity, typed diagrams, DLP qualification and Python 3.15; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-0-range-identity-typed-diagrams-dlp-qualification-and-python-3-15.md).
- [x] 2026-10-25: Completed Two-day GitHub Actions retention; [full archived plan](docs/engineering/execution_history/plans/2026-10-25-two-day-github-actions-retention.md).
- [x] 2026-10-23: Completed Toolkit 0.13.1 partial review of changes containing gitlinks; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-1-partial-review-of-changes-containing-gitlinks.md).
- [x] 2026-10-23: Completed Toolkit 0.13.0 protected default-policy fallback for single-MR review; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-0-protected-default-policy-fallback-for-single-mr-review.md).
