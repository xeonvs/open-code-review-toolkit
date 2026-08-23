# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Release 0.8.0: remediation threads, GitLab commands, and documentation

- Status: `active`
- Release classification: `release-required`
- Target stable version: `0.8.0`
- Stable delivery state: `release-deferred`

#### Goal

Deliver a backward-compatible, privacy-bounded remediation-thread context source, exact GitLab mention commands, a complete environment contract, mode-oriented GitLab examples, Accepted project decisions usage guidance, and navigation indexes. Integrate OCR 1.9.10 as the exact toolkit 0.8.0 target, raise meaningful boundary coverage, and keep the exact final head in Draft PR #122 until an external OCR 1.9.10 plus LLM qualification proves the production path without leaking raw remediation or provider data.

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
- Repair Actions storage maintenance after live run 32624698380 proved that more than ten aggregate pages of recent completed runs exceed the collector bound. Preserve a ten-page fail-closed limit per UTC day, delete completed TestPyPI development/preview runs after 14 days, ordinary workflow runs after 30 days, and stable Release runs after 60 days, then reconcile the current backlog without touching active or fresh runs.
- Integrate upstream OCR 1.9.10 as the only preflight-supported and example-pinned OCR version for toolkit 0.8.0 after direct source, checksum, and hosted compatibility review. Preserve OCR 1.9.9 only as the separately documented inherited predecessor already qualified for toolkit 0.7.1.
- Add risk-weighted fault tests at the existing result, preflight, GitLab transaction, context, DLP, receipt, MCP, and approval owners; fix production behavior only when a test exposes a real contract violation.
- Raise the existing combined branch-aware coverage floor from 70% to 85% and add four ordinary Coverage.py risk-group reports without a new coverage framework, configuration format, parser, or coverage-only production refactor.
- Finish with one final push of all locally self-reviewed commits to Draft PR #122, exact-head hosted CI, and an explicit handoff whose first external operation is toolkit 0.8.0 qualification with OCR 1.9.10 and a configured LLM endpoint.

#### Requirement Traceability

- `REQ-001` (`done`): materialized this full plan first, created the feature branch from synchronized `main`, made a signed planning commit, performed the one initial push, and opened Draft PR #122 before implementation. Covered by `WQ-01` and `WQ-02`.
- `REQ-002` (`done`): created v0.8.0 sub-issues #124, #125, and #123, attached them to #120, and appended/read back the coordination checklist without changing #120's core contract. Covered by `WQ-02`.
- `REQ-003` (`done`): implemented policy v1/v2 compatibility, a non-configurable remediation policy type, private store v2, and a fixed model-only safe remediation projection with a new closed MCP resource class. Covered by `WQ-03`.
- `REQ-004` (`done`): added a shared validated live `GET /user` identity owner and derive mutually exclusive generic discussions plus verified remediation bundles from one twice-read bounded snapshot; identity, edit, delete, reorder, and pagination drift fail closed as `mutated`. Covered by `WQ-04`.
- `REQ-005` (`done`): apply budgets and DLP before atomic storage, add MCP/bootstrap/receipt/cleanup integration, and preserve posting suppression, fingerprints, human ownership, resolve rollback, and receipt v5. Covered by `WQ-05`.
- `REQ-006` (`done`): apply DLP to every untrusted MR-derived text path, including title, description, generic discussions, remediation roots/replies, and adapter/reference content, before private-store or bootstrap admission. Keep each source's DLP admission/degradation isolated from receipt-based approval: safe non-remediation context must not block approval, DLP rejection cannot enable approval, and admitted remediation always forces comment-only. Covered by `WQ-05` and `WQ-06`.
- `REQ-007` (`done`): support exact whole-reply mention commands for the live bot username with slash-command parity and closed negative cases. Covered by `WQ-06`.
- `REQ-008` (`done`): removed `OCR_GITLAB_BOT_USER_ID`; reject `OCR_USE_ANTHROPIC` with migration guidance; removed example `OCR_RUN_HELPER_TESTS` and unsupported documentation-only variables while retaining active controls and redaction sentinels. Covered by `WQ-07`.
- `REQ-009` (`done`): published a complete environment-variable/default contract separated by runtime, GitLab predefined, example-local, and dynamic adapter inputs, protected by one exact-set/default contract test owner. Covered by `WQ-07`.
- `REQ-010` (`done`): reorganized GitLab examples by mode, relocated context recipes, removed user-facing `synthetic` labels, and demonstrated Accepted project decisions creation plus later evidence list/get use. Covered by `WQ-08`.
- `REQ-011` (`done`): removed 0.6.x migrations from `docs/gitlab.md`, documented current v1/v2 compatibility and discussion-policy selection in `docs/review-context.md`, and explained that retest requires GitLab retry UI/API or an external Note Hook receiver. Covered by `WQ-08`.
- `REQ-012` (`done`): added navigation-only managed indexes at `docs/README.md`, `docs/codex/README.md`, and `docs/engineering/README.md`; reconciled links, README, strategy, roadmap, and Towncrier fragments. Covered by `WQ-09`.
- `REQ-013` (`done`): completed focused, adversarial, artifact, quality, secret, manifest, release-draft, reproducibility, and clean-install validation without a separate Codex Security scan or any real local LLM call. Covered by every work item and `WQ-10`.
- `REQ-014` (`pending`): leave implementation in a Draft PR at the exact final feature head with stable release deferred until external qualification; perform no merge, stable publication, issue closure, or milestone closure. Covered by `WQ-18` and `WQ-11`.
- `REQ-015` (`done`): made the v0.8.0 release-note delta equally actionable for a production-integration agent and a human operator: categorized each outcome by effect, explicitly labelled additions, changes, removals, defaults, and migrations, and named exact public symbols and replacements. Removed environment variables have a separate `maintenance` fragment. Covered by `WQ-07` and `WQ-09`.
- `REQ-016` (`done`): made scheduled Actions maintenance tolerate more than ten aggregate recent-run pages without weakening bounded pagination, introduced conservative completed-run retention, executed one verified backlog reconciliation, and requalified hosted CI at `373fc2d`. Covered by `WQ-12`.
- `REQ-017` (`done`): integrated OCR 1.9.10 as the exact 0.8.0 target using official source, checksum, hosted compatibility, manifest/evidence, preflight, example, documentation, privacy regressions, and a maintenance-class compatibility update; kept OCR 1.9.9 separately described as the inherited 0.7.1 predecessor. Covered by `WQ-13` and `WQ-14`.
- `REQ-018` (`done`): added meaningful boundary and fault coverage for private results, preflight, GitLab reads/writes/rollback, context admission, DLP, receipts, MCP, provider neutrality, and approval without reorganizing tests or refactoring production solely for coverage. Covered by `WQ-15` and `WQ-16`.
- `REQ-019` (`pending`): enforce 85% combined branch-aware coverage plus the four locked risk-group floors through the existing local and hosted workflows, publish separately categorized release notes, and hand off one green exact Draft head for external OCR 1.9.10 qualification. Covered by `WQ-17`, `WQ-18`, and `WQ-11`.

