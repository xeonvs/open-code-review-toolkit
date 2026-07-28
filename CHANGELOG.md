## 0.3.1 - 2026-07-28

### Features

- Qualify Open Code Review 1.8.0 as the tested and recommended baseline, add native HTTPS Streamable HTTP MCP servers with environment-backed headers while preserving stdio fallback, and run OCR through a private-artifact wrapper that emits bounded redacted failure diagnostics to CI logs without posting. Repair interrupted package metadata only inside the disposable quality environment and avoid repeated synchronization noise. ([#24](https://github.com/xeonvs/open-code-review-toolkit/issues/24))


## 0.3.0 - 2026-07-28

### Features

- Add a bounded Bandit security gate and checksum-verified OCR compatibility qualification without automatic upstream upgrades. ([#19](https://github.com/xeonvs/open-code-review-toolkit/issues/19))

### Documentation

- Correct roadmap dependencies and rollout invariants for external MCP, repository evidence, compact bootstrap, and framework selection. ([#17](https://github.com/xeonvs/open-code-review-toolkit/issues/17))


## 0.2.1 - 2026-07-27

### Features

- Target Open Code Review 1.7.17 in preflight validation and the checksum-pinned GitLab CI example. ([#12](https://github.com/xeonvs/open-code-review-toolkit/issues/12))

### Documentation

- Document the durable toolkit strategy, milestone roadmap, and reconciled implementation backlog. ([#13](https://github.com/xeonvs/open-code-review-toolkit/issues/13))


## 0.2.0 - 2026-07-21

### Features

- Target Open Code Review 1.7.14 in preflight validation and the checksum-pinned GitLab CI example. ([#11](https://github.com/xeonvs/open-code-review-toolkit/issues/11))
- Replace the ambiguous `/ocr keep` and `/ocr skip` discussion replies with `/ocr resolve` and `/ocr suppress`, preserve human-owned deduplication, and document the complete GitLab review lifecycle for developers and CI operators. ([#8](https://github.com/xeonvs/open-code-review-toolkit/issues/8))

### Bug fixes

- Allow stable release verification to coexist with previously published development builds of the same base version on TestPyPI. ([#10](https://github.com/xeonvs/open-code-review-toolkit/issues/10))
- Treat ordinary merged pull requests as a successful no-op in the production release workflow while keeping release-branch authorization fail-closed. ([#7](https://github.com/xeonvs/open-code-review-toolkit/issues/7))

### Security

- Mark every source-distribution smoke install as hash-required while retaining the no-dependency boundary, and document the single-maintainer security posture and Scorecard triage policy. ([#6](https://github.com/xeonvs/open-code-review-toolkit/issues/6))

### Documentation

- Reduce the routine Ubuntu CI matrix to the supported Python 3.10 and 3.14 endpoints, matching the macOS matrix. ([#10](https://github.com/xeonvs/open-code-review-toolkit/issues/10))
- Document accepted project decisions, their optional `ocr-accept` marker convention, and the guard that prevents a merge request from whitelisting its own findings. ([#11](https://github.com/xeonvs/open-code-review-toolkit/issues/11))


## 0.1.0 - 2026-07-20

### Features

- Publish one deterministic, checksum-verified TestPyPI development build after every merge into `main`, with bounded registry downloads and idempotent reruns. ([#4](https://github.com/xeonvs/open-code-review-toolkit/pull/4))
- Target Open Code Review 1.7.13 in preflight validation and the pinned GitLab CI example. ([#4](https://github.com/xeonvs/open-code-review-toolkit/pull/4))
- Support and continuously test Python 3.14 while retaining Python 3.10-3.13 compatibility. ([#4](https://github.com/xeonvs/open-code-review-toolkit/pull/4))
- Publish reproducible 0.1.0 distributions to TestPyPI and PyPI with exact hash verification, provenance attestations, and immutable GitHub Release assets.
- Introduce the standalone `ocr-ci` toolkit with safe context generation, GitLab posting, runtime configuration, MCP configuration, and preflight checks.

### Bug fixes

- Bind production release smoke tests to the exact reviewed wheel and sdist hashes, with bounded HTTPS downloads from TestPyPI and PyPI. ([#4](https://github.com/xeonvs/open-code-review-toolkit/pull/4))
- Use `OCR_REVIEW_LANGUAGE` as the single safe language setting for OCR configuration and generated review context, with English as the default and Russian as an explicit option. ([#4](https://github.com/xeonvs/open-code-review-toolkit/pull/4))
- Preserve bounded context and version discovery with a 7,950-character ceiling, improve provider billing classification, and prevent cross-file remapping of findings that already name a path. ([#3](https://github.com/xeonvs/open-code-review-toolkit/pull/3))

### Security

- Require secure credential endpoints, block unsafe GitLab redirects, redact secret-shaped environment values, and reduce GitHub Actions credential persistence and permissions. ([#3](https://github.com/xeonvs/open-code-review-toolkit/pull/3))

### Documentation

- Document the checksum-verified TestPyPI prerelease path used before the public stable release. ([#2](https://github.com/xeonvs/open-code-review-toolkit/pull/2))


# Changelog

Changes for each release are assembled from `changelog.d/` by Towncrier.
