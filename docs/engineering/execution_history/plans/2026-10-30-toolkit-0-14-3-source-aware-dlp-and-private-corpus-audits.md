# Execution Plans

## Active Plan: Toolkit 0.14.3 source-aware DLP and private corpus audits

plan_schema_version: 2
Status: done
Owner: root
Last Updated: 2026-10-30

Release classification: release-required; target v0.14.3.

### Goal

Correct #282 and the confirmed related DLP false-positive classes, add a reusable private offline corpus audit, prove old/new behavior after review, and deliver v0.14.3 through the protected release lifecycle. Finish by removing this task's raw source snapshots and temporary raw inputs.

### Plan Origin

`direct_execution`

### Requested Scope

Separate literal source-code interpretation from prose/markup transformations and separate publication secret decisions from conservative diagnostic redaction. Add official local-only `ocr-ci dlp-audit` commands for arbitrary textual inputs, selected files and immutable Git corpora, with private reports, exact expectations and reproducible comparisons. Expand #282 only with independently constructed synthetic examples. The extra operator-provided corpus supplies local research evidence only: its identity, locations, contents and identifiers never enter public source, plans, issues, fixtures or PRs.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Reproduce #282 through source proof, projection and local reporting; keep native analysis and incomplete publication visibly distinct | WQ-01, WQ-03 | done |
| REQ-002 | Official local-only offline audit CLI for snippets, file sets and Git snapshots, using production DLP and code admission rather than another detector | WQ-02 | done |
| REQ-003 | Private snapshots/reports/expectations outside source trees; HMAC identities, explicit selections, no target-owned allowlist and no secret-bearing console output | WQ-02, WQ-05 | done |
| REQ-004 | Fix confirmed reference-expression and representation false positives without project-specific identifier exceptions, broad source exemptions or weakened literal-secret/PII checks | WQ-03 | done |
| REQ-005 | Broader synthetic regression/property matrix, real producer-consumer checks and truthful corpus classification rather than coverage or raw-hit targets | WQ-03, WQ-04 | done |
| REQ-006 | One aggregate Security scan, ordinary actual own-tool acceptance with a real PR diagram, then full repeated corpus scans and final quality | WQ-04 | done |
| REQ-007 | Signed feature PR and development verification complete; release preparation and archival complete, with required release-PR delivery and external reconciliation under Post-Close Delivery | WQ-01, WQ-05, WQ-06; Post-Close Delivery | out_of_scope |
| REQ-008 | Required removal of task-owned raw snapshots/spools and verification of absence after external acceptance; retain only source-free reports and synthetic regressions | WQ-06; Post-Close Delivery | out_of_scope |
| REQ-009 | Review CI/local coverage ownership and stale 80% floors; verify real CI-equivalent coverage and headroom before setting synchronized thresholds | WQ-03, WQ-04 | done |
| REQ-010 | After Security results, reconcile the repository threat model with actual audit, worker, private-output and release boundaries | WQ-04 | done |

### Explicit Non-Goals

No OCR/model pass during corpus diagnosis or replay; no new review engine, forge adapter, hosted corpus, production allowlist, country assumption, secret verification service, or automatic privacy-policy relaxation. Audit commands are local diagnostic tools, not a GitLab pipeline stage or automatic repository scan, and their reports cannot authorize posting or approval. Do not change result/receipt wire schemas, native coverage or ordinary partial-result exit behavior. Do not import or execute audited projects, initialize submodules, call devices, or acquire private measurements. No website-chat handoff. Do not rewrite previous releases or historical evidence.

### Constraints

