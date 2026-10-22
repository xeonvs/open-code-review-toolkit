# Execution Plans

Use this file for active or blocked work. Stable releases require indexing in
[execution history](docs/engineering/execution_history/README.md); this
no-release site launch will also be archived at the owner's explicit request.

## Active Plan: Toolkit site launch and release notification

plan_schema_version: 2
Status: active
Last Updated: 2026-10-22
Release classification: no-release for the toolkit workflow; the runtime and public toolkit contract are unchanged.

### Goal

Publish a clear English promotional site for Open Code Review Toolkit through a checked GitHub-to-Cloudflare path. Keep release content current and show only approved, rounded example operational metrics. The owner approved the first Cloudflare publication after checks and GitHub delivery.

### Plan Origin

plan_mode_approved

### Requested Scope

Edit the private `xeonvs/ocr-toolkit-site` landing page, latest-release block, video and Chief Review Officer cat Easter egg; add site CI/deployment and toolkit release notification; configure required secrets; perform review, security and first-user QA; merge through GitHub, publish, verify, and clean up. This public plan contains no private report source, raw telemetry, credentials, or local private paths.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Human site copy with only approved rounded operational shares | WQ-01, WQ-05 | done |
| REQ-002 | Latest stable release highlights, full notes, and event-driven refresh | WQ-01, WQ-02, WQ-06 | in_progress |
| REQ-003 | Accessible cat Easter egg with approved animation and separate sound | WQ-01, WQ-05 | done |
| REQ-004 | Checked merge-triggered CI/CD and first publication after approval | WQ-02, WQ-03, WQ-06 | in_progress |
| REQ-005 | Astra High pre-commit review, Codex Security, Gitleaks, first-user QA | WQ-04, WQ-05 | done |
| REQ-006 | Clean history and worktrees; no temporary QA or private material in commits; return toolkit checkout to current main | WQ-04, WQ-06 | in_progress |
| REQ-007 | Clear, consistent agent instructions and affected project documentation | WQ-04, WQ-06 | in_progress |

### Explicit Non-Goals

No custom domain, site account, form, analytics, raw operational report, private telemetry, or toolkit runtime change in this delivery. A local copied command is a first on-site action; it is not proof that a visitor completed an OCR review.

### Constraints

- Preserve the approved calm palette and cat speech-bubble style. The cat appears after three taps on a separate brand control; reduced-motion users see a still image without sound.
- Read GitHub Releases at build time. Required CI and production builds fail on unavailable, invalid, or mismatched latest release data. Do not poll on a schedule.
- Keep the site repository private. GitHub Free does not enforce its branch protection; deployment triggers only on merged PRs or a verified release dispatch, never a direct push.
- The owner authorized first publication after successful PR checks. The site PR merge triggers that deployment; the temporary `SITE_DEPLOY_ENABLED` variable has been removed from the site workflow and documentation.
- Publish no private paths, raw counts, production examples, credential values, or source report material.

### Inputs And Sources

- The current immutable toolkit GitHub Release and `release-receipt.json` are the changelog and publication source; `.github/workflows/release.yml` owns release publication.
- The existing Astro site, synthetic promo visuals, approved cat source animation and separate sound are source material; only optimized derivatives enter the site repository.
- `AGENTS.md`, `docs/development.md`, `docs/release.md`, and the installed engineering-workflow planning reference own repository process and closure.
- The owner supplied the LinkedIn URL for the published film and approved the rounded shares and revised visual example in this conversation.

### User Decisions And Answers

The owner approved the revised palette, release block, and comic-style cat; asked for natural English without self-repetition, no irrelevant site-data FAQ, and restrained license references. The owner requested cleanup and review before commits, supplied the cross-repository dispatch secret directly in GitHub, and approved Cloudflare publication after checks and GitHub completion. They confirmed that the toolkit change should be merged into `main` without a new stable version or stable-release artifacts, then the local toolkit checkout should return to current `main`. The ordinary TestPyPI development build may still run after merge. They explicitly requested archiving the final plan after live delivery.

### Completed Baseline State

Toolkit `main` had a stable v0.12.0 Release and protected release workflow. The site was an existing private Astro project with a local preview and base CI. Both repositories began this task with clean `main` checkouts; no task-owned QA files or private report path were found in reachable history, so no force rewrite was warranted.

### Current Work Queue

| Queue | Requirements | Exit evidence | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-001, REQ-002, REQ-003 | Edited site, release parser/tests, optimized cat assets, Astro check and strict build | `done` |
| WQ-02 | REQ-002, REQ-004 | Site deploy workflow and toolkit release notifier, trigger and receipt guards | `done` |
| WQ-03 | REQ-004 | Cloudflare secrets and owner-provided site-only dispatch secret verified | `done` |
| WQ-04 | REQ-005, REQ-006, REQ-007 | Separate Astra High review, completed Codex Security diff scans, Gitleaks, documentation audit | `done` |
| WQ-05 | REQ-001, REQ-003, REQ-005 | Desktop/mobile inspection and two sequential four-persona QA rounds | `done` |
| WQ-06 | REQ-002, REQ-004, REQ-006, REQ-007 | Merge checked PRs, verify Workers.dev deployment and release-refresh path, synchronize toolkit checkout with current main, close plan | `in_progress` |

