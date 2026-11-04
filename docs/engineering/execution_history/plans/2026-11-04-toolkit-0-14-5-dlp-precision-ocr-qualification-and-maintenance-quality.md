# Execution Plans

## Active Plan: Toolkit 0.14.5 — DLP precision, OCR qualification and maintenance quality

plan_schema_version: 2
Status: done
Release classification: release-required
Target release: 0.14.5
Next development marker: 0.15.0
Last Updated: 2026-11-04

### Goal

Deliver and independently reconcile v0.14.5: correct demonstrated DLP false
positives, prove bounded excerpts from large immutable sources, qualify OCR
1.13.4–1.13.5 including diagrams/federation/gitlinks, restore weekly qualification,
remove unreachable qualification code, improve meaningful boundary coverage and
documentation, and complete the protected stable-release lifecycle and cleanup.

### Plan Origin

plan_mode_approved

### Requested Scope

Implement the approved plan as one release cycle. Library analysis concerns
focused additions to toolkit-owned DLP, not replacement of its admission policy.
Revisit the existing 605 conservative observations by their 14 causal groups;
counts are role observations, not unique defects or a precision measurement.
Preserve public and private evidence boundaries throughout implementation,
reviews, repeated corpus checks, publication and cleanup.

The release PR also incorporates compatible maintenance from open Dependabot
PRs #289–#291: development tooling, certifi and pinned GitHub Actions. Review
upstream identities and changes, validate the combined lock and affected local
contracts, and let protected CI run the complete combined matrix. Preserve
already applicable DLP/native/security evidence for unchanged toolkit source.

### Requirement Traceability

| Requirement | Requested outcome | Work | Status |
| --- | --- | --- | --- |
| REQ-001 | Strict complete datetime interpretation without contact/secret bypasses | WQ-03, WQ-05 | done |
| REQ-002 | Bounded streaming immutable-source proof for short excerpts in large files | WQ-04, WQ-05 | done |
| REQ-003 | Source-free proof diagnoses and causal replay of remaining DLP groups | WQ-03, WQ-04, WQ-06 | done |
| REQ-004 | Evaluate focused model-free library additions and retain concrete comparative tests | WQ-03, WQ-05 | done |
| REQ-005 | Qualify adjacent OCR 1.13.4/1.13.5 and actual consumed capabilities | WQ-02, WQ-05 | done |
| REQ-006 | Restore weekly qualification, bounded dispatch and effective hosted execution | WQ-02, WQ-07 | done |
| REQ-007 | Remove unreachable live legacy and establish cohesive qualification owners | WQ-02 | done |
| REQ-008 | Improve branch/semantic coverage, property diversity and resource evidence | WQ-05, WQ-06 | done |
| REQ-009 | Reconcile instructions, architecture, contracts, threat model and backlog | WQ-01, WQ-05, WQ-06 | done |
| REQ-010 | Signed PRs, aggregate/security/native review, stable release and external closure; repository preparation complete, remaining delivery required under Post-Close Delivery | WQ-01, WQ-06, WQ-07, WQ-08 | out_of_scope |
| REQ-011 | Private-safe corpora and unchanged originals verified; owned raw cleanup complete, final delivery cleanup required under Post-Close Delivery | WQ-03, WQ-06, WQ-08 | out_of_scope |
| REQ-012 | Compatible Dependabot lock/pin updates prepared and locally qualified; required CI and superseded-PR reconciliation remain under Post-Close Delivery | WQ-09, WQ-08 | out_of_scope |

### Explicit Non-Goals

No new corpus repositories, new forge adapters, model/classifier downloads,
remote DLP validation, default phone region, repository-specific disclosure
exceptions, larger publishable-code limits, general workflow migration, blanket
runtime rewrite, new review-receipt schemas or landing-chat handoff. Do not
rewrite historical evidence or published tags/artifacts. Do not integrate corpus
audits into GitLab or hosted CI. Current runtime support windows remain intact.

### Constraints

- First repository write materializes this full plan; first signed feature push
  opens a draft PR. Further development remains local until final feature push.
- Root owns plan/status/release reconciliation. Self-review every logical commit;
  apply formatting before review and scan the exact staged content for secrets.
  Local unpublished corrections may amend; do not rewrite public history.
- Inspect actual producer/consumer boundaries. Use real Git, controlled protocol
  peers and clean installed artifacts where the contract crosses those owners.
- Keep source, credentials, private project identities, paths, hashes, raw audit
  state and internal conversation references out of public content. Publish
  independently constructed synthetic cases only. Preserve original inputs.
- One aggregate Codex Security diff scan after the finished range review, before
  actual own-tool acceptance. Ordinary fixes/docs do not trigger another scan
  without a concrete material coverage gap.
- Actual review uses ChatGPT high, unlimited aggregate budget, private debug
  artifacts and local diagrams. Budget/tool/context exhaustion or missing actual
  admitted diagram fails engineering acceptance. Plan one successful full run
  and a second only when needed; failed launches do not count. Record the count.
- Runtime dependencies preserve supported Python/platform, hash-locked binary-only
  installation, no models/network classification and bounded processing.
- Remove owned source copies and temporary builds/analysis resources at closure;
  preserve necessary source-free reports and release/security evidence. Include
  task-owned Docker/build resources and obsolete GitHub Actions logs/artifacts;
  preserve authoritative release evidence and unrelated user resources.

