# Execution Plans

## Active Plan: Toolkit 0.14.4 systematic DLP corrections and diagram source validation

plan_schema_version: 2
Status: active
Owner: root
Last Updated: 2026-10-31

Release classification: release-required; target v0.14.4; next development line remains 0.15.0.

### Goal

Fully reconcile the remaining offline DLP observations, correct their confirmed causes and false negatives, fix large-source diagram references (#285/#286), and deliver v0.14.4 through protected publication and independent external reconciliation.

### Plan Origin

`plan_mode_approved`

### Requested Scope

Examine both existing authenticated corpora completely by causally justified groups, not by a raw detection-count target. Improve the production DLP representation/candidate boundary and existing local audit reports, qualify a small model-free parsing stack, implement bounded immutable-source metadata for diagram references, and verify real producer/consumer handoffs. Repeat both complete audits after corrections and review; preserve original projects and remove task-owned raw copies. Finish the repository plan inside the release PR and verify stable external delivery afterward.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Full private causal disposition of all 3790 retained observations, including the 3767 previously unadjudicated entries; no unexplained remainder | WQ-02, WQ-06 | done |
| REQ-002 | Correct confirmed FP/FN causes across code, configuration, documentation, logs and ordinary text without corpus-specific exemptions | WQ-03, WQ-05, WQ-06 | done |
| REQ-003 | Qualify Mistune/regex/emoji with bounded work, supported-Python binary installation, dependency identity and resource evidence | WQ-03, WQ-05 | done |
| REQ-004 | Improve existing private audit reports; preserve exact annotations and closed persisted formats; no new CLI command or CI stage | WQ-02, WQ-03 | done |
| REQ-005 | Independently bounded immutable source metadata validates diagram references above the evidence-size limit, at admission and publication | WQ-04, WQ-05 | done |
| REQ-006 | Optional diagram/MCP/rendering failure never changes findings, coverage or approval eligibility; exact admitted Mermaid accompanies feature PR | WQ-04, WQ-05, WQ-06 | in_progress |
| REQ-007 | Meaningful branch/property/boundary coverage, one aggregate Security scan, threat-model reconciliation and real own-tool acceptance | WQ-05, WQ-06 | done |
| REQ-008 | Private-safe source, immutable inputs, bounded acquisition and owned raw-source cleanup with originals unchanged | WQ-02, WQ-06, WQ-08 | pending |
| REQ-009 | Signed draft-plan PR, local reviewed development, protected feature/release delivery and plan archive in the release PR | WQ-01, WQ-07, WQ-08 | in_progress |
| REQ-010 | Select a readable flowchart orientation automatically in the pure renderer; preserve sequence semantics and MCP/receipt grammar | WQ-04, WQ-05, WQ-06 | done |

### Explicit Non-Goals

No AI model, pretrained classifier, model download, remote classification, DNS/deliverability check, default phone region, repository/name/extension allowlist, general graph subsystem, additional forge adapter, new audit CLI command or pipeline stage. No inference that every audit hit is a bug. No reduction of receipt/range identity, source-proof authority, configured-secret protection, or existing sensitive-material checks. No promotional-site implementation or cross-service handoff.

### Constraints

Respect source-specific disclosure limits. Strictly private additional validation
inputs, locations, examples, counts and outcomes remain outside public artifacts,
including this plan, issues and release notes. Use metadata-only authenticated
inputs for that validation, with private bounded selections and reports.

The first repository write materializes this plan. Every logical commit receives semantic self-review, applicable formatting/tests and staged public-content scanning; Python commits require repository-wide clean format checking. First signed push opens a draft PR; subsequent feature push follows complete local development and acceptance. Preserve pure reporting and provider-neutral core behavior. Public records contain only synthetic cases and aggregates, never private project identities, source, locators, hashes or internal coordination details. Raw snapshots and exclusions stay private outside input roots; do not execute/import audited source. Existing audit schemas/annotation semantics and review receipt schemas stay readable and unchanged. Keep original scanner configuration and input populations comparable; fewer detections alone are not success.

### Inputs And Sources

- Issues #285 and #286; current protected main 17254d2202fd6d4c7d77c1d8d4b222970938c0fb, stable 0.14.3.
- Canonical project principles, development/release guides, review-context/federation contracts, decision flow and private-audit documentation; installed planning/instruction lifecycle references.
- Existing authenticated private audit state, source-free census and causal grouping reports; the current local ignored recovery pointer owns its location. Revalidate inputs before depending on source-derived conclusions.
- Official Mistune, regex and emoji documentation/metadata; isolated synthetic probes on Python 3.14/3.15. Other libraries were screened jointly against current DLP, Python support, resource cost and trust/sink requirements.

### User Decisions And Answers

Perform the full causal analysis, fix confirmed causes and publish a release including the second open issue. Select one coherent dependency approach using speed and memory as well as correctness; avoid models/classifiers. Preserve general-purpose behavior beyond programming languages. Private examples must be reconstructed synthetically. Repeat both project audits after corrections/review. Security scanning runs once for the aggregate runtime diff before own-tool acceptance. Normal own-tool review requires an admitted diagram and that exact Mermaid in the PR. Archive/reset the plan in the release PR, without a later closure PR.

### Completed Baseline State

Both original repeat audits completed with unchanged decisions relative to the reviewed 0.14.3 candidate. Retained observations: toolkit 3513 and private corpus 277; 23 toolkit entries were individually adjudicated (11 expected protection, 12 conservative ambiguity), leaving 3767 without individual verdicts. Deduplication gives 1906 line locations and 390 whole-file/role probes; 360 file probes repeat a child-line reason, 30 need cross-line/proof-budget analysis. Primary families total phone 1094, credential 858, markup policy 1354, email 430, controls/invalid text 54. These are observations, not a precision or defect count. Prior raw snapshots were removed; source-free state remains private.

### Current Work Queue

| Item | Requirements | Work | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-009 | Materialize/review plan, signed commit/push, draft PR and issue refinements; draft PR #287 opened from signed plan commit 1f99353 | done |
| WQ-02 | REQ-001, REQ-004, REQ-008 | Source-bound baseline causal ledger reconciles all 3790 entries; existing audit-report improvements remain in WQ-03/WQ-05 | done |
| WQ-03 | REQ-002, REQ-003, REQ-004 | After WQ-02: implement representation-aware DLP, confirmed regressions, existing audit report improvements, dependencies and scanner identity | done |
| WQ-04 | REQ-005, REQ-006, REQ-010 | Shared bounded streaming source metadata, closed diagnoses and pure LR/TB selection implemented; focused real-Git/result/receipt/publication tests pass | done |
| WQ-05 | REQ-002, REQ-003, REQ-005, REQ-006, REQ-007, REQ-010 | After WQ-03/WQ-04: integrate callers, fuzz/inverse tests, >=90% affected component coverage and installed/resource qualification | done |
| WQ-06 | REQ-001, REQ-002, REQ-006, REQ-007, REQ-008 | After WQ-05: aggregate self-review, one Security scan, threat-model review, actual own-tool review and repeat corpora/cleanup | done |
| WQ-07 | REQ-009 | Final local gates passed; attach exact diagram, push signed feature, verify protected CI/merge and development publication | in_progress |
| WQ-08 | REQ-008, REQ-009 | After WQ-07: signed release/v0.14.4 PR with archival/reset; stable publication, external closure and cleanup verification | pending |

### Locked Decisions

**Module map and profiling.** Group the detector in the one-level `context/dlp/` package, keeping the existing import facade and no parallel legacy file. Candidate, representation, credential-role and admission owners remain separate from acquisition, private audit state and pure reporting. Keep agent routes, development owner map and coverage paths synchronized. Profile actual full-audit workers and compare end-to-end time/CPU/RSS with 0.14.3; component timings alone do not complete acceptance.

**Causal ledger.** Keep original observation identities and role/proof context. Split mixed groups and verify every member against the claimed common cause and additional sensitive material. Use existing exact labels (expected-protection, confirmed-benign, conservative-ambiguity); record confirmed false negatives as synthetic regressions and inverse controls. A detector family alone cannot justify a verdict. Unsupported interpretation remains conservative with an explicit rationale, not an unexamined parking label.

**DLP architecture.** Keep candidate extraction, representation interpretation and final admission separate and pure. Trusted caller metadata identifies actual Markdown, literal source, plain data or diagram labels; a filename or successful parse cannot authorize disclosure. Check original and applicable decoded material independently, including known secrets and forbidden origins. Literal rendering prevents formatting activation, not confidentiality checks. Preserve national/unlabelled phones, unusual phone-shaped fixtures, .invalid email domains, low-entropy configured secrets and adjacent sensitive values. Correct valid technical date/list treatment, credential masks/references, mentions, Unicode email and valid presentation sequences through structural roles rather than accumulating lexical exceptions. An arithmetic parse alone is insufficient to waive a phone candidate. A map named permissions supplies no caller-qualified application schema; literal access-level values remain conservative. Only complete empty/masked values and closed symbolic references establish absent material. No configuration-role fallback manufactures code authority.

**Dependencies and resource bounds.** Qualify Mistune 3.4.0 AST without renderers/plugins, regex 2026.9.29 for narrow bounded operations/Unicode and emoji 2.16.0 static standard sequence data; stdlib HTMLParser supplies bounded HTML events. Do not rebuild text from emoji tokens: unmatched joiners can be skipped. Whole original checks and exact accepted spans remain authoritative. Extend the documented runtime-dependency exception only at this parsing boundary; pure reporting never imports it. Preserve external text budgets, limit nesting to 20 and enforce a shared 32768-token budget during construction, not afterward. Bound derived views/expansion as they are created; exhaustion is explicit limit, never admission. Prepare source once per file, avoid cross-file source retention and include actual dependency versions in scanner identity. Existing audit reports gain grouping/proof/aggregate visibility without new CLI commands or persisted review-schema changes.

**Diagram references.** The production Git reader owns a streaming immutable regular-blob text-metadata operation: exact object binding, strict incremental UTF-8, NUL rejection, byte count and LF line count including final non-LF line. Never follow symlinks/gitlinks or consult mutable checkout content. Use at most 5000000 bytes/blob, 32000000 aggregate bytes and 30 seconds for one diagram's reference-validation session; chunks <=65536 bytes. Cache metadata by immutable object, not whole sources. Share the adapter between initial admission and GitLab revalidation. Leave evidence/source-proof reads at 256000 bytes. Pure admission receives typed metadata; reporting has no Git/DLP orchestration. Use existing budget/unavailable/reference reasons with source-free diagnostics; do not change receipt schemas. Any auxiliary failure omits only the diagram.

**Orientation.** Added during implementation: pure deterministic LR/TB selection condenses cycles, ranks the resulting graph and estimates displayed node/condition widths, including Unicode. Prefer LR within 100 estimated display columns; otherwise select TB only when its estimated width is smaller. Preserve node/edge/message order and fixed Mermaid grammar. No model-selected direction, additional model pass, configuration or receipt fields. Sequence diagrams retain standard time ordering. Synthetic chains, branches, cycles and permutations qualify the estimator; final own-tool acceptance also checks the actual graph.

**Documentation and delivery.** Synchronize public contracts, audit docs, decision flow, evidence matrix, dependency-boundary rationale, changelog and backlog; preserve historical artifacts. The feature PR receives the exact admitted self-review Mermaid without debug text. Stable marker 0.14.4, next marker 0.15.0, signed release branch and exact PR title Release v0.14.4. Release authorization references both issues without premature closing keywords. Release CI owns issue closure after immutable receipt readback. Existing site notification remains the only release-site path.

### Verification

- Regressions and inverse/metamorphic properties cover original/encoded HTML/Markdown/Mermaid, Unicode controls and valid emoji, masks/empty/template/reference credentials, numeric separators/dates/versions, invalid networks/ports, cross-line data, stale proof and allocation/work bounds. Include general text/config/log and non-Python-only sources.
- Hypothesis: 100 examples/property ordinary CI, 1000 extended local with independent seeds; retain minimized synthetic failures. New and affected DLP/audit components receive >=90% branch-aware coverage without lowering existing higher results; inspect regex semantic alternatives too.
- Actual caller tests cross context/store/federation, local/GitLab finding projection, persistence, source proof and both diagram variants. Hostile persisted data is rejected atomically; optional omission cannot alter findings/coverage/eligibility.
- Real temporary Git tests cover 256000/5000000-byte boundaries, first/last line, empty text, trailing LF/CRLF/Unicode separators, split UTF-8, late NUL/invalid UTF-8, symlink/gitlink/stale head, shared aggregate/deadline limits and killed/reaped processes.
- Repeat both complete authenticated corpora after fixes/review. Explain each new admission/rejection, changed reason and protection loss; confirm original inputs unchanged. Benchmark end-to-end CPU/time/RSS against 0.14.3, adversarial inputs and constrained workers; no unexplained regression.
- Clean installed wheel/sdist outside checkout and binary-only hash-locked dependencies on supported Python/platform targets. Run applicable instruction, quality, public-content, complete-range secret and dependency gates.
- One aggregate Security diff scan of the finished runtime range, then threat-model reconciliation; focused fixes/tests afterward. Actual ChatGPT high own-tool acceptance uses --max-tokens-budget 0, OCR_REVIEW_DIAGRAM_MODE=local, private diagnostics and toolkit Rules. Plan at most two successful own-tool runs in this new release cycle; inspect all findings/DLP omissions/material auxiliary-read gaps. Budget/context/tool-round warnings or missing admitted diagram fail acceptance. Record used runs explicitly.

### Latest Validation Results

Final runtime is `bb9f2fb`; the strengthened field/reason contracts in `d464c2f`
pass the complete quality gate: 4223 tests, 47 expected skips, 357 subtests and
89.17% total branch-aware coverage. Every individual floor passes. Shared
material classification is 97%, lexical completion 94%, credentials/admission
98%, and audit owners meet their independent 90% floors. Strict typing covers
167 runtime files. Extended 1000-example profiles used independent seeds;
composed properties cover encoding order, quote runs, comments, multiline
continuations, Unicode identifiers and production publication. Minimized
counterexamples remain synthetic regressions. Coverage and example counts do
not establish universal precision or recall.

All 3790 original retained observations have source-bound causal dispositions:
1264 confirmed benign, 1921 expected protection and 605 conservative ambiguity.
Revision history preserves corrected initial verdicts. Final complete replays
cover the same authenticated 121583 and 19050 units as their baselines. Official
comparisons have zero benign rejection, protection loss, unexplained admission,
unreviewed change, changed unqualified reason or untriaged observation. The
1244/20 new admissions and 39/3 new rejections were individually reconciled;
fewer detections alone are not acceptance. A separate current-code diagnostic
covered 130139 units and reported 3087 role observations, including deliberate
synthetic fixtures and conservative policy restrictions. Its top groups and
changed-source delta were inspected; it is not a zero-finding or fully
adjudicated accuracy claim and does not replace the fixed-population comparison.

The installed final toolkit replay measured 107.70 seconds wall, 106.42 seconds
user CPU and about 153 MiB peak RSS, versus installed 0.14.3's 125.97/122.26
seconds and about 153 MiB. A real Python 3.12 audit worker profile has 499
samples and zero sampling errors; normalization/material checks dominate.
The short profile is supporting evidence, not a throughput guarantee.

One aggregate Security scan of immutable `17254d2..185d7db` reviewed 30 owners
and validated three findings. All were corrected and their installed production
reproducers still reject unsafe input. No aggregate scan was repeated. Actual
own-tool runs `17254d2..58b0bbc` and `17254d2..85a355e` completed 56/56 and 59/59
selected items with zero failed/waived coverage, no budget warnings and admitted
TB flowcharts. Their six findings were inspected, including the two privately
retained publication-filtered findings, and corrected through focused tests and
independent semantic review. The only failed auxiliary reads requested beyond
EOF and were recovered by complete reads. Both original model diagrams re-admit
through current DLP and real immutable Git metadata and exactly match delivered
Mermaid. Aggregate scans used: 1/1; successful own-tool runs used: 2/2.

Clean Python 3.15 wheel and sdist installations, hash-locked binary runtime
installation, pip checks and real installed MCP probes pass outside checkout;
the final Python 3.12 installed wheel/MCP probe passes. Installed audit lifecycle
and raw cleanup pass. The original diagram source/layout real-Git, admission,
receipt and publication slice passed 308 tests with 35 skips; final full-gate
coverage includes those unchanged consumers. Optional omission stays independent
of review outcome. Public contracts, threat model, decision flow, owner routes,
evidence matrix and maintained fuzzing backlog are synchronized. Mixed prose
without a proved credential boundary remains explicitly conservative, not a
claim of actual secret material or a repository-specific exception.

Owned Git source snapshots were removed through the official cleanup command;
metadata-only inputs were revalidated without source copying. Source-free
private state remains private. The obsolete repository dist and unused
project-owned qualification image were removed. Temporary analysis environments,
builds and raw diagnostic spools are removed; only source-free private comparison
state and admitted diagrams remain. PR #287 contains the completed implementation
and exact second-review Mermaid. Hosted Linux CI exposed three oversized pytest
parameter IDs: raw 270000-byte fixtures entered PYTEST_CURRENT_TEST and exceeded
Linux's per-environment-string exec limit before Git could start. Short semantic
IDs preserve the exact fixture bytes and assertions. The corrected 25-test owner
suite passes on macOS and Linux, including a 2-CPU/2-GiB temporary Linux container
that is removed after execution. Runtime is unchanged; no new Security/OCR/corpus
run is justified by this fixture correction. Protected CI/merge, development
publication, final hosted cleanup and stable delivery remain pending.

### Risks And Recovery

Lossy parsers can hide material; always retain independent original checks and use exact positive spans, with conservative rejection on incomplete interpretation. Regex timeouts do not bound unrelated parser operations; construction-time token/nesting/derived-size budgets and adversarial performance tests remain mandatory. New dependency versions must invalidate scanner identity and pass clean installed qualification. Full causal reconciliation may expose additional defects; add minimized cases within these requirements rather than corpus-specific exemptions. Private source availability or fingerprints can invalidate replay: stop that comparison and recover exact authorized inputs, never silently substitute a different corpus. Cancellation must kill/reap task-owned processes and retain explicit snapshot-cleanup ownership. Do not change published 0.14.3 artifacts/tags or force public feature history. Local unpushed fixups may amend after review.

### Resume Point

Commit/push the scoped fixture-ID correction after its semantic and secret gates.
Reconcile the current PR #287 head, wait for all protected checks, merge and verify development
publication. Prepare the signed release/v0.14.4 PR, archive/reset this complete
plan there, then independently verify stable external delivery and cleanup.
No further OCR or aggregate Security run is required for unchanged behavior.
No stable release or external publication is claimed complete.

### Plan Fidelity Check

- [x] All accepted outcomes and privacy/resource/compatibility constraints are represented.
- [x] Requirements map to ordered queue items and verification; no orphan implementation or delivery step.
- [x] Choices reflect current code and expanded probes, with no library menu left for implementation.
- [x] Optional diagram behavior, new dependency identity and unchanged evidence/receipt boundaries are explicit.
- [x] Recovery, private cleanup, exact resume action and release-PR archival/external delivery are retained.

### Reconciliation Check

Initial saved-plan semantic review confirmed construction-time parser bounds, separate treatment of the 30 whole-file-only cases, source revalidation after prior cleanup and both admission/publication paths. Corrected plan-origin/queue/state schema wiring before the first commit. Reconcile affected sections before logical commits; do not copy private artifact locations into this public plan.

### Closure Gate

All repository requirements and queue items must be verified, required reviews/checks passed, confirmed findings corrected and private raw copies cleaned. Archive this complete plan and reset PLANS.md in the release PR with external publication explicitly pending. Do not claim release completion until independent external evidence confirms delivery.

### Post-Close Delivery

Required after release-PR merge: inspect CI-owned stable TestPyPI/PyPI bytes/provenance/installs, annotated tag and immutable Release/receipt; confirm issue/milestone closure, site notification/deployment, synchronized clean main and final owned-state cleanup. No extra repository closure PR.

Final cleanup also removes task-owned temporary source copies, build products,
environments, diagnostic artifacts and Docker resources. Remove obsolete GitHub
Actions logs and temporary artifacts after external reconciliation, retaining
published releases and the evidence needed to verify their provenance.

### Handoff Notes

Root owns plan, private evidence reconciliation, integration and release state. First plan push only; implementation remains local until WQ-06 acceptance. Own-tool runs used: 1/2; aggregate Security scans used: 1/1, complete on 185d7db. Revalidate actual Git/external state before retrying an uncertain mutation.

## Recently Completed

- [x] 2026-10-30: Completed Toolkit 0.14.3 source-aware DLP and private corpus audits; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-3-source-aware-dlp-and-private-corpus-audits.md).
- [x] 2026-10-30: Completed Toolkit 0.14.2 compact bootstrap, diagram-only reports and DLP corrections; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-2-compact-bootstrap-diagram-only-reports-and-dlp-corrections.md).
- [x] 2026-10-29: Completed Toolkit 0.14.1 grouped diagrams and private debug qualification; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-1-grouped-diagrams-and-private-debug-qualification.md).
- [x] 2026-10-29: Completed Toolkit 0.14.0 range identity, typed diagrams, DLP qualification and Python 3.15; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-0-range-identity-typed-diagrams-dlp-qualification-and-python-3-15.md).
- [x] 2026-10-25: Completed Two-day GitHub Actions retention; [full archived plan](docs/engineering/execution_history/plans/2026-10-25-two-day-github-actions-retention.md).
- [x] 2026-10-23: Completed Toolkit 0.13.1 partial review of changes containing gitlinks; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-1-partial-review-of-changes-containing-gitlinks.md).
- [x] 2026-10-23: Completed Toolkit 0.13.0 protected default-policy fallback for single-MR review; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-0-protected-default-policy-fallback-for-single-mr-review.md).
