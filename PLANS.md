# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Toolkit 0.8.7 — OCR 1.11.1, evidence integrity, and efficient built-in MCP

- **Status:** active
- **Plan Origin:** plan_mode_approved
- **Release classification:** release-required
- **Target stable version:** 0.8.7
- **Branch:** `codex/v0.8.7-ocr-1.11.1-evidence-trust`
- **Delivery boundary:** published stable toolkit 0.8.7 with independently verified registry,
  provenance, attestation, immutable Release, issue, milestone, and synchronized-main receipts.

#### Goal

Qualify and adopt exact OCR 1.11.1, repair evidence comparison integrity, prevent OCR
multi-round wording from becoming toolkit validation, make admitted evidence efficiently
searchable with an explicit completeness check, admit protected same-revision GitLab CI
outcomes as provider-neutral context, and complete the related documentation work without
weakening DLP, privacy, approval, or immutable-ref boundaries.

#### Requested Scope

- Restore OCR 1.11.1 qualification through #163 and complete dependency tracker #158.
- Fix #159 so bounded base/head admission cannot synthesize dependency deltas.
- Fix #162 so repeated OCR findings remain unverified reports unless current evidence proves
  them; preserve the default `medium` effort and private reasoning/session boundary.
- Implement #160 as two dedicated built-in MCP tools: bounded search and authoritative
  coverage evaluation, with a model-facing routing contract.
- Implement #161 using protected-target context-policy v3 and provider-neutral same-revision
  CI evidence.
- Complete #157 with stable PyPI, supported-Python, and license badges.
- Reconcile backlog, public contracts, test-evidence ownership, changelog, Draft PR, issue
  checklists, and milestone state.
- Incorporate merged maintenance PR #165 from protected `main` before final qualification so
  the reviewed tree uses the updated CI, CodeQL, TestPyPI, release, and provenance actions.
- Run one configured semantic qualification of the new MCP/context contracts and one final
  repository review with project rules; remediate validated findings before the final push.
- Merge the protected feature and release pull requests, publish stable 0.8.7, independently
  read back every external artifact, close tracking, and clean task-owned scratch state.

#### Requirement Traceability

| Requirement | Outcome | Work queue | Acceptance evidence |
| --- | --- | --- | --- |
| REQ-001 | OCR 1.11.1 qualification separates budget, threshold-crossing, and below-threshold grouping behavior | WQ-02, WQ-03 | hosted compatibility artifact, strict fixture tests |
| REQ-002 | Runtime accepts only exact OCR 1.11.1 and records verified hashes plus semantic audit | WQ-05 | manifest/evidence validation, preflight/docs tests, isolated local binary checks |
| REQ-003 | Base/head truncation cannot create synthetic add/remove deltas | WQ-04 | oversized unchanged Go and second lock fixture, add/delete/change and hostile-readback tests |
| REQ-004 | Multi-round survivor wording cannot become toolkit confirmation | WQ-05 | two-round controlled peer, public unverified status, approval/privacy tests |
| REQ-005 | OCR can efficiently discover admitted facts without arbitrary repository search | WQ-06 | `ocr_toolkit_evidence_search` schema, routing and installed-artifact tests |
| REQ-006 | OCR can distinguish authoritative absence from unknown scope | WQ-06 | `ocr_toolkit_evidence_coverage` joins, no-match and partial-coverage tests |
| REQ-007 | OCR receives deterministic, efficient instructions for summary/list/get/search/coverage/context tools | WQ-06 | tool descriptions, bootstrap decision table, controlled call-sequence qualification |
| REQ-008 | New tools have exact count-only receipt and GitLab-summary attribution without content leakage | WQ-06 | receipt v6, action receipt v2, reconciliation/DLP/approval tests |
| REQ-009 | Protected same-revision GitLab CI outcomes become bounded provider-neutral evidence only | WQ-07 | policy v3, stable API snapshot, store/MCP and negative provider tests |
| REQ-010 | Public docs, badges, backlog, roadmap, strategy, and changelog describe added, changed, removed, and unchanged contracts | WQ-08 | documentation contracts and Towncrier draft |
| REQ-011 | Final feature head includes protected-main PR #165 and passes configured semantic qualification plus project-rule OCR review | WQ-09, WQ-10 | exact base/head receipts, complete manifests, remediation and self-review |
| REQ-012 | Stable 0.8.7 is published and independently reconciled across every release surface | WQ-11, WQ-12 | feature/release PR receipts, registry bytes, provenance, attestations, tag, Release, installs, issue and milestone closure |