#### Explicit Non-Goals

- Do not implement or create a future issue for `@bot retest`; the CI-only toolkit has no comment-event receiver. GitLab retry UI/API remains the no-commit mechanism.
- Do not let remediation text authorize, suppress, resolve, change severity, prove remediation, or affect automatic approval.
- Do not add arbitrary discussion search, cross-project retrieval, provider-facing model tools, write-capable MCP methods, or a second model pass.
- Do not migrate repository instruction contracts; only the three approved navigation indexes belong to this release.
- Do not modify local OCR configuration, credentials, LLM endpoints, the user's `HOME`, or globally installed OCR.
- Do not run real LLM/model calls or start a local model peer.
- Do not run a separate Codex Security scan, disable Bandit/Gitleaks/CodeQL, merge the Draft PR, publish stable 0.8.0, or close release issues/milestone in this implementation phase.
- Do not create a coverage framework, coverage JSON parser, or new configuration format; reorganize existing test modules for aesthetics; test unreachable lines or entrypoints merely to increase a percentage; or refactor production code solely for coverage.
- Do not install OCR 1.9.9 or require the external qualification agent to do so. Its accepted evidence remains historical; only OCR 1.9.10 is the current qualification target.

#### Constraints

- The initial planning push and Draft PR already exist. Commit this scope correction locally, make every remaining implementation commit locally, and perform no intermediate push; push the complete final history exactly once after holistic self-review.
- Each logical slice requires focused tests, full slice-diff self-review, requirement and trust-boundary reconciliation, `git diff --check`, and a signed commit.
- Apply normalization, bounds, and DLP before admitting any MR title, description, generic discussion, remediation root/reply, or dynamic adapter/reference text to the private store or bootstrap.
- Store no raw GitLab IDs, usernames, provider objects, rejected text, or source locations for rejected values in model projections, receipts, logs, or retained results.
- Keep receipt schema v5 and existing closed source/degradation accounting.
- Treat any admitted remediation bundle as mutable context and force comment-only independently of DLP outcome or semantic content.
- Hosted OCR 1.9.10 compatibility is the primary evidence. Do not download a local OCR binary unless a concrete discrepancy requires it; any optional local check is limited to a checksum-verified temporary Darwin OCR 1.9.10 `--version`, `--help`, or confirmed no-LLM behavior in an isolated temporary `HOME`, followed by removal.
- Preserve all unrelated user work and existing public posting/ownership contracts.
- Reuse pytest-cov, Coverage.py, `scripts/quality.sh`, and the compatibility workflow. Measure branches, run pytest once per full quality execution, and apply group floors through ordinary `coverage report --include=... --fail-under=...` commands.

#### Inputs And Sources

