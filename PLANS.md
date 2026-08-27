# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Toolkit 0.8.5 - provider diagnostics, OCR 1.10.2, and compatibility scheduling

Status: active

#### Goal

Deliver a production-ready Draft feature pull request for toolkit 0.8.5 that implements
issue #149's bounded provider diagnostics, qualifies and adopts OCR 1.10.2, moves the
daily compatibility discovery after the observed upstream release window, reconciles
upstream capabilities with the durable backlog, and leaves stable publication deferred.

#### Plan Origin

`plan_mode_approved`

#### Requested Scope

- Take open issue #149 and the canonical OCR 1.10.2 compatibility issue into one
  `v0.8.5` milestone and assign them to the repository owner.
- Change the single daily compatibility cron from `05:41 UTC` to `07:15 UTC`, retaining
  manual dispatch as the recovery path.
- Manually qualify exact OCR 1.10.2 rather than waiting for the next scheduled run.
- Promote the checksum-pinned compatibility manifest, preflight, GitLab example, current
  documentation, and effective Rules contract to OCR 1.10.2.
- Update the PATH-effective local Darwin arm64 OCR to 1.10.2 atomically after checksum
  verification and no-LLM isolated checks.
- Add one bounded deterministic CI diagnostic line derived only from a fully validated
  `ocr.llm-retry-report/v1`, without changing the merge-request summary structure.
- Reconcile every relevant OCR 1.10.2 capability and #149 outcome against backlog goals,
  activation triggers, dependencies, and acceptance criteria.
- Finish at a green Draft feature PR. Do not merge, prepare a release PR, tag, or publish
  toolkit 0.8.5.

Release classification: `release-required`; target stable version: `0.8.5`; delivery
state for this task: `release-deferred` at the green Draft PR boundary.

#### Requirement Traceability

| Requirement | Outcome | Queue | Verification |
| --- | --- | --- | --- |
| `REQ-001` | Start from synchronized released `v0.8.4`, materialize this complete plan first, and open a Draft PR after one signed planning commit/push. | `WQ-01` | Plan fidelity, signed commit, remote branch, Draft readback |
| `REQ-002` | Create milestone `v0.8.5`; assign/milestone #149 and the canonical OCR 1.10.2 issue while leaving both open. | `WQ-02` | GitHub API readback |
| `REQ-003` | Run daily compatibility discovery at `07:15 UTC` with manual recovery retained. | `WQ-03` | Exact workflow contract test and documentation test |
| `REQ-004` | Qualify and adopt checksum-pinned OCR 1.10.2 without weakening compatibility gates. | `WQ-02`, `WQ-03` | Hosted run, evidence/manifest validation, exact hashes, focused probes |
| `REQ-005` | Classify every upstream 1.10.2 change and reconcile any completed or partially satisfied backlog item. | `WQ-03` | Source audit, backlog/roadmap/strategy consistency review |
| `REQ-006` | Update local OCR to 1.10.2 without LLM calls or user configuration changes. | `WQ-03` | Binary digest/version/help and isolated Solidity/Vyper preview |
| `REQ-007` | Produce at most one closed numeric provider diagnostic line from a strictly validated retry report. | `WQ-04` | Parser, renderer, bounds, aggregation, and hostile-input tests |
| `REQ-008` | Preserve GitLab summary shape, prior review, DLP, receipt, telemetry, and approval boundaries while improving remediation text. | `WQ-04` | Posting/review/approval/privacy regressions |
| `REQ-009` | Document current behavior and classify dependency, Rules, feature, and scheduling changes accurately for humans and release agents. | `WQ-03`, `WQ-05` | Towncrier draft and documentation contract tests |
| `REQ-010` | Complete one local final gate, one final push, hosted CI reconciliation, and exact Draft handoff state. | `WQ-05`, `WQ-06` | Quality/coverage/Gitleaks/checks, PR/head/tree/status readback |

#### Explicit Non-Goals

- No real LLM or provider request, local model peer, OCR config/credential change, or
  caller-owned `HOME` use.
- No second scheduled compatibility run, dynamically calculated cron, polling service,
  or general provider-diagnostics framework.
- No new environment variable, public OCR result schema, receipt field, telemetry field,
  DLP input, or approval signal.
- No raw provider response parsing or publication of provider/model/task identity,
  response text, headers, URLs, request IDs, paths, warnings, or stderr.
