# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Toolkit 0.8.3 — OCR boundaries and review tool-usage visibility

Status: `active`
Owner: Codex
Plan Origin: `resumed`
Release classification: `release-deferred` (the product changes require stable
`0.8.3`, but feature merge and publication are explicitly deferred)
Target stable version: `0.8.3`
Last Updated: 2026-08-25

#### Goal

Close #139 and #140 and add one bounded review-usage feature as one protected
0.8.3 release: make a failed OCR
qualification's closed status authoritative even when stale evidence or invalid
support metadata exists, and replace the stale example-owned `OCR_MAX_TOOLS=30`
contract with installed-OCR delegation plus behaviorally qualified numeric CLI
boundaries. Extend the existing one-line GitLab technical summary so its bounded
numeric breakdown shows the useful non-zero OCR review-tool counters rather than
only the first six. Preserve private diagnostics, aggregate-promotion blocking,
the exact OCR 1.10.0 pin, DLP, receipt v5, posting, and automatic-approval
semantics.

#### Requested Scope

- Select OCR compatibility issue input from the actual qualification outcome;
  retained evidence from a failed step must never win over its failed status.
- Ensure every handled qualification failure after evidence creation, including
  a late issue-body write failure, commits a closed failure status before the
  workflow publishes the issue/artifact and restores the red job outcome.
- Let `upsert-issue --status` validate and publish a closed status independently
  of an invalid support manifest that the command does not consume.
- Replace the GitLab example's release-specific max-tools value with OCR's
  supported `0` sentinel and document the exact default as inherited from OCR.
- Recognize only the installed OCR's closed max-tools normalization diagnostic;
  expose a toolkit-authored operator notice without publishing raw stderr or
  treating the diagnostic's reported minimum as proof of the effective loop cap.
- Extend OCR qualification to exercise the behavior and effective semantics of
  toolkit-managed numeric OCR review options at omitted/default, sentinel,
  invalid-below-boundary, accepted-boundary, representative, and maximum edges
  where a maximum exists. Record only bounded closed facts in evidence.
- Add separate bug-fix changelog fragments for #139 and #140, update canonical
  development/public contracts, and complete the protected PR and stable-release
  lifecycle without a local real-LLM/model invocation.
- Keep the current inline `all OCR tool calls` format while publishing every
  admitted non-zero counter that helps explain review activity: OCR repository
  inspection (`file_read`, `file_read_diff`, `file_find`, `code_search`), review
  output/lifecycle (`code_comment`, `task_done`), toolkit context/evidence
  (`ocr_toolkit_evidence`, `context_list`, `context_get`), and the already
  verified per-server MCP summary.
- Treat tool-call counts as operational activity only. Keep aggregate token
  input/output/cache telemetry alongside them, but do not claim or derive
  per-tool token consumption because OCR 1.10.0 does not provide that contract.

#### Requirement Traceability

| Requirement | Source | Outcome | Work items | Verification |
| --- | --- | --- | --- | --- |
| `REQ-139-A` | #139 acceptance 1 | Qualification outcome, not file existence, selects evidence versus status | `WQ-02` | Workflow contract test with retained evidence and failed outcome |
| `REQ-139-B` | #139 acceptance 2 | Late output failure produces authoritative failed status | `WQ-02` | Injected issue-body and partial/failed write tests |
| `REQ-139-C` | #139 acceptance 3 | Status recovery does not load the support manifest | `WQ-02` | Invalid-manifest CLI recovery test |
| `REQ-139-D` | #139 acceptance 4-6 | Issue/artifact publish before red job; aggregate blocked; projection stays closed and private-safe | `WQ-02`, `WQ-04` | Focused script/workflow tests and privacy diff review |
| `REQ-140-A` | #140 expected behavior/scope | Public example delegates max-tools default to installed OCR | `WQ-03` | Environment, docs, and integration contract tests |
| `REQ-140-B` | #140 acceptance 2-4 | Exact enriched/MCP preview accepts valid sentinel and handles known normalization without ambiguous/raw diagnostics | `WQ-03` | Parser negatives plus production-caller integration with controlled OCR peer |
| `REQ-140-C` | #140 scope/acceptance 5 | Qualification records behavioral numeric boundaries and effective-value ownership | `WQ-03` | Exact OCR 1.10.0 no-model probe and evidence-schema tests |
| `REQ-140-D` | #140 acceptance 6 | Current docs/tests avoid toolkit-release wording where OCR owns the contract | `WQ-03`, `WQ-04` | Documentation contract tests and full-text review |
| `REQ-USAGE-A` | #142 and user-approved manager-facing usage summary | Existing inline technical format includes every admitted useful non-zero tool counter, deterministically ordered by count then name | `WQ-06` | Formatter and complete summary regressions with more than six tools |
| `REQ-USAGE-B` | #142 result/privacy boundary | Only bounded names and integer counters cross into GitLab; arguments, results, paths, IDs, provider data, and unknown/unattributed names remain private | `WQ-06` | Hostile map/name/count, DLP, Markdown, and note-budget regressions |
| `REQ-USAGE-C` | #142 honest token explanation | Tool activity appears beside aggregate token usage without percentages or per-tool token attribution | `WQ-06` | Rendering and documentation assertions |
| `REQ-USAGE-D` | #142 existing trust contracts | The expanded diagnostic is not a finding, receipt proof, telemetry source, severity input, or approval signal | `WQ-06`, `WQ-07` | Posting, DLP, and approval regression review |
| `REQ-REL` | Repository release contract | Deliver 0.8.3 through reviewed feature and release PRs with external reconciliation | `WQ-01`, `WQ-04`, `WQ-05` | Protected checks, registries, attestations, tag, receipt, issue/milestone closure |

