# Execution Plans

## Active Plan: Toolkit 0.14.6 — OCR 1.13.6, DLP precision and efficient delivery

plan_schema_version: 2
Status: done
Release classification: release-required
Target release: 0.14.6
Next development marker: 0.15.0
Last Updated: 2026-11-06

### Goal

Deliver and independently reconcile toolkit 0.14.6 with qualified OCR 1.13.6,
the approved compatible dependency refresh, evidence-backed DLP corrections,
complete disposition of the remaining public audit population, stronger tests
and a more efficient engineering/release cycle. Implementation readiness is not
stable delivery. The persistent objective remains active through external
publication, issue/PR reconciliation and task-owned cleanup.

### Plan Origin

plan_mode_approved

Owner-approved release plan of 2026-11-05, including the explicit choice to
support safe markup and the subsequent execution request.

### Requested Scope

Qualify OCR 1.13.6, including C# built-in Rules, Starlark selection/Rules and
explicit false streaming controls. Incorporate Dependabot #296 and refresh
compatible stable direct/transitive dependencies, uv and CodeQL pins before
expensive acceptance. Correct demonstrated DLP false positives without reducing
contact, credential, configured-secret or forbidden-source protection.

At plan entry the authenticated public audit had 1611 individually unannotated role
observations at 1203 positions, including whole-file probes. Detector/role
grouping and immutable-source verification were completed during planning;
grouping is not an individual benign/sensitive verdict. Five largest merged
groups contain 1495 observations (92.8%):

| Group | Observations | Planned disposition |
| --- | ---: | --- |
| Normalized credential-like material | 524 | Distinguish protective fixtures, ambiguous references/declarations and reproduced absent-value/boundary defects. Do not waive calls, permission values or nonempty literals by name. |
| Normalized email | 405 | Retain real address forms, including fictional domains; fix parser-position handling of repeated code spans and mention commands. |
| Markdown destinations | 255 | Admit safe ordinary links after complete material and destination validation. |
| HTML-like tokens | 218 | Preserve technical generics, regex groups and placeholders through safe rendering rather than blanket markup rejection. |
| HTML comments | 93 | Inspect all hidden content and render it visibly and safely rather than executing or silently removing it. |

Individually classify these groups and the remaining 116 observations through
the existing exact annotation contract. Complete fresh paired public and
previously authorized private replays and scan the current candidate checkout.
Keep private inputs, locators, statistics and results out of public artifacts.
Reconcile canonical instructions, architecture, public contracts, diagrams,
evidence matrix, causal matrix and backlog where behavior or recorded state changes.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Qualified OCR 1.13.6, C# Rules and existing project-context reads | WQ-03, WQ-06 | done |
| REQ-002 | Starlark, streaming controls and existing consumed handoffs qualified | WQ-03, WQ-06 | done |
| REQ-003 | Dependabot #296 and frozen compatible dependency/tool refresh | WQ-02, WQ-07 | done |
| REQ-004 | Safe bounded markup publication across real consumers/readback | WQ-04, WQ-06 | done |
| REQ-005 | Exact code-span email correction and credential/protection review | WQ-04, WQ-05 | done |
| REQ-006 | Individual disposition of all 1611 public observations and final paired replays | WQ-05, WQ-06 | done |
| REQ-007 | Expanded inverse/property tests, meaningful coverage and resource evidence | WQ-04, WQ-05, WQ-06 | done |
| REQ-008 | Efficient agent cycle and synchronized canonical documentation | WQ-01, WQ-06 | done |
| REQ-009 | Signed reviewed delivery, one Security scan and admitted own-tool diagram | WQ-01, WQ-06, WQ-07 | done |
| REQ-010 | Stable metadata/notes/examples and repository handoff prepared; publication, independent external reconciliation and final cleanup required under Post-Close Delivery | WQ-08 | out_of_scope |

### Explicit Non-Goals

