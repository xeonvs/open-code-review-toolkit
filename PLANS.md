# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### OCR 1.10.0 integration, review effort, and compatibility failure recovery

Status: `active`
Owner: Codex
Release classification: `release-required`
Target stable version: `0.8.2`
Plan Origin: `plan_mode_approved`
Last Updated: 2026-08-25

#### Goal

Qualify and integrate checksum-pinned Open Code Review 1.10.0, expose its bounded
review-effort control with a toolkit default of `medium`, preserve toolkit-owned
result, DLP, receipt, and approval boundaries around new group/round data, repair
the compatibility workflow so failed qualifications retain a canonical issue and
bounded artifact, complete the activated BL-017 signal-ownership audit without a
second telemetry layer, update the PATH-effective local OCR binary safely, and
deliver the result through the protected toolkit 0.8.2 release lifecycle.

#### Requested Scope

- Create `codex/v0.8.2-ocr-1.10.0` from synchronized `main`, make this plan the
  first repository write, commit it with an SSH signature, push it, and open a
  Draft PR before product implementation.
- Create milestone `v0.8.2`, one canonical OCR 1.10.0 qualification issue with
  the stable workflow marker, and bounded linked work for compatibility failure
  recovery and the BL-017 measurement audit.
- Repair the deterministic OCR compatibility gateway for OCR 1.10.0's required
  comment `path`, semantic grouping, group-level filtering, and multi-round
  lifecycle; qualify the exact hosted Linux amd64 artifact before promotion.
- Preserve a failed qualification as a closed schema-versioned status, update
  the canonical issue, upload the artifact, and still fail the qualification
  job so aggregation and promotion cannot proceed from incomplete evidence.
- Promote manifest, preflight, public GitLab example, documentation, and machine
  evidence from OCR 1.9.10 to exact OCR 1.10.0 with hosted asset/checksum parity.
- Add `OCR_REVIEW_EFFORT` with exact values `low`, `medium`, or `high`; default
  it to `medium`, write OCR's root `effort` config, and preserve an explicit OCR
  `--effort` CLI flag as the per-run override.
- Keep `OCR_LLM_MAX_COMPLETION_TOKENS` unset by default. Qualify and document
  inherited OpenAI completion caps separately: 58,888 for OCR 1.9.10 and 16,384
  for OCR 1.10.0, while retaining explicit `4096` as the operator workaround for
  gateways that reserve spending against the requested output cap.
- Reject caller-owned OCR `--output`, `--output=...`, `-o`, and attached short
  forms before OCR execution. Continue capturing stdout through the toolkit's
  pre-opened owner-only result descriptor and keep `--result` toolkit-owned.
- Treat additive OCR `groups` labels and paths as untrusted private result data.
  They may be privately sanitized but never enter findings, GitLab text, receipt
  v5, severity, fingerprints, lifecycle commands, toolkit telemetry, or approval.
- Document semantic grouping, review rounds, budget/cost effects, output-path
  ownership, completion-cap migration, git-error privacy, and OCR telemetry
  cardinality without adopting a second exporter or trusting MR content as a
  configuration authority.
- Activate and complete the bounded BL-017 audit. Keep BL-016 parked, BL-018
  conditional, and BL-019/BL-020 inactive; reconcile backlog, strategy, roadmap,
  engineering navigation, and execution history only to the achieved truth.
- Update the PATH-effective local `/opt/homebrew/bin/ocr` atomically from its
  current 1.8.10 Darwin arm64 binary to exact 1.10.0 after checksum and contract
  acceptance, without changing the user's OCR config, credentials, or HOME.
- Produce separate agent- and human-readable Towncrier fragments for maintenance,
  feature, and bug-fix outcomes, then run the protected 0.8.2 lifecycle through
  exact-head qualification, merge, registry publication, and external readback.

#### Requirement Traceability

- `REQ-001` (`done`): materialize the approved full plan first, create the
  feature branch, signed planning commit, initial push, Draft PR, milestone, and
  linked issue structure. Covered by `WQ-01` and `WQ-02`.
- `REQ-002` (`done`): make failed compatibility qualification produce a
  bounded status, canonical issue update, and artifact while the job remains red
  and aggregate remains blocked. Covered by `WQ-03`.
- `REQ-003` (`done`): adapt deterministic qualification to OCR 1.10.0 comment
  paths, grouping, filters, effort rounds, usage, budget, and version-specific
  completion caps. Covered by `WQ-03` and `WQ-04`.
