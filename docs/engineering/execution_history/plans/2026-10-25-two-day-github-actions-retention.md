# Execution Plans

## Active Plan: Two-day GitHub Actions retention

plan_schema_version: 2
Status: done
Owner: root
Last Updated: 2026-10-25
Release classification: `no-release` repository infrastructure maintenance; no toolkit version change.

### Goal

Keep this repository's new GitHub Actions checks, workflow runs, artifacts and logs for two days, align repository-owned cleanup, and remove older completed runs already present on GitHub.

### Plan Origin

`direct_execution`

### Requested Scope

Set repository Actions retention to two days; update conflicting workflow artifact and maintenance retention settings, focused tests and owner documentation; delete existing completed runs older than two days; verify remote settings, survivors and repository checks.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | GitHub repository retention is two days for new Actions records | WQ-01, WQ-05 | done |
| REQ-002 | Repository cleanup and upload policy agree on two days | WQ-02, WQ-04 | done |
| REQ-003 | Older completed runs are removed without touching newer or active runs | WQ-03, WQ-05 | done |
| REQ-004 | Focused validation and review are recorded; protected PR delivery is explicit below | WQ-04, WQ-05; Post-Close Delivery | done |

### Explicit Non-Goals

No stable toolkit release, package or runtime change. Do not remove tags, GitHub Releases, published distributions, attestations, issues or external receipts. Historical release notes remain historical.

### Constraints

Use the exact `xeonvs/open-code-review-toolkit` repository. Two days is within the user's allowed range. Inspect candidate ages and statuses before deletion; only completed runs past the cutoff qualify. GitHub's new setting does not retroactively remove existing records. Protect credentials and keep cleanup inventory outside tracked source.

### Inputs And Sources

User request of 2026-10-25; clean baseline `main` and GitHub remote; `docs/development.md`, `docs/release.md`, `.github/workflows/actions-maintenance.yml`, `scripts/actions_cleanup.py`, focused tests and GitHub's live Actions API. Baseline GitHub retention was 90 days with 198 runs. Official GitHub retention documentation confirms prospective application.

### User Decisions And Answers

The user authorized 1–2 days and deletion of old runs. Choose two days for a small troubleshooting window. No further approval is needed.

### Completed Baseline State

`main` matches `origin/main`; no worktree changes. Maintenance uses seven days for artifacts/preview, 14 days for ordinary runs and 30 days for Release runs. GitHub retention is 90 days; 139 runs predate 2026-10-23 UTC, but the exact two-day cutoff remains to be computed.

### Current Work Queue

| Item | Requirements | Work | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-001 | Read remote setting and select exact two-day cutoff and API method | done |
| WQ-02 | REQ-002 | Align cleanup constants, workflow uploads, tests and development owner | done |
| WQ-03 | REQ-003 | Inventory then delete only old completed runs and expired artifacts | done |
| WQ-04 | REQ-002, REQ-004 | Resolve dependency-audit blocker with targeted lock update, run checks and inspect diff | done |
| WQ-05 | REQ-001, REQ-003, REQ-004 | Confirm GitHub setting and surviving runs; prepare checked archive closure | done |

### Locked Decisions

Two-day repository setting owns newly created checks, runs, statuses, artifacts and logs. Keep the bounded cleanup workflow for cache and historical cleanup; it must not promise longer retention. Use exact live API identifiers for deletion after a read-only inventory.

### Verification

Read back the repository endpoint as `days=2`. Verify each deletion candidate is completed and older than the exact UTC cutoff. Reread run counts and survivors. Run focused cleanup and documentation tests, format/lint as applicable, `git diff --check`, self-review and staged Gitleaks before commit; run required tree/history and dependency audit before push. Check hosted PR CI before merge if needed.

### Latest Validation Results

On 2026-10-25, GitHub retention PUT succeeded and independent GET returned `days=2`, `maximum_allowed_days=90`. Focused cleanup and documentation tests passed (45); Ruff format/check and `git diff --check` passed. Independent read of all 198 runs confirmed the dry-run's 144 completed-run candidates were older than two days, with no missed old completed or active runs. Live cleanup exited zero: 144 runs plus 20 artifacts deleted, zero already absent. GitHub then listed 54 runs, all newer than two days; a fresh full-history dry run had zero candidates. The required dependency audit initially failed on locked `filelock 3.32.6` and `setuptools 84.0.0`; a pinned-uv targeted lock update selected `filelock 4.2.4` and `setuptools 84.2.1`, and the audit passes with no known vulnerabilities. The full quality gate passed after the lock update. A subsequent focused test found that artifact cleanup kept an artifact at the exact two-day cutoff; the comparison was corrected and the affected 69 tests now pass. The final full quality gate reran after the cutoff correction and passed. Codex Security diff scan `95f33625-b6ef-4a67-91e0-a19eb796c9a8` completed with zero findings across five changed source/workflow files; synthetic tests, docs and lock metadata were reviewed through their separate checks. The aggregate source, tests, docs and lock diff was reviewed before staging.

### Risks And Recovery

Run deletion removes logs, artifacts and check metadata and cannot be undone. The user explicitly requested short retention and old-run cleanup. Use a dry-run/inventory and stop on unexpected API shapes or pagination. Read back an uncertain remote write before retrying. The targeted lock update must remain limited to its two patched packages, retain lock schema revision 5, and pass the final dependency audit. If policy changes cannot be delivered, keep the plan open with the exact blocker.

### Resume Point

No unfinished in-scope repository work remains. Protected PR delivery is classified in Post-Close Delivery.

### Plan Fidelity Check

- [x] Every user outcome maps to a requirement, queue item and verification.
- [x] Two-day choice, remote scope, prospective behavior and destructive deletion are explicit.
- [x] Non-goals preserve release artifacts outside Actions runs.
- [x] Recovery and first safe resume action are recorded.

### Reconciliation Check

- [x] Current main/worktree and GitHub retention baseline were read before mutation.
- [x] Final source, remote setting and historical cleanup agree.

### Closure Gate

- [x] All in-scope requirements and queue items are terminal with current validation.
- [x] No current workflow or owner document promises more than two days; older historical notes remain historical.
- [x] Protected PR delivery is classified below rather than claimed complete.

### Post-Close Delivery

Outside the closed repository plan: the checked archive transition completed. Remaining delivery requires staging the reviewed files, staged Gitleaks, a signed commit on a `codex/` branch, tree/history Gitleaks and dependency audit, push, PR, required checks, squash merge, and `main` plus GitHub retention readback. No stable release is planned; do not claim merged policy while only a local commit or PR exists.

### Handoff Notes

The two-day GitHub setting and historical cleanup are already complete. The pending work after archive closure is the protected PR delivery listed above. Keep large live cleanup lists and credentials outside commits.

## Recently Completed

- [x] 2026-10-23: Completed Toolkit 0.13.1 partial review of changes containing gitlinks; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-1-partial-review-of-changes-containing-gitlinks.md).
- [x] 2026-10-23: Completed Toolkit 0.13.0 protected default-policy fallback for single-MR review; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-0-protected-default-policy-fallback-for-single-mr-review.md).