- User-approved release plan and follow-up decisions in the active task.
- GitHub issue #120 and milestone `v0.8.0` as the product contract and coordination root.
- `AGENTS.md`, `docs/engineering/project_principles.md`, `docs/development.md`, and `docs/release.md` as repository workflow and boundary owners.
- `docs/configuration.md`, `docs/operations.md`, `docs/gitlab.md`, `docs/review-context.md`, and `docs/security.md` as public product/operator contracts.
- Existing policy/store/provider/MCP/posting implementations and their tests as compatibility baselines.
- GitLab webhook, merge-request pipeline, and retry-job documentation for the `retest` feasibility decision.
- Engineering-workflow 0.8.1 planning/index contract and its pre-edit repository audit.
- Official upstream OCR v1.9.9/v1.9.10 releases, source comparison, hosted release assets/checksums, and the repository OCR compatibility workflow as version-integration evidence.

#### User Decisions And Answers

- Navigation-index debt is explicitly in scope because this release changes documentation; instruction-contract migration is not.
- Engineering-workflow 0.8.1 is current and requires no update.
- `OCR_GITLAB_BOT_USER_ID` and other obsolete compatibility/documentation-only variables should be removed rather than merely documented.
- Local OCR is not configured and must not be used for LLM review. OCR 1.9.9 stays an inherited predecessor; OCR 1.9.10 is the exact 0.8.0 integration and external qualification target.
- Mention actions use the correct spellings `suppress` and `resolve`; `supress` is ignored.
- Do not create a future `retest` issue.
- DLP must protect all untrusted MR-derived text, including title, description, every discussion class, remediation roots/replies, and dynamic adapter/reference content, without interfering with safe auto-approval; admitted remediation itself remains an independent comment-only condition.
- Provider-neutral context contracts must remain reusable for a future GitHub adapter: GitLab transport, pagination, identity, and posting stay behind GitLab modules, while the broker consumes only normalized protocols/records.
- Direct agent source review is sufficient for OCR 1.9.10; do not create a separate human-review handoff. Retry-report grouping is private terminal presentation only and must not become toolkit telemetry, receipt input, DLP input, outcome evidence, severity input, or approval signal.
- Coverage work must improve meaningful boundary confidence, not chase unreachable lines. Existing thematic test owners remain in place; a shared helper belongs in `tests/support.py` only after real reuse appears.
- Release notes must let both a production-integration agent and a human distinguish OCR 1.9.9 inherited evidence from OCR 1.9.10 changes, telemetry non-effects, required deployment/migration, coverage-gate changes, and any separately justified runtime bugfix.

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
- `WQ-07` (`done`): removed obsolete environment and production helper-test semantics, made `OCR_USE_ANTHROPIC` fail with explicit protocol migration, published complete categorized variable/default tables, added a source/docs/example exact inventory owner, and recorded durable operator/automation release-note guidance; 354 focused tests plus 116 subtests, Ruff, MyPy, slice review, and diff checks passed; signed commit.
- `WQ-08` (`done`): added a mode matrix and focused recipes, moved and split context policies by discussion/adapter need, documented policy selection and approval effects, added an Accepted decisions creation/consumption walkthrough, removed obsolete migration prose and user-facing terminology, and passed 225 focused tests plus 26 subtests, Ruff, MyPy, slice review, and diff checks; signed commit.
- `WQ-09` (`done`): added three managed navigation indexes, reconciled cross-links/README/strategy/roadmap and public-example terminology, rendered agent/human-readable feature/maintenance/documentation Towncrier fragments, and passed 47 focused tests, Ruff, MyPy, local-link checks, Towncrier draft, the engineering-workflow 0.8.1 index audit, slice review, and diff checks; signed commit.
- `WQ-10` (`done`): holistic requirement/privacy/architecture/documentation self-review and the complete local validation matrix passed; the final signed feature push moved Draft PR #122 to exact head `a196408`, and all 13 hosted CI/security/build checks passed without corrective changes.
- `WQ-12` (`done`): diagnosed scheduled Actions maintenance run 32624698380, implemented UTC-day sharding plus TestPyPI 14-day, ordinary 30-day, and stable Release 60-day completed-run retention, reconciled the live backlog, committed and pushed the reviewed correction at `373fc2d`, and passed all 13 exact-head hosted checks.
- `WQ-13` (`done`): materialized and self-reviewed this OCR 1.9.10/coverage scope correction in a signed local planning commit; hosted `OCR compatibility` run 32648809527 qualified `v1.9.10` successfully at remote head `373fc2d` and created canonical issue #126; created coverage issue #127; attached both to #120 and milestone `v0.8.0`; updated and read back #120 coordination. No automation PR was created and no repository push occurred.
- `WQ-14` (`done`): audited the four-commit official OCR 1.9.9-to-1.9.10 source delta, GitHub asset digests, and hosted probes; integrated exact evidence/manifest, preflight, GitLab example, current docs/default tests, private retry-report non-effect regressions, maintenance-class generator output, and separate actionable OCR release notes. The scan-only and VS Code changes remain outside the review path; no automation PR existed to reconcile.
- `WQ-15` (`done`): added focused fault tests at the existing private-result, parser, preflight, GitLab transport, posting transaction, strict/non-strict, and previous-review owners; covered bounded/atomic result handling, OCR process failures, bounded retry and authenticated reads, non-retried writes, exact partial publication identities, safe error projection, and coverage-dependent cleanup. The complete `artifact -> parser -> posting -> GitLab` review found no production contract defect.
- `WQ-16` (`done`): added focused tests for `MR text -> stable snapshot -> normalization -> DLP -> budget/admission -> store/MCP -> receipt -> approval`; proved exact mixed-source counts, safe title/description/discussion/adapter auto-approval parity, remediation and required-degradation fail-closed behavior, provider-shape rejection, command exclusion, and absence of rejected/provider diagnostics. Existing hostile replay/readback, malformed policy/MCP/receipt, provider-neutral import, non-GitLab fake-provider, no-duplication, and no-remediation-reference-discovery contracts were re-run without restructuring their owners.
- `WQ-17` (`done`): raised the combined branch-aware floor to 85% and added four ordinary scoped Coverage.py reports to the same local/hosted test run; added meaningful result/preflight/GitLab/MCP fault coverage in existing thematic owners; published a separate coverage maintenance fragment; and passed the full quality, manifest, lock, Towncrier, diff, privacy, architecture, telemetry, and data-flow review without a production-code change or test-file reorganization.
- `WQ-18` (`in_progress`): make one final push of the complete signed local history to Draft PR #122, wait for exact-head hosted CI, and update PR #122 plus #120 with toolkit 0.8.0, OCR 1.9.10, exact commit/tree/checksum, inherited-only OCR 1.9.9 status, and the external agent's first qualification operation. Keep every release issue, milestone, and Draft state open.
- `WQ-11` (`pending`): external owner starts from the green exact Draft head with OCR 1.9.10 and a configured LLM endpoint, then supplies a bound qualification receipt covering real `ocr review`, `context_list`/`context_get`, still-present/resolved findings, and raw-data leakage audit. Only after evidence may lifecycle work verify tree identity, ready and merge the exact head, reconcile TestPyPI development publication, and continue normal `release/v0.8.0` delivery.