- This full plan is the first tracked write. Use codex/ feature branch, signed logical commits and a plan-first draft PR. Keep implementation local until reviewed acceptance is complete; self-review, formatting and staged secret scanning precede every commit/amend.
- Original input text retains independent known-secret, literal-credential, contact and forbidden-source checks. Source proof only enables the interpretation justified by the exact excerpt and safe sink; it is not confidentiality authority.
- Prefer typed context and parsed value roles over lists of benign names, paths, functions, versions or numeric constants. Ambiguous/unproven syntax keeps the conservative decision.
- General-purpose text includes configuration, documentation, logs and extensionless inputs. Common sensitive-material checks do not depend on programming language; source/sink refinements require their own bounded proof.
- All private state is operator-selected outside audited roots and Git worktrees, with private physical directories/files, bounded closed schemas and atomic writes. No automatic reading of an input repository's exclusion configuration.
- Snapshots contain only selected code; keys, dumps, working logs, generated environments and private measurements are excluded from this task's external corpus. Source copies remain local and task-owned until mandatory final cleanup.
- Audit input bounds remain 20000 files, 1 MiB/file, 16 MiB total and 200000 line/file units, with no extension-based exclusion policy. Reject oversize bodies by metadata and nontext content before DLP; record omissions explicitly. Resource revision: expose finite total, per-file and per-Git budgets (defaults 900/60/120 seconds). Use exactly one worker so resource use and cancellation do not depend on a concurrent queue. Bound submissions, retained results and report generation before serialization; incomplete scans cannot pass. These bounds describe retained application data/work, not an exact process-RAM guarantee.
- Real own-tool acceptance is a new hotfix cycle, authorized for at most two successful runs, with qualified OCR, native ChatGPT high, diagram local and aggregate token budget zero. Inspect raw/filtered findings, auxiliary reads and the actual diagram; focused finding corrections follow the documented procedure.
- One aggregate Security diff scan precedes actual own-tool acceptance. Ordinary scoped fixes and docs do not cause another aggregate scan.

### Inputs And Sources

Issue #282; current clean main and published v0.14.2; AGENTS.md and the development, security, release and decision-flow owners; installed planning/lifecycle reference; production DLP/redaction, opaque-code proof, publication projection, shared reporting, private filesystem and Git-reader owners; current regression/property/native/installed suites. Public synthetic examples include an empty-string join bound to token, type/reference bindings, arithmetic byte limits and strict date literals. External detector documentation informs tradeoffs, not an exemption or replacement oracle.

### User Decisions And Answers

The owner requests a complete own-repository DLP pass, an additional mixed-language local corpus with a useful top-ten analysis, synthetic-only public reproductions, a reusable private audit helper, protected private expectation storage and full repeated scans after fixes/review. The owner subsequently selects official `ocr-ci dlp-audit` delivery in this cycle, requires complete command documentation and installed checks, allows amending the unpublished helper commit, and keeps corpus audits outside GitLab/CI automation. General CI coverage ownership/thresholds must be reviewed separately using current measurements. Actual release acceptance remains ordinary own-tool review; offline scans themselves never invoke OCR. The owner authorizes a closed local source snapshot outside repositories and requires its eventual removal. The continuing delivery objective includes that cleanup, even after repository plan archival.

### Completed Baseline State

Clean synchronized main is the published v0.14.2 tree. #282 reproduces: token = empty-string.join(parts) is rejected while its renamed control passes. Real immutable-source proof does not prevent the code excerpt from being omitted; local output still begins Review complete with DLP filtering while all findings remain.

A read-only Git-blob audit at the baseline covers 452 UTF-8 files and 121131 nonempty lines (6.46 MB): 160 file units and 1734 line units have a primary rejection. These counts are not a false-positive rate. Whole files and lines expose different units, and intentional negative fixtures remain expected detections. A separate local corpus confirms the need to replay actual source-proof/admission context: many raw markup hits already pass the production code path. No private source snapshot has been persisted by these diagnostic checks; retained diagnostic artifacts contain metadata/fingerprints only.

### Current Work Queue

| Item | Requirements | Work | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-001, REQ-007 | Materialize and critique full plan, reconcile state, signed first push/draft PR, issue/milestone scope with synthetic examples | done |
| WQ-02 | REQ-002, REQ-003 | Implement/test private audit CLI, worker, snapshot/expectation/report/compare lifecycle; curate safe source selections and capture complete baseline before changing DLP | done |
| WQ-03 | REQ-001, REQ-004, REQ-005, REQ-009 | Implement typed source/rendering contexts, structural secret classification and clear two-axis reporting; add synthetic regressions/fuzzing, reconcile coverage guards and update public contracts | done |
| WQ-04 | REQ-005, REQ-006, REQ-009, REQ-010 | Aggregate review, one Security scan and threat-model reconciliation, qualified actual self-review/diagram and scoped corrections; repeat both full corpora, review every transition and complete final quality with measured threshold headroom | done |
| WQ-05 | REQ-003, REQ-007 | Feature PR #283 with exact admitted diagram, protected CI/merge and development verification complete; release metadata, notes, pins and checked archive prepared | done |
| WQ-06 | REQ-007, REQ-008 | Required release-PR delivery, stable external verification, issue/milestone/site, clean main and verified raw cleanup under Post-Close Delivery | out_of_scope |