### Inputs And Sources

- Approved implementation plan and subsequent clarification: libraries supplement
  selected DLP stages; do not require replacing the toolkit detector.
- Current owners: AGENTS.md; project principles; development/release guides;
  security, local, diagram, context, audit and compatibility contracts; decision
  flow and test evidence matrix. Instruction contract version 3 is valid.
- The plan-entry recommendation was 1.13.3; local qualified pins now select
  1.13.5. The adjacent upstream stable
  releases: https://github.com/alibaba/open-code-review/releases/tag/v1.13.4 and
  https://github.com/alibaba/open-code-review/releases/tag/v1.13.5.
- Source review of both adjacent upstream diffs and repository planning probes.
- Public prior issue #286 and archived 0.14.4 plan establish historical causal
  dispositions. Authenticated private ledgers/replay locators remain outside Git.
- Current DLP implementation and acceptance are tracked in issue #292.
- Supplemental parser sources: Tree-sitter, Pygments, PIISA; prior Mistune/regex/
  emoji qualification and the existing production DLP implementation.

### User Decisions And Answers

Deliver through stable 0.14.5 with the normal feature/release PR sequence.
Investigate libraries rather than adding new corpus repositories. Prioritize
general causes, false negatives as well as false positives, meaningful coverage
and the Pareto principle. Remove actual legacy where it has no execution purpose.
Use libraries as focused additions where justified. Archive/reset the plan inside
the release PR; no later closure PR. No landing-chat task is requested.

### Completed Baseline State

Clean main/origin/main at ed42168c2605ea3f4ef22717d7e0862f8317e06f,
stable v0.14.4. Historical final gate: 4223 tests, 357 subtests, 89.17% branch-aware
coverage, individual affected DLP/audit floors passing. These are prior results,
not new-run evidence. At plan entry, no implementation changes had been made.

Planning confirmed the active workflow's daily cron is neutralized by a date
gate. Fresh qualification below 1.13.0 is already forbidden but live helpers
retain older branches. Diagram/gitlink gates separately require exact 1.13.3.
Datetime `updated 2026-10-23 08:52 UTC` is rejected because a phone match consumes
the date and part of the hour. All 115 public literal-proof-unavailable ledger
observations belong to one large file; existing DLP admits them under a
hypothetical verified excerpt. That is feasibility evidence, not production proof.

Tree-sitter 0.26.0 + C grammar distinguished computation/string/comment in a
synthetic probe, but erroneous trees also exposed expression nodes and Python
3.15 installation required a source build. Pygments tokens alone do not prove
executable context. Packaging parsers accept phone-like project/version syntax;
successful parsing alone cannot authorize a DLP exemption.

### Current Work Queue

| Item | Requirements | Work | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-009, REQ-010 | Full plan materialized/reviewed; signed plan commit 61a2fd2 pushed and draft PR #293 opened; DLP issue #292 created | done |
| WQ-02 | REQ-005, REQ-006, REQ-007 | Extracted owners, removed unreachable execution, froze predecessor epoch; both candidates passed Linux/Darwin base and actual consumed handoffs; promoted pins/capabilities locally and restored weekly workflow | done |
| WQ-03 | REQ-001, REQ-003, REQ-004, REQ-011 | Datetime/property fixes, fresh paired populations, fourteen-category causal review and retained supplemental-library counterexamples complete; missing historical authentication/locators remain explicit unknowns; final replay belongs to WQ-06 | done |
| WQ-04 | REQ-002, REQ-003 | Shared immutable session, identity/syntax separation, runner/diagram/GitLab consumers, closed audit diagnoses and installed/public-source handoffs verified; final own-tool acceptance belongs to WQ-06 | done |
| WQ-05 | REQ-001, REQ-002, REQ-004, REQ-005, REQ-008, REQ-009 | Linux coverage and source-boundary negative controls qualify the new floors; installed handoffs, synthetic/properties and current contracts/matrix/changelog reconciled; final aggregate/security/model review remains WQ-06 | done |
| WQ-06 | REQ-003, REQ-008, REQ-009, REQ-010, REQ-011 | Aggregate self-review, single Security scan, both native reviews/findings, full quality and final corpus/resource replay complete | done |
| WQ-07 | REQ-006, REQ-010 | Exact diagram delivered, all protected checks passed, feature PR #293 merged and development publication verified | done |
| WQ-08 | REQ-010, REQ-011, REQ-012 | Repository metadata, notes and checked archive handoff prepared; signed PR/CI/merge/publication/external readback and final cleanup remain required Post-Close Delivery | out_of_scope |
| WQ-09 | REQ-012 | Reviewed #289/#290/#291, combined targeted lock/pin updates and local compatibility/audit checks; protected delivery and superseded PR reconciliation transferred explicitly | done |

### Locked Decisions

**Datetime.** Interpret a complete bounded calendar datetime containing the phone
candidate, including time, optional seconds/fraction and timezone. Validate with
stdlib strict calendar parsing and token boundaries; do not exempt a word such as
`updated`. Explicit contact priority, invalid/continued token rejection and
independent original/derived sensitive-material checks remain authoritative.