#### Locked Decisions

- Policy v2 is additive and v1 remains valid for existing enriched configurations.
- Context store moves to private schema v2; remediation records are opaque, bounded, local, read-only, and non-provider-addressable.
- Root ownership requires both live bot ID equality and a valid toolkit marker/fingerprint.
- Generic discussion and remediation projections derive from one stable double snapshot; an admitted remediation thread is excluded from generic records and from external-reference discovery.
- Mention parsing is exact whole-reply matching for the live username and shares existing slash-command lifecycle semantics.
- DLP rejection affects only the admission/degradation state of the untrusted source being inspected. It cannot turn a review into approval; safe MR metadata, generic discussions, and adapter/reference context must not themselves disable otherwise valid receipt-based auto-approval.
- Any successfully admitted remediation record forces comment-only even when its text is safe.
- Stable publication remains deferred until external real-path qualification on the exact feature tree.
- Actions maintenance retains a ten-page cap per collection shard. Scheduled workflow-run acquisition uses a closed UTC-day window; completed TestPyPI development/preview runs are retained for 14 days, ordinary runs for 30 days, and stable Release runs for 60 days. Active runs and newer completed runs are never deletion candidates.
- Generic `ocr_toolkit.context` modules must not import `providers.gitlab*`; GitLab produces the common discussion/remediation views at the composition edge. A future GitHub implementation may satisfy the same views without inheriting GitLab API or identity semantics.
- OCR 1.9.9 is an inherited predecessor qualified for toolkit 0.7.1; its evidence and historical changelog stay intact. OCR 1.9.10 is the only accepted preflight version and GitLab example pin for toolkit 0.8.0. Its Linux amd64 SHA-256 is `359e5bafda1438a47ef389399f4994350e1016371eac1dc17a2c428acb228e6c`.
- OCR 1.9.10 terminal retry output may group failures by review stage, while `ocr.llm-retry-report/v1`, result, and manifest contracts remain unchanged. `ocr scan` background wait/resume changes are outside the toolkit's `ocr review` path. Retry reports remain private and non-authoritative.
- Combined branch-aware coverage has an 85% floor. Risk-group floors are: `ocr_result + preflight` 80%; posting workflow + GitLab + snapshot + GitLab approval 80%; review runner + context broker/store/DLP + approval 85%; MCP config + GitLab context providers + policy/result contracts 85%.

#### Verification

