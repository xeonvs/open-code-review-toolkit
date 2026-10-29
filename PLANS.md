# Execution Plans

## Active Plan: Toolkit 0.14.0 range identity, typed diagrams, DLP qualification and Python 3.15

plan_schema_version: 2
Status: active
Owner: root
Last Updated: 2026-10-29
Release classification: release-required, target v0.14.0; bounded BL-019 testing and fixture maintenance are accompanying no-release work within the same delivery objective.

### Goal

Implement issues #272 and #273, strengthen DLP and its adversarial tests, qualify Python 3.15, and publish v0.14.0 through the protected feature and release paths. Stable publication, immutable receipt readback, issue/milestone closure, site refresh and synchronized clean main are required to complete the user-facing delivery objective.

### Plan Origin

`plan_mode_approved`

### Requested Scope

Bind evidence, native execution, admitted results, coverage, reporting, receipts and publication to one immutable effective Git range. Add one optional typed flowchart or sequence diagram through the existing native OCR invocation and toolkit MCP transport. Complete BL-019 as a bounded dev-only Hypothesis campaign, prioritize technical-value DLP false positives and rare rejection branches, improve weak module coverage, and replace country-identifying telephone fixtures with reserved fictional numbers. Add official Python 3.15 support with narrowly required dependency and CI updates.

The first signed push contains the complete plan and its lifecycle pointer plus one separately reviewed dev-lock security correction, and opens a draft PR. This narrow initial-push exception addresses the mandatory dependency audit finding for msgpack 1.2.2; the approved correction is 1.2.3 and changes no product runtime dependency. Continue development locally with logical signed commits and self-review before every commit; amend unpublished commits where useful. Before the final feature push, perform aggregate semantic self-review, one aggregate Codex Security diff scan, fix its findings, and perform at most two successful local self-reviews through the toolkit with native ChatGPT authentication and explicit diagram generation. Failed review attempts do not consume that two-run allowance. Ordinary fixes and documentation changes do not trigger another aggregate security scan.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Resolve and prove the exact supported range before range-dependent evidence; reject sibling, unrelated and undecidable shallow ranges before model execution | WQ-03 | done |
| REQ-002 | Independently validate final native manifest identity, preserve ancestor/commit/empty/selection/gitlink semantics, and forbid unverified legacy range claims | WQ-03, WQ-05 | done |
| REQ-003 | Preserve independent GitLab diff, actual-target and policy identities and bind result/report/coverage/anchors to the admitted range | WQ-03, WQ-06 | done |
| REQ-004 | Implement the exact on/off/spoiler/local configuration matrix with early invalid-value and GitLab-local rejection | WQ-04, WQ-05 | done |
| REQ-005 | Support bounded typed flowchart and sequence variants, immutable source references, safe deterministic Mermaid and text, and explicit optional states | WQ-04, WQ-06 | done |
| REQ-006 | Receive diagram output in the same OCR run through an isolated fixed toolkit MCP capability; reconcile run-wide duplicates/conflicts and cleanup without a second model pass | WQ-04, WQ-05 | done |
| REQ-007 | Introduce explicit receipt v13/v14 production/readback while preserving frozen v9-v12 and pre-execution v5/v6 meanings | WQ-06 | done |
| REQ-008 | Keep graph DLP and omission separate from finding outcome and approval; correct narrowly proven technical comparison false positives without bypassing whole-unit checks | WQ-02, WQ-05, WQ-06 | done |
| REQ-009 | Complete BL-019 with bounded Hypothesis properties and minimized synthetic regressions for DLP, result/range, policy/diagrams, evidence/MCP, GitLab/registry metadata, context handles/store/CI outcomes and federation admission/upstream responses; qualify supported Python and retain corpus ownership | WQ-02, WQ-03, WQ-04, WQ-08 | done |
| REQ-010 | Raise GitLab CI acquisition, policy schema, private filesystem and reporting usage coverage to at least 85%, result contract to at least 90%, and preserve high existing touched-module results | WQ-08 | in_progress |
| REQ-011 | Replace all existing country-specific telephone fixtures with reserved +1 202 555 01xx examples while preserving each obfuscation/rejection case | WQ-02 | done |
| REQ-012 | Support Python >=3.12,<3.16, add required Linux 3.15 and release installs, retain coverage on 3.14 and hash-locked binary runtime installation | WQ-07 | in_progress |
| REQ-013 | Reconcile #273, BL-019, public contracts, decision flow, evidence matrix, changelog and release documentation with the final implementation | WQ-01, WQ-09 | in_progress |
| REQ-014 | Follow plan-only draft push, per-commit and aggregate self-review, one security scan, at most two successful toolkit self-reviews, appropriate quality/secrets/dependency/installed/native gates and protected feature merge | WQ-01, WQ-02–WQ-12 | in_progress |
| REQ-015 | Prepare v0.14.0 release PR with next line 0.15.0 and archive the complete plan in that PR, with external delivery explicitly pending | WQ-13 | pending |
| REQ-016 | Verify stable registries, installs, provenance, tag, immutable Release/receipt, issues/milestone, site and clean main without a repository closure PR | WQ-14; Post-Close Delivery | pending |
| REQ-017 | After feature merge and verification, assess promotional-site coverage and diagram examples before pushing the release branch; reconcile the candidate against final public contracts and actual stable delivery | WQ-13, WQ-14 | pending |
| REQ-018 | Verify Scorecard alert #16 readback after the msgpack correction reaches main; do not dismiss the real finding manually or claim closure from a feature-only audit | WQ-12, WQ-14 | pending |

