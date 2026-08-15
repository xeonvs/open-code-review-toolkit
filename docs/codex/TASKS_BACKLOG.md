# Tasks Backlog

This file contains implementation-ready future work derived from the [toolkit strategy](../engineering/toolkit_strategy.md) and ordered by the [roadmap](../../ROADMAP.md). Active repository work belongs in `PLANS.md`; roadmap outcomes are intentionally not repeated here.

Statuses are `ready`, `planned`, `parked`, `conditional`, or `owner action`. Release classification is an expectation to be confirmed when work is activated. Completed work is reflected in the roadmap and stable execution-history archive rather than retained as future backlog.

## Existing backlog reconciliation

| Previous item | Disposition | Result |
| --- | --- | --- |
| Native fuzzing campaign | Retained and revised | BL-019 connects fuzzing to the future evidence/MCP parser attack surface and keeps bounded CI and corpus ownership as activation requirements. |
| Additional provider adapters | Retained, clarified, and reprioritized | BL-021 is explicitly about code-hosting and review-host adapters beyond GitLab, not repository ecosystem/framework evidence. |
| File-based user configuration | Retained and redesigned | BL-020 waits for profile, MCP, and evidence schemas while preserving environment precedence and excluding secrets. |
| M2 evidence gaps (BL-008) | Completed and removed | Demonstrated framework resolution, component ownership, scoped completeness, and first-class MCP delta projection ship through the shared evidence contracts; unproven formats are not retained as mandatory work. |
| M2 framework selection (BL-009) | Completed and removed | The anonymized selection produced bounded static Jinja2, Go web, Symfony/Twig, and React/Next providers with synthetic cross-provider validation and no second MCP. |
| M2 milestone closure | Completed | Stable 0.5.0 delivery and independent external readback establish M2; BL-010 remains a conditional M6 extension and is not unfinished M2 scope. |
| M4 accepted decisions (BL-014) | Completed and removed | Structured target-only decisions now preserve deterministic identity, optional metadata, safe scope, applicability, staleness, and bounded bootstrap/MCP projections without granting suppression authority. |
| M4 project guidance (BL-015) | Completed and removed | Immutable target guidance now has bounded discovery, deterministic nested applicability and precedence, changed-guidance exclusion, compact bootstrap hints, and full text through the existing read-only evidence MCP. |
| M4 milestone closure | Completed | Independently verified stable v0.6.0 artifacts, provenance, hashes, annotated tag, immutable Release, supported-Python installs, and release receipts establish M4; later target-policy identity work extends rather than reopens it. |

## M3 External MCP hardening

### BL-011: Threat-model and constrain external references

- **Status:** ready
- **Priority:** high
- **Roadmap theme:** M3 External MCP hardening
- **Dependencies:** Bounded untrusted MR context, external stdio MCP, allowlist, and secret-injection contracts.
- **Activation trigger:** Met by the 0.6.1 MR-context boundary; complete this threat model before automatic external-reference detection or provider-specific YouTrack/Confluence examples are introduced.
- **Goal:** Detect useful references without allowing untrusted metadata or retrieved content to control policy or tools.
- **Scoped deliverables:** Define configured project-key patterns, host/space allowlists, canonical parsing, reference and traversal bounds, audit metadata, narrow tool contracts, and prompt-injection instructions.
- **Acceptance criteria:** External content cannot change policy, suppress findings, authorize actions, modify permissions, or trigger writes; rejected and truncated references are auditable without leaking secrets.
- **Exclusions:** Content prefetch, recursive browsing, generic web access, or external-system mutation.
- **Validation:** Threat model, adversarial MR/issue/page fixtures, Unicode/URL canonicalization, bound tests, and attack-path review.
- **Release classification expectation:** `no-release` for the threat model alone; automatic detection or public integration behavior is classified separately.

### BL-012: Define and validate managed OAuth for remote MCP

- **Status:** conditional
- **Priority:** low
- **Roadmap theme:** M3 External MCP hardening
- **Dependencies:** Established native remote Streamable HTTP and stdio proxy fallback, plus BL-011 only for provider examples that retrieve untrusted external content.
- **Activation trigger:** A supported provider requires authorization-code OAuth rather than static environment-backed headers, and a reviewed stdio proxy is insufficient for pilot operations.
- **Goal:** Add a provider-neutral authorization boundary without placing long-lived OAuth material in repository content or OCR config.
- **Scoped deliverables:** Define authorization-code plus PKCE, browser callback ownership, refresh and revocation, secure token persistence, tenant/resource binding, dynamic-client-registration policy, sanitized audit events, and provider conformance fixtures before selecting an implementation boundary.
- **Acceptance criteria:** Tokens never enter argv, repository files, generated context, or logs; refresh/revocation and tenant changes fail closed; synthetic static-header and browser-OAuth fixtures preserve native HTTP and stdio fallback.
- **Exclusions:** Provider SDKs in the zero-dependency runtime, automatic reference discovery, writes, generic web access, or treating a permanent token as OAuth lifecycle support.
- **Validation:** Threat-model review plus synthetic authorization, PKCE, callback, refresh, revocation, tenant mismatch, persistence-permission, redaction, and OCR integration cases.
- **Release classification expectation:** `release-required` once public authorization behavior is selected.