- Planning/coordination: inspect branch base, signed commit, remote Draft PR state, sub-issue parent relations, milestone assignments, and #120 checklist readback.
- Contracts/store/MCP: focused policy, store, broker, MCP, receipt, runner, posting-approval, cleanup, and installed-artifact tests with a controlled subprocess peer.
- Architecture: an import-boundary test proves generic context contracts/broker/store/MCP do not depend on GitLab provider modules; a non-GitLab fake view must project through the same remediation broker contract.
- Provider/adversarial: stable and mutated double snapshots; edit/delete/reorder/pagination drift; thread/reply/item/age/text bounds; prompt injection; Unicode, Markdown, and HTML laundering; PII/secrets across MR title, description, generic discussions, remediation roots/replies, and dynamic context; fake bot roots; system/automation events; conflicting/oversized replies.
- Commands: slash/mention parity; mixed-case username/action; whitespace boundary; typo, prose, code blocks, wrong mention, bot/system reply, and non-toolkit-owned discussion negatives; newest recognized human command wins.
- Approval safety: DLP-clean MR title/description, generic discussions, and dynamic context without admitted remediation preserve existing receipt-based auto-approval; any admitted remediation forces comment-only; a DLP-rejected source cannot enable approval; posting suppression/fingerprint/human ownership/resolve rollback remain unchanged.
- Environment/docs: exact supported variable/default inventory test; removal search for deleted names and user-facing `synthetic`; link and example checks; current schema compatibility and retest limitation documented.
- Release notes: use exact operator-facing delta labels (`Added`, `Changed`, `Removed`, `Migration`) when an objective spans multiple effects; name symbols, defaults, before/after behavior, and replacements rather than relying on a category heading. For v0.8.0, list removed environment variables in a dedicated `maintenance` fragment and categorize all other fragments by their actual user-visible effect.
- Repository gates: focused tests per slice, `git diff --check` per commit, final `scripts/quality.sh check`, `scripts/gitleaks.sh`, lock/OCR-manifest checks, Towncrier draft, reproducible packages, Twine checks, and clean installs on Python 3.12, 3.13, and 3.14.
- Hosted gates: final feature push must pass required GitHub Actions including CodeQL; no weakening or bypass.
- OCR integration: dispatch hosted `OCR compatibility` for `v1.9.10`; verify official release/source delta, Linux amd64 checksum, generated evidence, manifest/recommended/preflight/example consistency, compatibility probes, private retry-report behavior, and maintenance fragment generation.
- Result/preflight/GitLab boundaries: cover private result limits, hostile types, inode replacement, short writes/atomic cleanup, malformed or oversized JSON, stderr redaction, missing/timeout/non-zero/wrong OCR, bounded preflight reads/retries/deadlines/offline validation, GET-only retry, `Retry-After`, malformed/oversized provider responses, authenticated `/user`, ambiguous create, partial draft publish, exact transaction identities, rollback ownership, strict/non-strict failures, and previous-review preservation.
- Context/DLP/approval boundaries: verify safe MR/context approval parity; admitted-remediation comment-only; DLP/mutation/required degradation denial; optional degradation isolation; generic/remediation deduplication; no remediation reference discovery; exact mixed-source counts; no rejected text or raw identity in projections; hostile store/replay failure; provider-neutral imports/fake provider; malformed policy/MCP inputs; and impossible receipt-state rejection.
- Coverage: after one branch-aware pytest run, require combined 85% and the four locked group floors using ordinary Coverage.py include reports in both `scripts/quality.sh` and hosted test execution.
- External qualification: receipt records OCR 1.9.10 and checksum, external configured LLM endpoint, real `ocr review` through production toolkit, observed `context_list`/`context_get`, both still-present and code-evidence-resolved scenarios, and absence of raw remediation/provider leakage, all bound to exact commit/tree. OCR 1.9.9 does not need to be installed or requalified.

#### Latest Validation Results