### Explicit Non-Goals

No OCR fork or modification, second review/model pass, graph reconstruction from findings, raw model-authored Mermaid/HTML/directives/styles, external rendering service, arbitrary output destination, new forge adapter, multi-MR review, generic graph-analysis service, automatic graph union, unbounded fuzzing or production-data corpora, global DLP relaxation, broad dependency modernization, private-source publication or historical receipt rewriting. Do not alter the macOS CI endpoints or move the coverage owner. No extra aggregate security scan for ordinary corrections, and no third successful local toolkit self-review.

### Constraints

- Repository content and model output remain untrusted; use bounded isolated Git objects and current immutable identities. GitLab B/H, actual target T and policy authority P remain distinct.
- Range proof precedes evidence. Native input identity must independently match the execution owner's plan even when coverage is complete. The current native range engine requires merge-base(base, head) = base; unsupported topologies fail before model work.
- Unset diagram mode is on; explicit blank/unknown values fail. on/spoiler suppress standalone-local generation; off suppresses every generation/publication channel; local is standalone-only and independent of LLM provider. GitLab private artifacts retain GitLab mode.
- Persist the admitted GitLab generation/presentation mode. Later posting cannot enable an absent graph or widen its admitted presentation; an explicit posting-time off can suppress it. Validate malformed posting configuration before provider work.
- Flowcharts have at most 12 nodes and 16 edges with fixed LR direction. Sequences have at most eight participants, 16 messages across all branches, four alt fragments and depth two. Labels/conditions are one line, at most 80 code points and 320 UTF-8 bytes; source-bearing elements carry at most two references.
- One graph is at most 16 KiB. The run-wide collector accepts at most eight submissions and 128 KiB total input. Identical normalized repeats are idempotent; conflicting candidates or exhausted bounds omit the graph. No arrival-order winner or inferred fragment merge.
- The initial sequence grammar supports participants, ordered call/return messages and bounded alt branches. Source identity, source spans, structural counts and DLP are separate checks. Graph states and public omission reasons are toolkit-authored closed values; free model-authored justification never gains completion or approval authority.
- Diagram capability is initially qualified for exact OCR 1.13.3. Unsupported engines get an explicit state and no added invocation. States are disabled, not-applicable, unsupported, generated, not-generated and omitted-invalid.
- The collector has a fixed private run-bound destination; model arguments cannot select a path, network address, repository mutation or publication capability. Evidence tools remain read-only. Read and validate the private candidate before cleanup, then bind it to final native identity before publication.
- Keep pure contracts and presentation below orchestration/I/O. Reporting imports no environment, Git acquisition, MCP, DLP orchestration or provider actions; avoid adding independent responsibilities to the large runner.
- Apply secret/PII checks to the entire original text. Source validity does not grant a secret exception. Preserve current source-proof and sink requirements for optional opaque code. Graph DLP omission alone does not change finding outcome, coverage, publication-filtered state or approval eligibility; hostile persisted receipt corruption still rejects the artifact atomically.
- New ordinary/partial receipt producers are v13/v14. Freeze old version numbers and nested schema maps explicitly. Embedded review tuple is unchanged, so pre-execution v5/v6 retain their original mappings.
- Preserve zero new runtime dependencies for this feature and dev-only Hypothesis. Runtime installs remain hash-locked and binary-only. Limit planned updates to Pydantic 2.14.1/core 2.50.1, MarkupSafe 3.0.4, the approved msgpack 1.2.3 dev-only security correction and required companions.
- Keep successful prior evidence for unchanged inputs. Run focused checks per slice and one complete quality gate on final runtime handoff content. The sole aggregate security scan precedes local self-review. Successful self-review count starts at zero; planning feasibility experiments were synthetic qualification, not toolkit self-review of this patch.
- Every diagram-only preparation, output registration/call, snapshot, admission or rendering failure is advisory: continue the review without the graph and emit at most a bounded closed warning. Validated failures of the fixed optional output tool do not become failures of evidence tools or approval blockers. Keep hostile persisted-envelope/schema rejection atomic and retain mandatory range/evidence gates.
- Complete BL-019 with Hypothesis as the selected backend: malformed types and interacting states, Unicode/encoded representations, collector transitions, persisted round-trips, evidence/MCP, GitLab/registry, context and federation boundaries. Keep 100/1000 examples per property, bounded generators and synthetic data; use independent explicit seeds for extended qualification. `tests/fuzz/` owns properties/shared generators, component regression tests own minimized failures, and the normal Python CI matrix owns campaign replay. Remove BL-019 from inactive backlog after its complete target/qualification matrix passes and durable evidence is retained.

