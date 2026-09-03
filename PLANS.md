# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Release 0.9.0: unprotected-target integrity and OCR 1.11.2/1.11.3

Status: active
Owner: Codex
Last Updated: 2026-09-03
Release classification: `release-required`
Target stable version: `0.9.0`
Milestone: `v0.9.0`
Authorization issues: `#167`, `#168`, `#169`, `#170`, `#172`
Feature branch: `codex/v0.9.0-unprotected-target-integrity`

#### Goal

Deliver safe limited OCR reviews for explicitly permitted unprotected GitLab targets while
preserving immutable identity, comment-only approval boundaries, valid receipt/action
attribution, detached-pipeline diagnostics, and adjacent OCR 1.11.2/1.11.3 compatibility.

#### Locked scope and decisions

- The release snapshot contains every issue open at activation: #167-#170. Later issues are
  not added automatically. The owner explicitly authorized the late addition of qualification
  issue #172 after OCR 1.11.3 was published, so #172 is part of this release without widening
  scope to any other later issue. Consumer repositories, B2B, `core/common`, and shared CI
  templates are outside scope.
- Resolve one effective reviewed source SHA across review, posting, and pre-execution status
  validation. Accept only lowercase 40-hex values, prefer a valid non-zero MR SHA, and fall
  back to `CI_COMMIT_SHA` only for an absent or all-zero MR SHA. All malformed, conflicting,
  stale, and mismatched identities remain fail-closed.
- Preserve receipt v6's strict positive evidence-action attribution. Move receipt construction,
  hostile parsing, and validation behind one internal owner. Missing, malformed, unwritable,
  or mismatched private action receipts fail before normal atomic publication and cannot publish
  findings or authorize approval. Advisories are evaluated only after receipt validity.
- Add `OCR_GITLAB_TARGET_PROTECTION_MODE=required|unprotected`. Unset means `required`; an
  explicit empty or unknown value fails closed. A protected target keeps current behavior under
  either setting. An actually unprotected target is limited to comment-only review with context
  `off` or bounded untrusted `metadata`; enriched context, adapters, protected-policy acquisition,
  and direct or inherited external MCP are rejected before OCR. Built-in immutable repository
  evidence remains available. Target Rules may be bounded model guidance, but accepted decisions
  and structured project guidance are omitted in the first implementation.
- Advance the public toolkit receipt to v7 with immutable target SHA and closed actual protection
  state. Unprotected receipts are structurally approval-ineligible and alone authorize the static
  italic limitation line after the primary status line for every normal receipt-backed outcome.
  Legacy receipts are not reinterpreted.
- Documentation is a same-release deliverable: README quick start, configuration, GitLab setup,
  operations/troubleshooting, security/trust model, and synthetic public GitLab examples cover the
  complete integration and failure model, including two-MR and supported one-MR setup paths.
- Qualify OCR 1.11.2, promote tested/recommended pins, and make the language-rule probe verify
  `.mjs`/`.cjs` JavaScript and `.cxx`/`.hxx` C++ routing while `.svh` remains excluded. Viewer,
  remote-MCP documentation, localization, and Go module-boundary changes have no toolkit runtime
  impact.
- Qualify OCR 1.11.3 against the branch-qualified 1.11.2 baseline without another semantic OCR
  run. Map its raw-traffic capture, failed-tool telemetry, SIGTERM handling, untracked-file error
  propagation, and editor-only dependency changes to consumed toolkit boundaries. Raw provider
  traffic must never be captured by a toolkit-owned OCR child, while bounded credential-redacted
  failure details remain console/CI-job diagnostics only. The additive failure envelope is not
  authoritative for the review result: absent, malformed, or contradictory diagnostics must not
  discard or suppress a valid manifest, findings, summary, or posting transaction. Provider-backed
  receipts retain only a closed diagnostic state and verified aggregate failed count; the
  toolkit-owned action receipt remains authoritative for completed evidence. Non-zero or uncertain
  diagnostics may block later approval authority, but never publication of an otherwise valid review
  signal. Promote 1.11.3 only after deterministic/no-provider compatibility and hostile end-to-end
  publication boundary tests pass.

#### Delivery sequence

1. [x] Create milestone `v0.9.0`, assign #167-#170, create this feature branch, and record the
   complete release plan as the first signed commit.
2. [x] Push only the plan commit and open a Draft PR with all issue links and the delivery plan;
   do not use closing keywords because the stable Release workflow owns issue closure.
3. [x] Implement #167 as a focused signed identity/status commit with its synthetic regression
   matrix.
4. [x] Implement #169 as a focused signed receipt/action-integrity commit. Positive evidence
   usage now requires exact private action attribution before atomic publication, zero-call
   results receive verified zero counts, and the shared neutral receipt owner validates every
   generated MR receipt before any advisory can be attached. Security regressions cover missing,
   malformed, unwritable, incomplete, type-confused, and per-tool-mismatched attribution.
