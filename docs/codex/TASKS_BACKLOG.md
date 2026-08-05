# Tasks Backlog

This file contains implementation-ready future work derived from the [toolkit strategy](../engineering/toolkit_strategy.md) and ordered by the [roadmap](../../ROADMAP.md). Active execution belongs in `PLANS.md`; roadmap outcomes are intentionally not repeated here.

Statuses are `ready`, `planned`, `parked`, `conditional`, or `owner action`. Release classification is an expectation to be confirmed when work is activated. Completed work is recorded in `PLANS.md` and the roadmap rather than retained as future backlog.

## Existing backlog reconciliation

| Previous item | Disposition | Result |
| --- | --- | --- |
| Native fuzzing campaign | Retained and revised | BL-019 connects fuzzing to the future evidence/MCP parser attack surface and keeps bounded CI and corpus ownership as activation requirements. |
| Additional provider adapters | Retained, clarified, and reprioritized | BL-021 is explicitly about code-hosting and review-host adapters beyond GitLab, not repository ecosystem/framework evidence. |
| File-based user configuration | Retained and redesigned | BL-020 waits for profile, MCP, and evidence schemas while preserving environment precedence and excluding secrets. |

## M2 Ecosystem and framework coverage

### BL-008: Resolve lockfile, runtime, and container evidence

- **Status:** planned
- **Priority:** high
- **Roadmap theme:** M2 Ecosystem and framework coverage
- **Dependencies:** Established M1 evidence, snapshot, and delta contracts.
- **Activation trigger:** Snapshot and delta semantics are stable.
- **Goal:** Distinguish declared constraints, locked, installed, runtime-detected, container-pinned, inferred, and unknown versions.
- **Scoped deliverables:** Strengthen actual-use formats for Python, JavaScript/TypeScript, Go, PHP, Ansible, containers, and GitLab CI; define precedence without collapsing declared, locked, installed, runtime, image tag, and immutable digest evidence; implement source/target resolution and deltas with provenance.
- **Acceptance criteria:** Each supported format has deterministic semantics and fixtures; platform/marker/workspace variants and conflicting sources remain distinct; mutable image tags are never represented as immutable pins; malformed/oversized files degrade without network access; every domain that can support negative inference publishes applicable scoped completeness through the established evidence-coverage contract.
- **Exclusions:** Unused ecosystems, package-registry queries, arbitrary build execution, or treating declarations as resolved versions.
- **Validation:** Per-format source/target fixtures, conflict and limit cases, and common evidence-model contract tests.
- **Release classification expectation:** `release-required`.
- **Upstream overlap:** OCR 1.8.8 can now select Nix and Haskell files for review, but selection and generic rules do not resolve dependency/runtime versions or provide source/target evidence. BL-008 therefore remains planned with unchanged scope.

### BL-009: Select and establish framework evidence plugins

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M2 Ecosystem and framework coverage
- **Dependencies:** Established M1 evidence/snapshot contracts and BL-008.
- **Activation trigger:** An anonymized inventory of pilot repositories identifies at least two high-value framework candidates with safe synthetic fixtures.
- **Goal:** Select and implement 2-3 framework plugins that improve review evidence without building code graphs.
- **Scoped deliverables:** Inventory pilot repositories without recording private names or contents; score candidates by prevalence, version-sensitive API surface, deterministic detectability, synthetic-fixture feasibility, and expected review-quality impact; record the selection decision; define a bounded plugin protocol and implement the selected providers. Existing Ansible parser maturity may support, but cannot substitute for, the scored selection.
- **Acceptance criteria:** The inventory and scoring justify each selected plugin; plugins expose framework identity, verified version, component scope, important configuration paths, material deltas, and applicable scoped completeness; they cannot run arbitrary commands or network requests and avoid whole-repository traversal when changed components are known. Ansible's established coverage implementation is a reusable first adopter, not a substitute for selecting future plugins from demonstrated use.
- **Exclusions:** Route/call/symbol graphs, framework-specific reviewers, or speculative detection without version evidence.
- **Validation:** Positive/negative/multi-component fixtures, version-conflict and staleness cases, and plugin isolation tests.
- **Release classification expectation:** `release-required`.
- **Upstream overlap:** OCR 1.8.8's built-in Nix/Haskell rules improve language review but do not identify frameworks, versions, component scope, provenance, or completeness. They do not satisfy the plugin selection trigger or any BL-009 acceptance criterion.

