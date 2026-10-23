# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Toolkit 0.13.0: protected default-policy fallback for single-MR review

plan_schema_version: 2
Status: active
Last Updated: 2026-10-23
Release classification: #264 `release-required`, target v0.13.0; #265 `no-release` planning in the same feature PR.

#### Goal

Implement #264 without conflating the actual MR code target with protected policy authority, record the conditional #265 follow-up without activating chain review, and deliver, independently verify, and reconcile the stable v0.13.0 release through the protected repository workflow.

#### Plan Origin

`plan_mode_approved`

#### Requested Scope

The feature PR contains #264 implementation and public-contract updates plus a separate logical documentation commit for #265. Its first commit contains only this reviewed plan. Self-review every subsequent logical commit. Before the final feature push, run Codex Security on the changed range, then one real local toolkit/OCR review through the documented private-artifact path and fix admitted findings. Audit project documentation, agent instructions, and routes; correct any findings in a separate commit before final reviews. Use the protected feature PR, development artifact verification, protected release PR, stable publication/receipt, issue closure, site check after actual publication, and one `no-release` external-reconciliation PR. Do not run additional checks on another host or environment.

#### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Absent protection setting selects `auto`; explicit `required` and `unprotected`, malformed values, local entry point, and existing operator-file contracts retain their stated behavior | WQ-02, WQ-05 | pending |
| REQ-002 | Authenticate same-project MR and bind source H, actual target T, validated diff base/version B, and invocation; qualify detached, merged-result, and merge-train forms without synthetic-source confusion | WQ-02, WQ-03 | pending |
| REQ-003 | For an actually unprotected target, select the same project's protected default branch and immutable P; enforce rule provenance and preserve context/federation controls without pretending the target is protected | WQ-03, WQ-04 | pending |
| REQ-004 | Version result/receipt identity and capability decisions; reject old/forged contradictions, retain supported historical readback, and render truthful provenance and comment-only outcomes | WQ-04, WQ-05 | pending |
| REQ-005 | Revalidate code and authority before publication and approval; stale or unverifiable identity fails closed, bounded policy-only fast-forward remains pinned to P, and unprotected targets never receive new approval | WQ-05 | pending |
| REQ-006 | Preserve early exits, evidence applicability, DLP, current-MR context, ordinary outcomes, previous-review lifecycle, and controlled boundary budgets | WQ-03, WQ-04, WQ-05 | pending |
| REQ-007 | Update public configuration, GitLab examples, context, operations, security threat model, decision flow, strategy/roadmap, README, evidence matrix, and migration/changelog entry coherently | WQ-06, WQ-08 | pending |
| REQ-008 | Record #265 as inactive BL-025 with its durable issue links, full backlog fields, per-variant #264 dependencies, A–F alternatives, relationship shapes, request surfaces, activation authority, validation and non-claims; reconcile the merged entry back to #265 without runtime or public setting | WQ-07, WQ-09 | pending |
| REQ-009 | Review every commit; run applicable tests, secret scan, security diff scan, real local OCR review, and protected feature PR checks | WQ-01, WQ-02–WQ-09 | pending |
| REQ-010 | Publish and independently read back v0.13.0 distributions, provenance, attestation, tag, immutable Release, receipt, tracked issue/milestone, and post-release site notification | WQ-10, WQ-11 | pending |
| REQ-011 | Reconcile exact external facts and leave `PLANS.md` clean in the protected `no-release` closure PR | WQ-12 | pending |

#### Explicit Non-Goals

No related-MR discovery, chain/integration review, merge orchestration, source-branch policy bootstrap, fork/cross-project authority, new CI variable or policy field, second model pass, direct external MCP passthrough, approval revocation, downstream-project mutation, or new public command for #265. No separate host QA. Actual target protection is not a coverage score, and a successful current-MR review does not prove a parent or future integration.

#### Constraints

