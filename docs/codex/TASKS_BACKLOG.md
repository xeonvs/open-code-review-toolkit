# Tasks Backlog

This file contains implementation-ready future work derived from the [toolkit strategy](../engineering/toolkit_strategy.md) and ordered by the [roadmap](../../ROADMAP.md). Active repository work belongs in `PLANS.md`; roadmap outcomes are intentionally not repeated here.

Statuses are `ready`, `planned`, `parked`, `conditional`, or `owner action`; a temporary `promoted` entry points only to its active plan. Release classification is an expectation to be confirmed when work is activated. Completed work is reflected in the roadmap and stable execution-history archive rather than retained as future backlog.

## Existing backlog reconciliation

The qualified OCR capabilities do not complete any remaining conditional item:
Objective-C++ routing is an OCR Rules change rather than a framework evidence pack;
viewer fixed/ignored marks are browser state rather than forge lifecycle support;
private failure arguments add no telemetry exporter or model-profile capability.

| Previous item | Disposition | Result |
| --- | --- | --- |
| M2 evidence gaps (BL-008) | Completed and removed | Demonstrated framework resolution, component ownership, scoped completeness, and first-class MCP delta projection ship through shared evidence contracts. |
| M2 framework selection (BL-009) | Completed and removed | Bounded static Jinja2, Go web, Symfony/Twig, and React/Next providers ship with synthetic cross-provider validation and no second MCP. |
| M2 milestone closure | Completed | Stable 0.5.0 delivery and external readback establish M2; BL-010 remains a conditional M8 extension. |
| M3 generic external-MCP qualification (BL-011) | Completed and removed | Checksum-verified OCR 1.9.5, the production `ocr-ci review` path, a local model peer, and a real stdio MCP peer establish the documented direct-composition safe-use envelope and its claim limits. |
| M3 provider examples (BL-013) | Removed | Direct provider examples over model-selected unrestricted arguments are not the target architecture; valid synthetic adapter qualification moves behind the BL-023 broker boundary. |
| Same-session external-MCP annotation enforcement (#103) | Removed / not planned | M7 removed the direct-provider path. Server annotations remain untrusted metadata; operator-owned registry assurance and gateway controls own the current decision. |
| M4 accepted decisions (BL-014) | Completed and removed | Structured target-only decisions preserve deterministic identity, safe applicability, staleness, and bounded projections without suppression authority. |
| M4 project guidance (BL-015) | Completed and removed | Immutable target guidance has bounded discovery, deterministic applicability/precedence, changed-guidance exclusion, and full text through the built-in evidence MCP. |
| M4 milestone closure | Completed | Stable v0.6.0 and protected-target identity readback establish M4 without making later context enrichment part of it. |
| OpenSSF Best Practices publication (BL-022) | Completed historically and not reused | The stable execution history records the passing badge publication and closure; the next identifier is BL-023. |
| Native fuzzing campaign (BL-019) | Completed in the 0.14.0 implementation | Bounded Hypothesis targets and minimized regressions are retained in `tests/fuzz/` and component suites; the [test evidence matrix](../engineering/test_evidence_matrix.md#v0140-range-diagrams-and-bounded-fuzzing) records supported-Python replay and claim limits. |
| File-based user configuration | Retained and clarified | BL-020 remains parked; M5 owns only its narrow protected-target context/DLP policy, not a general configuration framework. |
| Additional provider adapters | Retained and clarified | BL-021 remains conditional; future forge parity includes discussion, snapshot, and protected same-revision CI-outcome capabilities without blocking GitLab-first M5. |
| M5 bounded review-context enrichment (BL-023) | Completed and removed | The v0.7.0 release establishes the protected policy, GitLab discussion, broker/store/handle, fixed context-tool, containment, publication-DLP, receipt, setup-diagnostic, and CI-uncertainty boundaries tracked by #107-#111. The complete plan and release checkpoint are preserved in the execution-history archive. |
| Review measurement gaps (BL-017) | Completed and removed | The toolkit 0.8.2 source-to-signal audit concludes `no-new-layer`: OCR retains provider/review telemetry ownership, while toolkit receipts and count-only DLP events retain deterministic lifecycle ownership. Group labels and path-derived keys are explicitly classified as untrusted, high-cardinality upstream telemetry. |

## M3 External MCP hardening

M3 is established. BL-011 is complete and recorded above rather than retained as future work. BL-012 is an authentication extension whose trigger is not met; authentication never substitutes for resource authorization and does not block M3 or BL-023.

### BL-012: Define and validate managed OAuth for remote MCP

- **Status:** conditional
- **Priority:** low
- **Roadmap theme:** M8 Later and conditional work — federation authentication
- **Dependencies:** Established M7 registry-v2 federation gateway and its bounded HTTPS transport. Authentication must preserve gateway admission and upstream tenant/object authorization; the historical BL-011 direct-composition envelope is not a current fallback.
- **Activation trigger:** A reviewed HTTPS upstream requires authorization-code OAuth rather than static environment-backed headers, and the existing gateway authentication contract is insufficient for pilot operations.
- **Goal:** Add a provider-neutral authentication lifecycle without placing long-lived OAuth material in repository content or OCR config; object authorization remains server-owned and separate.
- **Scoped deliverables:** Define authorization-code plus PKCE, browser callback ownership, refresh/revocation, secure token persistence, tenant/resource binding, dynamic-client-registration policy, sanitized audit events, and provider conformance fixtures before selecting an implementation boundary.
- **Acceptance criteria:** Tokens never enter argv, repository files, generated context, or logs; refresh/revocation and tenant changes fail closed; synthetic static-header and browser-OAuth fixtures preserve registry-v2 gateway admission, bounded HTTPS transport, and upstream resource authorization without direct OCR passthrough.
- **Exclusions:** Resource authorization by token presence, automatic reference discovery, writes, generic web access, or treating a permanent token as OAuth lifecycle support.
- **Validation:** Threat-model review plus synthetic authorization, PKCE, callback, refresh, revocation, tenant mismatch, persistence-permission, redaction, and OCR integration cases.
- **Release classification expectation:** `release-required` once public authorization behavior is selected.

## M6 Profiles and quality measurement

Provider/network telemetry remains outside M1 and M5. OCR owns token, cost, budget, provider-level review duration, request, and tool-call telemetry. The toolkit exposes only validated provider-neutral token buckets, distinguishes OCR-wide tool totals from verified internal evidence and content-free federation accounting, and carries deterministic stage-aware publication-DLP state in receipt v10, a parseable GitLab summary marker, and a structured local log event; it adds no exporter or endpoint.

### BL-016: Evaluate explicit run-level model profiles

- **Status:** parked
- **Priority:** medium
- **Roadmap theme:** M6 Profiles and quality measurement
- **Dependencies:** Established built-in MCP lifecycle and qualified OCR per-run model/provider overrides satisfy the capability dependency.
- **Activation trigger:** Not met. Activate only after repeated operations show direct settings are insufficient and the owner approves a closed model/provider matrix plus precedence contract.
- **Upstream overlap:** OCR supplies direct run-level selection; per-file and aggregate budgets remain explicit completeness controls, not profile defaults.
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

## M8 Later and conditional work

### BL-010: Add evidence packs from demonstrated use cases

- **Status:** conditional
- **Priority:** medium
- **Roadmap theme:** M8 Later and conditional work
- **Dependencies:** Established evidence, snapshot/delta, scoped-completeness, static-plugin, and built-in MCP contracts.
- **Activation trigger:** A real repository need identifies a missing ecosystem/framework and supplies safe synthetic fixtures and deterministic semantics.
- **Goal:** Extend coverage without accumulating shallow detectors.
- **Scoped deliverables:** Implement one coherent ecosystem or framework pack per activation, with provenance, bounds, source/target deltas, documentation, and public operational examples using safe placeholders.
- **Acceptance criteria:** The use case and completion signal are documented before implementation; false-positive behavior and unsupported versions are explicit through the shared scoped coverage contract.
- **Exclusions:** Checkbox coverage, network resolution, runtime execution, or unrelated bundles.
- **Validation:** Pack fixtures plus common evidence/bootstrap/MCP contracts.
- **Upstream overlap:** OCR language allowlists and review rules are review-engine capabilities; Handlebars/Mustache selection improves review coverage but does not supply a framework evidence contract or activate an evidence pack.
- **Release classification expectation:** `release-required`.

### BL-020: Design file-based non-secret configuration

- **Status:** parked
- **Priority:** low
- **Roadmap theme:** M8 Later and conditional work
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
- **Roadmap theme:** M8 Later and conditional work
- **Dependencies:** Stable provider-neutral core contracts and a funded non-GitLab use case. GitLab-first M5 does not depend on it.
- **Activation trigger:** A named forge has an owner, synthetic fixtures, and explicit parity requirements for CI orchestration, positioning, deduplication, discussion ownership, and safe publication.
- **Upstream overlap:** OCR reusable GitHub Action checkpoint ranges and Action/plugin capabilities cover only upstream execution surfaces. They do not provide toolkit forge acquisition, discussion, publication, or lifecycle parity, so the trigger and acceptance criteria remain unmet.
- **Local-provider distinction:** The local provider introduced in 0.10.0 shares pure reporting and supplies immutable local input plus Markdown delivery. It adds no forge authentication, discussion commands, threads, suppression or approval; it is not completion or activation of this second-forge item.
- **Goal:** Add one coherent host adapter without leaking forge semantics into evidence or core result handling.
- **Scoped deliverables:** The capability matrix covers authentication, diff positions, drafts, discussion acquisition, protected same-revision CI outcomes, provider-declared account classification, thread/reply structure, edit/version identity, anchors, resolved/stale state, pagination/snapshot mutation, ambiguous writes, permissions, and idempotency.
- **Acceptance criteria:** Core remains provider-neutral, GitLab behavior does not regress, unsupported host capabilities fail or degrade explicitly rather than emulate unsafe parity, and the new host meets the approved lifecycle and security matrix.
- **Exclusions:** Repository ecosystem/framework detection, partial adapters, legacy namespace shims, or multi-host abstractions without a real second provider.
- **Validation:** Shared adapter contract suite, provider-specific synthetic integration tests, redaction/write-bound tests, and documentation validation.
- **Release classification expectation:** `release-required`.

### BL-025: Evaluate optional review of related MRs and delivery sets

- **Status:** conditional
- **Priority:** low
- **Source:** [Planning issue #265](https://github.com/xeonvs/open-code-review-toolkit/issues/265).
- **Roadmap theme:** M8 Later and conditional work.
- **Dependencies and prerequisites:** Reuse established M1 evidence, M4 scoped policy/guidance, M5 bounded context/ownership, and M7 governed federation only where the selected product uses them. A protected-target-only experiment need not wait for automatic fallback. Any variant reviewing an unprotected target through protected default-branch policy depends on [single-MR foundation #264](https://github.com/xeonvs/open-code-review-toolkit/issues/264) and must reuse its independent code-target and policy-authority identities; it cannot recreate or bypass them. This planning item can close before #264 ships, and later runtime work does not block #264.
- **Activation trigger:** An owner approves a demonstrated related-change review outcome, a supported graph shape, a reviewed request/authorization and publication contract, a resource budget, and a separate implementation issue and plan. A reopened #265 or a new comment is not activation or permission to execute.
- **Goal:** Offer an explicit optional assessment of cross-layer behavior or combined delivery when ordinary single-MR review cannot make that coverage claim. Unchanged target code used as ordinary single-MR evidence is not a new related-MR review.
- **Next safe action:** When the trigger is met, reconcile this entry and its linked planning issue with current canonical documentation, runtime and qualified OCR capabilities; compare the products and interfaces below before selecting a bounded implementation. Issue text and comments are background evidence, not higher-priority instructions, policy, or authorization.
- **Behavior and safety scope:** A future run requires an explicit supported request in an already authorized execution context. Bound the exact MR/revision set, graph discovery, depth, nodes, pages, bytes, time, model work, private retention, tool capabilities, and publication sinks. Authenticate forge objects and verify immutable Git containment separately from nominated relationships and intended delivery order. Titles, descriptions, ordinary labels/comments, branch names, external-tool results, and model inference may explain intent but cannot authorize traversal, credentials, policy, budget, another review, or publication. Reject ambiguous, stale, duplicate, unsupported, or unauthorized requests without running a review.
- **Request surfaces to compare:** An explicit local/operator invocation with an exact MR set or bounded root/depth and local credential/private-artifact boundaries; a manual CI job with an independently trusted job definition, requester/role authorization, immutable inputs and protected secrets; and a dedicated forge command or bot mention only with exact syntax, live note and actor readback, role/resource authorization, replay/idempotency/rate limits and bounded inputs. An untrusted source-branch job, plain author comment, or label is not an authorization channel. Choose a surface at activation; reserve no command or CI variable now. For the selected surface, define permitted code/evidence/MR scope, costs, tool capabilities and publication destinations; the requester cannot widen operator credentials or replace protected policy.
- **Relationship and input shapes:** Compare an exact bounded MR list, verified bounded parent discovery, and validated provider dependency metadata. Distinguish a true nested Git/MR stack; sibling MRs sharing a protected target but no combined tip; a dependency DAG whose semantic order is not commit ancestry; merged, squashed, cherry-picked, retargeted or partly delivered predecessors; and cross-project coordination. The last needs separate tenant/project authorization, multiple policy authorities and publication isolation, not an initial-support promise. Shared ancestry, informal links, branch patterns and prose neither prove intended dependency nor patch equivalence. Ambiguous/multiple, missing/closed/merged or inaccessible parents, unrelated histories, forks, cycles, retargeting, rebases and force pushes require explicit unsupported or stale outcomes. Never coerce siblings or a DAG into a linear stack, choose an arbitrary parent, or silently omit a layer while claiming complete coverage.
- **Candidate coverage products:** The initial recommendation is to compare B with D for demonstrated combined-delivery needs, with B the preferred first candidate for a verified existing nested tip when full combined-delta coverage is required. This is an activation-time recommendation, not a frozen design or a promise to ship every candidate. A is appropriate only for missing related intent; C requires a demonstrated layer-accountability need; E is a later optimization; F remains a separately gated prospective option. Reject automatic traversal, treating inherited target code as fresh related-MR coverage, and running full B plus full C by default.

  | Candidate | Coverage and value | Cost, limitation and required non-claim |
  | --- | --- | --- |
  | A. Current MR with bounded related context | Current MR delta plus separately attributed, explicitly requested intent/discussions or exact evidence from named MRs. | Extra acquisition/privacy scope; no parent-delta or combined-delivery claim. Ordinary unchanged target code is already available to single-MR review. |
  | B. One cumulative review of an existing nested tip | Exact root/common-base-to-tip delta of a verified stack; combined-delivery audit without a hypothetical tree. | May select many files and model tokens; does not prove each layer independently or compatibility with a newer integration tip. Inherited findings retain parent provenance. |
  | C. Per-layer reviews plus bounded cross-layer check | Each MR delta and a separately selected interaction scope for layer accountability. | Highest repeated review and publication work among existing-snapshot products; per-layer completeness does not imply interaction completeness. |
  | D. Focused interaction review | Declared contracts, paths, APIs, schemas or interfaces spanning the requested changes. | Deliberately partial coverage; selection and omissions must be deterministic and visible, with no full-review claim. |
  | E. Snapshot-qualified incremental reuse | Exact eligible prior evidence and separately validated outcomes, with changed or invalidated scopes reviewed afresh. | Optimization of A-D/F, not an independent full-review product. A green receipt is not cached correctness; invalidate on code, topology, policy/rules, context, engine/config or coverage change. |
  | F. Prospective combined delivery of non-nested branches | An explicitly constructed and read-back candidate snapshot for an authorized set and order where no existing tip contains the whole delivery. | Highest identity, conflict, isolation and line-attribution complexity; prospective evidence is not an actual merge, deployment or completed layer review. |

- **Scoped deliverables on activation:** Compare every candidate's value beyond existing toolkit/OCR behavior, supported graph/input, acquisition and publication authority, DLP/retention, policy source/applicability, stale-state response, OCR/result representability, testability, expected Git/API/model work, cost bounds and precise coverage non-claims. Define a preview of resolved graph, immutable scopes, selected product, bounded work and intended sinks before expensive model work; it need not predict exact token cost. Keep OCR as the sole review engine. Distinguish each MR's validated merge-base/diff-version delta, inherited target code, combined contribution relative to an identified root/common base, and compatibility with the captured current integration branch; comparing every branch tip to the current default tip cannot replace those identities. An aggregate, focused or prospective run needs its own truthful versioned, hostile-parsed scope/result/receipt identity; it cannot reuse ordinary current-MR CI head, receipt or inline anchors. Record node revisions, graph edges, policy authority, context versions/completeness, reviewed scopes, reused/skipped/unsupported evidence, actual model invocations and available measured telemetry. Revalidate graph and sink identities before writes; a prior success is not valid for a new topology or SHA tuple.
- **Authorization, privacy and publication:** Policy authority stays independently selected and protected; following an MR grants no additional capability. Keep each MR's intent/discussions attributed to its own MR, author class, revision/anchor and acquisition state; related CI evidence still needs exact-revision and trusted-producer gates. Reuse existing DLP, allowlists, least-privilege transport, privacy-safe diagnostics and private retention. Prefer one authorized sink, the requesting MR or a private local artifact, in an initial delivery. Reading a parent does not authorize posting to it; multi-MR publication requires separate permission, identity, line mapping, idempotency and human-discussion ownership for each sink. Preserve finding provenance and deduplication; an inherited parent finding is not a new child finding. An unprotected target gains no approval. Extend the threat model for forged review/test/approval evidence, prompt injection, traversal/BOLA, credential exfiltration, policy/ref substitution, graph TOCTOU, stale reuse, cost amplification, finding misattribution and cross-project leakage.
- **Acceptance criteria and exit criterion:** The owner-selected product has explicit supported topology and request authority, immutable scope and independent protected policy identity, bounded work, truthful coverage/result/receipt, deterministic unsupported/stale outcomes, safe DLP/publication and no regression to ordinary single-MR review. Parent-only, child-only, cross-layer and intermediate-introduced/later-fixed defects yield distinguishable coverage and attribution. Unchanged target code, newly acquired intent, fresh code review, prospective integration and receipt/evidence reuse never stand in for one another. Mark this item promoted only into its own approved implementation plan; close it after that plan's validated delivery, rather than treating completion of #265 as runtime delivery.
- **Exclusions:** No automatic traversal from target branch or prose; no merge, push, ref update, MR creation, unrelated pipeline start, protection/project-variable/policy edit, credential or external-tool expansion, direct external MCP passthrough, second model arbiter or default multiplication of full reviews. Candidate F may assess a strictly isolated toolkit-owned Git computation or verified forge snapshot, but must not execute repository content, hooks, filters, builds, credential helpers or submodules; conflicts and ordering ambiguity stop the candidate. Do not activate BL-020 configuration, BL-021 second forge, model-profile routing, managed OAuth or other conditional work. Do not reopen completed M1/M4/M5/M7 work, closed #168 or historical release facts.
- **Validation:** Use synthetic/private-safe graph, mutation, force-push/retarget, stale-cache, privacy and publication fixtures across production forge, Git, context and write boundaries. Compare parent-only, child-only, interaction and intermediate-introduced/later-fixed defects; report coverage, provenance, duplicates and measured work/cost separately without invented savings. Separate mocked wiring, installed/integration proof and real-OCR qualification. Record engine or forge capability gaps instead of bypassing validation; absence of a test result or unmeasured layer remains unknown.
- **Release classification expectation:** This #265 planning reconciliation is `no-release`. A later activated runtime implementation is expected `release-required`, subject to its own approved scope and final-diff classification. Retain the Source link after #265 closes; the merged planning PR should link this entry and record the recommended, deferred and rejected alternatives in the issue body. A later runtime implementation needs its own linked issue and plan.
