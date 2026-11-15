# Execution Plans

## Active Plan: Toolkit 0.15.0 — complete evidence, .NET and numeric DLP

plan_schema_version: 2
Status: done
Release classification: release-required
Target release: 0.15.0
Next development marker: 0.16.0
Last Updated: 2026-11-16

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
| REQ-008 | Structural Hypothesis, paired private audits, resource comparison and repeat | WQ-04, WQ-07 | done |
| REQ-009 | Exact OCR assets, excluded coverage and request-scoped tools qualification | WQ-05 | done |
| REQ-010 | Hosted qualification, promotion, local binary update and weekly schedule | WQ-05, WQ-10 | done |
| REQ-011 | #311 actual concurrency control and #316 opt-in skip example | WQ-06 | done |
| REQ-012 | Remove completed planning history; regroup inactive work and preserve unique limits | WQ-06 | done |
| REQ-013 | Focused/installed/integration tests and measured coverage floors | WQ-02, WQ-03, WQ-04, WQ-05, WQ-06, WQ-07 | done |
| REQ-014 | Aggregate self-review, one Security scan, real own-tool review and admitted PR diagram | WQ-07 | done |
| REQ-015 | Final quality, protected feature merge and development TestPyPI verification | WQ-07, WQ-08 | done |
| REQ-016 | Signed release candidate metadata, notes, pins and checked plan archive/reset; protected delivery below | WQ-09 | done |
| REQ-017 | Independent registry/install/provenance/tag/receipt/issues/site/main verification | WQ-10 | out_of_scope |
| REQ-018 | Owned source snapshots, builds, environments, debug and obsolete binaries removed | WQ-10 | out_of_scope |
| REQ-019 | Local CLI debug/retention combinations preserve useful authorized diagnostics without forge authority | WQ-06, WQ-07 | done |
| REQ-020 | Improve the actual model/tool/release cycle and canonical instructions where evidence warrants | WQ-06, WQ-07 | done |
| REQ-021 | Update compatible stable libraries, uv and immutable GitHub Action pins before expensive acceptance | WQ-11, WQ-07 | done |

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
| WQ-04 | Numeric span/date corrections and authenticated paired audits/resource comparison accepted | REQ-007, REQ-008, REQ-013 | done |
| WQ-05 | New OCR contracts, exact Linux assets, hosted chain qualification and promotion; logical commit | REQ-009, REQ-010, REQ-013 | done |
| WQ-06 | Shared local diagnostics, actual concurrency guidance, opt-in label, future-only roadmap/backlog and canonical documentation accepted locally | REQ-011, REQ-012, REQ-013, REQ-019, REQ-020 | done |
| WQ-07 | Repeated corpus comparison, aggregate review, one Security scan, own-tool findings/diagram, final quality and installed gates | REQ-008, REQ-013, REQ-014, REQ-015, REQ-019, REQ-020, REQ-021 | done |
| WQ-08 | Final feature push with exact diagram, protected CI/merge and development TestPyPI verification | REQ-015 | done |
| WQ-09 | Complete release/v0.15.0 candidate, markers/authorization/notes/pins, checked archive/reset and active roadmap/BL-010 closure; protected delivery below | REQ-016 | done |
| WQ-10 | Required post-close stable CI/merge, external receipt/site/main verification and task-owned cleanup; local OCR already updated | REQ-017, REQ-018 | out_of_scope |

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

Final acceptance as of 2026-11-16: runtime 99079bf passed the full quality gate
(5733 tests, 357 subtests, 90.57% branch-aware coverage). All required feature
checks and both current-contract hosted OCR qualifications passed; feature #317
and development TestPyPI readback are verified. Detailed checkpoints below retain
their original scope; later final evidence supersedes their intermediate status.

Planning baseline: both verified Darwin candidates passed the existing 20 groups.
Hosted baseline workflow 43719258074 succeeded on 80eebd6 for both candidates,
creating canonical #318/#319; both comment inventories are empty.

WQ-02 passed 325 scoped collector/status/docs/workflow/property checks and a
319-test runner/status slice. Self-review corrected target-kind headroom and late
invocation-reserve interactions, adding their regressions. Latest affected rerun:
86 passed (7 unchanged large-snapshot cases deselected), with 100% branch-aware
coverage for all three new sizing/serialization/target owners. Ruff, formatter,
mypy (183 sources), instruction and plan contracts pass. Final aggregate and delivery evidence is recorded below.