#### Explicit Non-Goals

- No support or runtime fallback for OCR 1.11.0 or older releases.
- No automatic cap, tool choice, model, or protocol inference from provider metadata.
- No arbitrary repository grep, model-loop network, second evidence/context store, second OCR
  pass, or new DDL/testcontainer parser for evidence search.
- No CI log, artifact, job URL, runner, user, raw identifier, provider payload, reasoning,
  prompt, tool arguments, or tool results in public output or receipts.
- No approval, suppression, lifecycle, or severity authority from remediation text, search
  results, coverage hints, CI outcomes, OCR survivor wording, or tool-call counts.
- No downstream consumer or shared-template integration.
- No public retention of sensitive external-system data, model-session data, private fixtures,
  credentials, or local environment details.

#### Constraints

- Preserve Python 3.12–3.14 and standard-library-only runtime code.
- Fixtures and public material remain private-safe. All untrusted values are bounded before
  normalization, persistence, search indexing, MCP response, and publication.
- Provider-specific acquisition remains at the GitLab edge; evidence/store/MCP/receipt and
  approval layers remain provider-neutral.
- Existing context policy v1/v2 remain valid without CI outcomes. This policy compatibility is
  separate from exact OCR runtime compatibility.
- The only mandatory model-time evidence call remains one successful summary. Search and
  coverage are conditional and must not create needless calls for small reviews.
- Every Python slice runs formatter before self-review and passes repository-wide format check.
- New runtime functions/classes and new tests receive purpose-focused docstrings.

#### Inputs And Sources

- Approved conversation plan and subsequent delivery reset: protected policy v3; include #157;
  add dedicated search and coverage MCP tools; preserve efficient OCR routing; complete stable
  delivery after configured exact-head validation.
- GitHub issues #157–#163 and OCR dependency tracker #158.
- OCR v1.11.1 release/source diff and compatibility workflow run `33391721404`.
- OCR v1.11.1 pins: Linux amd64
  `1cdc7d1f776f1cdb69850130b930e40f64accc86ecaf09600573b3600456322f`, Darwin arm64
  `5fdf72e51aae021ac7bf43d7b9dcb160f04880f623c66e8ada5e6ae5a92e172c`, checksum file
  `8760d31184c12f947c182fcb00114730707892524ddf1beac78fc415cb61b37b`.
- Canonical owners: `docs/engineering/project_principles.md`, `docs/development.md`,
  `docs/release.md`, `docs/configuration.md`, `docs/gitlab.md`, `docs/operations.md`,
  `docs/review-context.md`, `docs/security.md`, and `docs/codex/TASKS_BACKLOG.md`.

#### User Decisions And Answers

- Delivery continues from a green Draft through configured exact-head qualification and the
  complete protected stable-release lifecycle.
- CI outcome authority is owned only by protected-target policy v3.
- Documentation issue #157 is part of v0.8.7.
- Built-in MCP gains two separate tools rather than another union action.
- OCR must receive explicit routing guidance and qualification proving correct and efficient
  use; optional tools are not forced on every review.
- Current GitLab technical-summary format stays stable and emits only non-zero tool names.
- Full delivery includes publication, independent external readback, Actions-owned issue
  receipts, milestone closure, synchronized `main`, and cleanup; merge or green CI is not final.
- Final repository OCR review uses project rules, `medium` effort, concurrency one, OCR-owned
  completion limits, and max-tools sentinel zero. Confirmed findings are fixed before push and
  followed by deterministic validation plus a complete self-review.
- If a newer stable OCR appears before the final repository review, qualify and adopt it as the
  sole runtime when compatible. Freeze the qualified OCR version once that review begins.

#### Completed Baseline State

- Protected `main` contains released v0.8.6 plus verified maintenance squash #165 at
  `4fd4eda3fb10ff3ae7c40b099ab791ba4797c134`; its development publication and Scorecard pass.
  `.next-version` selects 0.8.7.
- Existing evidence store v4 exposes one built-in MCP with summary/list/get; context uses fixed
  context_list/context_get; receipt v5 reconciles count-only evidence usage.
- OCR 1.11.1 is the exact target runtime; the PATH-effective local binary still requires an
  atomic checksum-verified update before configured qualification.
- Workflow audit with engineering-workflow 0.9.0 found canonical files and navigation indexes;
  no target workflow migration is required.
- OCR v1.11.1 assets verify, while current qualification fails because its probes assume
  pre-1.11.1 small-change grouping behavior.

#### Current Work Queue