#### Explicit Non-Goals

- Do not update OCR beyond exact 1.10.0 or change its checksum-pinned evidence
  except for additive qualification facts required by #140.
- Do not add a toolkit prompt/context max-tokens alias, a new configuration
  format, automatic discovery from help text, or a second compatibility service.
- Do not infer a maximum from absent diagnostics or treat OCR's documented
  `min 10` help text as authoritative over observed behavior.
- Do not publish raw subprocess output, filesystem paths, provider/model data,
  repository content, credentials, or exception strings in issues or receipts.
- Do not change DLP, receipt v5, severity, findings, posting transactions,
  telemetry ownership, or automatic-approval eligibility.
- Do not run a local real LLM/model/provider review. A controlled deterministic
  HTTP peer may exercise the OCR process boundary but is not model evidence.
- Do not reorganize tests or production modules beyond the cohesive owners
  directly required by these two fixes.
- Do not change the current one-line technical-summary layout, publish a catalog
  of merely available tools, add per-tool token estimates/percentages, or expose
  raw tool-call arguments, results, errors, paths, request IDs, or dynamic
  external MCP tool names.

#### Constraints

- Start from clean synchronized `main` at stable `v0.8.2`; use branch prefix
  `codex/` and signed logical commits.
- Before each commit: focused tests, requirement/trust-boundary self-review,
  complete staged diff review, and `git diff --check`.
- Run `scripts/quality.sh check` and `scripts/gitleaks.sh` once on the final
  feature head. Hosted PR checks own the full OS/Python matrix and package build;
  do not duplicate those gates locally without a new package boundary.
- Keep subprocess reads bounded, exact-schema status/evidence hostile on load,
  and issue projection based only on closed enums and validated version/run IDs.
- Preserve the user-owned environment: isolated temporary `HOME` only, no OCR
  config/credential writes, no global OCR installation change, and full cleanup.

#### Inputs And Sources

- GitHub issues #139, #140, and #142, including their complete acceptance criteria.
- `.github/workflows/ocr-compatibility.yml`, `scripts/ocr_compat.py`,
  `src/ocr_toolkit/review_runner.py`, current focused tests and public contracts.
- `docs/engineering/project_principles.md` persisted/atomic-state, external-format,
  subprocess, outcome-consistency, and integration-proof boundaries.
- Official OCR `v1.10.0` source in `cmd/opencodereview/shared_flags.go`,
  `cmd/opencodereview/shared.go`, and embedded `task_template.json`.
- Official OCR `v1.10.0` built-in registry and tools configuration: six native
  review tools (`task_done`, `code_comment`, `file_read`, `file_read_diff`,
  `file_find`, and `code_search`); toolkit context/evidence tools remain owned by
  the exact MCP composition and receipt.
- Isolated local OCR 1.10.0 no-model preview evidence: omitted and `0` accepted;
  negative rejected; `1..49` report normalization to `50`; `50+` accepted; help
  says `min 10`; embedded template owns `MAX_TOOL_REQUEST_TIMES=100` and applies
  CLI max-tools only when it raises that template value.

#### User Decisions And Answers

- Take both currently open issues into active work.
- Local execution against a real LLM/provider is explicitly waived because this
  environment has no access; do not claim that evidence.
- Continue the established efficient workflow: logical commits, self-review,
  one final complete local gate, and protected hosted CI.
- After the final push, keep PR #141 in Draft. Do not merge the feature branch,
  publish development/stable artifacts, create a release PR, or release 0.8.3.
