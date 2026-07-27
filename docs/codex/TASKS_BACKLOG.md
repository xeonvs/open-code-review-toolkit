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
- **Scoped deliverables:** Define a dependency-free manifest for one recommended production release, the tested support set, required capabilities, and explicitly reviewed incompatible releases; centralize version/capability inspection; generate or validate documentation and CI pins from it; fail closed when required contracts disappear. Observed upstream candidates remain workflow evidence until a reviewed change promotes them into the manifest.
- **Acceptance criteria:** Preflight, public examples, tests, and documentation agree with the manifest; recommended, tested, observed, and incompatible states cannot be conflated; additive version output remains tolerated; unknown or missing required capabilities fail with actionable errors.
- **Exclusions:** Automatic production upgrades, downloading OCR, or supporting arbitrary historical releases.
- **Validation:** Contract fixtures for supported, additive, malformed, and incompatible OCR outputs plus release-pin consistency tests.
- **Release classification expectation:** `release-required`.

### BL-003: Detect and qualify upstream OCR release candidates

- **Status:** planned
- **Priority:** high
- **Roadmap theme:** M0 Foundation
- **Dependencies:** BL-002.
- **Activation trigger:** BL-002 defines the manifest states, required capabilities, and reusable compatibility probes.
- **Goal:** Discover every unseen stable upstream release, produce reproducible compatibility evidence, and route it to human impact review without changing production support claims.
- **Scoped deliverables:** Add a daily and manually dispatchable workflow that enumerates all stable releases newer than the newest reviewed manifest entry instead of checking only `latest`; process candidates oldest-first under bounded count, download-size, retry, and timeout limits; reject drafts, prereleases, unexpected tags, missing assets, and malformed checksum manifests; cross-check GitHub asset digests with the signed-in API response and official checksum manifest before executing the runner-platform binary; run dependency-free offline probes for version identity, required commands/flags, help/config surface, and preview behavior in a synthetic repository; run result-schema and adapter contract fixtures for the supported set; archive normalized release metadata, notes, probe results, runner platform, and digests as an artifact; open or update one marker-keyed GitHub issue per candidate with machine evidence and a mandatory human classification checklist.
- **Acceptance criteria:** Intermediate releases cannot be skipped; reruns are idempotent and do not duplicate issues; issue content includes only bounded normalized metadata, probe results, and links rather than copied release notes; upstream metadata is treated as untrusted text and never interpolated into shell or workflow expressions; a passing probe is scoped to its actual runner platform and labels only a candidate as machine-tested, not compatible or recommended; human review records one of `compatible`, `compatible-with-toolkit-change`, `incompatible`, or `unknown`, with changelog impact and required follow-up; no workflow path edits the manifest, CI pin, checksum, documentation, tag, release, or package registry.
- **Exclusions:** Automatic semantic changelog classification, automatic manifest or production-pin updates, automatic pull requests or merges, executing unverified assets, real LLM/provider calls, external repository data, or claiming platform coverage that was not actually exercised.
- **Validation:** Recorded synthetic GitHub release pages containing multiple unseen versions, pagination, reruns, drafts/prereleases, invalid tags, missing/oversized assets, checksum mismatch, malicious release text, probe regression, issue deduplication, and no-change behavior; workflow permissions and shell-safety checks; successful manual dry run against official metadata with writes disabled.
- **Release classification expectation:** `no-release`; subsequent compatibility bumps are classified separately.

## M1 Evidence architecture

### BL-004: Define the common repository evidence model

