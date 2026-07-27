# Tasks Backlog

This file contains implementation-ready future work derived from the [toolkit strategy](../engineering/toolkit_strategy.md) and ordered by the [roadmap](../../ROADMAP.md). Active execution belongs in `PLANS.md`; roadmap outcomes are intentionally not repeated here.

Statuses are `ready`, `planned`, `parked`, `conditional`, or `owner action`. Release classification is an expectation to be confirmed when work is activated.

## Existing backlog reconciliation

| Previous item | Disposition | Result |
| --- | --- | --- |
| Native fuzzing campaign | Retained and revised | BL-019 connects fuzzing to the future evidence/MCP parser attack surface and keeps bounded CI and corpus ownership as activation requirements. |
| OpenSSF Best Practices registration | Retained as owner action | BL-022 remains conditional on truthful owner attestations and is not a product-roadmap priority. |
| Additional provider adapters | Retained, clarified, and reprioritized | BL-021 is explicitly about code-hosting and review-host adapters beyond GitLab, not repository ecosystem/framework evidence. |
| File-based user configuration | Retained and redesigned | BL-020 waits for profile, MCP, and evidence schemas while preserving environment precedence and excluding secrets. |

## M0 Foundation

### BL-001: Add Bandit as a repository security gate

- **Status:** ready
- **Priority:** high
- **Roadmap theme:** M0 Foundation
- **Dependencies:** Existing isolated quality environment and security workflow.
- **Activation trigger:** Strategy and backlog documentation is merged.
- **Goal:** Detect high-signal Python security defects in the toolkit without turning analyzers into a downstream product capability.
- **Scoped deliverables:** Add a development-only pinned Bandit dependency; scan `src/ocr_toolkit`; integrate concise execution with `scripts/quality.sh` and the repository security workflow; document narrow, justified suppressions.
- **Acceptance criteria:** Local and CI scans use identical configuration, produce no unexplained findings, keep full logs out of agent context, and add no runtime dependency.
- **Exclusions:** Scanning downstream repositories, auto-fixing findings, broad ignore lists, or treating Bandit as evidence supplied to OCR.
- **Validation:** Positive and negative synthetic fixtures where configuration needs proof, complete quality gate, and security workflow dry run or equivalent command.
- **Release classification expectation:** `no-release`, unless remediation changes user-visible behavior.

### BL-002: Centralize OCR compatibility in a machine-readable manifest

- **Status:** ready
- **Priority:** high
- **Roadmap theme:** M0 Foundation
- **Dependencies:** Current recommended/tested OCR baseline and preflight checks.
- **Activation trigger:** The next OCR compatibility change or before evidence MCP depends on an OCR capability.
- **Goal:** Replace scattered exact-version assumptions with one reviewed compatibility and capability source.
- **Scoped deliverables:** Define a dependency-free manifest for recommended/tested releases and required capabilities; centralize version/capability inspection; generate or validate documentation and CI pins from it; fail closed when required contracts disappear.
- **Acceptance criteria:** Preflight, public examples, tests, and documentation agree with the manifest; additive version output remains tolerated; unknown or missing required capabilities fail with actionable errors.
- **Exclusions:** Automatic production upgrades, downloading OCR, or supporting arbitrary historical releases.
- **Validation:** Contract fixtures for supported, additive, malformed, and incompatible OCR outputs plus release-pin consistency tests.
- **Release classification expectation:** `release-required`.

### BL-003: Detect and test new upstream OCR releases

- **Status:** planned
- **Priority:** high
- **Roadmap theme:** M0 Foundation
- **Dependencies:** BL-002.
- **Activation trigger:** Compatibility manifest and capability inspection are stable.
- **Goal:** Detect upstream changes quickly while keeping production upgrades review-gated.
- **Scoped deliverables:** Add scheduled latest-release detection, checksum retrieval, changelog impact classification, and contract tests across the supported release set; create an actionable report or issue when review is required.
- **Acceptance criteria:** Automation is bounded, uses official release metadata, distinguishes compatible/additive/breaking/unknown impact, and never edits production pins or publishes a release automatically.
- **Exclusions:** Automatic merge, automatic recommended-version changes, or relying on mutable download URLs without digest verification.
- **Validation:** Recorded synthetic release metadata, scheduled-workflow tests, and a no-change path that creates no noise.
- **Release classification expectation:** `no-release`; subsequent compatibility bumps are classified separately.

