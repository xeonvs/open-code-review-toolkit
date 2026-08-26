# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Toolkit 0.8.4 - GitLab summary correctness and OCR 1.10.1

#### Goal

Deliver toolkit `0.8.4` through the complete protected stable-release lifecycle:
finish and independently review the existing Draft feature PR, run one final
local OCR `1.10.1` review, correct confirmed findings, merge the exact hosted-
green feature head, prepare and merge `release/v0.8.4`, and independently
reconcile the published artifacts, provenance, immutable receipt, issues, and
milestone.

#### Plan Origin

`plan_mode_approved`

#### Requested Scope

- Resolve #145 by separating four GitLab summary inputs: OCR coverage,
  publication integrity, ordinary findings/warnings, and a toolkit-owned OCR
  core advisory.
- Resolve #146 by recording hosted qualification evidence for OCR `1.10.1`,
  promoting the exact version and checksums, documenting relevant upstream
  behavior, and updating the direct local OCR binary without changing user
  configuration.
- Permit HTAB only in published `existing_code` and `suggestion_code` values
  while preserving all remaining publication-DLP checks.
- Avoid duplicating one published finding in `Recommended focus areas` while
  preserving the deterministic ranking for two or more findings.
- Preserve the current tool-call and token technical-summary format and emit
  those independent non-empty metrics under passed, private-sanitized, and
  publication-filtered states.
- Finish with verified stable `0.8.4` artifacts and provenance, Actions-owned
  receipts on #145/#146, both issues closed, milestone `v0.8.4` closed, and a
  clean local `main` synchronized with `origin/main`.

#### Requirement Traceability

| Requirement | Owner | Implementation evidence | Acceptance evidence |
| --- | --- | --- | --- |
| OCR 1.10.1 compatibility and local update | #146 | compatibility evidence, manifest/preflight/example pins, current-version docs, Rules and Maintenance changelog fragments | hosted run `32955196785`, exact checksum validation, isolated no-LLM version/help/background/rule checks |
| Closed OCR advisory | #145 | strict private `ocr.toolkit-advisory/v1` parser/projection and Technical details renderer | spoof/malformed/duplicate/extra-key/no-receipt and approval-independence regressions |
| Correct publication-filtered coverage | #145 | derive original coverage from validated receipt v5 `publication.original`; keep publication integrity separate | complete 5/5 filtering, real partial/budget, no pathless fallback regressions |
| Field-bounded HTAB support | #145 | allow HTAB only for `existing_code` and `suggestion_code` through private and public publication DLP | tab preservation plus secrets/PII/laundering/control-character regressions |
| Non-duplicating reviewer guide | #145 | omit focus-area ranking for one published finding | one- and two-finding renderer regressions |
| Operational handoff | #145, #146 | Draft body and issue checklists with exact head/tree, checksums, validation, Added/Fixed/Changed/Unchanged | hosted-green Draft status, clean merge state, zero unresolved threads, remote/worktree readback |

#### Explicit Non-Goals

- No additional OCR qualification campaign or enriched-context qualification;
  run only the user-authorized final local OCR review on this repository.
- No receipt v5, publication-DLP signal v2, result, manifest, telemetry, or
  approval-contract version changes.
- No weakening of global context DLP or publication controls outside the two
  exact code-value fields.
- No adoption of upstream GitHub Action, delegate skill, npm launcher,
  provider preset, or upstream repository-local `providers.go` rule.
- No mechanical test-directory reorganization or refactor unrelated to the
  two activated issues.
- No consumer-repository, B2B, `core/common`, or shared-template integration.
- No issue or milestone closure before independent stable-release readback.

#### Constraints

- Release classification: `release-required`; target stable version: `0.8.4`;
  delivery state: `active stable delivery`.
- Branch: `codex/v0.8.4-summary-ocr-1.10.1`, based on clean released `v0.8.3`
  `main`; `.next-version` already owns `0.8.4`.
- The first tracked repository write is this complete active plan.
- After the signed planning commit, make one initial push and open the Draft PR;
  make no further pushes until all local implementation slices are complete.
- Every logical signed commit requires focused tests, complete slice diff
  self-review, trust/data-flow review, and `git diff --check`.
- New tests stay with existing thematic owners and include docstrings.
- Do not change OCR configuration, credentials, or the user's `HOME`.
- The final local OCR review uses the already configured local OCR `1.10.1`,
  concurrency `2`, no provider-specific `4096` completion cap, and private
  ignored artifacts. Its exit status is insufficient without complete result
  and manifest readback.
- Keep long-running test and OCR output in ignored owner-only logs and expose
  only bounded summaries in the interactive session.
