# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Toolkit 0.13.0: protected default-policy fallback for single-MR review

plan_schema_version: 2
Status: active
Last Updated: 2026-10-23
Release classification: #264 `release-required`, target v0.13.0; #265 `no-release` planning and the requested harness maintenance are separate logical changes in the same feature PR.

#### Goal

Implement #264 without conflating the actual MR code target with protected policy authority, record the conditional #265 follow-up without activating chain review, and deliver, independently verify, and reconcile the stable v0.13.0 release through the protected repository workflow.

#### Plan Origin

`plan_mode_approved`

#### Requested Scope

The feature PR contains #264 implementation and public-contract updates plus a separate logical documentation commit for #265. Its first commit contains only this reviewed plan. Self-review every subsequent logical commit. Before the final feature push, run Codex Security on the changed range, then one real local toolkit/OCR review through the documented private-artifact path and fix admitted findings. Audit project documentation, agent instructions, and routes; correct any findings in a separate commit before final reviews. Use the protected feature PR, development artifact verification, protected release PR, stable publication/receipt, issue closure, site check after actual publication, and one `no-release` external-reconciliation PR. Clean obsolete completed-run GitHub Actions artifacts and superseded caches without touching published Release assets or active-run inputs. Do not run additional checks on another host or environment.
The owner later requested an Astra harness/process audit. Its bounded current-branch follow-up removes one duplicate setup shared by two negative installed-artifact probes and preserves the failing command's exit status in the quality wrapper; keep both wheel/sdist behavioral cases and independent published-artifact gates. Capture per-test durations in the next required full quality run rather than adding a separate heavy measurement run.

#### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Absent protection setting selects `auto`; explicit `required` and `unprotected`, malformed values, local entry point, and existing operator-file contracts retain their stated behavior | WQ-02, WQ-05 | done |
| REQ-002 | Authenticate same-project MR and bind source H, actual target T, validated diff base/version B, and invocation; qualify detached, merged-result, and merge-train forms without synthetic-source confusion | WQ-02, WQ-03 | done |
| REQ-003 | For an actually unprotected target, select the same project's protected default branch and immutable P; enforce rule provenance and preserve context/federation controls without pretending the target is protected | WQ-03, WQ-04 | done |
| REQ-004 | Version result/receipt identity and capability decisions; reject old/forged contradictions, retain supported historical readback, and render truthful provenance and comment-only outcomes | WQ-04, WQ-05 | done |
| REQ-005 | Revalidate code and authority before publication and approval; stale or unverifiable identity fails closed, bounded policy-only fast-forward remains pinned to P, and unprotected targets never receive new approval | WQ-05 | done |
| REQ-006 | Preserve early exits, evidence applicability, DLP, current-MR context, ordinary outcomes, previous-review lifecycle, and controlled boundary budgets; expose actual target T as distinct untrusted code evidence when B and P differ | WQ-03, WQ-04, WQ-05 | done |
| REQ-007 | Update public configuration, GitLab examples, context, operations, security threat model, decision flow, strategy/roadmap, README, evidence matrix, and migration/changelog entry coherently | WQ-06, WQ-08 | done |
| REQ-008 | Record #265 as inactive BL-025 with its durable issue links, full backlog fields, per-variant #264 dependencies, A–F alternatives, relationship shapes, request surfaces, activation authority, validation and non-claims; reconcile the merged entry back to #265 without runtime or public setting | WQ-07, WQ-09 | in_progress |
| REQ-009 | Review every commit; run applicable tests, secret scan, security diff scan, real local OCR review, and protected feature PR checks | WQ-01, WQ-02–WQ-09 | pending |
| REQ-010 | Publish and independently read back v0.13.0 distributions, provenance, attestation, tag, immutable Release, receipt, tracked issue/milestone, and post-release site notification | WQ-10, WQ-11 | pending |
| REQ-011 | Reconcile exact external facts and leave `PLANS.md` clean in the protected `no-release` closure PR | WQ-12 | pending |
| REQ-012 | Reclaim Actions storage from obsolete completed-run artifacts and superseded caches, with before/after readback and retained release/current-run evidence | WQ-13 | done |
| REQ-013 | Improve meaningful test coverage in touched Python modules, measuring affected-file coverage before and after the change | WQ-02–WQ-05, WQ-14 | in_progress |
| REQ-014 | Reduce duplicate installed-artifact negative-probe setup, preserve exact quality failure exit status, and record timing/process evidence without weakening wheel/sdist or registry gates | WQ-14 | done |