No second Markdown engine, model/classifier-based DLP, inferred source execution,
MSBuild invocation, new .NET collector framework, repository/domain/fixture
allowlists, production annotation suppressions, extra user settings/CLI flags,
new forge adapter, CI corpus audit or general orchestration framework. Do not
rewrite historical evidence, receipts, published distributions or tags. Do not
send a landing-page chat handoff or create a post-release repository closure PR.

### Constraints

- This full plan is the first repository write. Preserve its scope at recovery;
  use stable requirement/queue IDs and the checked lifecycle at release closure.
- Create a `codex/` feature branch; the first signed push opens a draft PR with
  the plan. Keep subsequent development local until acceptance. Review each
  logical commit, apply formatting and staged secret checks, and sign commits.
  Unpublished corrections may amend; do not rewrite published history.
- Freeze dependencies before expensive acceptance. A newly published version
  after that freeze does not automatically expand this release.
- Preserve Python 3.12–3.15, binary-only hash-locked runtime installation and
  security floors. Exact-version optional capabilities need actual evidence.
- Reporting remains pure. Git I/O, MCP, environment, DLP orchestration and
  provider writes retain their existing owners; no duplicate range resolver.
- DLP examines original, hidden, decoded and projected material independently.
  Source identity does not authorize arbitrary syntax or disclose secrets.
- Exact annotations never change production admission. Every conservative
  verdict needs a concrete ambiguity and missing proof; it cannot hide a defect.
- Private sources, paths, counts/results, keys, raw debug and internal
  conversation identifiers never enter public plans, issues, PRs or packages.
- Use ordinary native CLI execution, existing helpers and bounded output.
  Do not create launch wrappers, per-command receipts or duplicate transcripts.
- One aggregate Security diff scan before own-tool acceptance. Ordinary fixes
  and documentation changes do not trigger another aggregate scan.
- Normal own-tool acceptance uses one real ChatGPT high run, unlimited aggregate
  token budget, private debug and an actual admitted diagram. A second run is
  reserved for incomplete acceptance or a concrete new coverage gap; document
  that reason first. Product diagram omission remains nonfatal.
- Full quality runs once on the final runtime handoff head. Rerun an affected
  check only for changed inputs, a failure or an unresolved concrete concern.

### Inputs And Sources

- Plan-entry clean main `881fd1d9ba3e4c25682e3b5321a9585f9ad78ac8`, published 0.14.5.
- Upstream release and adjacent diff: `alibaba/open-code-review` v1.13.5...v1.13.6.
- OCR 1.13.6 official Linux amd64 asset SHA-256
  `cb1330516431dea980c75497fa2bc46ad5fe5a4f3d35e947ab5af4a1742cae92`;
  Darwin arm64 `6d1e6bb73d1f14b2c03d7456c016c5b553b13d25931cf154605732304c6b367a`;
  checksum-list digest `58755741cf62e3d4046415c8ee8e14dff364fc43ecbd36254fb7792adb529fb1`.
- Dependabot PR #296 and reviewed PyPI compatible dry-run results.
- Public implementation issue #297 and canonical OCR qualification issue #298.
- Current authenticated public audit metadata, exact source population and
  annotations; previously authorized private populations remain private.
- Canonical owners: development/release/compatibility/security/DLP-audit guides,
  project principles, review-context/decision-flow contracts and causal matrix.
- Installed planning/instruction lifecycle references and read-only workflow
  audit. Heuristic findings require ownership/semantic triage, not blind changes.

### User Decisions And Answers

- Release the complete plan as 0.14.6 and include the outstanding Dependabot PR.
- Proactively update compatible stable libraries and dependencies.
- Safe markup selected: validate links and hidden material, render technical
  text/HTML safely, preserve independent sensitive-material checks.
- Classify the full remaining public population, deeply examine the top five
  groups before implementation, and fix confirmed defects in this release.
- Improve the agent/release cycle, speed and context cost while preserving
  quality. Prefer focused existing controls over more scaffolding.
