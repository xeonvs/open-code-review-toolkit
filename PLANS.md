# Execution Plans

## Active Plan: Toolkit 0.14.4 systematic DLP corrections and diagram source validation

plan_schema_version: 2
Status: active
Owner: root
Last Updated: 2026-10-30

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
| REQ-001 | Full private causal disposition of all 3790 retained observations, including the 3767 previously unadjudicated entries; no unexplained remainder | WQ-02, WQ-06 | pending |
| REQ-002 | Correct confirmed FP/FN causes across code, configuration, documentation, logs and ordinary text without corpus-specific exemptions | WQ-03, WQ-05, WQ-06 | pending |
| REQ-003 | Qualify Mistune/regex/emoji with bounded work, supported-Python binary installation, dependency identity and resource evidence | WQ-03, WQ-05 | pending |
| REQ-004 | Improve existing private audit reports; preserve exact annotations and closed persisted formats; no new CLI command or CI stage | WQ-02, WQ-03 | pending |
| REQ-005 | Independently bounded immutable source metadata validates diagram references above the evidence-size limit, at admission and publication | WQ-04, WQ-05 | pending |
| REQ-006 | Optional diagram/MCP/rendering failure never changes findings, coverage or approval eligibility; exact admitted Mermaid accompanies feature PR | WQ-04, WQ-05, WQ-06 | pending |
| REQ-007 | Meaningful branch/property/boundary coverage, one aggregate Security scan, threat-model reconciliation and real own-tool acceptance | WQ-05, WQ-06 | pending |
| REQ-008 | Private-safe source, immutable inputs, bounded acquisition and owned raw-source cleanup with originals unchanged | WQ-02, WQ-06, WQ-08 | pending |
| REQ-009 | Signed draft-plan PR, local reviewed development, protected feature/release delivery and plan archive in the release PR | WQ-01, WQ-07, WQ-08 | in_progress |

### Explicit Non-Goals

No AI model, pretrained classifier, model download, remote classification, DNS/deliverability check, default phone region, repository/name/extension allowlist, general graph subsystem, additional forge adapter, new audit CLI command or pipeline stage. No inference that every audit hit is a bug. No reduction of receipt/range identity, source-proof authority, configured-secret protection, or existing sensitive-material checks. No promotional-site implementation or cross-service handoff.

### Constraints

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
| WQ-01 | REQ-009 | Materialize/review plan, signed commit/push, draft PR and issue refinements | in_progress |
| WQ-02 | REQ-001, REQ-004, REQ-008 | After WQ-01: revalidate private evidence; fully adjudicate causal groups and improve audit grouping/diagnostics | pending |
| WQ-03 | REQ-002, REQ-003, REQ-004 | After WQ-02: implement representation-aware DLP, confirmed regressions, dependencies and scanner identity | pending |
| WQ-04 | REQ-005, REQ-006 | After WQ-01: implement shared bounded streaming diagram-source metadata and closed diagnoses | pending |
| WQ-05 | REQ-002, REQ-003, REQ-005, REQ-006, REQ-007 | After WQ-03/WQ-04: integrate callers, fuzz/inverse tests, >=90% affected component coverage and installed/resource qualification | pending |
| WQ-06 | REQ-001, REQ-002, REQ-006, REQ-007, REQ-008 | After WQ-05: aggregate self-review, one Security scan, threat-model review, actual own-tool review and repeat corpora/cleanup | pending |
| WQ-07 | REQ-009 | After WQ-06: final quality/docs/secret/dependency gates, exact diagram in feature PR, protected CI/merge and development publication | pending |
| WQ-08 | REQ-008, REQ-009 | After WQ-07: signed release/v0.14.4 PR with archival/reset; stable publication, external closure and cleanup verification | pending |

### Locked Decisions

**Causal ledger.** Keep original observation identities and role/proof context. Split mixed groups and verify every member against the claimed common cause and additional sensitive material. Use existing exact labels (expected-protection, confirmed-benign, conservative-ambiguity); record confirmed false negatives as synthetic regressions and inverse controls. A detector family alone cannot justify a verdict. Unsupported interpretation remains conservative with an explicit rationale, not an unexamined parking label.

**DLP architecture.** Keep candidate extraction, representation interpretation and final admission separate and pure. Trusted caller metadata identifies actual Markdown, literal source, plain data or diagram labels; a filename or successful parse cannot authorize disclosure. Check original and applicable decoded material independently, including known secrets and forbidden origins. Literal rendering prevents formatting activation, not confidentiality checks. Preserve national/unlabelled phones, unusual phone-shaped fixtures, .invalid email domains, low-entropy configured secrets and adjacent sensitive values. Correct valid technical date/list treatment, credential masks/permissions/references, mentions, Unicode email and valid presentation sequences through structural roles rather than accumulating lexical exceptions. An arithmetic parse alone is insufficient to waive a phone candidate.

