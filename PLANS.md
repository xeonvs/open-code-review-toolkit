# Execution Plans

Use this file for active, blocked, or recently completed execution work. Update it before implementation and before handoff or commit.

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
6. [x] Add pinned CI, build, security, dependency review, Scorecard, Dependabot, release-preparation, provenance, and OIDC release workflows.
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
- No repository credential values are available locally, so no secret value was invented or copied from another project. OIDC publication needs no PyPI token; only owner-created `RELEASE_PR_TOKEN` remains to be stored in the `release-preparation` environment.
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
- Owner gates: create/store the scoped `RELEASE_PR_TOKEN`; configure PyPI and TestPyPI Trusted Publishers; upgrade GitHub or pass the public-visibility privacy checkpoint; then enable branch protection/rulesets, required checks/reviews, environment reviewers, private vulnerability reporting, secret-scanning push protection, and immutable releases.

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