### Locked Decisions

**DLP boundaries.** Keep diagnostic redaction conservative. Publication uses explicit semantic detector decisions, sharing candidate rules rather than inferring a secret from any redactor rewrite. Bind source interpretation to the existing exact-source proof and safe literal renderer. Distinguish prose, fenced source and fixed renderer-owned diagram labels. Only proven computational operators can avoid Markdown deletion; a scalar parsing as an expression supplies no authority. Configurations, documents, logs and other data remain first-class inputs, with conservative decisions for ambiguous contacts. Keep independent security canonicalization, whole-unit sensitive-value checks and forbidden attribution. No blanket exemption for code or model-chosen context.

Use bounded standard-library syntactic analysis of proven Python source to classify declarations, reference/call/slice/keyword expressions, empty constructions and non-value defaults. Every waived generic candidate must map to the proven syntax and contain no credential literal material. Nonempty literals, embedded values, comments not covered by a valid syntax proof, unknown syntax and unsupported language refinements remain conservative. Other languages retain conservative credential and ambiguous-number handling; this is not a claim of universal language semantics. Parsed technical literal corrections require complete valid grammar and explicit contact priority, not repository-specific names. No new third-party runtime engine is selected: replacing the detector does not solve the proven source/sink mismatch and introduces different precision/recall tradeoffs.

Syntax qualification depends on complete content, never a filename suffix. A
contradictory interpreter closes refinement; ambiguous standalone data remains
strict. Any nonempty literal in the published excerpt, including mapping keys,
disables key waivers because alias/default/factory dataflow is not proved.
Text-bound contexts remain in memory with a four-file source-analysis cache.
Audit fast paths must check both prose and literal sinks rather than inferring
one from the other. Independent security views normalize compatibility Unicode
before removing markup. Only source-proven numeric computation retains its
operators; strings, templates, annotations and arbitrary data do not supply proof.

**Reporting.** Show native analysis and publication health separately whenever public fields/findings are omitted: analysis complete cannot imply accepted complete publication. Preserve native coverage, retained/omitted counts, partial/budget/failed precedence and private-only sanitization. Diagram-only omission stays optional. Share provider-neutral presentation; provider writes and approval rules remain with their existing owners. Ordinary review exit behavior and persisted identities remain unchanged.

**Audit tool.** Add `ocr-ci dlp-audit` with cohesive `src/ocr_toolkit/dlp_audit/` owners and no duplicate script entry point. Support scan from an immutable Git ref, explicit file set/NUL file list, stdin snippet, or a captured snapshot; compare baseline/candidate runs; annotate exact expectations; and clean owned raw state. Keep parser/dispatch separate from acquisition, private state and evaluation. Launch a fixed installed module through isolated Python; no provider setup, review execution or GitLab pipeline integration. Call the installed production scanner without importing the target or using its configuration. Evaluate raw text and, where justified, the real existing-code proof/projection path. Record the primary closed reason per unit, proof eligibility and projection omissions; do not pretend to collect every independent detector match. Cache bounded source analysis per immutable file, process batches by file, and infer passed units only from verified complete evaluation counts. Qualify the installed wheel/sdist command outside checkout and independently review the changed public entry point before amending the local commit.

Default reports are private JSON plus Markdown with locations, counts, primary detectors, top-ten groups and local source locators; they do not embed matched values or source snippets. Console output is source-free. Capture Git identity or descriptor-checked filesystem bytes, reject moving snapshots, do not follow links or open devices/FIFOs, and explicitly account for binary/oversize/gitlink/unsupported inputs. New audit output has its own closed diagnostic schema, not a toolkit receipt. Scanner identity, corpus selection, profiles and effective secret-set fingerprints bind comparisons; raw environment secrets are never stored.

**Expectations and comparisons.** Keep annotation state outside repositories. Use a private per-state HMAC key and identities bound to corpus, exact file content, unit/span and sink role; no plaintext values or production suppression rules. Unknown schemas, changed inputs/configuration and invalid keys fail closed. Labels distinguish expected protection, confirmed benign input and deliberately conservative ambiguity; they never stop scanning. Compare all input units, including previously passing ones, with the same complete snapshots/profile. Newly rejected units, newly admitted protected units and unexplained reason changes require review. A smaller hit count is not success. Scan/compare use exit 0 only for complete satisfied expectations, 1 for complete results needing triage or showing a regression, and 2 for incomplete/invalid execution.