**Excerpt proof.** Separate immutable source identity from optional full-source
syntax analysis. Stream regular Git text blobs, validate strict UTF-8 and reject
NUL across the entire blob, count exact lines and retain only bounded requested
excerpts/metadata. Limits: 5000000 bytes/blob, 32000000 aggregate bytes and 30
seconds/session, with shared accounting for repeated immutable objects. Retain
current publishable fragment limits. Large-file identity proof does not confer
syntax exemptions. Unavailable/oversized/stale/invalid inputs close proof. Runner
owns acquisition/session orchestration, pure contracts own identity/decisions,
reporting remains free of Git/MCP/environment/DLP orchestration. Reuse the Git
streaming boundary rather than creating another resolver or raw-blob reader.
Use Git's LF line addresses; CRLF is normalized for fragment comparison, while
bare CR and Unicode separators cannot introduce extra Git lines or authorize
misaligned full-source syntax roles. Plan all required spans before a blob read
and coalesce identical objects. Excerpt retention preserves the existing 12000
character and 200-line-span limits; optional full syntax stays within 256000
characters and never substitutes for the independent identity proof.

**Audit and causality.** Add source-free diagnoses for missing source,
source/excerpt limits, line mismatch and unavailable syntax refinement; diagnoses
never authorize publication. Review all 115 candidate observations through the
actual production path. Revisit all 14 causal groups, prioritizing numeric
composition and credential references, deduplicating line/whole-file roles while
preserving each observation's mapping. Unknown cases retain explicit conservative
reasons. Account for every newly admitted/rejected unit and changed reason;
never optimize an unclassified hit count or silently relabel a protection loss.

**Supplemental libraries.** Keep toolkit admission and existing parsing stack.
Use focused synthetic comparisons for Tree-sitter operator/string/comment roles,
Pygments token roles and PIISA candidate differences. No current Tree-sitter runtime
adoption because supported binary-only installation is unproved; retain precise
resume conditions (supported wheels, bounded correct role proof and demonstrated
benefit). Lexer/phone-plan/version-parser success or omission cannot establish
disclosure authority. No SDS execution boundary or CredSweeper ML graph in this
cycle. Use stdlib/current primitives for confirmed fixes; retain research
conclusions without leaving an implementation-choice catalogue.

**Qualification owners.** Keep scripts/ocr_compat.py as a stable thin CLI and
extract pure contracts, bounded acquisition/asset verification, deterministic
gateway/probes, promotion and GitHub delivery into cohesive repository-only
owners. Remove unreachable old execution branches and migrate applicable tests
to frozen readback; no import-everything shim. Qualify 1.13.4 first; freeze the
previous contract before introducing 1.13.5. Historical evidence bytes and current
runtime support windows remain unchanged. One pure runtime capability owner
replaces independent 1.13.3 diagram/gitlink checks; unqualified versions fail
closed. Native-auth applicability is reviewed separately from API probes.

**Consumed OCR changes.** Qualify checksum-verified Linux and Darwin binaries
against the adjacent chain. Check 1.13.4 missing/mixed diff reads. Check 1.13.5
max-tools omitted/0 default, 49 normalization to 50, exact 50/75/100/125 behavior,
grace completion and warnings/coverage through a real deterministic peer. Check
new language/Rules inventory, complex ` b/` paths, rename/copy and blank-line
anchors. Qualify both diagram variants/grouping, actual evidence/federation MCP
and partial gitlink handoffs. Promote runtime qualification pins/monitoring together
only after admission. Keep the example's published toolkit/OCR pair intact until
the release PR advances both versions and its checksum together. Release fragments distinguish maintenance, runtime fixes,
workflow behavior and Rules changes accurately.

**Weekly workflow.** Remove the obsolete date gate and dependent conditions;
cron `15 7 * * 1` is Monday 07:15 UTC. Preserve bounded discovery, mutually
exclusive manual tag/through_tag, issue idempotency and protected promotion.
Actual hosted acceptance uses a v1.13.5 ceiling and checks real work, not just
workflow success. No automatic stable release is introduced.
After promotion moves the monitoring floor to 1.13.5, use exact-tag dispatch
`tag=v1.13.5` at the final feature head: through-tag discovery at that same floor
would do no qualification work. The adjacent chain is covered by the retained
Linux/Darwin evidence; hosted acceptance must exercise the selected candidate.

**Coverage/resources.** Preserve >=90% individual affected DLP/audit/new-owner
floors and existing higher results. Hypothesis defaults 100 examples/property;
extended local 1000 with independent seeds/minimized synthetic regressions.
Improve posting group to >=87% before raising its gate to 85%; raise total gate
to 88% only after >=89% on CI-owner Python 3.14. Never waive a required check to
meet a number. Compare complete replay CPU/wall/RSS with installed 0.14.4 under
the same Python/environment/input; a wall-time or RSS increase above 15% triggers
repeat measurement and profiling, not automatic acceptance. Keep audit
local-only and test actual bounded/cancellation/cleanup paths.

**Review/delivery.** One aggregate Security scan then threat-model review. Actual
own-tool acceptance requires high ChatGPT, --max-tokens-budget 0,
OCR_REVIEW_DIAGRAM_MODE=local, reviewed Rules/private diagnostics, admitted model
diagram and no material unresolved failed reads or filtered findings. Attach the
exact Mermaid to the final feature PR, without debug text. Signed release branch
release/v0.14.5 and exact title Release v0.14.5; checked archive/reset belongs to
that PR. CI owns receipt-bound issue closure; independently verify external state.