| Queue | Status | Work |
| --- | --- | --- |
| WQ-01 | done | Materialize plan, create milestone/issue relationships, planning commit, and fidelity check |
| WQ-02 | done | #163 harness committed; initial push and Draft PR #164 created |
| WQ-03 | done | Hosted run 33400677367 accepted exact OCR 1.11.1 structural evidence |
| WQ-04 | done | #159 suppresses unsafe deltas when either side was not admitted while preserving comparable pairs |
| WQ-05 | done | #162 guidance, exact OCR 1.11.1 pins/rules/evidence, and local binary are complete |
| WQ-06 | done | Implement #160 search/coverage tools, OCR routing, action receipt v2, and toolkit receipt v6 |
| WQ-07 | done | Implement #161 protected policy v3 and same-revision GitLab CI evidence |
| WQ-08 | done | Implement #157, public docs, backlog/strategy/roadmap, changelog, and final plan truth |
| WQ-09 | in_progress | Merge protected `main` #165 into the Draft branch, update maintenance notes, and revalidate the combined tree |
| WQ-10 | pending | Run configured semantic qualification and final project-rule OCR review; remediate findings and self-review before push |
| WQ-11 | pending | Push the final feature head, reconcile hosted checks, merge #164, and verify its development publication |
| WQ-12 | pending | Prepare and merge `Release v0.8.7`, publish stable artifacts, independently read back every release surface, close tracking, and clean scratch state |

#### Locked Decisions

- Search tool: NFKC/casefold query of 1–128 characters and at most eight tokens; no regex,
  wildcard, operators, controls, bidi/format characters, or broad empty search. Search only
  DLP-admitted source paths, identities, and per-kind allowlisted scalar values.
- Coverage tool: exact kind/ref plus optional exact component/path. Missing mappings and any
  incomplete scope yield unknown; `absence_authoritative` requires complete scope, zero
  matches, and no truncation.
- Routing: summary once, list for known kinds/deltas, search for unknown location/identity, get
  selected records, coverage only before a negative claim, context_list before context_get,
  and stop when evidence is sufficient. No forced `tool_choice`.
- Receipt v6 replaces v5 for current results. Private action receipt v2 counts exactly
  summary/list/get/search/coverage; exact OCR by-tool/capability/server reconciliation is
  required. Only closed numeric counts may reach Technical details.
- CI policy v3 uses `required` default false, `max_age_seconds` default 86400 with range
  60–604800, unique exact check names, and normalized protected path prefixes.
- OCR survivor state is an unverified report. Toolkit guidance mitigates but does not claim to
  rewrite upstream prompt semantics.

#### Verification

- Focused grouping, compatibility, evidence comparison/store/readback, MCP/routing, receipt,
  posting/approval/DLP, context-policy/provider, installed-artifact, documentation, and
  changelog tests as mapped to each queue item.
- Local no-LLM OCR 1.11.1 version/help, rules, confinement, and grouping/background previews in
  an isolated temporary HOME after checksum verification.
- Before each commit: `scripts/quality.sh format` for Python changes,
  `uv run --frozen ruff format --check .`, focused tests, full slice diff/trust review, and
  `git diff --check`.
- Once on final local head: `scripts/quality.sh check`, scoped coverage floors,
  `PYTHONPATH=src python scripts/ocr_compat.py validate`, lock/manifest checks, Towncrier draft,
  `scripts/gitleaks.sh`, and `git diff --check`.
- Hosted PR workflows own OS/Python matrix, packages, dependencies, Security, and CodeQL.
- External configured qualification owns real OCR 1.11.1 LLM behavior, multi-round correction,
  search/get and no-match/coverage routing, same-revision CI evidence, and leakage audit.
- Final repository OCR review owns the complete `v0.8.6..feature-head` diff with
  `examples/gitlab/rules.json`; it runs only after the protected-main merge and latest-stable OCR
  check. Full output remains ignored and owner-only.
- Stable closure requires byte equality across workflow artifact, TestPyPI, PyPI, and immutable
  GitHub Release; PEP 740 provenance; GitHub attestations; annotated tag target; receipt
  validation; Python 3.12-3.14 wheel/sdist installs; Actions-owned issue receipts; closed
  milestone; and clean `main == origin/main == v0.8.7^{}`.

#### Latest Validation Results

- 2026-08-31: clean branch created from remote `main` at
  `d98763fc1cb3c14079a4b79911be57c63c7f767b`.
- 2026-08-31: engineering-workflow 0.9.0 audit found all canonical workflow files and required
  navigation indexes; ignored `.quality-logs` were audit noise only.