**Privacy and cleanup.** Publish only independently generated synthetic fixtures and conclusions; never copy and rename private source/key material. Before any persistent source capture, check the selected files against their provenance and privacy owners; exclude complete secret-bearing/generated-profile or measurement files instead of sanitizing input and calling it the original corpus. Freeze the accepted selection and establish its unchanged-scanner baseline. Keep each task's snapshot inventory and recovery pointer private. Final cleanup removes exactly owned source copies and raw spools after external delivery checks, preserves original inputs and verifies absence. Only source-free reports/expectations and synthetic regressions may remain; cleanup failure prevents completion. Interrupted work retains explicit cleanup ownership rather than an unrecorded raw snapshot.

For inputs unsuitable for source copying, support metadata-only explicit file selections. Persist exact private content identities, evaluate original bytes only in memory, and recheck every original before/after each replay. Drift or unavailable originals invalidate comparison. This preserves complete corpus evaluation without treating an excluded raw copy as an excluded scanner input.

**Resource revision before helper amendment.** Load and evaluate exactly one source at a time, with no queued source-bearing requests. A timed-out file is omitted and later files may proceed within the total budget. Keep source/corpus preflight and final fingerprint checks as bounded per-file passes. Account atomically by file: discard a capped file's partial results, exclude its units, and mark it plus unprocessed inputs incomplete. Cap hit records and encoded bytes while generating/accepting them, reserving room for errors, envelope and HMAC. The explicit worker lifecycle kills and reaps its owned peer on timeout, invalid/stale framing, cancellation and scan teardown; failed peers restart only for later files. Source-bearing request locals are released between files; no executor or global cache outlives the operation. Distinguish closed deadline, output, launch, worker and observed storage/allocation failures; an unexplained killed worker is not proof of OOM. Preserve recoverable raw ownership even when a report cannot be saved. Enforce audit's aggregate byte budget before Git blob transfer through bounded batches that respect the reader's own entry cap. Git-reader timeout overrides are opt-in for audit; existing consumers retain defaults. Record effective execution settings in a closed run contract, keeping complete same-input/scanner-profile/secret-set comparisons independent of resource-setting differences. Fixed one-worker execution is intentional: configurable concurrency is unnecessary for the local diagnostic contract. If the unpublished run schema changes, rerun the unchanged scanner over the preserved corpora rather than adding legacy APIs. Reuse one isolated worker through a bounded request/response protocol owned by this scan, with a fresh identity and timeout for each file. This replaces the original per-file launch decision after measured import overhead. No global worker/cache, hardware auto-tuning or automatic corpus CI job.

### Verification

- Independent safe/reference versus literal/embedded-secret controls; secret-name renaming invariance for nonsecret proven expressions; exact environment values, short credentials, PII and forbidden values still block in every applicable representation.
- Declarations, calls, slicing, keyword arguments, empty/default values, concatenated/interpolated/encoded values, malformed/partial syntax, Unicode byte/code-point positions and parser/resource limits. Failed/stale/mismatched proof never grants interpretation.
- C/other-language literal syntax, includes/generics, arithmetic and renderer profiles; existing source-proof successes stay successes. Unresolved numeric/credential ambiguities retain explicit conservative expectations.
- Real Git/source-proof -> projection -> persisted result/admission -> local/GitLab rendering handoffs. Cover all findings retained with one code field omitted, zero retained findings, native partial/budget states, private-only cleanup and optional diagrams.
- Audit hostile paths, Unicode/newlines, symlinks/hardlinks, FIFOs/devices, changing files, non-UTF8 and limits; shadow packages and no target execution; worker timeout/crash/malformed output; secret-bearing failures cannot spill values.
- Private state/report permissions, exact HMAC scope, stale/tampered/unknown/duplicate-key baseline rejection, complete unit accounting, comparison of previously passing units and idempotent ownership-checked raw cleanup.
- Default 100-example CI properties and independent 1000-example local seeds; old synthetic DLP corpus plus newly minimized independent cases, not implementation-mirroring assertions. Require at least 90% branch-aware coverage for each audit-helper module independently, with meaningful failure/resource/privacy tests. Independently review the completed helper and fix findings before its own signed local commit and corpus baseline use.
- After reviews/fixes, rerun every selected unit in both captured corpora and the new candidate repository. Classify all unexpected transitions, retain source-free summaries and repeat affected replay after material DLP changes. Final quality, installed/native checks, privacy and dependency gates bind the final runtime.
- Protected feature/development and stable release workflows, registry/provenance/Python installs, immutable receipt/tag/Release and independent issue/milestone/site/main readback; mandatory raw-state cleanup before final completion.