- **Status:** ready
- **Priority:** high
- **Roadmap theme:** M1 Evidence architecture
- **Dependencies:** Existing bounded context and repository-ref contracts.
- **Activation trigger:** M0 planning sources are merged.
- **Goal:** Give all collectors and projections one deterministic representation of repository facts.
- **Scoped deliverables:** Define dependency-free, schema-versioned evidence types for kind/typed value, source path, git ref, component scope, provenance, confidence, trust/sensitivity class, and optional staleness; specify stable identity, ordering, deduplication, redaction-before-storage, and global/per-kind bounds.
- **Acceptance criteria:** Existing context facts can be represented without losing trust or origin; raw secrets cannot enter the evidence store or serialized projections; unknown kinds/versions and malformed or over-limit facts degrade explicitly; serialization is deterministic and backward-readable across the supported schema set.
- **Exclusions:** OCR capability inspection, MCP transport, bootstrap prose, new ecosystem parsers, or network discovery.
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
- **Acceptance criteria:** Target content is read without checking it out or executing it; symlink, submodule, missing-object, shallow-clone, rename, and deleted-file behavior is explicit and repository-root constrained; source-only changes cannot self-authorize policy; added/removed/changed/unknown facts are reproducible.
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
- **Scoped deliverables:** Characterize current output with golden fixtures; move collectors behind evidence interfaces, add bounded storage, isolate bootstrap selection, and retain a renderer compatible with the current background contract during migration; remove each legacy collector only after parity or an explicitly approved behavior change is recorded.
- **Acceptance criteria:** Existing public context behavior remains covered; old/new paths cannot collect the same fact independently after migration; collectors are projection-independent; no bootstrap/MCP-specific duplicate collector path exists; rollout can compare projections deterministically before legacy removal.
- **Exclusions:** New parser breadth, changing the hard output limit, or enabling built-in MCP.
- **Validation:** Golden synthetic context fixtures, regression tests for truncation/redaction/guidance, and complete quality gate.
- **Release classification expectation:** `release-deferred` unless output behavior changes.

### BL-007: Deliver compact bootstrap and built-in evidence MCP atomically

- **Status:** planned
- **Priority:** high
- **Roadmap theme:** M1 Evidence architecture
- **Dependencies:** BL-002, BL-004 through BL-006, and current MCP validation.
- **Activation trigger:** Evidence collection and selection are projection-independent, and the supported OCR capability contract can validate MCP registration before review.
- **Goal:** Replace large background inventories with a compact trusted overview while preserving on-demand access to every removed evidence class.
- **Scoped deliverables:** Implement prioritized bootstrap planning; register a reserved `ocr_toolkit_evidence` server with bounded `ocr_toolkit_*` read-only tools; update OCR instructions to use those tools; define per-tool response and total-session evidence budgets plus deterministic pagination or truncation markers; retain `legacy_background` as compatibility and rollback mode; enable `compact_bootstrap` by default only after built-in MCP registration and capability validation succeed.
- **Acceptance criteria:** Bootstrap and MCP use the same evidence store and ship in one user-visible feature slice; compact mode never runs without a validated evidence server; registration failure fails closed or retains legacy mode according to the documented launch policy; detailed manifests remain available through MCP; omissions and degradation are explicit.
- **Exclusions:** Raising the hard limit, copying full guidance, generic file reads, shell execution, GitLab access, external URL fetches, documentation storage, or a release that removes detailed background evidence before MCP access exists.
- **Validation:** Budget and golden fixtures, protocol/root/traversal tests, registration/capability failures, legacy rollback, compact-mode gating, adversarial Markdown/redaction, and end-to-end synthetic OCR configuration.
- **Release classification expectation:** `release-required`.

## M2 Ecosystem and framework coverage

### BL-008: Resolve lockfile, runtime, and container evidence

- **Status:** planned
- **Priority:** high
- **Roadmap theme:** M2 Ecosystem and framework coverage
- **Dependencies:** BL-004 through BL-006.
- **Activation trigger:** Snapshot and delta semantics are stable.
- **Goal:** Distinguish declared constraints, locked, installed, runtime-detected, container-pinned, inferred, and unknown versions.
- **Scoped deliverables:** Strengthen actual-use formats for Python, JavaScript/TypeScript, Go, PHP, Ansible, containers, and GitLab CI; define precedence without collapsing declared, locked, installed, runtime, image tag, and immutable digest evidence; implement source/target resolution and deltas with provenance.
- **Acceptance criteria:** Each supported format has deterministic semantics and fixtures; platform/marker/workspace variants and conflicting sources remain distinct; mutable image tags are never represented as immutable pins; malformed/oversized files degrade without network access.
- **Exclusions:** Unused ecosystems, package-registry queries, arbitrary build execution, or treating declarations as resolved versions.
- **Validation:** Per-format source/target fixtures, conflict and limit cases, and common evidence-model contract tests.
- **Release classification expectation:** `release-required`.