### Verification

- Strict datetime valid/invalid calendar and token boundaries, explicit contacts,
  adjacent secret/email/phone values, original/encoded/Unicode representations.
- Excerpt first/last/empty/CRLF/non-LF lines, byte/character boundaries, split UTF-8,
  late NUL/invalid UTF-8, stale refs, symlink/gitlink, limits/deadlines, repeat
  references, malformed persisted data, descriptor ownership and cleanup.
- Production local/GitLab projection, renderer safety, optional diagram failure
  independence and real MCP peers; clean wheel/sdist outside checkout.
- Historical readback/promotion integrity and current real OCR numeric, Rules,
  diff-path/anchor, native auth, diagram, federation and gitlink qualifications.
- Weekly schedule/no-date-stop, manual selection, empty discovery, failures,
  bounded chain and actual hosted dispatch with the selected ceiling.
- Meaningful posting freshness/retry/idempotency/approval and context-persistence
  negative paths; branch-aware floors, extended independent property seeds.
- Complete authenticated before/after corpora including previously passing units;
  every transition classified, no unexplained protection loss; resource comparison.
- Instruction/document/public-content, format/lint/types/Bandit, secret/dependency,
  protected CI, installed artifact and release/provenance/receipt gates.

### Historical Validation Checkpoints

The initial plan commit has a verified SSH signature. Gitleaks passed for its
staged content, public tree and feature history; instruction/privacy checks and
the shared dependency audit passed too.
It is published in draft PR #293. Qualification characterization passed 175
tests in 11.92 seconds. The mechanical extraction retains all 77 original
function/class ASTs modulo explicit owner qualification; none is missing or
semantically changed. The same 175 tests pass in 8.15 seconds, and manifest
validation passes. Combined qualification/document/environment consumers pass
241 tests with one expected external-qualification skip. The checksum-verified
Darwin arm64 OCR 1.13.3 completed the full real deterministic probe-local CLI
through the extracted owners. Semantic review corrected module/local-name
collisions, preserved CLI help and fresh test-owner isolation, and reconciled
instruction routes. This proves extraction behavior for the existing contract,
not candidate 1.13.4/1.13.5 qualification or clean installed artifacts. No Security
scan, actual model review, hosted qualification or publication has completed in
this cycle. Further feature work remains local after the first plan push.

Signed local commits 4803979 and be4369e contain the characterized extraction and
unreachable-live-branch removal; the latter passed 187 focused tests. The current
slice freezes the proven 1.13.0–1.13.4 readback independently of live settings,
advances fresh qualification to 1.13.5, restores Monday qualification without the
date gate, and measures effective numeric defaults/overrides against native
manifest limits. OCR 1.13.4 and 1.13.5 passed their complete base contracts on
checksum-verified Linux amd64 and Darwin arm64 binaries. Both Linux candidates
are human-review-required. The first disposable 1.13.4 environment lacked Git;
the corrected setup passed. Current qualification/document/environment checks
passed 240 tests, including effective-limit corruption cases. Formatting, lint,
manifest validation, instruction and public-content checks pass. Semantic review
preserved frozen evidence and runtime support, checked default/override/grace
boundaries, and corrected the actual extracted-peer consumers. Existing
real diagram/group/gitlink consumers passed 100 tests against supported 1.13.3;
four stale peer imports were corrected to their extracted owner. These checks
do not qualify those capabilities on the new candidates. Issue #294 tracks the
adjacent qualification chain. Recommendation and runtime capabilities
were unchanged until specialised proofs passed. Candidate artifacts, setup environment
and cleanup inventory stay private. DLP implementation and corpus replays remain
pending; no new feature push, Security scan or model review has occurred.
Successful own-tool reviews in this cycle: 0/2. Aggregate Security scans: 0/1.

Signed local commit 4e83832 contains the frozen predecessor, live 1.13.5 contract
and weekly workflow. Both new Darwin binaries then passed 111 real native
diagram/group/federation/gitlink checks each. Missing/mixed/all-found diff reads
passed for both; 1.13.5 additionally passed delimiter-path modification, rename,
copy destination and new-side blank-line anchor checks. Fixture corrections
retained enough unchanged content for Git rename detection and disambiguated a
duplicate copied block; neither was a product failure. Official platform-specific
digests are now checked by shared opt-in test fixtures before candidate execution.
Promotion used the validated adjacent evidence chain and recorded bounded human
conclusions; manifest, preflight, example pins and pure capability gates now agree
on 1.13.5. Native-auth source review found no changed ownership or resolution
boundary. Public contracts, route map and decision flow reflect capability gates.
Consumer checks passed 754 tests with 45 expected external-binary skips; the one
stale current-pin assertion was corrected and its focused check passed. Types
pass across 168 runtime files; preflight/local-provider checks passed 150 tests
and 42 subtests. Clean installed artifacts, final coverage and hosted execution
remain WQ-05/WQ-07 gates. All implementation remains local after the plan push.
The new pure capability owner has 100% measured coverage with exact-version,
future-version and generated-string controls. Semantic review also found that
unhashable entries in current evidence capability lists could raise TypeError;
both frozen and live validators now reject them through the closed contract
error. The 33 focused malformed-list/current-pin checks pass. Review preserved
range/source/selection checks, optional-output degradation, historical evidence
and provider authority; only exact proven handoffs gain capability admission.