- The accepted manager-facing question is “where did the review activity go?”:
  preserve the current inline format, show the selected numeric counters, and
  explicitly avoid claiming exact per-tool token attribution.

#### Completed Baseline State

- `main` is clean at stable merge `6dae5b3821eb7aa22c8c8d8d9c17f869278340c7`
  and tree `ba935a1f0a7f0e6e6c899120ecdc08e3822097c4`.
- Toolkit 0.8.2 and OCR 1.10.0 are published and reconciled; `.next-version` is
  `0.8.3`; no active plan or open milestone existed before this activation.
- #139 reproduces three authority/recovery gaps added by the 0.8.2 failure path.
- #140 reproduces before any provider call because successful OCR preview stderr
  currently accepts only the background-warning grammar.
- The previously handed-off Draft head `e5a889f` is clean and fully green across
  protected hosted checks. Its current formatter publishes the aggregate total
  but truncates a valid per-tool breakdown to six entries, which is insufficient
  for the newly approved activity explanation.

#### Current Work Queue

| Work item | Status | Scope and commit boundary |
| --- | --- | --- |
| `WQ-01` | `done` | Signed planning commit `85b3097`; branch `codex/v0.8.3-ocr-boundaries`; milestone `v0.8.3` #6 with #139/#140; planning push; Draft PR #141 with exact scope/non-claims |
| `WQ-02` | `done` | #139: outcome-authoritative workflow selection; portable atomic evidence/status/issue-body handoffs; closed late-write recovery; manifest-independent status upsert; regression tests; public contract and `139.bugfix.md` |
| `WQ-03` | `done` | #140: example sentinel `0`; exact normalization parser and operator-only notice; behavioral numeric/effective-loop qualification; updated exact OCR evidence/hash; full enriched/MCP preview regression; public/development contracts and `140.bugfix.md` |
| `WQ-04` | `done` | Reconciled public/development contracts and requirements; complete quality/coverage, manifest, Towncrier, and privacy/data-flow review are green; final Draft push and hosted readback are handoff actions, not release delivery |
| `WQ-05` | `out_of_scope` | Owner-deferred delivery: keep PR #141 Draft after final push; do not merge, publish TestPyPI/PyPI, prepare a release PR, tag, close issues, or close the milestone in this run |
| `WQ-06` | `done` | #142 feature commit `a416f37`: the existing inline formatter now shows every admitted useful non-zero counter; external MCP stays aggregated by verified server; focused hostile-value/DLP/approval tests, public operational wording, and `142.feature.md` define the activity-not-token-attribution contract |
| `WQ-07` | `done` | One final full local gate and overall reporting/privacy/approval self-review are green; this signed handoff commit is followed by one final push, Draft/issue coordination, and exact-head hosted readback as delivery evidence rather than another repository-content change |

#### Locked Decisions

- Both issues belong to stable 0.8.3 and remain separate changelog entries.
- `OCR_MAX_TOOLS` remains an optional example-local variable but defaults to
  sentinel `0`, whose meaning is exactly “inherit installed OCR template”.
- OCR's normalization diagnostic is a bounded installed-component fact. Its raw
  text never crosses into result/posting/receipt; the toolkit reports only parsed
  integers and distinguishes the reported normalization target from the actual
  template-owned loop limit.
- A failed qualification status is authoritative whenever the qualification step
  outcome is failure, even if a complete evidence file also exists.
- `upsert-issue --status` has no support-manifest dependency; evidence-driven
  discovery, qualification, aggregation, and promotion retain manifest validation.
- OCR remains external and pinned to 1.10.0. No local model result substitutes
  for hosted exact-binary or deterministic controlled-peer evidence.
- The existing `all OCR tool calls: N total (...)` line remains the sole OCR
  tool-counter format. It lists admitted non-zero counters by descending count
  and then name; no grouping, percentages, or token-allocation inference is added.
- Built-in OCR and toolkit-owned context/evidence names may be shown as activity.
  External dynamic MCP tools remain represented only through the existing
  verified per-server aggregate; unknown raw names never gain public meaning.

#### Verification

- #139: focused `tests/test_ocr_compat.py` and workflow-source tests covering
  retained evidence, late write failure, invalid manifest, closed schemas,
  publication-before-red ordering, and blocked aggregation.
- #140: focused environment/integration/review-runner/compatibility tests covering
  sentinel/default, normalization, duplicate/near-miss/Unicode/oversized stderr,
  known/unknown success output, invalid non-zero diagnostics, effective-value
  evidence, and the complete evidence/MCP production caller up to the model gate.