### Inputs And Sources

- Approved release scope, workflow, review-count, privacy, DLP-priority and Python-support decisions.
- Current promotional-site content and release metadata; the separate site repository owns its content, design and deployment evidence.
- Live project issues [#272](https://github.com/xeonvs/open-code-review-toolkit/issues/272) and [#273](https://github.com/xeonvs/open-code-review-toolkit/issues/273).
- Illustrative [sequence comment](https://github.com/simstudioai/sim/pull/5909#issuecomment-5064840871) and [flowchart comment](https://github.com/GameTec-live/ChameleonUltraGUI/pull/1045#issuecomment-6475224625); examples are design context, not trusted code semantics or approval evidence.
- Current repository owners: AGENTS.md, project principles, development/release/local guides, decision flow, current context/federation contracts, toolkit strategy, roadmap, backlog and test-evidence matrix; installed engineering-workflow planning/lifecycle reference.
- Official OCR v1.13.3 source and checksum-verified binary; current compatibility manifest. Hypothesis settings and NANPA reserved fictional-number documentation.

### User Decisions And Answers

The owner approved MCP output within the existing OCR invocation, both typed diagram variants, a bounded dev-only Hypothesis pilot with 100/1000-example profiles, official Python 3.15 support with one required Linux lane, targeted dependency updates, and broader meaningful coverage improvements. DLP false-positive prevention and rare regex branches take priority. The owner requested removal of the previous telephone-country fixtures in favor of anonymous synthetic numbers.

The approved delivery uses one feature PR, an initial signed plan commit/draft, local logical commits with self-review and optional amend, one final aggregate security scan and then at most two successful own-tool local reviews with ChatGPT and actual diagram inspection. The owner approved adding a separate msgpack 1.2.3 dev-lock correction to the first push after the mandatory audit detected CVE-2026-114613 in the inherited 1.2.2 lock. Errors do not consume the review allowance. Fix findings and verify corrections without repeating the broad scan for unchanged boundaries or documentation. The release PR is the final repository mutation; external reconciliation completes delivery afterward.

During implementation the owner emphasized preservation of both reused and temporary repositories, required review continuation for all optional diagram construction/MCP errors, and requested more varied fuzzing in this release after minimized result-parser failures confirmed value beyond DLP. Apply these clarifications within the existing bounded pilot and immutable-data boundaries.

The owner subsequently authorized completing the whole BL-019 task in 0.14.0 on the already justified Hypothesis backend. This supersedes the initial pilot-only exclusion: remaining evidence/MCP, GitLab/registry metadata, context handles/store/CI-outcome and federation/upstream-response families are active. Preserve bounded resources and synthetic corpus rules, qualify the supported Python range, then close the backlog point. Finish this expanded scope before the sole aggregate security scan and own-tool reviews.

Begin promotional-site feature assessment and any diagram-example preparation only after feature merge and verification establish the final release scope, before pushing release/v0.14.0. Toolkit contracts and release facts remain owned here; site content, design and its candidate belong to the separate site repository. Prepare against the confirmed 0.14.0 candidate without claiming it is already shipped; verify publication only after stable evidence. Plan archive/reset belongs in the release PR and must not generate a later toolkit closure PR.

### Completed Baseline State

Clean main and origin/main both resolve to b81b4a15bb5212ece78c398665a9d576537ab404. The stable marker is 0.13.1 and next development line is 0.14.0. No active plan or implementation existed at activation. Runtime last changed in the merged 0.13.1 feature; the retained full coverage baseline from subsequent checks remains available privately.

Feature branch codex/toolkit-0.14.0 was created from that baseline. Initial signed commits d792463 (plan/lifecycle pointer) and ef4601c (approved isolated msgpack dev-lock correction) are pushed in draft PR [#274](https://github.com/xeonvs/open-code-review-toolkit/pull/274). Existing open milestone 0.14.0 (#23) tracks #272/#273, and #273 now contains the agreed typed flow/sequence contracts and acceptance matrix. No further feature push is allowed before final local delivery gates.

Planning experiments proved native OCR 1.13.3 MCP transport and real ChatGPT generation: a flowchart with nine nodes/nine edges and 23 valid references; a sequence with four participants/eight messages/two nested alt fragments and 15 valid references; comment-only not-applicable; and six independent candidates from six native groups in one run. Native runs completed with no tool failures. Temporary validation exercised existing Git/DLP owners, not yet-written production graph admission. Technical comparison false positives were minimized to version < 2020.1.10 and date < 2020-01-01; mixed sensitive additions remained rejected. Python 3.15 passed 116 existing result/reporting/auth tests with trial dependencies; binary runtime resolution passed for Darwin arm64 and Linux amd64. Private credentials were linked through the existing owner and never copied; all temporary auth links were removed.

### Current Work Queue

| Queue | Requirements | Exit evidence | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-013, REQ-014 | Reviewed complete plan/lifecycle pointer and separate approved msgpack dev-lock correction, initial signed push, draft PR, v0.14.0 issue tracking and #273 expansion | done |
| WQ-02 | REQ-008, REQ-009, REQ-011 | DLP comparison corrections, bounded Hypothesis profiles/properties, anonymous fixtures, focused checks and self-reviewed commit | done |
| WQ-03 | REQ-001–REQ-003, REQ-009 | Immutable range contract/resolution/admission and production-launcher regression tests; self-reviewed commit | done |
| WQ-04 | REQ-004–REQ-006, REQ-009 | Typed diagram contracts, bounded collector, duplicate/conflict semantics and hostile tests; self-reviewed commit | done |
| WQ-05 | REQ-002, REQ-004, REQ-006, REQ-008 | MCP/bootstrap/native/final-admission/cleanup wiring and real-protocol plus qualified native integration | done |
| WQ-06 | REQ-003, REQ-005, REQ-007, REQ-008 | Receipt v13/v14, frozen old readback, pure report/renderers, local/GitLab presentation and publication tests | done |
| WQ-07 | REQ-012 | Python 3.15 metadata/lock/required CI/install matrices and clean artifact checks; self-reviewed commit | in_progress |
| WQ-08 | REQ-009, REQ-010 | Full bounded BL-019 target matrix, minimized corpus and replay across supported Python, weak-module floors and semantic branch comparison; close backlog point after evidence | in_progress |
| WQ-09 | REQ-013, REQ-014 | Public owners, decision flow, evidence matrix, backlog/strategy status, changelog and aggregate self-review | done |
| WQ-10 | REQ-014 | Exactly one aggregate Codex Security diff scan; findings classified/fixed with scoped regression evidence | done |
| WQ-11 | REQ-014 | Own-tool ChatGPT local review with graph, findings/failed-read inspection, at most two successful runs and scoped corrections | done |
| WQ-12 | REQ-014, REQ-018 | Final quality and pre-push gates, finished feature push, protected checks/merge, Scorecard alert #16 and development TestPyPI readback | pending |
| WQ-13 | REQ-015, REQ-017 | Signed release/v0.14.0 candidate, confirmed site-contract handoff before release push, 0.14.0/0.15.0 markers, authorization/notes/pins, checked archive and protected release handoff | pending |
| WQ-14 | REQ-016, REQ-017, REQ-018 | Stable external publication/readback, Scorecard/site reconciliation and clean synchronized main; no repository closure PR | pending |

### Locked Decisions

Use a provider-neutral closed immutable range contract with Git acquisition at its existing boundary. Normalize supported local commit requests to the current first-parent range rather than introduce a new range-mode switch. Keep the GitLab authority tuple unchanged.

Use an optional tagged flowchart/sequence union and a fixed output capability in the existing toolkit stdio transport. Keep collection, admission, pure formatting and provider publication as separate responsibilities. A graph describes a bounded model-proposed summary, not exhaustive execution coverage, test execution, confidence or merge permission. Conflicting groups safely omit it. Source references and branch budgets are checked independently of the model's completion claim.

Reuse DLP and its explicit enablement contract; correct narrow technical contexts rather than weaken detectors globally. Properties compare safe technical forms and mixed sensitive forms. The entire BL-019 campaign is promoted under the owner's later authorization; Hypothesis remains dev-only and no second fuzzing engine or live-service campaign is introduced.

### Verification

BL-019 completion requires bounded properties/minimized replay for every family
below, default-profile replay across supported Python and extended independent
seeds. Parser properties do not claim live service behavior; real TLS/stdio,
private-filesystem and installed checks retain their separate claims.

| Fuzz family | Selected production owners | Required invariant |
| --- | --- | --- |
| DLP/result/range/policy/diagrams | Existing `tests/fuzz/` targets | Sensitive inverse checks, closed type errors, exact identity, global budgets and canonical round-trips |
| Evidence models/store | Record/coverage/delta contracts and `EvidenceStore.read` | Canonical identity or closed rejection; hostile nested fields cannot broaden trust/completeness |
| Internal/context MCP and handles | `evidence.mcp.handle_request`, `context.mcp`, `ContextStore.get` | Bounded serializable responses, closed errors, exact handle/run/policy/expiry and cursor isolation |
| Context/CI store | `ContextStore.commit/read`, fixed CI-outcome projection | Valid persistence round-trip; hostile envelope/record/projection rejects atomically |
| GitLab payloads | MR lifecycle/context normalizers and CI projection | Exact identity remains mandatory; malformed states/types cannot fabricate authority |
| Federation registry | Registry-v2 parser, origins/transports/headers/tool policy | Only permitted canonical profiles/origins/aliases survive; malformed fields use FederationError |
| Federation admission/wire | Schema/argument/result gates, `transport.parse_frame`, receipt reconciliation | Hostile schema/results/JSON-RPC stay bounded; DLP/origin gates hold and counters conserve attempts |
| Distribution metadata | TestPyPI/PyPI index/artifact-manifest validators | Version/hash/filename/host identity is exact; malformed or conflicting metadata cannot authorize download/recovery |

- Range: ancestor/equal/commit/merge-parent/empty/sibling/unrelated/shallow, hostile Git controls, missing/foreign manifests and exact base/head/range mismatch through the real launcher/parser/admission boundary; GitLab B/H/T/P and gitlink/selection regressions.
- Diagrams: full configuration matrix before acquisition, pure union validation, byte/code-point/line/count boundaries, dangling/duplicate identities, invalid references, nested/global sequence limits, stale and hostile persistence, canonical repeat/conflict/budget behavior, absence on failed/unadmitted runs, safe Mermaid/text and expanded/collapsed delivery.
- DLP: safe technical grammars and comparison forms, true secret/PII with mixed additions, Unicode/control/markup encodings, pure credentials references, optional source-proven code and whole-unit graph omission without changing findings/approval.
- Boundary map: runner resolves range -> collector/store/bootstrap -> native launcher and shared MCP -> private graph snapshot before cleanup -> final manifest/range/DLP admission -> closed result/receipt and pure report -> local Markdown or fresh GitLab post. Negative/mixed fixtures cross each changed real owner; external collaborators alone may be replaced.
- Tests/coverage: focused regression suites and Hypothesis CI/local profiles; final repository quality matrix and existing risk-group floors, plus REQ-010 module floors; record semantic regex-family coverage separately.
- Compatibility/install: locked metadata/dependencies, supported Python 3.12–3.15 CI and receipt matrix, unchanged Python 3.14 coverage ownership, clean wheel/sdist installs and real MCP/schema behavior outside the checkout with hostile shadow packages/private permissions.
- Review/delivery: self-review each commit and aggregate diff, pinned staged/tree/history secret gates and dependency audit, one security diff scan, <=2 successful own-tool ChatGPT reviews, feature/release protected CI, development publication and independent stable external reconciliation.

### Latest Validation Results

The paragraphs below retain slice checkpoints in implementation order. The last paragraph records the current aggregate status; earlier pending items and zero scan counts describe those earlier checkpoints.

The DLP slice now preserves parsed version/date comparisons, including encoded comparison operators, without exempting mixed sensitive content. The bounded properties also found a truncated quoted-credential gap; exact quoted keys and missing closing quotes are now handled while pure empty/template assignments remain admissible. The focused suite passes 276 tests and eight subtests; DLP branch coverage remains 97%. The extended profile passes up to 1000 examples per property (finite character-budget cases exhaust at 364). Repository-wide formatting, scoped lint and runtime typing pass. Reserved fictional telephone fixtures replace all prior country-specific values in tests/examples. Semantic self-review covers whole-unit checks, representation normalization, exact no-value grammar, regex near matches and unrelated diff risk.

Plan/lifecycle, instruction, public-content privacy and staged secret checks passed for the initial signed push. The inherited dev-only msgpack 1.2.2 audit finding is corrected to 1.2.3 in its own commit; the same audit passes with no known vulnerabilities, and its isolated lock comparison contains no other change. Draft feature PR #274 is open. Promotional-site preparation remains deferred until feature merge and verification, before release-branch push. Final quality, aggregate security scan, own-tool patch self-review, release PR, new publication and issue closure remain pending. Successful local self-review count: 0 of 2. Aggregate security scan count: 0 of 1.

Scorecard alert #16 was read through the provider API: its current main-bound finding is GHSA-j586-36cw-2gc2/CVE-2026-114613 in msgpack <1.2.3, matching the already corrected dev-lock package. Its finding remains open on baseline main until the correction is merged and a new main Scorecard analysis is read back; no dismissal is authorized or needed.

The range slice separates pure immutable identity/native admission from isolated Git topology proof. Real repositories exercise ancestor/equal/merge-first-parent, sibling/unrelated/reverse/shallow and replacement/graft cases through the launcher. Complete coverage cannot substitute for any native endpoint or exact-range field. Gitlink admission reuses the same validator; local and GitLab execution identities are independently reconciled. Legacy output carries no confirmed range in the admitted report model. The focused runner/gitlink/range suite passes 313 tests (ten environment-gated installed OCR cases skipped); reporting and added range handoff checks also pass. Receipt/rendering integration and real installed/native diagram handoffs remain pending in WQ-05/WQ-06.

Closed flow/sequence contracts and the private run-bound collector are locally implemented. Tests cover ordered nested alternatives and aggregate budgets, normalized duplicates, conflicts in either arrival order, eight concurrent cross-process submissions, raw wire byte accounting, exact hostile readback, unsafe file types, bounded lock contention and atomic-write failure cleanup. The focused slice passes 128 checks with 99% contract, 98% collector and 93% private-filesystem branch coverage; both diagram properties also pass the 1000-example profile. Existing local artifact/debug regressions pass. Semantic review additionally preserves staged/unstaged/untracked checkout data and default output-parent behavior. MCP, source/DLP admission, receipt and renderer activation remain pending; structural/source validity must not be described as proof of behavior.

Expanded result-contract properties minimized three uncaught enum-type errors to an empty list in terminal state, item failure classification and run failure classification. The parser now rejects them through OcrResultContractError; six ordinary minimized list/object regressions remain in the synthetic corpus. Focused contracts pass 52 checks with 99% result-contract branch coverage, and the 1000-example property profile passes. Valid native/legacy vocabularies and the absence of a legacy coverage claim are retained.

Policy variations found the same unhashable-state failure independently in guidance and accepted-decision records. Both now reject malformed applicability through the existing closed ValueError boundary; ordinary list/object regressions retain the findings. Policy schema passes 83 focused checks at 97% branch coverage. Shared JSON generators now combine finite floats, booleans, bounded integers, Unicode/controls/surrogates and object/array nesting up to two levels. Result and policy properties pass the extended profile under seeds 31514 and 31515; canonical scope/applicability producer-consumer checks include Unicode paths.

Further representation variation minimized a DLP gap to an entity-encoded credential name: Markdown normalization removed its underscores before classification. Publication now checks the decoded representation first, with the same exact empty/template grammar and whole-unit environment-secret priority. Synthetic regressions preserve the finding and later displayed/hidden-source checks. The expanded DLP properties vary plain, single/double-escaped, numeric-entity, Markdown and HTML representations; raw HTML remains inadmissible. State-transition, nested sequence and persisted-condition properties are also being expanded as part of diagram activation.

Numeric-context variation now includes valid IPv4 ports and nonbreaking/narrow-nonbreaking comparison spaces. The extended profile minimized a further false positive to `version\u00a0<\u00a02020.0.10`; only the bounded technical prefix is compatibility-normalized before its existing parsed date/version grammar. Mixed contact values remain blocked in both ingress and publication checks, and ordinary minimized regressions retain both Unicode-space forms.

WQ-05/WQ-06 are implemented locally: fixed MCP output, snapshot-before-cleanup, source/DLP admission, exact v13/v14 persistence and pure report consumers. Fault injection preserves mandatory evidence and findings across schema, binding, initialization, collector I/O, source, admission, cleanup, serialization, rendering and warning-sink errors. Hostile persisted envelopes still reject atomically. The official SDK crosses the real isolated stdio server for both variants, disabled inventory and optional I/O failure followed by successful evidence. Qualified OCR 1.13.3 crosses the actual launcher/MCP/admission/cleanup/private-report path for both variants, absence, not-applicable, invalid/conflicting candidates, OCR-side argument parse failure, output I/O failure, startup failure and off. Native coverage stays complete; optional-tool parse failures remain explicit without changing review health. Tests preserve reused checkout HEAD/index/staged/unstaged/untracked bytes. A varied transport property minimized an accounting gap to an escaped unpaired surrogate; the collector now counts its original wire bytes. Nested-field/tree, collector-transition and exact persisted-condition properties pass extended independent seeds. Mermaid 12.2.0 parses 22 production renderer variants and six public decision/example diagrams. The broader handoff checkpoint's current-receipt fixture failures are corrected with explicit native range proof and v13/v14 fixtures; focused posting/coverage suites pass while frozen historical fixtures remain unchanged.

Python 3.15 passes 631 source/contract checks and clean direct-wheel/sdist-derived-wheel integration (three checks), including both diagram types through the installed CLI under hostile import/PATH conditions. The lock changes only Pydantic 2.14.1/core 2.50.1 and MarkupSafe 3.0.4; runtime installation remains hash-locked and binary-only. The Linux 3.15 job and both release-install matrices are implemented; the protected-check ruleset addition is deferred to the final feature-push/CI handoff so unrelated current PRs are not blocked by a job absent on main. Coverage ownership remains 3.14. Focused GitLab CI acquisition reaches 90% and reporting usage 93%, with independent local/hosted module floors added. Public configuration, local/GitLab/security contracts and the decision flow describe optional-only diagram failure recovery and frozen pre-execution tuples. Final full quality, aggregate security scan and own-tool real-model patch review remain pending. No additional push has run; scan count is 0 of 1 and successful own-tool review count is 0 of 2.

The expanded BL-019 campaign now covers every selected family in the verification matrix, including valid round-trips, nested hostile shapes, origin/identity laws, counter conservation and multi-message protocol recovery. The complete 190-check property suite passes the default profile on Python 3.12–3.15 and extended 1000-example profiles under independent seeds 31514 (3.14) and 31515 (3.15). Minimized findings add ordinary regressions for pre-creation handles, invalid-Unicode context state, unhashable CI/lifecycle states, duplicate evidence JSON fields, unsafe MCP correlation IDs, oversized error responses and malformed registry metadata. The focused existing component/TLS/stdio regression set passes 351 checks with two environment-gated native cases skipped. BL-019 is removed from the inactive backlog; corpus ownership and claim limits remain in the development guide and test evidence matrix. Full final quality, the one security scan and actual own-tool model review are still pending.

The single aggregate Codex Security diff scan is complete for b81b4a15..74ddd5e5. All 38 changed production/configuration inventory entries were reviewed under the repository security policy with an independent source-backed architecture pass; no security findings or deferred security coverage remain. Ordinary correctness follow-ups found during review are fixed separately: optional diagram source failures no longer populate the mandatory finding-proof cache, and malformed context/transport/tool-execution receipt enums return closed invalid-receipt results. Mixed real-repository fault fixtures cover missing blob, I/O, invalid UTF-8 and timeout while preserving opaque finding code, outcome and publication state. Receipt properties cross actual file readback; the added family passes supported-Python default replay and independent 1000-example seeds on 3.14/3.15. Focused current/historical receipt, pre-execution, rejection and diagram suites pass 330 checks with ten environment-gated native cases skipped; the additional fault variants and opaque-code controls pass 68 checks. These corrections receive focused semantic review and regression evidence, without repeating the aggregate scan. Security scan count: 1 of 1 completed. Successful own-tool review count: 0 of 2.

Both allowed own-tool ChatGPT reviews are complete for b81b4a15..68a1273c using qualified OCR 1.13.3, gpt-6.1-sol/high and diagram mode local. Each proves native exact identity and 46 selected/completed items with zero failed/reused/waived items and zero failed auxiliary tool calls. The first consumed 780154 tokens and completed through budget grace with four warnings; the second used a raised three-million-token cap, consumed 1987605 tokens, and completed without warnings. Its one finding is confirmed and fixed: release verification matrices now use the existing supported-Python metadata owner in the authorized release checkout, preserving older <3.15 recovery while adding 3.15 for 0.14.0. Exact workflow-payload tests exercise both historical/current metadata and invalid bounds; 59 release/registry checks pass. Both real-model runs chose no diagram output and report not-generated; the production bootstrap requested the fixed tool correctly, and no schema/MCP errors occurred. Actual graph delivery and private Mermaid/text are proven separately by all ten controlled-model native cases and three clean Python 3.15 wheel/sdist installation checks on the same runtime content. Do not claim natural-model graph generation from these two runs. Review allowances are exhausted: security 1/1, successful own-tool 2/2. Remaining corrections use focused tests and semantic review only.

The first complete quality attempt ran 3041 passing tests, 22 skipped and 357 passing subtests, with 88.01% total coverage, but failed six checks. Five enrichment tests used now=0 before their synthetic store birth; their clocks/readback now agree at 150. The identity-diagnostic regression also exposed forwarding of arbitrary Git exception text: public errors are now closed and shallow-history guidance uses the existing typed exception without copying its payload. Scoped provider/runner/range checks pass 294 tests; both generic and shallow error types retain explicit private-diagnostic non-disclosure controls. Dependency audit, tree/history secret, instruction and lifecycle gates pass. Repeat the full quality gate after these corrections; no feature push has occurred.

### Risks And Recovery

Treat missing or contradictory range evidence as a pre-model or admission failure; preserve the existing failure/report semantics without an unverified clean result. Unsupported native diagram capability and model omission remain explicit optional states. Conflict, DLP loss of a necessary condition, stale references or graph budgets omit the entire graph without changing finding health.

Keep private run artifacts run-bound and atomically validated, read the candidate before cleanup, close owned processes and remove temporary auth links without changing persistent native registration. On a failed check inspect the owning evidence and correct the narrow cause; reuse applicable unchanged evidence. Do not overwrite unrelated work or rewrite pushed history. Stop publication on failed protected/security/dependency or immutable-artifact evidence. Recover release delivery only through the existing identity-bound authorizer/receipt path.

### Resume Point

Commit the reviewed closed identity diagnostics and corrected test clocks after format/lifecycle guards and staged secret scan. Repeat the complete quality gate on final runtime content, then remaining pre-push guards, add the protected 3.15 context at the feature-push handoff, push the complete feature and verify protected CI/merge/development publication. The aggregate security scan and both successful own-tool allowances are exhausted; use focused tests and semantic review for ordinary corrections. No further feature push before the local gates. Site work remains WQ-13, after feature merge and before release-branch push.

### Plan Fidelity Check

- [x] Approved outcomes, limits, workflow and privacy constraints are represented by stable requirements.
- [x] Every requirement maps to an ordered queue item and acceptance evidence.
- [x] Native feasibility is distinguished from production admission and final review evidence.
- [x] Pure contracts, acquisition, MCP output, DLP, reporting and publication ownership are explicit.
- [x] Non-goals, rollback/failure behavior, review counts and exact resume action are explicit.
- [x] Repository closure and mandatory external delivery are distinct.

### Reconciliation Check

- [x] Baseline repository and remote main are clean and synchronized.
- [x] Current plan replaces no active work and retains recent completed-plan links.
- [x] Current issue/backlog intent is reconciled with current implementation and approved additions.
- [ ] Final implementation, public status, backlog, checks and issue tracking agree.
- [ ] Final release archive/index and external delivery handoff agree.

### Closure Gate

- [ ] All in-scope repository requirements/queue items are done or explicitly transferred at the release boundary.
- [ ] Applicable final-content tests, coverage, formatting, secrets, dependencies and installed/native boundary evidence pass.
- [ ] Per-commit/aggregate self-review, one security scan and bounded local self-review corrections are complete.
- [ ] Feature PR merge and development publication are verified.
- [ ] Release candidate, version/epoch/authorization/pins/changelog/notes are reviewed and validated.
- [ ] Checked plan lifecycle archives this full plan in the release PR, updates indexes and clears the active pointer.
- [ ] Publication/readback remain truthfully pending as required Post-Close Delivery at repository closure.

### Post-Close Delivery

Required after the release PR archives repository work: pass protected release checks and merge; monitor stable TestPyPI/PyPI publication, artifact equality, supported-Python installs, provenance/attestations, annotated tag, immutable GitHub Release and receipt; independently read back tracked issues/milestone and Actions-owned receipts, site notification/current version, and clean synchronized main. WQ-14/REQ-016 transfer outside the repository plan only at that release boundary, without cancelling the overall delivery objective. No post-release repository closure PR.

The separately owned site candidate and relevant 0.14.0 feature/example content remain part of REQ-017 external coordination. Do not equate an automated version notification with completion of its content assessment. Keep its actual state and exact next action explicit at handoff; unresolved required site delivery is not silently marked complete.

### Handoff Notes

Keep operational state here, not in per-command receipts or duplicate logs. Use bounded native CLI output and private logs only where needed for volume/recovery. Preserve exact review counts, scanned range, corrections and remaining action before context loss. No subagents are authorized by this plan; keep execution with root unless the owner explicitly requests delegation.

## Recently Completed

- [x] 2026-10-25: Completed Two-day GitHub Actions retention; [full archived plan](docs/engineering/execution_history/plans/2026-10-25-two-day-github-actions-retention.md).
- [x] 2026-10-23: Completed Toolkit 0.13.1 partial review of changes containing gitlinks; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-1-partial-review-of-changes-containing-gitlinks.md).
- [x] 2026-10-23: Completed Toolkit 0.13.0 protected default-policy fallback for single-MR review; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-0-protected-default-policy-fallback-for-single-mr-review.md).