Signed local commit febab52 contains the consumed handoffs and OCR promotion.
The next DLP slice recognizes complete bounded calendar timestamps around the
whole phone candidate without a keyword whitelist. It validates calendar/clock
and offsets, keeps explicit contact priority, rejects continued/ambiguous bounded
lookahead, and leaves original/derived secret and PII checks independent. Diverse
properties found a Unicode decimal-domain mismatch; normalization now covers all
decimal digits while preserving source-position containment. Regressions also
cover stdlib 24:00 normalization and offset-minute overflow. A generator oracle
was corrected because additional fractional digits can form another valid
timestamp, rather than a malformed token.
The final scoped DLP/audit/context/property suite passes 1197 tests. Datetime
tests pass 72 checks on Python 3.12.9, 3.14.0 and 3.15.0; two independent extended
seeds pass all five properties at 1000 examples each. The new module has 100%
measured statement/branch coverage. Both new runtime owners now have explicit
90% local/hosted floors; 44 workflow/quality contracts pass. Format/lint, runtime
types and public-content checks pass. The audit's installed-source identity
automatically includes the new owner. Prior authenticated ledger/state remain
retained outside Git; corpus replays, resource comparisons and remaining causal
groups/library conclusions have not been completed or reclassified as passes.

WQ-04's producer foundation extends the existing streamed Git text boundary;
it validates the full UTF-8/NUL-free blob, exact size and actual Git object digest
before returning any captured range. Only bounded requested LF-addressed excerpts
and optional separately bounded full syntax text can be retained; metadata-only
consumers retain no source. Invalid capture arguments stop before Git I/O.
65 real Git/process and extraction controls pass with 100% measured coverage
across streaming/retention owners, including corrupt same-size loose objects,
late invalid bytes, CRLF, non-LF separators, process failures and deadlines after
peer exit/capture completion. Another 190 repository/syntax/quality checks pass;
two independent 1000-example extraction properties match a separate full-text
oracle. Shared pure limits preserve existing publication bounds. Caller batching,
admission integration, audit diagnoses and all 115 real proof observations remain
pending; the producer tests alone do not establish those outcomes.

The next local slice integrates one immutable session across finding proofs and
optional diagram metadata, with object-alias coalescing, charged failed reads,
four-entry syntax retention and finding-first priority. GitLab remapping precedes
its separate suggestion session; the old full-blob suggestion reader is removed.
Audit workers reuse authenticated snapshot text and publish closed source/syntax
diagnoses with an explicit version marker; old run shapes retain frozen readback.
256 focused tests pass with about 98% combined branch-aware coverage; each new
owner exceeds 90%. A real finalizer fixture preserves 115 distinct short fields
from a large synthetic file in one blob read. Real posting/remapping, stale and
missing source, corrupt persisted diagnoses and nested JSON properties pass.
Two independent extended property seeds pass; 445 runner/posting/optional-output
checks and 205 subtests also pass. These synthetic handoffs do not authenticate
the historical corpus observations. Current private replay and installed/final
acceptance remain outstanding.

Fresh paired public replay uses installed 0.14.4 and the clean candidate wheel
under the same Python 3.14/runtime dependencies and authenticated immutable input:
both complete all 121583 units. Rejections change from 2308 to 2192, with 116
admissions, no new rejections, and 172 changed facts/reasons awaiting causal
classification. This is not a precision/protection-preservation claim. Independent
snapshot-to-Git-to-publication replay confirms all 115 large-source observations
from the fresh run, with one 658778-byte read and no syntax authority. The other
admission contains the demonstrated complete calendar timestamp. Wall time is
98.42 versus 99.70 seconds; peak RSS is 177487872 versus 175194112 bytes. The 15%
investigation trigger is not reached. Historical HMAC state remains unverified.

Retained optional research tests pass against actual Tree-sitter 0.26.0/C 0.24.2,
Pygments 2.21.0 and PIISA regex 0.5.1: erroneous trees still expose expression
nodes, lexer numeric roles survive broken syntax, and the international lexical
stage omits a prefix-free contact that toolkit blocks. These do not qualify
source authority or the full regional/context pipeline. Binary-only probes fail
for Tree-sitter on Python 3.15 and for the PIISA plugin. No runtime dependency is
added; current admission/stdlib fixes remain the selected implementation. The
development owner records the concrete reconsideration conditions. Source
handoff tests also pass actual Python 3.12 and 3.15 (57 each).

The current full branch-aware coverage run passes 4461 tests and 357 subtests
(53 expected optional/external skips), including clean installed wheel/sdist
behavior. Total coverage is 89.41%; all current independent gates pass. GitLab
posting remains 82.45%, below the planned >=87% measurement required before its
gate moves to 85%; meaningful posting-edge tests remain WQ-05 work. New floor
values are not yet claimed as delivered. Additional authorized private paired
replays use explicit curated text selections and metadata-only original-file
verification, with no source copies. Their source-free comparisons and resource
results remain private; final post-review replay and cleanup are still required.

