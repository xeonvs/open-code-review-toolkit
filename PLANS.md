# Execution Plans

## Active Plan: Toolkit 0.14.3 source-aware DLP and private corpus audits

plan_schema_version: 2
Status: active
Owner: root
Last Updated: 2026-10-30

Release classification: release-required; target v0.14.3.

### Goal

Correct #282 and the confirmed related DLP false-positive classes, add a reusable private offline corpus audit, prove old/new behavior after review, and deliver v0.14.3 through the protected release lifecycle. Finish by removing this task's raw source snapshots and temporary raw inputs.

### Plan Origin

`direct_execution`

### Requested Scope

Separate literal source-code interpretation from prose/markup transformations and separate publication secret decisions from conservative diagnostic redaction. Add a repository-only helper for arbitrary textual inputs, selected files and immutable Git corpora, with private reports, exact expectations and reproducible comparisons. Expand #282 only with independently constructed synthetic examples. The extra operator-provided corpus supplies local research evidence only: its identity, locations, contents and identifiers never enter public source, plans, issues, fixtures or PRs.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Reproduce #282 through source proof, projection and local reporting; keep native analysis and incomplete publication visibly distinct | WQ-01, WQ-03 | in_progress |
| REQ-002 | Repository-only offline audit of snippets, file sets and Git snapshots, using production DLP and code admission rather than another detector | WQ-02 | pending |
| REQ-003 | Private snapshots/reports/expectations outside source trees; HMAC identities, explicit selections, no target-owned allowlist and no secret-bearing console output | WQ-02, WQ-05 | pending |
| REQ-004 | Fix confirmed reference-expression and representation false positives without project-specific identifier exceptions, broad source exemptions or weakened literal-secret/PII checks | WQ-03 | pending |
| REQ-005 | Broader synthetic regression/property matrix, real producer-consumer checks and truthful corpus classification rather than coverage or raw-hit targets | WQ-03, WQ-04 | pending |
| REQ-006 | One aggregate Security scan, ordinary actual own-tool acceptance with a real PR diagram, then full repeated corpus scans and final quality | WQ-04 | pending |
| REQ-007 | Reviewed signed plan-first draft PR, protected feature/development verification, v0.14.3 release PR with full plan archival/reset and external reconciliation | WQ-01, WQ-05, WQ-06 | pending |
| REQ-008 | Remove all task-owned raw source snapshots and raw spools, verify absence, retain only source-free reports and synthetic regressions | WQ-06 | pending |

### Explicit Non-Goals

No OCR/model pass during corpus diagnosis or replay; no new review engine, forge adapter, hosted corpus, production allowlist, country assumption, secret verification service, or automatic privacy-policy relaxation. The audit helper is not included in distributions and its reports cannot authorize posting or approval. Do not change result/receipt wire schemas, native coverage or ordinary partial-result exit behavior. Do not import or execute audited projects, initialize submodules, call devices, or acquire private measurements. No website-chat handoff. Do not rewrite previous releases or historical evidence.

### Constraints

- This full plan is the first tracked write. Use codex/ feature branch, signed logical commits and a plan-first draft PR. Keep implementation local until reviewed acceptance is complete; self-review, formatting and staged secret scanning precede every commit/amend.
- Original input text retains independent known-secret, literal-credential, contact and forbidden-source checks. Source proof only enables the interpretation justified by the exact excerpt and safe sink; it is not confidentiality authority.
- Prefer typed context and parsed value roles over lists of benign names, paths, functions, versions or numeric constants. Ambiguous/unproven syntax keeps the conservative decision.
- All private state is operator-selected outside audited roots and Git worktrees, with private physical directories/files, bounded closed schemas and atomic writes. No automatic reading of an input repository's exclusion configuration.
- Snapshots contain only selected code; keys, dumps, working logs, generated environments and private measurements are excluded from this task's external corpus. Source copies remain local and task-owned until mandatory final cleanup.
- Default audit bounds: 20000 files, 1 MiB/file, 16 MiB total, 200000 line/file units and 300 seconds overall. A supervised isolated worker has a 30-second/file ceiling within the remaining deadline. Limits and omissions are explicit; incomplete scans cannot pass.
- Real own-tool acceptance is a new hotfix cycle, authorized for at most two successful runs, with qualified OCR, native ChatGPT high, diagram local and aggregate token budget zero. Inspect raw/filtered findings, auxiliary reads and the actual diagram; focused finding corrections follow the documented procedure.
- One aggregate Security diff scan precedes actual own-tool acceptance. Ordinary scoped fixes and docs do not cause another aggregate scan.

