# Execution Plans

## Active Plan: Toolkit 0.14.2 compact bootstrap and diagram-only reports

plan_schema_version: 2
Status: active
Owner: root
Last Updated: 2026-10-30

Release classification: release-required; target v0.14.2 because the documented report presentation changes.

### Goal

Publish v0.14.2 with one compact immutable-ref block in the model bootstrap and diagrams without the unsolicited textual node/edge listing in ordinary reports. Complete feature validation, protected delivery and independent stable readback without a later plan-closure PR.

### Plan Origin

`direct_execution`

### Requested Scope

Remove the complete text equivalent from ordinary GitLab and standalone local reports in every diagram mode. Retain the existing private candidate/debug data, without adding another debug artifact. Consolidate identical SHA text in bootstrap, preserve explicit role mapping and truncation safety, and remove redundant range lines from human reports. Keep every machine identity and admission/publication boundary unchanged. Acceptance subsequently adds owner-authorized narrow DLP false-positive corrections and broader network/comparison fuzzing, as traced in REQ-011/012. Follow the established plan-first draft PR, local development, self-review, security, own-tool review and release procedure. No promotional-site chat handoff is requested.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Mermaid-only ordinary reports; no textual listing, including GitLab on/spoiler and local | WQ-02 | done |
| REQ-002 | A single protected bootstrap refs block; identical SHA values printed once with deterministic role aliases | WQ-02 | done |
| REQ-003 | Human report range details avoid duplicate endpoint/commit lines; legacy and distinct identities remain explicit | WQ-02 | done |
| REQ-004 | Preserve MCP, evidence records, receipts, persisted schema, immutable Git identity, findings and optional failure behavior; DLP corrections are limited to REQ-011/012 | WQ-02, WQ-03 | in_progress |
| REQ-005 | Update current public contracts and relevant tests; retain historical evidence unchanged | WQ-02, WQ-03 | in_progress |
| REQ-006 | Signed draft feature PR, reviewed local development, protected feature merge and verified development publication | WQ-01, WQ-04 | in_progress |
| REQ-007 | Deliver v0.14.2 with plan archived in its release PR and independent external reconciliation | WQ-05, WQ-06 | pending |
| REQ-008 | Require a real admitted diagram for own-tool acceptance, publish it in the feature PR at final push and document this normal development procedure | WQ-02, WQ-03, WQ-04 | pending |
| REQ-009 | Keep bootstrap provider-neutral for local, GitLab and future adapters, with conditional intent/protection hints and complete context discovery | WQ-02, WQ-03 | done |
| REQ-010 | Add repository-specific self-review Rules, retain system checks, select relevant tests per task, qualify and use a private operator copy in this review | WQ-03 | done |
| REQ-011 | Correct the real-review assertion and technical Mermaid false positives with whole-unit encoded-value checks and stronger property/publication tests | WQ-03 | done |
| REQ-012 | Exercise invalid IPv4, masks and IPv6; fix reproduced mapped-CIDR and dotted-mask false positives with bounded whole-token parsing and reverse contact checks | WQ-03 | done |

### Explicit Non-Goals

No new settings, diagram types, model pass, graph scope changes, debug artifacts, dependencies, native OCR changes, machine-contract/schema changes or token-accounting study. DLP changes are limited to reproduced false positives discovered during acceptance and owner-requested network fuzzing: bounded decimal Mermaid representations and technical prefixes, plus complete bounded CIDR/mask parsing. DLP does not become a network-configuration validator. No promotional-site messaging or manual website work. Do not rewrite published release objects or archived acceptance facts. The existing automatic release notification is unchanged.

### Constraints

