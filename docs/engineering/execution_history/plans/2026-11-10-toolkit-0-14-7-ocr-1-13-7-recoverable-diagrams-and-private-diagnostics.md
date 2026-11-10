# Execution Plans

## Active Plan: Toolkit 0.14.7 — OCR 1.13.7, recoverable diagrams and private diagnostics

plan_schema_version: 2
Status: done
Release classification: release-required
Target release: 0.14.7
Next development marker: 0.15.0
Last Updated: 2026-11-10

### Goal

Implement, publish and independently reconcile toolkit 0.14.7 with qualified OCR
1.13.7, corrected optional diagram submissions and useful bounded private trace
metadata. Carry one delivery objective through feature review, development and
stable publication, external readback, synchronized main and task-owned cleanup.

### Plan Origin

plan_mode_approved

Owner-approved replacement plan of 2026-11-10, including the second analysis and
self-review of every proposal in issue #302. This is its full materialization;
the requirement mapping below preserves the accepted chat plan.

### Requested Scope

Qualify OCR 1.13.7, including Clojure/ClojureScript/EDN Rules, changed default
exclusions, review-loop extraction, native session inspection and unchanged auth
boundaries. Correct #302 without introducing a second review pass, custom OCR
scheduler, alias repair, provider proxy or loss of optional-channel isolation.

Keep one diagram output tool and canonical payload grammar. Simplify advertised
schema for providers while retaining strict server semantics. Allow corrective
submissions within existing run budgets, preserve a valid candidate after an
invalid attempt and retain terminal conflict/budget states. Return bounded safe
feedback, improve bootstrap/help and capture correctly attributed private schema
and native duration/token/cache metadata. Expand real-boundary and property tests.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Complete plan fidelity, signed draft PR and sustained release objective | WQ-01, WQ-08 | done |
| REQ-002 | Exact official Linux/Darwin OCR 1.13.7 qualification and frozen 1.13.6 readback | WQ-02 | done |
| REQ-003 | New language/Rules/exclusions, review-loop handoffs, native auth and session-show qualification | WQ-02, WQ-06 | done |
| REQ-004 | Provider-friendly single-tool schema with strict canonical parser and safe actionable errors | WQ-03, WQ-04 | done |
| REQ-005 | Recoverable invalid submissions, deterministic candidate/conflict/budget state and hostile private storage | WQ-03 | done |
| REQ-006 | Bounded provider-neutral bootstrap, cross-group scope, modes/help and unchanged optional outcomes | WQ-04, WQ-06 | done |
| REQ-007 | Advertised MCP schema evidence, bounded debug v3 and private native trace v2 metadata | WQ-05, WQ-06 | done |
| REQ-008 | Explicit evidence-backed disposition of all seven performance proposals without invented speed claims | WQ-04, WQ-05, WQ-06 | done |
| REQ-009 | Real SDK/wire/installed handoffs, inverse/property tests and branch-aware coverage | WQ-03, WQ-04, WQ-05, WQ-06 | done |
| REQ-010 | Aggregate review, one Security scan, actual own-tool review with admitted diagram and final gates | WQ-06 | done |
| REQ-011 | Protected feature merge and development publication verified | WQ-07 | done |
| REQ-012 | Release metadata, authorization, notes/examples and checked archive handoff prepared | WQ-08 | done |
| REQ-013 | Stable delivery, receipt-backed issue closure, site/main readback and cleanup; required Post-Close Delivery | WQ-09 | out_of_scope |
| REQ-014 | General validation-oracle and measurement-boundary guidance in the existing canonical owner | WQ-06 | done |

### Explicit Non-Goals

No new user environment variable, custom scheduler, per-group effort routing,
additional model diagram pass, global native session discovery, provider proxy,
new caching/compression layer, profiler, exporter or performance.json. Do not
activate BL-016/BL-018 or add speculative roadmap work. No DLP detector change or
unchanged full-corpus audit. No compiler/MSBuild/project execution, historical
evidence rewrite, second landing-page chat handoff or post-release closure PR.
Do not publish private traces, source snapshots, credentials or debug bundles.

### Constraints