Dependency inventory: 11 compatible lock upgrades and uv 0.13.8 applied. All 11
Action versions and immutable tag targets already match latest stable releases,
including dereferenced annotated tags. CodeQL Action is v4.39.3; its separate
bundle release is not an Action version. Exact Bandit/setuptools-scm pins and
Gitleaks 8.30.1 are already current. The locked environment/export, 185 focused
dependency/workflow/HTTPS/federation/markup/property checks and shared dependency
audit pass. Final supported-platform binary/installed acceptance is recorded below.
The reviewed dependency/upstream composition is now frozen for this cycle.

WQ-03 scoped collector/framework/infrastructure/MCP/document checks pass. All
new .NET parser/linker/provider and container grammar owners exceed their 90%
branch-aware floors (latest measurement: 99% or 100% each). Real Git collection,
source-local deltas, central version changes, persistence/readback and a real
stdio MCP child are exercised. Semantic review strengthened unsupported XML
placement/namespaces, malformed-signal isolation, source-scoped identities and
runtime-dependent ASP.NET resolution coverage. Source adapters have an executable
no-I/O/no-higher-lifecycle guard; no language-specific confidentiality exemption
or new public configuration was introduced. Final aggregate acceptance is recorded below.

WQ-04: 1510 scoped DLP/audit/property checks passed; the measured numeric owner
was 98% and calendar owner 100% branch-aware. Subsequent punctuation refinements
passed 227 affected checks and focused production admission/projection replay.
Eight structural numeric properties passed the 1000-example local profile.
Initial authenticated pairs cover the public corpus and all authorized private
inputs, including .NET. Every changed admission was bound to original bytes and
classified individually as benign numeric syntax. Newly introduced timestamp
punctuation blocks were reproduced synthetically and resolved through the actual
proof/admission/publication path. The final repeated pairs, resource comparison
and current-checkout scan are accepted below; private details stay private.
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
Linux-only native TLS cases passed in the later installed/native gate.
The federation control separately passed with each candidate. Its redundant
digest environment gate was removed because the shared fixture already checks
the exact official asset and reported identity. Current readback/native/negative
contract tests passed, with affected corrections checked separately. Semantic
review additionally strengthened the existing incomplete grace control: request
a registered but unadvertised read, requiring no extra executed read and no task
completion. This passed installed 1.13.10; its later Linux repetition passed.
Upstream latest is v1.13.10. The local executable now matches its official Darwin
SHA-256; the former installed executable and temporary candidate copies were
removed. Historical evidence through 1.13.8 is frozen without rewriting bytes.

WQ-06 unified diagnostics implementation: the separate retention interface,
native-HOME preservation and duplicate DLP sidecar producer are removed. Local
debug captures bounded repository/context/Rules/action inputs before unconditional
cleanup; successful results always take ordinary finalization. Unsafe or failed
atomic finalization discards its unadmitted handoff, while hostile old private
markers remain rejected. The scoped runner/CLI/debug/rejection suite passed 280
checks, and three additional closed budget-fact cases passed after correcting the
synthetic authentication fixture. The controlled real-CLI matrix passed normal,
debug, progress, filtered/failure/forged-output and both diagram paths against the
working-tree entrypoint. ChatGPT auth checks passed 53 cases, including debug
cleanup without copying native auth/configuration. Debug coverage is 94% with
branches across 360 scoped checks. Clean installed-artifact and operator/planning acceptance followed
in the later checkpoints below.

WQ-06 operator/planning slice: current provider guidance uses native concurrency;
the historical changelog is unchanged. The label recipe is opt-in, precedes the
ordinary MR rule, leaves manual readiness and the distributed default intact, and
documents pipeline timing and merge/approval implications. Nine token-boundary
controls pass. Scoped posting/docs/release-note checks preserve earlier behavior.
Completed roadmap/backlog history is removed; all seven inactive IDs, unique
dependencies, activation constraints and acceptance gates remain. New next actions
and BL-010's active slice point to their owners. The absent historical enriched
model qualification remains explicit at the strategy owner. The release candidate removes the active roadmap rows and BL-010
promotion pointer when archiving this plan. No closure PR is needed. Instruction review retained the existing execution
rules and strengthened the concrete docstring check; no duplicate instruction or
new orchestration framework was added.

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