## M1 Evidence architecture

### BL-004: Define the common repository evidence model

- **Status:** ready
- **Priority:** high
- **Roadmap theme:** M1 Evidence architecture
- **Dependencies:** BL-002 for capability-sensitive evidence.
- **Activation trigger:** M0 planning sources are merged.
- **Goal:** Give all collectors and projections one deterministic representation of repository facts.
- **Scoped deliverables:** Define dependency-free evidence types for kind/value, source path, git ref, component scope, provenance, confidence, and optional staleness; specify stable ordering, deduplication, and global/per-kind bounds.
- **Acceptance criteria:** Existing context facts can be represented without losing trust or origin; malformed and over-limit facts degrade explicitly; serialization is deterministic.
- **Exclusions:** MCP transport, bootstrap prose, new ecosystem parsers, or network discovery.
- **Validation:** Unit/property tests for normalization, ordering, bounds, provenance, and round trips using synthetic facts.
- **Release classification expectation:** `release-deferred` until a user-visible projection ships.

### BL-005: Build source/target snapshots and evidence deltas

- **Status:** planned
- **Priority:** high
- **Roadmap theme:** M1 Evidence architecture
- **Dependencies:** BL-004 and existing bounded git-ref handling.
- **Activation trigger:** The common evidence model is merged.
- **Goal:** Describe base and head repository state without conflating declarations, resolved versions, and changes.
- **Scoped deliverables:** Collect target/base and source/head snapshots, map changed files to components, and compute typed dependency/runtime/container deltas while preserving absent and unknown states.
- **Acceptance criteria:** Target content is read from trusted refs, source-only changes cannot self-authorize policy, and added/removed/changed/unknown facts are reproducible.
- **Exclusions:** Whole-history analysis, network package resolution, installed-environment probing outside configured evidence, or framework plugins.
- **Validation:** Synthetic two-ref repositories covering additions, removals, renames, malformed manifests, missing refs, and bounded failure.
- **Release classification expectation:** `release-deferred`.

### BL-006: Separate collection, storage, planning, and rendering

- **Status:** planned
- **Priority:** high
- **Roadmap theme:** M1 Evidence architecture
- **Dependencies:** BL-004 and BL-005.
- **Activation trigger:** Current context output is characterized by regression fixtures.
- **Goal:** Decompose `context/render.py` without changing trust or fail-closed behavior.
- **Scoped deliverables:** Move collectors behind evidence interfaces, add bounded storage, isolate bootstrap selection, and retain a renderer compatible with the current background contract during migration.
- **Acceptance criteria:** Existing public context behavior remains covered, collectors are projection-independent, and no bootstrap/MCP-specific duplicate collector path exists.
- **Exclusions:** New parser breadth, changing the hard output limit, or enabling built-in MCP.
- **Validation:** Golden synthetic context fixtures, regression tests for truncation/redaction/guidance, and complete quality gate.
- **Release classification expectation:** `release-deferred` unless output behavior changes.

### BL-007: Deliver the compact OCR bootstrap

- **Status:** planned
- **Priority:** high
- **Roadmap theme:** M1 Evidence architecture
- **Dependencies:** BL-004 through BL-006.
- **Activation trigger:** Evidence selection is independent from rendering.
- **Goal:** Replace large background inventories with a trusted overview that guides OCR to detailed evidence on demand.
- **Scoped deliverables:** Implement prioritized bootstrap planning for constraints, trust, refs, ecosystems/frameworks, material deltas, reference identifiers, MCP capabilities, relevant decisions, and guidance hints; target 1,500-2,500 characters while preserving the 7,950-character hard limit.
- **Acceptance criteria:** Detailed manifests and external contents are absent; omissions and degradation are explicit; relevant high-priority facts survive tight budgets deterministically.
- **Exclusions:** Raising the hard limit, copying full guidance, or embedding all dependency lists.
- **Validation:** Budget boundary tests, deterministic golden fixtures, adversarial Markdown/redaction cases, and comparison with existing context scenarios.
- **Release classification expectation:** `release-required`.