- Run the full local gate after the final fixes; hosted workflows own the
  cross-platform, dependency, Security, and CodeQL validation, while local
  release closure additionally owns deterministic package and clean-install
  evidence.

#### Inputs And Sources

- GitHub issues #145 and #146 and compatibility run `32955196785`.
- OCR `1.10.1` release assets and checksums:
  - Linux amd64: `8b806c221d409727a21611b4a7952d8e15edadbbc25f5affccaeb8f677e4055c`.
  - Darwin arm64: `8fc24bd825c9d918b894be05c0cf27fac8d30bc549257c812d87337167c7563c`.
  - `sha256sum.txt`: `ec72bda51f1227f412ee00602d952868efc57d847cce0ae1586fb97069d4139d`.
- Current public contracts in `docs/configuration.md`, `docs/gitlab.md`,
  `docs/operations.md`, `docs/security.md`, and `docs/compatibility.md`.
- Runtime owners under `src/ocr_toolkit/` and their existing thematic tests.

#### User Decisions And Answers

- Complete and publish stable toolkit `0.8.4` in this task.
- Run one final local OCR `1.10.1` review, correct confirmed findings, perform a
  holistic self-review, then push and move the exact Draft head through the
  protected release process.
- Preserve the existing technical-summary format and publish tool-call/token
  numeric metrics only when their list/value is non-empty and non-zero.
- Default `OCR_REVIEW_EFFORT` remains `medium`.
- Highlight required environment variables in public documentation where
  applicable.
- Avoid duplicate local validation already owned by hosted PR workflows.

#### Completed Baseline State

- `main` and `origin/main` both resolve to released `v0.8.3` commit
  `4c697fee6eeceb02a50fbed1c150a6eb953a08d6` with a clean worktree.
- `.next-version` contains `0.8.4`; `.release-version` contains `0.8.3`.
- Hosted OCR compatibility run `32955196785` passed the required result,
  completion-cap, medium-effort, and max-tools probes for `1.10.1`.
- The direct local OCR binary is `1.10.0`; no Homebrew-managed OCR package is
  installed.
- Upstream semantic audit identified bounded session cache keys and `.m`
  MATLAB/Objective-C rule resolution as consumed behavior; result/manifest,
  completion cap `16384`, explicit cap `4096`, medium effort, and max-tools
  semantics remain unchanged.

#### Current Work Queue

1. **Plan and Draft coordination - completed**
   - Create milestone `v0.8.4`, assign #145/#146 to `xeonvs`, add both issues to
     the milestone, commit this plan, push once, and open the Draft PR.
2. **OCR 1.10.1 qualification - completed locally**
   - Import canonical evidence, human conclusion, manifest/preflight/example
     pins, current-version docs, and separate Maintenance/Rules fragments.
   - Atomically update the direct local binary with checksum verification and
     rollback on validation failure; run isolated no-LLM checks.
3. **Closed advisory contract - completed locally**
   - Remove the accepted background advisory from OCR warnings; validate and
     attach a private toolkit-owned numeric advisory after publication DLP;
     render it only with a valid receipt in Technical details.
4. **Coverage, publication DLP, and reviewer guide - completed locally**
   - Use `publication.original` for filtered coverage; suppress the legacy
     warning fallback in filtered state; correct DLP wording; permit HTAB only
     in the two code fields; omit focus areas for one finding.
5. **Independent feature review and final OCR - active**
   - Review the complete Draft diff and trust/data flows, run focused and full
     validation with bounded output, then execute the single final local OCR
     `1.10.1` review with concurrency `2`.
   - Inspect the OCR result and manifest for complete selected-item coverage;
     trace and fix only confirmed findings, rerun their owner tests, and record
     the private-safe conclusions without publishing raw provider artifacts.
   - The final exact-range run completed all 10 selected items at
     `02c2f9d8f76d736ba83deed7700bed9374c4e38d` with no failed, reused, or
     waived coverage and produced three confirmed boundary corrections: make
     receipt-v5 original outcome/count validation exhaustive; preserve the
     original HTAB-bearing code value for secret and forbidden matching while
     relaxing only its control-character admission; and carry a valid
     receipt-bound OCR core advisory into failed-result Technical details.
6. **Holistic self-review and feature delivery**
   - Review the complete post-OCR diff, correct findings, run the final
     quality/coverage, lock, manifest, Towncrier, Gitleaks, deterministic-build,
     clean-install, and diff gates, then push the exact reviewed head.
   - Verify hosted checks and unresolved threads on that head, move #147 to
     Ready, and squash-merge it through the protected branch policy.
