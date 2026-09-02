# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Release 0.9.0: unprotected-target integrity and OCR 1.11.2

Status: active
Owner: Codex
Last Updated: 2026-09-02
Release classification: `release-required`
Target stable version: `0.9.0`
Milestone: `v0.9.0`
Authorization issues: `#167`, `#168`, `#169`, `#170`
Feature branch: `codex/v0.9.0-unprotected-target-integrity`

#### Goal

Deliver safe limited OCR reviews for explicitly permitted unprotected GitLab targets while
preserving immutable identity, comment-only approval boundaries, valid receipt/action
attribution, detached-pipeline diagnostics, and OCR 1.11.2 compatibility.

#### Locked scope and decisions

- The release snapshot contains every issue open at activation: #167-#170. Later issues are
  not added automatically. Consumer repositories, B2B, `core/common`, and shared CI templates
  are outside scope.
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

#### Delivery sequence

1. [x] Create milestone `v0.9.0`, assign #167-#170, create this feature branch, and record the
   complete release plan as the first signed commit.
2. [x] Push only the plan commit and open a Draft PR with all issue links and the delivery plan;
   do not use closing keywords because the stable Release workflow owns issue closure.
3. [x] Implement #167 as a focused signed identity/status commit with its synthetic regression
   matrix.
4. [ ] Implement #169 as a focused signed receipt/action-integrity commit.
5. [ ] Implement #168 provider/config/snapshot, receipt v7, and approval boundary as one complete
   runtime commit.
6. [ ] Implement #168 summary projection, complete public documentation, and synthetic examples
   as one complete documentation contract commit.
7. [ ] Implement #170 qualification, OCR 1.11.2 pins, Rules probes, and `maintenance` plus `rules`
   Towncrier entries.
8. [ ] Review every commit and the complete `origin/main..HEAD` range, run all deterministic local
   gates, and fix supported findings in separately reviewed signed commits.
9. [ ] Run exactly one Codex Security diff scan for `origin/main..HEAD`, validate attack paths, fix
   supported findings, and repeat holistic review plus deterministic validation.
10. [ ] Checksum-verify and atomically install PATH-effective OCR 1.11.2 with a rollback copy, then
    run exactly one configured-provider local OCR review of the complete exact range with context
    `off`, public Rules, concurrency 2, and owner-only artifacts. Inspect complete manifest coverage
    and receipt/action attribution; fix findings and repeat deterministic validation only.
11. [ ] Push the locally closed implementation, finish hosted checks and review with zero unresolved
    threads, mark the Draft PR ready, and exact-head squash merge. Delete the feature branch.
12. [ ] Verify the protected-main TestPyPI development publication, create `release/v0.9.0`, set
    stable/next versions to `0.9.0`/`0.9.1`, record deterministic source epoch and authorization
    issues `[167,168,169,170]`, render Towncrier, archive this plan, and finish the protected release
    PR.
13. [ ] Monitor stable publication and independently verify registry/workflow/Release byte equality,
    PEP 740 and GitHub attestations, annotated tag target, immutable five-asset Release, release
    receipt, Python 3.12-3.14 wheel/sdist installs, Actions-owned issue receipts, issue/milestone
    closure, branch cleanup, and clean `main == origin/main == v0.9.0^{}`.

#### Per-commit and final validation

Before every commit, update this plan and affected status documents to post-commit truth, run focused
tests, apply the repository formatter for Python and require frozen Ruff format, inspect the entire
staged diff for correctness, hostile inputs, DLP/privacy, and scope, then run `git diff --check`.

Final deterministic gates are `scripts/quality.sh check`, compatibility validation, Towncrier draft,
Gitleaks, build/Twine, archive/privacy checks, and clean wheel/sdist CLI smoke. OCR exit zero is not
completion without complete selected-item coverage and exact receipt/action reconciliation. A second
semantic local OCR run is prohibited. Stable delivery remains incomplete until external publication
and independent reconciliation are complete.
