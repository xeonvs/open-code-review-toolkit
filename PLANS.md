# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Toolkit 0.8.6 - OCR 1.11.0 and precise security-signal classification

Status: active

#### Goal

Prepare a fully implemented, validated, and hosted-green Draft feature pull request for
toolkit 0.8.6. The Draft qualifies and exclusively targets OCR 1.11.0, preserves private
reasoning and provider request controls across the existing DLP/publication boundary,
fixes issue #153's false security promotion, and leaves merge and stable publication to a
later owner-authorized continuation.

#### Plan Origin

`plan_mode_approved`

#### Requested Scope

- Create `v0.8.6`, assign open issue #153 and the canonical OCR 1.11.0 compatibility issue
  to `xeonvs`, and keep both issues plus the milestone open at handoff.
- Update the qualification harness before dispatch so exact OCR 1.10.2 comparison evidence
  and exact OCR 1.11.0 candidate evidence use their own strict grouping inventory formats.
- Manually dispatch hosted compatibility qualification for exact `v1.11.0`, review its
  machine evidence and upstream source semantics, and promote only confirmed contracts.
- Make OCR 1.11.0 the sole runtime/preflight target; retain 1.10.2 only as historical and
  transition-comparison evidence, never as a supported fallback.
- Verify new grouping inventory, `file_find`, Handlebars/Mustache rules, timeout scaling,
  private reasoning replay, `tool_choice`, completion-cap, effort, and max-tools behavior.
- Preserve one data flow from private OCR session/result through canonical projection,
  DLP, publication, receipt, and approval; do not add a public reasoning schema.
- Fix #153 so neutral domain phrases do not promote reviewer-guide security counts while
  closed, contextual injection classes and explicit security metadata continue to do so.
- Correct the root README installation path and current public documentation for exact
  Python/OCR requirements, privacy boundaries, provider controls, and external validation.
- Atomically update the PATH-effective local Darwin arm64 OCR to exact 1.11.0 and perform
  only checksum-verified no-LLM checks without changing configuration, credentials, or
  the caller-owned home.
- Finish with one green Draft PR. Do not mark it ready, merge it, prepare a release branch,
  tag, publish packages, close issues, or close the milestone.

Release classification: `release-required`; target stable version: `0.8.6`; delivery
state for this task: `release-deferred` after a green Draft handoff.

#### Requirement Traceability

| Requirement | Outcome | Queue | Verification |
| --- | --- | --- | --- |
| `REQ-001` | Start from synchronized released v0.8.5, materialize this plan first, and open a Draft only after signed plan/harness commits. | `WQ-01`, `WQ-02` | Git status, plan fidelity, signed commits, remote/Draft readback |
| `REQ-002` | Strictly distinguish old 1.10.2 and new 1.11.0 grouping inventory in qualification without production backward compatibility. | `WQ-02` | Focused parser/gateway tests and exact workflow dispatch |
| `REQ-003` | Create and reconcile milestone v0.8.6, #153, and the canonical OCR 1.11.0 issue. | `WQ-03` | GitHub API readback |
| `REQ-004` | Qualify and exclusively adopt checksum-pinned OCR 1.11.0 with a complete semantic source audit. | `WQ-03`, `WQ-04` | Hosted evidence, hashes, manifest/preflight/example tests |
| `REQ-005` | Verify grouping, file lookup, rules, timeout, reasoning replay, tool choice, completion, effort, and max-tools contracts without public schema drift. | `WQ-04`, `WQ-05` | Controlled gateway and installed-artifact contract tests |
| `REQ-006` | Keep reasoning/session/provider request data private and preserve DLP, receipt v5, telemetry, summary, and approval boundaries. | `WQ-05` | Hostile projection, cleanup, receipt, approval, and leak regressions |
| `REQ-007` | Fix #153 using a closed contextual injection matcher that affects only reviewer-guide analytics. | `WQ-06` | Issue reproducer, positive/neutral/Unicode tests, input immutability |
| `REQ-008` | Update README, public docs, backlog reconciliation, and categorized release notes for humans and release agents. | `WQ-04`, `WQ-07` | Documentation contracts, Towncrier draft, link/version consistency |
| `REQ-009` | Replace local OCR safely and validate exact 1.11.0 without LLM or user-config changes. | `WQ-04` | Binary digest/version/help and isolated no-LLM previews |
| `REQ-010` | Complete one local final gate, push once, reconcile hosted CI and leave a clean green Draft with an exact external qualification checklist. | `WQ-08`, `WQ-09` | Quality/coverage/security gates, remote/PR/check/thread/worktree readback |