- `REQ-004` (`done`): independently source-audit, checksum-verify, and qualify
  OCR 1.10.0 Linux amd64, then promote every manifest, preflight, example, and
  evidence owner without changing historical OCR 1.9.10 evidence. Covered by
  `WQ-04` and `WQ-05`.
- `REQ-005` (`done`): add the exact documented environment contract
  `OCR_REVIEW_EFFORT=medium`, closed validation, root-config projection, and
  explicit CLI override precedence without MR-controlled routing. Covered by
  `WQ-05`.
- `REQ-006` (`done`): reject caller OCR output-path controls and preserve the
  existing safe result descriptor, cleanup, and failure behavior. Covered by
  `WQ-05`.
- `REQ-007` (`done`): prove new group/round fields remain provider-neutral,
  private, DLP-bounded, receipt-independent, and unable to alter severity,
  findings, approval, posting, or lifecycle commands. Covered by `WQ-06`.
- `REQ-008` (`pending`): complete the BL-017 source-to-signal audit with a
  no-new-layer conclusion unless evidence demonstrates a separately scoped gap;
  preserve BL-016/018/019/020 activation boundaries. Covered by `WQ-07`.
- `REQ-009` (`pending`): publish version-separated, deployment-actionable docs
  and changelog text covering added, changed, rejected, inherited, telemetry,
  privacy, and migration behavior. Covered by `WQ-07` and `WQ-08`.
- `REQ-010` (`pending`): atomically update local OCR to checksum-verified Darwin
  arm64 1.10.0 and pass isolated no-LLM checks without modifying user config.
  Covered by `WQ-09`.
- `REQ-011` (`pending`): complete focused and one final full local validation,
  exact-head hosted PR checks, a bounded real-model production-path review, and
  the protected 0.8.2 release/readback lifecycle without restoring validation
  duplication removed by #132. Covered by `WQ-10` through `WQ-12`.

#### Explicit Non-Goals

- Do not fork or patch upstream OCR, run `ocr scan`, adopt OCR's `--output` file
  ownership, or add a second review engine, grouping implementation, or result
  writer.
- Do not derive effort, model, provider, completion cap, approval, suppression,
  severity, or lifecycle state from merge-request title, description, paths,
  diff, discussions, group labels, model prose, or raw provider errors.
- Do not implement automatic effort/profile routing or activate BL-016/BL-018;
  explicit `medium` is an operator-owned default, not an inferred policy.
- Do not publish raw group labels, file paths, provider identities, response
  bodies, request IDs, stderr, failed compatibility exception text, or rejected
  DLP values in issues, notes, receipts, or toolkit telemetry.
- Do not create a general configuration file framework, fuzzing campaign, new
  coverage framework, new telemetry exporter, or broad test-directory rewrite.
- Do not weaken or disable Bandit, Gitleaks, CodeQL, dependency review, coverage,
  protected-branch, artifact, provenance, or registry gates. Do not run a
  separate Codex Security scan unless a later validated finding requires it.
- Do not edit the user's OCR config or credentials, invoke a real model during
  the local binary replacement, or preserve downloaded binaries in the repo.
- Do not close issues, milestone, active plan, or stable-release state before
  independent external reconciliation confirms the exact published artifacts.

#### Constraints

- `main` is clean and equals `origin/main` at stable toolkit v0.8.1 commit
  `b0ffdd3c324afe9095ee966b339748d5944b029b`; `.next-version` is `0.8.2`.
- The approved effort decision supersedes the earlier recommended `low`: toolkit
  default is exactly `medium`; `low` and `high` remain explicit alternatives.
- Each logical commit requires focused tests, full slice diff self-review,
  requirements and trust/data-flow reconciliation, `git diff --check`, and an
  SSH-signed commit. New non-trivial tests receive concise behavioral docstrings;
  docstrings name a concrete OCR version only when the assertion is versioned.
- Preserve the #132 ownership split: focused checks per slice, one complete local
  quality gate before final publication, one hosted coverage owner, one PR build
  owner, and complete stable-release gates only at the release boundary.
- The hosted Linux amd64 compatibility probe is primary version evidence. The
  Darwin arm64 probe is an independent local wire/CLI check with an isolated
  temporary HOME and deterministic HTTP peer, never a real LLM call.
- Qualification failures retain only closed status codes in public artifacts;
  raw exception detail may remain only in the bounded workflow log for synthetic
  compatibility fixtures and may not include credentials or private repository
  content.