- `2026-08-22`: pre-edit `git status`, `git fetch`, and revision comparison passed; local `main` equals `origin/main` at `42f7b9d` and the tree was clean.
- `2026-08-22`: engineering-workflow 0.8.1 pre-edit audit reproduced missing indexes only at `docs/README.md`, `docs/codex/README.md`, and `docs/engineering/README.md` for the approved index scope. The audit also enumerated protected/unknown repository-owned documents that will not be bulk-rewritten.
- `2026-08-22`: the planning slice passed complete diff review, requirement/trust-boundary reconciliation, required-section checks, and `git diff --check`; the planning commit is signed with the configured SSH key (local signature trust display requires an `allowedSignersFile`).
- `2026-08-22`: Draft PR #122 is open at planning head `c10fb8f`; #120 has exactly three open v0.8.0 children (#123, #124, #125) with corrected literal-safe bodies, parent links, and a read-back coordination checklist.
- `2026-08-22`: policy/store/MCP contract slice passed 44 focused tests, Ruff format/check, MyPy for the context package, full slice diff review, trust-boundary reconciliation, and `git diff --check`. Store v2 hostile-read tests reject nested DLP violations, inconsistent order/counts, raw extra fields, toolkit-bot replies, and remediation data outside its exact model-only placement.
- `2026-08-22`: GitLab acquisition/identity slice passed 225 focused provider/store/posting tests plus 78 subtests, Ruff format/check, full-package MyPy, real local TLS transport, and `git diff --check`. Tests cover live ID/username validation, stable double reads, edit/delete/reorder/pagination/identity mutation, forged roots, DLP rejection, command exclusion, bounded pagination, run-local pseudonyms, and absence of raw thread/display/path data in returned projections.
- `2026-08-22`: environment/configuration slice passed 354 focused runtime, provider, posting, OCR-compatibility, and documentation tests plus 116 subtests; the single-owner environment contract separately passed source-name inventory, categorized table/default, redaction-only, removal, and public-example checks. Ruff, MyPy, full slice diff/self-review, trust-boundary reconciliation, and `git diff --check` passed.
- `2026-08-22`: examples/public-documentation slice passed 225 integration, policy, adapter, MCP, runtime, evidence, and documentation tests plus 26 subtests. Runtime parsers validated both v2 policy recipes, stdio/remote adapter recipes, direct-MCP mode JSON, and the Accepted decisions example; documentation tests enforce the mode matrix, discussion-policy choice guide, later-MR list/get walkthrough, removed migrations, retest boundary, and absence of user-facing `synthetic` labels. Ruff, MyPy, full slice self-review, trust-boundary reconciliation, and `git diff --check` passed.
- `2026-08-22`: navigation/release-note slice passed 47 integration, documentation, release-note, and environment-contract tests. Ruff, MyPy, local Markdown target checks, and a rendered 0.8.0 Towncrier draft passed; the dedicated maintenance section enumerates every removed variable and replacement, while feature/documentation sections distinguish added, changed, and migration behavior. Engineering-workflow 0.8.1 reported all three managed indexes required, fully indexed, and error-free. Full slice self-review, provider-neutral/approval-state reconciliation, and `git diff --check` passed.
- `2026-08-22`: after the host environment limitation was removed, the canonical isolated quality environment was rebuilt with system CPython 3.14.7. `scripts/quality.sh check` passed Ruff format/check, strict MyPy, Bandit, 1,063 tests plus 203 subtests, and 82.66% coverage. The final tree retains the stronger isolated PEP 517 distribution-content test and stdlib-venv installed-artifact tests; temporary workaround commits are superseded by the restoring commit without rewriting review history.
- `2026-08-22`: `scripts/gitleaks.sh` passed with the repository-pinned Gitleaks 8.24.3 obtained only in a temporary directory from the official archive after verifying SHA-256 `b90f13bb8c90ab72083d9b0c842e39dafb82c0e5c3f872f407366b7a58909013`; no global installation changed and no findings were reported. `uv lock --check`, `scripts/ocr_compat.py validate`, the Towncrier 0.8.0 draft, and `pip-audit` also passed; pip-audit reported no known dependency vulnerabilities and only the expected local-project registry skip.
- `2026-08-22`: two clean `0.8.0.dev0` builds were byte-identical: wheel SHA-256 `11059a9a56e049fe420ac784126dfcc75b3d08d5b2470f9f53d44dfe7ea3b7eb` and sdist SHA-256 `03d18b3d8ac88294c4e542203299ffe5dc7c0d2e88e359fb26e48710681fb6cf`. Twine passed, and hash-locked wheel and sdist installs each passed `pip check`, isolated version import, `ocr-ci --version`, and `ocr-ci --help` on Python 3.12, 3.13, and 3.14.
- `2026-08-22`: holistic diff review passed requirements, privacy, architecture, documentation, omission, and trust-boundary reconciliation. Policy v1 is accepted only for published configuration compatibility while the private store has only schema v2; generic context modules do not import GitLab providers; remediation content remains model-only and comment-only; safe non-remediation MR context preserves approval eligibility; DLP rejection fails closed; exact slash/mention lifecycle parsing retains `@mr.bot resolve`; removed inputs occur only in rejection/migration/tests/history contracts. `git diff --check` passed and every feature-branch commit contains its SSH signature header (local trust display still requires an `allowedSignersFile`). No OCR binary, LLM endpoint, model peer, user `HOME`, credentials, or global OCR installation was used or changed.
- `2026-08-23`: scheduled Actions maintenance run 32624698380 failed because 1,015 completed runs inside its 44-day bounded window filled all ten 100-item aggregate pages. Manual attempt 2 on unchanged `main` head `42f7b9d` reproduced the same `workflow_runs exceeded 10 pages` failure, excluding a transient runner or network explanation.
- `2026-08-23`: the maintenance correction keeps ten pages as a fail-closed per-UTC-day bound and permits more than ten aggregate pages across the closed 74-day lookback. Tests cover 1,100 records across 11 shards, a full ten-page single-day rejection, non-overlapping run identities, exact TestPyPI/ordinary/Release retention, active-run exclusion, and elimination of redundant log deletion when a run itself is due. Focused tests, Ruff, MyPy, documentation/release-note contracts, `git diff --check`, lock/OCR-manifest checks, and Towncrier draft passed.
- `2026-08-23`: canonical CPython 3.14.7 `scripts/quality.sh check` passed 1,067 tests plus 203 subtests at 82.66% coverage, including Bandit. Checksum-verified repository-pinned Gitleaks 8.24.3 also passed without changing the global 8.30.1 installation.
- `2026-08-23`: the new code produced a read-only live plan of 697 objects, then deleted exactly 697 with zero already absent: 4 stale caches, 76 expired/old artifacts, 407 due log archives, and 210 completed runs selected by the 14/30/60-day policy. Completed-run count fell from 1,015 to 805; 80 fresh artifacts and three retained caches remained. The post-cleanup dry-run contained no run, artifact, or cache candidate; it reselected 407 log IDs only because GitHub does not expose log-archive absence and the existing 14-day idempotent retry window intentionally retries them as 404-safe candidates.
- `2026-08-23`: the signed local planning commit materialized the OCR 1.9.10 and coverage scope without a push. Hosted compatibility run 32648809527 succeeded at remote head `373fc2d`; `qualify-v1.9.10` passed and canonical issue #126 was created, while the automatic-patch/PR steps correctly remained skipped. OCR issue #126 and coverage issue #127 are open children of #120 in milestone `v0.8.0`, and #120's updated coordination block was read back.
- `2026-08-23`: direct OCR 1.9.10 review confirmed terminal-only retry grouping, scan-only background/resume changes, and an out-of-scope VS Code change; official asset metadata and hosted evidence agree on Linux amd64 SHA-256 `359e5bafda1438a47ef389399f4994350e1016371eac1dc17a2c428acb228e6c`. Manifest validation, 411 focused tests plus 116 subtests, Ruff, and the rendered Towncrier section passed. Retry-report regressions prove private DLP sanitization leaves canonical publication/approval inputs unchanged and never publishes stage/provider/path details.
- `2026-08-23`: private-result and GitLab transaction boundary tests now cover descriptor short reads, short writes and atomic cleanup, inode replacement, hard size bounds, OCR missing/timeout/non-zero behavior, bounded and redacted preflight retries, authenticated identity/project/MR reads, bounded `Retry-After`, write non-retry, partial draft publication identities, safe parse/provider failure notes, strict/non-strict exits, and completeness-dependent prior-review cleanup. All 253 tests plus 121 subtests in the affected files, Ruff, and diff checks passed; no production defect or version-specific generic docstring was introduced.
- `2026-08-23`: context-flow regressions now prove safe MR metadata plus generic discussion/adapter data preserves approval eligibility, while admitted remediation, DLP rejection, required degradation, mutation, and impossible provider shapes remain closed and comment-only. Mixed sources produce exact closed counts, remediation commands and rejected/provider values never enter the store/receipt, and the provider-neutral `codehost` projection still crosses the common broker. The affected context matrix passed 230 tests plus 71 subtests; a full run excluding the environment-broken installed-policy venv case passed 1,113 tests plus 208 subtests at rounded 84%, with the context/approval risk group already at 85% and the policy/provider group at 82% before the final coverage slice.
- `2026-08-23`: after rebuilding only the ignored disposable quality environment on the now-available system CPython 3.14.7, the complete installed-artifact-inclusive suite passed 1,136 tests plus 275 subtests at 85.74% combined branch coverage. The four locked groups passed at 82%, 81%, 85%, and 86%; `scripts/quality.sh check` also passed Ruff format/check, strict MyPy, and Bandit. Local and hosted workflows use the same single pytest run plus four ordinary scoped reports, `uv lock --check`, OCR manifest validation, Towncrier draft, and `git diff --check` passed, and the coverage fragment describes the new gates for both deployment agents and humans.
- `2026-08-23`: the two preceding boundary-test commits were amended before publication so every newly introduced test has a concise contract docstring; all five affected test owners passed 356 tests plus 121 subtests before the history rewrite, both rewritten commits retain SSH signature headers, and generic docstrings/comments do not unnecessarily pin an OCR version. The final coverage slice likewise keeps every new test documented and leaves the thematic file layout unchanged.