### Current Acceptance Evidence

Implementation commits through 5e46d49 completed WQ-02/03/04/06/11.
Independent aggregate review corrections are committed as 731d932.
The single Security scan covered 80eebd6..731d932 and reported one medium
pre-store XML allocation issue. Commit 9b2d316 addresses constructed identities,
.NET output payloads and the namespace-tree bypass found in its one independent
patch-review cycle. Its focused acceptance passed 136 tests with 99.38% .NET
branch-aware coverage. This does not replace the final runtime quality gate.

Initial Linux TLS, exclusion and restricted-grace controls passed nine cases
for each OCR candidate. Current own-tool findings strengthen fixture membership
and fresh-round proof further; those changed probes subsequently passed both platforms and hosted qualification.
The first real own-tool run reviewed 80eebd6..9b2d316: 90 selected/completed files,
seven findings, generated diagram and no DLP omissions. Its raw material remains
private. All seven findings are confirmed and corrected: fixture membership,
fresh-round evidence, SDK comments, central-transitive lock scopes, scoped central
conflicts, resume state and standalone debug-result wording. Focused acceptance
passed 177 tests (three opt-in cases separately passed on the installed native
binary), and independent review passed 47 narrow checks without residual defects.
The failed guessed example path was followed by a complete successful read of
the actual 120-line file. Bootstrap is retained whole; the length recommendation
is advisory, with no token/tool/context exhaustion. The optional debug trace hit
its explicit cap; raw findings and stderr remain complete. No additional
aggregate Security scan is required.

The second own-tool run reviewed 80eebd6..3f2e174: all 90 selected files,
two findings, an admitted diagram and no DLP omissions. Its corrections bound
optional records and composed deltas after the mandatory envelope, and recognize
closed contact-label bindings without evaluating source-language expressions.
Independent patch review added computed-key/call/window counterexamples and
structural partial coverage that survives redacted diagnostics, including plugin
domains distinct from record kinds. Retained-fact controls verify semantic plugin
scopes through MCP. The 20 new optional-byte regressions pass; the earlier focused
handoff suite passed 725 checks. Final quality acceptance is recorded below.

Canonical pre-commit instructions now require observable witnesses and distinct
counterexamples for security, identity, completeness and resource claims. Missing
proof blocks the commit. Format-owner variants, competing sources, composed
budgets, affected-mode documentation and an exact remaining-work resume point
are mandatory checklist dimensions; the OCR route includes the selection guard.

The first full gate was interrupted after ten stale test-contract failures
(3550 passed). Removed retention APIs, promoted native versions, package ownership
and canonical omission assertions are now reconciled; their focused suite passes
188 tests with ten opt-in cases skipped; native qualification remains separate. No runtime change
was needed for those corrections. Clean ca7dd78 wheel/sdist construction,
installed runtime/MCP on Python 3.12, 3.14 and 3.15, and the complete installed
local CLI debug/progress/diagram matrix pass. The third actual own-tool run then
reviewed the immutable 80eebd6..ca7dd78 production range.

The third own-tool run completed that range: all 96 selected files completed,
ten raw findings, nine admitted findings, one finding and the candidate diagram
omitted by DLP. No native group failed, reused or was waived. The omitted finding
exposed a genuine comparison-context false positive; its raw content admits after
the correction. The diagram's abbreviated version token remains conservatively
blocked; retain the earlier actually admitted diagram for the PR rather than
weakening DLP. Auxiliary failed reads were assessed through the successful recovery reads below.
All ten findings are confirmed and corrected in 99079bf: four documentation claims,
no-notice optional capacity, inline SDK versions, case-shadowed discovery, verified
suggestion coverage, comparison priority and pre-callback namespace amplification.
The XML finding was independently reproduced before correction; its raw-attribute
prepass and the other fixes passed one fresh independent patch-review cycle with
no outstanding findings. The focused suite passed 414 tests with 97.60% combined
branch-aware coverage; each affected measured module is at least 96%. Two further
raw-prepass depth/element regressions passed with the 95-test XML/SDK suite. The
raw prepass preserves those original early ceilings and attribute/entity limits.
Captured trace records prove successful reads of the actual GitLab example,
complete collector orchestration, DLP admission segments and the full coverage
owner after guessed paths failed. No material auxiliary-read gap remains. The
optional trace capture reached its explicit cap; raw result and stderr are complete.
The extended numeric profile passed eleven properties at 1000 examples. The
quality-owner route now runs the focused wrapper inventory test before the full
gate; shared-interface edits require current runtime/test reference review.