#### Explicit Non-Goals

- No real LLM/provider call in this environment and no local model peer.
- No compatibility range, production parser fallback, migration layer, or support promise
  for OCR 1.10.x or older; the 1.10.2 run is comparison evidence only.
- No new public result, receipt, telemetry, DLP-signal, or approval schema and no second
  reasoning-specific DLP pipeline.
- No publication of prompts, reasoning, provider bodies, tool arguments/results,
  credentials, model/provider identity, request IDs, paths, or session files.
- No dynamic timeout environment variable, second compatibility cron, polling service,
  unpinned npm OCR recommendation, or global bare-pip installation guidance.
- No consumption of upstream GitHub Action, OpenCode plugin, npm launcher, Korean docs,
  or provider preset changes.
- No mechanical test-directory reorganization or production refactor solely for coverage.
- No stable release, TestPyPI/PyPI publication, PR merge, issue closure, or milestone closure.

#### Constraints

- Runtime preflight accepts exact OCR 1.11.0 only. Version-aware old-format parsing is
  confined to the repository qualification harness and cannot enter production runtime.
- Baseline 1.10.2 accepts only `path (STATUS, +N/-M)`; candidate 1.11.0 accepts only
  `STATUS   path (+N/-M)`. Mixed, duplicate, malformed, reordered, truncated, overflowed,
  status-inconsistent, or churn-losing inventories fail closed.
- `reasoning_content`, Anthropic signed thinking, Responses encrypted reasoning,
  `tool_choice`, and OCR session cache remain provider/session-private. They never affect
  findings, severity, DLP counts, summary analytics, receipt, telemetry, or approval.
- Existing canonical-public DLP remains authoritative: private-only unknown fields may be
  removed without blocking approval only when the canonical public projection is byte
  equivalent; canonical/public filtering always blocks approval.
- OCR temporary HOME cleanup completes before publication. Cleanup failure, hostile
  replay, impossible receipt state, or leaked reasoning fails closed.
- The #153 matcher consumes only the already DLP-checked published finding projection and
  changes only reviewer-guide security count/effort, never finding or lifecycle state.
- Every new production and test function receives a purpose-focused docstring.
- Before every signed logical commit: focused tests, complete slice diff self-review,
  requirement/trust/data-flow/privacy review, backlog reconciliation where applicable,
  format changed Python with Ruff, run repository-wide `ruff format --check .`, and
  `git diff --check`. The existing `scripts/quality.sh check` remains the single complete
  final gate; do not add a duplicate formatting owner.
- After the initial plan/harness push, do not push partial implementation; perform one
  final push only after all local slices and final gates are complete.

#### Inputs And Sources

- Owner-approved implementation plan in the preceding Plan Mode conversation.
- Released toolkit v0.8.5 at `72c511104f078110ea78bb8f1f2bb1d4048f4d20`,
  `.next-version` `0.8.6`, open issue #153, and current repository contracts.
- Official OCR v1.11.0 release, adjacent 1.10.2 source comparison, release assets,
  checksums, help output, and upstream feature/fix history.
- Exact release anchors: Linux amd64
  `13f68cc2eca1a36d42140e9d37797b68fea5cbbf4b6345ec01ec1b06910fab60`, Darwin arm64
  `ac8bf5a0fcd176bb9dcc15b169e90f4b52bf32787adef17a850489dbed97fb78`, and
  `sha256sum.txt` `9dff050ec859882bef26037415b8bd9e5db70c5a7d960e5eb3989385372311ee`.
- Current compatibility manifest/evidence/harness/workflow, runtime preflight/configuration,
  review runner/result publication/DLP/receipt/approval, posting formatter, tests, README,
  public docs, strategy, roadmap, and backlog.
- Workflow audit using engineering-workflow 0.8.2: mature repository, canonical owners
  and required navigation indexes present; no instruction migration required.

#### User Decisions And Answers

- Target toolkit 0.8.6 and OCR 1.11.0 in one Draft-only delivery.
- Support only the current OCR release; comparison with 1.10.2 must not become backward
  compatibility.
- Include exact old/new grouping checks and provider-wire checks in the Draft handoff for
  another environment with configured OCR and LLM access.
- Treat reasoning and tool choice comprehensively, extend DLP edge coverage, and update
  stale root README installation guidance.
- Update the local OCR binary, but skip local LLM calls in this environment.
- Use complete logical signed commits with self-review; leave the final PR in Draft.