- Receipt schema stays v5. Existing DLP distinction between private sanitization
  and publication filtering, partial-review approval blocking, posting rollback,
  fingerprinting, and human ownership must remain intact.
- The real-model exact-head qualification uses the existing owner-configured
  provider only after local and hosted deterministic gates are green, with
  `OCR_LLM_MAX_COMPLETION_TOKENS=4096`; absence or failure of that environment
  changes the release state to `release-deferred` rather than weakening gates.

#### Inputs And Sources

- User-approved v0.8.2 plan and the later explicit choice of default
  `OCR_REVIEW_EFFORT=medium`.
- Root `AGENTS.md`, engineering-workflow 0.8.1, `docs/development.md`,
  `docs/release.md`, project principles, compatibility policy, public
  configuration/operations/GitLab contracts, and the #132 validation split.
- Stable main v0.8.1, issues #129/#130/#132, current OCR support manifest and
  evidence, existing compatibility harness, result/DLP/receipt/approval code,
  environment-contract tests, and GitLab example.
- Official upstream OCR v1.10.0 release, compare from v1.9.10, commit
  `a66240084b382ed97a47590bdec13a6a34df0743`, GitHub asset digests, and
  `sha256sum.txt`.
- Failed scheduled workflow run 32815275725: discovery passed; qualification
  failed because the existing deterministic response emitted no accepted
  comment; issue upsert and artifact upload were then skipped.
- Read-only exact Darwin arm64 probe during planning: reported OCR v1.10.0 and
  reproduced `candidate full review did not emit the synthetic comment` without
  a real LLM or user-config change.
- BL-016 through BL-020, toolkit strategy/roadmap, and engineering signal owners
  for backlog reconciliation.

#### User Decisions And Answers

- Ship OCR 1.10.0 in the next toolkit release and update the local OCR binary.
- Investigate every upstream change and prioritize what materially benefits the
  toolkit; track demonstrated backlog relationships without overengineering.
- Fix the compatibility Action failure and the missing canonical issue/artifact,
  rather than rerunning the unchanged failing workflow repeatedly.
- Default `OCR_REVIEW_EFFORT` to `medium`, accepting up to two review rounds and
  the associated cost/latency change; document `low` as the explicit economy
  choice and `high` as deliberate deeper review.
- Preserve provider-neutral architecture, DLP/approval independence, safe handling
  of every MR-controlled text source, accurate release-note categorization, and
  agent-readable deployment/migration language.
- Keep tests in their existing thematic owners, add meaningful boundary evidence,
  and avoid mechanical file/subdirectory reorganization or percentage-only tests.
- Preserve efficient validation ownership from #132 instead of repeating the
  full suite locally, on every push, after main merge, and again without a new
  trust boundary.

#### Completed Baseline State

- Toolkit v0.8.1 is stably released and `main` is synchronized and clean.
- OCR 1.9.10 is the exact current recommended/preflight/example version with
  immutable compatibility evidence; OCR 1.9.9 remains historical predecessor.
- `OCR_LLM_MAX_COMPLETION_TOKENS` already provides closed protocol-aware override
  mapping and is unset by default; provider failures already publish safe static
  GitLab guidance without raw provider fields or stderr.
- Receipt v5, canonical publication/DLP projection, partial-review approval
  blocking, context-store/MCP boundaries, provider-neutral codehost contracts,
  and GitLab posting transactions are implemented and covered.
- Combined branch coverage floor is 85% with four risk-group floors; PR and
  release validation ownership was deduplicated in #132.
- The PATH-effective local OCR is user-owned Darwin arm64 v1.8.10 at
  `/opt/homebrew/bin/ocr`; it is not managed by a Homebrew formula or cask.
- Latest upstream stable OCR is v1.10.0. Official SHA-256 values relevant here
  are Linux amd64 `f8f99ea071bed77dbcaa15fdd2083287bb8ae408d5928b3943ebe0788d191b6b`
  and Darwin arm64 `c8f51b17c2be193ca178ecce6b5bcc1e38a5614629fbe81c6e1c95af5ede12e4`.

#### Current Work Queue

1. `WQ-01` (`done`): pass plan fidelity, create the feature branch, perform
   planning self-review/checks, and make the signed planning commit.
2. `WQ-02` (`done`): push planning head, open Draft PR, create/read back
   milestone and canonical/sub-issue coordination.
3. `WQ-03` (`done`): implement bounded failure status plus always-run issue and
   artifact handling; add workflow/CLI tests and preserve final failure outcome.