- Exact installed OCR 1.10.0: isolated no-real-model boundary probe only; preserve
  command/exit/closed diagnostics/effective counts and remove its temporary HOME.
- Final feature head: `scripts/quality.sh check`, coverage floors,
  `PYTHONPATH=src python scripts/ocr_compat.py validate`, Towncrier draft,
  `scripts/gitleaks.sh`, `git diff --check`, and clean-tree confirmation.
- Hosted: all protected Draft feature checks on the exact final head. Development
  publication, stable release, registry/provenance/install readback, and closure
  remain deferred under `docs/release.md`.
- Tool-usage slice: focused formatter/posting/result-DLP/approval tests must prove
  more than six useful counters remain visible, deterministic and bounded; raw
  call content and unknown names remain absent; aggregate token rendering and
  approval decisions are unchanged.

#### Latest Validation Results

- 2026-08-25 reconnaissance: clean synchronized `main`; workflow audit reports
  canonical owners and complete documentation indexes; exactly #139 and #140 are
  open; both have no milestone.
- Isolated OCR 1.10.0 preview matrix reproduced #140 without LLM access and was
  fully cleaned. Official tag source disproved the assumption that reported
  normalization target `50` is necessarily the effective loop cap.
- No implementation, repository metadata, issue, milestone, branch, or PR write
  preceded this plan materialization.
- Coordination completed after the signed plan commit: milestone `v0.8.3` #6,
  #139/#140 assignment, planning head push, and Draft PR #141. The owner then
  explicitly deferred merge and release; no publication belongs to this run.
- #139 focused validation: 95 compatibility/workflow tests pass; Ruff and
  `git diff --check` pass. Self-review confirms the workflow selects output from
  `steps.qualify.outcome`, all file handoffs preserve the old baseline until an
  atomic replace, status recovery consumes only its closed schema, raw details
  remain private, and the restored red qualification blocks aggregation.
- #140 focused validation: 212 runtime/compatibility/environment/integration/
  documentation tests pass with Ruff, manifest validation, Towncrier draft, and
  `git diff --check`. Exact installed OCR 1.10.0 Darwin arm64 no-model probes
  pass in isolated temporary homes: CLI minimum/normalization target `50`,
  effective template value `100`, and explicit `101` producing 101 rounds.
  The enriched production caller performs collection, store/bootstrap, MCP
  registration/self-query, and exact preview before its controlled model
  boundary; the parsed normalization becomes only a CI notice and leaves result
  warnings, DLP, receipt, posting, telemetry, and approval inputs unchanged.
- Final local quality gate passes 1,269 tests plus 310 subtests at 86.16%
  combined branch coverage; risk groups report 84%, 82%, 85%, and 87% against
  floors 80%, 80%, 85%, and 85%. Ruff format/check, strict MyPy, Bandit,
  manifest validation, the rendered 0.8.3 Towncrier draft, and complete
  requirement/privacy/data-flow self-review pass. The first gate invocation
  stopped before tests on four format-only differences; Ruff formatted those
  files, signed commit `743d8fa` amended the logical slice, and the complete
  gate then passed on the corrected implementation head.
- Protected hosted checks subsequently passed on exact pushed head
  `e5a889ff2c415adc1dbce706582da5480024cc7d` and tree
  `1b89c1a69a7014baa0199343c457e7eb69419697`; PR #141 remained Draft, #139/#140
  acceptance boxes were checked, and both issues plus milestone stayed open.
- The user then approved an additive numeric tool-activity breakdown in the
  existing format. No repository or GitHub write for that new slice preceded
  this resumed-plan materialization.
- #142 now owns the additive feature under milestone `v0.8.3`. The combined
  focused formatter, posting, result-DLP, approval, documentation, and release
  gate passes 330 tests plus 133 subtests; the rendered Towncrier draft keeps
  #142 under Features with #139/#140 separately under Bug Fixes.
- Feature self-review confirms only the nine compile-time native/context/evidence
  labels and bounded positive integer counts can enter the inline line. Unknown
  or dynamic names remain private, static labels cannot create DLP false
  positives, filtered projections retain safe native counts, and the aggregate
  token line plus receipt/approval authorities are unchanged.
- Final local quality passes 1,275 tests plus 324 subtests at 86.35% combined
  branch coverage. Risk groups pass at 84%, 82%, 86%, and 87% against floors
  80%, 80%, 85%, and 85%; Ruff format/check, strict MyPy, and Bandit pass.
  Lock and OCR-manifest validation, the rendered Towncrier draft,
  checksum-verified temporary Gitleaks 8.24.3, `git diff --check`, and clean-tree
  confirmation also pass. The global Gitleaks installation and OCR/LLM state
  were not changed.

