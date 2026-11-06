# Execution Plans

## Active Plan: Internal engineering cycle corrections

plan_schema_version: 2
Status: done
Release classification: no-release
Last Updated: 2026-11-06

### Goal

Correct the demonstrated causes of the prolonged 0.14.6 engineering cycle,
retain the quality and privacy gates, and deliver a reviewed ordinary pull
request. No stable or development distributions, tag, release or site update
belong to this task.

### Plan Origin

direct_execution

Owner requested implementation of the read-only retrospective's improvements,
including a cause assessment of the installed engineering skill and an upstream
issue if a concrete skill defect warrants it.

### Requested Scope

Audit the applicable skill and repository instructions against the retrospective.
Improve the existing canonical workflow rather than adding a second workflow or
an orchestration framework. Make the contract/consumer qualification stage
concrete before expensive corpus/model/full-matrix acceptance. Repair brittle
quality-wrapper test oracles and the release documentation contract that inferred
publication state from one index phrase. Cover the changed test infrastructure
through real shell execution with a controlled external tool. Check normal
non-release delivery and preserve the no-artifact path.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Attribute fragmentation to loaded rules, routes, concrete controls or agent execution; assess skill contribution | WQ-01 | done |
| REQ-002 | General contract, complete consumer/test map and stable compact qualification before expensive acceptance | WQ-02 | done |
| REQ-003 | Behavioral coverage-wrapper parity and failure tests without incidental command-count coupling | WQ-03 | done |
| REQ-004 | Release archive checks follow explicit archive identity and delivery ownership, independent of index wording | WQ-03 | done |
| REQ-005 | Context, iteration, evidence reuse and check selection improvements in canonical owners | WQ-02, WQ-04 | done |
| REQ-006 | Focused validation, semantic review and guarded ordinary PR handoff ready; no publication artifacts | WQ-04, WQ-05 | done |
| REQ-007 | Address a reproducible skill-owned defect upstream if established; otherwise retain the evidence-backed local decision | WQ-01, WQ-05 | done |

### Explicit Non-Goals

No runtime/DLP algorithm or public behavior change; no dependency refresh,
OCR qualification, corpus rerun, model-backed OCR review or Security diff scan
for this instruction/test-only scope. No skill-cache edits, target migration,
new agent configuration, new telemetry framework, per-command receipts, timing
targets, test weakening, publication or private corpus disclosure. Do not rewrite
the completed 0.14.6 plan or release evidence.

### Constraints

- This full plan is the first repository write. Use a codex/ branch, semantic
  self-review and exact staged secret scan before each signed logical commit.
- Keep one canonical owner per instruction. AGENTS remains a route map; an
  incident record is diagnostic evidence, not another imperative rule copy.
- Preserve security, inverse-case, integration, coverage and release authority
  boundaries. Do not infer an absence proof from unknown syntax or test paths.
- Tests and documentation are internal. The final change set must qualify for
  the existing main-push no-distribution classifier; do not broaden that policy.
- Reuse current reads and successful checks for unchanged inputs. Keep raw
  sessions, local paths and private project information out of public content.
- Do not rerun the release pipeline. PR creation with initial check readback is
  the delivery boundary; merge/release and CI monitoring are not requested.

### Inputs And Sources

- Owner's accepted retrospective and follow-up implementation request.
- Published 0.14.6, feature #299, release #300 and their existing test corrections.
- AGENTS.md; docs/engineering/project_principles.md; docs/development.md;
  docs/release.md and docs/codex/AGENT_EXECUTION_PITFALLS.md.
- Installed engineering-workflow 0.10.0 planning, instruction, orchestration and
  audit owners; current repository workflow state remains historical 0.9.8.
- scripts/quality.sh, tests/test_quality_script.py, tests/test_operations_docs.py,
  scripts/docs_only.py and relevant workflow/test owners.