- Retain private-input confidentiality, audit key and necessary source-free
  evidence; remove task-owned source copies/builds/debug after acceptance.
- Inspect the canonical rules against ad hoc repository/language fixes and add
  one real C# project to private paired audits. Use actual-project diagnosis
  rather than a separate speculative C# corpus; public regressions stay synthetic.

### Completed Baseline State

Planning inspection verified the upstream 1.13.6 changelog/source changes and
official asset metadata. `.cs` was already selectable; 1.13.6 adds its C# Rules.
Starlark adds `.bzl`, `.bazel`, `.star`, `BUILD` and `WORKSPACE`. Explicit false
streaming changed in API clients; upstream Action/site changes are not toolkit
execution paths. No new candidate binary qualification is claimed yet.

Current production DLP reproduces false rejections of safe links, generic types,
named regex groups, comments and Markdown mention commands/repeated code spans.
An actual email and a credential-bearing URL remain rejected in the controls.
All 1611 public observations were grouped with authenticated source verification;
individual verdict annotation remains implementation work, not a completed claim.

The compatible resolver found 33 updates. Current open PR #296 updates Hypothesis
6.170.13 to 6.170.14 and also changes lock-format revision; regenerate the reviewed
lock through the pinned resolver rather than copying the bot's stale whole file.
Used Actions are current except CodeQL v4.39.1 -> v4.39.3. CodeQL bundle tags are
not Action-version tags. uv advances 0.13.4 -> 0.13.7.

Workflow audit found no instruction-contract errors. Its archive orphan warning
points at an existing historical navigation index; inspect the declared custom
archive graph before deciding that any repair is needed. Lexical prompt warnings
are not validated security findings. Earlier acceptance counters do not carry
into this cycle. Its allowance is one aggregate Security scan and at most two
actual own-tool reviews; current consumption is recorded below.

### Current Work Queue

| Item | Requirements | Work and completion evidence | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-008, REQ-009 | Full plan/fidelity/state verified; signed plan 0287855 pushed; draft PR #299 and issues #297/#298 created | done |
| WQ-02 | REQ-003 | Exact 33-update lock and uv/verified CodeQL pins; 47 focused tests, formatter/lint/types and updated dependency audit pass; semantic diff review complete | done |
| WQ-03 | REQ-001, REQ-002 | Identical full Linux/Darwin 1.13.6 contracts, 116 distinct optional/path consumers, 295 focused tests/types, frozen readback and reviewed promotion verified; hosted final-tree check remains WQ-06 | done |
| WQ-04 | REQ-004, REQ-005, REQ-007 | Consolidated slice and separate second-review corrections signed locally; 304 focused checks including 1000-example properties, independent coverage floors and semantic review pass | done |
| WQ-05 | REQ-005, REQ-006, REQ-007 | Original public correspondence, all 1611 exact annotations, final matched production replay and resource investigation complete; authorized private evidence remains private | done |
| WQ-06 | REQ-001, REQ-002, REQ-004, REQ-006, REQ-007, REQ-008, REQ-009 | Final local/installed/native acceptance, all review fixes, hosted OCR 42159743276 and protected feature quality/build/security checks verified | done |
| WQ-07 | REQ-003, REQ-009 | Exact diagram delivered; protected PR #299 merged as 421dd368; development publication/readback 42162186254 passed; #296 closed as incorporated | done |
| WQ-08 | REQ-010 | Repository stable metadata/notes/examples and checked full archive/reset handoff prepared; signed PR/CI/merge, stable publication, external verification and final cleanup remain required Post-Close Delivery | out_of_scope |

### Locked Decisions

Keep the existing bounded Mistune parser and separate material interpretation,
safe projection and transport/rendering. Inspect original text, hidden HTML,
destinations/titles and decoded views before projection, then inspect the result.
Do not grant an exception merely because a parser accepts a string.