5. [x] Implement #168 provider/config/snapshot, receipt v7, and approval boundary as one complete
   runtime commit. The exact closed setting preserves protected behavior, while an actually
   unprotected target rejects privileged context and external MCP, omits structured target policy,
   binds source/target/protection in receipt v7, renders the validated limitation, and cannot reach
   the approval executor. Hostile, orchestration, DLP-summary, and immutable-target regressions
   cover these boundaries.
6. [x] Implement #168 summary projection, complete public documentation, and synthetic examples
   as one complete documentation contract commit. The secure default, constrained capability matrix,
   two-MR and one-MR setup paths, static limitation, fail-closed diagnostics, and separate GitLab
   merge-policy boundary are now explicit and contract-tested.
7. [x] Implement #170 qualification, OCR 1.11.2 pins, Rules probes, and `maintenance` plus `rules`
   Towncrier entries. Hosted Linux workflow `33508349494` establishes the baseline qualification;
   the independently checksum-verified Darwin arm64 rerun matches every baseline contract and its
   expanded probe selects ten qualified extensions, binds `.mjs`/`.cjs` to exact JavaScript Rules
   and `.cxx`/`.hxx` to exact C++ Rules, and keeps `.svh` excluded. Security coverage across
   #167-#169 exercises the effective
   SHA matrix, strict evidence-action receipt reconciliation, atomic receipt identity, unprotected
   context/MCP rejection, static limitation provenance, and the unreachable approval executor.
8. [x] Review every commit and the complete `origin/main..HEAD` range, run all deterministic local
   gates, and fix supported findings in separately reviewed signed commits. The holistic source,
   test, and documentation review found no runtime defect; it reconciled the current receipt-v7,
   source/target identity, action-integrity, and constrained-target evidence/status contracts.
   The complete suite passed with 1,438 tests and 397 subtests at 86.37% coverage; every scoped
   risk floor passed. Compatibility, Towncrier draft, pinned Gitleaks, dependency audit, signatures,
   diff checks, clean build/Twine, archive privacy, and separate wheel/sdist CLI smokes also passed.
9. [x] Run exactly one Codex Security diff scan for `origin/main..HEAD`, validate attack paths, fix
   supported findings, and repeat holistic review plus deterministic validation. Scan
   `cecd81ce-bc01-42eb-bedf-a4a2a44a096c` completed with full changed-range coverage and no
   reportable findings. Its two rejected candidates still identified useful fail-closed contract
   hardening: surrounding whitespace must not normalize an inherited SHA, and summary/approval
   identities must come only from a fully valid receipt. Both controls and hostile regressions are
   included in the remediation commit. The post-remediation holistic review found no remaining
   defect, and the repeated deterministic gates passed with 1,438 tests, 406 subtests, 86.35%
   coverage, all scoped risk floors, compatibility, Towncrier, Gitleaks, dependency audit,
   signatures, diff checks, clean build/Twine, archive privacy, and wheel/sdist CLI smokes green.
10. [x] The checksum-verified PATH-effective OCR 1.11.2 installation and its rollback copy are
    complete. The one permitted configured-provider review ran over exact range
    `b9a0e54af7f39a1db21e2a8f4780761e74782bf8..cb9f4d9f39305e4cfdae5d4c91be7138edd0c4e3`
    with context `off`, public Rules, and concurrency 2, then failed closed before publication because
    OCR counts a dynamic MCP tool attempt before argument parsing/execution while private action
    receipt v2 counted only completed calls. No publishable result or complete manifest survived, no
    posting occurred. The owner subsequently authorized one repeat diagnostic OCR run with all raw
    private artifacts retained; it must run only after the root fix and relevant deterministic gates.
    The deterministic root remediation is complete with count-only action receipt v3: it authenticates
    MCP-received attempts and completed counts separately, retains a closed unattributed-attempt
    counter for malformed primary-tool actions and OCR-counted requests that fail argument parsing
    before MCP dispatch, reconciles received counts as subsets of OCR's authoritative by-tool
    attempts, requires a completed `summary` for mandatory evidence, and exposes only completed
    actions as successful evidence use.
    Hostile, malformed, failed-call, concurrency, receipt-readback, formatting, approval, and publication
    regressions restore the complete #167-#169 chain and adversarially cover parser, persistence,
    reconciliation, receipt, approval, and publication transitions. A completion is recorded only when
    that same request durably recorded its attempt, so it cannot consume an unmatched attempt retained
    from an earlier failed call. Normal posting now rejects every present incomplete or invalid receipt
    before reading prior review state or publishing findings; only a genuinely absent receipt keeps the
    compatible direct path. The complete deterministic suite passed with 1,468 tests and 407 subtests at
    86.31% coverage; compatibility, Towncrier, Gitleaks, dependency audit, signatures, diff checks,
    deterministic double build, Twine, archive privacy, and clean wheel/sdist CLI smokes are green. The
    owner-authorized retained-artifact OCR repeat then completed the exact
    `b9a0e54af7f39a1db21e2a8f4780761e74782bf8..782b205b8f8a2a5a2491c4f25b2b444a5e40c16b`
    range with all 20 selected items completed, no failed/reused/waived items, 144 total tool calls,
    and six exactly reconciled attempted/completed evidence summaries. No posting occurred and every
    raw private artifact remains retained. Its two supported findings are corrected in the current
    reviewed slice: generated OCR 1.11.1 language evidence and validation now share one canonical
    sorted extension projection, and local reviews no longer serialize receipt v7 with a non-GitLab
    `local` protection value. Local finalization still enforces result, action, and DLP contracts but
    remains receipt-less and approval-ineligible; any present invalid receipt still fails closed. The
    focused remediation and documentation matrix passes 253 tests, compatibility validation, Towncrier,
    Ruff format/check, and diff checks. Owner-only offline finalization of an exact copied result and
    action receipt confirmed the retained manifest range, terminal 20/20 coverage, six attempted and
    six completed evidence summaries, zero unattributed actions, the retained private DLP projection,
    a passed publication projection, and corrected receipt-less, approval-ineligible local output. The
    finalizer made no network or posting attempt, and recursive before/after hashes confirmed all 15
    files in the retained OCR directory remained byte-identical. No additional semantic OCR ran.
