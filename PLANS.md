# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Reconcile v0.9.0 external closure

Status: active
Owner: Codex
Last Updated: 2026-09-03
Release classification: `no-release`
Published stable version: `0.9.0`
Branch: `codex/reconcile-v0.9.0-external-closure`

#### Goal

Correct repository truth after verified v0.9.0 publication: replace the stale current
`external stable delivery pending` status with the exact external closure receipts and prevent
the release lifecycle from requiring future published versions to remain permanently pending.
This is documentation/process reconciliation only; it does not create or modify a package,
tag, Release, receipt, compatibility baseline, runtime contract, or consumer integration.

#### Work

1. [x] Re-read live release, tag, issue, milestone, branch, and synchronized-main state.
2. [ ] Record v0.9.0 as externally delivered, including exact merge/tag/workflow/receipt identity,
   issue and milestone closure, immutable Release, and branch cleanup.
3. [ ] Correct the release guide so external reconciliation updates the current archived release
   status through a protected no-release closure PR without mutating published artifacts.
4. [ ] Run focused documentation/link/release-process tests and `git diff --check`; self-review the
   complete diff, commit, push once, pass protected checks, merge, and re-read final repository truth.