#### Explicit Non-Goals

No related-MR discovery, chain/integration review, merge orchestration, source-branch policy bootstrap, fork/cross-project authority, new CI variable or policy field, second model pass, direct external MCP passthrough, approval revocation, downstream-project mutation, or new public command for #265. No separate host QA. Actual target protection is not a coverage score, and a successful current-MR review does not prove a parent or future integration.
Do not drop wheel or sdist packaging, remove the existing installed local-review scenarios, or repeat full tests in the release publication gate to optimize this task. Matrix reduction awaits measured scenario timing and an independent maintenance decision.

#### Constraints

- GitLab acquisition is authenticated, bounded, and same-project; missing or contradictory source/target/project, diff, branch protection, default metadata, or Git objects fail with explicit diagnostics, not inferred fallback.
- `B..H` is the current MR delta. `B != T` is valid if the authenticated MR diff identity is coherent. Never substitute `P..H`, `T..H`, synthetic `CI_COMMIT_SHA`, or unrelated CI evidence. Preserve B/H deltas while exposing T as a separate bounded, untrusted code snapshot; T content never becomes P authority.
- Capture actual target branch/head/protection and policy project/branch/P/protection separately. Only a protected authority may supply rules, context policy and eligible guidance; changed feature-branch material remains untrusted evidence. External absolute or omitted rule forms cannot claim P provenance.
- Preserve `off|metadata|enriched`, governed registry-v2 admission and budget gates, same-revision evidence, accepted-decision applicability, DLP, immutable Git isolation, existing setup-pending/two-MR onboarding, and terminal/stale/no-change lifecycle boundaries.
- Recheck the bound code tuple, authority, and present CI job identity before each provider write. Policy-only advancement is acceptable only with bounded proof of same protected branch and ancestry; keep captured P. Changed default/protection, rewrite, missing authority, cross-job handoff, or unverifiable ancestry fail closed. Read-before-write retains a residual provider race.
- An actually unprotected target is always comment-only, including when `OCR_AUTO_APPROVE=true`; prior bot approvals may remain and are not revoked. Protected targets keep their own policy and approval gates.
- Use only synthetic/private-safe examples and artifacts. Follow signed, linear protected PR and trusted-base release authorization; no manual mutation of immutable release objects.

#### Inputs And Sources