- First repository write is this full plan; feature branch uses codex/ and the first signed push opens a draft PR.
- Keep implementation local until all work and acceptance checks are complete. Review every logical commit before staging, run formatting and staged secret checks, and use local amend when appropriate.
- Consolidation is presentation only: role, trust and authority remain distinct even when commits are equal. Missing snapshots are never aliases.
- Use a 3000-character default bootstrap cap (existing 32 KiB byte bound and 7950-character maximum unchanged). The complete metadata/enriched/federation/policy-fallback opening and diagram closing need more room than the prior 2300-character default. Do not shorten essential semantics to fit that old incidental budget; full evidence still stays in MCP and optional hints remain bounded.
- Required evidence navigation, refs, domain/context/federation routing and policy limitations form the protected opening; the diagram request is a protected closing after the evidence overview. Reserve both before clipping optional overview/hints; reject an impossible bound rather than silently dropping required instructions. Evidence records remain fully available through the unchanged MCP.
- Ordinary reports render admitted Mermaid and the bounded-summary caveat, without node/edge/source-reference prose. Existing private diagram.json preserves candidate/reference diagnostics.
- Reporting remains pure; no Git, environment, MCP, DLP orchestration or provider writes enter it.
- Use one aggregate Codex Security diff scan after the aggregate semantic review. Focused corrections and documentation updates do not trigger another aggregate scan.
- Real own-tool acceptance uses qualified OCR, native ChatGPT high, diagram local, --max-tokens-budget 0 and private physical paths. The previous corrective allowance of four successful runs has one consumed; do not reset it. Aim for one run and inspect warnings, auxiliary reads, the actual output tool call and admitted diagram.
- No private artifact paths, internal conversation identifiers or raw diagnostics enter public source or PRs.
- The release PR owns all repository closure; external publication/readback remains truthful post-close delivery.

### Inputs And Sources

Owner-approved analysis and corrections; tracking issue #279 and milestone v0.14.2; AGENTS.md; project principles; development, local-review, diagram and release guides; installed planning/lifecycle reference; production bootstrap, shared renderer, local and GitLab adapters; existing regression/property/native/installed tests. Current artifacts demonstrate repeated base/head text in bootstrap and report; they are private diagnostic evidence, not public fixtures.

### User Decisions And Answers

Remove the textual equivalent from normal output rather than collapse it. It may remain in debug, but no new debug text is required. Exact token savings need not be measured; the layout must be logical and justified. Do not change MCP or persisted identities. Proceed under the normal delivery procedure without a landing-page chat handoff. Strengthen affected test coverage, including fuzzing. The own-tool acceptance must produce an actual admitted diagram; add that exact Mermaid to the feature PR at final push and establish this as the normal contributor procedure.

The owner additionally authorizes concise repository self-review Rules and an explicit operator overlay for the current run, through amend of the unpublished implementation commit. Local relative Rules stay bound to base; debugging does not change authority. Use a reviewed committed private copy outside the checkout for this first adoption. The runtime tree remains unchanged; the later Rules/configuration receive focused semantic/security review and real native preview/application checks alongside the single immutable runtime-diff Security scan already started.

Routine Rules do not blanket-include tests. For this test-heavy correction, the operator copy explicitly selects changed property/native/installed contract tests; their assertions are material to the release's boundary claims. The permanent Rules retain test guidance for such selected files and explicitly include maintained documentation/changelog text. A real native preview established that default pytest-prefix exclusions require explicit include for targeted tests.

The first actual review completed all 25 files, produced an admitted change diagram and found one valid test-assertion weakness. DLP omitted that finding because its Mermaid example `version #60; 2020.1.10` looked like a phone. The owner explicitly adds the narrow DLP correction to 0.14.2 and requests stronger fuzzing/coverage here. Recognize technical syntax in the existing bounded prefix and inspect one complete additional decimal Mermaid representation for secrets, contacts, forbidden attribution and controls. Keep original unit checks and output unchanged. Review this small correction at its source/sink with focused security tests; do not repeat the aggregate Security scan. A second actual review is justified by this newly changed runtime boundary and will supply the final PR diagram.