- 2026-08-31: milestone `v0.8.7` created; #157–#163 assigned to `xeonvs`; dependency and
  production-slice boundaries recorded on #158, #160, and #161.
- 2026-08-31: `tests/test_ocr_compat.py` passed with 88 tests after repository formatting;
  `git diff --check` passed.
- 2026-08-31: checksum-verified temporary OCR 1.11.1 passed the full local no-LLM contract
  probe. Evidence separates local single-file, bundle-all, and high-churn per-file grouping
  from the four-file semantic grouping request; it also records two medium review rounds,
  filter-survivor wording, partial budget coverage 2/3, completion cap, and max-tools behavior.
- 2026-08-31: Draft PR #164 opened from the two reviewed initial commits. Hosted compatibility
  run `33400677367` passed on exact commit `ffe1233242eb1c102b1cf34306d0c106bad60806`;
  candidate #158 now records schema-v3 compatible evidence and a human-review-required semantic
  audit classification.
- 2026-08-31: #159 focused evidence/store/MCP suite passed with 197 tests. Generated Go and
  Composer lock fixtures prove byte-identical over-limit inputs publish no semantic delta;
  bounded one-sided and ordinary version changes remain available.
- 2026-08-31: exact local OCR 1.11.1 passed the extended no-LLM contract. Small-change and
  semantic grouping remain distinct; the mandatory re-check marker reached all three main
  requests; Pug, `.v`, `.vh`, `.sv`, `.vhd`, and `.vhdl` were selected with system rules while
  unqualified `.svh` remained excluded. The focused compatibility/runtime/docs suite passed
  with 291 tests and 104 subtests.
- 2026-08-31: #160 adds separate fixed literal-search and exact-coverage tools over the existing
  DLP-admitted store. Action receipt v2 and toolkit receipt v6 reconcile every tool separately;
  incomplete coverage cannot prove absence or support approval, and only non-zero reconciled
  counts reach Technical details. Ruff format/check, `git diff --check`, and the focused boundary,
  installed-artifact, documentation, receipt, publication, and approval suite passed with 621
  tests and 350 subtests. Self-review also corrected two current-contract references from receipt
  v5 to v6 without rewriting historical compatibility records.
- 2026-08-31: #161 adds protected policy v3, a bounded twice-read GitLab pipeline/job adapter,
  and one immutable provider-neutral `ci_outcome` projection through the existing store and MCP.
  Exact-head and protected path scope are mandatory; pagination, stale checks, duplicate retries,
  mutation, DLP mismatch, hostile persistence, and replay fail closed. Only count hints enter the
  bootstrap, while raw provider identities/payloads and CI status stay outside receipts, public
  summaries, and approval authority. Ruff format/check, `git diff --check`, and the focused
  policy/provider/store/MCP/review/publication suite passed with 350 tests and 83 subtests.
- 2026-08-31: #157 adds dynamic stable PyPI version, supported-Python, and Apache-2.0
  product badges ahead of the unchanged supply-chain/CI badges. Live Shields readback reported
  stable `v0.8.6`, Python `3.12 | 3.13 | 3.14`, and Apache-2.0; no TestPyPI or duplicate GitHub
  version badge was added. Current strategy, roadmap, M5 evidence matrix, and conditional
  forge/fuzzing backlog now include the policy-v3 CI-outcome boundary without rewriting release
  history or marking those future backlog items complete. Documentation tests passed 56 tests;
  Towncrier draft renders every v0.8.7 category once without duplicate issue links.
- 2026-08-31: the first exact-head quality run reached 86.18% combined coverage and exposed one
  stale cross-provider assertion that still expected the pre-#159 one-sided-delta diagnostic in
  the compact bootstrap. Production behavior and budgets were unchanged; the test continues to
  prove actual framework/template deltas, summary counts, MCP list/get projection, and bootstrap
  routing without requiring a removed diagnostic. Its focused owner suite passed 41 tests.
- 2026-08-31: the corrected exact-head local gate passed 1,367 tests plus 366 subtests at 86.18%
  combined branch coverage; the four risk groups passed at 85%, 82%, 86%, and 87%. Ruff format
  and lint, strict MyPy, Bandit, lock, OCR manifest/evidence, rendered Towncrier, and
  `git diff --check` passed. Repository-pinned Gitleaks 8.24.3 passed the complete first-parent
  branch history from `origin/main`; its official Darwin arm64 archive verified SHA-256
  `b90f13bb8c90ab72083d9b0c842e39dafb82c0e5c3f872f407366b7a58909013`, the temporary files
  were removed, and the global 8.30.1 installation was not changed.