### Inputs And Sources

Issue #282; current clean main and published v0.14.2; AGENTS.md and the development, security, release and decision-flow owners; installed planning/lifecycle reference; production DLP/redaction, opaque-code proof, publication projection, shared reporting, private filesystem and Git-reader owners; current regression/property/native/installed suites. Public synthetic examples include an empty-string join bound to token, type/reference bindings, arithmetic byte limits and strict date literals. External detector documentation informs tradeoffs, not an exemption or replacement oracle.

### User Decisions And Answers

The owner requests a complete own-repository DLP pass, an additional mixed-language local corpus with a useful top-ten analysis, synthetic-only public reproductions, a reusable private audit helper, protected private expectation storage and full repeated scans after fixes/review. Actual release acceptance remains ordinary own-tool review; offline scans themselves never invoke OCR. The owner authorizes a closed local source snapshot outside repositories and requires its eventual removal. The continuing delivery objective includes that cleanup, even after repository plan archival.

### Completed Baseline State

Clean synchronized main is the published v0.14.2 tree. #282 reproduces: token = empty-string.join(parts) is rejected while its renamed control passes. Real immutable-source proof does not prevent the code excerpt from being omitted; local output still begins Review complete with DLP filtering while all findings remain.

A read-only Git-blob audit at the baseline covers 452 UTF-8 files and 121131 nonempty lines (6.46 MB): 160 file units and 1734 line units have a primary rejection. These counts are not a false-positive rate. Whole files and lines expose different units, and intentional negative fixtures remain expected detections. A separate local corpus confirms the need to replay actual source-proof/admission context: many raw markup hits already pass the production code path. No private source snapshot has been persisted by these diagnostic checks; retained diagnostic artifacts contain metadata/fingerprints only.

### Current Work Queue

| Item | Requirements | Work | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-001, REQ-007 | Materialize and critique full plan, reconcile state, signed first push/draft PR, issue/milestone scope with synthetic examples | in_progress |
| WQ-02 | REQ-002, REQ-003 | Implement/test private audit CLI, worker, snapshot/expectation/report/compare lifecycle; curate safe source selections and capture complete baseline before changing DLP | pending |
| WQ-03 | REQ-001, REQ-004, REQ-005 | Implement typed source/rendering contexts, structural secret classification and clear two-axis reporting; add synthetic regressions/fuzzing and update public contracts | pending |
| WQ-04 | REQ-005, REQ-006 | Aggregate review, one Security scan, qualified actual self-review/diagram and scoped corrections; repeat both full corpora, review every transition and complete final quality | pending |
| WQ-05 | REQ-003, REQ-007 | Final feature PR/diagram push, protected CI/merge and development verification; prepare signed release PR with full checked plan archival | pending |
| WQ-06 | REQ-007, REQ-008 | Stable external verification, issue/milestone/site and clean main; remove owned raw snapshots/spools and verify cleanup before task completion | pending |

### Locked Decisions

**DLP boundaries.** Keep diagnostic redaction conservative. Publication uses explicit semantic detector decisions, sharing candidate rules rather than inferring a secret from any redactor rewrite. Bind source interpretation to the existing exact-source proof and safe literal renderer. Distinguish prose, fenced source and fixed renderer-owned diagram labels so Markdown-only deletions do not manufacture contacts in literal arithmetic. Keep independent security canonicalization, whole-unit sensitive-value checks and forbidden attribution. No blanket exemption for code or model-chosen context.

Use bounded standard-library syntactic analysis of proven Python source to classify declarations, reference/call/slice/keyword expressions, empty constructions and non-value defaults. Every waived generic candidate must map to the proven syntax and contain no credential literal material. Nonempty literals, embedded values, comments not covered by a valid syntax proof, unknown syntax and unsupported language refinements remain conservative. Other languages retain strict credential handling while receiving the sink-correct literal rendering behavior; this is not a claim of universal language semantics. Parsed technical literal corrections require complete valid grammar and explicit contact priority, not repository-specific names. No new third-party runtime engine is selected: replacing the detector does not solve the proven source/sink mismatch and introduces different precision/recall tradeoffs.

**Reporting.** Show native analysis and publication health separately whenever public fields/findings are omitted: analysis complete cannot imply accepted complete publication. Preserve native coverage, retained/omitted counts, partial/budget/failed precedence and private-only sanitization. Diagram-only omission stays optional. Share provider-neutral presentation; provider writes and approval rules remain with their existing owners. Ordinary review exit behavior and persisted identities remain unchanged.