### BL-013: Validate provider-specific read-only MCP composition examples

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M3 External MCP hardening
- **Dependencies:** BL-011 before provider-specific examples or automatic external-reference instructions. Managed OAuth is not a prerequisite for static-header, stdio, YouTrack, Confluence, or documentation MCP composition.
- **Activation trigger:** The external-reference threat model is complete and a provider example has a supported narrow read-only tool contract.
- **Goal:** Publish synthetic provider examples on top of the established generic composition boundary without broadening permissions or duplicating evidence.
- **Implemented baseline:** Ordinary reviews always register the built-in evidence server; external stdio and native HTTPS servers remain independent entries; merge and replacement semantics preserve the built-in entry; reserved server/tool names, global tool collisions, deterministic capability inventory, protected environment/header injection, bootstrap composition, result receipts, and installed-artifact integration tests are complete. Bounded MR title, description, labels, and source branch are now invocation-trust evidence, but 0.6.1 deliberately performs no reference extraction, URL traversal, content prefetch, or provider-specific tool routing.
- **Scoped deliverables:** Add threat-model-aligned synthetic configuration and usage guidance for selected YouTrack, Confluence, and documentation MCP servers; validate their narrow read-only allowlists, protected secret injection, and combined bootstrap instructions through the existing composition contract.
- **Acceptance criteria:** Each example uses only synthetic services, cannot replace or shadow built-in evidence tools, exposes no generic URL fetch or write tool, and passes provider-specific configuration, redaction, capability-rendering, and end-to-end synthetic validation.
- **Exclusions:** New provider transports, external writes, generic URL fetch, content prefetch, or duplicate evidence collectors.
- **Validation:** Provider configuration, capability-rendering, redaction, and end-to-end synthetic example tests; do not duplicate the established core composition matrix.
- **Release classification expectation:** `no-release` for threat-model and documentation examples; any new public runtime behavior is classified separately.

## M5 Review profiles and quality measurement

Telemetry is intentionally outside M1. OCR owns token, cost, budget, provider-level review duration, LLM request, and per-tool call duration/count telemetry; the toolkit reuses those upstream signals instead of adding a second implementation. M5 audits only the remaining GitLab lifecycle, bounded evidence/MCP, posting, and review-value gaps before deciding whether any provider-neutral toolkit telemetry is needed.

### BL-016: Add explicit run-level review profiles

- **Status:** planned
- **Priority:** medium
- **Roadmap theme:** M5 Review profiles and quality measurement
- **Dependencies:** The established M1 built-in MCP lifecycle and an OCR compatibility entry advertising per-run model/provider override capability. OCR 1.8.7 satisfies the upstream capability dependency.
- **Activation trigger:** Profile model and limit differences can be documented without changing per-tool routing; the remaining trigger is an owner-approved closed profile matrix and precedence contract.
- **Upstream overlap:** OCR 1.8.10 makes tool-parameter rendering deterministic, OCR 1.9.0 exposes a per-file token limit, and OCR 1.9.1 improves Anthropic cache breakpoints. These are useful profile inputs but do not define the toolkit's closed profile matrix, precedence, validation, or effective-configuration contract, so BL-016 remains planned.
- **Goal:** Offer `economy`, `standard`, and `strong` choices for one OCR review run.
- **Scoped deliverables:** Define explicit profile configuration selecting a run-level model and a documented closed set of existing OCR limits; map the profile to OCR's per-run override rather than mutating persistent OCR configuration; publish the effective profile and observed additive result identity without credentials; validate profile/model availability through optional capabilities in the compatibility contract, environment precedence, and rendered effective configuration.
- **Acceptance criteria:** One model remains active per run, `standard` preserves current behavior, explicit per-setting environment values override profile defaults, secrets remain environment-only, and unavailable model/capability combinations or unsupported profiles fail before OCR execution.
- **Exclusions:** Per-file/per-tool model routing, hidden heuristics, multi-agent orchestration, or full-repository scan profiles.
- **Validation:** Profile matrix, precedence, preflight, configuration-rendering, and compatibility tests.
- **Release classification expectation:** `release-required`.