- GitLab acquisition is authenticated, bounded, and same-project; missing or contradictory source/target/project, diff, branch protection, default metadata, or Git objects fail with explicit diagnostics, not inferred fallback.
- `B..H` is the current MR delta. `B != T` is valid if the authenticated MR diff identity is coherent. Never substitute `P..H`, `T..H`, synthetic `CI_COMMIT_SHA`, or unrelated CI evidence.
- Capture actual target branch/head/protection and policy project/branch/P/protection separately. Only a protected authority may supply rules, context policy and eligible guidance; changed feature-branch material remains untrusted evidence. External absolute or omitted rule forms cannot claim P provenance.
- Preserve `off|metadata|enriched`, governed registry-v2 admission and budget gates, same-revision evidence, accepted-decision applicability, DLP, immutable Git isolation, existing setup-pending/two-MR onboarding, and terminal/stale/no-change lifecycle boundaries.
- Recheck the bound code tuple and authority before each provider write. Policy-only advancement is acceptable only with bounded proof of same protected branch and ancestry; keep captured P. Changed default/protection, rewrite, missing authority, or unverifiable ancestry fail closed. Read-before-write retains a residual provider race.
- An actually unprotected target is always comment-only, including when `OCR_AUTO_APPROVE=true`; prior bot approvals may remain and are not revoked. Protected targets keep their own policy and approval gates.
- Use only synthetic/private-safe examples and artifacts. Follow signed, linear protected PR and trusted-base release authorization; no manual mutation of immutable release objects.

#### Inputs And Sources

