# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Toolkit 0.8.4 - GitLab summary correctness and OCR 1.10.1

#### Goal

Deliver a fully implemented, locally validated, hosted-green Draft feature PR for
toolkit `0.8.4` that fixes GitLab review-summary ownership boundaries and
qualifies OCR `1.10.1`. The stable release remains deferred: this work does not
merge the feature PR, create `release/v0.8.4`, tag, or publish artifacts.

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
- Finish with an open Draft PR, open #145/#146, and open milestone `v0.8.4`.

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

- No real LLM or provider calls.
- No receipt v5, publication-DLP signal v2, result, manifest, telemetry, or
  approval-contract version changes.
- No weakening of global context DLP or publication controls outside the two
  exact code-value fields.
- No adoption of upstream GitHub Action, delegate skill, npm launcher,
  provider preset, or upstream repository-local `providers.go` rule.
- No mechanical test-directory reorganization or refactor unrelated to the
  two activated issues.
- No Ready transition, merge, release branch, tag, registry publication,
  issue closure, or milestone closure.

#### Constraints

- Release classification: `release-required`; target stable version: `0.8.4`;
  delivery state: `release-deferred`.
- Branch: `codex/v0.8.4-summary-ocr-1.10.1`, based on clean released `v0.8.3`
  `main`; `.next-version` already owns `0.8.4`.
- The first tracked repository write is this complete active plan.
- After the signed planning commit, make one initial push and open the Draft PR;
  make no further pushes until all local implementation slices are complete.
- Every logical signed commit requires focused tests, complete slice diff
  self-review, trust/data-flow review, and `git diff --check`.
- New tests stay with existing thematic owners and include docstrings.
- Do not change OCR configuration, credentials, or the user's `HOME`.
- Local OCR checks use an isolated temporary `HOME` and never invoke an LLM.
- Run the full local gate once at the end; hosted workflows own package,
  cross-platform, dependency, Security, and CodeQL validation.

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

- Keep the PR Draft after the final push; do not release `0.8.4` yet.
- Update the direct local OCR binary to `1.10.1` but skip local LLM execution.
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

1. **Plan and Draft coordination**
   - Create milestone `v0.8.4`, assign #145/#146 to `xeonvs`, add both issues to
     the milestone, commit this plan, push once, and open the Draft PR.
2. **OCR 1.10.1 qualification**
   - Import canonical evidence, human conclusion, manifest/preflight/example
     pins, current-version docs, and separate Maintenance/Rules fragments.
   - Atomically update the direct local binary with checksum verification and
     rollback on validation failure; run isolated no-LLM checks.
3. **Closed advisory contract**
   - Remove the accepted background advisory from OCR warnings; validate and
     attach a private toolkit-owned numeric advisory after publication DLP;
     render it only with a valid receipt in Technical details.
4. **Coverage, publication DLP, and reviewer guide**
   - Use `publication.original` for filtered coverage; suppress the legacy
     warning fallback in filtered state; correct DLP wording; permit HTAB only
     in the two code fields; omit focus areas for one finding.
5. **Final validation and Draft handoff**
   - Complete changelog/docs, run the single full local gate, push all local
     history, reconcile hosted CI, update Draft/issue checklists, and leave all
     release state open and deferred.

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
- Implementation validation: pending.

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

Current action: validate and commit this planning checkpoint, create GitHub
coordination state and the initial Draft PR, then begin the OCR `1.10.1` slice.
After the initial Draft push, do not push again until all local slices and the
final local gate are complete.

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

This active plan may leave implementation state only when the Draft feature PR
is hosted-green and accurately documents Added, Fixed, Changed, Unchanged,
checksums, validation, and the exact head/tree. It must remain active or blocked
if any required check, issue criterion, or remote readback is incomplete.

#### Post-Close Delivery

Stable delivery remains deferred. A later explicitly authorized task may move
the exact reviewed Draft head to Ready, merge it, create `release/v0.8.4`, and
perform the protected publication lifecycle. That future work must revalidate
the immutable reviewed head and live provider/registry state.

#### Handoff Notes

- Draft PR, #145, #146, and milestone `v0.8.4` must remain open.
- The next agent must not repeat completed local development or run a real LLM;
  it should start from the exact documented Draft head and current hosted CI.
- OCR `1.10.1` is the qualified toolkit target; the previous `1.10.0` evidence
  remains historical and must not be rewritten.