Additional approval-adapter tests exercise malformed MR/diff/author/approval JSON
through a validated current receipt, preserve the previous-review decision, and
assert no approval write. Post-write author changes cannot become a success or
trigger another write. All 20 focused tests pass; the non-object JSON property
also passes independent 1000-example seeds. Appending these checks to the unchanged
runtime measurement raises posting to 83.25% and total to 89.48%; the >=87%
posting target and threshold changes remain pending.

The next boundary slice adds 78 HTTP, snapshot, artifact, delivery and terminal-state
checks. Host posting coverage reaches 87.10%; Linux amd64/Python 3.14 measures
89.84% overall and 87.10% posting. The minimal-container full run exposed six
missing-jq shell checks and four fixture-only retained-HOME cleanup assumptions.
The prerequisite and owned-tree fixture cleanup were corrected; all affected
checks pass on focused Linux replay. A fresh immutable Git/projection test also
proves that a narrow reference role cannot authorize a mixed whole-source unit.
Total/posting gates now become 88%/85% in both local and hosted owners.

All fourteen causal groups have explicit dispositions in the public
[causal matrix](docs/engineering/dlp_causal_review.md), with per-observation
correspondence kept private. Fresh public comparison has zero unexplained
admissions, unreviewed transitions, new rejections, or classified protection loss.
Unchanged untriaged observations remain explicitly unclassified, not sensitive
by assertion or a precision claim. Historical missing-key/unrecoverable inputs
remain unknown. Fresh private transitions are independently reviewed and their
material, identities and statistics remain outside public artifacts.

Aggregate self-review reconciles the full branch interactions: qualification
capabilities remain separate from runtime acceptance; source identity remains
separate from syntax and privacy authority; finding proofs precede optional
diagram reads; remapping precedes posting excerpt acquisition; old/new audit
shapes reject mixed diagnostics atomically. The full range has no whitespace
errors, support-manifest validation, Ruff and runtime typing pass, and the new
delivery/source checks pass Python 3.12 and 3.15 (105 each). Independent Security
review and actual model/diagram acceptance remain mandatory and have not run.


The single aggregate Security diff scan completed on ed42168..68b4a73 with
complete changed-file coverage and no findings. Independent architecture review
reconciled the current threat model. The first real own-tool review completed
from the clean installed current-head wheel with ChatGPT high, unlimited token
budget and an admitted model diagram: 94/94 selected files complete, nine findings
(one conservatively filtered). At that checkpoint successful own-tool runs were 1/2; engineering
acceptance remains pending. Corrections cover datetime
lookahead, chunk-independent excerpt allocation, audit LF-span mapping, test
oracles/qualification isolation and plan/release notes. A parallel
full quality run passed 4543 tests but 17 CLI-boundary cases encountered the
active checkout's legitimate review lock. Those tests now use isolated working
directories without replacing the production lock: all 103 affected-module
checks pass. The repeated full gate passes 4595 tests and 357 subtests, with 53
expected optional/external skips; all independent coverage gates, format, lint,
types and Bandit pass. The missing Rules
changelog category is present. Corrections remain within the reviewed
source/proof/promotion boundaries and receive focused behavioral and semantic
checks without a second aggregate Security scan. The missing auxiliary decisions-module read targeted
no existing file; the retained trace proves successful scanner, proof, state and
consumer reads. The model's hidden audit finding was conservatively filtered as
HTML-like prose and has been independently reproduced through the real worker.
Initial focused fixes pass 321 checks with 99.34% combined coverage across the
three changed owners. Eleven properties pass two independent 1000-example seeds;
the actual qualified federation route passes with an invalid unrelated binary
setting. Final full tests, resource/corpus replay and second model review remain
required. The published example now retains its working pair until the release
PR; promotion cannot independently advance its OCR half. The correction suite
passes 272 checks on each of Python 3.12 and 3.15. Qualification/environment/docs
and release-note contracts pass 307 checks. Semantic self-review verifies fixed
whole-token grammar, byte-bounded source-position allocation, unchanged audit unit
identities, lazy optional-binary validation and the published-example boundary;
it preserves disclosure gates and does not infer authority from source proof.

The second installed-artifact own-tool review completed at 0fbe34f: native
coverage 99/99, no budget or coverage warnings, DLP passed and a generated
eleven-node change-flow diagram admitted. Its complete private trace confirms
the diagram output call and evidence navigation. One failed auxiliary read
named a nonexistent detector module; the actual numeric/admission owners were
read successfully. Successful own-tool runs are now **2/2**; do not launch another.
Five findings received focused corrections: bind qualification-issue reuse to
forge-controlled authorship, reject promotion-output collisions, and repair
three negative test oracles so their valid controls reach the intended guards.
A fresh independent security investigator and post-patch reviewer examined the
issue-authorization fix; no surviving bypass or regression was reported.
The public threat model and compatibility contracts now state that boundary.
No second aggregate Security scan is needed for these scoped corrections.

