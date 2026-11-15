# Execution Plans

## Active Plan: Toolkit 0.15.0 — complete evidence, .NET and numeric DLP

plan_schema_version: 2
Status: active
Release classification: release-required
Target release: 0.15.0
Next development marker: 0.16.0
Last Updated: 2026-11-15

### Goal

Implement, publish and independently verify toolkit v0.15.0: issues #311–#316,
bounded static .NET evidence, adaptive atomic evidence budgets, numeric DLP
corrections, qualified OCR 1.13.9/1.13.10, and useful current roadmap/backlog.
Carry the same objective through feature acceptance, stable delivery, external
readback, the local OCR update and task-owned cleanup.

### Plan Origin

plan_mode_approved

Full materialization of the approved plan and implementation request. This is
the first repository write. No implementation or configuration change precedes it.

### Requested Scope

| Issue | Approved outcome |
| --- | --- |
| #311 | Replace ineffective concurrency-variable advice with the supported native flag. |
| #312 | Add the bounded .NET evidence pack, activating the demonstrated BL-010 slice. |
| #313 | Share Dockerfile/Containerfile recognition across category, acquisition and FROM parsing. |
| #314 | Correct complete numeric spans, decimals, grouped amounts, dotted dates and datetimes, including all three issue comments. |
| #315 | Remove the artificial approximately 256-modified-file ceiling without partial mandatory snapshots. |
| #316 | Document explicit opt-in MR-label skipping with truthful merge/approval implications. |

Qualify the contiguous OCR 1.13.8 → 1.13.9 → 1.13.10 chain and recommend 1.13.10
only after complete acceptance. Clean current planning documents while preserving
durable architectural limits and historical evidence at their existing owners.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Complete plan fidelity, delivery goal, signed first push and draft PR | WQ-01 | done |
| REQ-002 | #315 adaptive structural budget, atomic store and bounded serialization | WQ-02 | done |
| REQ-003 | #315 v7 pre-execution budget diagnostic, freshness and preservation | WQ-02 | done |
| REQ-004 | #312 bounded XML/JSON .NET manifest facts and project scopes | WQ-03 | done |
| REQ-005 | #312 conservative central-version links, ASP.NET Core plugin, deltas and MCP | WQ-03 | done |
| REQ-006 | #313 shared container-build path recognition | WQ-03 | done |
| REQ-007 | #314 all numeric/date cases and inverse material protection | WQ-04 | done |
| REQ-008 | Structural Hypothesis, paired private audits, resource comparison and repeat | WQ-04, WQ-07 | in_progress |
| REQ-009 | Exact OCR assets, excluded coverage and request-scoped tools qualification | WQ-05 | pending |
| REQ-010 | Hosted qualification, promotion, local binary update and weekly schedule | WQ-05, WQ-10 | pending |
| REQ-011 | #311 actual concurrency control and #316 opt-in skip example | WQ-06 | pending |
| REQ-012 | Remove completed planning history; regroup inactive work and preserve unique limits | WQ-06 | pending |
| REQ-013 | Focused/installed/integration tests and measured coverage floors | WQ-02, WQ-03, WQ-04, WQ-05, WQ-06, WQ-07 | pending |
| REQ-014 | Aggregate self-review, one Security scan, real own-tool review and admitted PR diagram | WQ-07 | pending |
| REQ-015 | Final quality, protected feature merge and development TestPyPI verification | WQ-07, WQ-08 | pending |
| REQ-016 | Signed Release v0.15.0 PR, markers, authorization, notes, pins and plan archive/reset | WQ-09 | pending |
| REQ-017 | Independent registry/install/provenance/tag/receipt/issues/site/main verification | WQ-10 | pending |
| REQ-018 | Owned source snapshots, builds, environments, debug and obsolete binaries removed | WQ-10 | pending |
| REQ-019 | Local CLI debug/retention combinations preserve useful authorized diagnostics without forge authority | WQ-06, WQ-07 | in_progress |
| REQ-020 | Improve the actual model/tool/release cycle and canonical instructions where evidence warrants | WQ-06, WQ-07 | in_progress |
| REQ-021 | Update compatible stable libraries, uv and immutable GitHub Action pins before expensive acceptance | WQ-11, WQ-07 | in_progress |

### Explicit Non-Goals