### BL-009: Select and establish framework evidence plugins

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M2 Ecosystem and framework coverage
- **Dependencies:** BL-004, BL-005, and BL-008.
- **Activation trigger:** An anonymized inventory of pilot repositories identifies at least two high-value framework candidates with safe synthetic fixtures.
- **Goal:** Select and implement 2-3 framework plugins that improve review evidence without building code graphs.
- **Scoped deliverables:** Inventory pilot repositories without recording private names or contents; score candidates by prevalence, version-sensitive API surface, deterministic detectability, synthetic-fixture feasibility, and expected review-quality impact; record the selection decision; define a bounded plugin protocol and implement the selected providers. Existing Ansible parser maturity may support, but cannot substitute for, the scored selection.
- **Acceptance criteria:** The inventory and scoring justify each selected plugin; plugins expose framework identity, verified version, component scope, important configuration paths, and material deltas; they cannot run arbitrary commands or network requests and avoid whole-repository traversal when changed components are known.
- **Exclusions:** Route/call/symbol graphs, framework-specific reviewers, or speculative detection without version evidence.
- **Validation:** Positive/negative/multi-component fixtures, version-conflict and staleness cases, and plugin isolation tests.
- **Release classification expectation:** `release-required`.

### BL-010: Add evidence packs from demonstrated use cases

- **Status:** conditional
- **Priority:** medium
- **Roadmap theme:** M2 Ecosystem and framework coverage
- **Dependencies:** BL-008 and BL-009.
- **Activation trigger:** A real repository need identifies a missing ecosystem or framework and supplies safe synthetic fixtures and deterministic semantics.
- **Goal:** Extend coverage without accumulating shallow detectors.
- **Scoped deliverables:** Implement one coherent ecosystem or framework pack per activation, with provenance, bounds, source/target deltas, documentation, and public synthetic examples.
- **Acceptance criteria:** The use case and completion signal are documented before implementation; false-positive behavior and unsupported versions are explicit.
- **Exclusions:** Checkbox coverage, network resolution, runtime code execution, or bundles spanning unrelated ecosystems.
- **Validation:** Pack-specific fixtures plus common evidence and bootstrap/MCP projection contracts.
- **Release classification expectation:** `release-required`.

## M3 External MCP hardening

### BL-011: Threat-model and constrain external references

- **Status:** ready
- **Priority:** high
- **Roadmap theme:** M3 External MCP hardening
- **Dependencies:** Current MR metadata, external stdio MCP, allowlist, and secret-injection contracts.
- **Activation trigger:** Before automatic external-reference detection or provider-specific YouTrack/Confluence examples are introduced.
- **Goal:** Detect useful references without allowing untrusted metadata or retrieved content to control policy or tools.
- **Scoped deliverables:** Define configured project-key patterns, host/space allowlists, canonical parsing, reference and traversal bounds, audit metadata, narrow tool contracts, and prompt-injection instructions.
- **Acceptance criteria:** External content cannot change policy, suppress findings, authorize actions, modify permissions, or trigger writes; rejected and truncated references are auditable without leaking secrets.
- **Exclusions:** Content prefetch, recursive browsing, generic web access, or external-system mutation.
- **Validation:** Threat model, adversarial MR/issue/page fixtures, Unicode/URL canonicalization, bound tests, and attack-path review.
- **Release classification expectation:** `no-release` for the threat model alone; automatic detection or public integration behavior is classified separately.

### BL-012: Document current external read-only MCP operation