#### Completed Baseline State

- `main` and `origin/main` are clean and synchronized at released v0.8.5 commit
  `72c5111`; there are no open PRs and no v0.8.6 milestone.
- Issue #153 is the sole open issue and has no assignee or milestone.
- The manifest/preflight/example and PATH-effective local OCR target exact 1.10.2.
- Compatibility discovery runs once daily at `07:15 UTC` and retains exact manual
  dispatch. No 1.11.0 issue has yet been created.
- The qualification stub parses only the old grouping inventory, so dispatching 1.11.0
  before the harness correction would produce false failure evidence.
- Root README recommends package installation without a Python range or isolated CLI
  owner and refers only generically to a separately installed supported OCR.

#### Current Work Queue

| Queue | Status | Deliverable |
| --- | --- | --- |
| `WQ-01` | `done` | Full plan materialized first and passed the workflow fidelity/lifecycle check. |
| `WQ-02` | `done` | Strict grouping harness committed; the two signed initial commits were pushed and Draft PR #154 opened. |
| `WQ-03` | `done` | Milestone v0.8.6 and issue #155 are coordinated; hosted run 33158664020 produced accepted exact 1.11.0 evidence. |
| `WQ-04` | `done` | Exact 1.11.0 evidence/pins/preflight/example/docs/rules/timeouts/backlog and max-tools help/runtime distinction are integrated; local OCR is atomically updated and no-LLM qualified. |
| `WQ-05` | `done` | Provider-private reasoning/request fields are stripped before persistence and receipt binding; laundering through public sinks is filtered, explicit tool choice is preserved, and receipt/approval regressions pass. |
| `WQ-06` | `done` | #153 now uses explicit metadata/strong terms plus a closed injection-class matcher over published findings; neutral domains do not inflate guide count or effort. |
| `WQ-07` | `done` | README/public operations/install/formatting guidance and agent-readable categorized changelog are current; the Draft retains the external old/new grouping and provider-wire qualification table for final-head binding. |
| `WQ-08` | `pending` | Run holistic self-review and the one complete local final gate; update plan to truthful Draft handoff state. |
| `WQ-09` | `pending` | Final push, hosted CI reconciliation, Draft/issue/milestone/remote/worktree readback. |

#### Locked Decisions

- Branch: `codex/v0.8.6-ocr-1.11.0-security-signal`; Draft base: protected `main`.
- Compatibility comparison is strict and version-bound: 1.10.2 old format versus 1.11.0
  new format. Runtime and public installation support only 1.11.0.
- GitLab example job timeout becomes 45 minutes. OCR base timeout remains inherited 15
  minutes, yielding low/medium/high effective limits of 15/30/45 minutes.
- Completion behavior remains inherited cap 16384 with the existing explicit toolkit
  override example 4096. Default effort remains medium. OCR 1.11.0 only corrects stale
  max-tools help text: runtime behavior is unchanged from the qualified 1.10.2 baseline,
  where `0` selects template default `100`, `1-49` reports normalization to `50` but the
  template remains effective, and only a value above `100` raises the effective cap.
- Provider flow:
  `private session/result -> canonical projection -> DLP -> publication -> receipt/approval`.
- Reviewer-guide flow:
  `DLP-checked published finding -> closed signal matcher -> guide count/effort only`.
- Changelog categories: OCR qualification/pins are Maintenance; Handlebars/Mustache are
  Rules; #153 is Bug Fix; installation and public explanation are Documentation.
- BL-010, BL-017, and BL-021 remain open/conditional because 1.11.0 does not meet their
  exit criteria; record reconciliation without inventing progress.

#### Verification

- Qualification inventory fixtures cover old/new valid forms; add/modify/delete/rename,
  binary and zero-churn records; spaces, parentheses, backslashes, Unicode, duplicate and
  reordered paths; mismatched status, mixed format, truncation, overflow, and malformed
  prompt boundaries.
- Controlled gateway tests cover grouping stage order, medium rounds, cap 16384, explicit
  4096, absent versus explicit `tool_choice`, text-only comment retention, OpenAI Chat
  reasoning replay, Anthropic signed thinking, Responses encrypted reasoning, ordering,
  orphan/duplicate/malformed/cross-protocol payloads, and bounded session behavior.
- DLP tests cover secrets/tokens, PII, paths, URLs, request/model/provider identifiers,
  Markdown/HTML, GitLab commands/mentions, Unicode normalization, bidi/format controls,
  NUL/HTAB/VT/FF, oversized/nested laundering, canonical versus private-only projection,
  hostile replay, receipt rejection, cleanup success/failure, and approval independence.