**Audit tool.** Add scripts/dlp_audit.py as a thin repository-only CLI with cohesive private tooling helpers. Support scan from an immutable Git ref, explicit file set/NUL file list, stdin snippet, or a captured snapshot; compare baseline/candidate runs; annotate exact expectations; and clean owned raw state. Call the installed production scanner from a supervised isolated worker without importing the target or using its configuration. Evaluate raw text and, where justified, the real existing-code proof/projection path. Record the primary closed reason per unit, proof eligibility and projection omissions; do not pretend to collect every independent detector match. Cache bounded source analysis per immutable file, process batches by file, and infer passed units only from verified complete evaluation counts.

Default reports are private JSON plus Markdown with locations, counts, primary detectors, top-ten groups and local source locators; they do not embed matched values or source snippets. Console output is source-free. Capture Git identity or descriptor-checked filesystem bytes, reject moving snapshots, do not follow links or open devices/FIFOs, and explicitly account for binary/oversize/gitlink/unsupported inputs. New audit output has its own closed diagnostic schema, not a toolkit receipt. Scanner identity, corpus selection, profiles and effective secret-set fingerprints bind comparisons; raw environment secrets are never stored.

**Expectations and comparisons.** Keep annotation state outside repositories. Use a private per-state HMAC key and identities bound to corpus, exact file content, unit/span and sink role; no plaintext values or production suppression rules. Unknown schemas, changed inputs/configuration and invalid keys fail closed. Labels distinguish expected protection, confirmed benign input and deliberately conservative ambiguity; they never stop scanning. Compare all input units, including previously passing ones, with the same complete snapshots/profile. Newly rejected units, newly admitted protected units and unexplained reason changes require review. A smaller hit count is not success. Scan/compare use exit 0 only for complete satisfied expectations, 1 for complete results needing triage or showing a regression, and 2 for incomplete/invalid execution.

**Privacy and cleanup.** Publish only independently generated synthetic fixtures and conclusions; never copy and rename private source/key material. Before any persistent source capture, check the selected files against their provenance and privacy owners; exclude complete secret-bearing/generated-profile or measurement files instead of sanitizing input and calling it the original corpus. Freeze the accepted selection and establish its unchanged-scanner baseline. Keep each task's snapshot inventory and recovery pointer private. Final cleanup removes exactly owned source copies and raw spools after external delivery checks, preserves original inputs and verifies absence. Only source-free reports/expectations and synthetic regressions may remain; cleanup failure prevents completion. Interrupted work retains explicit cleanup ownership rather than an unrecorded raw snapshot.

### Verification

- Independent safe/reference versus literal/embedded-secret controls; secret-name renaming invariance for nonsecret proven expressions; exact environment values, short credentials, PII and forbidden values still block in every applicable representation.
- Declarations, calls, slicing, keyword arguments, empty/default values, concatenated/interpolated/encoded values, malformed/partial syntax, Unicode byte/code-point positions and parser/resource limits. Failed/stale/mismatched proof never grants interpretation.
- C/other-language literal syntax, includes/generics, arithmetic and renderer profiles; existing source-proof successes stay successes. Unresolved numeric/credential ambiguities retain explicit conservative expectations.
- Real Git/source-proof -> projection -> persisted result/admission -> local/GitLab rendering handoffs. Cover all findings retained with one code field omitted, zero retained findings, native partial/budget states, private-only cleanup and optional diagrams.
- Audit hostile paths, Unicode/newlines, symlinks/hardlinks, FIFOs/devices, changing files, non-UTF8 and limits; shadow packages and no target execution; worker timeout/crash/malformed output; secret-bearing failures cannot spill values.
- Private state/report permissions, exact HMAC scope, stale/tampered/unknown/duplicate-key baseline rejection, complete unit accounting, comparison of previously passing units and idempotent ownership-checked raw cleanup.
- Default 100-example CI properties and independent 1000-example local seeds; old synthetic DLP corpus plus newly minimized independent cases, not implementation-mirroring assertions.
- After reviews/fixes, rerun every selected unit in both captured corpora and the new candidate repository. Classify all unexpected transitions, retain source-free summaries and repeat affected replay after material DLP changes. Final quality, installed/native checks, privacy and dependency gates bind the final runtime.
- Protected feature/development and stable release workflows, registry/provenance/Python installs, immutable receipt/tag/Release and independent issue/milestone/site/main readback; mandatory raw-state cleanup before final completion.

