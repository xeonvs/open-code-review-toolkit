# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Release 0.8.0: remediation threads, GitLab commands, and documentation

- Status: `active`
- Release classification: `release-required`
- Target stable version: `0.8.0`
- Stable delivery state: `release-deferred`

#### Goal

Deliver a backward-compatible, privacy-bounded remediation-thread context source, exact GitLab mention commands, a complete environment contract, mode-oriented GitLab examples, Accepted project decisions usage guidance, and navigation indexes. Keep the exact feature head in a Draft PR until an external OCR 1.9.9 plus LLM qualification proves the production path without leaking raw remediation or provider data.

#### Plan Origin

`plan_mode_approved`

#### Requested Scope

- Extend the protected review-context policy with optional `remediation_threads` under schema `ocr.review-context-policy/v2`; retain v1 behavior for existing enriched configurations.
- Acquire one verified toolkit-owned finding root and its admissible replies as one opaque remediation-thread record from a stable, twice-read GitLab snapshot.
- Expose remediation threads only through the local read-only context store/MCP projection, with DLP, budgets, closed state/counts, and run-local identities.
- Keep every review with admitted remediation text comment-only. Remediation prose may focus fresh inspection but cannot change severity, prove a fix, suppress a finding, resolve a thread, issue a lifecycle command, or enable approval.
- Obtain the active GitLab bot ID and username only from authenticated `GET /user` and support exact `@<live_bot_username> suppress|resolve` replies alongside existing `/ocr` commands.
- Remove obsolete or unsupported environment semantics and publish an exact, categorized environment-variable contract including defaults.
- Reorganize GitLab examples around supported operating modes, move context recipes beneath them, and demonstrate both creation and later consumption of Accepted project decisions.
- Remove obsolete GitLab migration prose, add three navigation-only documentation indexes, and reconcile README, strategy, roadmap, and release notes.
- Create three v0.8.0 sub-issues beneath GitHub issue #120 and keep #120, its sub-issues, milestone, and Draft PR open until stable external reconciliation.

#### Requirement Traceability

- `REQ-001` (`done`): materialized this full plan first, created the feature branch from synchronized `main`, made a signed planning commit, performed the one initial push, and opened Draft PR #122 before implementation. Covered by `WQ-01` and `WQ-02`.
- `REQ-002` (`done`): created v0.8.0 sub-issues #124, #125, and #123, attached them to #120, and appended/read back the coordination checklist without changing #120's core contract. Covered by `WQ-02`.
- `REQ-003` (`done`): implemented policy v1/v2 compatibility, a non-configurable remediation policy type, private store v2, and a fixed model-only safe remediation projection with a new closed MCP resource class. Covered by `WQ-03`.
- `REQ-004` (`done`): added a shared validated live `GET /user` identity owner and derive mutually exclusive generic discussions plus verified remediation bundles from one twice-read bounded snapshot; identity, edit, delete, reorder, and pagination drift fail closed as `mutated`. Covered by `WQ-04`.
- `REQ-005` (`done`): apply budgets and DLP before atomic storage, add MCP/bootstrap/receipt/cleanup integration, and preserve posting suppression, fingerprints, human ownership, resolve rollback, and receipt v5. Covered by `WQ-05`.
- `REQ-006` (`done`): apply DLP to every untrusted MR-derived text path, including title, description, generic discussions, remediation roots/replies, and adapter/reference content, before private-store or bootstrap admission. Keep each source's DLP admission/degradation isolated from receipt-based approval: safe non-remediation context must not block approval, DLP rejection cannot enable approval, and admitted remediation always forces comment-only. Covered by `WQ-05` and `WQ-06`.
- `REQ-007` (`done`): support exact whole-reply mention commands for the live bot username with slash-command parity and closed negative cases. Covered by `WQ-06`.
- `REQ-008` (`pending`): remove `OCR_GITLAB_BOT_USER_ID`; reject `OCR_USE_ANTHROPIC` with migration guidance; remove example `OCR_RUN_HELPER_TESTS` and unsupported documentation-only variables while retaining active controls and redaction sentinels. Covered by `WQ-07`.
- `REQ-009` (`pending`): publish a complete environment-variable/default contract separated by runtime, GitLab predefined, example-local, and dynamic adapter inputs, protected by an exact-set contract test. Covered by `WQ-07`.
- `REQ-010` (`pending`): reorganize GitLab examples by mode, relocate context recipes, remove user-facing `synthetic` labels, and demonstrate Accepted project decisions creation and later evidence list/get use. Covered by `WQ-08`.
- `REQ-011` (`pending`): remove 0.6.x migrations from `docs/gitlab.md`, document current v1/v2 compatibility in `docs/review-context.md`, and explain that retest requires GitLab retry UI/API or an external Note Hook receiver. Covered by `WQ-08`.
- `REQ-012` (`pending`): add navigation-only indexes at `docs/README.md`, `docs/codex/README.md`, and `docs/engineering/README.md`; reconcile links, README, strategy, roadmap, and Towncrier fragments. Covered by `WQ-09`.
- `REQ-013` (`pending`): complete focused, adversarial, artifact, quality, secret, manifest, release-draft, reproducibility, and clean-install validation without a separate Codex Security scan or any real local LLM call. Covered by every work item and `WQ-10`.
- `REQ-014` (`pending`): leave implementation in a Draft PR at the exact final feature head with stable release deferred until external qualification; perform no merge, stable publication, issue closure, or milestone closure. Covered by `WQ-10` and `WQ-11`.