Final paired corpus replays are complete, with no unexplained admissions,
unreviewed changes, new rejections or confirmed protection loss. Existing
untriaged observations remain explicit and are not a clean-precision claim.
Three resource comparisons remain within the 15% investigation threshold; one
short scan initially exceeded it. Three repeated serial baseline/candidate pairs
all completed; median candidate/baseline ratios are 0.961 wall time, 0.997 CPU
and 1.000 RSS. The initial variance does not establish a performance regression.
Repository-only follow-up corrections do not change the replayed runtime.
The final full quality gate passes 4625 tests and 357 subtests, with 53 expected
optional/external skips; coverage is 89.86% overall and 87.10% for posting, and
every independent floor, format, lint, typing and Bandit check passes. Focused
qualification/posting/document checks pass 334 cases. A delayed HTTP-response
finalizer warning exposed unclosed error responses in controlled-peer tests;
those responses now close explicitly rather than relying on garbage collection.
All 262 qualification checks pass with unraisable-exception warnings treated as
errors. Dependency audit and working-tree/unpublished-history secret gates pass.


### Latest Validation Results

Final verification date: 2026-11-04. Historical checkpoints above retain their
original scope and are superseded by the final results in this section.

The final runtime and first-review corrections pass the full quality gate:
4625 tests and 357 subtests, with 53 expected optional/external skips. Coverage
is 89.86% overall and 87.10% for posting; every independent floor, formatting,
lint, typing and Bandit check passes. Eleven source/datetime properties pass two
independent 1000-example seeds. Focused corrections pass 272 checks on each of
Python 3.12 and 3.15, and clean installed Linux consumers pass 521 checks.

Verified Linux amd64 and Darwin arm64 OCR 1.13.4/1.13.5 binaries pass the consumed
contract suite. Each Darwin binary also passes 111 actual diagram, grouped-round,
evidence/federation MCP and partial-gitlink consumer checks. Effective numeric
limits, missing/mixed diff reads and 1.13.5 path/rename/copy/blank-anchor cases
pass. Frozen evidence remains unchanged. Exact-tag hosted run 41860552131 passes
actual qualification and canonical-issue update, rather than empty discovery.

One aggregate Security diff scan of ed42168..68b4a73 completed with complete
changed-file coverage and no findings. Its independent architecture pass
reconciled the threat model. Later own-tool findings received focused fixes and
independent issue-authorization investigation/post-patch review; the current
threat model includes that boundary. No second aggregate scan was run.

Two clean installed ChatGPT high own-tool reviews used unlimited aggregate token
budgets and admitted diagrams. The first completed 94/94 files with nine findings;
the second completed 99/99 with five findings, DLP passed and no budget/coverage
warnings. All findings are corrected. Failed auxiliary reads named nonexistent
modules; actual owners were read. The second trace was complete. The exact second
admitted Mermaid appears in feature PR #293. The allowance is exhausted at 2/2.

Final authenticated baseline/candidate corpus replays are complete, with no
unexplained admissions, unreviewed transitions, new rejections or confirmed
protection loss. Retained conservative/unknown observations remain explicit;
these results do not establish universal precision or authenticate old records
whose HMAC key is unavailable. All fourteen causal groups have synthetic public
dispositions. Supplemental parser comparisons remain counterexamples, not new
runtime parsing authority. A short timing outlier triggered three repeated serial
pairs: median candidate/baseline ratios are 0.961 wall time, 0.997 CPU and 1.000
RSS. No reproduced resource regression remains.

All 11 checks required by the current main ruleset passed on 542000b, including
Linux Python 3.15. Additional macOS jobs were queued at feature merge; the local
macOS full gate was already verified. PR #293 merged as b9905b0. Development
TestPyPI run 41866229748 is completed/success: build, publish, provenance and
clean installed-artifact verification jobs all succeeded on that exact merge.

The approved dependency updates change only certifi, mypy, ast-serialize, pytest
and Ruff package records; all unrelated records and lock metadata are unchanged.
Twenty-one Action pins in nine workflows match verified upstream tags; workflow
permissions/control flow and the restored weekly schedule are preserved. New
Ruff formatting/lint, mypy typing, all 4678 pytest collection cases and dependency
audit pass. Selected qualification/release-boundary checks pass with the new
tools; all 64 post-archive environment, documentation and release-note checks
pass. Certifi's updated bundle loads in the real TLS context. Full combined tests, packaging
and installed registry matrices remain mandatory protected/external delivery.

The release branch pairs toolkit 0.14.5 with OCR 1.13.5 and its verified Linux
checksum, keeps next marker 0.15.0, and authorizes issues #292/#294. Towncrier
includes dependency maintenance from #289/#290/#291 and preserves conditional
Rules/Security sections. Stable publication and external closure are pending.
Owned raw audit snapshot cleanup succeeded; private inputs were metadata-only.
Temporary builds/debug environments moved to OS Trash after required acceptance
artifacts were retained privately. The current audit key/source-free state is
preserved; original input repositories were not modified.

### Risks And Recovery

Source proof must never imply confidentiality or syntax authority. Streaming
failures discard partial proof; repeated reads cannot bypass aggregate limits.
Do not enlarge publication budgets to fix audit counts. A parser's recovery tree
or a missing phone match cannot justify admission. Qualification extraction can
break monkeypatch-based tests or CLI imports: characterize first, preserve the
external CLI and exercise actual callers after each move. Qualify 1.13.4 before
freezing its epoch. Block promotion on consumed-contract failures; do not silently
drop diagrams/gitlinks. Source-free replay metadata may outlive removed snapshots:
recover only exact authorized immutable inputs, never substitute another corpus.
Retain explicit ownership/cleanup for any new private snapshots. Preserve failed
check evidence and review exact identities before retrying external mutations.