7. **Release PR and stable publication**
   - Verify the protected-main development publication, prepare
     `release/v0.8.4` with the canonical release metadata, changelog, issue set,
     and plan archive, then validate and squash-merge the exact release head.
   - Monitor the Release workflow and independently verify TestPyPI/PyPI/GitHub
     bytes, PEP 740 provenance, GitHub attestations, annotated tag target,
     immutable Release, receipt identities, and clean Python 3.12-3.14 installs.
8. **External closure**
   - Verify Actions-owned receipts, close #145/#146 and milestone `v0.8.4` only
     after external reconciliation, re-read planning sources, synchronize clean
     local `main`, and remove temporary logs, archives, and unused environments.

#### Locked Decisions

- Data flow for the advisory is
  `exact preview stderr -> strict parser -> numeric toolkit state -> closed renderer -> Technical details`.
- The accepted advisory is not an OCR warning, DLP input, coverage signal,
  receipt input, telemetry field, or approval signal.
- Raw OCR output may not supply the reserved `_ocr_toolkit_advisory` key.
- Advisory schema is exact `ocr.toolkit-advisory/v1` with kind
  `background_recommended_limit`, bounded positive non-boolean `actual` and
  `recommended`, `actual > recommended`, and unit `characters`.
- Without a valid receipt v5 the advisory is untrusted; malformed, extended,
  duplicated, or spoofed forms fail closed.
- Complete OCR coverage plus publication filtering renders
  `Review complete with publication filtering`; real failed/budget/partial
  coverage retains its existing higher-priority state.
- Publication filtering always blocks auto-approval; a valid advisory alone
  does not.
- HTAB is allowed only in values of `comments[*].existing_code` and
  `comments[*].suggestion_code`; all secret, PII, forbidden-value, laundering,
  budget, and other control-character checks remain active.
- OCR `1.10.1` promotion is Maintenance; MATLAB/Objective-C rule effects are a
  separate Rules entry. Historical `1.10.0` records remain immutable.

#### Verification

- Per slice: focused owner tests, complete diff review, requirement and
  trust/data-flow review, `git diff --check`, signed commit.
- OCR checks: compatibility evidence/manifest validation, exact checksum and
  documentation consistency, isolated `--version`/`--help`, soft/hard
  background preview, and MATLAB/Objective-C rule resolution without LLM.
- #145 regression matrix: both reported scenarios; advisory spoof/malformed/
  duplicate/extra-key/no-receipt; approval independence; complete filtered and
  actual partial/budget coverage; field-specific HTAB and remaining DLP
  controls; one/two finding guide; tool-call/token summaries across publication
  states.
- One final local gate: `scripts/quality.sh check`, coverage floors,
  `uv lock --check`, `scripts/ocr_compat.py validate`, Towncrier draft,
  `scripts/gitleaks.sh`, and `git diff --check`.
- Hosted Draft PR: build artifacts, Twine, clean installs, OS/Python matrix,
  dependency checks, Security, and CodeQL.

#### Latest Validation Results

- Baseline branch/worktree check: clean `main` at
  `4c697fee6eeceb02a50fbed1c150a6eb953a08d6`.
- Hosted OCR compatibility run `32955196785`: successful.
- OCR `1.10.1` compatibility slice: 146 focused tests passed; support manifest
  and Towncrier draft validated.
- The direct local Darwin arm64 binary now reports OCR `1.10.1` and matches
  SHA-256 `8fc24bd825c9d918b894be05c0cf27fac8d30bc549257c812d87337167c7563c`;
  upstream `sha256sum.txt` matches
  `ec72bda51f1227f412ee00602d952868efc57d847cce0ae1586fb97069d4139d`.
- Isolated no-LLM version/help, hosted/local contract, soft/hard background,
  and MATLAB/Objective-C rule-resolution checks passed without changing user
  configuration or `HOME`.
- Closed advisory slice: 360 focused tests and Ruff passed. Raw/duplicate/
  malformed/unbound advisory input fails closed; the valid numeric projection
  remains outside OCR warnings, publication DLP, coverage, receipt v5,
  telemetry, and approval inputs and renders only in Technical details.
- Coverage/publication slice: 342 focused tests and 209 subtests passed. The
  complete 5/5 filtered scenario retains its original coverage counts without
  legacy pathless failures; real partial/budget state remains stronger;
  passed/private-sanitized/publication-filtered tool and token lines remain
  independent; field-specific HTAB, hostile controls and remaining DLP checks,
  one/two-finding guide behavior, and impossible receipt counts are covered.
- Final quality gate passed: Ruff format/lint, mypy, Bandit, and the complete
  pytest run produced 86% combined coverage. Risk groups passed at 85%
  (result/preflight), 82% (posting/GitLab transaction), 86%
  (review/context/DLP/approval), and 87% (MCP/provider/policy/result).