### BL-017: Audit remaining review measurement gaps

- **Status:** ready
- **Priority:** medium
- **Roadmap theme:** M5 Review profiles and quality measurement
- **Dependencies:** Established discussion/fingerprint lifecycle, structured OCR result normalization, review-health reporting, failed-file coverage, finding/posting receipts, and MCP-use attribution. BL-016 is required only for later comparisons between named profiles, not for the gap audit.
- **Activation trigger:** Met for the audit: current OCR telemetry and toolkit result-derived receipts are sufficient to inventory available signals before any new telemetry layer is proposed.
- **Upstream overlap:** OCR 1.8.10's deterministic tool rendering and OCR 1.9.1's Anthropic cache optimization reduce upstream comparison or execution cost noise. OCR 1.9.4 adds the session ID to terminal summaries while leaving JSON output unchanged; that is useful OCR-owned correlation evidence for resume and audit work, but it is high-cardinality run identity rather than a missing toolkit metric or a reason to duplicate telemetry. The `TraceSummary` struct is an internal upstream refactor with unchanged output. The now-ready audit must determine whether current upstream telemetry, session correlation, and toolkit result-derived receipts already suffice.
- **Goal:** Determine whether any privacy-safe toolkit telemetry is still necessary before implementing metrics or profile routing.
- **Scoped deliverables:** Inventory OCR token, cost, budget, latency, request, tool-call, and provider/model identity alongside established review health, failed-file coverage, findings, suppression, omission, posting, and MCP-use receipts. Document only the remaining lifecycle, evidence degradation, repeated-discussion, compatibility, or review-value gaps. If no material gap remains, close the item without a runtime layer; any justified implementation becomes a separately scoped release-classified follow-up.
- **Acceptance criteria:** The audit maps every available signal to its current authoritative source, distinguishes derived from genuinely missing data, records privacy/cardinality constraints for any gap, and reaches an explicit no-new-layer or separately scoped follow-up conclusion. OCR remains the source for token, cost, budget, request, latency, and tool-call telemetry; the audit itself adds no runtime, exporter, or public schema.
- **Exclusions:** User surveillance, ranking developers, automatic routing, or mandatory external telemetry.
- **Validation:** Representative structured-result and repeated-discussion fixtures, privacy review, and a source-to-signal coverage matrix; exporter tests belong only to a later approved implementation.
- **Release classification expectation:** `no-release` for the audit; a later public telemetry contract is classified separately.

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

### BL-010: Add evidence packs from demonstrated use cases

- **Status:** conditional
- **Priority:** medium
- **Roadmap theme:** M6 Later and conditional work
- **Dependencies:** Established evidence, snapshot/delta, scoped-completeness, static-plugin, and built-in MCP projection contracts; only the boundary consumed by the demonstrated pack is required.
- **Activation trigger:** A real repository need identifies a missing ecosystem or framework and supplies safe synthetic fixtures and deterministic semantics.
- **Goal:** Extend coverage without accumulating shallow detectors.
- **Scoped deliverables:** Implement one coherent ecosystem or framework pack per activation, with provenance, bounds, source/target deltas, documentation, and public synthetic examples.
- **Acceptance criteria:** The use case and completion signal are documented before implementation; false-positive behavior and unsupported versions are explicit through the shared scoped coverage contract.
- **Exclusions:** Checkbox coverage, network resolution, runtime code execution, or bundles spanning unrelated ecosystems.
- **Validation:** Pack-specific fixtures plus common evidence and bootstrap/MCP projection contracts.
- **Release classification expectation:** `release-required`.
- **Upstream overlap:** Built-in OCR language allowlists and rules are review-engine capabilities, not toolkit evidence packs. A new reviewable language alone creates no demonstrated missing-evidence use case and does not activate BL-010.

### BL-019: Run a native fuzzing campaign

- **Status:** parked
- **Priority:** medium
- **Roadmap theme:** M6 Later and conditional work
- **Dependencies:** Stable evidence/MCP parser interfaces from M1; this technical prerequisite is complete.
- **Activation trigger:** Not met: high-value parser targets, bounded CI resources, corpus ownership, and backend-selection criteria across Python 3.12-3.14 are not yet agreed.
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
- **Dependencies:** MCP composition and evidence schemas are established. A profile schema is a dependency only if profiles are included in the proposed file contract.
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