### BL-008: Add the built-in read-only evidence MCP

- **Status:** planned
- **Priority:** high
- **Roadmap theme:** M1 Evidence architecture
- **Dependencies:** BL-004 through BL-007 and current MCP validation.
- **Activation trigger:** Common evidence storage and compact bootstrap are stable.
- **Goal:** Let OCR retrieve bounded derived facts without duplicating its native repository tools.
- **Scoped deliverables:** Register a reserved `ocr_toolkit_evidence` server by default; expose `ocr_toolkit_*` tools for environment, components, dependencies/deltas, frameworks, versions, and decisions; compose with external servers; reserve names and validate collisions.
- **Acceptance criteria:** Server is read-only, root-constrained, deterministic, network-independent, command-free, bounded, and uses the same evidence store as the bootstrap.
- **Exclusions:** Generic file reads, shell execution, GitLab access, external URL fetches, or documentation storage.
- **Validation:** Protocol and composition tests, traversal/collision/adversarial-input tests, and synthetic OCR configuration integration.
- **Release classification expectation:** `release-required`.

## M2 Ecosystem and framework coverage

### BL-009: Resolve lockfile, runtime, and container evidence

- **Status:** planned
- **Priority:** high
- **Roadmap theme:** M2 Ecosystem and framework coverage
- **Dependencies:** BL-004 through BL-006.
- **Activation trigger:** Snapshot and delta semantics are stable.
- **Goal:** Distinguish declared constraints, locked, installed, runtime-detected, container-pinned, inferred, and unknown versions.
- **Scoped deliverables:** Strengthen actual-use formats for Python, JavaScript/TypeScript, Go, PHP, Ansible, containers, and GitLab CI; implement source/target resolution and deltas with provenance.
- **Acceptance criteria:** Each supported format has deterministic semantics and fixtures; conflicting sources remain distinct; malformed/oversized files degrade without network access.
- **Exclusions:** Unused ecosystems, package-registry queries, arbitrary build execution, or treating declarations as resolved versions.
- **Validation:** Per-format source/target fixtures, conflict and limit cases, and common evidence-model contract tests.
- **Release classification expectation:** `release-required`.

### BL-010: Establish framework evidence plugins

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M2 Ecosystem and framework coverage
- **Dependencies:** BL-004, BL-005, and BL-009.
- **Activation trigger:** At least two demonstrated repository use cases can share a plugin contract.
- **Goal:** Expose framework identity, verified version, component scope, important configuration paths, and material deltas without building code graphs.
- **Scoped deliverables:** Define a bounded plugin protocol and implement first providers chosen from demonstrated fixtures, prioritizing pytest, Ansible collections, and Molecule before broader candidates.
- **Acceptance criteria:** Plugins cannot run arbitrary commands or network requests, use common evidence records, and avoid whole-repository traversal when changed components are known.
- **Exclusions:** Route/call/symbol graphs, framework-specific reviewers, or speculative detection without version evidence.
- **Validation:** Positive/negative/multi-component fixtures, version-conflict and staleness cases, and plugin isolation tests.
- **Release classification expectation:** `release-required`.

### BL-011: Add evidence packs from demonstrated use cases

