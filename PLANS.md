# Execution Plans

Use this file for active, blocked, or recently completed execution work. Update it before implementation and before handoff or commit.

## Active Plan: Qualify OCR 1.8.0, add native remote MCP, and release v0.3.1

Status: active; implementation in progress
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
- Do not push or open the feature PR until implementation, full validation, multiple self-review/fix cycles, and exactly one final complete local OCR 1.8.0 review of `main..HEAD` are finished. Fix every actionable OCR finding and rerun deterministic validation without a second OCR review.

### Work Queue

1. [x] Reconcile current repository and external qualification state, close the stale M0 plan checkbox, create tracking issue #24, and branch from synchronized protected `main`.
2. [ ] Promote OCR 1.8.0 in the compatibility manifest and all durable version/checksum pins using normalized workflow evidence and a recorded human conclusion; document why non-MCP upstream changes require no toolkit code.
3. [ ] Add bounded native remote MCP parsing and OCR config projection with HTTPS-only URLs, environment-backed secret headers, sensitive-literal rejection, transport field separation, redaction, and backward-compatible stdio behavior.
4. [ ] Update public configuration/security/compatibility documentation, synthetic examples, durable strategy/backlog boundaries, project-agent upstream-impact instructions, and Towncrier fragments. Reconcile the documented `OCR_MCP_REPLACE` behavior with runtime truth.
5. [ ] Add positive, negative, adversarial, documentation, manifest, workflow, and distribution-content tests while retaining zero runtime dependencies and minimal published artifacts.
6. [ ] Run targeted checks, the complete local validation matrix, and at least three self-review/fix cycles covering architecture/compatibility, security/redaction, and documentation/packaging/release completeness.
7. [ ] Run exactly one final local OCR 1.8.0 review over the complete feature diff, retain ignored evidence, fix every actionable finding, and rerun the deterministic validation matrix without another OCR review.
8. [ ] Update plan/backlog to post-commit truth, create signed feature commits, push the branch, open the non-draft feature PR, resolve review feedback, pass all protected checks, merge, and verify exact TestPyPI `0.3.1.devN` artifacts, provenance, and smoke installs.
9. [ ] Create signed `release/v0.3.1` from refreshed `main`, render and verify Towncrier release notes, open the exact-title release PR, pass all gates, merge, and monitor stable TestPyPI/PyPI/tag/immutable GitHub Release publication.
10. [ ] Reconcile registry, workflow, and GitHub hashes and provenance; smoke-install the wheel on Python 3.10 and hash-locked sdist on Python 3.14; close issues #23 and the tracking issue through a checked documentation-only closure PR.

### Release Gates

- Feature merge and TestPyPI development publication are intermediate checkpoints, not completion.
- Wheel contents remain limited to the runtime package and required metadata; repository qualification evidence, workflows, docs, examples, tests, plans, release tooling, and fragments remain excluded.
- Stable publication is blocked until OCR 1.8.0 is human-qualified, the final one-shot local OCR review is addressed, all protected checks pass, and the release PR is merged.
- Closure requires exact registry/GitHub/workflow hash equality, provenance verification, exact annotated tag target, immutable Release state, supported-Python smoke installs, external issue closure, and recorded receipts.

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
- Runtime dependencies remain empty and supported Python remains 3.10 through 3.14.

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
- Supported Python versions are 3.10 through 3.14 on Linux and macOS.
- The legacy language identifier is removed rather than supported as an alias.
- TestPyPI run number maps directly to the alpha number; run #3 publishes `0.1.0a3`, reruns are idempotent, and subsequent merges consume subsequent alpha numbers.
- The public example remains pinned to the already verified `0.1.0a2` wheel; the automatic workflow never commits its own published URL back to `main`.
- Production PyPI publication, Git tags, and GitHub Release creation are not executed in this change; their existing workflow now verifies published files against the reviewed artifact hashes.
- Pull-request checks, squash merge, and independent `0.1.0a3` TestPyPI verification are operational follow-through after this implementation plan is closed.