- Live [#264](https://github.com/xeonvs/open-code-review-toolkit/issues/264) (updated 2026-10-23 08:40 UTC) and [#265](https://github.com/xeonvs/open-code-review-toolkit/issues/265) (updated 08:31 UTC), including acceptance lists; GitLab's official MR/version, project, CI-variable, merged-results and merge-train API documentation.
- Current `main` baseline `b8786e7`, stable `.release-version=0.12.1`, next `.next-version=0.13.0`, empty active plan, and the completed v0.12.1 archive.
- Canonical owners: `AGENTS.md`, `docs/engineering/project_principles.md`, `docs/development.md`, `docs/release.md`, `docs/review-decision-flow.md`, `docs/review-context.md`, `docs/engineering/toolkit_strategy.md`, `ROADMAP.md`, `docs/codex/TASKS_BACKLOG.md`, and `docs/engineering/test_evidence_matrix.md`.

#### User Decisions And Answers

The owner selected a full stable v0.13.0 release after #264 and chose one feature PR containing #265 as a separate logical commit. The owner requested the previous release's plan-first, self-review, security then local OCR review, protected PR, artifact/receipt, site-after-release and clean plan closure sequence. The root agent must switch to the feature branch; #265 remains planning-only and does not itself authorize a release.

#### Completed Baseline State

v0.12.1 is published and externally reconciled; prior release and internal follow-up issues are closed. `main` was clean and synchronized with `origin/main` at `b8786e7`. Both current issues are open. `feature/264-auto-policy-0.13.0` was created from that baseline; no feature implementation exists yet. BL-024 is historical, so BL-025 is the next unused backlog identifier.

#### Current Work Queue

| Queue | Requirements | Exit evidence | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-009 | Review and commit only this plan; establish goal, milestone and feature PR identity | in_progress |
| WQ-02 | REQ-001, REQ-002, REQ-009 | Provider/config/CI identity changes and production-boundary tests; self-reviewed commit | pending |
| WQ-03 | REQ-002, REQ-003, REQ-006, REQ-009 | Immutable diff/authority/rule acquisition and applicability tests; self-reviewed commit | pending |
| WQ-04 | REQ-003, REQ-004, REQ-006, REQ-009 | Capability/context/federation, receipt/result v11 and hostile readback tests; self-reviewed commit | pending |
| WQ-05 | REQ-001, REQ-004–REQ-006, REQ-009 | Freshness, publication/approval, diagnostic and local-entry tests; self-reviewed commit | pending |
| WQ-06 | REQ-007, REQ-009 | Public contracts, examples, threat model, decision flow, changelog; self-reviewed commit | pending |
| WQ-07 | REQ-008, REQ-009 | Self-contained BL-025 with Source #265 and reference #264, status/theme/prerequisites/trigger/scope/deliverables/acceptance/exclusions/validation/future release classification; per-variant dependencies, A–F coverage, graph shapes and request/publication trade-offs; aligned strategy/roadmap and self-reviewed separate commit | pending |
| WQ-08 | REQ-007, REQ-009 | Documentation/instruction/route audit, distinct correction commit if needed, complete local quality and private/public-source checks | pending |
| WQ-09 | REQ-008, REQ-009 | Codex Security scan, corrected real local toolkit/OCR review, finding fixes and final feature PR checks/merge; link the merged BL-025 entry in #265 and record selected/deferred/rejected variants there | pending |
| WQ-10 | REQ-010 | Verified deterministic TestPyPI development wheel and sdist, release PR repository prep and protected checks/merge | pending |
| WQ-11 | REQ-010 | Stable TestPyPI/PyPI, provenance, attestation, immutable release/receipt, issue/milestone and real site readback | pending |
| WQ-12 | REQ-011 | One protected no-release reconciliation PR with exact receipts, clean plan, and synchronized main | pending |

#### Locked Decisions

Use `auto` as the absent-setting default and retain explicit modes. Use closed provider-neutral authority/capability identity with GitLab acquisition behind the adapter. Receipt v11 distinguishes code target from policy authority; historical v9/v10 remain readback-only under their original invariants, never guessed into a new profile. Choose clear rejection for unsupported pipeline or rule forms. Keep #265 in BL-025 only until separately activated by owner approval. Track only #264 in the v0.13.0 release issue set; close #265 through its feature PR after its planning deliverable is reviewed.

#### Verification

- Focused parser/provider, real temporary Git and bounded local HTTP, result/receipt hostile-readback, context/federation, posting/approval, lifecycle and source-identity tests for every #264 acceptance branch; preserve exact owner entry points and note test doubles beyond them.
- Public example/preflight and `--local` contract tests, clean installed wheel/sdist runtime probes, one actual OCR review for changed model-visible behavior, plus `scripts/quality.sh check`, `scripts/gitleaks.sh`, instruction-contract lint if routes change, documentation links/semantic audit and final scoped diff review.
- Codex Security diff scan after implementation and before final feature push; then one correctly invoked local toolkit/OCR review to completion with private physical output path, terminal status, report and findings readback; fix findings and rerun only on a genuine failed launch or authorized correction.
- Exact required protected feature/release PR checks; stable workflow's independent hash, registry provenance, supported-Python installed smoke, immutable receipt readback and post-publication external verification. Check the live site only after release notification/deployment.

#### Latest Validation Results

Baseline only: clean synchronized `main`, issues read at the update times above, `.release-version` and `.next-version` confirmed. No feature tests, security scan, local OCR review or external release gate has run yet.

#### Risks And Recovery

GitLab diff/version and pipeline variants may require rejecting unsupported forms before model work; do not guess identity. Shallow Git history may prevent proving policy fast-forward; fail closed with actionable stale/security outcome. If protection/default selection or target changes during review, retain earlier valid publication and report stale. External publication or workflow state must be read back before retry; resume a failed authorized release through its documented exact-artifact recovery rather than republishing different bytes. Preserve private review artifacts until report and admitted findings are verified.

#### Resume Point

WQ-01: the plan-only signed commit and explicit goal are established, and the current issue cross-check is reflected here. Next establish the release milestone and feature PR identity before runtime edits.

#### Plan Fidelity Check

- [x] #264 and #265 outcomes, non-goals, updated #264 identity/freshness additions, and user decisions map to REQ and ordered WQ items.
- [x] Release classification, 0.13.0 target, #265 no-release boundary and plan/closure ownership are explicit.
- [x] Each acceptance family has focused verification and production-boundary evidence; reviews, site timing, and external receipts have owners.
- [x] Risks, fail-closed recovery, immutable artifacts and first safe unfinished action are recorded.

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