No new toolkit environment variables or CLI flags, general MSBuild evaluator,
NuGet restore/build/network resolution, nuget.config acquisition, second review
engine, new forge adapter or automatic finding masking. No activation of model
profiles, configuration framework, managed OAuth or related-MR review. No new
dependency additions without a demonstrated package boundary. No
landing-chat handoff, private corpus CI stage, historical evidence rewrite or
post-release closure PR. No copied private code, private project identities,
paths, credentials, internal chat identifiers or raw debug in public artifacts.

### Constraints

- Preserve Python 3.12–3.15, hash-locked binary-only runtime installs and existing
  security/coverage floors. Overall coverage gate remains 88%; measure margin.
- First signed push contains the plan and opens a draft feature PR. Keep further
  implementation local until final feature acceptance; amend unpublished fixes.
- Semantic self-review, formatting and staged secret scan precede each commit.
  Tree/history secret and dependency gates precede every push.
- Use direct native CLI execution and bounded output. Reuse unchanged evidence,
  native process sessions and completion-driven waits; no per-command receipts,
  duplicate transcripts or new command-runner framework.
- Reporting remains pure. Parsers/linkers operate on bounded immutable inputs;
  the existing Git reader and runner own acquisition and orchestration.
- Preserve source/sink authority, whole-material DLP checks and optional diagram
  independence from findings, completeness, approval and cleanup.
- Mandatory B/H/P snapshots, indexes and deltas remain atomic. Optional T context
  cannot displace their budget or confer policy/completeness authority.
- Preserve old v5/v6 pre-execution contracts and historical evidence bytes.
  Ordinary receipt/range/diagram structures remain unchanged by this scope.
- Run one aggregate Security diff scan before own-tool acceptance. Later fixes
  receive focused validation; repeat an expensive scan/review only for a concrete
  uncovered material boundary or incomplete acceptance.
- Normal own-tool acceptance uses ChatGPT high, budget 0, private debug and an
  actually generated/admitted diagram. Inspect raw findings, omissions, warnings
  and failed reads; include the exact admitted Mermaid in the feature PR.
- Required Linux checks block release. Advisory macOS outcomes remain visible
  without delaying a Linux-priority release.

### Inputs And Sources

- Owner-approved implementation plan and decimal-ambiguity answer.
- Issues https://github.com/xeonvs/open-code-review-toolkit/issues/311 through
  https://github.com/xeonvs/open-code-review-toolkit/issues/316, including all
  comments read during planning; #314 has three material continuations.
- OCR releases https://github.com/alibaba/open-code-review/releases/tag/v1.13.9
  and https://github.com/alibaba/open-code-review/releases/tag/v1.13.10, their
  official assets/checksum files and adjacent source changes.
- Actions-owned qualification issues #318 (1.13.9) and #319 (1.13.10), created by
  workflow 43719258074; use these canonical trackers rather than duplicate issues.
- MSBuild folder semantics:
  https://learn.microsoft.com/en-us/visualstudio/msbuild/customize-by-directory
  and central package management:
  https://learn.microsoft.com/en-us/nuget/consume-packages/central-package-management.
- GitLab rule semantics: https://docs.gitlab.com/ci/jobs/job_rules/.
- Canonical project principles, development/release/compatibility/security/local
  and DLP-audit guides, current strategy and evidence/decision-flow contracts.
- Installed engineering-workflow planning/lifecycle owners. Workflow migration
  is not part of ordinary plan/backlog maintenance.

### User Decisions And Answers

- Publish a complete standard release; choose the version from the resulting
  scope. Static .NET evidence warrants 0.15.0; next marker is 0.16.0.
- Treat a complete single-dot decimal without '+' or explicit contact context
  as a decimal, including a shape that could be a short local phone. Preserve
  that deliberate ambiguity policy in tests and public security guidance.
- Keep additions general-purpose and structurally justified; a filename,
  repository, language or successful parse grants no confidentiality exemption.
- Remove completed tasks from current planning, regroup unfinished tasks and
  select related backlog work. BL-010's .NET slice is activated; other conditional
  work remains inactive.
- Keep minimum configuration surface, actual own-tool diagram acceptance and
  the normal protected two-PR delivery lifecycle. No landing-chat handoff.
- Subsequent owner request: check local CLI debug/artifact-retention combinations
  for later diagnosis, and recheck the recorded plan against the approved plan.
  Current code/docs forbid --debug-dir with --preserve-private-artifacts; verify
  their real lifecycles and remove an unjustified local-only incompatibility.
