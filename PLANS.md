# Execution Plans

Use this file for active, blocked, or recently completed execution work. Update it before implementation and before handoff or commit.

## Active Plan: Complete evidence coverage and GitLab review health for v0.4.4

Status: active
Owner: Codex
Last Updated: 2026-08-03
Release Classification: release-required
Target Stable Version: 0.4.4
Tracking Issues: #41, #42

### Goal

Make bounded repository evidence explicit about when negative conclusions are safe, repair Ansible dynamic-inventory and recursive role topology coverage, suppress exact no-op suggestions, and redesign the GitLab summary around independent review health, findings, and incomplete coverage. Close BL-022 by publishing the already-earned OpenSSF Best Practices badge and reconcile affected future backlog without claiming unrelated milestones.

### Decisions

- Build from verified toolkit v0.4.3 and retain checksum-qualified OCR 1.8.6; a newer OCR release requires separate qualification.
- Deliver #41, #42, and the OpenSSF documentation/backlog closure in one feature pull request, followed by the protected v0.4.4 release pull request.
- Treat OCR 1.8.6 `ocr.run-manifest/v1` failed coverage records as the canonical per-file failure source. Legacy warnings remain a bounded compatibility fallback, and `summary.files_reviewed` never proves successful coverage.
- Render a complete result with non-coverage warnings as `Review complete with warnings`; warnings do not demote validated complete coverage to incomplete.
- The OpenSSF record at project 13906 is publicly passing. Badge publication and BL-022 closure are `no-release` work bundled into this release-required objective.

### Work Queue

1. [x] Add a reusable scoped evidence-coverage schema, persistence/MCP/bootstrap contract, v1-store fail-closed compatibility, and deterministic coverage deltas.
2. [x] Classify static, dynamic, and executable inventory sources without execution; compose per-scope group coverage conservatively.
3. [x] Model Ansible's bounded recursive `defaults/main/` and `vars/main/` surfaces with upstream-compatible ordering and exclusions.
4. [x] Omit exact no-op suggestion blocks using the reviewed head blob while preserving findings and lifecycle identity.
5. [x] Normalize manifest/legacy incomplete-coverage diagnostics and render every result through one review-health/findings/coverage summary model.
6. [x] Add the OpenSSF badge, close BL-022 in planning truth, and reconcile BL-008/009/010/017 without changing their completion status or the roadmap.
7. [x] Add Towncrier fragments and update public evidence, GitLab operations, configuration, and security documentation.
8. [x] Run focused, complete, security, package, supported-Python, and GitLab Markdown contract validation. The optional live GitLab renderer requires authentication and is not a release gate.
9. [ ] Merge the feature through protected main, verify its TestPyPI development artifacts, then publish and independently verify stable v0.4.4 across TestPyPI, PyPI, tag, immutable GitHub Release, provenance, hashes, and supported-Python installs.

### Initial Evidence

- `main` is clean and synchronized with `origin/main` at `ce48166`; the latest independently verified stable release is v0.4.3 and `.next-version` is 0.4.4.
- The recommended/tested OCR baseline is 1.8.6. Its versioned manifest provides selected/completed/reused/failed/waived partitions plus bounded failed-item path, classification, and redacted reason fields.
- OpenSSF project 13906 reports passing at 100% and publishes the exact requested badge Markdown, so BL-022 can close after the repository badge readback succeeds.
- #41 touches the established M1 evidence boundary but does not complete BL-008, BL-009, or BL-010. #42 establishes result-derived reporting that BL-017 must reuse rather than duplicate; it does not implement telemetry.

### Pre-push Review Checkpoint

- The v2 store persists `repository.evidence-coverage/v1` atomically with snapshot indexes and deterministic semantic deltas. Legacy v1 stores remain readable but carry an explicit unknown-completeness diagnostic; missing facts support absence only for applicable `complete` coverage.
- Ansible topology stays offline and read-only. Static supported inventory, plugin YAML, and executable sources compose per directory; malformed, templated, truncated, symlinked, unreadable, or over-limit topology degrades coverage. Recursive role-main precedence and exclusions follow the loader contract verified in ansible-core 2.17 through current 2.x/devel, without a 2.17-only version gate.
- GitLab output now has one visible heading, independent health/findings/coverage states, bounded manifest-first failed-file diagnostics, quiet inline metadata, aggregate emoji, collapsed operational details, and exact reviewed-head no-op suppression. Existing discussion identity, suppression, rollback, and prior-review preservation remain intact.
- `uv run pytest -q` passes 541 tests plus 35 subtests. Ruff format/lint, mypy, `scripts/quality.sh check` (coverage above 70%), manifest validation, `git diff --check`, and checksum-verified Gitleaks 8.24.3 all pass.
- Two clean builds are byte-identical. Twine passes; the wheel smoke passes on Python 3.12 and the sdist smoke passes on Python 3.14. Current development hashes are wheel `13b6843dd4003115b8f93cd900b914170fef1ff292e6979ee592a01663f05029` and sdist `2115f60d35da864439b588ba9561f6d15c08db7c0aabfb47ae23c8f14c82dc5b`.
- The exact OpenSSF badge and target both return HTTP 200, and the target resolves to the public passing record. BL-022 is therefore removed; BL-008/009/010/017 retain their future status with only overlap clarified. No roadmap milestone is completed.

## Completed Plan: Harden OCR compatibility automation and release v0.4.3

Status: completed
Owner: Codex
Last Updated: 2026-08-03
Release Classification: release-required
Target Stable Version: 0.4.3
Tracking Issue: #49

### Goal

Repair the scheduled OCR compatibility workflow as a durable product boundary: consume OCR's versioned run-manifest outcomes safely, keep exactly one enriched qualification issue per upstream version, qualify OCR 1.8.4 through 1.8.6, and publish stable toolkit 0.4.3. Reduce GitHub Actions storage without deleting audit metadata by constraining cache writers, adding bounded retention automation, and performing one verified cleanup of accumulated caches, logs, and artifacts.

### Root Causes And Decisions

- Run `30798939793` proved two independent defects. OCR 1.8.5 and 1.8.6 emit the new manifest-derived `complete` status, while both the qualification probe and runtime consumers still require the legacy `success` family. OCR 1.8.4 passed, but two workflow steps independently searched an eventually indexed HTML marker and each created an issue.
- Keep one canonical issue per stable OCR version. For v1.8.4 preserve issue #48, copy current evidence into it, and close #43 through #47 with the `duplicate` label and an explicit link to #48.
- Qualification issues include a bounded, neutralized upstream change summary plus official release/compare links, machine evidence, toolkit-impact classification, and the current workflow receipt. Raw upstream Markdown is never forwarded as trusted issue content.
- Normalize legacy and manifest outcomes through one runtime contract. `success` and `complete` are clean; `completed_with_warnings` is complete with warnings; `completed_with_errors`, `budget_exceeded`, and `partial` are partial; `failed` is a failure; `skipped` is skipped. Manifest v1 status, coverage partition, failure classes, and bounds must agree before any result is accepted.
- Cache writes become main-only for uv; pull requests may restore the main cache but cannot save branch-scoped copies. Disable both CodeQL TRAP caching and the separately controlled v4 overlay-database mode for this small repository. Keep run/check metadata, delete only aged logs/artifacts, and retain release logs longer than ordinary workflow logs.
- GitHub's managed repository cache retention/storage-limit endpoints return HTTP 402 without a payment method. Repository-owned bounded maintenance is therefore the available policy mechanism.

### Work Queue

1. [x] Create tracking issue #49 and the implementation branch from synchronized protected `main`.
2. [x] Add one provider-neutral OCR result contract used by review execution, GitLab posting, and compatibility qualification. Validate legacy outcomes plus `ocr.run-manifest/v1`, including record/field bounds, set partition, terminal-state derivation, failure classes, and budget consistency.
3. [x] Render clean, warning, partial, failed, and skipped outcomes from one normalized matrix. Preserve partial findings with an explicit coverage warning; never publish normal comments for failed results; retain legacy OCR compatibility.
4. [x] Replace full-text issue search with bounded exact-marker REST reconciliation. Pass one concrete issue number through issue upsert and patch preparation; ignore only closed issues explicitly labeled `duplicate`, fail closed on every other competing marker, and preserve fatal integrity/API failures.
5. [x] Add safe upstream change summaries and official release/compare links to qualification issues. Classify every OCR 1.8.4-1.8.6 changelog item as toolkit-owned contract work, future-backlog impact, or release-note-only context.
6. [x] Qualify checksum-pinned Linux amd64 OCR 1.8.4, 1.8.5, and 1.8.6; recommend 1.8.6; update the manifest, evidence, runtime/example/docs pins, exact checksums, tests, and Towncrier fragments.
7. [x] Make uv cache saving main-only, disable CodeQL TRAP caching, set transient build artifact retention to seven days, and add a weekly/manual bounded Actions maintenance workflow with explicit dry-run/apply behavior.
8. [x] Validate the retention selector against synthetic API fixtures, execute a live dry-run, then delete accumulated stale caches and policy-expired logs/artifacts. Preserve tags, Releases, attestations, registry artifacts, and workflow/check metadata; reread usage after GitHub's delayed accounting refresh.
9. [x] Run focused contract/workflow tests, the complete Python matrix, Gitleaks, diff checks, build/Twine, and clean wheel/sdist installs. Perform adversarial review of result parsing, GitHub API bounds, issue rendering, and destructive target selection.
10. [x] Merge protected feature PR #50 and independently verify its exact TestPyPI `0.4.3.dev31` wheel and sdist against the workflow artifact and PEP 691 index.
11. [x] Prepare and merge `release/v0.4.3`, publish stable TestPyPI/PyPI artifacts, and independently verify tag/immutable GitHub Release, hashes, attestations, and Python 3.12-3.14 installs.
12. [x] Correct the post-release CodeQL v4 overlay-cache gap through a protected no-release follow-up, delete the two newly written overlay caches, and prove through hosted CodeQL plus live cache readback that they do not return.
13. [x] Record final receipts, close the tracking issue, and reconcile this plan plus every status-bearing roadmap/backlog representation affected by completed work.

### Initial Evidence

- The repository is clean and synchronized at stable release `ee769c3` (`v0.4.2`); `.next-version` is already `0.4.3`.
- Run `30798939793` discovered v1.8.4-v1.8.6. v1.8.4 produced a valid automatic-safe patch, while v1.8.5 and v1.8.6 failed with `candidate full review emitted an unsupported result object`.
- Upstream v1.8.5 introduces `ocr.run-manifest/v1` and derives top-level `status` from `terminal_state` (`complete`, `partial`, `failed`, `skipped`). v1.8.6 retains that contract.
- Issues #43-#48 contain the same exact v1.8.4 marker. The workflow created #47 in the patch-preparation step and #48 seconds later in the final issue step because both relied on GitHub full-text search rather than a concrete issue identity.
- Current Actions artifacts total about 16.6 MiB, while 37 active caches consume 494,925,898 bytes. Twenty-two CodeQL caches consume about 182.3 MiB and fourteen setup-uv caches about 284.2 MiB. Keeping the current two main uv caches plus Gitleaks and removing obsolete setup-uv/CodeQL entries should reclaim roughly 393 MiB before log/artifact cleanup.

### Pre-push Review Checkpoint

- Reviewed the complete local diff before any push across result normalization/publication, issue reconciliation/untrusted release rendering, and every destructive Actions selector/URL.
- Corrected two review findings before publication: partial results now preserve the prior complete review, and log cleanup is idempotent with a bounded retry window instead of repeatedly traversing immutable run history.
- `scripts/quality.sh check`, 180 focused tests plus 12 subtests, Ruff, mypy, workflow YAML parsing, `git diff --check`, and checksum-verified Gitleaks 8.24.3 worktree scanning pass locally. Supported-Python and hosted workflow results remain pending the protected PR.
- A second review after hosted v1.8.5 qualification exposed a transport-only timeout while downloading `sha256sum.txt`. The correction retries only bounded transient timeout, connection, incomplete-read, and selected HTTP failures; resets partial files before each retry; preserves origin, byte, and digest checks; and still fails immediately on HTTP 404 and local I/O errors. Focused validation passes 27 tests plus Ruff, mypy, and `git diff --check`.
- Promotion review confirms all three committed evidence files are byte-identical to hosted artifacts, every manifest evidence hash matches, all runtime/example/documentation pins select v1.8.6 with its qualified Linux checksum, and the unchanged upstream MCP SDK remains v1.6.1. The complete quality gate, 117 focused tests plus 15 subtests, manifest validation, Twine, and restricted-path wheel/sdist smokes on Python 3.12/3.14 pass. Fetching the repository's published tags corrected a local fallback-version-only preview before the final artifact gate and restored the intended 0.4.3 development line.
- Release review caught that OCR v1.8.6's new default exclusions are an effective rules-contract change and therefore require the conditional `🧩 Rules` changelog section. The corrected release diff contains only the 0.4.3/0.4.4 version markers, deterministic epoch, generated changelog, consumed fragments, and current plan receipts; no unrelated roadmap or backlog status changes are implied.
- The required post-release review caught that CodeQL v4 controls overlay-base database caching separately from the configured TRAP cache input. The follow-up selects full-database mode explicitly, preserving complete analysis while eliminating that cache writer; focused tests, workflow parsing, the complete quality gate, Gitleaks, signed-commit verification, hosted CodeQL, and live cache readbacks all pass before closure.

### Execution Evidence