#### Explicit Non-Goals

- Do not implement or create a future issue for `@bot retest`; the CI-only toolkit has no comment-event receiver. GitLab retry UI/API remains the no-commit mechanism.
- Do not let remediation text authorize, suppress, resolve, change severity, prove remediation, or affect automatic approval.
- Do not add arbitrary discussion search, cross-project retrieval, provider-facing model tools, write-capable MCP methods, or a second model pass.
- Do not migrate repository instruction contracts; only the three approved navigation indexes belong to this release.
- Do not modify local OCR configuration, credentials, LLM endpoints, the user's `HOME`, or globally installed OCR.
- Do not run real LLM/model calls or start a local model peer.
- Do not run a separate Codex Security scan, disable Bandit/Gitleaks/CodeQL, merge the Draft PR, publish stable 0.8.0, or close release issues/milestone in this implementation phase.

#### Constraints

- After the signed planning commit, push exactly once and open the Draft PR immediately. Make all implementation commits locally and do not push again until the complete local implementation and holistic self-review are finished.
- Each logical slice requires focused tests, full slice-diff self-review, requirement and trust-boundary reconciliation, `git diff --check`, and a signed commit.
- Apply normalization, bounds, and DLP before admitting any MR title, description, generic discussion, remediation root/reply, or dynamic adapter/reference text to the private store or bootstrap.
- Store no raw GitLab IDs, usernames, provider objects, rejected text, or source locations for rejected values in model projections, receipts, logs, or retained results.
- Keep receipt schema v5 and existing closed source/degradation accounting.
- Treat any admitted remediation bundle as mutable context and force comment-only independently of DLP outcome or semantic content.
- Optional local OCR checks are limited to OCR 1.9.9 `--version`, `--help`, or confirmed no-LLM preview/selection in an isolated temporary `HOME`. A missing binary may only be replaced by a checksum-verified temporary 1.9.9 copy that is removed afterward.
- Preserve all unrelated user work and existing public posting/ownership contracts.

#### Inputs And Sources

- User-approved release plan and follow-up decisions in the active task.
- GitHub issue #120 and milestone `v0.8.0` as the product contract and coordination root.
- `AGENTS.md`, `docs/engineering/project_principles.md`, `docs/development.md`, and `docs/release.md` as repository workflow and boundary owners.
- `docs/configuration.md`, `docs/operations.md`, `docs/gitlab.md`, `docs/review-context.md`, and `docs/security.md` as public product/operator contracts.
- Existing policy/store/provider/MCP/posting implementations and their tests as compatibility baselines.
- GitLab webhook, merge-request pipeline, and retry-job documentation for the `retest` feasibility decision.
- Engineering-workflow 0.8.1 planning/index contract and its pre-edit repository audit.

#### User Decisions And Answers

- Navigation-index debt is explicitly in scope because this release changes documentation; instruction-contract migration is not.
- Engineering-workflow 0.8.1 is current and requires no update.
- `OCR_GITLAB_BOT_USER_ID` and other obsolete compatibility/documentation-only variables should be removed rather than merely documented.
- Local OCR is not configured and must not be used for LLM review; an optional 1.9.9 no-LLM check is the maximum local OCR interaction.
- Mention actions use the correct spellings `suppress` and `resolve`; `supress` is ignored.
- Do not create a future `retest` issue.
- DLP must protect all untrusted MR-derived text, including title, description, every discussion class, remediation roots/replies, and dynamic adapter/reference content, without interfering with safe auto-approval; admitted remediation itself remains an independent comment-only condition.
- Provider-neutral context contracts must remain reusable for a future GitHub adapter: GitLab transport, pagination, identity, and posting stay behind GitLab modules, while the broker consumes only normalized protocols/records.