4. `WQ-04` (`done`): adapt the gateway and real OCR contracts for path,
   grouping, filtering, effort rounds, budget, usage, and completion caps; push
   the signed qualification checkpoint and run hosted Linux qualification.
5. `WQ-05` (`done`): validate hosted evidence, promote OCR 1.10.0, add
   `OCR_REVIEW_EFFORT=medium`, reject OCR output-path ownership, and update exact
   environment/config/installed-artifact contracts.
6. `WQ-06` (`done`): add focused groups/DLP/receipt/approval/result regressions
   and repair only real contract violations exposed by them.
7. `WQ-07` (`in_progress`): complete BL-017 audit and reconcile backlog, strategy,
   roadmap, telemetry privacy/cardinality, and no-new-layer conclusion.
8. `WQ-08` (`pending`): update public docs, examples, compatibility text, test
   evidence matrix, and separate Towncrier feature/bugfix/maintenance fragments.
9. `WQ-09` (`pending`): checksum-verify and atomically install local Darwin arm64
   OCR 1.10.0; run version/help/no-LLM isolated contract checks and clean temporary
   artifacts with rollback on failure.
10. `WQ-10` (`pending`): perform holistic requirements/privacy/architecture/data-
    flow/telemetry/docs self-review and one final local quality/security/manifest/
    changelog gate; update plan to exact implementation truth and final commit.
11. `WQ-11` (`pending`): push final signed history, wait for exact-head hosted PR
    checks, fix only evidence-backed failures through the same commit gate, and
    perform bounded real-model exact-head qualification.
12. `WQ-12` (`pending`): ready and merge the protected feature PR, verify the
    TestPyPI development artifact, execute protected release/v0.8.2, independently
    reconcile PyPI/TestPyPI/provenance/tag/GitHub Release/receipt/install state,
    close issues and milestone through release automation, archive this plan with
    `scripts/plan_lifecycle.py`, and synchronize clean local `main`.

#### Locked Decisions

- Toolkit target is 0.8.2; exact OCR target is 1.10.0.
- `OCR_REVIEW_EFFORT` is a closed lower-case enum with exact default `medium`.
- Explicit OCR `--effort` remains the per-run override; no second CLI wrapper flag
  and no MR-derived automatic routing are introduced.
- OCR `groups` is optional untrusted private data, not a toolkit public contract
  or approval/receipt/telemetry input.
- OCR `--output/-o` is not adopted because it transfers path creation/truncation
  ownership across the toolkit's existing safe result boundary.
- OCR 1.10.0 inherited completion cap is documented and qualified as 16,384, but
  toolkit completion-cap default remains unset and explicit 4,096 remains the
  recommended gateway-specific workaround.
- Compatibility failure status uses closed phase/reason values and the same stable
  version marker; success and failure never own separate issues.
- BL-017 completes as a bounded ownership audit with no new exporter unless the
  audit proves a separate gap; current evidence expects `no-new-layer`.
- Local OCR replacement occurs only after exact checksum and contract acceptance,
  uses an atomic rollback transaction, and never edits user configuration.

#### Verification

- Planning: plan-fidelity check, full `PLANS.md` diff review, `git diff --check`,
  signed commit verification, remote branch/Draft PR/issue/milestone readback.
- Workflow failure: unit tests for success/failure status schemas, bounded public
  rendering, duplicate issue prevention, failed-job preservation, always-run
  issue/artifact steps, cancelled behavior, and aggregate blocking; YAML parse.
- OCR contracts: exact Linux hosted and Darwin local binaries, asset digest plus
  checksum-file agreement, version/help/preview, two-file grouping, path-aware
  finding, low/medium rounds, early stop, group filter, budget partial, token/tool
  accounting, inherited/explicit completion caps, and target-rule selection.
- Runtime config: exact environment set/default tests, closed effort enum,
  generated root config, CLI precedence documentation, installed-artifact
  configure/preflight/review checks, and caller output-option rejection forms.
- Privacy/approval: safe and hostile group metadata, PII/secret/laundering/private
  sanitization, no publication/receipt/log/toolkit-telemetry projection, unchanged
  finding fingerprint/severity, safe auto-approval parity, and fail-closed partial,
  malformed, budget, or publication-filtered cases.
- Documentation/backlog: current-version/default/checksum consistency, BL-017
  source-to-signal matrix, BL-016/018/019/020 status checks, rendered Towncrier
  categories, links/index checks, and deployment-agent language review.