- #153 tests cover the exact reproducer, explicit metadata, closed injection classes,
  neutral phrases, punctuation/Unicode/word boundaries, determinism, and input immutability.
- Exact 1.11.0 manifest/preflight/example/hash/default/README/documentation/backlog and
  changelog contract tests; local version/help and no-LLM rules/background previews.
- Final local gate once: `scripts/quality.sh check`, coverage floors,
  `scripts/ocr_compat.py validate`, lock check, Towncrier draft, `scripts/gitleaks.sh`,
  and `git diff --check`. Hosted PR workflows own package, OS/Python, dependencies,
  Security, and CodeQL gates.
- External configured-environment checklist compares checksum-verified 1.10.2 and 1.11.0
  on one private fixture, then qualifies exact Draft head with real 1.11.0 and a controlled
  gateway. Only versions, hashes, structural assertions, and pass/fail may enter the PR.

#### Latest Validation Results

- 2026-08-28: `main`/`origin/main` clean at v0.8.5 `72c5111`; no open PR or v0.8.6
  milestone; issue #153 is the only open issue.
- 2026-08-28: engineering-workflow 0.8.2 audit found the mature canonical repository
  owners and documentation indexes present. The audit traversed ignored quality artifacts
  but identified no tracked workflow migration requirement.
- 2026-08-28: exact OCR 1.11.0 release hashes, public help defaults, source changes, local
  1.10.2 state, and the old-format-only grouping harness were read before this first write.
- 2026-08-28: this active plan passes the engineering-workflow lifecycle/fidelity check
  and `git diff --check`; the planning slice has no product/runtime change.
- 2026-08-28: 86 compatibility tests pass, including 14 focused old/new grouping and
  gateway tests; Ruff, MyPy, and `git diff --check` pass. Exact local OCR 1.10.2 also
  passes the strict old-format semantic grouping probe through the loopback-only gateway.
- 2026-08-28: signed planning and grouping-harness commits were pushed once; Draft PR
  #154, milestone v0.8.6, assigned issues #153/#155, and exact-tag compatibility run
  33158664020 are open. The hosted artifact verified all release hashes and candidate
  contracts and requires the planned human semantic conclusion, which has been recorded.
- 2026-08-28: initial Draft CI quality failed only because two newly committed Python files
  were not Ruff-formatted. The canonical local `scripts/quality.sh check` already owns
  `ruff format --check .`; the process correction is to format and run that lightweight
  check before each Python commit. The macOS 3.14 diagnostic independently failed while
  fetching `hatch-vcs` from PyPI after three network retries, not on repository behavior.
- 2026-08-28: upstream release/source and both 1.10.2/1.11.0 hosted artifacts confirm the
  max-tools runtime contract is identical (`0 -> 100`, `49 -> reported 50/effective 100`,
  `50 -> effective 100`, `101 -> effective 101`). OCR 1.11.0 changes help/docs only.
- 2026-08-28: the checksum-verified Darwin arm64 candidate and atomically installed
  `/opt/homebrew/bin/ocr` both report 1.11.0 and pass isolated version/help,
  Handlebars/Mustache system-rule readback, accepted 2,001-character soft background,
  rejected 8,001-character hard background, and no-session preview checks. The previous
  exact 1.10.2 digest was verified before replacement; no LLM, user HOME, configuration,
  or credentials were used.
- 2026-08-28: the integrated OCR slice passes 229 focused tests plus 104 subtests,
  manifest validation, Ruff lint and repository-wide format check, and `git diff --check`.
- 2026-08-28: provider-private reasoning, encrypted/native replay payloads, and request
  `tool_choice` fields are removed from the persisted result without changing a
  byte-equivalent canonical review projection or blocking approval. The same keys in a
  public finding or warning fail closed as `publication-filtered`; receipt v5 rejects
  private replay/request fields, while actual tool-call and reasoning-token counters remain
  available. The focused boundary suite passes 253 tests plus 186 subtests, Ruff, MyPy,
  repository-wide format check, and `git diff --check`.
- 2026-08-28: #153's exact three-finding reproducer now yields one security-sensitive
  finding and effort `2/5`. Explicit security metadata and command/shell, SQL/NoSQL,
  code, template, prompt, LDAP, XPath, CRLF/header, log, HTML/script, and expression
  injection remain promoted across bounded separator/case variants; knowledge, dependency,
  and other non-closed phrases remain ordinary. All 200 posting-helper tests plus 161
  subtests pass with deterministic ordering and no input mutation; Ruff, MyPy,
  repository-wide format check, and `git diff --check` pass.