#### Completed Baseline State

- `main`, `origin/main`, and tag `v0.7.1` resolve to `42f7b9d171694b4cf3384588c941153d2e85e0f6` before branch creation.
- The working tree was clean before this plan write.
- Engineering-workflow 0.8.1 was verified as the active marketplace-managed version.
- The pre-edit workflow audit found only the three approved navigation-index gaps relevant to this release.
- GitHub issue #120 is open in the open `v0.8.0` milestone; no sub-issues existed at plan start.
- Existing policy/store schemas are v1, receipt schema is v5, and slash commands already implement newest-recognized-human-command semantics.

#### Current Work Queue

- `WQ-01` (`done`): self-reviewed and committed this first-write plan checkpoint on `codex/v0.8.0-remediation-threads`.
- `WQ-02` (`done`): pushed only the signed planning commit, opened Draft PR #122, created and attached three milestone sub-issues, and appended/read back #120's coordination checklist. No further push is allowed until `WQ-10`.
- `WQ-03` (`done`): added policy v1/v2, remediation policy types, context-store v2, fixed model-only nested projection, `remediation_thread` MCP resource filtering, and architecture/threat-contract updates; focused tests and slice review passed.
- `WQ-04` (`done`): implemented shared validated live identity, one bounded double snapshot, root verification by live bot ID plus exact fingerprint marker, remediation grouping/generic exclusion, command exclusion, and mutation/pagination semantics; focused and adversarial tests passed.
- `WQ-05` (`done`): added provider-neutral forge origins and normalized remediation views, repeated DLP before store, provider DLP rejection accounting, one-snapshot runner composition, nested aggregate budgets, fixed bootstrap non-authority guidance, receipt-v5 comment-only semantics only for admitted remediation, metadata DLP hostile readback, and an import-boundary test; 176 focused tests plus 71 subtests, Ruff, MyPy, slice review, and diff checks passed.
- `WQ-06` (`done`): connected the exact slash/mention parser to the posting snapshot with the authenticated live username; verified `@mr.bot suppress|resolve`, newest-recognized-human precedence, toolkit-owned-root scoping, and bot/system/typo/prose/code/wrong-mention/retest negatives; 171 focused tests plus 90 subtests, Ruff, MyPy, slice review, and diff checks passed.
- `WQ-07` (`pending`): runtime environment cleanup, complete configuration tables, exact supported-set/default contract tests, and example helper-test removal; signed commit.
- `WQ-08` (`pending`): mode-oriented examples, moved recipes, Accepted decisions consumption walkthrough, GitLab/review-context documentation, user-facing terminology cleanup; signed commit.
- `WQ-09` (`pending`): three managed navigation indexes, cross-link/README/strategy/roadmap/Towncrier reconciliation, index audit; signed commit.
- `WQ-10` (`pending`): holistic requirement/privacy/architecture/documentation self-review and complete local validation matrix; correct only evidence-backed failures through the same commit gates; update plan to implementation-complete/external-qualification-pending; final local signed commit and one final push; wait for hosted CI.
- `WQ-11` (`pending`): external owner supplies qualification receipt bound to the exact feature commit/tree; after evidence, verify runtime-tree identity, update lifecycle state, ready and merge the exact reviewed head, reconcile TestPyPI development publication, and proceed through the normal `release/v0.8.0` lifecycle.

#### Locked Decisions

- Policy v2 is additive and v1 remains valid for existing enriched configurations.
- Context store moves to private schema v2; remediation records are opaque, bounded, local, read-only, and non-provider-addressable.
- Root ownership requires both live bot ID equality and a valid toolkit marker/fingerprint.
- Generic discussion and remediation projections derive from one stable double snapshot; an admitted remediation thread is excluded from generic records and from external-reference discovery.
- Mention parsing is exact whole-reply matching for the live username and shares existing slash-command lifecycle semantics.
- DLP rejection affects only the admission/degradation state of the untrusted source being inspected. It cannot turn a review into approval; safe MR metadata, generic discussions, and adapter/reference context must not themselves disable otherwise valid receipt-based auto-approval.
- Any successfully admitted remediation record forces comment-only even when its text is safe.
- Stable publication remains deferred until external real-path qualification on the exact feature tree.
- Generic `ocr_toolkit.context` modules must not import `providers.gitlab*`; GitLab produces the common discussion/remediation views at the composition edge. A future GitHub implementation may satisfy the same views without inheriting GitLab API or identity semantics.