#### Risks And Recovery

- A stale evidence artifact may coexist with failure status. Recovery: bind issue
  selection to step outcome and keep aggregate dependent on the restored red job.
- Status output itself may encounter unsafe/partial filesystem state. Recovery:
  use a bounded same-directory atomic writer and fail the job without adopting a
  partial status; workflow upload remains diagnostic, never promotion evidence.
- Future OCR diagnostics may change spelling or semantics. Recovery: exact closed
  parsing and compatibility probes fail closed; promote a new grammar only with a
  checksum-pinned OCR release and tests.
- The OCR help/runtime/template mismatch can mislead documentation. Recovery:
  document sentinel ownership and observed behavior separately; never derive a
  runtime contract from help text alone.
- External write or hosted CI failure: preserve local commits and Draft PR, record
  exact run evidence, fix only the demonstrated boundary, and rerun its focused
  gate before a new signed commit.
- Tool counts can be mistaken for token allocation, and one tool call can return
  very different context volume from another. Recovery: label them only as OCR
  tool calls, retain the separate aggregate token line, document the limitation,
  and never compute per-tool token shares.
- A hostile or future OCR result can add names or excessive counters. Recovery:
  admit only the closed useful set, validate bounded integer counts, sort
  deterministically, and omit unknown/raw entries without changing review or
  approval state.

#### Resume Point

After this handoff commit, push the accumulated signed history once, update Draft
PR #141 and #142 with the exact remote head/tree, and wait for protected hosted
checks. If green, the next authorized agent starts from review of that immutable
Draft head rather than repeating local development. Do not merge or start release
delivery.

#### Plan Fidelity Check

- [x] Every requested issue acceptance criterion maps to a stable requirement and work item.
- [x] Release target, local-LLM waiver, privacy boundaries, and unchanged contracts are explicit.
- [x] Inputs distinguish current repository behavior, official OCR source, and observed probes.
- [x] Rejected scope and overengineering boundaries are explicit.
- [x] Each logical commit has focused verification and self-review gates.
- [x] External writes, hosted delivery, recovery, and exact resume state are represented.
- [x] The accepted tool list, current-format decision, token-attribution
  non-claim, and unknown/external-tool privacy boundary are explicit.

#### Reconciliation Check

- [x] `PLANS.md` was inactive and the worktree was clean at activation.
- [x] #139, #140, and #142 are the complete open release issue set and do not conflict with backlog/roadmap scope.
- [x] Stable 0.8.2 closure remains historical and is not rewritten.
- [x] Target 0.8.3 matches `.next-version` and no competing milestone exists.
- [x] The new reporting slice extends the open Draft and milestone without
  changing the completed #139/#140 contracts or deferred-release boundary.

#### Closure Gate

- [x] All implementation requirements and in-scope work items are terminal with current local validation evidence.
- [x] Complete diff self-review confirms issue, workflow, subprocess, privacy, DLP, approval, and documentation boundaries.
- [ ] Exact feature head is green locally and in protected hosted checks with resolved review threads.
- [ ] PR #141 remains Draft at the exact pushed head; #139/#140/#142 and milestone `v0.8.3` remain open.
- [x] The active plan retains an exact external-review/release resume point and is not archived before deferred delivery; this repository has no separate plan-lifecycle checker.

#### Post-Close Delivery

- This run ends at a pushed green Draft PR. Feature implementation does not close
  through merge, and no TestPyPI/PyPI or stable publication is authorized.
- A later owner-authorized continuation must review the exact Draft head, preserve
  or amend the plan from current state, then use the protected feature/release
  lifecycle. Readiness is not delivery.
- #139/#140/#142 and milestone `v0.8.3` remain open until stable receipt publication.
- Final handoff must repeat that no local real-LLM/provider qualification was run
  or claimed, while identifying the exact deterministic OCR boundary evidence.
- #142 and its feature fragment separately own the manager-facing reporting
  change; #139 and #140 stay checked/open and do not absorb it.
- Final handoff must state that tool-call counts explain review activity only;
  exact per-tool token consumption remains unavailable in OCR 1.10.0.

#### Handoff Notes

- Start at `WQ-01`; do not implement from an uncommitted or compressed substitute.
- The source-level max-tools mismatch is material: reported normalization `50`
  and embedded template default `100` are distinct facts. Preserve that distinction
  in code, evidence, docs, changelog, issue updates, and future OCR upgrades.