- No toolkit consumption of OCR's GitHub Action checkpoint ranges or `ocr session
  compare`; resemblance alone does not activate or close backlog work.
- No mechanical test-directory reorganization, production refactor solely for coverage,
  stable release, issue closure, milestone closure, merge, tag, or registry publication.

#### Constraints

- Keep one owner for retry-report validation and let review/post consume the same closed
  projection; provider-controlled strings never cross that boundary.
- The GitLab renderer consumes only the existing closed reason. Numeric diagnostics stay
  in toolkit-controlled CI output and cannot affect DLP, receipt v5, findings, severity,
  suppression, resolution, or automatic approval.
- Only positive/bounded schema counts and HTTP statuses `100..599` are admitted.
  Malformed, oversized, contradictory, unknown-version, or unsupported reports retain the
  existing generic fail-closed behavior.
- Omit unavailable and zero counters. Emit a single `detail=` for one terminal category,
  deterministic `details=<category>:<count>,...` for mixed categories, and `status=` only
  for one shared HTTP status.
- Use `http-payment-required` for 402 and `http-rate-limited` for 429 without claiming a
  provider business cause. Other details remain closed and provider-neutral.
- Recovered requests affect aggregate counts but never the terminal failure reason.
- A backlog item becomes completed only when its acceptance criteria are met. Partial
  overlap updates the item's upstream overlap and remaining criteria without a false
  completion claim.
- Every production/test function added in this work receives a purpose-focused docstring.
- Before each signed logical commit: focused tests, complete slice diff review,
  trust/data-flow/privacy review, requirement/backlog reconciliation, and
  `git diff --check`.
- After the initial Draft push, do not push again until local implementation and the final
  gate are complete.

#### Inputs And Sources

- Approved implementation plan in the preceding Plan Mode conversation.
- Open toolkit issue #149 and released toolkit `v0.8.4`/next line `0.8.5`.
- Official OCR v1.10.2 release, release assets, checksums, comparison with v1.10.1, and
  upstream PRs #961, #945, #946, #1066, and #1067.
- Current `compatibility/ocr-support.json`, compatibility workflow, evidence harness,
  provider-failure parser, review runner, posting workflow, tests, public docs, strategy,
  roadmap, and backlog.
- Observed 30-release sample: approximately 5.35 stable releases/week, 27.3-hour median
  interval, and long-window publish density around 06:43 UTC. OCR 1.10.2 was published at
  05:49 UTC after the current 05:41 cron; no 2026-08-27 scheduled run existed by 08:29 UTC.
- Exact release anchors: Linux amd64
  `e9205614f80e009ee7b1f444c9da08486fb9ff6db022954fe9203d923ab720b2`, Darwin arm64
  `74fc7bcc0e6d0790c5ca033fd82a5474b6f05d443ed51a26a6f61c0cac6589fd`, and
  `sha256sum.txt` `b5176aaa04a7f00bd84dd61556ca29e6cbdfcfe64cc50af6653163d9be4e7654`.

#### User Decisions And Answers

- Delivery ends at a green Draft PR; stable toolkit 0.8.5 publication is deferred.
- Use one daily `07:15 UTC` compatibility check, not two checks.
- Update any backlog item that toolkit or OCR actually closes; update partial overlap
  truthfully and keep unmet work open.
- Update the local OCR binary, but skip local LLM execution.
- Work efficiently in complete logical commits with self-review before each commit.

#### Completed Baseline State

- `main` is synchronized and clean at released toolkit v0.8.4 commit `299e7b1`.
- `.next-version` is `0.8.5`; `PLANS.md` contained no active work before this plan.
- Issue #149 is the only open toolkit issue; no open PR or `v0.8.5` milestone exists.
- OCR compatibility is active, daily at `05:41 UTC`, and supports exact manual tags.
- The manifest recommends OCR 1.10.1; local `/opt/homebrew/bin/ocr` reports 1.10.1.
- Existing retry-report v1 validation already maps terminal failures to a closed public
  reason but discards safe aggregate/status detail.
- Repository workflow audit classified the repository as mature with canonical plan,
  backlog, principle, instruction, and documentation-index owners present.

#### Current Work Queue

| Queue | Status | Deliverable |
| --- | --- | --- |
| `WQ-01` | `completed` | Planning commit `123c331` was signed and pushed once; Draft PR #150 is open. |
| `WQ-02` | `completed` | Milestone `v0.8.5` owns assigned open issues #149/#151; hosted run 33055459209 qualified exact OCR 1.10.2. |
| `WQ-03` | `completed` | OCR 1.10.2 pins/evidence, schedule, classifier correction, current docs/Rules, source audit, backlog reconciliation, and local no-LLM update are complete. |
| `WQ-04` | `pending` | Implement the single closed provider diagnostic projection/renderer and GitLab remediation with boundary regressions. |
| `WQ-05` | `pending` | Finalize changelog/docs/plan truth and run the complete local gate once. |
| `WQ-06` | `pending` | Push the complete history once, reconcile hosted CI, update Draft/issue coordination with exact evidence, and verify final state. |

#### Locked Decisions

- Branch: `codex/v0.8.5-provider-diagnostics-ocr-1.10.2`; Draft base: protected `main`.
- Schedule: `15 7 * * *`; `workflow_dispatch` remains unchanged.
- Provider data flow:
  `private OCR result -> bounded retry-report parser -> closed numeric projection ->`
  `one toolkit-authored CI line`; GitLab continues to receive only the public reason.
- Example single-detail output:
  `OCR provider diagnostics: summary=rate-or-spending-limit detail=http-rate-limited status=429 failed_requests=1 retried_requests=1 total_retries=2`.
- Mixed output uses deterministic category counts and omits a non-uniform status.
- Rate/spending remediation recommends lowering `OCR_REVIEW_CONCURRENCY` and/or
  `OCR_LLM_MAX_COMPLETION_TOKENS`, starting a new MR pipeline, then checking provider
  request/account limits; it never states the cap is the proven cause.
- OCR 1.10.2 Solidity/Vyper support is a Rules change. Pin/evidence/schedule work is
  Maintenance. #149 is a Feature. Do not combine or misclassify these release notes.
- BL-021 remains conditional because an upstream GitHub Action is not a toolkit forge
  adapter. BL-010 is not activated by review-language rules alone. #149 remains bounded
  operator output and does not reopen the completed telemetry/export audit.

#### Verification

- Focused workflow/compatibility tests for exact cron, manual dispatch, evidence, hashes,
  manifest/preflight/example consistency, and Rules documentation.
- No-LLM exact OCR 1.10.2 version/help and Solidity/Vyper selection/rule preview in an
  isolated temporary home.
- Provider parser/renderer cases for 400, 401, 402, 403, 404, 408, 409, 413, 422, 429,
  5xx, 529, timeout, network, response decode/status/stream, cancellation, retries,
  recovery, grouping/grace-round records, mixed aggregation, bounds, zero omission,
  malformed/oversized/contradictory inputs, and deterministic rendering.
- Privacy regressions prove credentials, provider body/code, URL, model, request ID, task
  identity, paths, warnings, and stderr do not enter toolkit-controlled logs, GitLab
  notes, receipts, DLP signals, or approval inputs.
- Lifecycle regressions prove previous review preservation, no failed-result findings,
  no approval, unchanged public classification, and strict/non-strict posting behavior.
- Final local gate once: `scripts/quality.sh check`, all coverage floors,
  `scripts/ocr_compat.py validate`, lock check, Towncrier draft, `scripts/gitleaks.sh`,
  and `git diff --check`. Hosted PR workflows own package/OS/Python/Security/CodeQL gates.

#### Latest Validation Results

- 2026-08-27: synchronized `main` to released v0.8.4 commit `299e7b1`; worktree clean.
- 2026-08-27: engineering-workflow repository audit reported `mature_repo`, complete
  required documentation indexes, and all canonical workflow owners present.
- 2026-08-27: live GitHub readback found open #149, no open PR, no open milestone, active
  compatibility workflow, and no scheduled compatibility run for the day by 08:29 UTC.
- 2026-08-27: signed planning commit `123c331` was pushed and Draft PR #150 opened;
  milestone `v0.8.5` was created and assigned open issues #149/#151.
- 2026-08-27: hosted run 33055459209 passed OCR 1.10.2 checksum and compatibility
  probes. Human semantic review overrode its erroneous `automatic-safe` result because
  the release contains Features; the classifier now routes feature-bearing patches to
  human review.
- 2026-08-27: exact local Darwin arm64 OCR 1.10.2 at SHA-256
  `74fc7bcc0e6d0790c5ca033fd82a5474b6f05d443ed51a26a6f61c0cac6589fd` passed
  version/help, isolated Solidity/Vyper selection/rule checks, and a loopback-only
  semantic grouping probe with cap `16384` and default-medium stage sequence. No external
  LLM/provider call or user OCR configuration change occurred.
- 2026-08-27: 104 focused compatibility/workflow/environment tests pass; manifest
  validation, focused Ruff, Towncrier draft, and `git diff --check` pass.

#### Risks And Recovery

- GitHub scheduled workflows may be delayed or omitted. The later cron fixes the observed
  pre-release ordering but does not claim delivery guarantees; exact manual dispatch is
  the retained recovery path.
- The hosted compatibility run may classify 1.10.2 as human-review-required or fail. Keep
  its canonical issue/evidence, perform semantic review, and do not promote until every
  consumed contract is reconciled.
- An automation PR may appear. Compare its exact patch; integrate only reviewed bytes into
  this Draft and close/supersede the automation PR truthfully.
- Local OCR replacement may fail. Keep the verified 1.10.1 binary until the new binary
  passes all isolated checks and restore it on any post-replacement mismatch.
- A broader diagnostic projection could leak provider data or affect control flow. Keep
  the type closed/numeric, render through one bounded owner, and prove GitLab/DLP/approval
  independence with hostile values.
- Upstream features can resemble backlog outcomes without meeting toolkit acceptance
  criteria. Require exact goal/dependency/acceptance mapping before status changes.
- Hosted CI evidence may expose a real defect. Fix only the evidenced boundary through a
  separately reviewed signed commit; do not broaden scope or push partial work.

#### Resume Point

Begin `WQ-04` from the reviewed OCR 1.10.2 slice. Implement the single closed numeric
provider diagnostic owner and GitLab remediation regressions without changing public
summary, DLP, receipt, telemetry, or approval schemas. Do not push until WQ-05 completes.

#### Plan Fidelity Check

- [x] Every approved outcome has a stable requirement and queue owner.
- [x] Release classification, target, Draft-only boundary, and deferred stable delivery
  are explicit.
- [x] Inputs, exact hashes, schedule evidence, public/private data flow, backlog rules,
  non-goals, validation, recovery, and resume state are retained.
- [x] DLP, receipt, telemetry, approval, GitLab summary, local OCR, and no-LLM boundaries
  are explicit.
- [x] Initial and final push behavior plus hosted ownership are explicit.

#### Reconciliation Check

- [x] Current `main`, tag, next version, open issues/PRs/milestones, local OCR, workflow,
  plan, and worktree were read before this first write.
- [x] Current backlog, strategy, roadmap, compatibility, release, development, operations,
  security, and GitLab owners were identified for focused reconciliation.
- [ ] OCR 1.10.2 semantic audit/evidence and canonical issue are reconciled.
- [ ] Backlog/roadmap/strategy status agrees with demonstrated upstream/toolkit outcomes.
- [ ] Final diff, validation, Draft, issues, milestone, remote ref, and hosted CI agree.

#### Closure Gate

- [ ] All requirements and queue items are `done` or explicitly `out_of_scope`.
- [ ] Every logical commit passed focused tests, self-review, boundary review, and
  `git diff --check`.
- [ ] Final quality, coverage, OCR validation, lock, Towncrier, Gitleaks, and diff gates
  are green on the exact final tree.
- [ ] Hosted required checks are green and the Draft PR has no unresolved conversations.
- [ ] #149 and the OCR issue remain open in milestone `v0.8.5`; milestone remains open.
- [ ] Draft remains unmerged; no release PR, tag, registry publication, or stable closure
  occurred.

#### Post-Close Delivery

- This task ends with a green Draft feature PR and an explicit `release-deferred` state.
- Merge, protected-main TestPyPI publication, `release/v0.8.5`, stable registries, tag,
  immutable GitHub Release, issue receipts/closure, milestone closure, and independent
  external reconciliation require a later owner instruction.
- Hosted package, OS/Python, Dependency Review, Security, and CodeQL jobs are required PR
  evidence but are not duplicated locally.

#### Handoff Notes

- Final Draft body must identify toolkit target 0.8.5, OCR target 1.10.2, exact head/tree,
  exact OCR hashes and qualification run/issue, schedule rationale, Added/Fixed/Changed/
  Unchanged behavior, backlog disposition, local no-LLM checks, and hosted validation.
- The next agent starts from the exact Draft head; it does not rerun completed local
  development or publish stable 0.8.5 without explicit authorization.