- **Status:** conditional
- **Priority:** medium
- **Roadmap theme:** M2 Ecosystem and framework coverage
- **Dependencies:** BL-009 and BL-010.
- **Activation trigger:** A real repository need identifies a missing ecosystem or framework and supplies safe synthetic fixtures and deterministic semantics.
- **Goal:** Extend coverage without accumulating shallow detectors.
- **Scoped deliverables:** Implement one coherent ecosystem or framework pack per activation, with provenance, bounds, source/target deltas, documentation, and public synthetic examples.
- **Acceptance criteria:** The use case and completion signal are documented before implementation; false-positive behavior and unsupported versions are explicit.
- **Exclusions:** Checkbox coverage, network resolution, runtime code execution, or bundles spanning unrelated ecosystems.
- **Validation:** Pack-specific fixtures plus common evidence and bootstrap/MCP projection contracts.
- **Release classification expectation:** `release-required`.

## M3 External MCP hardening

### BL-012: Document and validate external read-only MCP composition

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M3 External MCP hardening
- **Dependencies:** BL-008 and existing explicit external tool allowlists.
- **Activation trigger:** Built-in evidence MCP configuration is stable.
- **Goal:** Compose external knowledge tools with built-in evidence without prefetching content or weakening tool permissions.
- **Scoped deliverables:** Add synthetic generic stdio, HTTP-to-stdio proxy, YouTrack read-only, Confluence read-only, and versioned-documentation MCP examples; document reserved names, allowlists, secret injection, and composition behavior.
- **Acceptance criteria:** Examples expose narrow reads only, use synthetic hosts, keep credentials out of generated files/logs, and cannot replace the built-in server.
- **Exclusions:** External writes, generic URL fetch, documentation mirroring, or issue/page prefetch into bootstrap.
- **Validation:** Configuration contract tests, redaction checks, collision cases, and executable synthetic example validation.
- **Release classification expectation:** `release-required` if configuration changes; otherwise `no-release`.

### BL-013: Threat-model and constrain external references

- **Status:** planned
- **Priority:** high
- **Roadmap theme:** M3 External MCP hardening
- **Dependencies:** BL-004, BL-008, and canonical MR metadata handling.
- **Activation trigger:** External references are proposed for bootstrap or MCP use.
- **Goal:** Detect useful references without allowing untrusted metadata or retrieved content to control policy or tools.
- **Scoped deliverables:** Define configured project-key patterns, host/space allowlists, canonical parsing, reference and traversal bounds, audit metadata, narrow tool contracts, and prompt-injection instructions.
- **Acceptance criteria:** External content cannot change policy, suppress findings, authorize actions, modify permissions, or trigger writes; rejected and truncated references are auditable without leaking secrets.
- **Exclusions:** Content prefetch, recursive browsing, generic web access, or external-system mutation.
- **Validation:** Threat model, adversarial MR/issue/page fixtures, Unicode/URL canonicalization, bound tests, and attack-path review.
- **Release classification expectation:** `release-required`.

## M4 Policy and project guidance

### BL-014: Evolve accepted decisions into tolerant structured Markdown

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M4 Policy and project guidance
- **Dependencies:** BL-004, BL-005, and current target-branch self-whitelisting guard.
- **Activation trigger:** Evidence model can preserve decision scope and provenance.
- **Goal:** Add optional Scope, Category, Review after, and Owner metadata without breaking existing decision documents.
- **Scoped deliverables:** Parse heading/rationale entries and optional bullet metadata; tolerate unknown fields; filter by target branch and component scope; place summaries in bootstrap and full rationale in evidence MCP.
- **Acceptance criteria:** Existing files remain valid, malformed optional metadata cannot invalidate unrelated decisions, and source-branch edits never affect the current review.
- **Exclusions:** YAML, unconditional finding suppression, policy authorization, or mandatory metadata.
- **Validation:** Backward-compatibility, unknown/malformed field, scope, date, target/source, and size-bound fixtures.
- **Release classification expectation:** `release-required`.

### BL-015: Simplify project guidance after an upstream OCR contract exists

