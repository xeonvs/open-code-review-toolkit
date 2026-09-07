# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Toolkit 0.9.1 — OCR 1.11.4 and 1.11.5

- **Status:** active; qualification, remediation and security review complete; final push pending
- **Plan Origin:** plan_mode_approved
- **Release classification:** release-required; stable delivery authorized
- **Target stable version:** 0.9.1
- **Branch:** `codex/v0.9.1-ocr-1.11.5`

#### Goal

Integrate OCR 1.11.4 and 1.11.5 through a reviewed protected PR and complete the
0.9.1 stable release, with exact 1.11.5 runtime support and precise diagnostic/DLP
boundaries that preserve GitLab summary publication. Remediate the configured model
qualification findings before feature merge and independently verify every published
artifact, receipt and tracked issue before closure.

#### Requested Scope

- Qualify #176 and #177 separately; retain adjacent semantic audits and evidence.
- Accept bounded private failure arguments without exposing them or degrading publication.
- Qualify serialized comment repair, Objective-C++ routing, grouped review and defaults.
- Update local OCR to checksum-verified 1.11.5, current docs, examples and changelog.
- Remediate the completed model-backed OCR findings without discarding its owner-only
  evidence, then run the holistic quality and Codex Security gates.
- Publish only the completed feature head, finish the protected feature and release PRs,
  verify stable delivery, close #176/#177 and milestone `v0.9.1`, clean branches and
  synchronize `main`.
- Complete the required no-release external-reconciliation PR without producing another
  stable release.

#### Requirement Traceability

| Requirement | Outcome | Queue | Verification |
| --- | --- | --- | --- |
| REQ-001 | Exact OCR 1.11.5 with separate predecessor evidence | WQ-02, WQ-04 | assets, adjacent audits, real binary probes |
| REQ-002 | Bounded arguments never reach normalized/public diagnostics | WQ-03 | hostile parser and production projection tests |
| REQ-003 | Private arguments cannot change summary or publication DLP | WQ-03 | paired result/publication/summary regressions |
| REQ-004 | Comment repair and Objective-C++ routing are qualified | WQ-04 | deterministic real OCR gateway and rules previews |
| REQ-005 | Grouping, defaults, MCP and receipt boundaries remain correct | WQ-04 | compatibility and runtime tests |
| REQ-006 | Docs, decision flow, changelog and backlog reflect current behavior | WQ-05 | documentation checks and rendered Towncrier |
| REQ-007 | Green protected feature PR with truthful model qualification | WQ-06, WQ-08 | local/hosted gates, OCR receipt and remote readback |
| REQ-008 | Forward-only live qualification, isolated historical readback and stable tests | WQ-04R | no live version branches, frozen-history validation, CLI and probe regressions |
| REQ-009 | Version-neutral current guidance with exact compatibility identities preserved | WQ-07 | documentation contracts, pin validation, self-review and green Draft push |
| REQ-010 | Malformed probe output always fails through the closed qualification status path | WQ-08 | focused shape matrix and CLI status-output regression |
| REQ-011 | Stable 0.9.1 is published and independently reconciled | WQ-09, WQ-10 | release workflow, registry/provenance/install readback and protected closure PR |

#### Explicit Non-Goals

No GitLab posting, GitLab MR, new environment variables, MCP tools, receipt schemas,
upstream repair implementation, runtime compatibility fallback, or unrelated B2B,
`core/common` or shared-template work. Do not expose OCR configuration, credentials,
raw private output or owner-only evidence. Do not repeat the completed model-backed
OCR run without separate authorization; remediation is verified with deterministic
tests and the required Codex Security diff scan.

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

Stable delivery is authorized through final reconciliation. The configured model-backed
review has completed without GitLab posting and owns the two parser-hardening findings
below. Local OCR is 1.11.5; all deterministic binary checks use isolated HOME.
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
| WQ-05 | done | Public docs, decision flow, changelog and backlog reconciliation |
| WQ-06 | in_progress | Final reconciliation commit, exact-head push and hosted checks |
| WQ-07 | done | Version-neutral guidance and generic fixtures validated and self-reviewed; Draft push/readback remains owned by WQ-06 |
| WQ-08 | done | Malformed-output and hostile language-preview remediation, regressions and Codex Security complete |
| WQ-09 | pending | Push completed feature head, make PR ready, verify checks/threads, squash-merge and verify development publication |
| WQ-10 | pending | Prepare/merge `Release v0.9.1`, verify stable delivery and close issues/milestone; then no-release external reconciliation and cleanup |

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
- Follow-up documentation maintenance is `no-release` within this deferred release
  branch. Current guidance links to the compatibility manifest instead of repeating
  OCR release numbers or asset hashes. Preserve executable pins, exact identity
  checks, historical evidence, release notes and this release-specific plan.
  No runtime behavior, supported-version policy or release authorization changes.

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
- 2026-09-06: final quality gate passed 1524 tests and 408 subtests at 86.39%
  combined coverage; risk groups passed at 85/82/86/88%. Ruff format/lint, MyPy,
  Bandit, lock, manifest/evidence, Towncrier and plan lifecycle checks passed.
  Pinned Gitleaks 8.24.3 passed full feature history and current tree. Value-free
  privacy comparison against main found only two added email matches in the
  intentional private/public PII regression fixtures; no new hard-category finding.
  Aggregate self-review confirmed unchanged publication/summary/DLP authority,
  isolated historical readback and forward-only current qualification.