- 2026-08-31: engineering-workflow 0.9.0 plan lifecycle check passed. Its value-free public-tree
  privacy scanner reported 339 established baseline matches and 346 on the final tree; the seven
  added match counts are limited to controlled OCR qualification probes, the new GitLab token
  parser owner, and explicit DLP/evidence test owners. No new hard-category appeared. This
  repository-owned synthetic/false-positive provenance agrees with the clean redacted Gitleaks
  history scan; no candidate value was opened or copied into the review.
- 2026-09-01: protected-main PR #165 was squash-merged as verified commit `4fd4eda`; its seven
  workflow-only pin changes have no path overlap or merge conflict with #164. Development run
  33482577560 and Scorecard run 33482577475 completed successfully on that exact commit.

#### Risks And Recovery

- If hosted OCR qualification still fails, do not promote OCR pins; update #158 with the closed
  failed subprobe/counts and keep WQ-03 blocked.
- If pair-aware comparison cannot prove source completeness, degrade to unknown rather than
  emit a one-sided delta.
- If search cannot map a value safely, omit it from the index. If coverage applicability is
  ambiguous, return unknown and prohibit an absence claim.
- If MCP counts do not reconcile, receipt v6 is invalid and auto-approval remains blocked;
  never coerce a new tool into a legacy action count.
- If GitLab CI snapshot mutates, paginates beyond bounds, or has ambiguous retries, admit no
  trusted outcome and apply required/optional degradation policy.
- If local OCR replacement validation fails, restore the verified previous binary and keep the
  runtime pin work blocked; never modify OCR config, credentials, or user HOME.
- Evidence-backed CI fixes use a new logical commit after the same focused tests and review.

#### Resume Point

Merge protected `origin/main` at `4fd4eda` into the local #164 branch without pushing, validate
the combined trusted workflow/runtime tree, atomically update OCR, and run the two configured OCR
gates. Push only after validated findings are remediated and the final self-review is complete.

#### Plan Fidelity Check

- [x] Every approved outcome has a stable requirement ID and queue owner.
- [x] Stable-release boundary, exact OCR target, checksums, and external qualification are explicit.
- [x] Data-flow, DLP, provider-neutral ownership, approval, and failure semantics are explicit.
- [x] Rejected alternatives and non-goals prevent compatibility fallbacks and extra infrastructure.
- [x] Validation maps production owners, installed boundaries, hosted ownership, and local limits.
- [x] Resume point names the first safe unfinished action.

#### Reconciliation Check

- [x] Live `main`, released v0.8.6, `.next-version`, open issues, local OCR, and workflow owners
  were inspected before implementation.
- [x] No pre-existing user changes are present in the worktree.
- [x] Milestone and issue relationships agree with this plan.
- [ ] Draft PR, protected-main #165, and compatibility artifact agree with this plan.
- [x] Final implementation, docs, changelog, backlog, and local tests agree.
- [ ] Remote Draft head, hosted checks, and compatibility artifact agree.

#### Closure Gate

- [ ] All REQ and WQ items are done or explicitly out of scope.
- [ ] Final local and hosted checks are current for the exact Draft head.
- [ ] Feature and release PR exact heads pass their owned checks and have no unresolved threads.
- [ ] Configured qualification and project-rule review have complete exact-head receipts.
- [ ] Stable publication and independent readback satisfy every external closure invariant.
- [ ] #157-#163 and any added release tracker are closed by Actions receipts; milestone is closed.
- [ ] Task-owned scratch state is removed and local/remote `main` equals the peeled stable tag.

#### Stable Delivery

The feature PR becomes Ready only after the combined exact head passes configured qualification,
project-rule review, remediation, self-review, and hosted checks. Its verified squash merge is
followed by development publication readback and a separate protected `Release v0.8.7` PR. The
release merge authorizes stable publication; independent registry/Release/provenance/install and
tracking readback completes delivery without another repository PR.

#### Handoff Notes

- Do not repeat local development or qualify OCR 1.11.0 as a supported runtime.
- OCR v1.11.0 may appear only as historical comparison evidence.
- Do not publish external qualification prompts, reasoning, tool arguments/results, provider
  bodies, session files, credentials, or private fixture content.
- Keep #157-#163 and milestone `v0.8.7` open until the protected stable workflow records its
  Actions-owned receipts. PR #165 is included maintenance history, not a release-closure issue.