Preserve safe Markdown links. Published destinations allow HTTP/HTTPS, relative
links and anchors; reject dangerous schemes, userinfo, controls and malformed
destinations without network access. Images must not automatically fetch remote
content. Escape HTML and comments so their complete content is visible and inert;
preserve literal text inside valid code spans/fences. Projection is deterministic,
idempotent and bounded before/during expansion. Oversize fields are rejected,
never silently clipped. Safe formatting alone does not mean findings were filtered.

Code-span recognition uses exact parser-token positions, including repeated
identical spans and mention commands. A genuine email inside code remains PII.
Credential fixes require reproduced no-material/boundary proof, not an allowlist
of permission maps, callees, types, filenames, repositories or fictional domains.
Literal code retains its text and source-proof contract. Diagram labels use the
existing deterministic Mermaid encoder and independent DLP; optional failures do
not change findings, coverage, outcome or approval eligibility.

Reuse the same prepared clean model across production finalization, persisted
readback, local/GitLab presentation and audit replay. Reporting performs no I/O
or DLP orchestration. Preserve native-result and receipt shapes unless actual
structure changes justify explicit versioning; add no user configuration.

Freeze all 33 compatible updates found on 2026-11-05 before expensive reviews:
AnyIO 4.16.0, charset-normalizer 3.5.2, coverage 7.17.2, cryptography 50.0.2,
filelock 4.2.9, hatchling 1.33.0, Hypothesis 6.170.14, idna 3.20,
iniconfig 2.3.1, more-itertools 11.2.1, msgpack 1.2.4, mypy-extensions 1.2.0,
OpenTelemetry API 1.45.2, pip 26.3, platformdirs 4.14.5, pluggy 1.7.0,
pycparser 3.12, Pydantic 2.14.3/core 2.50.4, pyparsing 3.3.3,
pyproject-hooks 1.3.3, python-multipart 0.0.33, rpds-py 2026.9.1,
Ruff 0.17.4, SSE-Starlette 3.6.0, Starlette 1.10.0, tomli 2.5.0,
tomlkit 0.15.2, trove-classifiers 2026.9.21.13, truststore 0.10.5,
typing-inspection 0.4.5, uvicorn 0.54.0 and vcs-versioning 2.6.0.
Keep unrelated current packages and dependency constraints. Qualify uv 0.13.7
consistently in workflows/audit wrapper and SHA-pin CodeQL Action v4.39.3.

New live OCR probes target the current epoch; old 1.13.5 evidence is immutable
frozen readback, not a reason to add legacy execution branches. C# context reads
use existing bounded repository/native tools, not compiler execution. Verify
both platforms and optional capabilities before promotion. Preserve the weekly
schedule. The stable PR updates the published toolkit/OCR/checksum example pair.

The workflow correction is enforcement and sequencing, not new infrastructure:
inventory/freeze first, focused slice checks, aggregate review -> one Security
scan -> actual own-tool acceptance, focused corrections, then one final full
quality gate. Preserve evidence while its relevant inputs remain unchanged.
Use native watch commands for required CI; return only meaningful changes or
completion. Keep state in the existing plan and retain only necessary private
acceptance/recovery artifacts. Do not duplicate rules across canonical owners.

### Verification

- V-01: Check full plan fidelity, installed lifecycle, instruction ownership,
  exact dependency inventory and privacy before the signed initial delivery.
- V-02: Frozen lock integrity, updated formatter/linter/types, dependency audit,
  actual affected runtime/transport checks, clean hash-locked binary installs
  and supported-Python packaging. Do not count collection as executed tests.
- V-03: Official 1.13.6 asset identity, CLI/preview/result/manifest/range/partial,
  effective controls, C#/Starlark Rules, C# context reads and false-stream wire
  tests. Real controlled stdio/HTTP peers cover groups, federation, diagrams and
  gitlinks. Verify exact-tag hosted qualification with the final lock/pins.