### BL-010: Add evidence packs from demonstrated use cases

- **Status:** conditional
- **Priority:** medium
- **Roadmap theme:** M2 Ecosystem and framework coverage
- **Dependencies:** BL-008 and BL-009.
- **Activation trigger:** A real repository need identifies a missing ecosystem or framework and supplies safe synthetic fixtures and deterministic semantics.
- **Goal:** Extend coverage without accumulating shallow detectors.
- **Scoped deliverables:** Implement one coherent ecosystem or framework pack per activation, with provenance, bounds, source/target deltas, documentation, and public synthetic examples.
- **Acceptance criteria:** The use case and completion signal are documented before implementation; false-positive behavior and unsupported versions are explicit through the shared scoped coverage contract.
- **Exclusions:** Checkbox coverage, network resolution, runtime code execution, or bundles spanning unrelated ecosystems.
- **Validation:** Pack-specific fixtures plus common evidence and bootstrap/MCP projection contracts.
- **Release classification expectation:** `release-required`.
- **Upstream overlap:** Built-in OCR language allowlists and rules are review-engine capabilities, not toolkit evidence packs. OCR 1.8.8 creates no demonstrated missing-evidence use case and does not activate BL-010.

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

### BL-012: Define and validate managed OAuth for remote MCP

- **Status:** ready
- **Priority:** high
- **Roadmap theme:** M3 External MCP hardening
- **Dependencies:** Native remote Streamable HTTP and stdio proxy fallback shipped with toolkit 0.3.1, plus BL-011 external-content constraints.
- **Activation trigger:** A supported provider requires authorization-code OAuth rather than static environment-backed headers, and a reviewed stdio proxy is insufficient for pilot operations.
- **Goal:** Add a provider-neutral authorization boundary without placing long-lived OAuth material in repository content or OCR config.
- **Scoped deliverables:** Define authorization-code plus PKCE, browser callback ownership, refresh and revocation, secure token persistence, tenant/resource binding, dynamic-client-registration policy, sanitized audit events, and provider conformance fixtures before selecting an implementation boundary.
- **Acceptance criteria:** Tokens never enter argv, repository files, generated context, or logs; refresh/revocation and tenant changes fail closed; synthetic static-header and browser-OAuth fixtures preserve native HTTP and stdio fallback.
- **Exclusions:** Provider SDKs in the zero-dependency runtime, automatic reference discovery, writes, generic web access, or treating a permanent token as OAuth lifecycle support.
- **Validation:** Threat-model review plus synthetic authorization, PKCE, callback, refresh, revocation, tenant mismatch, persistence-permission, redaction, and OCR integration cases.
- **Release classification expectation:** `release-required` once public authorization behavior is selected.

### BL-013: Compose external MCP with built-in evidence MCP

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M3 External MCP hardening
- **Dependencies:** Established M1 built-in composition boundary, BL-011, and BL-012.
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
- **Dependencies:** Established M1 evidence/MCP contracts and current target-branch self-whitelisting guard.
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
- **Dependencies:** Established M1 evidence/MCP contracts and documented/tested upstream OCR automatic guidance behavior.
- **Activation trigger:** A supported OCR release proves in compatibility tests that its guidance mechanism can resolve the intended target-ref version rather than the source worktree path.
- **Goal:** Replace large excerpts with target-branch paths and short non-authoritative hints while preserving fail-closed handling.
- **Scoped deliverables:** Define root-to-file applicability and precedence for nested `AGENTS.md`/`CLAUDE.md`; discover applicable target-branch files without checkout or execution; exclude guidance changed, added, renamed, or deleted by the merge request; supply target-ref-aware paths/hints; permit OCR native tools to read only the intended target versions on demand.
- **Acceptance criteria:** Source changes and symlink/submodule indirection cannot self-instruct; conflicting nested guidance resolves deterministically; missing upstream capability retains current bounded behavior; guidance remains untrusted and never overrides system policy.
- **Exclusions:** Removing safeguards before the trigger, copying full guidance into bootstrap, or toolkit-specific instruction execution.
- **Validation:** Multi-scope target/source fixtures, changed-guidance attacks, capability fallback tests, and bootstrap budget tests.
- **Release classification expectation:** `release-required`.