**Dependencies and resource bounds.** Qualify Mistune 3.4.0 AST without renderers/plugins, regex 2026.9.29 for narrow bounded operations/Unicode and emoji 2.16.0 static standard sequence data; stdlib HTMLParser supplies bounded HTML events. Do not rebuild text from emoji tokens: unmatched joiners can be skipped. Whole original checks and exact accepted spans remain authoritative. Extend the documented runtime-dependency exception only at this parsing boundary; pure reporting never imports it. Preserve external text budgets, limit nesting to 20 and enforce a shared 32768-token budget during construction, not afterward. Bound derived views/expansion as they are created; exhaustion is explicit limit, never admission. Prepare source once per file, avoid cross-file source retention and include actual dependency versions in scanner identity. Existing audit reports gain grouping/proof/aggregate visibility without new CLI commands or persisted review-schema changes.

**Diagram references.** The production Git reader owns a streaming immutable regular-blob text-metadata operation: exact object binding, strict incremental UTF-8, NUL rejection, byte count and LF line count including final non-LF line. Never follow symlinks/gitlinks or consult mutable checkout content. Use at most 5000000 bytes/blob, 32000000 aggregate bytes and 30 seconds for one diagram's reference-validation session; chunks <=65536 bytes. Cache metadata by immutable object, not whole sources. Share the adapter between initial admission and GitLab revalidation. Leave evidence/source-proof reads at 256000 bytes. Pure admission receives typed metadata; reporting has no Git/DLP orchestration. Use existing budget/unavailable/reference reasons with source-free diagnostics; do not change receipt schemas. Any auxiliary failure omits only the diagram.

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

Planning probes only: isolated binary-only Python 3.14/3.15 component experiments succeeded without target code execution or network classification. On the same synthetic 64 KiB inputs, Mistune used roughly 7 ms for prose, 110 ms for brackets and 62 ms for malformed tags, versus markdown-it-py about 12/520/180 ms. Both required memory/work bounds; the full chosen stack reached approximately 87 MiB peak RSS in the Python 3.15 adversarial probe. These are feasibility results, not production or full-corpus acceptance. No new implementation, Security scan or own-tool run has passed yet.

### Risks And Recovery

Lossy parsers can hide material; always retain independent original checks and use exact positive spans, with conservative rejection on incomplete interpretation. Regex timeouts do not bound unrelated parser operations; construction-time token/nesting/derived-size budgets and adversarial performance tests remain mandatory. New dependency versions must invalidate scanner identity and pass clean installed qualification. Full causal reconciliation may expose additional defects; add minimized cases within these requirements rather than corpus-specific exemptions. Private source availability or fingerprints can invalidate replay: stop that comparison and recover exact authorized inputs, never silently substitute a different corpus. Cancellation must kill/reap task-owned processes and retain explicit snapshot-cleanup ownership. Do not change published 0.14.3 artifacts/tags or force public feature history. Local unpushed fixups may amend after review.

### Resume Point

WQ-01: critically review this saved plan and its requirement/queue coverage, run plan/public-content/dependency guards, create the signed plan commit and first draft-PR push. Then update the two issues with public-safe final contracts and enter WQ-02.

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

### Handoff Notes

Root owns plan, private evidence reconciliation, integration and release state. First plan push only; implementation remains local until WQ-06 acceptance. Initial own-tool runs used: 0/2; aggregate Security scans used: 0/1. Revalidate actual Git/external state before retrying an uncertain mutation.

## Recently Completed

- [x] 2026-10-30: Completed Toolkit 0.14.3 source-aware DLP and private corpus audits; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-3-source-aware-dlp-and-private-corpus-audits.md).
- [x] 2026-10-30: Completed Toolkit 0.14.2 compact bootstrap, diagram-only reports and DLP corrections; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-2-compact-bootstrap-diagram-only-reports-and-dlp-corrections.md).
- [x] 2026-10-29: Completed Toolkit 0.14.1 grouped diagrams and private debug qualification; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-1-grouped-diagrams-and-private-debug-qualification.md).
- [x] 2026-10-29: Completed Toolkit 0.14.0 range identity, typed diagrams, DLP qualification and Python 3.15; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-0-range-identity-typed-diagrams-dlp-qualification-and-python-3-15.md).
- [x] 2026-10-25: Completed Two-day GitHub Actions retention; [full archived plan](docs/engineering/execution_history/plans/2026-10-25-two-day-github-actions-retention.md).
- [x] 2026-10-23: Completed Toolkit 0.13.1 partial review of changes containing gitlinks; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-1-partial-review-of-changes-containing-gitlinks.md).
- [x] 2026-10-23: Completed Toolkit 0.13.0 protected default-policy fallback for single-MR review; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-0-protected-default-policy-fallback-for-single-mr-review.md).
