# Tasks Backlog

This file contains implementation-ready future work derived from the [toolkit strategy](../engineering/toolkit_strategy.md) and ordered by the [roadmap](../../ROADMAP.md). Active repository work belongs in `PLANS.md`; roadmap outcomes are intentionally not repeated here.

Statuses are `ready`, `planned`, `parked`, `conditional`, or `owner action`. Release classification is an expectation to be confirmed when work is activated. Completed work is reflected in the roadmap and stable execution-history archive rather than retained as future backlog.

## Existing backlog reconciliation

| Previous item | Disposition | Result |
| --- | --- | --- |
| M2 evidence gaps (BL-008) | Completed and removed | Demonstrated framework resolution, component ownership, scoped completeness, and first-class MCP delta projection ship through shared evidence contracts. |
| M2 framework selection (BL-009) | Completed and removed | Bounded static Jinja2, Go web, Symfony/Twig, and React/Next providers ship with synthetic cross-provider validation and no second MCP. |
| M2 milestone closure | Completed | Stable 0.5.0 delivery and external readback establish M2; BL-010 remains a conditional M7 extension. |
| M3 generic external-MCP qualification (BL-011) | Completed and removed | Checksum-verified OCR 1.9.5, the production `ocr-ci review` path, a local model peer, and a real stdio MCP peer establish the documented direct-composition safe-use envelope and its claim limits. |
| M3 provider examples (BL-013) | Removed | Direct provider examples over model-selected unrestricted arguments are not the target architecture; valid synthetic adapter qualification moves behind the BL-023 broker boundary. |
| Same-session external-MCP annotation enforcement (#103) | Removed / not planned | This repeated the removed direct-provider path: generic direct MCP remains privileged operator configuration, while future external records stay behind the BL-023 broker. A server-authored annotation is not semantic non-mutation proof. |
| M4 accepted decisions (BL-014) | Completed and removed | Structured target-only decisions preserve deterministic identity, safe applicability, staleness, and bounded projections without suppression authority. |
| M4 project guidance (BL-015) | Completed and removed | Immutable target guidance has bounded discovery, deterministic applicability/precedence, changed-guidance exclusion, and full text through the built-in evidence MCP. |
| M4 milestone closure | Completed | Stable v0.6.0 and protected-target identity readback establish M4 without making later context enrichment part of it. |
| OpenSSF Best Practices publication (BL-022) | Completed historically and not reused | The stable execution history records the passing badge publication and closure; the next identifier is BL-023. |
| Native fuzzing campaign | Retained and revised | BL-019 keeps its activation requirements and includes the established M5 parsers, handles, schemas, and hostile adapter responses in its candidate inventory. |
| File-based user configuration | Retained and clarified | BL-020 remains parked; M5 owns only its narrow protected-target context/DLP policy, not a general configuration framework. |
| Additional provider adapters | Retained and clarified | BL-021 remains conditional; future forge parity includes discussion, snapshot, and protected same-revision CI-outcome capabilities without blocking GitLab-first M5. |
| M5 bounded review-context enrichment (BL-023) | Completed and removed | The v0.7.0 release establishes the protected policy, GitLab discussion, broker/store/handle, fixed context-tool, containment, publication-DLP, receipt, setup-diagnostic, and CI-uncertainty boundaries tracked by #107-#111. The complete plan and release checkpoint are preserved in the execution-history archive. |
| Review measurement gaps (BL-017) | Completed and removed | The toolkit 0.8.2 source-to-signal audit concludes `no-new-layer`: OCR retains provider/review telemetry ownership, while toolkit receipts and count-only DLP events retain deterministic lifecycle ownership. Group labels and path-derived keys are explicitly classified as untrusted, high-cardinality upstream telemetry. |

## M3 External MCP hardening

M3 is established. BL-011 is complete and recorded above rather than retained as future work. BL-012 is an authentication extension whose trigger is not met; authentication never substitutes for resource authorization and does not block M3 or BL-023.

### BL-012: Define and validate managed OAuth for remote MCP

- **Status:** conditional
- **Priority:** low
- **Roadmap theme:** M3 External MCP hardening
- **Dependencies:** Established native remote Streamable HTTP and stdio proxy fallback. The completed BL-011 safe-use envelope applies to any direct provider composition.
- **Activation trigger:** A supported provider requires authorization-code OAuth rather than static environment-backed headers, and a reviewed stdio proxy is insufficient for pilot operations.
- **Goal:** Add a provider-neutral authentication lifecycle without placing long-lived OAuth material in repository content or OCR config; object authorization remains server-owned and separate.
- **Scoped deliverables:** Define authorization-code plus PKCE, browser callback ownership, refresh/revocation, secure token persistence, tenant/resource binding, dynamic-client-registration policy, sanitized audit events, and provider conformance fixtures before selecting an implementation boundary.
- **Acceptance criteria:** Tokens never enter argv, repository files, generated context, or logs; refresh/revocation and tenant changes fail closed; synthetic static-header and browser-OAuth fixtures preserve native HTTP and stdio fallback.
- **Exclusions:** Resource authorization by token presence, automatic reference discovery, writes, generic web access, or treating a permanent token as OAuth lifecycle support.
- **Validation:** Threat-model review plus synthetic authorization, PKCE, callback, refresh, revocation, tenant mismatch, persistence-permission, redaction, and OCR integration cases.
- **Release classification expectation:** `release-required` once public authorization behavior is selected.

## M6 Profiles and quality measurement

Provider/network telemetry remains outside M1 and M5. OCR owns token, cost, budget, provider-level review duration, request, and tool-call telemetry. The toolkit exposes only validated provider-neutral token buckets, distinguishes OCR-wide tool totals from verified MCP-server and count-only evidence-action use, and carries deterministic publication-DLP state in receipt v6, a parseable GitLab summary marker, and a structured local log event; it adds no exporter or endpoint. The 0.8.5 development line adds at most one bounded toolkit-authored CI failure diagnostic from closed retry-report enums and counts, not provider telemetry or an export path. M6 audits whether result-derived lifecycle signals need provider-neutral export/alert routing instead of duplicating OCR telemetry.

### BL-016: Evaluate explicit run-level model profiles

- **Status:** parked
- **Priority:** medium
- **Roadmap theme:** M6 Profiles and quality measurement
- **Dependencies:** Established built-in MCP lifecycle and OCR per-run model/provider overrides; OCR 1.8.7 satisfies the capability dependency.
- **Activation trigger:** Not met. Activate only after repeated operations show direct settings are insufficient and the owner approves a closed model/provider matrix plus precedence contract.
- **Upstream overlap:** OCR 1.8.7 supplies direct run-level selection; OCR 1.9.0 per-file and 1.9.5 aggregate budgets remain explicit completeness controls, not profile defaults.
- **Goal:** If need appears, offer `economy`, `standard`, and `strong` aliases for one OCR run without hiding aggregate, per-file, or tool controls.
- **Scoped deliverables:** Define an owner-approved closed matrix and precedence contract; map an alias to one OCR run; publish effective non-secret identity; validate compatibility and environment precedence.
- **Acceptance criteria:** One model remains active per run, `standard` preserves current behavior, explicit provider/model settings override profile aliases, aggregate/per-file/tool limits remain independent explicit operator inputs, secrets remain environment-only, and unavailable combinations fail before OCR execution.
- **Exclusions:** Hidden budgets, per-file/per-tool routing, multi-agent orchestration, or full-repository scan profiles.
- **Validation:** Profile matrix, precedence, preflight, rendering, and compatibility tests.
- **Release classification expectation:** `release-required`.

### BL-018: Evaluate conservative automatic profile routing

- **Status:** conditional
- **Priority:** low
- **Roadmap theme:** M6 Profiles and quality measurement
- **Dependencies:** BL-016, the completed BL-017 ownership audit, and an owner-approved quality/cost policy; M5 is not a dependency.
- **Activation trigger:** Representative metrics demonstrate a stable deterministic rule that improves an explicit objective without reducing safety.
- **Goal:** Select one run-level profile conservatively from trusted bounded inputs.
- **Scoped deliverables:** Document the decision rule, inputs, fallback, observability, and opt-out; implement only after replay evaluation and owner approval.
- **Acceptance criteria:** Routing is deterministic and explainable, never uses untrusted content as authority, cannot let merge-request-controlled inputs select below a repository-configured minimum profile, never selects `ocr scan`, and falls back to the policy minimum (default `standard`) on uncertainty.
- **Exclusions:** Learned online routing, per-tool models, multiple agents, or silent policy changes.
- **Validation:** Offline replay, adversarial boundaries, fallback tests, and quality thresholds.
- **Release classification expectation:** `release-required`.

## M7 Later and conditional work

### BL-010: Add evidence packs from demonstrated use cases

- **Status:** conditional
- **Priority:** medium
- **Roadmap theme:** M7 Later and conditional work
- **Dependencies:** Established evidence, snapshot/delta, scoped-completeness, static-plugin, and built-in MCP contracts.
- **Activation trigger:** A real repository need identifies a missing ecosystem/framework and supplies safe synthetic fixtures and deterministic semantics.
- **Goal:** Extend coverage without accumulating shallow detectors.
- **Scoped deliverables:** Implement one coherent ecosystem or framework pack per activation, with provenance, bounds, source/target deltas, documentation, and public operational examples using safe placeholders.
- **Acceptance criteria:** The use case and completion signal are documented before implementation; false-positive behavior and unsupported versions are explicit through the shared scoped coverage contract.
- **Exclusions:** Checkbox coverage, network resolution, runtime execution, or unrelated bundles.
- **Validation:** Pack fixtures plus common evidence/bootstrap/MCP contracts.
- **Upstream overlap:** OCR language allowlists and review rules are review-engine capabilities; OCR 1.11.0 Handlebars/Mustache selection improves review coverage but does not supply a framework evidence contract or activate an evidence pack.
- **Release classification expectation:** `release-required`.

### BL-019: Run a native fuzzing campaign

- **Status:** parked
- **Priority:** medium
- **Roadmap theme:** M7 Later and conditional work
- **Dependencies:** Stable evidence/MCP parser interfaces from M1; M5 targets enter the inventory only after their contracts exist.
- **Activation trigger:** Not met: named targets, bounded CI resources, corpus ownership, and backend criteria across Python 3.12-3.14 are not agreed.
- **Goal:** Find crashes and invariant violations at untrusted evidence, MCP, result, GitLab payload, registry-metadata, and M5 parser/protocol boundaries.
- **Scoped deliverables:** Candidate targets include current evidence/MCP/result/GitLab/registry parsers plus M5 policy parsers, recognizers, handle codec, broker schema, CI-outcome adapter/store readback, and hostile adapter responses. Select a bounded backend, synthetic seeds, corpus ownership, minimization, and regression policy before activation.
- **Acceptance criteria:** Targets are deterministic and bounded, minimized failures become tests, corpora contain no repository/provider secrets, and ownership is explicit.
- **Exclusions:** Unbounded CI, production data, blanket fuzzing, or a runtime dependency.
- **Validation:** Reproducible smoke campaign and minimized-corpus replay.
- **Release classification expectation:** `no-release`, except user-visible fixes found by it.

### BL-020: Design file-based non-secret configuration

- **Status:** parked
- **Priority:** low
- **Roadmap theme:** M7 Later and conditional work
- **Dependencies:** Established MCP/evidence schemas. M5 owns only `.opencodereview/review-context-policy.json`; it neither activates nor depends on this general framework.
- **Activation trigger:** Environment-only configuration is a demonstrated constraint and one coherent schema can cover affected non-secret settings.
- **Goal:** Improve maintainability without weakening precedence, validation, or secret handling.
- **Scoped deliverables:** Decide format/versioning, discovery/trust source, field-level environment precedence, migration, allowed non-secret fields, unknown/deprecated-key behavior, and redacted diagnostics before implementation.
- **Acceptance criteria:** Environment precedence is explicit; secrets are rejected; source files cannot self-authorize; paths remain rooted; unknown/deprecated keys and rollback are documented/tested.
- **Exclusions:** Credentials on disk, implicit configuration, overlapping formats, or implementation before design approval.
- **Validation:** Threat model, schema/precedence, migration, and secret rejection.
- **Release classification expectation:** `release-required`.

### BL-021: Add code-hosting and review-host adapters beyond GitLab

- **Status:** conditional
- **Priority:** low
- **Roadmap theme:** M7 Later and conditional work
- **Dependencies:** Stable provider-neutral core contracts and a funded non-GitLab use case. GitLab-first M5 does not depend on it.
- **Activation trigger:** A named forge has an owner, synthetic fixtures, and explicit parity requirements for CI orchestration, positioning, deduplication, discussion ownership, and safe publication.
- **Upstream overlap:** OCR 1.10.2 reusable GitHub Action checkpoint ranges and OCR 1.11.0 Action/plugin changes cover only upstream execution surfaces. They do not provide toolkit forge acquisition, discussion, publication, or lifecycle parity, so the trigger and acceptance criteria remain unmet.
- **Goal:** Add one coherent host adapter without leaking forge semantics into evidence or core result handling.
- **Scoped deliverables:** The capability matrix covers authentication, diff positions, drafts, discussion acquisition, protected same-revision CI outcomes, provider-declared account classification, thread/reply structure, edit/version identity, anchors, resolved/stale state, pagination/snapshot mutation, ambiguous writes, permissions, and idempotency.
- **Acceptance criteria:** Core remains provider-neutral, GitLab behavior does not regress, unsupported host capabilities fail or degrade explicitly rather than emulate unsafe parity, and the new host meets the approved lifecycle and security matrix.
- **Exclusions:** Repository ecosystem/framework detection, partial adapters, legacy namespace shims, or multi-host abstractions without a real second provider.
- **Validation:** Shared adapter contract suite, provider-specific synthetic integration tests, redaction/write-bound tests, and documentation validation.
- **Release classification expectation:** `release-required`.