### Latest Validation Results

2026-10-30: read-only diagnosis is complete enough to establish #282's source/projection defect and the audit's need for sink-aware interpretation. Both initial corpora scans complete without OCR. Their results are private diagnostic evidence, not accepted ground truth or publication eligibility. The repository was unmodified before this plan. Signed plan commit 3a2ad25 is pushed as draft PR #283; #282 has synthetic-only scope additions and milestone v0.14.3. Plan/instruction and staged/tree/history privacy gates plus the dependency audit pass. Runtime remains byte-identical to v0.14.2; no private source snapshot has yet been captured.

2026-10-30: the audit helper and its documented source-free/private lifecycle are implemented. Independent review found a prose/code horizontal-tab mismatch and quadratic per-hit file lookup; both were corrected and independently rechecked with the two regressions passing. The helper/quality focused suite passes 76 tests; individual branch-aware coverage is cli 92%, corpus 94%, scanner 92% and state 99% (94.23% overall). Local guards enforce each module's 90% floor; no dedicated hosted audit/coverage integration is authorized. Extended 1000-example property qualification also passes. Public privacy and plan/navigation checks pass. Curated-copy and full metadata-only input modes preserve the distinction between retaining source and evaluating it. Complete helper-owned corpus baselines are the next step, before any DLP runtime change.

2026-10-30: signed helper commit 39f6e97 is local only. Complete production baselines now cover the entire immutable public tree (121583 whole-file/nonempty-line units in two roles) and the full additional code selection; the latter persists metadata only, with no private source copies. Rejections remain untriaged, not false-positive counts. Public raw copies have authenticated cleanup ownership. The owner selects official local CLI delivery; migrate the reviewed implementation, document and qualify it, then amend this unpublished commit. General CI coverage review is newly authorized; no corpus-audit pipeline job is authorized.

2026-10-30: official command naming is `ocr-ci dlp-audit`; obsolete script/namespace paths are removed. Native focused checks and type/lint checks pass. Clean wheel/sdist installation passed the short synthetic installed-command/worker/cleanup smoke before subsequent resource fixes. Independent reviews now use GPT-6 Astra high as requested. Its three concrete findings (open stdin deadline, unhandled Git timeout, unsupported-member completeness forgery) are fixed; its batch-deadline follow-up is fixed in the canonical reader, with 149 focused behavioral checks passing. The full CI-equivalent suite passes 3512 tests with 41 skips and 88.58% total coverage; audit modules individually exceed 90%, result/preflight are about 87%, posting about 82%, and the shared repository reader about 82%. The 80% gates therefore require differentiated changes and meaningful weak-path tests, not a blind global raise. The owner requests resource-aware large-project behavior and content-based binary handling; finish that resource revision and its independent review before amending the helper commit. Successful real own-tool acceptance runs in this hotfix cycle remain zero; an invalid reviewer CLI probe returned code 2 and is not acceptance evidence.

2026-10-30: official `dlp-audit` implementation is complete, including the resource revision. Serial isolated execution replaces the eager request queue; adjustable overall/file/Git deadlines, binary/oversize preflight, bounded Git metadata/blob transfer, incremental rejection/document budgets and atomic capped-file omissions are implemented. Independent Astra high review and its focused resource follow-up have no outstanding confirmed findings. All 175 focused tests pass, including actual timeout/cancellation kill/reap, hostile state, CLI, Git and binary boundaries. Individual branch-aware coverage is CLI 96%, corpus 92%, scanner 93%, state 99%, execution limits 100%; the 1000-example property profile passes with an independent seed. Ruff, mypy, Bandit, privacy and plan/instruction guards pass. Clean wheel/sdist installation and actual installed CLI/worker/cleanup checks pass (3 installed-suite tests). The helper was amended as signed local commit ddfc8cf; signature verification passed and the worktree was clean before corpus replay. No DLP algorithm correction has been bundled into this helper slice. Corpus replays using the final run schema follow the commit, before source-semantics changes.