### Latest Validation Results

2026-10-30: read-only diagnosis is complete enough to establish #282's source/projection defect and the audit's need for sink-aware interpretation. Both initial corpora scans complete without OCR. Their results are private diagnostic evidence, not accepted ground truth or publication eligibility. The repository remains unmodified before this plan.

### Risks And Recovery

Source provenance is not permission to publish a secret: reject unmapped candidates and scan all original/encoded sensitive material. A lexer/normalizer can create a false phone or hide a real one: choose representations by the actual sink and replay strong counterexamples. Broad expectation patterns can conceal new defects: bind them to exact private input identity and keep scanning. An altered corpus/environment is not a detector regression or improvement: fail comparison as incomparable. Private state can leak through reports/errors or cleanup: use closed output fields, fixed private destinations and ownership-checked removal; preserve originals. On a failed check retain value-free diagnostics and the exact resume action, repair the narrow owner and rerun the affected checks. No additional aggregate Security scan for ordinary follow-up fixes.

### Resume Point

WQ-01: critique this saved plan, set active-plan state and create the codex/ branch; run plan/instruction/privacy/dependency guards, sign the plan-first commit, push and open a draft PR. Then implement the audit helper and capture the complete unchanged-scanner baseline before DLP changes. Private corpus details remain outside public artifacts.

### Plan Fidelity Check

- [x] Every requested outcome, privacy correction, review choice, replay and snapshot cleanup maps to a requirement and queue item.
- [x] Source semantics, rendering, diagnostic redaction, audit state and provider outcomes have explicit owners and failure boundaries.
- [x] The helper uses production decisions and source context; initial raw-hit counts are not ground truth or release gates.
- [x] Unsupported/ambiguous cases, resource limits, private annotations and post-review replay are explicit.
- [x] Release archival and continuing external delivery/cleanup are retained without a later closure PR.

### Reconciliation Check

- [x] Baseline is current clean main with published v0.14.2; prior evidence remains historical.
- [x] Public material contains synthetic examples only; no private corpus identity or source is retained here.
- [ ] Final implementation, actual decisions, docs and acceptance evidence agree.

### Closure Gate

- [ ] Implementation and applicable final-runtime verification are complete.
- [ ] Security/own-tool findings and all unexpected corpus transitions are resolved; an actual admitted PR diagram exists.
- [ ] Protected feature merge and development publication are verified.
- [ ] Release PR prepares authorization, markers, notes, pins and checked full plan archival/reset.
- [ ] Required external publication/reconciliation and raw snapshot cleanup are truthfully classified under Post-Close Delivery.

### Post-Close Delivery

Required and not yet completed: release-PR signing/push/protected CI/merge, stable registry/provenance/install/tag/immutable Release/receipt verification, Actions-owned issue closure, milestone/site and independently clean main. The final external checklist also removes owned raw source snapshots/spools and verifies their absence. Repository archival in the release PR does not complete or waive these actions; no follow-up repository closure PR is authorized.

### Handoff Notes

Continue at the Resume Point. Public source receives only independent synthetic examples. Raw snapshot removal is part of the continuing objective, not optional housekeeping. Retain private evidence only under its explicit ownership and do not message a website chat.

## Recently Completed

- [x] 2026-10-30: Completed Toolkit 0.14.2 compact bootstrap, diagram-only reports and DLP corrections; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-2-compact-bootstrap-diagram-only-reports-and-dlp-corrections.md).
- [x] 2026-10-29: Completed Toolkit 0.14.1 grouped diagrams and private debug qualification; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-1-grouped-diagrams-and-private-debug-qualification.md).
- [x] 2026-10-29: Completed Toolkit 0.14.0 range identity, typed diagrams, DLP qualification and Python 3.15; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-0-range-identity-typed-diagrams-dlp-qualification-and-python-3-15.md).
- [x] 2026-10-25: Completed Two-day GitHub Actions retention; [full archived plan](docs/engineering/execution_history/plans/2026-10-25-two-day-github-actions-retention.md).
- [x] 2026-10-23: Completed Toolkit 0.13.1 partial review of changes containing gitlinks; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-1-partial-review-of-changes-containing-gitlinks.md).
- [x] 2026-10-23: Completed Toolkit 0.13.0 protected default-policy fallback for single-MR review; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-0-protected-default-policy-fallback-for-single-mr-review.md).
