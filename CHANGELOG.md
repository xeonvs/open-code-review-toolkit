## 0.4.7 - 2026-08-11

### 🚀 Features

- Add default-on `OCR_AUTO_APPROVE` for conservative, exact-SHA GitLab approval after every current review note publishes, with an explicit fail-closed opt-out and bounded status readback.
  Limit eligibility to complete manifest-backed reviews with at most three low-severity style, documentation, or maintainability findings, while preserving every existing approval when a later review is ineligible or disabled. ([#71](https://github.com/xeonvs/open-code-review-toolkit/issues/71))
- Target checksum-verified Open Code Review 1.9.1 after qualifying 1.9.0 through 1.9.1. ([#72](https://github.com/xeonvs/open-code-review-toolkit/issues/72))

### 🐛 Bug Fixes

- Publish an actionable GitLab suggestion only when `existing_code` proves that the replacement applies to one contiguous range in the immutable reviewed head.
  Retain the explanatory finding, with a bounded non-sensitive omission reason, when a replacement is stale, malformed, multi-region, diff-prefixed, or otherwise unverifiable. ([#70](https://github.com/xeonvs/open-code-review-toolkit/issues/70))

### 📖 Documentation

- Document the established evidence and MCP architecture, reconcile the completed 0.4.6 lifecycle and remaining backlog with current code, and index archived execution history by stable release tag.
  Make the release pull request the final repository mutation while exact-tree authorization, registry and provenance verification, an immutable machine-readable receipt, and idempotent issue closure prove external delivery after merge. ([#69](https://github.com/xeonvs/open-code-review-toolkit/issues/69))

### 🧩 Rules

- The recommended OCR built-in rules and reviewable-file allowlist now include Nim source, script, and package files. ([#73](https://github.com/xeonvs/open-code-review-toolkit/issues/73))


## 0.4.6 - 2026-08-08

### 🚀 Features

- Target checksum-verified Open Code Review 1.8.10 after reviewing the complete 1.8.9 through 1.8.10 compatibility chain; valid toolkit CLI, result, MCP, configuration, and GitLab contracts remain compatible. ([#66](https://github.com/xeonvs/open-code-review-toolkit/issues/66))


## 0.4.5 - 2026-08-05

### 🚀 Features

- Target checksum-verified Open Code Review 1.8.8 after reviewing the complete 1.8.7 through 1.8.8 compatibility chain and recording per-run provider/model and result-identity capabilities. ([#61](https://github.com/xeonvs/open-code-review-toolkit/issues/61))

### 🔧 Refactoring

- Qualify consecutive OCR patch releases as one ordered chain, keeping adjacent release comparisons separate from the currently tested baseline and preparing an automatic update only when every release is safe. ([#60](https://github.com/xeonvs/open-code-review-toolkit/issues/60))

### 🧩 Rules

- Accept OCR 1.8.8's Nix and Haskell allowlist and built-in rule support as an effective review-scope expansion; toolkit evidence-pack backlog items remain separate and unfinished. ([#61](https://github.com/xeonvs/open-code-review-toolkit/issues/61))


## 0.4.4 - 2026-08-03

### 🚀 Features

- Redesign GitLab summaries around independent review health, published findings, and bounded failed-file coverage diagnostics, with aggregate finding emoji and operational metadata under technical details. ([#42](https://github.com/xeonvs/open-code-review-toolkit/issues/42))

### 🐛 Bug Fixes

- Represent scoped evidence completeness explicitly, distinguish static, dynamic, and executable Ansible inventory sources, collect supported recursive role defaults and vars without execution, and omit exact no-op suggestions while retaining their findings. ([#41](https://github.com/xeonvs/open-code-review-toolkit/issues/41))


## 0.4.3 - 2026-08-03

### 🚀 Features

- Target checksum-verified Open Code Review 1.8.6, support its versioned run manifest, keep one compatibility issue per upstream version with release-change context and bounded transient download retries, and bound GitHub Actions cache, artifact, and log retention. ([#49](https://github.com/xeonvs/open-code-review-toolkit/issues/49))

### 🧩 Rules

- Adopt OCR 1.8.6 default review exclusions for snapshots, testdata, fixtures, and generated files. ([#49](https://github.com/xeonvs/open-code-review-toolkit/issues/49))


## 0.4.2 - 2026-07-31

### 🚀 Features

- Qualify OCR 1.8.3 after its per-file terminal-state and Cobra CLI changes, recommend it with exact checksums, and retain the existing toolkit result, command, and rules contracts. ([#38](https://github.com/xeonvs/open-code-review-toolkit/issues/38))


## 0.4.1 - 2026-07-31

### 🚀 Features

- Qualify OCR 1.8.1 and 1.8.2, recommend OCR 1.8.2 with exact checksums, and preserve findings and usage metadata when OCR returns a token-budget-limited partial review. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))

### 🐛 Bug Fixes

- Authenticate scheduled GitHub release-metadata checks without forwarding credentials to public asset downloads, preventing anonymous API rate limits from interrupting compatibility monitoring. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))

### 📖 Documentation

- Use conditional emoji headings in changelogs and append an exact comparison link to GitHub Release notes. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))

### 🧩 Rules

- **OCR allowlist:** Add Prisma schema review support from OCR 1.8.1. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))
- **OCR built-in rules:** Add PHP and Composer review guidance from OCR 1.8.2. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))
- **Toolkit rules:** `examples/gitlab/rules.json` is unchanged; integrations receive these additions by updating OCR rather than copying a new toolkit rules file. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))
- **OCR built-in rules:** Add comprehensive Go review guidance from OCR 1.8.1. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))
- **OCR allowlist:** Add Protocol Buffers (`.proto`) review support from OCR 1.8.2. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))


## 0.4.0 - 2026-07-31

### Features

- Add the repository evidence architecture for OCR reviews:

  - collect schema-versioned facts and immutable base/head deltas through bounded Git reads;
  - prepare private evidence, compact bootstrap, and composed MCP configuration automatically in `ocr-ci review`;
  - expose detailed context on demand through the built-in read-only evidence MCP instead of embedding legacy Markdown;
  - preserve Ansible Galaxy role and collection declarations, optional sources and versions, and bounded requirement includes as typed immutable evidence with explicit degradation diagnostics;
  - preserve Python declarations, runtime constraints, dependency groups, recursive requirements includes, and resolved uv, Poetry, Pipenv, and standardized lock facts as bounded typed evidence available through the built-in MCP;
  - require Python 3.12 or newer for toolkit 0.4 while retaining tested support through Python 3.14;
  - preserve JavaScript runtime and package-manager constraints, scoped package declarations, and resolved npm, Yarn, and pnpm lock facts as bounded typed evidence;
  - preserve Go module identity, language and toolchain declarations, direct/indirect requirements, replacements, exclusions, and resolved `go.sum` checksums as bounded typed evidence;
  - preserve Composer/PHP package identity, production/development links, virtual-platform constraints, safe repository-source classifications, resolution policy, and resolved lock metadata as bounded typed evidence;
  - preserve application and infrastructure version pins, nested container images, and Ansible role vars as bounded typed evidence with safe exclusions and immutable deltas; and
  - bind a safe review-time MCP-use receipt to the private OCR result and report independently configured servers that OCR actually used while omitting unused servers and sensitive connection details.

  ([#30](https://github.com/xeonvs/open-code-review-toolkit/issues/30))

### Bug fixes

- Improve GitLab review summaries:

  - distinguish skipped, clean, warning, error, and finding outcomes;
  - omit zero-value counters that do not help the reviewer;
  - add severity and category emoji that can be disabled through configuration;
  - refresh the development toolchain and immutable GitHub Actions pins, and cover every supported Python minor in CI;
  - negotiate the MCP 2025-11-25 revision used by Open Code Review 1.8.0 while retaining the older supported revisions;
  - launch the built-in evidence MCP through the toolkit's current Python installation so reviews do not depend on the caller's executable search path;
  - keep evidence records and deltas recursively immutable, and revalidate persisted values, metadata, diagnostics, and limits before serving them through MCP;
  - preserve semantic dependency and infrastructure facts across supported Ansible, Python/Poetry, JavaScript, Go, Composer, lockfile, URL, variable, tag, and digest variants, with explicit bounded-traversal notices;
  - harden evidence parsing and persistence against type-confused JSON, unusual Git paths, nested manifest variants, duplicate identities, descriptor reuse, and provider-controlled summary text;
  - keep repository evidence snapshots, private artifacts, bootstrap diagnostics, MCP requests, immutable OCR refs, result reads, and fallback Markdown safe and atomic at their trust boundaries;
  - bind evidence and GitLab remap reads to authenticated Git objects despite repository replacement refs or inherited Git configuration, and bound existing OCR configuration before parsing it; and
  - add a pinned, history-aware local Gitleaks gate so secret-shaped content is rejected before branch publication as well as in CI.

  ([#30](https://github.com/xeonvs/open-code-review-toolkit/issues/30))


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