- `uv lock --check`, OCR support-manifest validation, Towncrier 0.8.4 draft,
  and `git diff --check` passed. The rendered draft has separate Bug Fixes
  (#145), Maintenance (#146), and Rules (#146) sections with explicit
  deployment and unchanged-contract guidance.
- The original product implementation and all three final-OCR corrections are
  complete locally. Focused posting/review regressions pass 343 tests plus 217
  subtests; shared DLP callers pass 66 tests plus 8 subtests; Ruff and strict
  MyPy pass. The release remains active pending the final holistic gates, push,
  hosted CI reconciliation, Draft transition, and protected release lifecycle.
- The single authorized final local OCR `1.10.1` review completed the exact
  `origin/main..02c2f9d8f76d736ba83deed7700bed9374c4e38d` range in 6m23s with
  concurrency `2`, complete 10/10 coverage, no failed/reused/waived items,
  no stderr, and 102 tool calls. Its three candidates were all confirmed as
  bounded correctness or trust-boundary defects and are the active corrective
  scope above; the retained private result and DLP sidecar remain local-only
  remediation evidence and will be deleted after verification.
- Final holistic gates passed after the corrective slice: Gitleaks 8.24.3
  scanned the complete `origin/main..HEAD` feature range; `pip-audit
  --skip-editable` found no known dependency vulnerabilities; the focused
  public-contract suite passed 25 tests; and `git diff --check` passed.
- Two independent local `0.8.4` builds with one fixed source epoch were
  byte-identical. Twine accepted both wheel/sdist pairs, archive inspection
  found no private/log/Git/environment/key paths, and clean wheel plus sdist
  installations passed `ocr-ci --help` on Python 3.12, 3.13, and 3.14.
- Holistic documentation review replaced the remaining obsolete
  tab-normalized-copy wording with the implemented unchanged-value DLP
  contract. Required variables remain bold in the canonical tables, and the
  example toolkit pin correctly stays at the currently published `0.8.3`
  until the release PR advances it.

#### Risks And Recovery

- **Advisory spoofing or privilege confusion:** reject reserved input before
  toolkit projection; exact-schema validation and receipt-gated rendering fail
  closed. Revert the advisory slice if the boundary cannot be proven.
- **Coverage conflation:** use only already-validated receipt v5 original counts
  for filtered publication; preserve real partial/budget outcomes. Revert the
  summary slice if legacy result compatibility regresses.
- **DLP weakening:** make the allowance field-aware and tab-only; retain every
  semantic scanner. Any secret/PII/control regression blocks the commit.
- **Local OCR replacement:** verify release checksum and existing source binary,
  stage an adjacent replacement atomically, retain a rollback copy until all
  no-LLM checks pass, and restore `1.10.0` on failure.
- **Hosted-only failure:** diagnose from exact job evidence, make a focused
  reviewed fix commit, rerun the affected local owner check, and push only the
  evidence-driven correction.

#### Resume Point

Current action: sign and push the complete post-OCR corrective head, verify the
hosted checks and review threads on that exact head, then move Draft PR #147 to
Ready and squash-merge it through the protected branch policy.

#### Plan Fidelity Check

- The active queue maps every accepted requirement to #145 or #146 and retains
  all approved trust, DLP, approval, compatibility, and release boundaries.
- No requested product behavior is deferred silently; stable publication alone
  is intentionally deferred.
- Scope additions require an explicit plan update before implementation.

#### Reconciliation Check

- Before final push, compare implementation, tests, docs, changelog, manifest,
  examples, and issue acceptance criteria against this plan.
- After hosted CI, verify the exact remote head/tree, all required checks,
  unresolved review threads, Draft state, merge state, and local cleanliness.

#### Closure Gate

This objective is complete only when the exact protected release is externally
reconciled: registry and Release bytes agree, provenance and attestations
validate, the annotated tag and immutable receipt bind the reviewed release,
Python 3.12-3.14 clean installs pass, Actions-owned issue receipts exist,
#145/#146 and milestone `v0.8.4` are closed, and local `main` is clean and
synchronized. Earlier feature, merge, development-publication, or workflow-green
states are intermediate only.

#### Post-Close Delivery

No post-close repository delivery remains in this objective. Conditional backlog
work stays inactive unless its own trigger and authorization are met.

#### Handoff Notes

- Draft PR #147 may move to Ready only after the final OCR fixes, holistic
  self-review, exact-head local gates, push, and hosted reconciliation.
- #145, #146, and milestone `v0.8.4` remain open until the stable receipt and
  independent external readback prove closure.
- OCR `1.10.1` is the qualified toolkit target; the previous `1.10.0` evidence
  remains historical and must not be rewritten.