## M5 Review profiles and quality measurement

Telemetry is intentionally outside M1. OCR owns token, cost, budget, provider-level review duration, LLM request, and per-tool call duration/count telemetry; the toolkit reuses those upstream signals instead of adding a second implementation. M5 audits only the remaining GitLab lifecycle, bounded evidence/MCP, posting, and review-value gaps before deciding whether any provider-neutral toolkit telemetry is needed.

### BL-016: Add explicit run-level review profiles

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M5 Review profiles and quality measurement
- **Dependencies:** The established M1 built-in MCP lifecycle and an OCR compatibility entry advertising per-run model/provider override capability. OCR 1.8.7 satisfies the upstream capability dependency.
- **Activation trigger:** Profile model and limit differences can be documented without changing per-tool routing; the remaining trigger is an owner-approved closed profile matrix and precedence contract.
- **Goal:** Offer `economy`, `standard`, and `strong` choices for one OCR review run.
- **Scoped deliverables:** Define explicit profile configuration selecting a run-level model and a documented closed set of existing OCR limits; map the profile to OCR's per-run override rather than mutating persistent OCR configuration; publish the effective profile and observed additive result identity without credentials; validate profile/model availability through optional capabilities in the compatibility contract, environment precedence, and rendered effective configuration.
- **Acceptance criteria:** One model remains active per run, `standard` preserves current behavior, explicit per-setting environment values override profile defaults, secrets remain environment-only, and unavailable model/capability combinations or unsupported profiles fail before OCR execution.
- **Exclusions:** Per-file/per-tool model routing, hidden heuristics, multi-agent orchestration, or full-repository scan profiles.
- **Validation:** Profile matrix, precedence, preflight, configuration-rendering, and compatibility tests.
- **Release classification expectation:** `release-required`.

### BL-017: Measure review cost and quality signals

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M5 Review profiles and quality measurement
- **Dependencies:** BL-016 and stable discussion/fingerprint lifecycle.
- **Activation trigger:** Explicit profiles can label comparable runs, and M1 E2E/operational evidence demonstrates material gaps that upstream OCR telemetry and structured result artifacts cannot cover reliably.
- **Goal:** Produce privacy-safe evidence for profile tuning and any future routing decision.
- **Scoped deliverables:** Reuse OCR token, cost, budget, latency, request, and tool-call telemetry plus OCR 1.8.7's additive provider/model result identity and the established review-health, failed-file, finding-publication, suppression, omission, and posting receipts, then audit structured result artifacts for the remaining gaps. If GitLab lifecycle, bounded evidence/MCP, posting, or review-value gaps justify a toolkit layer, define one provider-neutral, dependency-free event/metric model, bounded label vocabulary, no-op/local JSON exporters, optional upstream/OTLP bridge, failure isolation, and schema/version ownership. Candidate toolkit-only coverage includes evidence/store bounds and degradation; bootstrap size; independently attributable MCP readiness and usage; repeated discussion lifecycle; compatibility reasons; and cache/profile identifiers. Implement only signals that cannot be derived safely and reliably from OCR telemetry or bounded result artifacts.
- **Acceptance criteria:** OCR remains the source for token, cost, and budget telemetry. The gap audit may conclude that OCR telemetry plus bounded result-derived reporting is sufficient, in which case no toolkit telemetry runtime is added. If a layer is justified, metrics contain no source, prompts, tool arguments/results, finding text, paths, URLs, user identities, secrets, external contents, or unbounded project/MR labels; labels use closed vocabularies and bounded cardinality; built-in and optional MCP servers remain independently attributable; OCR and toolkit metrics cannot double-count the same semantic event; missing upstream data is explicit; failed/partial/skipped and repeated runs are distinguishable without changing review behavior; telemetry failure cannot fail review.
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
- **Activation trigger:** High-value parser targets, bounded CI resources, corpus ownership, and backend-selection criteria across Python 3.12-3.14 are agreed.
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