- **Status:** conditional
- **Priority:** medium
- **Roadmap theme:** M4 Policy and project guidance
- **Dependencies:** BL-004, BL-005, BL-007, and documented/tested upstream OCR automatic guidance behavior.
- **Activation trigger:** A supported OCR release proves the required guidance contract in compatibility tests.
- **Goal:** Replace large excerpts with target-branch paths and short non-authoritative hints while preserving fail-closed handling.
- **Scoped deliverables:** Discover applicable `AGENTS.md`/`CLAUDE.md`, exclude files changed by the merge request, supply paths/hints, and permit OCR native tools to read target versions on demand.
- **Acceptance criteria:** Source changes cannot self-instruct, missing upstream capability retains current bounded behavior, and guidance never overrides system policy.
- **Exclusions:** Removing safeguards before the trigger, copying full guidance into bootstrap, or toolkit-specific instruction execution.
- **Validation:** Multi-scope target/source fixtures, changed-guidance attacks, capability fallback tests, and bootstrap budget tests.
- **Release classification expectation:** `release-required`.

## M5 Review profiles and quality measurement

### BL-016: Add explicit run-level review profiles

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M5 Review profiles and quality measurement
- **Dependencies:** Stable compatibility manifest and evidence/bootstrap contracts.
- **Activation trigger:** Profile model and limit differences can be documented without changing per-tool routing.
- **Goal:** Offer `economy`, `standard`, and `strong` choices for one OCR review run.
- **Scoped deliverables:** Define explicit profile configuration selecting a run-level model and existing OCR limits; validate supported values, environment precedence, and rendered effective configuration.
- **Acceptance criteria:** One model remains active per run, defaults preserve current behavior, secrets remain environment-only, and unsupported profiles fail before OCR execution.
- **Exclusions:** Per-file/per-tool model routing, hidden heuristics, multi-agent orchestration, or full-repository scan profiles.
- **Validation:** Profile matrix, precedence, preflight, configuration-rendering, and compatibility tests.
- **Release classification expectation:** `release-required`.

### BL-017: Measure review cost and quality signals

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M5 Review profiles and quality measurement
- **Dependencies:** BL-016 and stable discussion/fingerprint lifecycle.
- **Activation trigger:** Explicit profiles can label comparable runs.
- **Goal:** Produce privacy-safe evidence for profile tuning and any future routing decision.
- **Scoped deliverables:** Define bounded metrics for latency, token use when available, evidence/MCP use, findings, repeats, suppression, resolution, and human ownership; document retention and export boundaries.
- **Acceptance criteria:** Metrics contain no source, prompts, secrets, or external contents; missing provider telemetry is explicit; repeated runs are comparable without changing review behavior.
- **Exclusions:** User surveillance, ranking developers, automatic routing, or mandatory external telemetry.
- **Validation:** Synthetic lifecycle aggregation, redaction/privacy tests, missing-data behavior, and deterministic export fixtures.
- **Release classification expectation:** `release-required` if exposed publicly; otherwise `no-release`.

### BL-018: Evaluate conservative automatic profile routing

- **Status:** conditional
- **Priority:** low
- **Roadmap theme:** M5 Review profiles and quality measurement
- **Dependencies:** BL-016, BL-017, and an owner-approved quality/cost decision policy.
- **Activation trigger:** Representative metrics demonstrate a stable deterministic rule that improves an explicit objective without reducing review safety.
- **Goal:** Select one run-level profile conservatively from trusted bounded inputs.
- **Scoped deliverables:** Document the decision rule, inputs, fallback, observability, and opt-out; implement only after replay evaluation and owner approval.
- **Acceptance criteria:** Routing is deterministic and explainable, never uses untrusted content as authority, never selects `ocr scan`, and falls back to `standard` on uncertainty.
- **Exclusions:** Learned online routing, per-tool models, multiple agents, or silent policy changes.
- **Validation:** Offline replay, boundary/adversarial cases, fallback tests, and quality regression thresholds.
- **Release classification expectation:** `release-required`.

## M6 Later and conditional work

### BL-019: Run a native fuzzing campaign