- 2026-09-06: version-neutral follow-up passed 1525 tests and 408 subtests at
  86.39% combined coverage, all scoped floors, Ruff, MyPy and Bandit. Focused
  documentation/environment/integration tests passed 48 tests; manifest, lock,
  Towncrier and diff checks passed. Self-review removed the remaining duplicated
  documentation checksum and separated manifest-reference assertions from exact
  executable-pin assertions. Runtime, pins and historical evidence are unchanged.
- 2026-09-07: configured model-backed OCR 1.11.5 completed on immutable range
  `ae0a9ac..029cdf0`: 9/9 selected items completed, 0 failed/reused/waived,
  77 tool calls and no GitLab posting. Owner-only result SHA-256 is
  `3a5374a846c3033734da0c66d7a9032e54043e96b8a8322fd9724f37691c2873`.
  The retained evidence is under `/tmp/ocr-v091-plan.1B3JOS` with mode 0700/0600.
  Two medium findings identify uncontrolled `JSONDecodeError` and non-object
  payload/detail shapes in `_comment_arguments_probe`; both must become controlled
  contract-probe failures and preserve a safe `--status-output` result.
- 2026-09-07: `_comment_arguments_probe` now rejects malformed JSON, non-object
  top-level values, non-object comments, invalid `tool_calls`/`failure_details` and
  non-object detail entries through `CompatibilityError`. Sixteen focused cases pass,
  including the complete qualification CLI path to a private stderr diagnostic and
  closed `contracts/contract-probe-failed` status without traceback or evidence output.
- 2026-09-07: holistic repository-script MyPy and trust-flow review found that a
  selected language-preview entry with a non-string `path` could reach mixed-type set
  sorting and raise `TypeError`. Explicit selected-path validation now rejects hostile
  `null`/numeric values through `CompatibilityError`. Seven focused preview tests,
  repository-script MyPy, Ruff and diff checks pass; self-review found no remaining
  uncontrolled path in this slice.
- 2026-09-07: Codex Security scan `5db2da0c-3f84-46a4-b4dd-cf3521fd1402`
  completed the security-relevant feature range `ae0a9ac..57f5236` with 7/7
  surfaces closed and no reportable findings. Incremental scan
  `90628f3c-10aa-4ce9-a3fa-b8c497e504d4` then covered the final
  `57f5236..ecd7ecb` remediation commit, closed its sole runtime surface and found
  no reportable issue. Both scans produced sealed reports and SARIF; the TAC status
  was unavailable because its connector was not configured and did not gate review.
- 2026-09-07: final completed-head gate passed 1537 tests and 408 subtests at
  86.40% combined coverage; risk groups passed at 85/82/86/88%. Ruff, runtime
  MyPy, Bandit, lock, manifest/evidence validation, rendered 0.9.1 Towncrier,
  diff checks and pinned Gitleaks 8.24.3 passed.

#### Risks And Recovery

Restore the old verified local binary if replacement validation fails. Failed probes
block promotion; retain their bounded evidence and classify the failing owner.
Never weaken summary/DLP/receipt gates to obtain green checks. Evidence-driven CI
fixes receive the same self-review and commit gates. Preserve temporary private
outputs until verification, then remove only task-owned files.

#### Resume Point

Preserve the existing OCR evidence. Reconcile the current manifest and plan with the
completed model qualification and two complementary Codex Security scans, run the
final scoped/full local gates, commit the truthful state, then push only the finished
head and complete WQ-09/WQ-10 through protected PR and release workflows.

#### Plan Fidelity Check

- [x] Requirements, sources, constraints and user decisions are preserved.
- [x] Every requirement maps to an ordered queue and verification owner.
- [x] Data/privacy boundaries, recovery and exact next action are explicit.

#### Reconciliation Check

- [x] Baseline and workflow owners verified.
- [ ] Code, tests, public docs, issues and Draft agree.
- [ ] Local/remote head and current hosted checks agree.

#### Closure Gate

- [ ] Implementation, OCR remediation, Codex Security and local/hosted checks complete.
- [ ] Feature and release PR exact heads merged through the protected process.
- [ ] TestPyPI/PyPI bytes, provenance, attestations, tag, immutable Release and installs verified.
- [ ] #176/#177 and milestone closed from exact receipts; branches cleaned and `main` synchronized.
- [ ] No-release reconciliation PR merged without changing stable artifacts.

#### Post-Close Delivery

The configured review is complete. Publish only bounded structural evidence, hashes
and pass/fail state in PR/issue receipts. After remediation, follow `docs/release.md`
for feature merge, development artifact verification, release PR, stable publication,
independent readback, issue/milestone closure and the separate no-release reconciliation.

#### Handoff Notes

Do not require intermediate OCR installation. Keep 1.11.4 audit distinct from final
1.11.5 support. Update issue checkboxes only for proven criteria. Stable release
remains deferred and the active plan remains available until later release closure.
