# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Toolkit 0.9.1 — OCR 1.11.4 and 1.11.5

- **Status:** active
- **Plan Origin:** plan_mode_approved
- **Release classification:** release-required; stable delivery release-deferred
- **Target stable version:** 0.9.1
- **Branch:** `codex/v0.9.1-ocr-1.11.5`

#### Goal

Integrate OCR 1.11.4 and 1.11.5 through a green published Draft PR, with exact
1.11.5 runtime support and precise diagnostic/DLP boundaries that preserve GitLab
summary publication. External configured qualification owns the later release decision.

#### Requested Scope

- Qualify #176 and #177 separately; retain adjacent semantic audits and evidence.
- Accept bounded private failure arguments without exposing them or degrading publication.
- Qualify serialized comment repair, Objective-C++ routing, grouped review and defaults.
- Update local OCR to checksum-verified 1.11.5, current docs, examples and changelog.
- Publish a green Draft with external qualification instructions; keep issues/milestone open.

#### Requirement Traceability

| Requirement | Outcome | Queue | Verification |
| --- | --- | --- | --- |
| REQ-001 | Exact OCR 1.11.5 with separate predecessor evidence | WQ-02, WQ-04 | assets, adjacent audits, real binary probes |
| REQ-002 | Bounded arguments never reach normalized/public diagnostics | WQ-03 | hostile parser and production projection tests |
| REQ-003 | Private arguments cannot change summary or publication DLP | WQ-03 | paired result/publication/summary regressions |
| REQ-004 | Comment repair and Objective-C++ routing are qualified | WQ-04 | deterministic real OCR gateway and rules previews |
| REQ-005 | Grouping, defaults, MCP and receipt boundaries remain correct | WQ-04 | compatibility and runtime tests |
| REQ-006 | Docs, decision flow, changelog and backlog reflect current behavior | WQ-05 | documentation checks and rendered Towncrier |
| REQ-007 | Green pushed Draft with truthful external qualification | WQ-06 | local/hosted gates and remote readback |
| REQ-008 | Forward-only live qualification, isolated historical readback and stable tests | WQ-04R | no live version branches, frozen-history validation, CLI and probe regressions |

#### Explicit Non-Goals

No real LLM calls, merge, release PR, tags, package publication, or issue/milestone
closure. No new environment variables, MCP tools, receipt schemas, upstream repair
implementation, or runtime compatibility fallback. No OCR config/credentials or
user HOME changes. No separate Codex Security scan.

#### Constraints

Preserve zero runtime dependencies, Python 3.12–3.14, receipt v8 and action receipt
v3. Keep malformed additive diagnostics independent from authoritative review
publication. Preserve summary format, numeric tool/token reporting, DLP protection
of public findings/warnings/suggestions, and independent later-action decisions.
New tests receive purpose-focused docstrings and stay with existing owners.

#### Inputs And Sources

- Approved conversation plan and final DLP/summary acceptance clarification.
- GitHub #176/#177; hosted compatibility run 33962853525.
- Official adjacent comparisons 1.11.3→1.11.4 and 1.11.4→1.11.5.
- Canonical project principles, development/release guides, compatibility policy,
  review decision flow and public configuration/security contracts.
- Engineering-workflow 0.9.1; repository ownership takes precedence over templates.

#### User Decisions And Answers

Delivery stops at a published green Draft. External configured environment owns
real model testing and confirmation. Local OCR may immediately advance to 1.11.5
after plan materialization; all local binary checks use isolated HOME and no LLM.
Private failure arguments alone must not alter DLP counts, review status, findings
or GitLab summary. Public secrets remain subject to normal DLP filtering.

#### Completed Baseline State

Clean main at ae0a9ac4357b95349e73939d71b0a2a9e0e6d69d; toolkit 0.9.0 released,
next version 0.9.1, recommended OCR 1.11.3. Local OCR is 1.11.1. Both candidate
issues report compatible machine evidence; current parser rejects arguments as
an extra diagnostic field. Workflow audit found canonical owners and valid indexes.

#### Current Work Queue

| Queue | Status | Work |
| --- | --- | --- |
| WQ-01 | done | Signed planning commit pushed; Draft PR #178 opened |
| WQ-02 | done | Verified assets and safely updated local OCR 1.11.5 |
| WQ-03 | done | Bounded failure arguments and DLP/summary regressions |
| WQ-04 | done | Expanded real OCR qualification, adjacent evidence and final pins |
| WQ-04R | done | Forward-only live qualification, frozen historical readback and maintenance instructions |
| WQ-05 | in_progress | Public docs, decision flow, changelog and backlog reconciliation |
| WQ-06 | pending | Final local gate, push, hosted checks and external Draft handoff |

#### Locked Decisions

- Optional arguments is an opaque string, including empty, capped at 32768 code
  points and 131072 UTF-8 bytes under the existing whole-result bound. Wrong shape
  or excess produces invalid diagnostic state, never loss of a valid review.
- Discard arguments before normalized details/rendering and publication DLP;
  raw OCR artifacts remain private. Do not parse nested serialized payloads.