- V-04: Red reproductions, minimized synthetic regressions and actual publication
  paths; malicious persisted values, local/GitLab parity, unsafe URL/image/HTML,
  Unicode, entities/encoding, repeated/nested delimiters, code spans/fences,
  malformed markup, near matches and chars/bytes/lines/parser-work boundaries.
- V-05: Inverse phone/email/credential/configured-secret/forbidden-material
  insertion in text, URLs, titles, comments, attributes and adjacent fields.
  Hypothesis uses 100 examples normally and 1000 with independent local seeds.
  Check idempotence and preserve semantic text, source proof and optionality.
- V-06: Exact verdicts for all 1611 original public observations, including the
  remaining 116; repeat complete identical baseline/candidate populations and
  current checkout. Explain every new admission/rejection/reason change and
  retain all expected protection. Labels never suppress runtime checks.
- V-07: Compare wall/CPU/RSS on matched environments; >15% wall/RSS worsening
  triggers repeat measurement and hot-path investigation before acceptance.
- V-08: Existing independent coverage floors, affected DLP/audit owners >=90%
  branch-aware; align pyproject overall threshold to existing gate 88%. Focused
  endpoint checks precede one final full quality gate; protected Linux 3.12–3.15
  and installed-artifact owners retain their required scope.
- V-09: Aggregate semantic self-review, one Security diff scan and threat-model
  reconciliation, one normal ChatGPT high review with budget 0/private debug/
  local diagram; inspect raw omissions, warnings and auxiliary reads. Fix all
  findings. A second model run needs an explicit incomplete/new-gap basis.
- V-10: Signed final feature push with exact accepted Mermaid, protected merge,
  development TestPyPI, signed stable PR, supported-Python registry installs,
  provenance/attestations/tag/immutable receipt and independent external closure.

### Latest Validation Results

Final acceptance evidence reviewed: 2026-11-06.

- Protected feature PR #299 is merged as 421dd368d0584ac79e9efe025c06a7ade26fbcb5.
  Reviewed head 7fbd184 passes all required checks, including corrected CodeQL,
  supported Linux Python jobs, dependency/security and installed Build artifacts.
  The exact admitted Mermaid is in its body. Development TestPyPI run
  42162186254 and independent published-development verification pass on that
  exact merge; #296 is closed and its Hypothesis update is incorporated.
- All 33 approved dependency updates are frozen and audited. Official Linux
  amd64 and Darwin arm64 OCR 1.13.6 contracts agree, including C# Rules/context,
  Starlark and explicit streaming controls. Local OCR is verified 1.13.6.
  Hosted exact-tag run 42159743276 passes on the unchanged runtime/qualification owners.
- All 1611 original public observations have exact authenticated annotations:
  583 confirmed benign, 891 expected protection and 137 conservative ambiguities
  with concrete missing proof. Original immutable correspondence is preserved.
  Final public replay and all 708 actual production handoffs pass: 26 new
  conservative boundaries have exact annotations; no untriaged, unexplained
  admission, changed reason or lost annotated protection remains.
- Authorized private validation includes an actual C# source population. All
  inputs, measurements and outcomes stay private; no source-language waiver is
  introduced. Their final replay, transition and resource-review evidence is retained privately.
- Aggregate self-review and the single Security diff scan are complete. Its
  composition, amplification and prepared-path findings are fixed; the threat
  model remains applicable. Security scans: **1/1 completed**, no repeat planned.
- Both GPT-6 Astra/high own-tool reviews completed all 83 selected files without
  budget warnings and produced admitted diagrams. All raw findings, including
  DLP omissions, were inspected. Four auxiliary read failures in the second run
  were followed by successful reads of the actual owners and complete email
  module. No material context gap remains. Model reviews: **2/2 completed**.