- Issues #43 through #47 are closed with the `duplicate` label and a link to canonical issue #48. The passing v1.8.4 qualification run `30807114499` updated #48 in place with bounded upstream release changes and its current receipt.
- The accumulated cleanup deleted 189 stale Actions objects while preserving workflow and check metadata. GitHub's refreshed aggregate and direct cache listings now agree on three current caches totaling 79,827,436 bytes. After the feature-PR and qualification runs, 108 policy-retained artifacts total 10,922,669 bytes.
- Hosted run `30807169920` reached v1.8.5 asset qualification but failed on a single read timeout, motivating the bounded transport retry correction above rather than weakening checksum or result-contract validation.
- Runs `30807639061` and `30807718526` then qualified v1.8.5 and v1.8.6 respectively, producing byte-identical committed evidence and one canonical release-enriched issue each (#51 and #52). The manifest records v1.8.6 as the tested recommendation with its exact Linux amd64 checksum `1f2611766a562aee300af75524270de9b99ab2cf5c63bf75a9546ebf809f78a6`.
- Release classification found one toolkit-owned contract change: v1.8.5's `ocr.run-manifest/v1`, handled by the shared normalized parser. v1.8.4's LLM/gitignore fixes and GitHub Action fallback, plus v1.8.5's telemetry, VS Code, manual-provider, configuration, and test changes, require no further toolkit adaptation. v1.8.6's expanded default exclusions are an accepted effective review-scope change; its session-comment command, truncated-chat retry, and test refactor require no toolkit work. No future-backlog item is warranted, and OCR's Go MCP SDK remains v1.6.1.
- Feature PR #50 merged through the active ruleset as signed squash commit `8106bcedf237b1efe132503bb7f7f8f2d712471b` after 13 required checks passed and zero review threads remained. A pre-merge ruleset audit caught unsigned checkpoint commits; the feature branch was re-signed with an already registered key, proven tree-identical, rescanned, and revalidated without using an administrative bypass.
- TestPyPI development run `30808897066` published and installed immutable `0.4.3.dev31` artifacts. The downloaded workflow artifact and independent PEP 691 query agree on wheel SHA-256 `3506f6789942309d2efc7849f2509e0cb707df4c3372592a18177eab332161f0` and sdist SHA-256 `49412600010f5d36b0ab1004a099778d92487c64c1cfafb6869e7168d3039131`.
- Because OCR v1.8.6 expands its default file exclusions, the stable 0.4.3 changelog includes a separate `🧩 Rules` entry in addition to the main feature entry. The reproducible source epoch is `1785755800`, one second after the feature merge commit, and `0.4.4` becomes the next development line.
- Release-focused validation passes 71 tests, the complete quality gate, manifest validation, exact release-body rendering, and `git diff --check`. Two independent stable builds are byte-identical: wheel SHA-256 `236b08306f6fe3a6fe65e1a96e8170ad3566b77e0cbf6d7c6525c1ec98432273` and sdist SHA-256 `4617ce04bb957130d1dae8be7237fe82a9d342ef09f45836779cfc1dec24ec92`; Twine and restricted-path Python 3.12 wheel/Python 3.14 sdist installs pass.
- Release PR #53 passed all 13 protected checks with no review threads and merged as GitHub-signed commit `a9822bfcf28c9f38d3f3078c31550a76a520eea9`. Release workflow run `30809679849` completed authorization, deterministic build, GitHub provenance attestation, stable TestPyPI and PyPI publication and verification, and GitHub Release publication successfully.
- Independent PEP 691 reads from TestPyPI and PyPI expose exactly the reviewed wheel and sdist hashes above, and the downloaded registry bytes, workflow artifact, and immutable GitHub Release assets are byte-identical. Both registries expose integrity attestations from their authorized `release.yml` environments, while `gh attestation verify` binds both distributions to the exact release merge and workflow run. Clean installs of the published wheel pass on Python 3.12 and 3.13; the published sdist install passes on Python 3.14.
- Annotated tag `v0.4.3` resolves exactly to the release merge, and the GitHub Release is public, non-draft, non-prerelease, and reports `immutable: true`. The automation-created annotated tag is not separately cryptographically signed; authenticity is carried by the GitHub-signed target commit and Sigstore-backed artifact provenance.
- Canonical qualification issues #48, #51, and #52 have checked human outcomes, preserve bounded upstream release changes, and are closed as completed; #43 through #47 remain closed and labeled as duplicates of #48. Tracking issue #49 was reopened for the post-release review correction and closed as completed only after protected-main and live-storage verification passed.
- No-release follow-up PR #54 passed all 13 protected checks with no review threads and merged as GitHub-signed commit `fdb5354d27c0a763ff14bfddb5a5d7e96e2dd72b`. PR CodeQL run `30810867531` and protected-main run `30811041908` both completed successfully in full-database mode without creating a CodeQL cache.
- The cleanup removed 192 stale or expired Actions storage objects in total, including one artifact that expired after the first readback and the two post-release `codeql-overlay-base-database-*` entries totaling 20,848,354 bytes. The post-follow-up aggregate and direct API listings agree on exactly three intended caches totaling 79,827,436 bytes and zero CodeQL caches; at that receipt, 122 non-expired policy-retained artifacts total 12,727,750 bytes, with no expired artifacts. Workflow/check metadata, tags, Releases, attestations, and registry artifacts remain preserved.
- Every protected-main follow-up workflow passed: CI run `30811041625`, Security `30811041628`, OpenSSF Scorecard `30811041871`, CodeQL `30811041908`, and TestPyPI development run `30811041769`. The latter published and installed immutable `0.4.4.dev33`; its workflow artifact and an independent PEP 691 query are byte-identical at wheel SHA-256 `7745ffe5cf084dbbe887c9663c7b236ca831156d770aacfc82c5451dbc994209` and sdist SHA-256 `c9eaeeaf96519da9c62ad422224927c72e4a267cc9fa1d90433bbaa2a08b9b29`.
- No roadmap milestone or future-backlog status was coupled to this operational compatibility/release plan, so `ROADMAP.md` and `docs/codex/TASKS_BACKLOG.md` require no closure change. The post-release repository-infrastructure correction is `no-release`; stable product behavior remains the published 0.4.3 release.

## Completed Plan: Qualify OCR 1.8.3 and release v0.4.2

Status: completed in repository; release PR is the final publication gate
Owner: Codex
Last Updated: 2026-07-31
Release Classification: release-required
Target Stable Version: 0.4.2
Tracking Issue: #38

### Goal

Qualify OCR 1.8.3 through the reduced patch-release path, recommend and pin it with exact checksums, adapt only consumed toolkit contracts proven to have changed, and publish stable toolkit 0.4.2. Preserve the protected implementation/release PR and external verification gates while avoiding unnecessary compatibility approval or post-release closure stages.

### Initial Impact Classification

- Per-file terminal-state handling is a possible result-contract interaction and must be covered by the normal JSON consumer probes before it can be declared compatible.
- The Cobra CLI migration changes implementation and adds shell completion, but the toolkit consumes only the existing review/help/version/config commands and flags; exact help/version/preview probes determine whether adaptation is needed.
- Viewer and VS Code changes are outside the toolkit contract. Configuration URL documentation and stale comments are release-note-only context unless the consumed rendered-config behavior changed.
- Rules content and OCR allowlisted file types do not change in 1.8.3. The upstream rules change adds integrity tests only, so 0.4.2 must omit `🧩 Rules` unless qualification finds a real effective-contract delta.

### Work Queue

1. [x] Run Linux amd64 qualification for OCR 1.8.3, preserve canonical evidence, and classify every release item against the toolkit/backlog contract.
2. [x] Add the reviewed manifest conclusion, recommend/pin OCR 1.8.3 everywhere, and update exact checksum regressions without weakening the future classifier.
3. [x] Add ordinary changelog entries without `🧩 Rules`, run proportional targeted/full/security/package validation, and verify the exact release-body comparison URL.
4. [x] Merge the protected implementation PR and verify its exact TestPyPI development build.
5. [x] Complete repository closure in `release/v0.4.2`, publish through the protected release workflow, and create no post-release repository PR.
6. [x] Hand stable TestPyPI/PyPI artifact, tag/immutable GitHub Release, hash, provenance, and Python 3.12-3.14 verification to the release workflow and external issue/goal closure.

### Initial Evidence

- OCR 1.8.3 release notes contain viewer comments, per-file terminal-state handling, VS Code force-kill behavior, a Cobra CLI migration with shell completion, configuration URL documentation, documentation cleanup, and rules-integrity tests. No built-in rules or file allowlist content change is advertised.
- Linux amd64 qualification passed all published asset and upstream checksum-file checks plus version, Cobra help/required-flag, preview, and additive result-consumer probes. Canonical evidence SHA-256: `4acc04e487834e367851c64b5cfa18316a09ae1c59f5c0c991eb69c712ef58bd`.
- Source-diff review confirms the MCP SDK remains Go MCP SDK v1.6.1. Per-file terminal-state fixes preserve the consumed result contract; the CLI migration preserves toolkit commands and flags. Viewer, VS Code, documentation/comment, gitignore, and rules-integrity changes need no toolkit adaptation.
- Targeted compatibility, integration, preflight, and evidence-MCP regressions pass with 109 tests and 15 subtests. The 0.4.2 Towncrier draft contains only `🚀 Features`; `🧩 Rules` is correctly omitted because toolkit `rules.json`, OCR built-ins, and OCR allowlist are unchanged.
- `scripts/quality.sh check` passes with 494 tests and 35 subtests at 78.73% coverage plus Ruff formatting/lint, strict mypy, and Bandit. Gitleaks, `git diff --check`, build/Twine, and clean wheel/sdist CLI installs on Python 3.12/3.14 pass.
- A disposable release build renders only the non-empty `🚀 Features` category and ends with `**Full Changelog**: https://github.com/xeonvs/open-code-review-toolkit/compare/v0.4.1...v0.4.2`; no `🧩 Rules` or conventional prefixes appear.
- Implementation PR #39 merged as `71af90da9258e57f1457ce86c94ffff403b8eb87` after every required check passed and no review threads remained. TestPyPI development run `30625374711` published and installed immutable `0.4.2.dev29` artifacts successfully.
- The final release branch renders the 0.4.2 changelog without `🧩 Rules`, authorizes reproducible artifacts from source epoch `1785495495`, establishes `0.4.3` as the next development line, and leaves no repository planning closure for after publication. Issue #38 remains the external stable-publication tracker.
- Two independent 0.4.2 release builds are byte-identical: wheel SHA-256 `0ca73e62dfaf4ebd478419cd6214c33444eff4697cd616accb6a33b7193b7e1d`, sdist SHA-256 `c7a341fd2de948c681093f03db1225cc6a145a4448fbc14fcb54b01da529f9ef`; Twine, exact release-body checks, and clean Python 3.12 wheel/Python 3.14 sdist installs pass.

## Completed Plan: Qualify OCR 1.8.1/1.8.2 and release v0.4.1

Status: completed in repository; release PR is the final publication gate
Owner: Codex
Last Updated: 2026-07-31
Release Classification: release-required
Target Stable Version: 0.4.1
Tracking Issue: #35

### Goal

Adopt OCR 1.8.1 and 1.8.2, make 1.8.2 the recommended version, preserve partial reviews when the upstream token budget is exhausted, and publish toolkit 0.4.1. Improve release notes with OCR-style emoji headings, an explicit `Rules` category for changes to the effective toolkit plus OCR rules/allowlist contract, and an exact full-changelog comparison link.

### Release Decisions

- The completed release-note and source review in this plan is the compatibility decision for both OCR releases. Do not create a separate compatibility issue or approval checkpoint; retain the conservative classifier for future unknown releases.
- `Rules` covers changes to `examples/gitlab/rules.json`, recommended OCR built-in rules, or the recommended OCR allowlist. It is present in 0.4.1 for the Go, PHP/Composer, Prisma, and Protocol Buffers changes even though the toolkit-owned `rules.json` content is unchanged.
- Keep BL-015 and BL-016. Refine BL-017/M5 to reuse OCR token, cost, and budget telemetry and limit toolkit-owned work to missing GitLab lifecycle, evidence/MCP, and posting signals.
- Complete repository planning closure in the final release branch before publication. Do not require a post-release closure PR.

### Work Queue

0. [x] Create tracking issue #35 and open the implementation branch from current `main`.
1. [x] Record qualification evidence for OCR 1.8.1 and 1.8.2; update the compatibility manifest and all recommended runtime, preflight, example, CI, and documentation pins to 1.8.2.
2. [x] Support `budget_exceeded`, `summary.budget_exceeded`, and `token_budget_reached` as a partial warning outcome while preserving findings and usage metadata.
3. [x] Authenticate compatibility metadata requests without forwarding credentials to release assets or diagnostics.
4. [x] Add conditional emoji Towncrier categories, the 0.4.1 `Rules` entries, and an exact GitHub Release `Full Changelog` link.
5. [x] Reconcile BL-017/M5 and document the upstream-impact classification; keep BL-015/BL-016 unchanged.
6. [x] Run targeted tests, full quality, Gitleaks, diff checks, distribution checks, and Linux amd64 OCR contract probes.
7. [x] Merge the protected implementation PR and verify the resulting TestPyPI development publication.
8. [x] Prepare `release/v0.4.1` with the final changelog, release authorization metadata, next development line, validation evidence, and repository planning closure.
9. [x] Hand stable TestPyPI/PyPI 0.4.1, exact tag and immutable GitHub Release, hash, provenance, and supported-Python verification to the release workflow and external issue/goal closure; no post-release repository PR is required.

### Validation Evidence

- Local Linux amd64 qualification probes completed for OCR 1.8.1 and 1.8.2: all release assets and `sha256sum.txt` matched, consumed CLI/preview/result contracts passed, and both candidates were compatible.
- Upstream impact review: OCR 1.8.1 adds budget termination fields, Go built-in guidance, and Prisma allowlist support; OCR 1.8.2 adds PHP/Composer built-in guidance and Protocol Buffers allowlist support. GitHub Action, VS Code, viewer/Pages, and unrelated provider/URL/help fixes do not require toolkit runtime adaptation.
- The scheduled compatibility run `30615923070` failed before qualification because anonymous GitHub metadata access returned HTTP 403 rate-limit exhaustion; authentication is therefore part of this correction.
- Compatibility manifest validation accepts the reviewed 1.8.1 -> 1.8.2 sequence, exact evidence hashes/assets, 1.8.2 recommendation, and 1.8.2 monitoring floor while preserving the conservative machine classifier.
- Targeted compatibility, release-note, review-runner, posting, integration, and evidence-MCP regressions pass. The 0.4.1 Towncrier draft contains non-empty `🚀 Features`, `🐛 Bug Fixes`, `📖 Documentation`, and five separate `🧩 Rules` entries; empty categories and conventional prefixes are absent.
- BL-015 and BL-016 remain unchanged. BL-017 and M5 now explicitly reuse OCR token/cost/budget telemetry and restrict future toolkit telemetry to demonstrated GitLab lifecycle, evidence/MCP, posting, and review-value gaps.
- `scripts/quality.sh check` passes with 494 tests and 35 subtests at 78.73% coverage, plus Ruff formatting/lint, strict mypy, and Bandit. Gitleaks and `git diff --check` pass; wheel and sdist pass Twine and clean Python 3.12 install/CLI smoke tests.
- A disposable release build renders exact conditional emoji headings, five separate `🧩 Rules` entries without conventional prefixes, and `**Full Changelog**: https://github.com/xeonvs/open-code-review-toolkit/compare/v0.4.0...v0.4.1`.
- Implementation PR #36 merged as `5c205a7f59a32556264957c4b70eb0517521cdb9` after every required check passed and no review threads remained. TestPyPI development run `30623803468` published and installed immutable `0.4.1.dev2+g5c205a7f5` artifacts successfully.
- The final release branch renders the 0.4.1 changelog, authorizes reproducible artifacts from source epoch `1785493846`, establishes `0.4.2` as the next development line, and leaves no repository planning closure for after publication. Issue #35 remains the external stable-publication tracker.
- Release-branch validation passes 494 tests and 35 subtests at 78.73% coverage plus release-specific authorization/documentation tests, Gitleaks, and diff checks. Two independent 0.4.1 builds are byte-identical: wheel SHA-256 `d71d64cd2d40fa3d09e7d849bd42ab17f5339b57e6589be7299cb0332cb2b033`, sdist SHA-256 `3dfee22ca57ca8941a946e928c5cb4f9e2a0e61e6bad1199b5df359480ef821f`; Twine, exact metadata/content checks, and clean Python 3.12/3.14 installs pass.

## Completed Plan: Implement M1 evidence architecture for v0.4.0

Status: completed; stable release and external reconciliation verified
Owner: Codex
Last Updated: 2026-07-31
Release Classification: release-required
Target Stable Version: 0.4.0
Tracking Issue: #30

### Goal

Replace the bounded legacy Markdown context generator with a schema-versioned repository evidence engine, base/head snapshots and typed deltas, compact bootstrap projection, and a built-in read-only MCP server. Preserve all safe legacy facts through semantic parity checks, remove the legacy public contract only after end-to-end verification, and improve GitLab review outcome rendering.

### Work Queue

0. [x] Refresh the zero-runtime-dependency build/test toolchain and pinned GitHub Actions from authoritative upstream release metadata. The 12 direct build/dev requirements have a combined declared floor of Python 3.10 and no declared upper bound; the already approved M1 toolkit contract remains Python 3.12 through 3.14. The complete locked toolchain and 524 tests plus 53 subtests pass separately on 3.12, 3.13, and 3.14, while 3.15 remains unclaimed until the complete toolchain and project suite are qualified there. All 11 Action repositories resolve their documented stable tags to the pinned immutable SHAs. The isolated quality gate passes formatting, lint, strict typing, Bandit, 524 tests plus 53 subtests, and 78.37% coverage. Fresh wheel/sdist artifacts pass Twine 7, zero-runtime-dependency metadata checks, and Python 3.12 wheel/Python 3.14 sdist smoke installs. Package metadata and CI remain the version source of truth; the README development notice no longer duplicates Python numbers. This is release-deferred work for 0.4.0 and remains a separate signed checkpoint from legacy removal.

1. [x] Update the effective local OCR binary to verified upstream v1.8.0 while retaining a rollback copy.
2. [x] Freeze legacy context behavior and upstream OCR v1.8.0 result contracts in synthetic tests and fixtures.
3. [x] Implement the dependency-free evidence schema, bounded store, redaction-before-storage, deterministic identities, and serialization (BL-004).
4. [x] Implement immutable base/head file snapshots and repository-file deltas with explicit missing, both rename sides, deletion, symlink, submodule, and shallow-clone behavior (first BL-005 slice).
5. [x] Complete typed dependency/runtime/container/guidance collection and deltas for both refs without routing facts through legacy Markdown (BL-005). The typed-only path, source-aware identities, container images, application/infrastructure pins, guidance, Ansible topology/Galaxy parity, and Python, JavaScript, Go, and Composer/PHP declarations/locks are implemented and validated. The v0.4 package/runtime floor is Python 3.12, matching the documented `python:3.12-slim` CI integration and allowing the standard-library TOML parser to remain dependency-free, with tested support through Python 3.14. Missing lockfiles remain represented as absent resolved facts rather than an invented error: only a present candidate can be malformed or unavailable.
   - Ecosystem parser boundaries are final before implementation: shared normalized contracts live in `evidence.manifest_model`, orchestration and immutable reads stay in `evidence.collectors`, and each ecosystem owns a dedicated parser module. JavaScript, Go, and Composer/PHP must be implemented directly in their final modules, without temporary duplicate parsers in the orchestrator.
   - JavaScript checkpoint: `evidence.javascript_manifests` directly preserves `package.json` Node/npm/Yarn/pnpm runtime and package-manager constraints, production/development/peer/optional declarations, npm lock v1-v3, Yarn Classic/Modern, and pnpm v5-v9 resolved facts without a YAML runtime dependency.
   - Go checkpoint: `evidence.go_manifests` directly preserves module identity, Go language/toolchain/GODEBUG declarations, direct/indirect requirements, replace/exclude/tool/retract/ignore semantics, and `go.sum` module/content checksum pairs as separately typed resolved evidence.
   - Composer/PHP checkpoint boundary and test matrix: implement `composer.json` and `composer.lock` directly in `evidence.composer_manifests`, while `evidence.collectors` retains only registry and immutable-read orchestration. Preserve package identity, production/development requirements, PHP/HHVM/extension/Composer platform constraints, configured platform overrides, provide/replace/conflict semantics, stability preferences, locked production/development packages, lock platform requirements, content/plugin API metadata, safe source classifications and references, aggregate bounds, malformed-versus-missing lock behavior, base/head deltas, and built-in MCP visibility. Repository-controlled URLs and paths remain untrusted and are classified or redacted rather than copied as credentials.
   - Composer/PHP checkpoint validation: the dedicated parser preserves the planned declaration, virtual-platform, lock, safe-source, bounds, delta, and MCP contracts; legacy PHP context facts remain covered semantically while the typed model adds scopes and resolution metadata. Focused parser/collector tests pass with 38 tests; the full gate passes with 504 tests and 53 subtests at 77.97% coverage; strict typing/lint, a fresh package build with metadata checks, and Python 3.12 wheel/Python 3.14 sdist smoke installs pass.
   - Remaining application/infrastructure checkpoint boundary: implement conservative version-like key and nested-image extraction directly in `evidence.infrastructure`, register only the legacy-supported declarative configuration surfaces, and collect them from immutable base/head blobs. Emit `application.version` for non-image pins and the established image kinds for image pins, with path/key/name identities that turn upgrades into `changed` deltas. Preserve fixture/environment exclusions, interpolation and unpinned/latest rejection, schema/API/config metadata exclusions, redaction, deterministic aggregate bounds, bounded diagnostics, and MCP visibility. Extend the dedicated Ansible topology parser only for history-backed core-manifest gaps proven by the migration matrix; do not turn this compatibility checkpoint into an unbounded framework detector.
   - Application/infrastructure checkpoint validation: conservative declarative pins, nested image tags/digests, Dockerfile stages, exclusions, interpolation/latest rejection, redaction, aggregate bounds, application/image changed deltas, normalized parity tokens, Ansible role vars, and MCP visibility pass 45 focused tests. The full gate passes with 510 tests and 53 subtests at 78.27% coverage; strict typing/lint, a fresh package build with metadata checks, and Python 3.12 wheel/Python 3.14 sdist smoke installs pass.
6. [x] Separate collection, storage, planning, and rendering completely; remove legacy rendering only after the typed path passes its removal gates (BL-006). The lifecycle/composition checkpoint is sealed in signed commit `dda2efe`. The removal audit maps every migration-matrix row to typed tests, preserves renderer-independent GitLab CI/docs/project-rule/test-integrity contracts, and proves 11/11 non-empty legacy dependency/image facts on immutable refs with no missing fact. Public `context`, temporary `evidence-parity`, `ocr_toolkit.context`, `ocr_toolkit.evidence.parity`, and the `repository.context` schema kind are removed. The full isolated quality/security gate passes 412 tests plus 35 subtests at 77.41% coverage; fresh wheel/sdist artifacts pass Twine, contain no legacy modules or runtime dependencies, and clean-install on Python 3.12/3.14 without exposing legacy CLI commands.
7. [x] Integrate compact bootstrap and deterministic JSON projections into one toolkit-owned review preflight; `.review-context/evidence.json` and `.review-context/bootstrap.md` are private implementation artifacts, not a separately configured user workflow.
8. [x] Complete the bounded read-only `ocr_toolkit_evidence` stdio MCP integration (BL-007): toolkit-owned artifact discovery, toolkit-owned internal module registration, review-lifecycle startup, bounded diagnostics, and proven non-zero calls from real OCR. OCR's registry contains independent MCP entries: the built-in evidence server is always one mandatory entry, while every retained or newly configured local/remote server remains a separate optional entry. Current architecture reserves the mandatory server and tool names, derives bootstrap inventory from the exact registry, owns artifact preparation inside `ocr-ci review`, and never passes evidence JSON to OCR. Real OCR 1.8.0 exposed two compatibility gaps before its LLM review could prove use: its exact `go-sdk` v1.6.1 client negotiates MCP revision `2025-11-25`, and a clean-start review showed that registering the bare `ocr-ci` console script incorrectly depended on the caller's `PATH`. Both are corrected. The registry now uses the current absolute Python executable with isolated mode and an internal module entrypoint, so editable and wheel installs remain self-contained with an empty `PATH` and an untrusted repository shadow package cannot intercept imports. Python lifecycle contracts, a 87-test/15-subtest focused gate, a clean Python 3.12 wheel adversarial subprocess probe, the full 415-test/35-subtest quality/security gate at 77.38% coverage, and a process-level initialize/initialized/ping/list/summary/list/get probe through exact Go MCP SDK v1.6.1 pass. The two completed real OCR reviews then recorded 165 and 220 verified `ocr_toolkit_evidence` calls respectively, proving non-zero use through the integrated lifecycle and closing the item.
9. [x] Improve GitLab summary outcomes, zero-counter suppression, severity/category presentation, and the default-on `OCR_POST_EMOJI` switch.
   - MCP usage reporting maps OCR's structured per-tool counters back to the exact validated independent server registry used by that review. The review step atomically binds only positive per-server counts in a schema-versioned toolkit receipt to the private result; posting consumes that receipt rather than reconstructing environment-dependent MCP state. Commands, URLs, headers, arguments, inputs, results, repository contents, and configured-but-unused entries remain absent. Cross-server tool-name collisions are rejected because OCR exposes one global tool namespace and attribution would otherwise be ambiguous.
   - Telemetry remains outside M1. Upstream OCR already owns provider-level duration, LLM/token, and tool-call metrics. M1 E2E will record whether structured OCR results and existing telemetry expose mandatory evidence-MCP/optional-MCP usage and lifecycle outcomes adequately; M5/BL-017 now starts with that gap audit and permits a no-new-layer conclusion.
   - Lifecycle checkpoint validation passes 522 tests and 53 subtests at 78.17% coverage with formatting, lint, strict typing, and the medium-confidence/medium-severity source security scan clean. Its 183 focused tests and 27 subtests cover registry readback, independent entry preservation, global tool-name collision rejection, evidence summary/list/get self-query, mandatory-use gating, skipped results, optional-server attribution, reserved receipt spoofing, symlink/hard-link rejection, bounded/deep result parsing, reporting, and zero-use omission. A fresh wheel and sdist pass Twine and zero-runtime-dependency metadata checks; Python 3.12 wheel and Python 3.14 source-distribution smoke installs pass. The subsequent real OCR reviews supplied the remaining non-zero-use evidence for item 8.
10. [x] Audit the complete pre-M1 repository-context pipeline from the merge-base and repository history, then run legacy/evidence semantic parity cycles, component-level MCP verification, and a full synthetic GitLab-style OCR v1.8.0 E2E without posting. The history-backed coverage matrix maps every legacy source and contract to typed evidence or an explicit removal. The temporary oracle matched all 11 non-empty comparable dependency/image facts with none missing. The completed public `ocr-ci review` release gate reviewed one synthetic source change, recorded one `ocr_toolkit_evidence` call in both OCR counters and the toolkit receipt, and kept private `.review-context` artifacts outside Git. The real-engine synthetic E2E remains a manual release gate: stable automated coverage stays at component, clean-install subprocess, real protocol-client, and artifact-boundary layers unless repeated releases justify a permanent local HTTPS/LLM harness.
11. [x] Remove the legacy implementation, CLI, environment contract, and compatibility path after the new path passes all gates. Signed checkpoint `c2caa9d` removed the renderer, CLI/environment surface, compatibility assertions, and temporary parity code only after the migration matrix and non-empty history-backed oracle passed; the final integration suite asserts that the retired contract is absent.
12. [x] Reconcile user, agent, engineering, security, configuration, roadmap, plan, and backlog documentation.
13. [x] Run complete validation, review the full feature diff with OCR through the new local MCP, fix valid findings, create and verify the final signed checkpoint, and finish the local ready-PR audit.
14. [x] Add and run an explicit local pre-push Gitleaks gate that uses the same explicitly pinned scanner version, configuration, and first-parent branch-history scope as CI, and record the missed-gate failure mode in contributor and agent guidance. The wrapper is the single pin owner, exposes a side-effect-free `--version` for the hosted security job, and remains separate from the Python quality environment. TestPyPI and stable-release workflows do not duplicate the dedicated security job. The exact Gitleaks 8.24.3 binary was checksum-verified from its upstream release before installation; the local first-parent feature-history scan and focused shell/contracts tests pass.
15. [x] Update the ready feature PR without prematurely closing issue #30, verify its exact current head, required review, resolved conversations, and Actions state, and merge through the protected `main` branch. PR #31 kept issue #30 open, all current-head required checks passed, no review conversations remained, and GitHub created verified signed squash commit `53f559ab2db4918d990575063c836ae99ee871b2` on `main`. The active ruleset's obsolete Python 3.10 required contexts were corrected to the implemented Python 3.12 endpoints before merge.
    - The first `main` development-build attempt exposed a gate-integration omission: `scripts/quality.sh check` correctly failed closed because the hosted TestPyPI job had not provisioned the newly required scanner. The correction adds one checksum-verified Linux installer shared by the TestPyPI and stable-release workflows, with focused success-path and workflow-contract regressions; it will be delivered through the normal protected hotfix PR before retrying publication.
16. [x] Verify the resulting immutable TestPyPI development build and independently smoke-install its wheel and source distribution. TestPyPI workflow run 30614810741 published and read back `0.3.1.dev24` from exact signed `main` SHA `0396dd200e6097e2a650a2ce07c5236bcd8ff33f`; the run artifact and registry wheel/sdist SHA-256 values matched byte-for-byte, metadata retained `Requires-Python >=3.12,<3.15` with zero runtime dependencies, and independent clean installs passed for the wheel on Python 3.12 and sdist on Python 3.14.
17. [x] Prepare a signed `release/v0.4.0` branch and exact-title release PR with the stable version marker, deterministic source epoch, generated Towncrier changelog, and next development line. The branch starts at exact `origin/main` SHA `0396dd200e6097e2a650a2ce07c5236bcd8ff33f`; its deterministic source epoch is `1785484860`, and the stable and next development lines are both 0.4.0. The pre-commit release checkpoint passes the explicit first-parent Gitleaks gate and the complete Python 3.12 matrix: 480 tests plus 35 subtests, 79.04% coverage, Ruff formatting/checks, strict mypy, and Bandit. Two independent deterministic builds produce byte-identical artifacts (`665ba25e375cb91df1815c2a7d27dda6605872121b8f5bfd76a08495ae8e7f15` wheel, `9c7bd39e7fc613ba3686a31c7d0afbdedb30297c2c1bb7da74f213c9f8eada8b` sdist); Twine, exact metadata/content, zero runtime dependencies, Python 3.12.13 wheel, Python 3.14.6 sdist, runtime version, and CLI smoke checks pass. Signed checkpoint `8f7b72e15991fc09c0f9251c5dad3352f992d2cc` and exact-title release PR #33 complete the item.
18. [x] Verify and merge the protected release PR, then monitor stable TestPyPI and PyPI publication, the annotated `v0.4.0` tag, immutable GitHub Release, attestations/provenance, and exact artifact hashes. All exact-head checks passed before PR #33 merged as GitHub-signed commit `251315dda9e025ad0ca76dd28011e6c85903aa9c`. Release workflow run `30617233026` completed every authorize, build, attestation, TestPyPI, PyPI, registry-smoke, and GitHub Release job. Both registries and Release assets expose the reviewed hashes, `gh attestation verify` accepts both distributions, the annotated tag resolves to the merge commit, and GitHub API version `2026-03-10` reports `immutable: true`.
19. [x] Independently smoke-install the published wheel on Python 3.12 and source distribution on Python 3.14, close issue #30, reconcile M1 as established across the plan, roadmap table/diagram, and backlog, and verify the final external state. Files downloaded directly from PyPI match the reviewed hashes and pass runtime-version plus CLI smoke checks on Python 3.12.13 and 3.14.6; issue #30 is closed. The final planning-only closure change removes only completed BL-004 through BL-007 and promotes M1 consistently in the roadmap table and diagram.

   - Closure-documentation checkpoint: the history-backed parity/removal and public-invocation synthetic E2E gates are now reconciled across this plan, the roadmap completion signal, and the active BL-004 through BL-007 scope. User operations guidance now documents the H1 summary, distinct skipped/clean outcomes, positive clean report, zero-counter omission, used-MCP inventory, and the default-on emoji switch. The complete quality gate passes formatting, lint, strict typing, Bandit, 453 tests plus 35 subtests, and 78.31% coverage. The final OCR/security results and ready-PR state recorded below subsequently closed item 12.
   - The first completed full OCR review covered 42 files, made 423 core tool calls including 165 verified `ocr_toolkit_evidence` calls, and returned 31 findings (10 high, 20 medium, 1 low). Root-cause analysis grouped them into post-hoc rather than streaming bounds, byte/code-point confusion, incomplete hostile-environment isolation, validate-on-write without validate-on-read, canonical-only parser fixtures, non-atomic cross-references, mocked rather than installed subprocess contracts, and drift between report outcomes. Durable principles, agent defaults, failure-mode corrections, and the contributor boundary checklist were updated before the findings were corrected and the full OCR review was repeated.
   - The second completed full OCR review covered 69 files, made 549 core tool calls including 220 verified `ocr_toolkit_evidence` calls, and returned 35 findings. Corrections are grouped by root-cause class: sibling trust boundaries, NUL-safe Git records, applicability-aware identities, semantic parser variants, exact negative-test paths, and hermetic synthetic Git repositories. Per owner direction, a third local OCR review is intentionally not run; ordinary quality/build matrices and Codex Security remain the independent final gates.
   - The second-OCR correction implementation now passes the complete Python 3.12 quality gate: formatting, Ruff, strict mypy, Bandit, 472 tests plus 35 subtests, and 78.54% coverage. Fresh wheel and sdist artifacts pass Twine, hash-locked isolated installs, zero-runtime-dependency metadata checks, and restricted-`PATH` `ocr-ci --help` smoke tests on Python 3.12. Per owner direction this correction checkpoint does not repeat the already completed 3.13/3.14 M1 qualification.
   - Codex Security diff review of the complete M1 merge-base-to-checkpoint range validated two root-cause classes. Repository replacement refs could substitute content behind authenticated SHAs in both evidence collection and GitLab remap helpers; the existing OCR config reader also captured an unbounded linked file before JSON parsing. The correction disables replacement objects, isolates process/global/system Git configuration for both sibling readers, bounds config reads/writes at one MiB through a regular single-link descriptor, and adds real replacement-ref, hostile-environment, oversized, UTF-8 path, and hard-link regressions. No third OCR review was run per owner direction. The post-security Python 3.12 quality/artifact gates and signed checkpoint recorded below subsequently closed item 12 and the non-PR portion of item 13; complete publication was later authorized and is tracked by items 15 through 19.
   - First OCR correction checkpoint: record and delta values are recursively immutable; deserialization rejects type-confused metadata and limits; and persisted record, delta, top-level diagnostic, and snapshot diagnostic payloads are re-redacted and re-bounded before MCP exposure. Adversarial mutation, secret, oversized-value, diagnostics, snapshot-reference, and metadata regressions pass in the 225-test/15-subtest evidence/review/docs gate with Ruff, formatting, strict mypy, and whitespace checks clean. A corrected process-level cProfile workload validates 200 real `summary`/`list`/`get` cycles (600 tool calls, 603 responses, zero errors) over the 340-record review store: wall time under profiling is 0.964 seconds, strict cold read accounts for 0.829 seconds, and an unprofiled run measures 0.210 seconds cold read plus 0.090 ms per steady-state call. The previous 0.596-second profile is retained only as a transport/error-dispatch baseline because its request generator omitted `action`; it is not evidence for successful tool semantics. Remaining OCR findings stay open.
   - Second OCR correction checkpoint: all parser-semantic findings now have direct regressions for Ansible indentation and Galaxy key order/scalar sources, standard and named `pylock` manifests, Composer malformed optional repository URLs and disabled platform entries, quoted Go tokens, infrastructure digest fields and plain variables, npm v1 traversal coverage, Poetry interpreter declarations, and stable list-valued alternatives. Boundary regressions additionally cover atomic snapshot admission, hard-linked artifacts, notification response suppression, streaming MCP request limits, inert bootstrap diagnostics, hostile Git object-store/replacement overrides, immutable OCR ref binding with non-diff option preservation, timeout normalization, short result reads, cyclic warning objects, consistent clean/skipped MCP reporting, and quick-action-safe fallback fences. Focused validation completed with 78 parser tests, 140 evidence/MCP/review-runner tests, and 100 posting tests plus 12 subtests. The complete quality gate passes 453 tests and 35 subtests at 78% coverage with Ruff, formatting, strict mypy, Bandit (zero medium/high findings), and `git diff --check` clean. The signed checkpoint is `fe8f62b`; its ED25519 signature is verified.
   - Post-checkpoint qualification reruns all 453 tests plus 35 subtests independently on Python 3.12.13, 3.13.4, and 3.14.6. Fresh wheel and sdist artifacts pass Twine and installed `ocr-ci --help` smoke tests under restricted `PATH` on Python 3.12 and 3.14 respectively. The public `ocr-ci review` flow then completes against a fresh synthetic repository and deterministic local HTTPS LLM gateway: evidence preflight binds the immutable base/head pair, creates four private records, OCR reviews exactly the intended source change, calls `ocr_toolkit_evidence` once, and the validated result records `tool_calls.total=1`, `tool_calls.by_tool.ocr_toolkit_evidence=1`, and `_ocr_toolkit.mcp_usage.ocr_toolkit_evidence=1`. The diff contains only the synthetic source file; `.review-context` remains outside Git and both internal artifacts are mode `0600` under a `0700` directory. The temporary localhost certificate/trust entry, gateway, repository, and OCR home are test-only and removed after evidence capture.

### Validation And Review Gates

- Every completed implementation slice receives a signed checkpoint commit after targeted tests, `scripts/quality.sh check`, `git diff --check`, and plan/backlog reconciliation.
- Python 3.12 is the minimum toolkit runtime for v0.4.0. This is an intentional release-required contract change rather than a bundled TOML backport: package metadata, Ruff/mypy targets, Linux/macOS endpoint CI, release smoke documentation, backlog version references, and clean wheel/sdist installation must agree on the supported 3.12-3.14 range. The recommended GitLab image remains `python:3.12-slim`; repository evidence may still describe any target project's Python constraints and is not limited to the toolkit's own runtime range.
- Review each committed diff for correctness, architecture, security, compatibility, tests, documentation, and hidden legacy dependencies. Fix every valid finding in a signed follow-up commit and repeat the gate before starting the next slice.
- Semantic parity compares facts, trust, ref, component, and provenance rather than exact Markdown. Any unexplained divergence starts another analysis, implementation, test, and review cycle.
- Legacy parity is history-backed rather than renderer-only: characterization fixtures and the temporary projection are checked against the context collectors and orchestration as they existed at the M1 merge-base, including their evolution where later commits fixed meaningful omissions. Similar prose or dependency counts alone are insufficient evidence of parity.
- Production collection is now typed-only: `ocr-ci review` no longer invokes the legacy renderer or persists `repository.context`. The legacy projection was attached only by an explicit migration-oracle helper used by parity tests before the parity gate closed. Immutable candidate blobs are size-checked and read in bounded Git batches (two `cat-file` processes per ref) rather than one process per file. Batch-check and response framing are adversarially validated; oversized candidates degrade individually with explicit coverage diagnostics, and YAML collection is restricted to changed or repository-context-relevant paths. History-backed migration coverage is tracked in `docs/engineering/evidence_migration_matrix.md`; resolving its partial/pending rows and removing the public legacy namespace closed BL-006.
- Typed evidence now owns deterministic multi-category changed-path classification and manifest discovery without importing the legacy context namespace. One immutable internal manifest registry owns path matching, ecosystem metadata, and bounded parser dispatch for every implemented ecosystem. Dependency/runtime identities include the immutable source path, while CI/container image identities separate component name from version so version updates produce one `changed` delta. Deleted-path categories retain base-ref provenance and target-repository trust.
- A separate bounded Ansible topology collector now describes root playbooks, canonical role metadata/defaults, inventory paths and immediate inventory groups from immutable blobs. Synthetic integration verifies that these records survive the common store and are queryable through filtered MCP `list` plus stable-ID `get`; generic root YAML and host/group variable payloads are not misclassified. Galaxy evidence distinguishes roles and collections, preserves redacted sources and explicit missing-version state, supports documented shorthand and bounded immutable include graphs, and diagnoses malformed, conflicting, missing, cyclic, escaping, depth-limited, and truncated input.
- Review-invocation evidence is isolated from immutable repository collectors: a GitLab provider adapter supplies only bounded numeric project/pipeline/job/MR identifiers to provider-neutral normalized descriptors with `invocation` trust. URLs, refs, tokens and arbitrary environment values are never read. Mutable locally installed tool versions remain intentionally excluded and are represented by an explicit toolkit-owned coverage diagnostic rather than an implicit context loss.
- Final validation includes unit, contract, adversarial, packaging, clean-install, protocol, subprocess MCP, source/head snapshot, failure-mode, and real OCR v1.8.0 E2E checks.
- Architecture correction implemented for the review boundary: evidence preparation, fixed internal artifact paths, compact-bootstrap injection, the BL-007 composition foundation, and bounded lifecycle diagnostics now belong to `ocr-ci review`. The public `OCR_EVIDENCE_STORE_PATH` contract and user-facing `evidence-build` workflow are removed; only the hidden lower-level stdio launch target remains for OCR, with toolkit-owned defaults. Collection uses the exact immutable OCR refs, completes before OCR starts, and fails closed on invalid refs, unsafe artifacts, collection, composition, or health-summary failures. The reserved built-in server is mandatory and authoritative; validated external MCP definitions compose alongside it and cannot shadow or remove it, including replacement mode.
- Bootstrap planning must describe the complete composed capability set available to OCR: always the built-in evidence tool plus only the explicitly allowlisted external MCP servers/tools that survive validation. It must not expose secrets, setup commands, URLs, headers, or stale OCR config entries. The generated MCP config and bootstrap therefore come from the same validated composition plan, preventing capability drift between instructions and the actual OCR tool loop.
- M1 implements only the provider-neutral composition foundation required for BL-007 correctness: reserved built-in server/tool names, deterministic augmentation by already-supported validated external definitions, and shared capability rendering. BL-013 remains in M3 for provider examples, external-reference instructions, threat-model-dependent integrations, and the broader composition product surface; M1 must not claim BL-013 complete or bypass BL-011/BL-012 dependencies.
- Real OCR v1.8.0 integration exposed three distinct fail-open boundaries that remained part of the gate rather than being hidden by handwritten mocks: OCR first treated the built-in server's prose `setup` value as a shell command; its exact Go SDK then required MCP revision `2025-11-25`; and a clean-start run showed that a bare `ocr-ci` registry command depended on the caller's `PATH`. Empty setup, protocol negotiation, and path-independent isolated launch were corrected and covered by editable plus clean-wheel adversarial subprocess checks. Both completed full OCR reviews later produced structured non-zero `ocr_toolkit_evidence` use.
- Corrected preflight/composition validation: 432 tests and 53 subtests pass with 75.13% coverage; Ruff formatting/checks, strict mypy, Bandit, build metadata, and repository contracts pass through `scripts/quality.sh check`. A real local automatic preflight for `origin/main..HEAD` created a `0700` internal directory and `0600` store/bootstrap, collected 134 records, wrote an empty built-in `setup`, and kept config/bootstrap capability inventories identical. A second preflight in replacement mode retained the mandatory built-in server and added a synthetic allowlisted external server in both outputs. The two subsequent full OCR reviews closed the real-use gate with 165 and 220 verified built-in MCP calls.
- Baseline before M1 runtime changes: 368 tests and 41 subtests passed. OCR v1.8.0 structured skip, clean result, subtask error, severity, and category contracts are pinned in synthetic fixtures sourced from upstream tag v1.8.0. Existing context regression coverage remains the legacy behavior baseline.
- BL-004 evidence model validation: 17 focused evidence/OCR contract tests pass; Ruff and mypy pass. Self-review added strict unknown-field rejection, mapping-key redaction, sensitivity promotion, and deduplication that supports structured JSON values. The v0.4.0 Towncrier draft was rendered successfully, and fragment authoring guidance now covers grouped related outcomes without using the changelog as a backlog.
- Snapshot/projection checkpoint validation: 26 focused evidence tests pass; Ruff and mypy pass. Synthetic two-commit repositories cover add, delete, both rename sides, changed blobs, unavailable commits, symlink refusal, tree/blob limits, semantic retention of the bounded legacy context, and explicit compact-bootstrap truncation. Self-review found that the transitional collector still calls `build_context()` and reparses Markdown; BL-005 and BL-006 therefore remain incomplete until typed collectors are projection-independent.
- MCP protocol checkpoint validation: 88 focused evidence, CLI, MCP-configuration, and runtime-helper tests plus 15 subtests pass; Ruff and strict mypy pass. The server protocol itself completes initialize, tools/list, summary, list, get, cursor binding, request/response bounds, and safe-error contracts over stdio, while generated private artifacts remain mode 0600 and existing parent-directory permissions are preserved. A direct local stdio handshake initially exposed the misclassified `setup`; the corrected integrated review lifecycle and later real OCR call receipts closed BL-007.
- Version ownership self-review: MCP server metadata now reads the installed package version from centralized `ocr_toolkit.__version__`, generated by `hatch-vcs` from SCM. The durable project principle forbids duplicated toolkit release literals and distinguishes release versions from independently versioned schema, wire-protocol, fixture, and qualified-upstream contracts.
- GitLab presentation checkpoint: posting summaries now use `# Open Code Review summary`, preserve the exact structured OCR v1.8.0 clean/skipped/warning/error message, suppress zero tool-call and posting counters, and render optional status, severity, and category emoji. `OCR_POST_EMOJI` is default-on and disables all toolkit-added emoji without rewriting OCR content. Focused posting validation passes with 97 tests and 24 subtests; the full suite passes with 417 tests and 53 subtests; Ruff and strict mypy pass.
- Typed collector checkpoint: immutable base/head collectors now parse Python, JavaScript/npm, Go, Composer, Ansible, container/CI image, project-guidance, and accepted-decision evidence directly from bounded Git blobs; typed facts no longer come from reparsing legacy Markdown. Semantic dependency/runtime/image deltas are explicit, malformed manifests degrade to bounded diagnostics, and changed head guidance cannot self-authorize policy. Focused collector/snapshot validation passes with 17 tests; the full suite passes with 422 tests and 53 subtests; Ruff and strict mypy pass. At this checkpoint legacy Markdown remained only as the temporary parity projection; the later parity and removal checkpoints closed BL-006.
- Public integration migration is corrected: the synthetic GitLab example calls one `ocr-ci review` lifecycle, which prepares its own private store/bootstrap, composes MCP configuration, reports bounded preflight diagnostics, and invokes OCR. It no longer exposes evidence paths, `OCR_EVIDENCE_STORE_PATH`, a separate `evidence-build`, manual built-in `mcp-config`, or caller-owned `--background-file`. The legacy context command remains physically present only until history-backed parity and integrated E2E pass.
- Semantic parity checkpoint: `ocr-ci evidence-parity` compares independently typed dependency/image records against the temporary legacy projection and fails when comparable coverage is absent or missing. The current branch report is clean with 11 comparable facts matched and none missing. Language documentation consistently keeps English as the default and presents Russian only as one localization example. The first full run exposed one stale documentation assertion; the test was corrected to enforce the intended default/example wording.
- Python checkpoint validation: 29 collector tests cover PEP 621/735, Poetry, recursive requirements, uv/Poetry/Pipenv/pylock facts, unsafe include modes, redaction, changed lock-version deltas, missing versus malformed locks, and built-in MCP visibility. `scripts/quality.sh check`, `uv lock --check`, wheel/sdist metadata checks, and isolated Python 3.12 wheel plus Python 3.14 sdist smoke installs pass.
- JavaScript checkpoint validation: focused tests cover scoped `package.json` declarations, runtime/package-manager constraints, aggregate bounds, npm lock v1-v3, Yarn Classic/Modern, pnpm v5-v9, malformed/unsupported contracts, redacted source classification, changed locked versions, and built-in MCP visibility. Read-only qualification against current upstream-generated Yarn Classic/Modern and pnpm v6/v7/v8/current locks produced bounded typed facts with explicit truncation notices. `scripts/quality.sh check`, wheel/sdist metadata checks, and isolated Python 3.12 wheel plus Python 3.14 sdist smoke installs pass.
- Go checkpoint validation: focused tests cover module identity, language/toolchain/GODEBUG declarations, direct and indirect requirements, module/local replacements, exclusions, tool/retract/ignore directives, aggregate bounds, module and go.mod checksums, safe malformed-line diagnostics, base/head changes, and built-in MCP visibility. Read-only qualification compares the parser output with `go mod edit -json` and checks real generated `go.sum` pairs. `scripts/quality.sh check`, wheel/sdist metadata checks, and isolated Python 3.12 wheel plus Python 3.14 sdist smoke installs pass.
- Planning reconciliation at the implementation checkpoint kept M1 `next` until release completion and retained BL-004 through BL-007 as active acceptance criteria linked to issue #30. The stable-release closure recorded above now promotes M1 and removes those completed entries without altering the historical checkpoint evidence.
- Codex Security reviewed the complete M1 runtime/package diff through signed checkpoint `9a58ccf`: all 42 deterministic worklist rows were closed and two validated findings were corrected. Authenticated Git reads now share one isolation policy that disables replacement objects and inherited process/global/system configuration across evidence and inline remapping, and OCR configuration reads reject links and oversized payloads before bounded JSON decoding. The final Python 3.12.13 gate passes with 477 tests, 35 subtests, 79% line coverage, Ruff, strict mypy, and no Bandit medium/high findings. Fresh wheel and sdist builds pass Twine, contain zero runtime dependencies, install from hash-locked local requirements into isolated Python 3.12 environments, and run `ocr-ci --help` under restricted `PATH` from a hostile shadow-package working directory. A third OCR review was intentionally not run.
- The final local implementation checkpoint was signed and verified. At that checkpoint the branch contained only signed commits, `git diff --check` was clean, the worktree had no project changes, no extra worktrees or validation/profiling processes remained, and disposable OCR/build/quality artifacts were removed. The owner then authorized and completed the full v0.4.0 delivery cycle recorded in items 15 through 19.

### Release Delivery And Closure

- The owner explicitly authorized the complete release cycle on 2026-07-30. Proceed through the feature PR, protected merge, immutable TestPyPI development verification, release PR, stable publication, tag/immutable GitHub Release, provenance/hash checks, and supported-Python smoke installs without stopping at intermediate checkpoints.
- The feature and release PR merges remain the repository's protected human publication gates; do not bypass required checks, resolved-conversation requirements, signed-commit policy, or the workflow's fail-closed registry verification.
- Stable publication and the closure sequence are complete, so M1 is `established` in the roadmap and this release-required plan is closed.

## Completed Plan: Reconcile completed M0 planning state

Status: completed; planning sources reconciled and M1 entry state verified
Owner: Codex
Last Updated: 2026-07-28
Release Classification: no-release
Target Stable Version: not applicable

### Goal

Make the roadmap and backlog consistently represent M0 as completed after the verified 0.3.0 release closure, without changing runtime or published behavior.

### Work Queue

1. [x] Reconcile the M0 execution plan, protected repository state, release, issue, and compatibility-workflow evidence.
2. [x] Audit the release-closure instructions and history to identify why publication receipts were reconciled without reconciling the roadmap and future-work backlog.
3. [x] Mark M0 unambiguously established in every roadmap representation, use a documented status color legend for all milestone nodes, and remove completed M0 implementation items from the future-work backlog.
4. [x] Correct stale completed-item retention in the remaining backlog; restore unimplemented BL-004 as the ready entry point for M1.
5. [x] Add a durable release-closure instruction requiring status-bearing roadmap diagrams, tables, backlog, and execution plans to be reconciled together.
6. [x] Review the resulting planning diff, render the Mermaid graph with Mermaid CLI 11.16.0, validate status/dependency references and repository whitespace, and record post-change truth.

### Release Gates

- This is a planning-state correction only: no runtime, CLI, configuration, schema, integration, or packaging behavior changes.
- No Towncrier fragment or stable release is required.
- Mermaid colors encode status only: established is green, next is blue, planned is neutral gray, and conditional is amber. Nodes with mixed phases use the earliest actionable status, while the label retains the detailed phase split.

### Closure Evidence

- Repository history shows the 0.3.0 closure PR updated only `PLANS.md`; it did not perform the promised post-release cleanup of `ROADMAP.md` and `docs/codex/TASKS_BACKLOG.md`.
- The M0 feature commit also marked BL-004 complete even though its evidence-model deliverables were not implemented; source inspection confirms the model remains the first M1 implementation slice, so BL-004 is restored as `ready`.
- Mermaid CLI 11.16.0 rendered the roadmap successfully with all seven milestone nodes colored according to the documented status legend: one established, two next, three planned, and one conditional.
- Targeted stale-state and dependency searches plus `git diff --check` pass. Public runtime, package contents, CLI/configuration contracts, and release artifacts are unchanged.

## Completed Plan: Qualify OCR 1.8.0, add native remote MCP, and release v0.3.1

Status: completed; stable release, development-line verification, and external reconciliation verified
Owner: Codex
Last Updated: 2026-07-28
Tracking Issue: #24
Qualification Issue: #23
Release Classification: release-required
Target Stable Version: 0.3.1

### Goal

Human-qualify OCR 1.8.0 from the successful M0 workflow evidence, promote it to the tested and recommended baseline, expose its native Streamable HTTP MCP transport through the existing bounded toolkit configuration contract, correct the durable OAuth backlog boundary, and carry the complete result through stable 0.3.1 publication and external reconciliation.

### Fixed Decisions

- Start from clean protected `main` merge `3ddbb4e`, which is synchronized with `origin/main` and records completed 0.3.0 publication.
- OCR compatibility workflow run `30344510383` passed every machine probe for v1.8.0 and classified it `human-review-required`; issue #23 is the human qualification record. Promote only after recording the reviewed upstream impact and normalized evidence.
- Of the OCR 1.8.0 changes, only native remote MCP changes a toolkit-owned integration contract. The remaining upstream changes receive a concise compatibility/release impact review and no artificial toolkit implementation or roadmap work.
- Extend `OCR_MCP_SERVERS_JSON` with explicit `stdio` and `remote` transports. Missing `type` remains `stdio`; stdio remains a supported local and OAuth-proxy fallback. Remote authentication in 0.3.1 is limited to environment-backed static headers.
- Preserve zero runtime dependencies, bounded parsing, fail-closed validation, redacted output, synthetic public content, and minimal wheel/sdist contents.
- Keep `scripts/quality.sh` isolated and quiet: repair only its disposable environment when interrupted editable metadata lacks `RECORD`, then synchronize once and run checks without repeated package mutation.
- Keep new runtime functions purpose-documented and comment non-obvious security, compatibility, and state-transition decisions; record this durable expectation in `AGENTS.md`.
- Do not push or open the feature PR until implementation, full validation, multiple self-review/fix cycles, and exactly one final complete local OCR 1.8.0 review of `main..HEAD` are finished. Fix every actionable OCR finding and rerun deterministic validation without a second OCR review.

### Work Queue

1. [x] Reconcile current repository and external qualification state, close the stale M0 plan checkbox, create tracking issue #24, and branch from synchronized protected `main`.
2. [x] Promote OCR 1.8.0 in the compatibility manifest and all durable version/checksum pins using normalized workflow evidence and a recorded human conclusion; document why non-MCP upstream changes require no toolkit code.
3. [x] Add bounded native remote MCP parsing and OCR config projection with HTTPS-only URLs, environment-backed secret headers, sensitive-literal rejection, transport field separation, redaction, and backward-compatible stdio behavior.
4. [x] Update public configuration/security/compatibility documentation, synthetic examples, durable strategy/backlog boundaries, project-agent upstream-impact instructions, and Towncrier fragments. Reconcile the documented `OCR_MCP_REPLACE` behavior with runtime truth.
5. [x] Add positive, negative, adversarial, documentation, manifest, workflow, quality-environment, and distribution-content tests while retaining zero runtime dependencies and minimal published artifacts.
6. [x] Run targeted checks, the complete local validation matrix, and three self-review/fix cycles covering architecture/compatibility, security/redaction, and documentation/packaging/release completeness.
7. [x] Run exactly one final local OCR 1.8.0 review over the complete feature diff, retain ignored evidence, fix every actionable finding, and rerun the deterministic validation matrix without another OCR review.
8. [x] Update plan/backlog to post-commit truth, create signed feature commits, push the branch, open the non-draft feature PR, resolve review feedback, pass all protected checks, merge, and verify the exact immutable TestPyPI development artifacts, provenance, and smoke installs.
9. [x] Create signed `release/v0.3.1` from refreshed `main`, render and verify Towncrier release notes, open the exact-title release PR, pass all gates, merge, and monitor stable TestPyPI/PyPI/tag/immutable GitHub Release publication.
10. [x] Reconcile registry, workflow, and GitHub hashes and provenance; smoke-install the wheel on Python 3.10 and hash-locked sdist on Python 3.14; close issues #23 and the tracking issue through a checked documentation-only closure PR.

### Release Gates

- Feature merge and TestPyPI development publication are intermediate checkpoints, not completion.
- Wheel contents remain limited to the runtime package and required metadata; repository qualification evidence, workflows, docs, examples, tests, plans, release tooling, and fragments remain excluded.
- Stable publication is blocked until OCR 1.8.0 is human-qualified, the final one-shot local OCR review is addressed, all protected checks pass, and the release PR is merged.
- Closure requires exact registry/GitHub/workflow hash equality, provenance verification, exact annotated tag target, immutable Release state, supported-Python smoke installs, external issue closure, and recorded receipts.

### Completed Checkpoints

- Repository started clean and synchronized at `3ddbb4e`; tracking issue #24 records the release objective and issue #23 records OCR qualification.
- Public ruleset `Protect main` now requires the M0 `sast-bandit` check in addition to the existing quality, platform, dependency, build, CodeQL, and security contexts; API readback confirmed the active rule on 2026-07-28.
- OCR 1.8.0 is recorded as tested and recommended from normalized run evidence; the changelog review found native remote MCP to be the only toolkit-owned contract change and moved managed OAuth lifecycle work to BL-012.
- Three self-review cycles fixed merge-vs-replace MCP semantics, private artifact race/permissions, remote field and control-character bounds, ruleset coverage, stale artifact-dependent tests, and repeated quality-environment mutation. The quality wrapper now repairs an interrupted missing-`RECORD` install only inside its disposable environment, syncs once, and runs all tools with `--no-sync`; its focused 366-test run is warning-free.
- The one permitted complete local OCR review used the checksum-verified OCR 1.8.0 Darwin arm64 binary and the toolkit's `ocr-ci review` path against a disposable index containing all 24 changed files. No GitLab command or credential was used. OCR returned success with six actionable findings; all were repaired: visible quality-sync failures, broader credential-header rejection, environment-secret and URL bounds, regular-file/hard-link/FIFO artifact validation, and same-inode output separation. Post-review deterministic validation passes with 368 tests plus 41 subtests, compatibility validation/discovery, lockfile, Towncrier draft, build/Twine, minimal artifact inspection, Python 3.10/3.14 wheel smoke installs, and `git diff --check`; no second OCR review was run.
- Feature PR #25 merged as protected-main squash `4513956` after every required CI, security, dependency, build, and CodeQL check passed with no review threads. TestPyPI workflow run `30350463053` then built, published, provenance-attested, hash-verified, and wheel/sdist smoke-installed immutable `0.3.0.dev18`. That version reflects the pre-release `.next-version` state inherited from 0.3.0; this release PR advances the stable authorization and next development line to 0.3.1.
- Release PR #26 merged as protected-main squash `035864d`; release workflow run `30351032061` published and verified the same bytes on TestPyPI and PyPI, then created annotated tag `v0.3.1` targeting that merge and an immutable GitHub Release. Wheel SHA-256 is `d37233e0f8736418f69b5a26fe1342dbed7b0c16a75962ce7f98200cfd9a71ee`; sdist SHA-256 is `aa403ec1b4bc052ae6d3a97980e81bc356e3513dd196cdb37f51488028c1452e`. Registry and GitHub hashes agree, both artifacts have release-workflow provenance bound to `035864d`, and fresh local smoke installs passed for the wheel on Python 3.10 and sdist on Python 3.14. Issue #23 is closed; closure of tracking issue #24 is carried by this documentation-only PR.
- Documentation closure PR #27 merged as `532b7a3`, closed issue #24, and passed every protected check. Its post-merge TestPyPI workflow run `30351569649` published, provenance-attested, hash-verified, and wheel/sdist smoke-installed `0.3.1.dev20`; all post-merge CI, Security, CodeQL, and OpenSSF runs also passed.

## Completed Plan: Complete M0 foundation and release v0.3.0

Status: completed; stable release and external reconciliation verified
Owner: Codex
Last Updated: 2026-07-27
Tracking Issue: #19
Release Classification: release-required
Target Stable Version: 0.3.0

### Goal

Complete roadmap milestone M0 as one production-quality feature: add a bounded Bandit repository gate, establish one versioned OCR compatibility manifest, automate checksum-verified evidence collection for unseen stable OCR releases without automatic upgrades, and carry the result through the full protected release path to stable 0.3.0 publication.

### Fixed Decisions

- Start from protected `main` merge `808a7f7`, which is the merged tree of PR #18 and has successful post-merge CI, Security, CodeQL, Scorecard, and TestPyPI development workflows.
- Deliver implementation through one `feature/m0-foundation` PR with coherent signed intermediate commits, then a separate `release/v0.3.0` PR. Do not push the feature branch or open its PR until iterative self-review, full local validation, and the single final local OCR review are complete.
- OCR 1.7.17 is the only tested and recommended baseline. Releases after 1.7.17 are classified by deterministic policy: a same-minor patch with unchanged consumed contracts may produce a bot-ready compatibility patch, while every ambiguous or material change remains an observed candidate requiring explicit human qualification.
- Candidate execution is Linux amd64; all published upstream assets and the checksum file are independently verified. The compatibility contract covers only toolkit-consumed CLI and JSON behavior and permits unknown additive upstream fields.
- The final OCR gate is one checksum-verified OCR 1.7.17 review of the complete `main..HEAD` feature diff. Any finding is fixed and locally revalidated before the feature branch is committed for PR handoff; OCR is not rerun.

### Work Queue

1. [x] Reconcile the checkout with merged PR #18, refresh `main`, verify a clean tree, and create tracking issue #19 and `feature/m0-foundation`.
2. [x] Add Bandit 1.9.4 as a development-only dependency; scan only `src/ocr_toolkit` at medium severity and confidence; document narrow B108 suppressions; expose the scan through `scripts/quality.sh security`; add a dedicated Security workflow job. The local gate and targeted tests pass; adding the new context to protected-main requirements remains a post-merge repository-admin checkpoint so the branch is not deadlocked before the workflow exists on `main`.
3. [x] Add a versioned OCR support manifest with 1.7.17 as the only tested/recommended baseline, all upstream asset metadata, deterministic machine evidence, human rationale, and cross-field validation.
4. [x] Add a standard-library-only qualification harness for bounded stable-release discovery, double-source checksum verification, Linux amd64 execution, synthetic CLI/preview/review contract probes, normalized evidence, conservative automatic-safe classification, and fail-closed behavior.
5. [x] Add scheduled/manual candidate qualification automation that emits an idempotent human-review issue for material/ambiguous candidates and a bot-ready patch artifact for strictly compatible same-minor patches. It never silently modifies `main`; a real PR is opened only when `OCR_UPDATE_BOT_TOKEN` is configured, otherwise the issue and artifact are the exact resume path.
6. [x] Update public security/development/compatibility documentation, roadmap/strategy/backlog state, and Towncrier fragments; add unit, contract, workflow, adversarial, documentation, and distribution-content tests. Published wheel/sdist contents are explicitly minimal and exclude all qualification and repository-only tooling.
7. [x] Complete multiple self-review and fix cycles covering architecture, security boundaries, workflow permissions/idempotency, test quality, documentation truth, and repository hygiene. Fixes include bounded pagination to the monitoring floor, sequential patch-only automatic classification, final asset redirect origin validation, optional bot identity validation, strict Mypy compatibility restored across the existing runtime, and minimal distribution composition.
8. [x] Run the complete local matrix: `scripts/quality.sh check` passes with 351 tests and 26 subtests at 73.54% branch coverage; Bandit gates pass; build/Twine and exact wheel/sdist smoke installs pass; `uv lock --check`, workflow/config contracts, public-content scan, Markdown target validation, official upstream discovery dry run, and `git diff --check` pass. The wheel contains 38 runtime/metadata entries; the sdist roots are only `src`, `README.md`, `LICENSE`, `pyproject.toml`, generated `PKG-INFO`, and Hatch's forced `.gitignore`.
9. [x] Complete the final local OCR 1.7.17 review over `main..HEAD` with project rules and prepared background, retain ignored local evidence, fix every actionable finding, and rerun deterministic validation without another OCR review. Initial session `d01fd4a6-82ce-4a58-8356-f26feea2eae1` failed all items before review because the external key returned `429`; after reset OCR refused resume because no file had completed, so replacement session `f568b93c-29f8-4bd9-81f8-5dca16c0f388` was required. It reviewed all 13 files, returned six medium findings and zero warnings, and all six were fixed: Mypy/Bandit table ownership, portable issue-number capture, idempotent bot branches, manifest/evidence asset equality, monitoring-floor bounds, and controlled missing `tool_calls`. The post-fix quality gate passes with 353 tests and 26 subtests at 73.54% branch coverage.
10. [x] Push the signed feature branch, open a non-draft PR, resolve review feedback, require all protected checks including Bandit, merge through protected `main`, and verify the resulting 0.3.0.devN TestPyPI artifacts, hashes, attestations, and smoke installs.
11. [x] Create signed `release/v0.3.0` from refreshed `main`, render and verify Towncrier release notes, set reproducible release authorization metadata, validate the exact release diff, open the release PR, and merge only after all protected checks pass.
12. [x] Monitor stable TestPyPI, PyPI, annotated tag, provenance, and immutable GitHub Release; independently reconcile all distribution hashes and smoke-install the wheel on Python 3.10 and hash-locked sdist on Python 3.14.
13. [x] Record exact external evidence in `PLANS.md`, merge the documentation-only closure PR #22, verify its checks, and only then compact the completed M0 plan.

### Completed Checkpoints

- Feature PR #20 passed every protected check, including the new `sast-bandit` job, and was squash-merged to protected `main` as `b23fcece393b52557ad7b66d2f57b6efe6b9cb3b` on 2026-07-28.
- TestPyPI development workflow run `30341458637` published and exact-hash verified `0.3.0.dev15`; wheel SHA-256 is `2869be43396a4b4df4d7c3a9098d48c8bd6f99960819b798480e4b6276ce9c26`, sdist SHA-256 is `47c54863cc580a2624ed9cd56e40e416bb71e3b0f606c49d751cd12945cbee76`, and registry JSON matches the reviewed workflow artifact. The workflow's provenance publication and exact wheel/sdist smoke verification succeeded.
- Release PR #21 passed every protected check and was squash-merged to protected `main` as `2e2cc835966f51cd378f46abfc15b0c625f4a7c6` on 2026-07-28. Release workflow run `30342158059` completed successfully.
- Stable TestPyPI and PyPI `0.3.0`, the reviewed workflow artifact, and immutable GitHub Release `v0.3.0` have identical distribution hashes: wheel `d752d18a8d7650e11e1a8066fab0b71e94f6d1625824112844de36a866e1def5`, sdist `ccd78c9262cc0aefcae0b13df982a015933896bc19428341c210f195bedc075f`. `artifact-hashes.json` and `SHA256SUMS` agree.
- GitHub provenance verification succeeds for both distributions. Annotated tag `v0.3.0` targets exact release merge `2e2cc835966f51cd378f46abfc15b0c625f4a7c6`; the release is non-draft, non-prerelease, and immutable.
- Independently reconciled artifacts install successfully: the wheel reports `0.3.0` and runs `ocr-ci --help` on Python 3.10; the hash-reviewed sdist reports `0.3.0` and runs `ocr-ci --help` on Python 3.14.

### Release Gates

- Feature merge and any TestPyPI `.devN` build are intermediate checkpoints, not completion.
- Wheel contents remain limited to the `ocr_toolkit` runtime package plus required distribution metadata; sdist contents remain limited to runtime source, readme, license, build/generated package metadata, and Hatch's automatically force-included `.gitignore`. Tests, examples, documentation trees, planning sources, release automation, compatibility qualification evidence, repository workflows, and changelog fragments are excluded from published distributions and checked by an explicit build-content contract.
- A stable release is blocked by any unseen upstream stable OCR release above 1.7.17 until it is either classified automatic-safe by the complete deterministic gate or receives human compatibility classification. Automatic-safe candidates still travel through a normal compatibility PR and a separate signed release PR; failures and ambiguity cannot auto-promote.
- Release closure requires registry/GitHub hash equality, GitHub artifact attestation verification, immutable non-draft release state, exact tag target, and supported-Python smoke installs.

## Completed Plan: Refine roadmap dependency and rollout safety

Status: completed
Owner: Codex
Last Updated: 2026-07-27
Release Classification: no-release
Release Decision: documentation correction only; retain the Towncrier fragment for the next planned release

### Goal

Correct dependency and rollout mistakes in the durable strategy, milestone roadmap, and regenerated backlog without implementing product features or publishing another package release. Separate current external MCP capabilities from future evidence MCP composition, preserve atomic bootstrap/MCP delivery, parallelize independent foundations, and replace speculative framework priorities with an evidence-based selection gate.

### Work Queue

1. [x] Reinspect current external MCP configuration, context rendering, strategy, roadmap, backlog dependencies, planning tests, and execution pitfalls against the architecture-review findings.
2. [x] Update strategy and roadmap to show parallel compatibility/evidence foundations, early external-reference security/current-MCP documentation, and late built-in/external MCP composition.
3. [x] Review all 22 backlog items and rewrite the dependency graph, rollout boundaries, selection gates, trust semantics, validation expectations, and activation triggers where repository evidence exposed omissions.
4. [x] Record the planning failure mode. Remove brittle planning-content tests instead of encoding mutable item counts, wording, or temporary dependency edges into the permanent product suite.
5. [x] Render and visually inspect the updated Mermaid roadmap, validate public-content hygiene, run `git diff --check`, and the complete quality gate.
6. [x] Perform architecture and rollout-safety self-review passes, correct findings, close this plan to post-change truth, and prepare a signed ready PR without auto-merge or a stable release.

### Root-cause Hypothesis

- The original backlog projected the desired end-state architecture into an overly linear implementation order.
- It did not distinguish existing external MCP primitives from future built-in evidence MCP composition.
- It separated implementation modules without preserving the user-safe release boundary between compact bootstrap and on-demand evidence.
- Framework priorities were inferred from current parser maturity rather than selected through a documented pilot-repository inventory.

### Backlog Review Findings

- OCR candidate qualification now enumerates every unseen stable release oldest-first, verifies API asset digests and checksum manifests before runner-platform execution, separates machine-tested from human-compatible/recommended states, and cannot mutate production contracts.
- Evidence foundations now cover schema evolution, trust/sensitivity, redaction before storage, source/target git edge cases, migration parity, MCP response/session budgets, lockfile variants, and mutable image-tag semantics.
- External MCP security and documentation use the current configurator; only reserved-name composition waits for built-in evidence MCP. Compact bootstrap and evidence MCP ship atomically with legacy rollback.
- Accepted decisions define duplicate/scope/expiry/authority behavior; guidance requires target-ref-aware upstream capability and nested precedence; framework plugins require anonymized inventory and scoring.
- Profiles define field-level precedence and capability validation; metrics are low-cardinality, privacy-bounded, opt-in, and non-fatal; routing preserves a repository minimum profile.
- Later file configuration rejects secrets and source self-authorization with explicit migration/rollback; host adapters require a capability matrix and explicit degradation; fuzzing chooses a backend through a bounded target-specific spike.
- The roadmap no longer blocks profiles and measurement on completion of every ecosystem, external MCP, and policy item.

### Validation and Review Record

- First review corrected current-vs-future MCP boundaries, independent compatibility/evidence foundations, atomic compact-bootstrap/evidence-MCP rollout, and framework selection based on anonymized inventory rather than parser familiarity.
- Second review covered every remaining backlog item and added missing semantics for release candidate qualification, evidence trust/schema/migration, git-ref edge cases, dependency and image evidence, decisions/guidance, profiles/metrics/routing, fuzzing, file configuration, and host adapter degradation.
- Removed `tests/test_project_strategy.py`: permanent tests tied to 22 temporary item IDs and exact prose would fail as completed backlog entries are removed and would make normal planning maintenance look like a product regression. Durable prevention now lives in explicit review guidance rather than brittle content assertions.
- The updated Mermaid roadmap renders successfully and remains readable without synthetic dates. Local Markdown link targets exist; public-content scans found no concrete OCR version pins, private infrastructure names, or credential markers in durable planning documents.
- `UV_CACHE_DIR=.quality-logs/uv-cache ./scripts/quality.sh check` passes with 332 tests and 26 subtests at 73.60% branch coverage. `git diff --check` is clean.

## Completed Plan: Publish stable 0.2.1

Status: completed
Owner: Codex
Last Updated: 2026-07-27
Release Classification: release-required
Target Stable Version: 0.2.1

### Goal

Publish the OCR compatibility update and durable strategy/roadmap documentation as stable `0.2.1` through the protected release-PR workflow, then independently verify registry, GitHub Release, hashes, attestations, and supported-Python installs.

### Work Queue

1. [x] Confirm PR #14 merged as signed squash commit `3a8a8c9`, all feature and post-merge checks passed, build artifacts exist, and TestPyPI development version `0.3.0.dev9` was published.
2. [x] Create `release/v0.2.1` from exact `origin/main` and confirm stable trusted-publisher environments, protected-main ruleset, and release workflow authorization contract remain configured.
3. [x] Set stable release metadata, assemble the 0.2.1 changelog from issue #12 and #13 fragments, and remove only those consumed fragments.
4. [x] Run complete quality, deterministic build, artifact metadata, wheel/sdist smoke-install, and release-contract validation; correct every finding.
5. [x] Commit and push the signed release branch, open `Release v0.2.1`, and merge only after every required check succeeds.
6. [x] Monitor production publication and independently reconcile stable TestPyPI/PyPI files, immutable GitHub Release assets, hashes, attestations, and Python 3.10/3.14 installs before closing this plan.

### Release Inputs

- Feature merge: `3a8a8c982fca5cc7b270bd1b0ce0085f514a3c13`.
- Development verification: TestPyPI `0.3.0.dev9` and retained workflow artifacts from successful post-merge automation.
- Stable changes: OCR compatibility target 1.7.17; durable strategy and milestone roadmap; regenerated 22-item backlog and canonical documentation links.
- Exact OCR versions remain only in operational compatibility surfaces, not durable strategy or roadmap.

### Pre-merge Validation Record

- `UV_CACHE_DIR=.quality-logs/uv-cache ./scripts/quality.sh check`: 338 tests and 26 subtests pass at 73.60% branch coverage.
- Two isolated `0.2.1` builds are byte-identical. Wheel SHA-256 is `46c8ef99f4cb6b62b22d5407474aa32e1c2e41b7fb02a08a880c1d4803893d4b`; sdist SHA-256 is `0fdde8b7f20221b6a04ff5a17a46c77d036866ecdf7a3e21d424561e8a49d0cd`.
- `twine check` passes for wheel and sdist; metadata reports version `0.2.1`, Python 3.10-3.14 classifiers, and no runtime dependencies.
- Python 3.10 installs the wheel and Python 3.14 builds/installs the hash-locked sdist; both report package version `0.2.1` and run `ocr-ci --help`.
- The release authorization helper accepts the exact repository-owned `release/v0.2.1` / `Release v0.2.1` contract. `git diff --check` is clean.

### Publication Record

- Release PR #15 passed every required CI, security, dependency, CodeQL, and build check and merged as signed squash commit `24a6ba6f3684acda6d6698f7a2269fa58f0cd28a`.
- Release workflow `30258933950` completed successfully: stable TestPyPI and PyPI publication, exact registry verification, build-provenance attestation, and GitHub Release publication all passed.
- TestPyPI, PyPI, and immutable GitHub Release `v0.2.1` contain the same wheel (`46c8ef99f4cb6b62b22d5407474aa32e1c2e41b7fb02a08a880c1d4803893d4b`) and sdist (`15d8eb5bd14d614d6c4aad3c3d801c2724451a8c2cb78e43a367c9fcedf4f607`). `SHA256SUMS` and `artifact-hashes.json` agree with those files.
- GitHub provenance verification succeeds for both published distributions. The annotated `v0.2.1` tag targets exact release merge `24a6ba6`; the release is non-draft, non-prerelease, and immutable.
- Independently downloaded PyPI artifacts install successfully: the wheel on Python 3.10 and hash-locked sdist on Python 3.14 both report `0.2.1` and run `ocr-ci --help`.

## Completed Plan: Establish durable strategy and roadmap

Status: completed
Owner: Codex
Last Updated: 2026-07-27
Release Classification: no-release
Release Line: included with the pending 0.2.1 compatibility work; no independent publication required

### Goal

Establish a durable product and architecture strategy, an outcome-oriented milestone roadmap, and a completely reconciled implementation backlog based on the repository's current behavior and compatibility policy. Keep the work documentation-only and make every future capability explicit as implemented, partial, planned, conditional, or rejected.

### Work Queue

1. [x] Inspect the canonical instructions, all execution plans, the existing backlog, public documentation, context and MCP implementation, preflight/configuration boundaries, GitLab normalization/posting code, tests, examples, and the latest official OCR release.
2. [x] Create the durable toolkit strategy and concise milestone/dependency roadmap, including rendered Mermaid component, data-flow, and roadmap diagrams.
3. [x] Regenerate the backlog as 22 coherent production-quality items and record an explicit disposition for native fuzzing, OpenSSF registration, additional code-hosting adapters, and file-based configuration.
4. [x] Update the canonical source index, concise README development section, Towncrier fragment, and documentation contract tests.
5. [x] Validate Markdown links and anchors, render Mermaid blocks, scan public documentation for private infrastructure or credentials, run focused tests, `git diff --check`, and the complete quality gate.
6. [x] Perform self-review, correct all findings, record post-change truth, close this plan, and prepare a separate signed documentation commit on `chore/ocr-1.7.17`.

### Established Decisions

- Use a Mermaid milestone dependency flowchart rather than a calendar Gantt; synthetic milestone identifiers express order without inventing deadlines.
- Place Bandit in M0 as high-priority repository maintenance, while keeping it outside the toolkit product architecture and outside this documentation-only implementation.
- Treat ecosystem/framework evidence and additional code-hosting adapters as separate concerns: the former describes reviewed repositories, while the latter changes the forge, CI, and publication adapter boundary.
- Preserve signed commit `c0630bf` as the OCR 1.7.17 compatibility change and add this work as a second commit without amending it.

### Completion Record

- Created `docs/engineering/toolkit_strategy.md` and `ROADMAP.md`; updated `AGENTS.md`, `README.md`, `docs/codex/TASKS_BACKLOG.md`, and this execution record; added issue #13 Towncrier documentation fragment and strategy contract tests.
- Regenerated 22 backlog items across M0-M6. Native fuzzing was retained and tied to parser attack surfaces; OpenSSF remained an owner action; provider adapters were clarified as code-hosting/review-host adapters; file configuration was deferred until profile/MCP/evidence schemas stabilize.
- Kept exact OCR versions out of durable strategy, roadmap, and backlog. The operational version remains in preflight, installation guidance, checksum-pinned examples, and compatibility tests where it is required.
- Rendered all three Mermaid blocks through Mermaid CLI and installed Chrome, producing readable temporary diagrams of 2860x796, 2368x398, and 3160x556 pixels. No generated image is tracked.
- Local Markdown links resolve; bounded checks of the public GitHub, PyPI, and OpenSSF links passed. Public planning documents contain no private infrastructure names, credential markers, or secrets.
- Strategy/release contract tests pass with 10 tests. The complete quality gate passes with 340 tests and 26 subtests at 73.73% branch coverage; `git diff --check` is clean. The final rerun used the repository-isolated `UV_CACHE_DIR=.quality-logs/uv-cache` because the sandbox cannot read the shared user uv cache.

## Closed Plan: Target Open Code Review 1.7.17

Status: closed; stable-release monitoring explicitly deferred by the owner
Owner: Codex
Last Updated: 2026-07-27
Release Classification: release-required
Target Stable Version: 0.2.1

### Goal

Update the locally installed Open Code Review binary and the toolkit's exact supported-version contract from 1.7.14 to 1.7.17, verify the upstream release notes and immutable asset checksums, and deliver the compatibility update through the complete protected release path.

### Work Queue

1. [x] Review the v1.7.15-v1.7.17 release notes and classify toolkit impact; retain the existing adapter and configuration contracts unless CLI/runtime verification proves a required change.
2. [x] Review the parked backlog for a coherent companion item. Keep native fuzzing, OpenSSF registration, additional provider adapters, and file-based configuration separate because each has an independent activation trigger or owner boundary.
3. [ ] Atomically replace the local darwin-arm64 OCR binary only after verifying the official v1.7.17 checksum manifest and release-asset digest. The candidate is verified and executable; replacing `~/.local/bin/ocr` was deferred after the approval service repeatedly returned HTTP 502.
4. [x] Update preflight, tests, public documentation, and the checksum-pinned linux-amd64 GitLab example to v1.7.17; add a Towncrier compatibility fragment linked to issue #12.
5. [x] Run focused compatibility checks, self-review, the complete quality gate, and release-contract validation; correct every finding before handoff.
6. [x] Prepare the validated feature branch for a signed commit, protected-main pull request, and owner-requested immediate merge without post-merge monitoring.
7. [ ] Verify the post-merge TestPyPI development build, prepare and merge `release/v0.2.1`, then reconcile stable TestPyPI/PyPI, tag, immutable GitHub Release, hashes, attestations, and Python 3.10/3.14 smoke installs. Explicitly deferred by the owner on 2026-07-27; resume by confirming the merged feature SHA and successful TestPyPI development build, then create `release/v0.2.1` from that `main`.

### Upstream Review

- v1.7.15 contains fixes relevant to CI review correctness: per-file comment work no longer races pool submissions, merge commits are reviewed against their first parent, binary diff markers are anchored correctly, and hand-edited `timeout_sec` survives config round-trips.
- v1.7.16 removes a hardcoded 180-second review-filter timeout and corrects reviewed-file accounting; its new provider and GraphQL support do not require toolkit changes.
- v1.7.17 adds OpenCode, Julia, and Rust-rule features and normalizes code-comment metadata enums. None changes the documented `ocr review`, configuration, or JSON result contract used by the toolkit according to the release notes; runtime verification remains required.
- The v1.7.17 official release records SHA-256 `d1771b962ae518bd0e75093b695633e1d12f80700521f5eb5872651b83595012` for darwin-arm64 and `ab2fae81796a00dda292def8261bec2203d03f3909673c08219e7c5df5f4feee` for linux-amd64.
- The downloaded darwin-arm64 candidate matches both the official checksum manifest and GitHub asset digest, reports `open-code-review v1.7.17 (0ced7165)`, preserves the toolkit-used `review` flags, and successfully previews a repository diff.
- Focused tests pass with 162 tests and 18 subtests. The complete quality gate passes with 332 tests and 26 subtests at 73.60% branch coverage; `git diff --check` is clean.
- The owner explicitly requested plan closure after feature merge and waived further monitoring. Stable `0.2.1` publication is therefore not claimed as complete; its exact resume action remains work item 7.

## Completed Plan: Publish stable 0.2.0

Status: completed
Owner: Codex
Last Updated: 2026-07-27

### Goal

Publish the incompatible reviewer-command contract, GitLab operations model, documented accepted-decision guidance, and OCR v1.7.14 compatibility target as stable `0.2.0`, using the already validated development artifact line and the protected release-PR automation.

### Work Queue

1. [x] Verify feature PR #8 merged into `main`, all post-merge workflows passed, and TestPyPI `0.2.0.dev7` was published and installed successfully.
2. [x] Prepare reproducible stable release metadata, consume the 0.2.0 Towncrier fragments, and move the following development line to `0.3.0.devN`.
3. [x] Run the complete quality, package, and release-contract validation gates; close implementation preparation to release-PR truth. A second security scan was explicitly waived because the feature branch already completed a full repository scan and this patch changes release metadata, generated changelog, tests, and process documentation only.
4. [x] Merge the registry-boundary fix through protected `main`, then recreate `release/v0.2.0` from that merge so the stable artifact necessarily contains the fix.
5. [x] Verify and document the retained `.opencodereview/accepted-decisions.md` contract, update the supported local and CI OCR version to v1.7.14, and regenerate the complete 0.2.0 changelog.
6. [x] Run the complete quality, package, release-contract, reproducibility, and Python 3.10/3.14 validation gates. The user explicitly waived another security scan for this release.
7. [x] Deliver a signed `release/v0.2.0` pull request. Its merge is the human authorization gate for TestPyPI `0.2.0`, production PyPI, tag, attestations, and immutable GitHub Release publication.
8. [x] After merge, monitor the complete release chain and independently verify registry/GitHub bytes, hashes, provenance, metadata, and Python 3.10/3.14 installs.

### Process Correction

- No repository instruction prohibited the stable release. The implementation mistake was closing the command-contract task after the feature PR and TestPyPI development build even though `0.2.0` had already been selected.
- `AGENTS.md` now makes stable publication or explicit deferral part of closure for incompatible public-contract changes.
- The stable artifact must be built from the release PR merge commit; no feature-branch artifact or TestPyPI development bytes are promoted in place.
- Release preparation uses stable version `0.2.0`, deterministic epoch `1784558537`, and next development line `0.3.0`. Two local builds were byte-identical; Twine, Python 3.10 wheel installation, Python 3.14 sdist installation, complete quality checks, and release-contract tests passed.
- First production run `29753514788` stopped before artifact upload or publication. Registry classification incorrectly treated legitimate `0.2.0.devN` TestPyPI files as conflicts for stable `0.2.0`; the boundary must accept other valid versions while still rejecting malformed filenames and duplicate/conflicting exact-version artifacts.
- The Ubuntu CI matrix is intentionally reduced to the supported endpoints, Python 3.10 and 3.14, matching macOS. The protected-main ruleset must remove the retired 3.11-3.13 job contexts in the same change so future PRs cannot wait for checks that no longer exist.
- PR #10 merged the registry-boundary fix into `main`. The first release branch is obsolete: the replacement `release/v0.2.0` is based on merge `39d8517`, so no recovery path can publish the pre-fix source.
- Accepted decisions remain implemented as bounded, sanitized project guidance. The public contract must explain the Markdown entry format, optional `ocr-accept` marker convention, prompt-level suppression semantics, and fail-closed omission when the decision file is changed by the current MR or changed-file discovery fails.
- OCR v1.7.14 is the compatibility target for this stable release. The local darwin-arm64 binary and public linux-amd64 example must use independently checked release-asset digests.
- The official v1.7.14 checksum manifest verified the example's linux-amd64 digest `f5ee3118...cc5f8b`; the local darwin-arm64 binary was atomically replaced only after verifying digest `48301e64...06929f6`, and reports `open-code-review v1.7.14 (870fc6a4)`.
- Accepted-decision support was not lost in extraction: the toolkit retained the earlier bounded reader, trusted-path check, Markdown sanitization/redaction, prompt section, and changed-file fail-closed guard. This release adds the missing user-facing contract instead of duplicating the feature or parking a false backlog item.
- The complete quality gate passes with 332 tests and 26 subtests at 73.60% branch coverage. Two stable builds were byte-identical, Twine accepted both distributions, the exact wheel/sdist set matched the release contract, and local smoke installs passed for the Python 3.10 wheel and Python 3.14 sdist.
- The only failed GitHub run was production release `29753514788`: it failed before upload because the old classifier mistook existing `0.2.0.devN` artifacts for malformed stable files. PR #10 fixed that boundary; every check on merge `39d8517` passed, including the reduced 3.10/3.14 matrix and verified `0.3.0.dev1` publication.
- Replacement release PR #11 merged as signed commit `11a526e`; TestPyPI and PyPI contain stable `0.2.0`, and immutable GitHub Release `v0.2.0` publishes the wheel, sdist, `SHA256SUMS`, and `artifact-hashes.json`.

## Completed Plan: Document and simplify GitLab discussion lifecycle

Status: completed
Owner: Codex
Last Updated: 2026-07-20

### Goal

Make repeated OCR reviews and GitLab discussion ownership understandable to developers and CI operators, replace ambiguous reviewer commands with an explicit pre-1.0 contract, and publish a complete operations guide grounded in the existing fail-closed posting behavior.

### Work Queue

1. [x] Replace `/ocr keep` and `/ocr skip` with `/ocr resolve` and `/ocr suppress`, remove legacy aliases, and preserve human-reply ownership and fingerprint suppression.
2. [x] Add focused lifecycle, command parsing, duplicate suppression, compatibility-removal, and documentation contract tests.
3. [x] Add `docs/operations.md` with a Mermaid state machine, rerun/deduplication semantics, posting modes, token permissions, limits, failure behavior, and operator-facing examples.
4. [x] Add a concise README overview, link the GitLab and configuration guides, and update the public GitLab CI example with recommended blocking-job defaults.
5. [x] Isolate `scripts/quality.sh` in its own ignored environment so routine checks never mutate or warn about a developer's shared `.venv`.
6. [x] Complete self-review, full validation, complete security scan, close the plan to post-change truth, and prepare a signed pull request for the 0.2.0 development line.

### Locked Decisions

- `/ocr resolve` preserves and suppresses the finding, then resolves the discussion after the next successful posting transaction.
- `/ocr suppress` preserves the discussion open and suppresses matching future findings.
- `/ocr keep` and `/ocr skip` are removed without aliases; their previous messages remain ordinary human replies and therefore retain the thread and exact-finding suppression without command-specific state changes.
- Any human reply still transfers the thread out of bot-only cleanup and suppresses findings matching its recorded inline position or compatible fingerprint.
- README remains concise; the complete operator model lives in `docs/operations.md`.
- `OCR_POST_MODE=draft` is the safe default; blocking review jobs should use `OCR_STRICT_POSTING=true`.
- Documentation targets both CI operators and developers who add or maintain the job. It does not add fork/protected-variable guidance, a connection-verification procedure, or a standalone troubleshooting section.

### Validation Record

- `scripts/quality.sh check` passes in its isolated `.quality-logs/venv` with 99.67% branch coverage and no shared-`.venv` uninstall warning.
- Focused lifecycle and documentation contracts pass alongside the complete test suite; all workflow/example YAML parses, shell syntax is valid, and `git diff --check` passes.
- Runtime dependency export is empty and `pip-audit` reports no known vulnerabilities. Secret-pattern review found only fixed synthetic redaction fixtures.
- A complete Codex Security repository scan reviewed all 68 inventoried runtime, workflow, release, test, example, package, security, and operator-documentation files, including the working tree, and finalized with zero reportable findings in 2 minutes 51 seconds.
- PR validation exposed that the ruleset-required `dependency-review` check still had pull-request path filters. The workflow now runs for every pull request so protected `main` never waits for a required check that GitHub did not create.
- The first Mermaid state diagram rendered poorly in GitHub because long transition labels and self-loops forced an excessively wide layout. It was replaced with a compact top-down decision flow and rendered locally before handoff.

## Completed Plan: Make non-release merges a clean release-workflow no-op

Status: completed
Owner: Codex
Last Updated: 2026-07-20

### Goal

Ensure the production release workflow distinguishes an ordinary merged pull request from a malformed release attempt before running strict release authorization, so normal merges do not create failed Actions runs while release-branch/title/version/commit validation remains fail-closed.

### Work Queue

1. [x] Reconcile every post-merge run for PR #6 and identify the only failure as `Release / authorize-release` rejecting the ordinary `hardening/scorecard-follow-up` branch.
2. [x] Add a read-only classification gate that selects only merged `release/v*` pull requests or explicit recovery dispatches for production authorization.
3. [x] Add contract tests for ordinary merge no-op, malformed release fail-closed, and unchanged authorized release behavior.
4. [x] Make the required `build-distributions` check unconditional for pull requests so path filtering cannot leave otherwise valid PRs permanently blocked.
5. [x] Repeat full validation and security diff review, close this plan, and prepare the signed pull request for merge.

### Current Evidence

- All six `main` push workflows for merge `5a0f754ede10834f703965946470bd04219ac379` succeeded: CI, build, Security, CodeQL, Scorecard, and TestPyPI development publication.
- TestPyPI published and independently verified `0.2.0.dev5`; the stable `0.1.0` PyPI and immutable GitHub Release artifacts remain unchanged.
- Scorecard closed all four `Pinned-Dependencies` alerts and now reports only six classified governance, age, historical coverage, fuzzing, and badge signals.
- The sole post-merge failure is run `29740626723`, triggered by `pull_request.closed`; strict authorization treated an ordinary merge as a release attempt and raised `release pull request branch must start with release/v`.
- The six remaining Code Scanning entries are current Scorecard posture signals, not failed jobs or CodeQL vulnerabilities: Fuzzing, SAST history coverage, OpenSSF Best Practices registration, repository age, external code review, and maximal multi-maintainer branch protection. They must not be dismissed or cosmetically suppressed.
- Targeted release contracts (24 tests), the complete quality suite, workflow YAML parsing, and `git diff --check` pass. Codex Security reviewed all five changed files in full and finalized a complete diff report with zero reportable findings.
- PR #7 exposed a second workflow-contract issue: `build-distributions` is required by the `main` ruleset but its pull-request trigger had path filters, so a release-workflow-only patch produced no required check and remained blocked despite every started check passing. The required PR build is now unconditional; optional `main` push builds retain their path filter.
- The repeated complete security diff review covers all six changed files and reports zero findings; targeted contracts, the full quality suite, workflow parsing, and diff checks remain green.

## Completed Plan: Release 0.1.0 and remediate public security findings

Status: completed
Owner: Codex
Last Updated: 2026-07-20

### Goal

Recover the authorized 0.1.0 release after the TestPyPI Trusted Publisher rejected the first OIDC exchange, finish the exact-artifact TestPyPI-to-PyPI-to-GitHub publication chain, and then address the actionable OpenSSF Scorecard findings without weakening the single-maintainer release controls.

### Work Queue

1. [x] Confirm that the failed run stopped before external publication and preserved the reviewed artifact set.
2. [x] Correct and read back the TestPyPI Trusted Publisher for `release.yml` and `testpypi-public-disclosure`.
3. [x] Rerun the failed release jobs and monitor TestPyPI, PyPI, tag, attestations, and immutable GitHub Release publication through independent byte and install verification.
4. [x] Classify every open Scorecard alert as actionable, historical, temporal, or an intentional single-maintainer tradeoff.
5. [x] Fix repository-owned workflow and hardening findings, add focused regressions and documentation, and preserve required signed commits and protected-main checks.
6. [x] Run the complete validation matrix and a security diff review, close this plan to post-change truth, and prepare the follow-up for delivery through a signed pull request.

### Locked Decisions

- 2026-07-20: The merge of release PR #5 is the sole human authorization gate; recovery may only publish version 0.1.0 from merge commit `96d6d33d2faa1d664b41f4b19d3498a7bb148d72`.
- 2026-07-20: The first failed release run published nothing. Recovery must reuse the workflow's deterministic build contract and accept existing registry state only when exact filenames and SHA-256 values match.
- 2026-07-20: Scorecard findings are not assumed to be code vulnerabilities. Repository-owned CI findings will be fixed, while historical, age-based, and incompatible multi-reviewer expectations will be documented rather than misrepresented.
- 2026-07-20: No API tokens or long-lived publication secrets will be introduced; TestPyPI and PyPI remain OIDC Trusted Publisher integrations.

### Validation Evidence

- Release run `29738037085` completed authorization, quality, dependency audit, secret scan, deterministic build, Twine, exact version/hash checks, provenance attestation, and artifact upload before TestPyPI rejected the OIDC publisher identity.
- Release run `29738037085` attempt 2 succeeded end to end. TestPyPI and PyPI expose the exact same wheel (`ad2ddac2...d6016`) and sdist (`34400866...8ce9`) bytes; the immutable GitHub Release `v0.1.0` exposes the same assets and checksum manifest, and GitHub provenance verifies against `release.yml`.
- Independent Python 3.10 wheel and Python 3.14 sdist installs passed with package version `0.1.0` and `Requires-Python: >=3.10,<3.15`. The GitHub Release is immutable and its annotated tag resolves to the authorized merge `96d6d33d2faa1d664b41f4b19d3498a7bb148d72`.
- All ten open code-scanning alerts are OpenSSF Scorecard findings; Dependabot and secret-scanning have no open alerts, and CodeQL reported no source vulnerability. Four actionable Pinned-Dependencies alerts are scanner-visible sdist smoke installs. Branch-Protection and Code-Review reflect the documented single-maintainer model; Maintained is age-gated; SAST is historical coverage while CodeQL is already required; CII Best Practices needs truthful owner registration; fuzzing needs a separately designed native integration rather than a cosmetic workflow.
- `scripts/quality.sh check`, targeted workflow tests, a real hash-locked sdist install, YAML parsing, shell syntax checks, `git diff --check`, and OpenSSF Scorecard v5.5.0 `Pinned-Dependencies` analysis all pass; the local Scorecard result is 10/10 for dependency pinning. The first CI attempt exposed that `pip --require-hashes` also requires an explicit digest for a local path, so the final implementation generates a one-artifact requirements file from the just-read SHA-256 before installation.
- Codex Security reviewed all ten changed files in full and finalized a complete working-tree diff report with zero reportable findings. The generated report is outside the repository under the system temporary Codex Security scan directory.
- The signed follow-up pull request is the remaining delivery operation, not unfinished implementation or validation.

## Completed Plan: Public release 0.1.0 preparation

Status: completed
Owner: Codex
Last Updated: 2026-07-20

### Goal

Publish the first stable public toolkit release as one reproducible artifact set across TestPyPI, PyPI, and an immutable GitHub Release; update the supported Open Code Review CLI to 1.7.13; and establish a protected public trunk with deterministic `0.2.0.devN` TestPyPI builds after future merges.

### Work Queue

1. [x] Update the local OCR binary and toolkit contract to the verified 1.7.13 release.
2. [x] Replace private alpha and PAT-based release preparation with public trunk development builds and a local release-PR flow.
3. [x] Make the stable workflow reproducible and idempotent across TestPyPI, PyPI, Git tagging, attestations, and GitHub Release publication.
4. [x] Generate the 0.1.0 changelog, stable package metadata, release notes, documentation, and checksum-pinned public example.
5. [x] Enable and validate the GitHub protections and security features unlocked by public visibility.
6. [x] Complete iterative self-review, full quality/build/package checks, and a diff-scoped Codex Security scan; repair every actionable result.
7. [x] Close this plan to post-change truth and prepare the release branch for commit, pull request, required-check monitoring, and the single squash-merge gate.
8. [ ] After the owner merges the release PR, verify exact 0.1.0 bytes on TestPyPI, PyPI, and GitHub, plus tag, attestations, independent installs, and the next 0.2.0.devN build.

### Locked Decisions

- The repository is public and remains public throughout release publication.
- The owner-configured TestPyPI and PyPI Trusted Publishers are the only registry credentials; no API token or release PAT is stored in GitHub.
- Feature work remains trunk-based through pull requests into protected `main`; no persistent `develop` branch is introduced.
- Every non-release merge to `main` publishes one idempotent `0.2.0.dev<GITHUB_RUN_NUMBER>` development build to TestPyPI.
- Squash-merging the exact `release/v0.1.0` pull request is the only human publication gate. The external publication chain then runs automatically and fails closed.
- TestPyPI, PyPI, and GitHub Release receive the same reviewed wheel and sdist bytes; an existing partial or hash-conflicting release is never overwritten.
- GitHub distribution consists of release assets, checksums, and provenance attestations. GitHub Packages is not used because it does not provide a Python package registry.
- At the v0.1.0 release checkpoint, runtime dependencies remained empty and supported Python was 3.10 through 3.14; M1 raises the v0.4 floor to Python 3.12.

### Validation Record

- Local OCR was atomically replaced with the official darwin-arm64 v1.7.13 binary after SHA-256 verification; `ocr --version` reports commit `a4a281c1`.
- `scripts/quality.sh check` passed on the final staged diff: 312 tests and 26 subtests with 73.37% branch coverage, plus Ruff formatting/lint and strict mypy.
- The complete test suite passed independently on Python 3.10.20 and 3.14.6 with 312 tests and 26 subtests on each interpreter.
- `pip-audit --skip-editable`, Gitleaks v8.30.1 over all history and the staged diff, Zizmor v1.27.0, YAML parsing, shell syntax, `uv lock --check`, and `git diff --check` passed.
- Two independent exact `0.1.0` builds were byte-identical. Twine, metadata, archive-content inspection, wheel install, and sdist install passed. Reviewed SHA-256 values are `ad2ddac2fe39bc204a1ea5f80340a126faee96797de97e8505c18b2acb7d6016` for the wheel and `912923a8cedee8a2a4de103b1b490120212b1d0bad49e35b9d5718b205886386` for the sdist.
- Codex Security diff scan completed with 39 of 39 staged files covered. One low-severity immutable-release rerun finding was remediated; validation and attack-path analysis leave zero open findings and zero deferred work.
- Public GitHub readback confirms the active `main` ruleset, immutable releases, private vulnerability reporting, secret scanning with push protection, Dependabot security updates, and protected-branch policies on both publication environments. CodeQL and OpenSSF Scorecard completed successfully after public disclosure.
- Pull-request readback exposed that the distribution build previously ran only after pushes to `main`; the build workflow now runs as a bounded `build-distributions` pull-request gate with non-isolated builds and no-dependency smoke installs. Its follow-up contract tests, YAML parse, Ruff, Zizmor, Gitleaks, and diff review passed.
- Owner-configured TestPyPI and PyPI Trusted Publishers remain the only publication credentials. Registry publication, tag creation, GitHub Release publication, attestations, and independent external installs are intentionally pending the owner squash-merge gate.

## Completed Plan: Initial standalone toolkit extraction

Status: completed
Owner: Codex
Last Updated: 2026-07-17

### Goal

Create the first production-quality standalone Open Code Review Toolkit repository: extract the existing CI helper behavior into the `ocr_toolkit` package, expose a unified `ocr-ci` CLI, publish only synthetic public material, add packaging and automation, validate the complete deliverable, and create a clean initial commit only after all gates pass.

### Requested Scope

- Preserve parity for rendering safety, redaction, runtime and MCP configuration, preflight, context generation, repository and manifest inspection, guidance extraction, categorization, reusable Ansible context, GitLab posting, payload normalization, markers, fingerprints, snapshots, rollback, and ownership boundaries.
- Provide `ocr-ci preflight`, `configure`, `mcp-config`, `context`, and `post`.
- Add a PEP 621/Hatchling/hatch-vcs package, uv lockfile, Ruff, strict mypy, pytest, coverage, build and security tooling.
- Add English public documentation, synthetic GitLab examples, pinned GitHub Actions, Dependabot, changelog fragments, and gated OIDC release automation.
- Validate privacy and source-repository immutability before the initial commit.
- External account setup and public disclosure remain paused until explicit owner actions.

### Constraints

- The extraction source is read-only; never edit, stage, commit, switch branches, or inspect its untracked private test material.
- Do not copy local paths, private identities, private infrastructure, or the one-time private audit criteria into tracked files.
- Do not bundle or download the OCR binary in the Python package.
- Runtime configuration remains environment-only in v0.1.
- Posting accepts only `GITLAB_API_TOKEN`; remove all legacy fallback variables and messages.
- Do not provide the old package namespace or `python -m` compatibility contract.
- Runtime targets Python 3.10 through 3.13 on Linux and macOS.
- Keep the task specification local-only through `.git/info/exclude`.
- Multi-agent execution is disabled for this repository.

### Inputs

- Local extraction material kept outside version control.
- Tracked runtime and test sources from the read-only source repository at commit `b770f6e66b504a675ba7f594b55f4b156b8a2a53`.
- Tracked rules and design documentation listed by the extraction specification.
- `engineering-workflow` v0.4.0 scaffold and validation guidance.

### Completed Baseline State

- [x] Target directory exists and is initialized as a Git repository on `main`.
- [x] Multi-agent support is disabled by project-local Codex configuration.
- [x] Local extraction material is ignored and absent from Git status.
- [x] Source repository branch, commit, tracked candidate list, and pre-existing untracked paths were recorded without opening private untracked content.
- [x] Source baseline in the specification records 252 passing tests and standard-library-only runtime code.
- [x] Engineering-workflow audit classified the target as a minimal repository.

### Current Work Queue

1. [x] Bootstrap the canonical workflow documentation for this repository.
2. [x] Extract tracked runtime/tests, rename imports to `ocr_toolkit`, and remove all legacy environment aliases.
3. [x] Implement and test the unified `ocr-ci` parser and required subcommands.
4. [x] Add packaging, quality tooling, changelog infrastructure, and a reproducible lockfile.
5. [x] Rewrite public documentation and add synthetic GitLab fixtures/examples.
6. [x] Add pinned CI, build, security, dependency review, Scorecard, Dependabot, provenance, and OIDC release workflows.
7. [x] Run tests, coverage, Ruff, strict mypy, build/twine/install/CLI smoke checks, workflow checks, and generic secret scanning.
8. [x] Run the one-time public-safety/privacy audit and verify the source repository is unchanged.
9. [x] Update this plan to final truth and prepare the clean initial import commit after every available gate passed.

### Locked Decisions

- 2026-07-17: Distribution and repository name are `open-code-review-toolkit`; import namespace is `ocr_toolkit`; CLI is `ocr-ci`.
- 2026-07-17: Provider-neutral core with GitLab as the first adapter; Ansible support remains a reusable context feature.
- 2026-07-17: Apache-2.0, Hatchling, hatch-vcs, src layout, standard-library-only runtime, and SCM-derived versions.
- 2026-07-17: Public API and schema are provisional before 1.0 but every 0.1.x user-visible change requires a changelog fragment.
- 2026-07-17: External GitHub/PyPI setup and public visibility are not attempted until their explicit approval gates.

### Verification

- Adapted pytest suite and measured 70% coverage threshold.
- `ruff check`, `ruff format --check`, and strict `mypy` over `src/ocr_toolkit`.
- Build wheel and sdist, `twine check`, and isolated install smoke for both artifacts.
- CLI smoke for all required subcommands.
- Synthetic GitLab API posting tests.
- Generic secret scan plus one-time external privacy/public-safety audit.
- GitHub workflow/action pin audit and YAML parse.
- `git diff --check`, ignored-task verification, clean source-repository status comparison, and final target status review.

### Latest Validation Results

- Local extraction material is ignored outside tracked repository content.
- Engineering workflow audit: minimal repository; no prompt-injection warnings.
- Source read-only inventory: expected tracked candidates present; only the known private untracked paths were reported and not inspected.
- `engineering-workflow` scaffold and read-only validator applied; canonical workflow files are present.
- 258 adapted tests pass; measured branch coverage is 72.51% against the 70% gate.
- Private GitHub repository created; Actions default to read-only tokens, SHA pinning is enforced, allowed Actions are restricted, Dependabot alerts/security fixes are enabled, and TestPyPI/PyPI environments exist.
- GitHub Free rejected branch protection, rulesets, secret-scanning push protection, and environment approval rules for this private repository. These remain owner gates: upgrade the plan or make the repository public only after the privacy/license checkpoint, then enable them before any release.
- No repository credential values were invented or copied from another project. OIDC publication needs no PyPI token, and stable release pull requests are prepared locally without a long-lived GitHub credential.
- Pre-commit security review is in progress using the diff-scoped Codex Security workflow in single-agent mode, followed by a final engineering review.
- Focused security review found and fixed one fail-open posting path: missing/invalid GitLab configuration now exits nonzero and has a regression test. No unresolved high-confidence vulnerability remains in the reviewed trust boundaries.
- Engineering review also corrected the public GitLab example to the supported OCR `--format json` CLI contract and added a regression assertion.
- Dependabot version updates are configured monthly in grouped Python-tooling and GitHub Actions PRs; vulnerability alerts and automated security fixes are enabled through GitHub.
- Public-safety scans found no private paths, infrastructure markers, legacy integration names, high-confidence secret patterns, or local specification files in the staged tree.
- Source repository verification still reports branch `ai-ocr` at `b770f6e66b504a675ba7f594b55f4b156b8a2a53` with only the two pre-existing untracked paths documented by the extraction input.
- Final workflow policy check: all third-party Actions use full commit SHAs, `pull_request_target` is absent, workflow tokens default to read-only, and repository Actions SHA pinning is enforced.
- Final GitHub Actions audit updated checkout, setup-uv, PyPI publishing, and Gitleaks to their current 2026 releases while retaining immutable full-SHA pins and readable version comments.
- Live private-repository runs confirmed CI, build, dependency/security, and Dependabot workflows. Scorecard and CodeQL are intentionally skipped while private because GitHub Free blocks their repository integrations; both activate automatically after the public-visibility approval gate.
- Final quality wrapper: 259 tests pass with branch coverage above the 70% gate; Ruff format/check and strict mypy pass. Build, Twine, Python 3.13 wheel/sdist install smokes, Towncrier draft, YAML parsing, and `pip-audit --skip-editable` pass.

### Resume Point

- Initial import commit `9fdc8fa282480c83ad1d8d3a33744dffbbbbf2f3` was pushed once to seed the private remote. Use pull requests only from this point. Before release, satisfy the owner gates below.

### Handoff Notes

- Do not create the initial commit while any validation, privacy audit, or source-integrity check is pending.
- Stop for owner action before PAT setup, Trusted Publisher setup, final public-package approval, or visibility changes.
- The later public-release plan replaced these historical owner gates with local release-PR preparation, Trusted Publishing, public rulesets, private vulnerability reporting, secret-scanning push protection, and immutable releases.

## Completed Plan: Private TestPyPI preview

Status: completed
Owner: Codex
Last Updated: 2026-07-18

### Goal

Keep the source repository private while publishing a prerelease to TestPyPI for installation testing. Defer public GitHub visibility, public-only GitHub protections, and production PyPI publication to a separate explicitly approved release task.

### Work Queue

1. [x] Verify the current GitHub Free/private-repository limits and the current PyPI Trusted Publisher setup flow against official documentation.
2. [x] Split private TestPyPI preview automation from the production release workflow.
3. [x] Make unavailable GitHub Free/private integrations skip cleanly while preserving local dependency and secret checks.
4. [x] Validate the workflow syntax, quality suite, build, and focused security properties.
5. [x] Open pull request #2 and wait for all applicable GitHub Actions checks.
6. [x] Configure the TestPyPI Trusted Publisher, publish `0.1.0a1`, and verify the public artifacts.

### Locked Decisions

- 2026-07-17: The GitHub repository remains private during TestPyPI validation.
- 2026-07-17: TestPyPI publication is a public package disclosure, but it is not the production release and must not publish to PyPI or publish a GitHub Release.
- 2026-07-17: Production publication remains fail-closed until the repository is public and the public-only GitHub hardening is configured.

### Validation Evidence

- `scripts/quality.sh check`: 259 tests and 26 subtests passed; branch coverage 72.67% against the 70% gate; Ruff and strict mypy passed.
- All workflow YAML files parsed successfully and `git diff --check` passed.
- A synthetic `0.1.0a1` wheel and sdist built successfully, passed Twine metadata checks, contained the exact requested version, and installed into a Python 3.13 smoke environment.
- The wheel and sdist contain no local extraction material, Codex configuration, Git metadata, or IDE metadata. Local-only configuration remains ignored and untracked.
- Gitleaks v8.30.1 scanned all Git history and the built `dist/` artifacts with no leaks found.
- Zizmor 1.27.0 reported no findings in the private-preview, Security, and Dependency Review workflows. The pre-existing production release workflow has only low/informational hardening suggestions and remains fail-closed while private.
- Focused review confirms that the preview publishes only from the current `main` SHA, accepts only canonical prerelease versions, refuses an existing TestPyPI version, stores no index credential, disables provenance disclosure from the private workflow, and smoke-installs from TestPyPI without dependency confusion fallback.
- Pull request #2 passed the complete Python 3.10-3.13 Linux/macOS CI matrix, quality, pip-audit, and Gitleaks checks. CodeQL and Dependency Review skipped as designed for GitHub Free/private mode.

## Recently Completed

- None yet.

## Completed Plan: OCR 1.7.12 compatibility and correctness hardening

Status: completed
Owner: Codex
Last Updated: 2026-07-18

### Goal

Harden the current standalone toolkit with regression coverage, update OCR compatibility to 1.7.12, and reach a clean review/security state before opening a pull request.

### Work Queue

1. [x] Verify the OCR 1.7.12 release, checksum, CLI contract, and local installation.
2. [x] Reassess inherited behavior against the current toolkit and preserve only applicable product fixes.
3. [x] Add focused regression tests and implement confirmed fixes without broad refactors.
4. [x] Update public documentation, examples, compatibility pins, prerelease metadata, and Towncrier fragments.
5. [x] Complete targeted and full quality, build, package, and supply-chain validation.
6. [x] Validate bounded context, manifest, and version discovery against a tracked consumer snapshot without adding consumer-specific behavior.
7. [x] Complete iterative internal self-review and repair cycles with no remaining actionable findings.
8. [x] Complete the full repository security scan, fix validated findings, and seal a post-remediation rescan with no open findings.
9. [x] Update this plan to post-change truth before commit and pull request creation.

### Locked Decisions

- Local-only material remains ignored and is not staged, committed, packaged, or quoted into public artifacts.
- The source integration repository remains read-only; fixes are implemented in the standalone toolkit only.
- Consumer validation may inspect only tracked source-integration files and run the standalone toolkit against that repository. No consumer-specific path, host, package, version, or layout may enter toolkit runtime code, tests, documentation, or examples.
- Multi-agent Codex features remain disabled for this project; the complete security scan ran sequentially with exhaustive primary-agent receipts.
- Runtime dependencies remain empty; fixes should use the standard library.
- The package version remains SCM-derived. This change advances the next development/release line through changelog fragments and the eventual release tag rather than hard-coding a package version.

## Completed Plan: Unified review language and automatic TestPyPI alpha releases

Status: completed
Owner: Codex
Last Updated: 2026-07-19

### Goal

Make `OCR_REVIEW_LANGUAGE` the single safe language contract with default `English`, synchronize public GitLab examples, support Python 3.14, and publish one deterministic TestPyPI alpha for every successful merge into `main`.

### Work Queue

1. [x] Implement one shared language resolver used by runtime configuration and generated context; remove the legacy language identifier from tracked and built content.
2. [x] Pin the synthetic GitLab example to a checksum-verified TestPyPI wheel downloaded with bounded retries and timeouts.
3. [x] Convert the TestPyPI workflow to automatic `main` publication using `0.1.0a${GITHUB_RUN_NUMBER}` and idempotent PEP 691 artifact verification.
4. [x] Add regression, workflow, versioning, registry-state, documentation, and packaging tests.
5. [x] Extend package metadata, CI, documentation, and install smokes through Python 3.14.
6. [x] Run iterative internal self-review and repair cycles until no actionable findings remain.
7. [x] Run the full repository Codex Security scan, fix every validated finding, repeat self-review and validation, and seal a clean post-remediation scan.
8. [x] Validate the package and read-only consumer flow and close this implementation plan to post-change truth before commit and pull-request publication.

### Validation Evidence

- The complete quality wrapper passes with 301 tests, 26 subtests, 73.37% branch coverage, Ruff format/check, and strict mypy.
- Independent Python 3.10 and Python 3.14 test runs pass the complete 301-test suite.
- Duplicate `0.1.0a3` wheel and sdist builds are byte-identical, pass Twine, exclude ignored local files, and install successfully on supported Python versions.
- `pip-audit --skip-editable`, locked dependency validation, YAML parsing, and Zizmor over every GitHub workflow pass; Zizmor reports no findings.
- Live TestPyPI PEP 691 metadata for `0.1.0a2` matches the public example's immutable wheel URL and SHA-256.
- A full repository Codex Security scan covered runtime and privileged CI surfaces. One production-release artifact-binding issue was fixed; the sealed post-remediation result has no open findings or deferred scope.
- A tracked-only archive of the read-only consumer repository generates bounded context with the default English review language and no toolkit-specific hardcoding; its existing local untracked files remain unchanged and unread.

### Locked Decisions

- Default review language is `English`; `Russian` is the documented explicit example.
- At the v0.1.0 release checkpoint, supported Python versions were 3.10 through 3.14 on Linux and macOS; M1 raises the v0.4 floor to Python 3.12.
- The legacy language identifier is removed rather than supported as an alias.
- TestPyPI run number maps directly to the alpha number; run #3 publishes `0.1.0a3`, reruns are idempotent, and subsequent merges consume subsequent alpha numbers.
- The public example remains pinned to the already verified `0.1.0a2` wheel; the automatic workflow never commits its own published URL back to `main`.
- Production PyPI publication, Git tags, and GitHub Release creation are not executed in this change; their existing workflow now verifies published files against the reviewed artifact hashes.
- Pull-request checks, squash merge, and independent `0.1.0a3` TestPyPI verification are operational follow-through after this implementation plan is closed.