- **Status:** ready
- **Priority:** high
- **Roadmap theme:** M3 External MCP hardening
- **Dependencies:** BL-011 and the existing external stdio MCP configurator.
- **Activation trigger:** The external-reference threat model defines safe provider-specific examples.
- **Goal:** Make the toolkit's existing external MCP capability deployable without waiting for the Repository Evidence Engine.
- **Scoped deliverables:** Document generic stdio MCP, the HTTP-to-stdio proxy pattern, read-only YouTrack and Confluence configurations, explicit tool allowlists, protected environment injection, setup-command constraints, redaction, limits, and current fail-closed behavior using synthetic hosts and payloads.
- **Acceptance criteria:** Examples match the current implementation, expose narrow read tools only, keep credentials out of generated files and logs, distinguish configuration from future automatic reference detection, and require no built-in evidence MCP.
- **Exclusions:** Built-in/external composition, reserved evidence namespaces, external writes, generic URL fetch, documentation mirroring, or issue/page prefetch.
- **Validation:** Executable synthetic configurations, allowlist/secret/setup failure fixtures, redaction checks, link validation, and documentation contract tests.
- **Release classification expectation:** `no-release` for documentation-only work.

### BL-013: Compose external MCP with built-in evidence MCP

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M3 External MCP hardening
- **Dependencies:** BL-007, BL-011, and BL-012.
- **Activation trigger:** The built-in evidence server and current external MCP documentation are stable.
- **Goal:** Compose external knowledge tools with `ocr_toolkit_evidence` without replacement, shadowing, or permission broadening.
- **Scoped deliverables:** Define reserved server/tool namespaces, collision behavior, deterministic merge order, combined capability instructions, and synthetic composition examples for generic, YouTrack, Confluence, and documentation MCP servers.
- **Acceptance criteria:** External configuration cannot replace built-in evidence tools; collisions fail before OCR execution; combined examples preserve narrow read-only allowlists and protected secret injection.
- **Exclusions:** New provider transports, external writes, generic URL fetch, content prefetch, or duplicate evidence collectors.
- **Validation:** Composition order, reserved-name, collision, capability-rendering, redaction, and end-to-end synthetic configuration tests.
- **Release classification expectation:** `release-required`.

## M4 Policy and project guidance

### BL-014: Evolve accepted decisions into tolerant structured Markdown

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M4 Policy and project guidance
- **Dependencies:** BL-004, BL-005, BL-007, and current target-branch self-whitelisting guard.
- **Activation trigger:** Evidence model can preserve decision scope and provenance.
- **Goal:** Add optional Scope, Category, Review after, and Owner metadata without breaking existing decision documents.
- **Scoped deliverables:** Parse heading/rationale entries and optional bullet metadata; normalize unique decision IDs; define repository-relative glob semantics, Category as descriptive metadata, Owner as contact metadata, and `Review after` as an expiry signal rather than automatic deletion; tolerate unknown fields; filter by target branch and component scope; place summaries in bootstrap and full rationale in evidence MCP.
- **Acceptance criteria:** Existing files remain valid; duplicate IDs and unsafe scope patterns are reported deterministically; malformed optional metadata cannot invalidate unrelated decisions; expired decisions are surfaced as stale and do not silently suppress findings; Owner/Category cannot grant authority; source-branch edits never affect the current review.
- **Exclusions:** YAML, unconditional finding suppression, policy authorization, or mandatory metadata.
- **Validation:** Backward-compatibility, unknown/malformed field, scope, date, target/source, and size-bound fixtures.
- **Release classification expectation:** `release-required`.

### BL-015: Simplify project guidance after an upstream OCR contract exists

- **Status:** conditional
- **Priority:** medium
- **Roadmap theme:** M4 Policy and project guidance
- **Dependencies:** BL-004, BL-005, BL-007, and documented/tested upstream OCR automatic guidance behavior.
- **Activation trigger:** A supported OCR release proves in compatibility tests that its guidance mechanism can resolve the intended target-ref version rather than the source worktree path.
- **Goal:** Replace large excerpts with target-branch paths and short non-authoritative hints while preserving fail-closed handling.
- **Scoped deliverables:** Define root-to-file applicability and precedence for nested `AGENTS.md`/`CLAUDE.md`; discover applicable target-branch files without checkout or execution; exclude guidance changed, added, renamed, or deleted by the merge request; supply target-ref-aware paths/hints; permit OCR native tools to read only the intended target versions on demand.
- **Acceptance criteria:** Source changes and symlink/submodule indirection cannot self-instruct; conflicting nested guidance resolves deterministically; missing upstream capability retains current bounded behavior; guidance remains untrusted and never overrides system policy.
- **Exclusions:** Removing safeguards before the trigger, copying full guidance into bootstrap, or toolkit-specific instruction execution.
- **Validation:** Multi-scope target/source fixtures, changed-guidance attacks, capability fallback tests, and bootstrap budget tests.
- **Release classification expectation:** `release-required`.