The owner additionally requests malformed/unrealistic IPv4 and mask variants, IPv6 examples and broader regex variation. Independent generators reproduce false positives for `::ffff:192.0.2.1/96` and `192.0.2.100/255.255.255.255`. Reconstruct at most 64 characters of the complete network token and parse it with `ipaddress`; reject truncated/embedded tokens rather than enlarge the phone regex. Preserve explicit phone-context priority and whole-unit credential/contact checks. Negative properties distinguish actual PII rejection from malformed network syntax that is simply outside DLP's purpose. Extended seeds use 1000 examples/property for raw/HTML/Markdown/Mermaid forms, mixed operators, Unicode, exact bounds and long near matches. The network corpus includes the owner examples 123.456.789.385, IPv4 /35 versus valid IPv6 /35, and ports at 65535/65536 and beyond. The original real finding survives the production publication projection after the correction. Metamorphic tests through both actual renderers additionally expose and correct Decimal/nonbreaking-space false positives and an encoded sensitive-value gap. One non-expanding decimal decode layer receives complete secret/PII/forbidden/control checks, retaining exact empty/template semantics and escaped literal hashes. This avoids treating a numeric exception as permission for the rest of the unit.

### Completed Baseline State

Clean synchronized main contains published v0.14.1. Current diagram rendering appends a text equivalent in both adapters. Bootstrap repeats base/head inside the protected diagram instruction and the lower refs section; equal policy/target commits may repeat further. Human reports repeat endpoints in exact range and Reviewed commit. No implementation changes made yet.

### Current Work Queue

| Item | Requirements | Work | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-006 | Materialize and critique full plan; set active-plan state; signed plan commit, privacy/dependency gates, initial push and draft PR | done |
| WQ-02 | REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-008, REQ-009 | Implement compact protected refs, Mermaid-only reports and range-line consolidation with focused regression/property/native tests and documentation | done |
| WQ-03 | REQ-004, REQ-005, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012 | Aggregate semantic review, full quality, one security diff scan, qualified actual own-tool acceptance with repository Rules; fix findings and rerun affected checks | in_progress |
| WQ-04 | REQ-006, REQ-008 | Final reviewed feature push with the real admitted diagram in the PR, protected CI and merge; verify development TestPyPI workflow | pending |
| WQ-05 | REQ-007 | Signed release/v0.14.2 PR: metadata, changelog, notes, issue authorization and full checked plan archival; protected CI and merge | pending |
| WQ-06 | REQ-007 | External stable workflow, immutable receipt/release/tag, registries, installed/provenance CI evidence, issue/milestone and clean main readback | pending |

### Locked Decisions

Use the existing provider-neutral renderer; remove obsolete text-renderer helpers instead of leaving unused production code. Consolidate refs in a deterministic pure bootstrap projection with aliases pointing only to earlier explicit full values. Protect all necessary navigation before clipping optional overview/hints, and protect the diagram instruction at the end. Do not copy framework, dependency/version, CI or policy facts into bootstrap: summary kinds/components/delta_kinds route relevant list/get/search queries. Context uses list-before-get; external aliases/schemas come from the frozen actual MCP tools, not another bootstrap inventory. For verified human reports show the full exact range once; retain Reviewed commit when range is absent or the value differs, and preserve distinct MR head/policy context. Keep existing JSON contracts byte-for-byte in shape and meaning. No extra model phase or candidate synthesis.

Prioritize applicable decision/guidance hints over secondary capability/status detail. Remove duplicated kind/delta inventories from bootstrap because the required summary supplies them. The clipping notice describes optional overview/hints and points to scoped reads; do not require a redundant second summary. A qualified real OCR/relay replay with forced clipping has already preserved summary -> intent getter -> federated tracker execution.

### Verification

- Both diagram variants in local and GitLab on/spoiler: no Text equivalent or node/edge listing; Mermaid, escaping, bounded caveat and optional omission behavior retained.
- Refs matrix: all distinct, policy/base equal, target/base equal, target/head equal, equal base/head, absent/legacy snapshots, deterministic aliases and malicious/Unicode surrounding content.
- Clipping: ordinary and tight char/UTF-8 limits, long MR/context navigation and unsupported tiny bounds; complete protected navigation and refs or explicit failure.
- Context routing matrix: framework/runtime, declared/locked dependency versions, templates, CI/images/infrastructure, policy/guidance, metadata/enriched and external federation. Verify actual tool schemas and queryable records, not only bootstrap wording. Scale facts, long diagnostics and tool inventory together; mandatory routing and both protected ends survive while the last fact stays retrievable through MCP.
- Provider parity: common review-intent wording, no unconditional MR/GitLab prerequisite in local+federation, and only factual conditional protection/intent hints. No speculative new forge adapter or machine-contract rename.
- Range display: verified, legacy/unverified, distinct reviewed and MR heads, skipped/failed/filtered paths.
- Producer/consumer coverage: actual native grouped bootstrap delivery, stdio candidate/admission, private artifacts and both report paths; installed wheel/sdist checks from the existing suite/CI owner.
- Focused pytest and Hypothesis plus final scripts/quality.sh check; public-contract/navigation/instruction guards, staged/tree/history Gitleaks and pre-push dependency audit.
- Aggregate semantic review, one security scan and at least one qualified real own-tool acceptance under the remaining allowance. No budget/tool/context-exhaustion warnings; inspect auxiliary reads and real diagram output.
- Feature/release protected checks and existing development/stable registry, provenance, supported-Python install and immutable receipt gates.

