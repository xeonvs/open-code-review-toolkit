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