- **Status:** parked
- **Priority:** medium
- **Roadmap theme:** M6 Later and conditional work
- **Dependencies:** Stable evidence/MCP parser interfaces from M1 and selected Python 3.10-3.14-compatible fuzzing backend.
- **Activation trigger:** Reproducible local execution, bounded CI resources, corpus ownership, and high-value parser targets are agreed.
- **Goal:** Find crashes and invariant violations at untrusted evidence, MCP, result, GitLab payload, and registry-metadata boundaries.
- **Scoped deliverables:** Compare Atheris and property-based alternatives; define synthetic seeds; fuzz selected parsers; minimize and retain regressions; evaluate public service integration only after useful local results.
- **Acceptance criteria:** Targets are deterministic and bounded, minimized failures become tests, corpora contain no repository/provider secrets, and ownership is explicit.
- **Exclusions:** Unbounded CI, production data, low-value blanket fuzzing, or a runtime dependency.
- **Validation:** Reproducible smoke campaign across supported Python boundaries and replay of minimized corpus.
- **Release classification expectation:** `no-release`, except user-visible fixes found by the campaign.

### BL-020: Design file-based non-secret configuration

- **Status:** parked
- **Priority:** low
- **Roadmap theme:** M6 Later and conditional work
- **Dependencies:** Stable profile, MCP composition, and evidence configuration schemas.
- **Activation trigger:** Environment-only configuration is a demonstrated operational constraint and one coherent schema can cover the affected non-secret settings.
- **Goal:** Improve maintainability without weakening environment precedence, validation, or secret handling.
- **Scoped deliverables:** Decide format/versioning, precedence, migration, allowed non-secret fields, unknown-key behavior, target/source trust, and schema evolution before implementation.
- **Acceptance criteria:** Environment values retain explicit precedence, secrets are rejected from files, source-branch files cannot self-authorize, and migration is documented and tested.
- **Exclusions:** Credentials on disk, implicit repository configuration, multiple overlapping formats, or implementation before the design decision.
- **Validation:** Threat model, schema/precedence fixtures, migration compatibility tests, and secret-rejection tests.
- **Release classification expectation:** `release-required`.

### BL-021: Add code-hosting and review-host adapters beyond GitLab

- **Status:** conditional
- **Priority:** low
- **Roadmap theme:** M6 Later and conditional work
- **Dependencies:** Stable provider-neutral core contracts and a funded non-GitLab use case.
- **Activation trigger:** A named forge has an owner, synthetic fixtures, and explicit parity requirements for CI orchestration, positioning, deduplication, discussion ownership, and safe publication.
- **Goal:** Add one coherent host adapter without leaking forge semantics into evidence or core result handling.
- **Scoped deliverables:** Specify adapter contract gaps, implement one provider boundary, add synthetic API fixtures and public setup documentation, and preserve fail-closed write behavior.
- **Acceptance criteria:** Core remains provider-neutral, GitLab behavior does not regress, and the new host meets explicit lifecycle and security parity.
- **Exclusions:** Repository ecosystem/framework detection, partial adapters, legacy namespace shims, or multi-host abstractions without a real second provider.
- **Validation:** Shared adapter contract suite, provider-specific synthetic integration tests, redaction/write-bound tests, and documentation validation.
- **Release classification expectation:** `release-required`.

### BL-022: Register for OpenSSF Best Practices

- **Status:** owner action
- **Priority:** low
- **Roadmap theme:** M6 Later and conditional work
- **Dependencies:** Public repository and owner access to `bestpractices.dev`.
- **Activation trigger:** The owner is ready to authenticate and attest every passing-level criterion truthfully.
- **Goal:** Create an evidence-backed public badge record without guessing governance or usage answers.
- **Scoped deliverables:** Complete the questionnaire with current public evidence links, leave unsupported criteria unmet, add the badge only after readback confirms the record.
- **Acceptance criteria:** Record and repository badge agree, every affirmative answer has current evidence, and owner-only statements are owner-confirmed.
- **Exclusions:** Automated attestations, aspirational answers, or treating badge work as a product feature.
- **Validation:** Public record readback, repository link check, and badge target verification.
- **Release classification expectation:** `no-release`.