11. [x] Implement #172 as a separately reviewed signed slice. Hosted workflow `33725971286`,
    checksum-pinned schema-v3 evidence, adjacent-source audit, and independent Darwin arm64 readback
    qualify OCR 1.11.3 against the branch-qualified 1.11.2 predecessor without another semantic OCR
    run. Toolkit-owned preview and review children now remove inherited `OCR_RAW_LOGGING`; the strict
    additive diagnostic parser keeps bounded credential-redacted detail in the local/CI console only,
    strips detail and per-tool failure maps before finalization, and records only a closed receipt-v8
    state plus a verified aggregate. Absent, malformed, hostile, non-zero, and action-receipt-conflicting
    diagnostics preserve valid local and provider-backed findings, summary, manifest, DLP projection,
    and actual posting transaction; toolkit action receipt v3 remains authoritative for completed
    evidence, while uncertain or non-zero diagnostics independently block later approval authority.
    The new canonical `docs/review-decision-flow.md` supplies three contract-tested Mermaid maps with
    stable error, warning, success, auxiliary, and decision colors; the root `AGENTS.md`, strategy,
    documentation index, runtime owners, hostile tests, and all affected public contracts link to and
    agree with it. The complete deterministic suite passes with 1,486 tests and 408 subtests at 86.38%
    coverage and every scoped risk floor green. Compatibility, Towncrier draft, pinned Gitleaks,
    dependency audit, frozen Ruff format, signatures, diff checks, deterministic double build, Twine,
    archive privacy, and separate clean wheel/sdist CLI smokes also pass. No additional semantic OCR or
    Codex Security scan ran.
12. [ ] Push the locally closed implementation, finish hosted checks and review with zero unresolved
    threads, mark the Draft PR ready, and exact-head squash merge. Delete the feature branch.
13. [ ] Verify the protected-main TestPyPI development publication, create `release/v0.9.0`, set
    stable/next versions to `0.9.0`/`0.9.1`, record deterministic source epoch and authorization
    issues `[167,168,169,170,172]`, render Towncrier, archive this plan, and finish the protected
    release PR.
14. [ ] Monitor stable publication and independently verify registry/workflow/Release byte equality,
    PEP 740 and GitHub attestations, annotated tag target, immutable five-asset Release, release
    receipt, Python 3.12-3.14 wheel/sdist installs, Actions-owned issue receipts, issue/milestone
    closure, branch cleanup, and clean `main == origin/main == v0.9.0^{}`.

#### Per-commit and final validation

Before every commit, update this plan and affected status documents to post-commit truth, run focused
tests, apply the repository formatter for Python and require frozen Ruff format, inspect the entire
staged diff for correctness, hostile inputs, DLP/privacy, and scope, then run `git diff --check`.

Final deterministic gates are `scripts/quality.sh check`, compatibility validation, Towncrier draft,
Gitleaks, build/Twine, archive/privacy checks, and clean wheel/sdist CLI smoke. OCR exit zero is not
completion without complete selected-item coverage and exact receipt/action reconciliation. The one
owner-authorized repeat semantic OCR run and its private intermediates remain retained; it is complete
and no additional semantic run is authorized. The completed Codex Security scan must not be rerun.
OCR 1.11.3 qualification is deterministic/no-provider only. Stable delivery remains incomplete until
external publication and independent reconciliation are complete.