- Live [#264](https://github.com/xeonvs/open-code-review-toolkit/issues/264) (updated 2026-10-23 08:52 UTC) and [#265](https://github.com/xeonvs/open-code-review-toolkit/issues/265) (updated 08:31 UTC), including acceptance lists; GitLab's official MR/version, project, CI-variable, merged-results and merge-train API documentation.
- Current `main` baseline `b8786e7`, stable `.release-version=0.12.1`, next `.next-version=0.13.0`, empty active plan, and the completed v0.12.1 archive.
- Canonical owners: `AGENTS.md`, `docs/engineering/project_principles.md`, `docs/development.md`, `docs/release.md`, `docs/review-decision-flow.md`, `docs/review-context.md`, `docs/engineering/toolkit_strategy.md`, `ROADMAP.md`, `docs/codex/TASKS_BACKLOG.md`, and `docs/engineering/test_evidence_matrix.md`.

#### User Decisions And Answers

The owner selected a full stable v0.13.0 release after #264 and chose one feature PR containing #265 as a separate logical commit. The owner requested the previous release's plan-first, self-review, security then local OCR review, protected PR, artifact/receipt, site-after-release and clean plan closure sequence. The root agent must switch to the feature branch; #265 remains planning-only and does not itself authorize a release.
The owner additionally requested cleanup of GitHub Actions run artifacts because storage is scarce; this is `no-release` operational work.
The owner also requested regular coverage improvement in touched files; focus on behavior and failure branches rather than tests that only reproduce an implementation.
The owner requested a separate Astra agent to audit harness duplication and process, then apply justified corrections. This scoped harness maintenance is `no-release` by itself and does not add another release trigger or publication job.

#### Completed Baseline State

v0.12.1 is published and externally reconciled; prior release and internal follow-up issues are closed. `main` was clean and synchronized with `origin/main` at `b8786e7`. Both current issues are open. `feature/264-auto-policy-0.13.0` was created from that baseline; its first signed commit contains only this plan and draft feature PR [#266](https://github.com/xeonvs/open-code-review-toolkit/pull/266) is open. Milestone v0.13.0 tracks #264 only. At activation no feature implementation existed. BL-024 is historical, so BL-025 is the next unused backlog identifier.

#### Current Work Queue

| Queue | Requirements | Exit evidence | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-009 | Review and commit only this plan; establish goal, milestone and feature PR identity | done |
| WQ-02 | REQ-001, REQ-002, REQ-009 | Provider/config/CI identity changes and production-boundary tests; self-reviewed commit | done |
| WQ-03 | REQ-002, REQ-003, REQ-006, REQ-009 | Immutable diff/authority/rule acquisition, distinct target T evidence/readback and applicability tests; self-reviewed commit | done |
| WQ-04 | REQ-003, REQ-004, REQ-006, REQ-009 | Capability/context/federation, receipt/result v11 and hostile readback tests; self-reviewed commit | done |
| WQ-05 | REQ-001, REQ-004–REQ-006, REQ-009 | Full-identity freshness at current-result and static-note writes, publication/approval/draft and cleanup boundaries, receipt-less error isolation, cross-run private-artifact isolation, and local-entry tests; self-reviewed commit | done |
| WQ-06 | REQ-007, REQ-009 | Public contracts, examples, threat model, decision flow, changelog; self-reviewed commit | done |
| WQ-07 | REQ-008, REQ-009 | Self-contained BL-025 with Source #265 and reference #264, status/theme/prerequisites/trigger/scope/deliverables/acceptance/exclusions/validation/future release classification; per-variant dependencies, A–F coverage, graph shapes and request/publication trade-offs; aligned strategy/roadmap and self-reviewed separate commit | done |
| WQ-08 | REQ-007, REQ-009 | Documentation/instruction/route audit, distinct correction commit, focused documentation checks and valid instruction contract | done |
| WQ-14 | REQ-014, REQ-009 | Astra-backed installed negative-probe setup and quality exit-status corrections, focused tests, docs, timing in the next full quality gate, separate self-reviewed commit | done |
| WQ-09 | REQ-008, REQ-009 | Codex Security scan, corrected real local toolkit/OCR review, finding fixes and final feature PR checks/merge; link the merged BL-025 entry in #265 and record selected/deferred/rejected variants there | in_progress |
| WQ-10 | REQ-010 | Verified deterministic TestPyPI development wheel and sdist, release PR repository prep and protected checks/merge | pending |
| WQ-11 | REQ-010 | Stable TestPyPI/PyPI, provenance, attestation, immutable release/receipt, issue/milestone and real site readback | pending |
| WQ-12 | REQ-011 | One protected no-release reconciliation PR with exact receipts, clean plan, and synchronized main | pending |
| WQ-13 | REQ-012 | Inventory completed-run artifacts/cache, delete only obsolete bytes, retain current PR and latest release evidence, verify remaining inventory and record reclaimed size | done |

#### Locked Decisions

Use `auto` as the absent-setting default and retain explicit modes. Use closed provider-neutral authority/capability identity with GitLab acquisition behind the adapter. Receipt v11 distinguishes code target from policy authority; historical v9/v10 remain readback-only under their original invariants, never guessed into a new profile. Choose clear rejection for unsupported pipeline or rule forms. Keep #265 in BL-025 only until separately activated by owner approval. Track only #264 in the v0.13.0 release issue set; close #265 through its feature PR after its planning deliverable is reviewed.

#### Verification

- Focused parser/provider, real temporary Git and bounded local HTTP, result/receipt hostile-readback, context/federation, posting/approval, lifecycle and source-identity tests for every #264 acceptance branch; preserve exact owner entry points and note test doubles beyond them.
- A B!=T!=P evidence fixture must prove T-only implementation facts are available as untrusted target evidence without changing B..H deltas, policy authority, historical store readback or bounded admission.
- Public example/preflight and `--local` contract tests, clean installed wheel/sdist runtime probes, one actual OCR review for changed model-visible behavior, plus `scripts/quality.sh check`, `scripts/gitleaks.sh`, instruction-contract lint if routes change, documentation links/semantic audit and final scoped diff review.
- Record baseline and final per-file coverage for touched Python modules, add meaningful branch/boundary tests where coverage is weak, and compare aggregate coverage without hiding new uncovered lines.
- Codex Security diff scan after implementation and before final feature push; then one correctly invoked local toolkit/OCR review to completion with private physical output path, terminal status, report and findings readback; fix findings and rerun only on a genuine failed launch or authorized correction.
- Exact required protected feature/release PR checks; stable workflow's independent hash, registry provenance, supported-Python installed smoke, immutable receipt readback and post-publication external verification. Check the live site only after release notification/deployment.

#### Latest Validation Results

Plan-only signed commit `d616e98` contains only `PLANS.md` and passed `git diff --check`; `scripts/gitleaks.sh --tree` and the reachable-range scan passed before its push. Draft PR #266 exists, and #264 is in milestone v0.13.0 while #265 remains outside it. At that plan-only point no feature test or review gate had run.
GitHub Actions inventory at 2026-10-23 shows 42 artifacts totaling 14,613,655 bytes and four caches totaling 142,839,380 bytes. The current draft-PR artifact is 7,171 bytes; the completed v0.12.1 release and its development-build artifact remain useful for recovery/readback. Two superseded uv caches account for 89,449,983 bytes. All 100 most recent workflow runs are completed.
All 195 listed workflow runs were confirmed completed. Deleted 21 obsolete distribution artifacts and two superseded uv caches. Readback lists 21 remaining artifacts totaling 1,422,439 bytes and two retained caches totaling 53,389,397 bytes, so listed stored bytes fell by 102,641,199. The current PR SARIF, latest release/development distributions, and immutable v0.12.1 Release assets remain; GitHub's cache-usage aggregate briefly lagged the cache listing after deletion.
Focused provider tests pass (68 tests, 2026-10-23). Review of the B!=T!=P execution path found a real evidence gap: T was fetched and stored in the receipt but not available through evidence MCP. WQ-03 now explicitly includes a versioned, bounded target evidence snapshot. The pre-change complete quality log from 2026-10-22 provides a comparable baseline for affected-file coverage; final numbers remain pending.
Signed self-reviewed implementation commits: `cd74ac4` binds detached MR CI, same-project provider and target/policy snapshot; `a1d056a` adds bounded target T evidence v5 and protected-P ancestry support; the following execution commit binds diagnostics and receipt v11, including the local-policy collection regression fix. Focused provider/local tests: 148 passed; evidence/freshness tests: 201 passed; execution/receipt/docs-contract tests: 254 passed. Full quality, security and local OCR gates remain pending until documentation is complete. Review of posting found additional mid-publication freshness transitions now being corrected in WQ-05.
Signed self-reviewed planning commit `76a1c3a` records conditional BL-025 for #265 and its roadmap placement without runtime changes or a release claim. Its scoped diff check passed. #265 still needs issue-body reconciliation after the feature PR merges.
WQ-05 focused source and boundary suites passed with 686 tests and 299 subtests after the CI-job handoff and current-version-contract additions. Ruff format/check, mypy across 132 source files, and diff whitespace checks passed. A second independent seam audit found the review-to-post interval in a shared checkout; receipt and preview/setup status now bind the supplied GitLab job ID, code 75 prevents a losing review from adopting another run's status, and the example uses job-specific output paths. Production GitLab uses one review/post pair per CI job. Full quality and final security/OCR reviews remain pending until WQ-06/WQ-08 documentation is committed.
Signed self-reviewed WQ-05 commit `d5bc468` contains the posting, cross-run, current-version contract and regression changes. WQ-06 public documentation now explains v11, default `auto`, B/H/T/P, job-specific handoff, local private paths and the no-note failure policy. The public GitLab example omits the selector so its still-published wheel pin remains valid until the release PR advances it; the new toolkit then supplies the `auto` default. The 51 focused documentation/example contracts passed.
Signed self-reviewed WQ-06 commit `58d29d3` contains the public docs, examples and changelog. Signed self-reviewed commit `0b416c8` makes the historical v9/v10/v11 nested-schema mapping explicit, so a future v12 cannot inherit a predecessor's federation or publication schema by fallback; 129 receipt/approval/freshness tests and 94 subtests passed. The WQ-08 documentation/instruction audit corrected context and federation ownership routes, engineering contracts and example links; the instruction contract is valid, the 51 focused documentation contracts pass, and full quality and final reviews remain pending.
The first full quality attempt stopped at a single Ruff formatting defect in the public-example contract test; it was corrected in amended documentation commit `ae83977`. The next full pytest/coverage run reached 86.36% total coverage and 2270 passing tests, but 14 tests still asserted obsolete local-status, private-error-note or historical-receipt publication behavior. Six affected test modules now assert the current no-write/no-status boundaries and retain late debug/progress coverage; 108 focused tests passed with three qualified skips before the successful complete run below.
Astra's read-only harness audit confirmed #260 is closed and the expensive installed-artifact suite already runs on one Ubuntu/Python 3.12 CI leg; other legs start in parallel, while stable publication verifies new artifacts without repeating full pytest. Different observed CI runs spanned 13m24s and 4m22s, which is directional evidence rather than a controlled benchmark. The remaining duplicate was two negative probes creating equivalent clean no-dependency environments. The quality wrapper also reduced an underlying failing command's exit status to 1 before the WQ-14 fix.
The bounded WQ-14 patch now shares one module-scoped wheel-only interpreter between both read-only negative dependency probes, preserves their distinct PATH/cwd assertions, and makes `scripts/quality.sh` propagate failure statuses. The fake-uv regression checks exit codes 2, 7 and 130 plus stop-before-coverage behavior. All 12 focused harness tests pass in 2.14 seconds; 40 focused documentation/environment tests, repository-wide Ruff check/format, instruction-contract lint and whitespace checks pass. The prior failed quality log is retained in a private task archive outside the repository.
The complete local quality gate now passes: 2288 tests, five qualified skips and 357 subtests in 295.67 seconds, with 86.47% aggregate line/branch coverage. The installed wheel/sdist MCP scenario accounts for 157.09 seconds; the shared negative-probe setup takes 1.06 seconds, and the independent wheel/sdist behavioral cases remain intact. Current changed-file coverage includes 100% for `posting/freshness.py` and `review_identity.py`, 88.02% for `review_receipt.py`, 86.74% for `providers/gitlab.py`, and 80.14% for `posting/workflow.py`. The available pre-change JSON was collected from an incomplete test run (70.24%) and is not a valid before/after baseline; do not report it as coverage growth. A public-tree secret scan passes. Astra's process recommendation is captured in the bounded harness commit; the remaining expensive integration matrix needs a separately measured follow-up before any reduction.

#### Risks And Recovery

GitLab diff/version and pipeline variants may require rejecting unsupported forms before model work; do not guess identity. Shallow Git history may prevent proving policy fast-forward; fail closed with actionable stale/security outcome. If protection/default selection or target changes during review, retain earlier valid publication and report stale. External publication or workflow state must be read back before retry; resume a failed authorized release through its documented exact-artifact recovery rather than republishing different bytes. Preserve private review artifacts until report and admitted findings are verified.

#### Resume Point

Run the Codex Security diff scan over `b8786e7..HEAD`, fix validated findings, then run the real local OCR review through physical private output paths. Reconcile final coverage without claiming a before/after change from incomplete baseline data; run the remaining secret and instruction gates before final feature push. Continue the protected PR and release lifecycle only after those results are reconciled.

#### Plan Fidelity Check

- [x] #264 and #265 outcomes, non-goals, updated #264 identity/freshness additions, and user decisions map to REQ and ordered WQ items.
- [x] Release classification, 0.13.0 target, #265 no-release boundary and plan/closure ownership are explicit.
- [x] Each acceptance family has focused verification and production-boundary evidence; reviews, site timing, and external receipts have owners.
- [x] Risks, fail-closed recovery, immutable artifacts and first safe unfinished action are recorded.
- [x] The newly requested Actions storage cleanup has an independent `no-release` requirement and readback owner.

#### Reconciliation Check

- [x] This plan reflects the current issue bodies and clean `b8786e7` baseline at activation.
- [ ] Reconcile changed implementation, test, PR, release and external facts before their dependent milestones and final archive.

#### Closure Gate

- [ ] Every in-scope requirement and queue item is done with final validation evidence.
- [ ] No issue, instruction, document, backlog or release state contradicts the delivered result.
- [ ] The protected release PR archives repository-complete work with external delivery pending; the closure PR records exact external receipts and leaves no active plan.

#### Post-Close Delivery

Pending: feature and release PRs, stable artifacts, immutable receipt, tracked issue/milestone, site check and protected no-release external reconciliation. Completion requires their independent readback, not a local commit or green advisory job alone.

#### Handoff Notes

Root owns `PLANS.md`, BL-025 status, commit sequencing, external writes and final synthesis. Delegated work must not close the plan or mutate shared plan state. At interruption, read this current plan and `git status`, then resume the first non-terminal WQ item without repeating side effects.