2026-10-30: source-aware DLP and two-axis reporting are signed as 81af7a6;
the helper's call-time default-budget correction is included in signed 75fe7d2.
Focused source/property, reader/collector/quality and reporting/DLP checks pass.
The single aggregate Codex Security diff scan covers every one of the 20 changed
source inventory files in the full published-base-to-81af7a6 range, with complete
static coverage, zero findings and no deferred work. A fresh independent
architecture model confirms the actual boundaries. After those results, the
repository threat model is reconciled with the explicit local audit, trusted
same-user worker, private state/original-preserving cleanup, local report delivery
and protected-base release authorization. This documentation update changes no
runtime; no second aggregate Security scan is required. Successful actual
own-tool acceptance runs remain zero; final corpus replay and quality are pending.

2026-10-30: the first actual Astra/high review of published base through 301d4ae
completes 42/42 files, without native warnings, but is not accepted: no diagram
submission occurs and publication retains two of five findings. All three hidden
findings are inspected in the private raw result and DLP journal. Their prose
contains phone or named-credential examples; those omissions follow the current
policy, while their underlying findings reproduce real defects. Missing cases
were unmatched unlabeled contact markup, known passphrases changed by token-name
normalization after decoding, and collision of an ambient secret with audit's
synthetic wrapper text. Two additional findings expose repeated package hashing
per file and repeated whole-source preparation per line. Correct all five at
their shared owners, extend general representation/property and actual worker
tests, then requalify the native diagram path before the remaining actual run.
The owner explicitly retains a single aggregate Security scan.

2026-10-30: post-review source/representation qualification passes 545 tests and
properties at 1000 examples per property; focused audit/source checks pass 284.
Each audit module measures 92-100% branch-aware coverage, source syntax 93%,
and text-bound contexts 100%. Official native diagram handoffs pass all 24
group/round/format cases; 67 SDK/bootstrap/schema checks also pass. Full captured
replays evaluate 121583 and 19050 units. All 80 newly admitted role units and 23
changed reasons are reviewed and privately classified: no new rejection,
unexplained admission or lost confirmed protection. Unchanged untriaged
observations remain explicit (3490 and 277), not a claimed precision/recall rate.
The overall final quality gate is running; positive actual diagram acceptance,
post-acceptance replays, candidate-tree diagnosis and installed artifacts remain.

2026-10-30: the second actual ChatGPT/Astra high run of 72abb603..b4cfbb1 is
accepted: 51/51 selected files, zero raw/delivered findings, no DLP omissions and
one admitted twelve-node flowchart. All 147 tool calls are retained. The one
guessed missing reporting path is recovered by successful reads of the real
local provider/outcome owners. The unchanged oversized lock and the soft
bootstrap recommendation remain explicit, with no budget or exhaustion warning.
No more actual model runs are authorized in this cycle. Candidate-tree audit
evaluates 126855 units completely; added synthetic controls and conservative
data/prose decisions remain visible. A stale prompt-title property is corrected.
Seven tests in the first full gate collided with the concurrent actual review's
repository lock; repeat the gate sequentially after that review. Post-acceptance
corpus replays and final quality are running. Runtime remains b4cfbb1.

2026-10-30: the sequential final quality gate passes: 3747 tests, 47 skips and
357 subtests, 88.79% total coverage and every scoped floor. Result/preflight is
87%, posting 82%, each audit module 92-100%, source syntax 93% and text contexts
100%. Clean wheel/sdist installations and installed local/MCP/audit checks are
included. Extended bootstrap properties also pass after correcting the stale
title. Remaining local acceptance work is the post-quality corpus replay; builds
and scans are serialized because generated version metadata participates in
scanner identity. No runtime change follows the accepted actual review.

2026-10-30: both post-quality captured replays are complete. Comparisons against
the reviewed candidates have zero decision changes, new admissions/rejections,
unexplained transitions or lost confirmed protection. The unchanged untriaged
populations remain explicit. Local implementation acceptance is complete;
continue with the signed feature push and exact admitted Mermaid in PR #283.

2026-10-30: feature PR #283 is merged as a58be92 after the complete protected
Linux/macOS Python matrix. Development TestPyPI workflow 41079397775 succeeds,
including immutable published-artifact/provenance/install verification. Release
0.14.3 metadata, authorization for #282, next marker 0.15.0, example pins and
Towncrier notes are prepared. The release-index contract is checked after the
atomic archive transition: all 156 focused release/environment/documentation
checks pass, with valid lifecycle and instruction contracts. Stable publication
and raw cleanup remain required external delivery.