## M5 Review profiles and quality measurement

### BL-016: Add explicit run-level review profiles

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M5 Review profiles and quality measurement
- **Dependencies:** BL-002 and BL-007.
- **Activation trigger:** Profile model and limit differences can be documented without changing per-tool routing.
- **Goal:** Offer `economy`, `standard`, and `strong` choices for one OCR review run.
- **Scoped deliverables:** Define explicit profile configuration selecting a run-level model and a documented closed set of existing OCR limits; publish the effective profile without credentials; validate profile/model availability through the compatibility contract, environment precedence, and rendered effective configuration.
- **Acceptance criteria:** One model remains active per run, `standard` preserves current behavior, explicit per-setting environment values override profile defaults, secrets remain environment-only, and unavailable model/capability combinations or unsupported profiles fail before OCR execution.
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
- **Scoped deliverables:** Define bounded low-cardinality metrics for latency, token use when available, evidence/MCP use, findings, repeats, suppression, resolution, and human ownership; define run/profile/schema-version identifiers, aggregation windows, retention, opt-in export, and local/no-export behavior.
- **Acceptance criteria:** Metrics contain no source, prompts, finding text, paths, user identities, secrets, external contents, or unbounded project/MR labels; missing provider telemetry is explicit; failed/partial and repeated runs are distinguishable and comparable without changing review behavior; telemetry failure cannot fail review.
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
- **Acceptance criteria:** Routing is deterministic and explainable, never uses untrusted content as authority, cannot let merge-request-controlled inputs select below a repository-configured minimum profile, never selects `ocr scan`, and falls back to the policy minimum (default `standard`) on uncertainty.
- **Exclusions:** Learned online routing, per-tool models, multiple agents, or silent policy changes.
- **Validation:** Offline replay, boundary/adversarial cases, fallback tests, and quality regression thresholds.
- **Release classification expectation:** `release-required`.

## M6 Later and conditional work

### BL-019: Run a native fuzzing campaign

- **Status:** parked
- **Priority:** medium
- **Roadmap theme:** M6 Later and conditional work
- **Dependencies:** Stable evidence/MCP parser interfaces from M1.
- **Activation trigger:** High-value parser targets, bounded CI resources, corpus ownership, and backend-selection criteria across Python 3.10-3.14 are agreed.
- **Goal:** Find crashes and invariant violations at untrusted evidence, MCP, result, GitLab payload, and registry-metadata boundaries.
- **Scoped deliverables:** Use a bounded spike to choose Atheris, property-based testing, or both for named targets and supported Python versions; define synthetic seeds; fuzz selected parsers; minimize and retain regressions; version corpora with parser contracts; evaluate public service integration only after useful local results.
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
- **Scoped deliverables:** Decide format/versioning, discovery location, target/source trust, explicit field-level environment precedence, migration, allowed non-secret fields, unknown/deprecated-key behavior, schema evolution, and redacted effective-config diagnostics before implementation.
- **Acceptance criteria:** Environment values retain explicit field-level precedence, secrets and secret-shaped keys are rejected from files, source-branch files cannot self-authorize, paths cannot escape the repository boundary, unknown/deprecated keys are actionable, and migration/rollback behavior is documented and tested.
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
- **Scoped deliverables:** First write a capability matrix covering authentication, diff positions, draft/pending reviews, discussion identities, resolution, pagination/rate limits, ambiguous writes, permissions, and idempotency; explicitly classify unsupported parity; then implement one provider boundary with synthetic API fixtures and public setup documentation.
- **Acceptance criteria:** Core remains provider-neutral, GitLab behavior does not regress, unsupported host capabilities fail or degrade explicitly rather than emulate unsafe parity, and the new host meets the approved lifecycle and security matrix.
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