The second full quality run reached 5656 passing tests, 74 skips and 357 passing
subtests at 90.56% overall branch-aware coverage. Its sole failure was a stale
coverage-loop inventory assertion; the focused script test is corrected. This
run does not establish final runtime acceptance after the third-review fixes.

Final local acceptance is complete on signed runtime commit 99079bf. The full
quality gate passed 5733 tests, 74 skips and 357 subtests at 90.57% branch-aware
coverage; every additional boundary floor passed. Its wheel was built from the
sdist and installed through the hash-locked binary-runtime recipe. Independent
installed MCP checks and the full installed local CLI matrix passed. Dependency
audit passed with no known third-party vulnerabilities.
Authenticated baseline/candidate comparisons are complete for all authorized
corpora, with every new admission and primary-reason change reviewed and annotated.
There are no new blocks, unexplained admissions, unreviewed changes or losses of
annotated protection. The immutable current-checkout scan is complete. Resource
checks passed after repeating the one RSS outlier under isolated comparable
conditions; the repeat stayed within the agreed thresholds. Private details and
source-bound annotations remain outside the repository. The earlier admitted
diagram was compared with final change semantics and retained verbatim for the PR.

Hosted and feature delivery on 2026-11-16: current-contract exact-tag runs
43772316403 (OCR 1.13.9) and 43772318071 (OCR 1.13.10) passed on e3ae5ab.
All required feature checks passed, including installed wheel/sdist acceptance;
the automatic provider review completed without findings. PR #317 merged as
42f2c3e3c3a031ebb16fb49b6bbe9445084516d6. Development TestPyPI run
43773136303 passed all build, publication and installed/provenance readback jobs
for that exact merge. The local qualified OCR 1.13.10 is already installed.

### Resume Point

No unfinished repository implementation remains. The complete release candidate
owns markers, authorization, changelog, pins and checked archive/reset. Required
protected publication, external readback and cleanup are classified in Post-Close
Delivery; the overall delivery goal remains active until they are verified.

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
- [x] Final runtime, tests, public contracts, planning and evidence owners agree.
- [x] Review findings and omissions are fixed or explicitly justified.
- [x] Release handoff and remaining external delivery are classified truthfully.

### Closure Gate

- [x] All repository implementation, documentation and runtime acceptance complete.
- [x] Aggregate self-review, one Security scan and actual own-tool findings/diagram acceptance complete.
- [x] Protected feature CI/merge and development TestPyPI publication verified.
- [x] Release candidate owns metadata, notes, pins and focused release-contract inputs.
- [x] Checked lifecycle archive/reset and current roadmap/backlog/index reconciliation belong to this release candidate.
- [x] Required external delivery and cleanup remain explicit below, without a closure PR.

### Post-Close Delivery

Required delivery outside the closed repository plan: validate and commit the
complete signed Release v0.15.0 candidate, push its exact-title protected PR,
complete required CI and squash merge. Then independently verify stable
TestPyPI/PyPI, Python 3.12–3.15 installs, provenance, attestations, annotated tag,
immutable Release and receipt, CI-owned #311–#316/#318/#319 closure, milestone,
site and clean synchronized main. Remove task-owned raw source snapshots,
temporary binaries/environments, build/debug artifacts and obsolete Actions data;
preserve audit keys and necessary source-free evidence. The local qualified OCR
1.13.10 is already installed. REQ-017/018 and WQ-10 are outside the closed
repository plan only because the release guide requires this prepublication
handoff; they remain mandatory for the active overall goal. This archive is a
prepublication snapshot and makes no claim that stable artifacts already exist.
No separate closure PR, fourth OCR review, repeat aggregate Security scan or
landing-chat handoff is required for this unchanged runtime.

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
