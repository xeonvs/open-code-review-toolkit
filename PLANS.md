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
This is documentation/process reconciliation only; it does not modify product/package source,
the stable tag, Release, receipt, compatibility baseline, runtime contract, or consumer
integration. Its protected-main merge may run the repository's standard TestPyPI development
build; that does not modify stable v0.9.0 and requires workflow-outcome readback only.

#### Work

1. [x] Re-read live release, tag, issue, milestone, branch, and synchronized-main state.
2. [x] Record v0.9.0 as externally delivered, including exact merge/tag/workflow/receipt identity,
   issue and milestone closure, immutable Release, and branch cleanup.
3. [x] Correct the release guide so external reconciliation updates the current archived release
   status and `.release-reconciled-version` through a protected no-release closure PR without
   mutating published artifacts; enforce that state transition with one focused CI contract.
4. [x] Run focused documentation/release-process tests, formatting, lint, and `git diff --check`;
   self-review the complete diff.
5. [ ] Commit, return this plan to its inactive template, push once, pass protected checks, merge,
   and re-read final repository truth.