### Risks And Recovery

Source provenance is not permission to publish a secret: reject unmapped candidates and scan all original/encoded sensitive material. A lexer/normalizer can create a false phone or hide a real one: choose representations by the actual sink and replay strong counterexamples. Broad expectation patterns can conceal new defects: bind them to exact private input identity and keep scanning. An altered corpus/environment is not a detector regression or improvement: fail comparison as incomparable. Private state can leak through reports/errors or cleanup: use closed output fields, fixed private destinations and ownership-checked removal; preserve originals. On a failed check retain value-free diagnostics and the exact resume action, repair the narrow owner and rerun the affected checks. No additional aggregate Security scan for ordinary follow-up fixes.

### Resume Point

No unfinished in-scope repository work remains. Required release-branch signing,
push, exact Release v0.14.3 PR creation, protected CI/merge, publication, external
readback and verified raw cleanup are classified under Post-Close Delivery.
This archive records the prepublication repository handoff; the continuing
release objective remains active until external acceptance and cleanup.

### Plan Fidelity Check

- [x] Every requested outcome, privacy correction, review choice, replay and snapshot cleanup maps to a requirement and queue item.
- [x] Source semantics, rendering, diagnostic redaction, audit state and provider outcomes have explicit owners and failure boundaries.
- [x] The helper uses production decisions and source context; initial raw-hit counts are not ground truth or release gates.
- [x] Unsupported/ambiguous cases, resource limits, private annotations and post-review replay are explicit.
- [x] Release archival and continuing external delivery/cleanup are retained without a later closure PR.

### Reconciliation Check

- [x] Baseline is current clean main with published v0.14.2; prior evidence remains historical.
- [x] Public material contains synthetic examples only; no private corpus identity or source is retained here.
- [x] Final implementation, actual decisions, docs and acceptance evidence agree.

### Closure Gate

- [x] Implementation and applicable final-runtime verification are complete.
- [x] Security/own-tool findings and all unexpected corpus transitions are resolved; an actual admitted PR diagram exists.
- [x] Protected feature merge and development publication are verified.
- [x] Release PR prepares authorization, markers, notes, pins and checked full plan archival/reset.
- [x] Required external publication/reconciliation and raw snapshot cleanup are truthfully classified under Post-Close Delivery.

### Post-Close Delivery

The approved sequence and docs/release.md require archival/reset in the release PR before publication. Required work outside the closed repository plan remains: release-PR signing/push/protected CI/squash merge, stable registry/provenance/install/tag/immutable Release/receipt verification, Actions-owned issue #282 closure, milestone v0.14.3/site and independently clean main, then removal of every owned raw snapshot/spool/build/install copy with verified absence and preservation of originals. This higher-priority release boundary justifies out_of_scope for REQ-007's remaining external part, REQ-008 and WQ-06; it neither waives nor completes the continuing delivery objective. No stable external fact or cleanup is claimed complete by this prepublication snapshot. No follow-up repository closure PR or website-chat handoff is authorized.

### Handoff Notes

No in-scope work remains. Implementation and verification are complete. Required external delivery and verified raw cleanup are classified under Post-Close Delivery. Private diagnostic material remains outside public artifacts.

## Recently Completed

- [x] 2026-10-30: Completed Toolkit 0.14.2 compact bootstrap, diagram-only reports and DLP corrections; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-2-compact-bootstrap-diagram-only-reports-and-dlp-corrections.md).
- [x] 2026-10-29: Completed Toolkit 0.14.1 grouped diagrams and private debug qualification; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-1-grouped-diagrams-and-private-debug-qualification.md).
- [x] 2026-10-29: Completed Toolkit 0.14.0 range identity, typed diagrams, DLP qualification and Python 3.15; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-0-range-identity-typed-diagrams-dlp-qualification-and-python-3-15.md).
- [x] 2026-10-25: Completed Two-day GitHub Actions retention; [full archived plan](docs/engineering/execution_history/plans/2026-10-25-two-day-github-actions-retention.md).
- [x] 2026-10-23: Completed Toolkit 0.13.1 partial review of changes containing gitlinks; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-1-partial-review-of-changes-containing-gitlinks.md).
- [x] 2026-10-23: Completed Toolkit 0.13.0 protected default-policy fallback for single-MR review; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-0-protected-default-policy-fallback-for-single-mr-review.md).