- 2026-08-28: root installation now requires Python 3.12–3.14, recommends isolated
  `uv tool install`, bounds `pip` to an activated virtualenv, and names exact
  checksum-verified OCR 1.11.0 plus no-LLM version/help smoke checks. Public docs clarify
  max-tools, private reasoning/tool choice, and contextual security signals; required
  environment-variable names remain bold. The canonical development workflow now applies
  Ruff formatting before self-review and checks the entire repository before every Python
  commit. All 61 documentation/integration/quality/release-note tests, Ruff, the
  repository-wide format check, Towncrier draft, and `git diff --check` pass.

#### Risks And Recovery

- GitHub schedule omitted the same-day release. Manual exact-tag dispatch after the harness
  fix is the recovery; do not add schedule frequency or duplicate runs.
- Hosted qualification can fail or create a machine issue without usable evidence. Keep the
  issue/run open, inspect bounded artifacts, correct only demonstrated harness/product faults,
  and never promote an unqualified release.
- An automatic compatibility PR may appear. Compare it against reviewed evidence, integrate
  only required bytes into this Draft, and close/supersede it truthfully without merging it.
- Local binary replacement can fail. Retain the verified 1.10.2 binary until 1.11.0 passes
  checksum/version/help/no-LLM checks and atomically restore it on mismatch.
- Provider reasoning or request controls could escape through an unowned field. Keep one
  canonical projection/DLP owner, fail closed at public/receipt boundaries, and test all sinks.
- Strict grouping parsing could accidentally imply old runtime support. Keep baseline parsing
  in qualification-only code and assert exact runtime rejection of 1.10.x.
- Hosted CI may expose a real defect. Fix only evidence-backed boundaries in a separately
  self-reviewed signed commit, then rerun the affected and final gates before pushing.

#### Resume Point

Commit the reviewed `WQ-04` OCR integration slice without pushing, then continue `WQ-05`
with the existing canonical projection/DLP/cleanup owners and focused provider-private
reasoning/tool-choice regressions.

#### Plan Fidelity Check

- [x] Every approved outcome has a stable requirement and queue owner.
- [x] Release-required classification, target 0.8.6, Draft-only deferred delivery, and
  explicit non-publication boundary are recorded.
- [x] Exact versions/hashes, old/new qualification distinction, runtime compatibility
  decision, data flows, DLP/reasoning/tool-choice rules, issue fix, local binary, docs,
  validation, recovery, and external handoff are preserved.
- [x] Initial/final push behavior, signed commit gates, and hosted ownership are explicit.
- [x] Resume point names the first safe unfinished action.

#### Reconciliation Check

- [x] Current main/tag/next version, worktree, plan, issues, PRs, milestones, workflow,
  local OCR, manifest, harness, README, backlog, and canonical docs were read.
- [x] Hosted OCR 1.11.0 issue/evidence and semantic source audit agree.
- [ ] Backlog, roadmap, strategy, public docs, changelog, issues, milestone, and Draft agree.
- [ ] Final local/hosted validation, head/tree, threads, remote ref, and worktree agree.

#### Closure Gate

- [ ] All in-scope requirements and queue items are done or justified out of scope.
- [ ] Every logical commit passed focused tests, self-review, boundary review, and
  `git diff --check`.
- [ ] Final quality, coverage, manifest, lock, Towncrier, Gitleaks, and diff gates are green.
- [ ] Hosted required Draft checks are green with no unresolved conversations.
- [ ] Draft body, issues, milestone, remote ref, exact head/tree, and clean worktree agree.

#### Post-Close Delivery

- This task deliberately stops at a green Draft PR. Merge, protected-main development
  publication, `release/v0.8.6`, stable publication, external artifact reconciliation,
  issue closure, and milestone closure require a later explicit owner continuation.

#### Handoff Notes

- Draft body must retain Added/Fixed/Changed/Unchanged sections, exact toolkit head/tree,
  OCR hashes and hosted evidence, strict old/new grouping comparison, local no-LLM checks,
  backlog disposition, and a safe external configured-environment qualification table.
- The external agent starts from exact Draft head and OCR 1.11.0. It may run 1.10.2 only
  as an isolated comparison and must not interpret that run as toolkit compatibility.