### Latest Validation Results

Signed plan a7454cb is pushed; draft PR #280 is open and attached. Implementation is complete locally. Initial lifecycle, instruction, staged/tree/history secret and dependency checks pass. Owner review exposed gaps in the initial analysis: critical navigation could be clipped, and local federation inherited an MR prerequisite. The protected provider-neutral routing and 40 supported-profile matrix address those paths. Qualified OCR 1.13.3 passes 19 grouped/round and federation cases, retrieving actual framework, locked dependency version and runtime data through production MCP; forced-clipping federation routing also passes. Both extended property seeds pass at runtime commit 1745810. Generated ordinary and maximal-profile bootstraps were read in full; dangling optional headings were removed. The initial full quality run exposed an installed policy-hint presentation failure; optional-body priority and duplicate inventories were corrected without weakening that assertion. Fresh focused and clean installed wheel/sdist checks pass together (128 tests). The next full run at 1745810 records 3175 passes, 41 skips and 357 subtests, failing only an obsolete assertion of kind counts in bootstrap. That test now checks exact unchanged MCP summary counts and protected bootstrap navigation; its focused suite passes (57 tests). A final complete quality exit remains required. The 3000-character default protects complete rich-profile instructions. Aggregate semantic review covers all four changed runtime owners and their unchanged producer/admission/MCP/persistence boundaries. The single immutable-range Codex Security scan is sealed with complete changed-file coverage and zero findings. Late Rules/docs receive focused semantic/security and real native configuration checks without runtime changes. The later owner-authorized DLP correction receives separate focused source/sink security review and negative property tests, preserving the single aggregate scan. Initial quality at amended head 4326742 passes all 3176 tests and 357 subtests. The first successful actual-model run has complete 25/25 coverage and a generated diagram, but exposed the assertion and DLP defects described above. Final corrected-head quality and second-run acceptance remain required; one successful run is consumed by this task.

### Risks And Recovery

Moving refs or the diagram request can displace required navigation; protect the complete opening and closing and test the worst supported profile under the default budget, not only small fixtures. Review the fully generated bootstrap before any implementation commit. Aliases can obscure roles or chain through unavailable values; permit only deterministic references to an earlier concrete equal SHA. Removing prose must not alter DLP/admission; assert both adapters and failure paths. Report de-duplication must not hide mismatched/legacy identities. A real model diagram describes changes in the reviewed range; publish it in the feature PR without adding a separate program-completeness disclaimer. On failed checks preserve the evidence, repair the narrow owner and rerun affected checks before committing. On external publication failure use the existing receipt-bound recovery path; never move tags or replace artifacts.

### Resume Point

WQ-03: initial quality at amended head 4326742 passes (3176 tests, 41 skipped, 357 subtests). The first actual-model review completes 25/25 files, calls the diagram tool once and produces an admitted nine-node flowchart; trace capture is complete, Rules apply at their file groups, and no failed source/tool responses or budget warnings occur. Its valid test finding and the authorized DLP false positives are corrected locally; both extended DLP/network corpora pass, the 18 grouped native cases pass, and federation qualification passes with the verified binary digest. Complete reviewed correction commit, final full quality and the justified second actual review with a fresh selective Rules copy that includes these added DLP tests. Use its exact admitted diagram in the PR. One successful own-tool run has been consumed by this task; the earlier corrective run remains counted in the allowance. No feature push until these gates pass.

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