#### Verification

- Planning/coordination: inspect branch base, signed commit, remote Draft PR state, sub-issue parent relations, milestone assignments, and #120 checklist readback.
- Contracts/store/MCP: focused policy, store, broker, MCP, receipt, runner, posting-approval, cleanup, and installed-artifact tests with a controlled subprocess peer.
- Architecture: an import-boundary test proves generic context contracts/broker/store/MCP do not depend on GitLab provider modules; a non-GitLab fake view must project through the same remediation broker contract.
- Provider/adversarial: stable and mutated double snapshots; edit/delete/reorder/pagination drift; thread/reply/item/age/text bounds; prompt injection; Unicode, Markdown, and HTML laundering; PII/secrets across MR title, description, generic discussions, remediation roots/replies, and dynamic context; fake bot roots; system/automation events; conflicting/oversized replies.
- Commands: slash/mention parity; mixed-case username/action; whitespace boundary; typo, prose, code blocks, wrong mention, bot/system reply, and non-toolkit-owned discussion negatives; newest recognized human command wins.
- Approval safety: DLP-clean MR title/description, generic discussions, and dynamic context without admitted remediation preserve existing receipt-based auto-approval; any admitted remediation forces comment-only; a DLP-rejected source cannot enable approval; posting suppression/fingerprint/human ownership/resolve rollback remain unchanged.
- Environment/docs: exact supported variable/default inventory test; removal search for deleted names and user-facing `synthetic`; link and example checks; current schema compatibility and retest limitation documented.
- Repository gates: focused tests per slice, `git diff --check` per commit, final `scripts/quality.sh check`, `scripts/gitleaks.sh`, lock/OCR-manifest checks, Towncrier draft, reproducible packages, Twine checks, and clean installs on Python 3.12, 3.13, and 3.14.
- Hosted gates: final feature push must pass required GitHub Actions including CodeQL; no weakening or bypass.
- External qualification: receipt records OCR 1.9.9 and checksum, external configured LLM endpoint, real `ocr review` through production toolkit, observed `context_list`/`context_get`, both still-present and code-evidence-resolved scenarios, and absence of raw remediation/provider leakage, all bound to exact commit/tree.

#### Latest Validation Results

- `2026-08-22`: pre-edit `git status`, `git fetch`, and revision comparison passed; local `main` equals `origin/main` at `42f7b9d` and the tree was clean.
- `2026-08-22`: engineering-workflow 0.8.1 pre-edit audit reproduced missing indexes only at `docs/README.md`, `docs/codex/README.md`, and `docs/engineering/README.md` for the approved index scope. The audit also enumerated protected/unknown repository-owned documents that will not be bulk-rewritten.
- `2026-08-22`: the planning slice passed complete diff review, requirement/trust-boundary reconciliation, required-section checks, and `git diff --check`; the planning commit is signed with the configured SSH key (local signature trust display requires an `allowedSignersFile`).
- `2026-08-22`: Draft PR #122 is open at planning head `c10fb8f`; #120 has exactly three open v0.8.0 children (#123, #124, #125) with corrected literal-safe bodies, parent links, and a read-back coordination checklist.
- `2026-08-22`: policy/store/MCP contract slice passed 44 focused tests, Ruff format/check, MyPy for the context package, full slice diff review, trust-boundary reconciliation, and `git diff --check`. Store v2 hostile-read tests reject nested DLP violations, inconsistent order/counts, raw extra fields, toolkit-bot replies, and remediation data outside its exact model-only placement.
- `2026-08-22`: GitLab acquisition/identity slice passed 225 focused provider/store/posting tests plus 78 subtests, Ruff format/check, full-package MyPy, real local TLS transport, and `git diff --check`. Tests cover live ID/username validation, stable double reads, edit/delete/reorder/pagination/identity mutation, forged roots, DLP rejection, command exclusion, bounded pagination, run-local pseudonyms, and absence of raw thread/display/path data in returned projections.
- No implementation validation has run yet.