- Upstream work retained as
  [skill #25](https://github.com/xeonvs/codex-engineering-workflow/issues/25) and
  [skill #26](https://github.com/xeonvs/codex-engineering-workflow/issues/26).

### User Decisions And Answers

- The read-only retrospective is complete. Implement necessary internal fixes.
- Examine skill influence and open an upstream issue if warranted.
- No release process or distribution artifacts for these corrections.
- Make skill-generated rules actionable across repository maturities: propose
  explicit evidence-based stage transitions, not universal numeric limits or
  additional generic prohibitions. Apply the local procedure now and track the
  reusable skill change upstream.

### Completed Baseline State

- Clean synchronized main at 23c2930; 0.14.6 already published and verified.
- Existing instructions already require bounded output, changed-boundary tests,
  reuse of evidence, focused checks, one aggregate scan and scoped final quality.
- Retrospective identified late DLP contract revisions, unstable-candidate corpus
  replays, missing consumer tests, incidental command-count test oracles and a
  release index wording selector. Model reviews themselves were not the main
  delay; do not weaken them to address agent iteration overhead.
- Read-only workflow audit reports a valid instruction contract; archive-link
  and heuristic content warnings require ownership triage, not automatic edits.

### Current Work Queue

| Item | Work and acceptance | Requirements | Status |
| --- | --- | --- | --- |
| WQ-01 | Finish bounded owner audit; distinguish existing skill guidance from local controls and reproduce any upstream defect | REQ-001, REQ-007 | done |
| WQ-02 | Amend development procedure with contract/consumer qualification and meaningful escalation/reuse criteria; retain a concise incident if useful | REQ-002, REQ-005 | done |
| WQ-03 | Replace incidental quality counts with executed local/CI coverage parity and terminal-failure evidence; remove index prose as publication selector | REQ-003, REQ-004 | done |
| WQ-04 | Self-review final changed handoffs and representative tasks; run focused contracts, formatting/lint, instruction and public-content guards | REQ-005, REQ-006 | done |
| WQ-05 | Resolve upstream issue disposition and prepare checked closure and reviewed ordinary PR handoff; external delivery remains required below | REQ-006, REQ-007 | done |

### Locked Decisions

- Keep the existing skill planning/lifecycle contract and established owners.
  More generic prose or mandatory bookkeeping is not an execution control.
- Choose small semantic counterexample matrices before full corpora; map old
  consumers explicitly when a common helper changes semantics. Failed checks
  alter the hypothesis and invalidate only affected evidence.
- Use actual shell commands with a controlled uv peer to observe the existing
  quality owner, not a mock replacement of the wrapper under test. Compare
  executed coverage policies instead of counting source-string occurrences.
- Use archive metadata, linked plan and post-close delivery ownership to qualify
  current release history. Index wording does not prove external publication.
- Keep full CI requirements intact. No full local runtime matrix is needed for
  test/instruction-only changes; hosted checks may independently run it.
- Reject changes to correct historical indexes merely to satisfy a faulty skill
  heuristic; create a minimal public upstream reproduction if that is confirmed.

### Verification

- V-01 / REQ-001,007: compare loaded owner instructions with concrete failures;
  inspect/reproduce any skill defect and check existing upstream issues.
- V-02 / REQ-002,005: semantic walkthrough for common DLP/parser helper, provider
  handoff, documentation-only correction and future release preparation.
- V-03 / REQ-003: tests execute local coverage shell and extracted CI step using
  a controlled uv executable; assert matching expanded policies, required floors,
  one test owner per path, output freshness and exact fail-stop exit behavior.
- V-04 / REQ-004: affected operations/release documentation contracts plus
  synthetic archive/index variations and negative metadata/identity controls.
- V-05 / REQ-006: focused quality/operations/environment/release/classifier
  tests; Ruff format/check; instruction contract and public-content scan.
- V-06 / REQ-006: aggregate diff self-review, staged/tree/history Gitleaks,
  dependency audit and exact diff classification before push. Confirm unchanged
  markers/package/runtime and initial PR state; no release authorization.
- V-07 / REQ-006: plan fidelity, reconciliation and lifecycle check/close; retain
  this plan because its decisions and validation have continuing recovery value.

### Latest Validation Results

- 2026-11-06: Focused quality, operations, release authorization/receipt/notes, environment
  and classifier suite: 171 passed. Local shell and extracted CI coverage step
  agree on expanded policies; pytest/report failures preserve exit 2, 7 and 130.
- Ruff format/check and public-tree privacy check pass; instruction contract is
  valid with zero errors/warnings. The incident initially referenced a subsection
  instead of its invariant owner and an undeclared manual guard; corrected to
  the existing owner/route guard, then the instruction check passed again.
- Dependency audit exited successfully with no known dependency vulnerabilities;
  the local toolkit project itself is skipped as an unpublished SCM version.
- Ownership triage: skill audit bypasses explicit archive-layout allowances;
  lifecycle accepts the same graph. Reported as
  [skill #26](https://github.com/xeonvs/codex-engineering-workflow/issues/26),
  not repaired by deleting valid target navigation.
- Loaded instructions already cover efficient execution; the execution failure
  remains ours. Local qualification stages and behavioral guards address it.
  Reusable maturity-aware generated stage gates are tracked in
  [skill #25](https://github.com/xeonvs/codex-engineering-workflow/issues/25).
  Both created issues were independently read back as open.
- Installation update-policy check failed to read local policy safely. Installed
  skill bytes are available; no update/currentness claim or cache mutation made.
- Final test-only adjustment: quality/operations contracts replayed, 56 passed.
  Full runtime matrix, corpus scans and model/security reviews were not repeated
  for this internal scope. No runtime, dependencies, workflow or version changed.
- Aggregate self-review covered all changed instructions/tests and the complete
  plan. Representative decisions checked: shared parser/DLP helper includes old
  consumers and unknown syntax; provider changes preserve partial/failure and
  cleanup handoffs; documentation-only edits retain scoped checks; release
  preparation includes final operations/environment contracts and does not
  infer external publication from index prose.
- Existing explicit Hypothesis profile selection and native waiter/output rules
  already cover the other retrospective execution mistakes. No extra duplicate
  rules, wrappers or telemetry were added. The remaining behavioral improvement
  is to apply those existing rules at the qualified transition.
- Tree secret/privacy scan passed. Exact staged and reachable-history scans,
  final diff classification, signed commit and PR are required at delivery.

### Risks And Recovery

- Overprescription can worsen fragmentation: keep changes in existing procedure
  sections and test real decisions, not duplicated wording.
- Shell parity tests can mirror both faulty paths: preserve independent required
  coverage floors and hostile failure controls as well as local/CI comparison.
- Removing the index selector must retain identity, closed-plan and external
  handoff checks; reject missing/conflicting archive metadata.
- Keep original files recoverable in Git; preserve unrelated changes. On a failed
  guard correct its narrow cause, rerun affected checks and update the resume
  point. On network/sandbox failure keep the verified local result and exact
  external delivery status; never claim a PR/issue exists without readback.

### Resume Point

No unfinished in-scope implementation remains. The checked repository handoff is
ready; required external delivery is classified separately below.

### Plan Fidelity Check

- [x] Requested outcomes and annotation captured in REQ-001 through REQ-007.
- [x] Each requirement maps to queue work and explicit verification.
- [x] Sources, constraints, decisions and non-goals preserve approved scope.
- [x] Risks, recovery and exact first safe action are recorded.
- [x] No release/artifact lifecycle or private input disclosure is introduced.

### Reconciliation Check

- [x] Queue, requirements, evidence and final diff agree.
- [x] Canonical instructions and tests contain no competing rules or stale state.
- [x] Skill findings are addressed locally or assigned to confirmed upstream issues.

### Closure Gate

- [x] All scoped work and applicable checks complete; no local findings left open.
- [x] Aggregate semantic review and tree privacy/secret/dependency checks complete.
- [x] Checked closure is prepared; retained plan rationale has recovery value.

### Post-Close Delivery

The reviewed repository handoff is completed. Final closure-artifact guards,
exact staged/tree/history scans, no-distribution diff classification, signed
commit, feature push and ordinary PR creation with initial check readback remain
required outside the closed repository plan. The task objective stays active
until that PR delivery is verified. CI completion and merge are not requested;
release and stable/development distribution publication are excluded.

### Handoff Notes

No unfinished implementation remains. Upstream #25/#26 own reusable skill work;
the installed cache and source repository are unchanged. The retained evidence
and decisions are sufficient for the ordinary external handoff above.

## Recently Completed

- [x] 2026-11-06: Completed Toolkit 0.14.6 — OCR 1.13.6, DLP precision and efficient delivery; [full archived plan](docs/engineering/execution_history/plans/2026-11-06-toolkit-0-14-6-ocr-1-13-6-dlp-precision-and-efficient-delivery.md).
- [x] 2026-11-04: Completed Toolkit 0.14.5 — DLP precision, OCR qualification and maintenance quality; [full archived plan](docs/engineering/execution_history/plans/2026-11-04-toolkit-0-14-5-dlp-precision-ocr-qualification-and-maintenance-quality.md).
- [x] 2026-10-31: Completed Toolkit 0.14.4 systematic DLP corrections and diagram source validation; [full archived plan](docs/engineering/execution_history/plans/2026-10-31-toolkit-0-14-4-systematic-dlp-corrections-and-diagram-source-validation.md).
- [x] 2026-10-30: Completed Toolkit 0.14.3 source-aware DLP and private corpus audits; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-3-source-aware-dlp-and-private-corpus-audits.md).
- [x] 2026-10-30: Completed Toolkit 0.14.2 compact bootstrap, diagram-only reports and DLP corrections; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-2-compact-bootstrap-diagram-only-reports-and-dlp-corrections.md).
- [x] 2026-10-29: Completed Toolkit 0.14.1 grouped diagrams and private debug qualification; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-1-grouped-diagrams-and-private-debug-qualification.md).
- [x] 2026-10-29: Completed Toolkit 0.14.0 range identity, typed diagrams, DLP qualification and Python 3.15; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-0-range-identity-typed-diagrams-dlp-qualification-and-python-3-15.md).
- [x] 2026-10-25: Completed Two-day GitHub Actions retention; [full archived plan](docs/engineering/execution_history/plans/2026-10-25-two-day-github-actions-retention.md).
- [x] 2026-10-23: Completed Toolkit 0.13.1 partial review of changes containing gitlinks; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-1-partial-review-of-changes-containing-gitlinks.md).
- [x] 2026-10-23: Completed Toolkit 0.13.0 protected default-policy fallback for single-MR review; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-0-protected-default-policy-fallback-for-single-mr-review.md).