### Locked Decisions

Use Cloudflare Workers Static Assets on Workers.dev first. The site fetches latest release content during the build and deploys only the current `main` commit after verification. The first Worker needs a Cloudflare token with creation permission; narrow it to the existing Worker after publication. The owner-provided GitHub token belongs only in the toolkit Actions secret. QA screenshots remain outside both repositories.

### Verification

Run toolkit `scripts/quality.sh check`, Gitleaks, scoped diff and instruction/document checks; site `npm run check`, `npm run test`, strict latest-tag build, Wrangler dry run, public-path and secret scans; inspect desktop and 375 px/mobile rendering; run two sequential sets of four first-user personas. Require a separate Astra High pre-commit review, Codex Security diff scans, GitHub PR checks, and live Workers.dev readback. Test automatic merge deployment and validate release dispatch wiring without issuing a new product release.

### Latest Validation Results

- 2026-10-22: Site Astro check, three release-parser tests, strict v0.12.0 build, Wrangler dry run, staged public-content scan and Gitleaks passed. Toolkit full quality matrix and staged Gitleaks passed. YAML syntax and diff whitespace checks passed. `actionlint` was unavailable on the last local pass after a network timeout; GitHub Actions execution is the live workflow gate.
- 2026-10-22: Four first-user browser personas ran in sequence, fixes were applied, then four fresh personas repeated the path. The 375 px and 320 px layouts had no horizontal overflow. On-site command copy took two actions for three personas; actual review still requires local setup. Headless automation did not establish video playback progress.
- 2026-10-22: Astra High reviewed both diffs, found two notification edge cases that were fixed, and reported no remaining actionable findings. Both Codex Security diff scans completed with full changed-surface coverage and zero findings.
- 2026-10-22: Both GitHub PRs are open. Site checks passed on its current documentation head; the toolkit follow-up's matrix is running. The temporary site deploy variable has been removed in the site branch before publication.
- 2026-10-22: Reachable history in both repositories passed Gitleaks; historical path and text searches found no task QA artifacts or private report path. Agent instruction contract, documentation navigation, and plan-lifecycle checks passed. The broader repo audit still labels the explicit archive successor link as an orphan despite the lifecycle and navigation checks accepting it; four prompt-risk heuristics are ordinary token references, not instruction overrides.

### Risks And Recovery

- GitHub Free cannot enforce branch protection on the private site repository. The deploy workflow rechecks the current main tip and reruns gates; maintainers must still avoid direct pushes.
- A missing latest release or tag mismatch must stop production build. If publication fails, keep the prior Worker version, inspect the failed GitHub job, and retry only from current reviewed main. Cloudflare rollback or a verified prior build is available after the first deployment.
- GitHub dispatch token scope is externally configured. If release notification fails, inspect its fixed workflow and site dispatch receipt; rotate or revoke the dedicated token. Do not use the broader local GitHub login token as an Actions secret.
- Do not revise historical archive records mechanically to silence a lifecycle checker; inspect their ownership and migration contract before any such change.

### Resume Point

WQ-06: commit and push this reviewed documentation correction, wait for toolkit PR checks, then merge it without a new stable version. Merge the newly checked site PR to trigger Cloudflare deployment. Verify the live site, synchronize the local toolkit checkout to current `main`, then reconcile plan closure. The owner already approved first publication after these checks.

### Plan Fidelity Check

- [x] Every requested outcome and restriction has a stable requirement and queue item.
- [x] Sources, decisions, non-goals, checks, risks, and next safe action are recorded.
- [x] Private report source and raw data are absent from public plan text.

### Reconciliation Check

- [x] Current implementation, review, and secret state match the queue above.
- [ ] Reconcile final GitHub checks, merged SHAs, Cloudflare URL, and live readback.

### Closure Gate

- [ ] All requirements and queue items are terminal and final validation matches delivered commits.
- [ ] GitHub merge, Cloudflare deployment, token narrowing, live readback, and release refresh wiring are verified.
- [ ] Archive this no-release plan through the installed lifecycle tool after publication evidence exists, as explicitly requested by the owner.

### Post-Close Delivery

Provide the verified Workers.dev URL, merged PRs, security and QA summary, and remaining factual limitations. No private report path or raw telemetry enters public delivery material.

### Handoff Notes

Continue only from WQ-06 and current GitHub check state. Both reviewed branches are open; deployment is not active yet. The site workflow removes the temporary variable and retains checked merge/dispatch triggers. Report actual live results rather than inferred success.