#### Risks And Recovery

- Risk: DLP coverage misses an MR-derived text path or becomes accidentally coupled to approval eligibility. Recovery: inventory title, description, generic discussions, remediation roots/replies, and adapter/reference inputs at their admission boundaries; keep DLP results inside per-source enrichment state; assert safe-context approval parity and separately assert admitted-remediation comment-only behavior.
- Risk: provider drift creates mixed or duplicated projections. Recovery: compare canonical complete snapshots including identity and ordering; emit only closed `mutated`, `partial`, or `unavailable` state and commit no partial store.
- Risk: marker-like user content is treated as toolkit ownership. Recovery: require active bot ID plus strict marker/fingerprint parsing and cover forged roots adversarially.
- Risk: raw provider identities leak through diagnostics or receipts. Recovery: retain run-local pseudonyms only, assert serialized artifacts/log capture, and discard rejected values without locations.
- Risk: documentation inventory drifts from runtime. Recovery: own the supported/default inventory in executable contract data and compare public tables/examples against it.
- Risk: the final-only push boundary is violated. Recovery: keep every new planning/implementation commit local through `WQ-17`; if an intermediate push occurs, stop and report the lifecycle discrepancy before continuing.
- Risk: external qualification is unavailable. Recovery: leave Draft PR, issues, milestone, and release deferred at the exact locally validated head; resume from `WQ-11` only when external evidence exists.
- Risk: coverage work rewards artificial tests or distorts production boundaries. Recovery: target listed fault/data-flow contracts in their existing owners, reject percentage-only entrypoint/unreachable-line work, and change production only for a demonstrated contract defect.
- Risk: OCR version prose conflates inherited 1.9.9 evidence with the 1.9.10 deployment target. Recovery: keep separate headings in compatibility docs and the OCR maintenance fragment, assert exact manifest/preflight/example defaults, and tell the external agent to start directly with 1.9.10.
- Risk: grouped retry diagnostics leak or influence decisions. Recovery: assert the report stays in private result handling and cannot feed telemetry, DLP, receipt, severity, outcome, or approval.