- First repository write is this full plan. Reconcile it against the accepted
  chat plan before implementation; preserve full scope at recovery.
- First signed push opens a draft codex/ feature PR containing the plan. Keep
  subsequent implementation local until acceptance; review each logical commit,
  format Python and run the exact staged secret gate. Amend unpublished fixes.
- Freeze composition before expensive reviews. No new libraries are needed;
  change the lock only for demonstrated necessity. Keep Python 3.12–3.15 and
  existing locked binary-only installation and coverage/security floors.
- Collector admits only private output for its bound run/range. Reporting stays
  pure; Git/source/DLP admission and publication retain their current owners.
- Diagram failures must not change findings, coverage, outcome or cleanup.
  Public result/diagram/release receipt schemas remain unchanged.
- Use ordinary CLI execution and native waits. Keep evidence bounded; no duplicate
  transcripts, per-command receipts or unrelated instruction migrations.

### Inputs And Sources

- Owner-approved full replacement plan and explicit implementation request.
- AGENTS.md; canonical development, release, local, diagram, compatibility,
  security, decision-flow and project-principles owners.
- [Toolkit #302](https://github.com/xeonvs/open-code-review-toolkit/issues/302).
- [Canonical OCR qualification #304](https://github.com/xeonvs/open-code-review-toolkit/issues/304), retaining existing verified evidence and CI-owned stable closure.
- [OCR 1.13.7](https://github.com/alibaba/open-code-review/releases/tag/v1.13.7)
  and [adjacent source diff](https://github.com/alibaba/open-code-review/compare/v1.13.6...v1.13.7).
- Current scripts/ocr_compat.py harness, real SDK/stdio/native tests, property
  suites, support manifest and existing checked release lifecycle.

### User Decisions And Answers

- Release by the standard feature/development/stable workflow.
- Analyze and decide every #302 proposal, self-review the resulting complete
  plan and compare it to its disk materialization before implementation.
- Existing inline diffs and concurrency need qualification/navigation rather
  than duplicate toolkit mechanisms. Improve available private metadata now.
- Keep findings primary, diagram optional, deterministic Mermaid rendering and
  the existing automatic flowchart orientation. Do not add textual graph listings.
- For subsequent own-tool reviews, prefer gpt-6.1-sol with xhigh reasoning.
  Preserve the already-running Astra high acceptance rather than restarting it.
- Strengthen future validation generically: test all promised postconditions and
  define observation units/events before measuring concurrent work. Extend the
  existing development owner without case-specific agent rules or duplication.
- Qualification policy's per-version tracker is #304, populated from the existing
  verified evidence without rerunning unchanged qualification. Stable release
  authorization includes #302 and #304; CI owns their receipt-backed closure.

### Completed Baseline State

- Clean synchronized main at 952bff219598149beb83737e31e3369c21cb5e6d; 0.14.6 published.
- Exact Darwin arm64 1.13.7 asset verified against metadata/checksum file; current
  controlled probes passed. New language selection/Rules and four synthetic
  exclusion controls passed. Existing diagram contracts: 126 passed.
- Invalid then valid collection reproducibly stays omitted-invalid.
- Comparable controlled 1.13.6/1.13.7 runs each contain hunks in all three main
  requests and duration/usage in all five responses. Current toolkit projection
  demonstrably drops those metrics; no real-model speed equivalence is claimed.
- Open dependency PR inventory empty; dependency audit reports no known issues,
  excluding the local unpublished SCM project itself. Linux Docker is available.
- Planning artifacts remain private and are reusable only for unchanged inputs.

### Current Work Queue

| Item | Work and exit evidence | Requirements | Status |
| --- | --- | --- | --- |
| WQ-01 | Materialize/reconcile plan, enable active state, sign/scan/push plan and open draft PR | REQ-001 | done |
| WQ-02 | Extend current qualification, freeze old readback, verify Linux/Darwin assets and optional handoffs; promote only after passing | REQ-002, REQ-003 | done |
| WQ-03 | Implement closed parser diagnostics and collector v2 transitions with compact state/inverse/hostile-storage tests | REQ-004, REQ-005, REQ-009 | done |
| WQ-04 | Simplify MCP schema, qualify provider wire, revise bounded bootstrap/status/help and actual retry handoff | REQ-004, REQ-006, REQ-008, REQ-009 | done |
| WQ-05 | Capture advertised schema, preserve numeric native metrics in trace v2 and debug v3; qualify private lifecycle | REQ-007, REQ-008, REQ-009 | done |
| WQ-06 | Final docs/issue disposition, properties/coverage, aggregate review, one Security scan, own-tool diagram and final quality/install gates | REQ-003, REQ-006 through REQ-010, REQ-014 | done |
| WQ-07 | Exact Mermaid delivered in #303; protected head d9b0177 merged as b6cde02; development publication and verification 42852688869 passed | REQ-011 | done |
| WQ-08 | Stable metadata/notes/pins and checked archive/reset handoff prepared; signed release PR, focused post-archive guards, CI and merge are required Post-Close Delivery | REQ-001, REQ-012 | out_of_scope |
| WQ-09 | Required stable receipts/install/provenance/tag/release/issue/site/main readback and task cleanup are classified in Post-Close Delivery | REQ-013 | out_of_scope |

### Locked Decisions

#### Diagram contract and retry

- Keep ocr_toolkit_review_diagram and canonical generated/not-applicable payloads.
  Advertise object-root schema with properties/enums/bounded arrays and finite
  sequence expansion, without oneOf/anyOf/allOf/not/$defs/$ref/const. The strict
  parser still enforces cross-field grammar and rejects guessed aliases.
- Retain 16 KiB candidate, eight attempts/128 KiB original wire input; flowchart
  12 nodes/16 edges; sequence eight participants/16 total messages/four alt/depth
  two; labels one line/80 code points/320 bytes; up to two source references.
- Every bound submission consumes budgets. Invalid attempts are repairable;
  invalid-after-valid preserves the candidate. Identical normalized valid repeats
  are idempotent. Different valid candidates give terminal conflict, excess gives
  terminal budget. Never select first/last or merge candidates.
- Keep storage/run/range corruption and I/O faults separate from model-correctable
  validation. Feedback is a normal optional MCP response with state=invalid,
  retryable, submissions_left and closed code/pointer/static message/allowed enum
  values. Never reflect arbitrary input or unknown keys. Pointer uses known
  fields and bounded indexes only.
- Collector v2 keeps the last safe diagnostic (at most 1 KiB), not raw attempt
  history. Give storage 18 KiB for maximum candidate plus diagnostic/metadata,
  within the existing 20,000-byte debug artifact cap. Do not reuse old ephemeral
  collectors. Status adds retryable-invalid when no valid candidate exists.
- received confirms collection only. Immutable source/DLP checks still occur
  after native execution. Preserve valid output across fresh rounds; only the
  existing output-owner group submits, with relevant cross-group context.

#### Prompt and diagnostics

- Remove ambiguous model-proposed wording. Add a compact diagram-object example,
  explicit wrapper fields and refs lookup without repeating SHA. The example is
  structural, not source evidence. Reuse inline hunks first, reading missing
  source/dependency/cross-group context when necessary; do not prohibit reads.
- Keep default 3000-character bootstrap by regrouping existing instructions.
  Preserve required prefix/suffix/truncation notice and evidence/framework/version,
  completeness, context/policy and federation navigation for every supported mode.
  The current complex profile already uses 2659 protected characters.
- Final omission logs a short safe reason/pointer; recovered output does not log
  a false omission. Help documents on/unset versus local semantics.
- Debug v3 captures the advertised toolkit MCP name/schema/hash with explicit
  origin. It does not claim to observe provider/gateway wire; controlled peers
  prove OpenAI Chat Completions/Responses/Anthropic transformations separately.
- Trace v2 preserves available duration_ms on responses/errors/tool calls, known
  numeric prompt/completion/cache-read/cache-write usage, and session duration.
  Fields are optional, absent is not zero; reject invalid/nonfinite/negative or
  unbounded metadata with explicit degraded capture, never review failure.
- Preserve private permissions, source/record/output caps and exclusion of
  reasoning, opaque replay, config and credentials. No global session discovery.

#### Every performance proposal in #302

| Proposal | Decision and evidence boundary |
| --- | --- |
| 1. Prefetch group hunks | Already inline in actual 1.13.6/1.13.7 main requests. Add navigation/regression, not duplicate global diffs or unqualified full-file/function prefetch. |
| 2. Split heavy groups/longest first | OCR already applies token/file limits; dispatch follows group order. Cost-aware splitting/scheduling belongs upstream and needs coverage/cross-component/cancellation/budget qualification; no toolkit scheduler. |
| 3. Cache/compact repeated context | Responses affinity and Anthropic breakpoints exist; OpenAI-compatible backend behavior varies. Qualify existing controls/preserve reported cache usage; no global key, new cache or compression. Input/output ratio alone proves no cache defect or cost. |
| 4. Lower effort for docs | Reject automatic downgrade: docs include policy/security/CI contracts. Preserve explicit run-level effort; do not activate BL-016/BL-018. |
| 5. Lightest group/dedicated diagram task | Actual group costs unavailable to toolkit before execution; lightest file need not be lightest group and no task CLI exists. Preserve deterministic owner and global source scope. |
| 6. Fine-grained metrics | Preserve existing native durations/usage now. Do not fabricate millisecond timestamps, start/end or queue waits. |
| 7. Concurrency setting | Qualify/document existing --concurrency (default eight), actual bounds and stop/coverage behavior. No new environment setting or default change. |

- Record disposition of A-G and these seven proposals in #302 before acceptance.
  Its functional closure makes no general speed or arbitrary-gateway promise.
- parentUuid is record-chain order, not request causality; group keys are opaque,
  not comma-separated paths. Do not invent request IDs, add parallel durations
  into wall time, double-count usage or infer billing/cache savings.
- Analyze the actual own-tool trace with bounded existing queries for long task
  labels, LLM/tool durations, read categories, reported usage and completeness;
  no new profiler/artifact or extra model benchmark.

### Verification

- V-01 / REQ-001: reconcile every accepted plan section, decision, source and
  delivery condition to requirements/queue; initial fidelity check before code.
- V-02 / REQ-002,003: official Linux amd64 qualification in disposable pinned
  container, independent Darwin, new languages/Rules/exclusions and old controls;
  grouping/round/MCP/federation/budgets/grace/manifests/findings/diagrams/gitlinks/
  cancellation/cleanup plus native-auth source and session-show cases.
- V-03 / REQ-004,005,009: state/property matrix for invalid→valid, valid→invalid,
  normalized repeats, both conflict orders, final allowed attempt, byte/count
  exhaustion, concurrency, maximum candidate+diagnostic and hostile storage.
- V-04 / REQ-004,006,009: actual SDK/stdio/native peer repair and preserved findings;
  both variants, stale range/references/Unicode/nesting/sensitive material; schema
  wire capture on three protocols, server semantics and safe feedback reflection.
- V-05 / REQ-006,008: render/inspect all local/GitLab/context/federation profiles,
  large inventories and clipping under default bounds; retain mandatory navigation
  and single SHA block; qualify existing concurrency on real controlled peer.
- V-06 / REQ-007,009: present/absent/zero/malformed/boolean/negative/oversized metrics,
  unknown fields, interleaved tasks, incomplete/truncated/changed native files;
  private artifact ownership/limits and cleanup independent of debug failure.
- V-07 / REQ-009: 100-example CI and 1000-example local properties, minimized
  regressions; at least 90% branch-aware touched runtime modules, existing floors.
- V-08 / REQ-010: aggregate semantic review, one Security diff scan and threat-model
  reconciliation; actual ChatGPT high own-tool review with max-tokens-budget=0,
  private debug, local diagram, meaningful changed tests in operator Rules. Inspect
  raw findings/omissions/warnings/auxiliary reads/schema/metrics/admitted graph.
  Second model review only for incomplete acceptance or a concrete new gap.
- V-09 / REQ-009,010: full quality once on final runtime head, applicable clean
  wheel/sdist installed handoffs, formatting/static/secret/dependency gates.
- V-10 / REQ-011 through REQ-013: exact feature Mermaid/protected CI/development,
  signed release metadata/atomic archive, Python 3.12–3.15 installs, registry hashes,
  provenance/attestations/tag/immutable release/receipt, CI-owned #302 closure,
  site and synchronized main readback; no additional closure PR.

### Latest Validation Results

2026-11-10 planning evidence: Darwin current contract suite passed on exact OCR
1.13.7; new language selection/Rules/exclusions passed; 126 existing diagram
checks passed. Comparable controlled 1.13.6/1.13.7 probes confirmed inline hunks
and native metadata availability. Correction/extended Linux/new production
contracts remain unimplemented. Dependency audit passed for current dependencies.

2026-11-10 implementation: signed plan commit 771d1e9 opened draft PR #303.
Frozen 1.13.6 readback validates without rewriting evidence. Expanded Darwin
suite passed with 52 language paths, Clojure Rules in main request and native
EDN context reads; qualification tests: 237 passed. Linux uses official Python
image under amd64 emulation, hash-locked runtime and no operator credentials.
The first image had unsupported Git 2.39.5; its native warning correctly failed
the diagnostic gate. Full Linux qualification then passed on Git 2.47.3 with
official image digest 1cef1664561971647b94fedf437145415991d4feeda09c81df12acfad8829cde.
No gate was weakened. Supplemental gitlink/federation checks passed; recommendation
and preflight now admit 1.13.7. Frozen/current qualification regressions: 245 passed.

Production diagram changes passed 60 focused collector/feedback checks and 47
schema/SDK/optional-channel checks. Actual OCR-to-MCP-to-report repairs passed
for both variants, following observed invalid feedback. Three actual API adapter
captures preserve the advertised schema. Bootstrap/trace checks: 145 passed;
the default 3000-character bootstrap retains protected navigation. Native default
eight and explicit one/two concurrency bounds, full selected coverage, outside-CWD
session lookup, restriction, missing/invalid and ambiguous IDs passed with isolated
synthetic sessions. Numeric trace properties retain absent-versus-zero semantics.

Final focused native consumers: 37 passed, including actual factory-schema debug
capture, grouped evidence, private trace and repaired output. Focused suites: 442
passed; additional owner checks: 169 passed; extended 1000-example state/metric
properties and optional regressions: 55 passed. Branch-aware owner measurements:
diagnostics 95%, collector 97%, contracts 99%, MCP 98%, lifecycle 91%, bootstrap
91%, debug 93% and trace 96%. Ruff and all runtime types passed. The obsolete
peer assertion caused an interrupted early coverage attempt; the corrected run
passed and its task-owned children were cleaned. Local OCR is replaced by the
verified 1.13.7 binary. #302 now records A-G and every performance disposition.

Aggregate semantic review completed on dc1d55f. One Codex Security diff scan
covered 952bff2..dc1d55f with four independent Astra high reviewers and parent
documentation/test reconciliation: zero candidates/findings, complete changed
surface coverage. The canonical threat model remains applicable and documents
closed feedback and private definition provenance. Scan usage accounting is
partial and is not a billing measurement. Clean wheel/sdist installed acceptance:
three tests passed, including real installed MCP/local-review and debug parity.

Actual ChatGPT/Astra high own-tool review completed on the same immutable range,
with max-tokens-budget=0, local diagram and private debug. An explicit operator
overlay derived from base retains system Rules and includes meaningful changed
tests: all 50 files, including 16 test files, completed. Two medium findings
survived DLP unchanged; the ten-node TB Mermaid flowchart was admitted and its
semantics inspected. Both findings are fixed: field/collection scopes now retain
diagnostic provenance, and native request accounting ends before response
delivery, separately checking saturation under a bounded probe deadline.
Corrections passed 108 checks including 1000-example properties, plus three
native controls; instruction-contract is valid. Generic postcondition/oracle and
measurement-boundary guidance extends the existing development owner.

The single failed guessed-path read was recovered in the same group by reading
the actual contracts.py mode parser. The 2260-character background advisory is
about a recommendation, not truncation/exhaustion; protected context is intact
within the configured 3000-character bound. No budget/round/context exhaustion
warning appeared. All 64 native responses retain duration/usage; reported session
duration is 152.637 seconds and response usage totals agree with native review
totals. No parallel-duration sum or billing inference is made. Source snapshots
from Linux qualification have been removed. Corrections leave the admitted flow
unchanged; focused native/property checks and semantic review qualify them without
a second model run or another aggregate Security scan.

Final runtime head 28afc57: full quality run passed static/security checks and
5005 tests with 357 subtests; two stale qualification expectations failed. Only
test/instruction corrections followed: exact capability fixtures now include the
newly qualified patch and future negatives; live selection follows the current
recommendation, while frozen fixtures retain exact versions. The boundary test
module has a semantic name and is included in the focused qualification route.
All 35 affected checks passed; coverage was appended to the full measurement.
Every remaining canonical coverage floor then passed separately: 90.13% overall,
95% diagnostics/lifecycle, 97% collector, 99% contracts, 98% MCP, 94% bootstrap/debug
and 96% trace. No runtime changes followed that full measurement. Dependency,
working-tree disclosure and unpublished-history scans passed; final push guards
must cover the final documentation/test commit as well.

Final signed feature head d9b0177 is pushed and PR #303 is ready, with the exact
admitted Mermaid in its body. GitHub verifies its signature; protected-base
identity remains 952bff2. Final push dependency/disclosure/history gates passed.
Required static, security, CodeQL, dependency and build checks passed; required
Linux Python jobs also passed before merge. Local status reconciliation is
included in the release archive rather than another feature push.

Protected feature checks passed on d9b0177 and #303 merged as b6cde02.
Development run 42852688869 passed classification, build, publication and immutable
registry/provenance/installed verification. Local main fast-forwarded to that
same merge. The missing canonical per-version tracker is now owner-authored
#304 with the exact marker and existing evidence; no qualification is rerun.
Release preparation is on release/v0.14.7 with #302/#304 authorization.
Stable marker 0.14.7, next marker 0.15.0, source epoch, authorization, generated
changelog/notes and paired toolkit/OCR/checksum pins are prepared. Canonical
qualification links use #304. The full archive/reset transition is prepared for
the checked lifecycle; focused release guards run after its final documents exist.
The checked archive/reset completed; 130 focused release/environment/receipt/notes
contracts and instruction/lifecycle guards passed on the prepared release tree.
Runtime source remains identical to accepted feature merge b6cde02.

### Risks And Recovery

- Permissive advertised structure must not widen server admission; test both.
- Retry feedback must not reflect private data or alter findings. Keep attempt,
  collection, semantic admission and publication identities separate.
- Maximum candidate plus later error must fit storage; reject hostile files and
  preserve atomic descriptor-relative writes and lock ownership.
- Prompt additions must not overrun default bounds or displace required evidence.
- Debug metrics are reported evidence, not causality, completeness or cost proof.
- On failure inspect the class, fix the compact reproducer/affected consumers
  before broad replay, and retain applicable unchanged evidence. Never weaken
  scanners, force publication, silently waive model warnings or claim a skipped
  stage passed. Preserve exact resume action if externally blocked.
- No runtime rollback changes published evidence or tags. Keep old qualified
  support until promotion succeeds; failed optional output remains omitted.

### Resume Point

No unfinished repository implementation or preparation remains. Required
post-archive guards, signed release delivery and external reconciliation are
classified in Post-Close Delivery; the overall release goal remains active.

### Plan Fidelity Check

- [x] Accepted replacement plan sections 1–5 and all #302 A-G/performance decisions retained.
- [x] Requirements map to ordered work and explicit behavioral verification.
- [x] First-write/goal/signing/draft/local-development/release/archive/readback constraints retained.
- [x] All diagram bounds, privacy/source/authority boundaries and rejected alternatives retained.
- [x] Evidence distinguishes planning checks, remaining implementation and external delivery.
- [x] Risks, recovery, cleanup and exact first safe action recorded; no private chat identifiers.

### Reconciliation Check

- [x] Requirements, queue, native qualifications and final diff agree.
- [x] #302 A-G and all seven performance proposals have explicit verified disposition.
- [x] Documentation, diagram flow, evidence matrix, threat model and inactive backlog agree.
- [x] Version/notes/pins/authorization and archive/external delivery ownership agree.

### Closure Gate

- [x] Repository implementation and feature validation are complete; post-archive release guards are explicitly classified below.
- [x] Review findings resolved, positive own-tool diagram accepted and runtime gates passed.
- [x] Protected feature/development delivery and prepared stable metadata are verified.
- [x] Checked lifecycle owns the complete archive/reset transaction in the release PR; no later closure PR is required.

### Post-Close Delivery

Required work outside the closed repository plan remains part of the active
release objective:

1. Checked archival and 130 focused release contracts plus instruction/lifecycle
   guards passed. Complete final privacy/dependency gates, sign and push
   release/v0.14.7, open exact-title `Release v0.14.7`, require protected checks and
   merge only the exact checked head. No new Security/model review is required
   for unchanged runtime and release-only metadata/documentation.
2. Independently read back CI-owned TestPyPI/PyPI publication, all Python
   3.12–3.15 installs, hashes, provenance, attestations, annotated tag and immutable
   Release/receipt. Do not claim these before they exist or repeat successful
   CI-owned artifact installations locally.
3. Verify CI-owned receipt-backed closure for #302 and #304, any associated
   milestone, the site workflow and live site, then clean synchronized main.
4. Remove task-owned temporary source copies, debug/build/test environments and
   obsolete task artifacts/images without deleting durable audit keys, retained
   Security evidence or unrelated work. No additional closure PR or landing chat
   handoff is required. Close the overall goal only after external verification.

### Handoff Notes

All repository implementation and stable preparation are complete. Feature #303
and development publication are verified. This archive is a prepublication
handoff; required stable delivery/readback/cleanup is preserved above and the
overall goal remains active. No private trace/source or chat identifiers are
embedded here. The checked lifecycle owns archival and root/state/index reset.

## Recently Completed

- [x] 2026-11-06: Completed Internal engineering cycle corrections; [full archived plan](docs/engineering/execution_history/plans/2026-11-06-internal-engineering-cycle-corrections.md).
- [x] 2026-11-06: Completed Toolkit 0.14.6 — OCR 1.13.6, DLP precision and efficient delivery; [full archived plan](docs/engineering/execution_history/plans/2026-11-06-toolkit-0-14-6-ocr-1-13-6-dlp-precision-and-efficient-delivery.md).
- [x] 2026-11-04: Completed Toolkit 0.14.5 — DLP precision, OCR qualification and maintenance quality; [full archived plan](docs/engineering/execution_history/plans/2026-11-04-toolkit-0-14-5-dlp-precision-ocr-qualification-and-maintenance-quality.md).
- [x] 2026-10-31: Completed Toolkit 0.14.4 systematic DLP corrections and diagram source validation; [full archived plan](docs/engineering/execution_history/plans/2026-10-31-toolkit-0-14-4-systematic-dlp-corrections-and-diagram-source-validation.md).
- [x] 2026-10-30: Completed Toolkit 0.14.3 source-aware DLP and private corpus audits; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-3-source-aware-dlp-and-private-corpus-audits.md).
- [x] 2026-10-30: Completed Toolkit 0.14.2 compact bootstrap, diagram-only reports and DLP corrections; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-2-compact-bootstrap-diagram-only-reports-and-dlp-corrections.md).
- [x] 2026-10-29: Completed Toolkit 0.14.1 grouped diagrams and private debug qualification; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-1-grouped-diagrams-and-private-debug-qualification.md).
- [x] 2026-10-29: Completed Toolkit 0.14.0 range identity, typed diagrams, DLP qualification and Python 3.15; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-0-range-identity-typed-diagrams-dlp-qualification-and-python-3-15.md).
- [x] 2026-10-25: Completed Two-day GitHub Actions retention; [full archived plan](docs/engineering/execution_history/plans/2026-10-25-two-day-github-actions-retention.md).
- [x] 2026-10-23: Completed Toolkit 0.13.1 partial review of changes containing gitlinks; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-1-partial-review-of-changes-containing-gitlinks.md).