- Second-review corrections require complete closed-data proof for quoted
  absent credential carriers, reject decoded leading-whitespace URL authorities,
  bound complete prose slots before recursive DLP/sanitization, and strengthen
  the malformed-markup preservation oracle. Unknown calls/comparisons remain
  conservative across languages. The focused scope passes 304 checks, including
  the 1000-example property profile. Lint and types pass; branch-aware coverage
  is 96% for literal context, 98% for credentials and above 90% for projection.
- Current tracked checkout audit completed: 551 files, 138983 units, no acquisition
  errors or omissions. It is a distinct diagnostic population, not a precision
  measurement or a replacement for the individually reviewed original corpus.
- Repeated public measurement is 136.10 s versus 97.67 s for published 0.14.5;
  RSS is 185286656 versus 176832512 bytes. The >15% time threshold triggered
  repeat measurement and actual worker profiling. Credential interpretation,
  normalization and bounded Markdown work dominate sampled cost; additional
  complete-representation/presentation checks are retained. No speedup is claimed.
- Final quality gate passes: 4866 tests, 357 subtests, 89.95% branch-aware
  coverage against the 88% overall floor; all independent owner floors pass.
  Value boundaries measure 100%. The 49 optional native cases passed in the
  preceding full attempt on the same runtime; only stale test oracles changed.
  A separate current-source Python 3.15 run passes 598 affected checks. Earlier
  clean wheel/sdist installation and MCP/local/diagram smoke remain applicable;
  protected feature Build artifacts verifies the current package. Stable build
  and registry verification remain required Post-Close Delivery.
- The pre-push frozen dependency audit and complete public tree/history scans
  pass. Merged PR #299 includes the exact accepted diagram. Hosted run
  42159743276 passes the final-runtime OCR contract; its human disposition is
  recorded in #298. Requalification's self-comparison is not promotion authority.
- CodeQL alert #22 is statically not actionable: a fixed test fixture's URL
  substring assertion is neither shipped nor an authorization control. Reported
  merge-ref and local blobs agree. The test now checks full text preservation
  and exact parsed destination equality; 78 focused checks pass. No runtime,
  query suppression or scan policy changes. Corrected CodeQL and protected CI pass.
- Stable 0.14.6 metadata, next marker 0.15.0, source epoch, issue authorization
  for #297/#298, generated notes and the toolkit/OCR/checksum example pair are
  prepared. Stable distributions, tag, immutable receipt, CI-owned issue closure,
  site readback and final cleanup are required Post-Close Delivery, not completed
  facts. Security/model scans and full runtime checks are not repeated for
  release-only documentation and metadata preparation.

### Risks And Recovery

Markup can conceal protected values or execute at a sink. Do not remove data to
make admission succeed: preserve/check original and derived representations and
test the actual output. Token positions must survive repeats, nesting, encodings
and parser bounds. Limits or ambiguous source mapping fail closed. Idempotent
persisted readback must not re-escape technical code or accept hostile raw markup.

Dependency and upstream changes can invalidate earlier tests; freeze early and
repeat only affected checks. Candidate C# selection alone does not prove Rules
or project-context availability. Keep historical evidence immutable and refuse
unsupported capabilities rather than advertising them from a version label.

Lower hit counts and completed annotations are not detector precision/recall.
Keep conservative reasons explicit and do not inherit unverified historical
identities. Preserve the durable current audit key. Remove only task-owned source
copies, build/debug environments and policy-selected Actions data, never originals.

### Resume Point

No unfinished repository implementation or preparation remains. Required
external delivery is classified in Post-Close Delivery.

### Plan Fidelity Check

- [x] Approved release, DLP, dependency, OCR, workflow and cleanup scope retained.
- [x] Every requirement maps to queue items and concrete verification.
- [x] Safe-markup decision and protection/privacy boundaries are explicit.
- [x] Grouping versus individual classification and prior versus new evidence distinguished.
- [x] Native/capability/historical and producer-consumer boundaries covered.
- [x] Review counts, efficient sequence, delivery lifecycle and resume point retained.