#### Resume Point

Continue at `WQ-18`: commit the reviewed coverage-gate slice, complete final reproducible artifact/clean-install and secret/history validation, record the exact final commit/tree/checksum handoff, push once to Draft PR #122, wait for exact-head hosted CI, and update PR #122 plus #120. Do not ready, merge, publish stable, or close issues/milestone; external qualification remains `WQ-11`.

#### Plan Fidelity Check

- [x] Every user-requested outcome has a stable `REQ-###` entry and one or more ordered work-queue owners.
- [x] Release-required implementation and release-deferred stable delivery are both explicit.
- [x] GitHub writes, push ordering, commit gates, and issue/milestone non-closure are preserved.
- [x] Full MR-text DLP coverage, auto-approval independence, comment-only remediation, identity, privacy, and mutation trust boundaries are explicit.
- [x] Local OCR/LLM restrictions, inherited OCR 1.9.9 evidence, and exact OCR 1.9.10 target are explicit.
- [x] Meaningful boundary-test scope, non-overengineering limits, combined coverage, and four risk-group floors are explicit.
- [x] Validation covers functional, adversarial, artifact, documentation, release, and hosted gates.
- [x] Non-goals preserve the retest and instruction-migration decisions.
- [x] The Resume Point names the first safe unfinished action.

#### Reconciliation Check

- [x] Current repository head `373fc2d`, clean worktree, Draft PR #122 checks, issue/milestone baseline, workflow version, and index-audit baseline have been read back.
- [x] The work queue preserves every logical slice and the external qualification phase.
- [x] No existing completed work is represented as pending implementation.
- [x] No release, merge, issue closure, or external qualification is claimed complete.

#### Closure Gate

- [ ] All in-scope `REQ-###` items are `done` or explicitly justified `out_of_scope`; `WQ-13` through `WQ-18` are complete and only externally owned `WQ-11` remains pending.
- [ ] Each new logical slice has focused test evidence, full diff self-review, boundary reconciliation, `git diff --check`, and a signed commit.
- [ ] Holistic privacy, architecture, requirements, telemetry, data-flow, documentation, and omission review is complete with no unresolved findings.
- [ ] The final local validation matrix and hosted CI are green for the exact feature head.
- [ ] `PLANS.md`, roadmap/strategy, Towncrier fragments, Draft PR, issues, milestone, and remote refs agree that implementation is complete but stable release remains externally blocked.
- [ ] Plan lifecycle validation succeeds before any eventual closure transition.

#### Post-Close Delivery

- Initial planning push and Draft PR were completed at `WQ-02`; one final implementation push and hosted CI are now in scope only at `WQ-18`.
- External qualification, ready-for-review transition, exact-head merge, TestPyPI development reconciliation, release branch/PR, stable publication, and issue/milestone closure remain pending `WQ-11` and are not authorized before the required receipt.
- If external evidence invalidates an assumption, reopen active corrective work rather than rewriting completed validation history.

#### Handoff Notes

- Do not push implementation commits individually. Keep all new slices local until `WQ-17` is complete; push once at `WQ-18`.
- Do not use local OCR for model review. Prefer the controlled subprocess peer for installed-artifact tests.
- Keep OCR 1.9.9 inherited and OCR 1.9.10 changed/deployed text separate in evidence, docs, changelog, PR, and #120. The external agent starts directly with OCR 1.9.10.
- Keep #120's existing core body and explicit non-goals intact; append coordination only and track mention behavior in its own child issue.
- When resuming after interruption or compaction, read this plan, inspect `git status` and local/remote commit graphs, reconcile requirement/queue states, and continue from the first non-terminal queue item.