- Final local: focused suites while iterating; once at final head run
  `scripts/quality.sh check`, `scripts/gitleaks.sh`, `uv lock --check`,
  `scripts/ocr_compat.py validate`, Towncrier draft, `git diff --check`, and the
  repository privacy scan. Do not repeat clean multi-Python installs locally
  because hosted Build artifacts and release gates own that boundary.
- Hosted/delivery: all required feature-PR checks, exact-head real-model review,
  protected merge, TestPyPI development build/provenance/install readback,
  protected stable release, immutable registry/GitHub/tag/receipt readback, and
  supported-Python install verification.

#### Latest Validation Results

- `2026-08-25`: `main` and `origin/main` both resolve to
  `b0ffdd3c324afe9095ee966b339748d5944b029b`; worktree is clean and next version
  is 0.8.2.
- `2026-08-25`: engineering-workflow 0.8.1 audit found all canonical files and
  required documentation indexes; no index errors. Audit noise is confined to
  ignored disposable `.quality-logs` environments, which remain untouched.
- `2026-08-25`: GitHub CLI is authenticated with repository/workflow scope.
  Scheduled compatibility run 32815275725 discovered v1.10.0, then failed its
  full-review contract; issue upsert and artifact upload were skipped and the
  aggregate job did not run.
- `2026-08-25`: official release metadata and upstream source comparison identify
  semantic grouping/rounds, path-aware comments, output-file support, and git
  diagnostic changes; exact public asset hashes are recorded above.
- `2026-08-25`: an isolated checksum-verified Darwin arm64 1.10.0 planning probe
  reproduced the compatibility comment failure without using a real LLM or
  changing the installed OCR/config; all temporary probe/source directories were
  removed afterward.
- `2026-08-25`: the complete schema-v2 active plan passed engineering-workflow
  `plan_lifecycle.py check`; full plan diff self-review and `git diff --check`
  passed with no product or external mutation before the planning checkpoint.
- `2026-08-25`: signed planning commit
  `4cc7d6427cfebd26db6ff26739f8710d4b8ae134` was pushed and opened Draft PR
  #134. Milestone `v0.8.2` contains canonical OCR issue #135 and linked sub-issues
  #136 (failed-qualification retention) and #137 (BL-017 audit); GitHub API
  readback confirms all three open issues and both parent-child relationships.
- `2026-08-25`: failed qualification now emits only the closed
  `ocr-toolkit.compatibility-status/v1` projection to issue automation, retains
  raw diagnostics in the private job log, always attempts canonical issue and
  artifact handling, and explicitly restores the red job outcome. Ruff, mypy,
  83 focused compatibility/workflow tests, YAML parsing, plan validation, and
  `git diff --check` pass; self-review also added the pre-manifest failure path.
- `2026-08-25`: an isolated checksum-verified Darwin arm64 OCR 1.10.0 contract
  run passed the adapted real-binary gateway: path-aware comments, one semantic
  grouping call, two default-medium review rounds, one filter call, inherited
  `max_completion_tokens=16384`, explicit override `4096`, the existing partial
  budget contract, result consumers, and telemetry-off environment. The binary,
  HOME, repositories, and receipt were temporary and removed; installed OCR and
  user configuration remain unchanged.
- `2026-08-25`: hosted Linux run 32825123658 passed on exact head `3c49968`,
  updated canonical issue #135, retained its seven-day artifact, and produced
  human-review-required evidence with Linux amd64 SHA-256
  `f8f99ea071bed77dbcaa15fdd2083287bb8ae408d5928b3943ebe0788d191b6b`. The reviewed source and
  wire contract were accepted and promoted to manifest/preflight/example owners.
  `OCR_REVIEW_EFFORT` now defaults to root-config `medium`, explicit CLI effort
  remains authoritative, caller output paths fail before preview, and 272 focused
  tests plus 104 subtests, installed wheel/sdist checks, Ruff, mypy, manifest
  validation, and `git diff --check` pass. Promotion also exposed and fixed the
  relative-manifest success-reporting bug in the compatibility CLI.
- `2026-08-25`: additive OCR group labels, file lists, and round diagnostics have
  explicit boundary regressions: safe values leave the canonical result and
  auto-approval decision unchanged; PII and recognized secrets are sanitized in
  the private result without becoming a publication failure; neither safe nor
  sanitized values enter receipt v5; and receipt extensions fail closed. The 129
  focused review/approval tests plus 71 subtests, Ruff, and `git diff --check`
  pass. Direct mypy invocation over test files remains non-owner validation and
  reports pre-existing test-module export errors; the repository quality owner
  remains the final typed gate.