- Keep normal warning/DLP/later-action treatment of comment_args_repaired.
- Qualify both releases, promote only exact 1.11.5, and retain historical evidence.
- Current group terminology must distinguish group prompt ceiling from per-file
  preselection filtering. Viewer marks carry no GitLab lifecycle authority.
- Existing scheduled discovery works and stays unchanged.
- User requested a complete qualification-layer refactor during implementation.
  Live probes target the current consumed contract without historical execution
  branches or patch-specific fixtures. Historical evidence keeps its original
  validation semantics in a separate owner. Promotion-policy tests use frozen
  baselines; current pin tests alone assert the current version. Update canonical
  development/compatibility instructions rather than adding duplicate agent rules.

#### Verification

Focused parser/production projection tests compare equivalent results with/without
private arguments across summary, findings, DLP, token/tool counters and coverage.
Exercise malformed, oversized, secret/PII/control/Unicode arguments; genuine public
DLP filtering; verified-zero/nonzero/invalid/conflicting diagnostics; repaired and
rejected comment batches; rules .mm/.m; grouping and numeric/MCP contracts.
Before each signed logical commit: formatter, focused tests, complete diff and
trust-flow self-review, git diff --check. Once after implementation: quality/coverage
floors, lock, manifest/evidence, Towncrier, privacy and pinned Gitleaks. Hosted PR
owns OS/Python matrix, package checks, dependencies, Security and CodeQL.

#### Latest Validation Results

- 2026-09-06: current branch and version markers verified; plan approved; no edits
  preceded this plan. Existing scheduled candidate run is successful.
- 2026-09-06: local Darwin arm64 OCR 1.11.5 verifies digest
  c041b03cc840957b52df28514e8dbb51f798e6cb1259d97555a41a2e3e3ccaf9 against
  GitHub and the verified upstream checksum file. Isolated version/help passed;
  config, credentials and user HOME were preserved. Milestone v0.9.1 tracks #176/#177.
- 2026-09-06: Draft #178 opened. Baseline real OCR 1.11.5 no-LLM contracts passed.
  Diagnostic/parser/finalization/posting tests passed 236 tests and 94 subtests.
  Paired clean/finding/warning/partial/filtered results produced identical persisted
  projections, DLP state, console diagnostics and GitLab notes with/without private
  arguments. Malformed and oversized arguments remain diagnostic-only degradation.
- 2026-09-06: expanded real-binary no-LLM suites passed for OCR 1.11.4 and 1.11.5.
  Native/serialized/repaired two-comment batches preserve fields and anchors;
  suspect truncation is rejected with raw arguments confined to private diagnostics.
  Objective-C++ and both .m routing modes passed. Historical Linux asset proofs
  remain linked to run 33962853525; new contract evidence explicitly names Darwin.
- 2026-09-06: full live qualification refactor removed historical execution branches
  and text/grouping fallbacks, separated frozen evidence readback, and made
  promotion validate current contracts before writes. Generic tests now use frozen
  baselines. Complete real-binary JSON proof is identical before/after refactoring
  for both releases. Focused suite passed 389 tests and 109 subtests; documentation
  and metadata suite passed 163 tests. Canonical maintenance instructions updated.

#### Risks And Recovery

Restore the old verified local binary if replacement validation fails. Failed probes
block promotion; retain their bounded evidence and classify the failing owner.
Never weaken summary/DLP/receipt gates to obtain green checks. Evidence-driven CI
fixes receive the same self-review and commit gates. Preserve temporary private
outputs until verification, then remove only task-owned files.

#### Resume Point

Finish WQ-05 public contract review, then perform WQ-06 final local/hosted gates.
After the initial Draft push, keep later implementation commits local until all
slices and final local validation complete.

#### Plan Fidelity Check

- [x] Requirements, sources, constraints and user decisions are preserved.
- [x] Every requirement maps to an ordered queue and verification owner.
- [x] Data/privacy boundaries, recovery and exact next action are explicit.

#### Reconciliation Check

- [x] Baseline and workflow owners verified.
- [ ] Code, tests, public docs, issues and Draft agree.
- [ ] Local/remote head and current hosted checks agree.

#### Closure Gate

- [ ] Implementation and required local/hosted checks complete.
- [ ] Draft open and mergeable; unresolved review threads absent.
- [ ] Issues and milestone open; external qualification checklist recorded.
- [ ] Worktree clean and resume point reflects external qualification.

#### Post-Close Delivery

External agent starts with exact Draft head/tree and checksum-verified OCR 1.11.5
in isolated HOME, then runs production ocr review using configured LLM. Verify
MCP use, diagnostics/repair, grouping, findings/suggestions, privacy and cleanup.
Publish only bounded structural evidence, hashes and pass/fail. Owner confirmation
precedes the ordinary protected merge/release process.

#### Handoff Notes

Do not require intermediate OCR installation. Keep 1.11.4 audit distinct from final
1.11.5 support. Update issue checkboxes only for proven criteria. Stable release
remains deferred and the active plan remains available until later release closure.
