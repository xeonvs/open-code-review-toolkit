# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Reconcile stable v0.9.1 and accept reopened release issues

- **Status:** active
- **Release classification:** `no-release`
- **Stable version:** unchanged `0.9.1`
- **Scope:** fix the release-issue pre-publication validator so an ordinary open issue
  remains eligible after GitHub records `state_reason=reopened`; add focused regressions;
  replace only the current v0.9.1 archive's pending external state with independently
  verified publication and recovery receipts; advance `.release-reconciled-version`.
- **External evidence:** release PR #179; failed pre-publication run 34101259655;
  successful recovery run 34101444987; immutable GitHub Release 383941713; receipt
  SHA-256 `4cff33ee3627d3d1fb1226afa819d44cb1ecb3eade9fb9a09c6b3946353a3433`;
  completed #176/#177 and closed milestone 12.
- **Invariants:** do not modify runtime/package behavior, stable authorization metadata,
  tag, Release, distributions, hashes, attestations, provenance, OCR evidence, or run
  OCR/Codex Security again. Keep pull-request payload rejection and completed-issue
  recovery strict.
- **Verification:** focused validator matrix; release/operations documentation contracts;
  Ruff; `git diff --check`; pinned Gitleaks; complete diff and trust-boundary self-review;
  protected hosted checks and post-merge TestPyPI development workflow readback.
- **Closure:** return this file to its inactive template before the final commit, merge the
  exact protected PR head, verify no topic/release branch remains, synchronized clean
  `main`, equal release/reconciliation markers, and unchanged immutable v0.9.1 surfaces.