- The owner subsequently rejects legacy preservation. Consolidate diagnosis into
  --debug-dir with bounded necessary evidence/context/action captures before
  cleanup; remove the separate --preserve-private-artifacts interface and producer
  path without an alias. Keep hostile rejection of old diagnostic artifacts where
  it prevents publication, not an old positive generation/execution path. Debug
  must never mislabel an unfiltered retained result as safe-result.json.
- Subsequent owner requests include improving the actual model/tool/release
  cycle and checking agent/project instructions, plus updating existing libraries
  and GitHub Actions to current compatible stable versions. This supersedes the
  original dependency-only-on-need restriction. Check immutable action identity
  and supported binary installs; freeze composition before expensive acceptance.

### Completed Baseline State

- Clean local main and remote main both resolve to
  80eebd6497b3e1dd3fa002d764175002f94a1cd2; published toolkit is 0.14.8.
- Planning inventory found six open issues (#311–#316), all comments read, and
  no open pull requests, including Dependabot. Recheck for drift before delivery.
- #315 reproduced with 260 modified files: 520 repository.file records exceed
  the current 512 per-kind limit. With sufficient record capacity the complete
  store is 452700 bytes, 780 records and 260 deltas, without diagnostics.
- #314 reproduces grouped amounts, complete dotted dates/datetimes, adjacent
  parenthesized decimals and long single-dot fractions as phone:normalized.
  Explicit contact/+ controls remain rejected at baseline.
- Verified official Darwin arm64 OCR 1.13.9 and 1.13.10 against metadata and
  checksum files. Each completed all 20 existing controlled LLM/MCP peer groups.
  This does not replace new-contract, Linux or hosted qualification.
- Existing roadmap/backlog retain completed history. Some documentation tests
  require obsolete wording in those documents; retarget them to canonical owners
  rather than preserving duplication to satisfy assertions.

### Current Work Queue

| Queue | Ordered work and acceptance | Requirements | Status |
| --- | --- | --- | --- |
| WQ-01 | Full plan/fidelity, signed 6e11f47 first push and draft PR #317 completed | REQ-001 | done |
| WQ-02 | Atomic structural/optional budgets, bounded serializer/target batches, v7 CLI/readback/freshness diagnostics qualified | REQ-002, REQ-003, REQ-013 | done |
| WQ-11 | Eleven compatible lock upgrades and uv 0.13.8 applied; all current Action tag/SHA identities verified; composition frozen | REQ-021 | done |
| WQ-03 | Bounded .NET declarations/central links, project-scoped ASP.NET, shared container grammar and Git/store/stdio MCP handoffs accepted | REQ-004, REQ-005, REQ-006, REQ-013 | done |
| WQ-04 | Numeric span/date corrections and initial authenticated paired audits accepted; final resource/repeat comparison remains at WQ-07 | REQ-007, REQ-008, REQ-013 | done |
| WQ-05 | New OCR contracts, exact Linux assets, hosted chain qualification and promotion; logical commit | REQ-009, REQ-010, REQ-013 | in_progress |
| WQ-06 | Operator guidance, label example, unified local diagnostics, workflow-cycle audit, roadmap/backlog and canonical owners; logical commits | REQ-011, REQ-012, REQ-013, REQ-019, REQ-020 | pending |
| WQ-07 | Repeated corpus comparison, aggregate review, one Security scan, own-tool findings/diagram, final quality and installed gates | REQ-008, REQ-013, REQ-014, REQ-015, REQ-019, REQ-020, REQ-021 | pending |
| WQ-08 | Final feature push with exact diagram, protected CI/merge and development TestPyPI verification | REQ-015 | pending |
| WQ-09 | Signed release/v0.15.0 PR with exact title, metadata/notes/pins and lifecycle archive/reset; protected merge | REQ-016 | pending |
| WQ-10 | Stable external readback, CI-owned issue/milestone closure, site, local OCR update, synchronized main and cleanup | REQ-010, REQ-017, REQ-018 | pending |

### Locked Decisions

#### .NET evidence

Use ecosystem dotnet through existing manifest collectors, scoped coverage,
framework plugins, deltas, bootstrap and evidence MCP. Support csproj/fsproj/vbproj,
Directory.Build.props/targets, Directory.Packages.props, packages.lock.json and
global.json. Collect SDK, TargetFramework(s), LangVersion, Nullable,
PackageReference/FrameworkReference, central declarations, framework-scoped
direct/transitive locked packages and SDK version/rollForward. Categorize these
as dependency manifests; .cs/.csx as csharp without claiming native selection.

Use stdlib Expat with DTD/entity/external-entity rejection and construction-time
bytes/depth/element/attribute/fact bounds; no new runtime dependency. Support XML
namespaces, attributes/child values, conditions and multi-targeting. Do not
evaluate expressions, property functions, Import or Update semantics. Preserve
conditional alternatives/provenance and partial/runtime-dependent outcomes.
Link a versionless reference to the nearest central file only when central
management and the link are statically unambiguous. Conflicts, overrides or
unknown imports prevent an effective-version claim. Keep sibling/nested project
scopes independent; folder discovery is not MSBuild evaluation. Never read
nuget.config or run restore/build/network resolution.

Add ASP.NET Core detection through Web SDK and framework/package references with
distinct evidence provenance. A TFM never invents a resolved ASP.NET Core version.
Exercise base/head deltas, scope completeness and actual MCP access.

#### Atomic evidence budgets

Derive structural capacity from actual B/H snapshots, policy, coverage and
categories. Preserve existing optional typed-fact caps independently from
structural growth; reserve invocation/context/diagnostic room. Keep absolute
100000-record, 20 MB serialized and existing Git-reader bounds. Enforce bounded
serialization without quadratic whole-store reserialization. Keep every snapshot,
index and delta consistent; optional T still follows mandatory B/H/P.

On a genuine hard budget overflow, run no model. Produce pre-execution status v7
with closed evidence_budget_exceeded reason, records/bytes/entries unit,
actual/limit and existing immutable identity. Old v5/v6 remain frozen. Local
reports the same safe reason. GitLab permits only authenticated fresh diagnostic
publication, preserves prior findings and performs no approval/thread cleanup.
Identity failures, corruption and unknown errors remain ordinary failures.

#### Numeric DLP

Recognize complete single-dot decimal tokens, correctly space-grouped fractional
amounts, separate decimals through spaces/parentheses, valid DD.MM.YYYY dates and
datetimes with existing calendar/time/zone checks. '+' and contact intent take
priority. Do not join separate fractional tokens for digit counts or borrow a
technical span for adjacent contact material. Keep national/multi-dot phones,
independent contacts/secrets and all original/decoded/publication checks. Keep
source-proof/sink authority and omission behavior; add no automatic masking.

#### Container and operator contracts

One case-insensitive Dockerfile/Containerfile predicate recognizes the base name,
base.variant and name.base across categorization/acquisition/FROM parsing. Test
multi-stage aliases, platform arguments and negative names. Replace current
OCR_REVIEW_CONCURRENCY advice with native --concurrency N after the existing '--'
separator; preserve default 8 and completion-token control. Do not rewrite history.

Document an opt-in no-ai-review exact-label rule before the ordinary MR run rule.
The main example remains enabled by default and manual readiness remains available.
Explain pipeline-time rule evaluation/new-pipeline requirements and that skipping
does not remove an old review or approval and may weaken review requirements.
GitLab permissions and merge/reset policy own those consequences.

#### OCR and planning documents

Qualify excluded reasons/identity/disjoint selected/terminal partition and
request-scoped tool availability across evidence/diagram/federation and later
rounds. Toolkit keeps explicit immutable range, existing JSON/numeric/partial/
grouping/comparison/gitlink/diagram contracts and no workspace/resume adoption.
Verify Linux assets, run hosted chain qualification and promote only after proof.
Preserve weekly scheduling and frozen historical bytes. Update installed OCR to
the qualified recommendation and remove its former installed version.

Roadmap contains nearest/conditional outcomes rather than completed milestone
tables or release chronology. Existing strategy/history own implemented behavior
and history. Remove the backlog completed-reconciliation table; group BL-010 packs,
BL-012/021/025 integrations and BL-020/016/018 configuration/profiles. Preserve IDs,
dependencies, triggers, next safe actions and exit criteria. Keep unique historical
qualification limits at their canonical owner; retarget documentation assertions.

### Verification

- Begin each subsystem with a compact grammar/behavior/failure matrix and inverse
  controls before broad corpus/model work. Tests enter real production owners.
- .NET: project/folder isolation, namespaces, attributes/children, conditions,
  conflicts/overrides/imports, multi-targeting, malformed JSON/XML, entity attacks,
  construction bounds, central-version changes, coverage/deltas and stdio MCP.
- Evidence: 255/256/257/260/413/513/1000 files; add/delete/rename/long paths/T/gitlinks;
  persistence/readback, pagination, clipped bootstrap, exact deltas, record/byte/
  entry hard limits and fresh/stale/hostile pre-execution diagnostics.
- DLP: all issue comments, single-dot policy, inverse sensitive controls, Unicode
  spaces/digits, encodings/Markdown/Mermaid, span boundaries, 63/64/65 chars and
  malformed near matches. Hypothesis 100 examples/property in CI, 1000 extended
  local; vary composition/structure and retain minimized synthetic regressions.
- Pair baseline/candidate on identical previously authorized public/private
  inputs, including available .NET input; classify every new admission, rejection
  and reason change, then repeat after fixes/review. Keep all private details
  private. Investigate repeated time/RSS regression above 15% with hot-path evidence.
- New .NET/budget owners and changed DLP modules require >=90% branch-aware
  coverage; retain existing floors/high results and measure the overall 88% gate.
- Verify local/GitLab paths, hostile persistence, actual source/MCP/HTTP/process
  boundaries and clean wheel/sdist installs outside checkout on Python 3.12–3.15.
- Local CLI matrix covers unified debug on/off, removed-flag rejection, API/native
  auth, success/filter/failure, invalid/overlapping/private paths and cleanup.
  Capture needed evidence/context/action data and closed early-budget facts before
  cleanup; retain no native HOME or credential-store copy and grant no diagnostic
  publication authority. Nonlocal debug remains rejected. Enter through the
  installed CLI with controlled OCR rather than mocks of retention.
- Aggregate semantic review, exactly one Security diff scan, then actual own-tool
  acceptance with budget 0/private debug/admitted diagram. Inspect findings,
  omissions, warnings and auxiliary reads; fix and run affected regressions.
- Full quality once on final runtime head, plus staged/tree/history secrets,
  dependency audit, instruction/plan lifecycle and final release-document guards.
- External receipt readback verifies exact authorized identities, artifact hashes,
  registry provenance, attestations, supported-Python installs, annotated tag,
  immutable Release and bot-owned issue/milestone closure; then site/main/cleanup.

### Latest Validation Results

Planning baseline: both verified Darwin candidates passed the existing 20 groups.
Hosted baseline workflow 43719258074 succeeded on 80eebd6 for both candidates,
creating canonical #318/#319; both comment inventories are empty.

WQ-02 passed 325 scoped collector/status/docs/workflow/property checks and a
319-test runner/status slice. Self-review corrected target-kind headroom and late
invocation-reserve interactions, adding their regressions. Latest affected rerun:
86 passed (7 unchanged large-snapshot cases deselected), with 100% branch-aware
coverage for all three new sizing/serialization/target owners. Ruff, formatter,
mypy (183 sources), instruction and plan contracts pass. Aggregate quality,
Security, own-tool acceptance and publication remain pending.

Dependency inventory: 11 compatible lock upgrades and uv 0.13.8 applied. All 11
Action versions and immutable tag targets already match latest stable releases,
including dereferenced annotated tags. CodeQL Action is v4.39.3; its separate
bundle release is not an Action version. Exact Bandit/setuptools-scm pins and
Gitleaks 8.30.1 are already current. The locked environment/export, 185 focused
dependency/workflow/HTTPS/federation/markup/property checks and shared dependency
audit pass. Supported-platform binary/installed acceptance remains at WQ-07/CI.
The reviewed dependency/upstream composition is now frozen for this cycle.

WQ-03 scoped collector/framework/infrastructure/MCP/document checks pass. All
new .NET parser/linker/provider and container grammar owners exceed their 90%
branch-aware floors (latest measurement: 99% or 100% each). Real Git collection,
source-local deltas, central version changes, persistence/readback and a real
stdio MCP child are exercised. Semantic review strengthened unsupported XML
placement/namespaces, malformed-signal isolation, source-scoped identities and
runtime-dependent ASP.NET resolution coverage. Source adapters have an executable
no-I/O/no-higher-lifecycle guard; no language-specific confidentiality exemption
or new public configuration was introduced. Aggregate acceptance remains pending.

WQ-04: 1510 scoped DLP/audit/property checks passed; the measured numeric owner
was 98% and calendar owner 100% branch-aware. Subsequent punctuation refinements
passed 227 affected checks and focused production admission/projection replay.
Eight structural numeric properties passed the 1000-example local profile.
Initial authenticated pairs cover the public corpus and all authorized private
inputs, including .NET. Every changed admission was bound to original bytes and
classified individually as benign numeric syntax. Newly introduced timestamp
punctuation blocks were reproduced synthetically and resolved through the actual
proof/admission/publication path. The final repeated pairs, resource comparison
and current-checkout scan remain mandatory at WQ-07; private details stay private.
Dateparser was qualified as a supplement, not selected for runtime admission:
strict parsing can reinterpret invalid dates or truncate excess time precision,
and adds measured startup/resources without demonstrated benefit for this slice.
The shared lexical boundary and stdlib calendar validation remain authoritative.

Docstring review found no removed pre-existing descriptions, but uncovered missing
descriptions for new runtime and test definitions. They were added and executable
AST equality verified; the existing development self-review requirement now
explicitly includes constructors, callbacks and observable test intent.

WQ-05: both official Linux amd64 candidates passed the expanded live suite
(20 executable probes plus CLI and optional-capability inventories)
in isolated Linux containers; both Darwin assets passed the same current suite.
Actual Darwin consumer suites passed 44 checks per candidate; the seven
Linux-only native TLS cases remain assigned to the final installed/native gate.
The federation control separately passed with each candidate. Its redundant
digest environment gate was removed because the shared fixture already checks
the exact official asset and reported identity. Current readback/native/negative
contract tests passed, with affected corrections checked separately. Semantic
review additionally strengthened the existing incomplete grace control: request
a registered but unadvertised read, requiring no extra executed read and no task
completion. This passed installed 1.13.10; repeat it on Linux at WQ-07.
Upstream latest is v1.13.10. The local executable now matches its official Darwin
SHA-256; the former installed executable and temporary candidate copies were
removed. Historical evidence through 1.13.8 is frozen without rewriting bytes.

### Risks And Recovery

Dateparser 1.5.0 was qualified as a possible supplement on a synthetic 34-value
matrix, including strict order and custom-only profiles. It recognizes additional
numeric dates but strict parse success can reinterpret invalid ISO-like input or
accept excessive timestamp precision. No automatic admission fallback or runtime
dependency is selected from that result. Retain the shared calendar grammar and
stdlib validation, preserve synthetic research probes, and include remaining
calendar causes in the required corpus analysis before selecting broader support.

- Numeric ambiguity is an explicit owner-approved policy; other contact/material
  checks remain independent. A lost expected-protection case blocks acceptance.
- Missing old private keys/snapshots do not justify fabricated comparisons. Capture
  a fresh authenticated baseline and candidate on identical authorized bytes.
- Unknown MSBuild semantics stay declared/partial rather than guessed. Resource
  exhaustion never proves absence or an effective dependency version.
- Structural growth must not starve late invocation or optional-T boundaries.
  A true hard stop remains visible and cannot become a clean review.
- Upstream composition is fixed at 1.13.10 for this cycle; later releases require
  separate scope. Failed qualification blocks promotion, not silent fallback.
- Reuse current proof for unchanged inputs, inspect failures before retrying, and
  preserve actual process completion/exit status. Do not restart live CI jobs.
- Never mutate published tags/distributions/receipt bytes for recovery. Use the
  protected release recovery lifecycle and preserve originals/audit keys.

### Resume Point

WQ-06: operator guidance and unified debug lifecycle. The OCR promotion is
implemented; retain hosted reconciliation, Linux TLS and the strengthened grace
control in the final native gate. The numeric slice has
passed scoped checks, initial paired audits and focused correction replay; retain
its final full repeat/resource comparison at WQ-07 after runtime work is complete.
WQ-02 is committed as a031c1c, dependencies as e37bf90 and .NET as 2f4ee21;
purpose-focused descriptions are committed as a7004e2.
Draft PR #317 remains at its signed plan commit; all development
stays local until final feature acceptance.

### Plan Fidelity Check

- [x] Every requested outcome, all six issues and three #314 comments are mapped.
- [x] Approved decimal ambiguity, no-new-configuration and privacy limits retained.
- [x] Product contracts, bounds, module ownership and compatibility are explicit.
- [x] OCR/assets/hosted/local update and related BL-010 activation retained.
- [x] Roadmap/backlog cleanup preserves unique constraints and inactive work.
- [x] Acceptance, corpus/resource checks, one Security scan and diagram retained.
- [x] Ordered queue, risks/recovery, exact resume point and full delivery retained.
- [x] No incompatible non-goal, internal chat reference or private corpus detail.

### Reconciliation Check

- [x] Baseline main/remote and current plan state checked before materialization.
- [x] Sources and issue comments reconcile with the approved implementation plan.
- [x] Full 2026-11-15 recheck retained all approved outcomes, bounds and lifecycle;
  the separately identified REQ-019 records the subsequent local CLI request.
- [ ] Final runtime, tests, public contracts, planning and evidence owners agree.
- [ ] Review findings and omissions are fixed or explicitly justified.
- [ ] Release handoff and remaining external delivery are classified truthfully.

### Closure Gate

- [ ] All in-scope implementation, documentation and validation complete.
- [ ] Full final self-review, Security and actual own-tool acceptance complete.
- [ ] Feature protected CI/merge and development publication independently checked.
- [ ] Release markers/authorization/notes/pins and focused release guards pass.
- [ ] Lifecycle archive/reset and all indexes agree in the release PR.
- [ ] Post-close delivery preserves required external verification and cleanup.

### Post-Close Delivery

Stable publication and independent readback are required parts of the overall
delivery objective. At the release PR, classify WQ-10 as required external work
outside the closed repository plan; archive the complete prepublication state
through the installed lifecycle CLI and return PLANS.md to template state.
Do not claim publication before the immutable receipt exists or create a closure
PR afterward. Close the goal only after WQ-10's actual external outcome is verified.

### Handoff Notes

The root owns plan/status/final synthesis. Reuse applicable completed evidence;
read the full active plan and current repository state after material context loss.
Keep private temporary locations and source-bearing recovery data out of tracked
content. No successful check is inferred from a running command or intermediate JSON.

## Recently Completed

- [x] 2026-11-12: Completed Toolkit 0.14.8 — OCR 1.13.8, provider HTTP and first integration; [full archived plan](docs/engineering/execution_history/plans/2026-11-12-toolkit-0-14-8-ocr-1-13-8-provider-http-and-first-integration.md).
- [x] 2026-11-10: Completed Toolkit 0.14.7 — OCR 1.13.7, recoverable diagrams and private diagnostics; [full archived plan](docs/engineering/execution_history/plans/2026-11-10-toolkit-0-14-7-ocr-1-13-7-recoverable-diagrams-and-private-diagnostics.md).
- [x] 2026-11-06: Completed Internal engineering cycle corrections; [full archived plan](docs/engineering/execution_history/plans/2026-11-06-internal-engineering-cycle-corrections.md).
- [x] 2026-11-06: Completed Toolkit 0.14.6 — OCR 1.13.6, DLP precision and efficient delivery; [full archived plan](docs/engineering/execution_history/plans/2026-11-06-toolkit-0-14-6-ocr-1-13-6-dlp-precision-and-efficient-delivery.md).
- [x] 2026-11-04: Completed Toolkit 0.14.5 — DLP precision, OCR qualification and maintenance quality; [full archived plan](docs/engineering/execution_history/plans/2026-11-04-toolkit-0-14-5-dlp-precision-ocr-qualification-and-maintenance-quality.md).
- [x] 2026-10-31: Completed Toolkit 0.14.4 systematic DLP corrections and diagram source validation; [full archived plan](docs/engineering/execution_history/plans/2026-10-31-toolkit-0-14-4-systematic-dlp-corrections-and-diagram-source-validation.md).
- [x] 2026-10-30: Completed Toolkit 0.14.3 source-aware DLP and private corpus audits; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-3-source-aware-dlp-and-private-corpus-audits.md).
- [x] 2026-10-30: Completed Toolkit 0.14.2 compact bootstrap, diagram-only reports and DLP corrections; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-2-compact-bootstrap-diagram-only-reports-and-dlp-corrections.md).
- [x] 2026-10-29: Completed Toolkit 0.14.1 grouped diagrams and private debug qualification; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-1-grouped-diagrams-and-private-debug-qualification.md).
- [x] 2026-10-29: Completed Toolkit 0.14.0 range identity, typed diagrams, DLP qualification and Python 3.15; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-0-range-identity-typed-diagrams-dlp-qualification-and-python-3-15.md).