### Reconciliation Check

- [x] Current main and prior stable release verified before this first write.
- [x] No preexisting implementation edits or competing active plan.
- [x] Public plan contains only public/synthetic evidence and no private locators.
- [x] Implemented scope, current evidence and source-owned status documents agree.

### Closure Gate

- [x] Every in-scope requirement and queue item has verified terminal evidence; external delivery is explicitly classified below.
- [x] Every original public observation has an individual causal disposition.
- [x] Protection, actual consumers, installed/native handoffs and resource investigation are verified.
- [x] Security/model findings corrected; exact accepted diagram and final quality gate verified.
- [x] Protected feature delivery, development publication and #296 reconciliation verified.
- [x] Stable metadata/notes/examples and full plan closure handoff prepared; checked lifecycle owns the archive/reset transaction.

### Post-Close Delivery

Required work outside the closed repository plan remains part of the active
release objective:

1. After checked archival and focused release-contract checks, commit/push the
   signed release/v0.14.6 branch and open exact-title `Release v0.14.6`. Require
   protected CI/security/build/dependency checks and merge only that checked head.
2. Independently verify CI-owned TestPyPI/PyPI publication and all Python
   3.12–3.15 installs, hashes, provenance, attestations, annotated tag, immutable
   Release/receipt and bot-owned closure of #297/#298. #296 is already closed as
   incorporated; milestone state is checked when applicable.
3. Verify automatic site refresh and clean synchronized main. Remove task-owned
   source copies, build/debug environments and obsolete Actions data according
   to the existing policy; retain the audit key and necessary source-free proof.

Stable publication, the signed release PR/merge and external readback are not
claimed completed. No repository closure PR or landing-chat handoff follows.
The persistent objective stays active until every external requirement is verified.

### Handoff Notes

All in-scope repository implementation and preparation are completed. No private
origin locators or source-bearing debug artifacts are embedded here. Required
external delivery is classified in Post-Close Delivery; the durable audit key
and source-free acceptance evidence are retained.

## Recently Completed

- [x] 2026-11-04: Completed Toolkit 0.14.5 — DLP precision, OCR qualification and maintenance quality; [full archived plan](docs/engineering/execution_history/plans/2026-11-04-toolkit-0-14-5-dlp-precision-ocr-qualification-and-maintenance-quality.md).
- [x] 2026-10-31: Completed Toolkit 0.14.4 systematic DLP corrections and diagram source validation; [full archived plan](docs/engineering/execution_history/plans/2026-10-31-toolkit-0-14-4-systematic-dlp-corrections-and-diagram-source-validation.md).
- [x] 2026-10-30: Completed Toolkit 0.14.3 source-aware DLP and private corpus audits; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-3-source-aware-dlp-and-private-corpus-audits.md).
- [x] 2026-10-30: Completed Toolkit 0.14.2 compact bootstrap, diagram-only reports and DLP corrections; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-2-compact-bootstrap-diagram-only-reports-and-dlp-corrections.md).
- [x] 2026-10-29: Completed Toolkit 0.14.1 grouped diagrams and private debug qualification; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-1-grouped-diagrams-and-private-debug-qualification.md).
- [x] 2026-10-29: Completed Toolkit 0.14.0 range identity, typed diagrams, DLP qualification and Python 3.15; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-0-range-identity-typed-diagrams-dlp-qualification-and-python-3-15.md).
- [x] 2026-10-25: Completed Two-day GitHub Actions retention; [full archived plan](docs/engineering/execution_history/plans/2026-10-25-two-day-github-actions-retention.md).
- [x] 2026-10-23: Completed Toolkit 0.13.1 partial review of changes containing gitlinks; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-1-partial-review-of-changes-containing-gitlinks.md).
- [x] 2026-10-23: Completed Toolkit 0.13.0 protected default-policy fallback for single-MR review; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-0-protected-default-policy-fallback-for-single-mr-review.md).