#### Risks And Recovery

- Risk: the gateway fixture accidentally models OCR internals instead of the
  consumed public wire contract. Recovery: keep stage detection structural,
  assert real binary output/counters, and separately source-audit upstream logic.
- Risk: failure handling masks the qualification exit. Recovery: preserve the
  failed step outcome, run only issue/artifact cleanup afterward, then use an
  explicit terminal step to fail the job; aggregate continues to require success.
- Risk: medium effort silently changes cost or turns budgeted runs partial.
  Recovery: document exact default/round count, retain explicit low override,
  count grouping/round usage, and keep partial outcomes approval-ineligible.
- Risk: group labels/paths leak through additive fields, private diagnostics, or
  upstream telemetry. Recovery: exclude them from the canonical projection,
  re-sanitize private readback, test every sink, default OCR telemetry off, and
  document upstream path/cardinality exposure when operators enable it.
- Risk: OCR `--output` bypasses safe file ownership. Recovery: reject every long,
  equals, short, and attached form before preview or model execution.
- Risk: local replacement fails or changes config. Recovery: verify the new file
  before rename, retain the old executable inside the atomic transaction, restore
  it on any failed check, use isolated HOME for probes, and compare user config
  metadata before/after without reading or rewriting credential values.
- Risk: live provider qualification remains unavailable or fails under gateway
  policy. Recovery: keep Draft PR and release issues open, record exact head and
  deterministic evidence, set release `release-deferred`, and resume only from a
  configured environment with explicit cap 4096.
- Risk: validation duplication returns. Recovery: follow #132 ownership, use
  focused local checks per slice and one final full gate, and retain repetition
  only where PR, platform, artifact, release, or registry boundaries differ.

#### Resume Point

Continue `WQ-07`: trace OCR group/round signals from upstream source through the
toolkit's telemetry, receipt, logs, and operator surfaces; record the bounded
BL-017 ownership/cardinality conclusion while preserving the activation state of
BL-016, BL-018, BL-019, and BL-020.

#### Plan Fidelity Check

- [x] Every user-requested outcome and the later `medium` decision has a stable
  requirement and queue owner.
- [x] Product, workflow, local-install, external-issue, qualification, release,
  and post-release outcomes are distinguished.
- [x] Inputs, authoritative documents, upstream evidence, current baseline, and
  rejected alternatives are recorded.
- [x] Data flow, trust boundaries, DLP/approval independence, telemetry privacy,
  result-file ownership, and provider-neutral reuse are explicit.
- [x] Focused, final local, hosted, real-model, artifact, and release validation
  responsibilities are mapped without undoing #132.
- [x] Risks have bounded recovery paths and the first safe unfinished action is
  exact.

#### Reconciliation Check

- [x] `PLANS.md` was empty before this activation; no prior active work was
  overwritten.
- [x] Stable v0.8.1 baseline, closed #129/#130/#132, next version 0.8.2, current
  OCR 1.9.10 support, failed v1.10.0 workflow, and local OCR 1.8.10 agree.
- [x] BL-017 is ready and its trigger is met; BL-016/018/019/020 remain outside
  implementation scope unless later evidence and user approval change them.
- [x] Documentation indexes are complete; no unrelated instruction migration or
  test reorganization is pending.

#### Closure Gate

- [ ] All requirements and queue items are `done` or explicitly `out_of_scope`.
- [ ] Final exact-head validation, self-review, hosted checks, real-model review,
  stable publication, external reconciliation, issue/milestone closure, and local
  OCR verification are recorded.
- [ ] Backlog, roadmap, strategy, public docs, changelog, manifest/evidence, and
  execution history describe the same delivered state.
- [ ] `scripts/plan_lifecycle.py check` passes before the checked close/archive
  transition; `PLANS.md` is not manually marked done.

#### Post-Close Delivery

- Protected feature PR merge, TestPyPI development verification, stable release
  PR, PyPI/TestPyPI publication, provenance/attestation, annotated tag, immutable
  GitHub Release and release receipt, supported-Python registry installs, issue
  receipts, milestone closure, and clean synchronized `main` are in scope for the
  complete requested release and remain pending until independently verified.

#### Handoff Notes

- Resume from the first non-terminal WQ item and update this plan before every
  signed commit, push, external qualification, release transition, or handoff.
- Do not infer success from repository prose, a green aggregate summary, or an
  installed version string alone; retain exact commit/tree, asset hashes, job
  conclusions, artifacts, and registry/GitHub readback for each boundary.