Historical audit recovery found retained signed metadata but no matching HMAC
key; the operator confirmed the temporary state is no longer available. Source
repositories do not replace that key. Treat retained locators as untrusted hints,
recover authorized immutable revisions where possible, and capture a fresh
authenticated population for both installed 0.14.4 and the candidate. Keep its key
and source-free evidence in durable private storage. Do not claim old identities,
annotations or the historical 115 observations have been authenticated or exactly
replayed without their original key. Classify current observations independently;
record unrecovered historical cases as unknown. This changes evidence recovery,
not the required detector, corpus, privacy or protection-preservation outcomes.

### Resume Point

No unfinished in-scope repository implementation remains. Required external delivery is classified below; the full release objective is not complete.

### Plan Fidelity Check

- [x] Requested outcomes map to requirements, queue and verification.
- [x] Supplemental-library clarification and concrete planning probes preserved.
- [x] Privacy, source/sink, resource, capability and review limits recorded.
- [x] Qualification/frozen-history ordering avoids invalidating predecessor proof.
- [x] Release-required target, archive owner and external closure are explicit.
- [x] No omitted outcome is disguised as a non-goal; resume point is actionable.
- [x] Disk plan rechecked against all five approved scope groups after the first
  implementation step: baseline/prior research, concrete DLP fixes, supplemental
  libraries, OCR/architecture/tests/docs, and complete protected release/cleanup.
  The check restored explicit Linux/Darwin qualification, the 15% performance
  investigation trigger and hosted/task-owned cleanup detail; no approved
  deliverable was dropped. Current queue/evidence were reconciled separately.

### Reconciliation Check

- [x] Baseline and final repository contracts, backlog, current issues and verification state agree.
- [x] Historical evidence is distinguished from current qualified observations.
- [x] Repository completion and pending external delivery are classified separately without claiming publication.

### Closure Gate

- [x] In-scope repository requirements/queue are terminal; requested external work remains explicitly required below.
- [x] Aggregate/security/native review findings are resolved and the admitted diagram is delivered.
- [x] Applicable local gates, exact corpus transitions and owned raw cleanup are verified; combined CI remains required delivery.
- [x] Version/authorization/example/notes handoff is prepared and the checked lifecycle owns the archive/reset transaction.

### Post-Close Delivery

Required work outside the closed repository plan remains part of the active release objective:

1. Commit and push the signed release/v0.14.5 branch, open the exact-title Release v0.14.5 PR, and require current protected CI/security/build/dependency gates for the combined dependency changes. The post-archive local release-contract checks precede that commit.
2. Exercise exact-tag hosted OCR 1.13.5 qualification with the updated Action pins and lock, retaining the verified unchanged consumed-contract boundary. No additional paid model review or aggregate Security scan is authorized or needed.
3. Merge only the checked release head. Independently verify Release CI's exact TestPyPI/PyPI distributions, provenance, attestations, all supported-Python installs, annotated tag, immutable Release/receipt and CI-owned closure of #292/#294.
4. Reconcile superseded dependency PRs #289/#290/#291, milestone state when applicable, automatic site update and clean synchronized main. Remove remaining task-owned temporary files/builds and obsolete Actions logs/artifacts under the existing maintenance policy; keep the audit key and necessary source-free acceptance evidence.

Publication, PR creation/merge and external readback are not claimed completed. No extra repository closure PR follows stable publication. Do not mark the persistent release goal complete until every external requirement is verified.

### Handoff Notes

All in-scope repository implementation and preparation are completed. No private origin locators or source-bearing debug artifacts are embedded here. Required external delivery is classified in Post-Close Delivery; durable private acceptance evidence and the current audit key are retained.

## Recently Completed

- [x] 2026-10-31: Completed Toolkit 0.14.4 systematic DLP corrections and diagram source validation; [full archived plan](docs/engineering/execution_history/plans/2026-10-31-toolkit-0-14-4-systematic-dlp-corrections-and-diagram-source-validation.md).
- [x] 2026-10-30: Completed Toolkit 0.14.3 source-aware DLP and private corpus audits; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-3-source-aware-dlp-and-private-corpus-audits.md).
- [x] 2026-10-30: Completed Toolkit 0.14.2 compact bootstrap, diagram-only reports and DLP corrections; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-2-compact-bootstrap-diagram-only-reports-and-dlp-corrections.md).
- [x] 2026-10-29: Completed Toolkit 0.14.1 grouped diagrams and private debug qualification; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-1-grouped-diagrams-and-private-debug-qualification.md).
- [x] 2026-10-29: Completed Toolkit 0.14.0 range identity, typed diagrams, DLP qualification and Python 3.15; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-0-range-identity-typed-diagrams-dlp-qualification-and-python-3-15.md).
- [x] 2026-10-25: Completed Two-day GitHub Actions retention; [full archived plan](docs/engineering/execution_history/plans/2026-10-25-two-day-github-actions-retention.md).
- [x] 2026-10-23: Completed Toolkit 0.13.1 partial review of changes containing gitlinks; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-1-partial-review-of-changes-containing-gitlinks.md).
- [x] 2026-10-23: Completed Toolkit 0.13.0 protected default-policy fallback for single-MR review; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-0-protected-default-policy-fallback-for-single-mr-review.md).