#### Risks And Recovery

- Risk: DLP coverage misses an MR-derived text path or becomes accidentally coupled to approval eligibility. Recovery: inventory title, description, generic discussions, remediation roots/replies, and adapter/reference inputs at their admission boundaries; keep DLP results inside per-source enrichment state; assert safe-context approval parity and separately assert admitted-remediation comment-only behavior.
- Risk: provider drift creates mixed or duplicated projections. Recovery: compare canonical complete snapshots including identity and ordering; emit only closed `mutated`, `partial`, or `unavailable` state and commit no partial store.
- Risk: marker-like user content is treated as toolkit ownership. Recovery: require active bot ID plus strict marker/fingerprint parsing and cover forged roots adversarially.
- Risk: raw provider identities leak through diagnostics or receipts. Recovery: retain run-local pseudonyms only, assert serialized artifacts/log capture, and discard rejected values without locations.
- Risk: documentation inventory drifts from runtime. Recovery: own the supported/default inventory in executable contract data and compare public tables/examples against it.
- Risk: initial push ordering is violated. Recovery: stop immediately if a non-planning commit or extra push occurs; report the lifecycle discrepancy before implementation.
- Risk: external qualification is unavailable. Recovery: leave Draft PR, issues, milestone, and release deferred at the exact locally validated head; resume from `WQ-11` only when external evidence exists.

#### Resume Point

Continue at `WQ-07`: remove obsolete environment semantics and example helper-test controls, rebuild the exact categorized environment/default contract with regression coverage, pass the slice commit gate, and do not push.

#### Plan Fidelity Check

- [x] Every user-requested outcome has a stable `REQ-###` entry and one or more ordered work-queue owners.
- [x] Release-required implementation and release-deferred stable delivery are both explicit.
- [x] GitHub writes, push ordering, commit gates, and issue/milestone non-closure are preserved.
- [x] Full MR-text DLP coverage, auto-approval independence, comment-only remediation, identity, privacy, and mutation trust boundaries are explicit.
- [x] Local OCR/LLM restrictions and optional no-LLM 1.9.9 boundary are explicit.
- [x] Validation covers functional, adversarial, artifact, documentation, release, and hosted gates.
- [x] Non-goals preserve the retest and instruction-migration decisions.
- [x] The Resume Point names the first safe unfinished action.

#### Reconciliation Check

- [x] Current repository head, worktree, issue, milestone, workflow version, and index-audit baseline have been read back.
- [x] The work queue preserves every logical slice and the external qualification phase.
- [x] No existing completed work is represented as pending implementation.
- [x] No release, merge, issue closure, or external qualification is claimed complete.

#### Closure Gate

- [ ] All in-scope `REQ-###` and `WQ-##` items through `WQ-10` are `done` or explicitly justified `out_of_scope`.
- [ ] Each logical slice has focused test evidence, full diff self-review, boundary reconciliation, `git diff --check`, and a signed commit.
- [ ] Holistic privacy, architecture, requirements, documentation, and omission review is complete with no unresolved findings.
- [ ] The final local validation matrix and hosted CI are green for the exact feature head.
- [ ] `PLANS.md`, roadmap/strategy, Towncrier fragments, Draft PR, issues, milestone, and remote refs agree that implementation is complete but stable release remains externally blocked.
- [ ] Plan lifecycle validation succeeds before any eventual closure transition.

#### Post-Close Delivery

- Initial planning push and Draft PR are in scope at `WQ-02`; one final implementation push and hosted CI are in scope at `WQ-10`.
- External qualification, ready-for-review transition, exact-head merge, TestPyPI development reconciliation, release branch/PR, stable publication, and issue/milestone closure remain pending `WQ-11` and are not authorized before the required receipt.
- If external evidence invalidates an assumption, reopen active corrective work rather than rewriting completed validation history.

#### Handoff Notes

- Do not push implementation commits individually. After the Draft PR exists, keep all slices local until `WQ-10` is complete.
- Do not use local OCR for model review. Prefer the controlled subprocess peer for installed-artifact tests.
- Keep #120's existing core body and explicit non-goals intact; append coordination only and track mention behavior in its own child issue.
- When resuming after interruption or compaction, read this plan, inspect `git status` and local/remote commit graphs, reconcile requirement/queue states, and continue from the first non-terminal queue item.
