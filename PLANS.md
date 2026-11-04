# Execution Plans

## Toolkit 0.14.5 — DLP precision, OCR qualification and maintenance quality

Status: active
Plan Origin: plan_mode_approved
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

### Requested Scope

Implement the approved plan as one release cycle. Library analysis concerns
focused additions to toolkit-owned DLP, not replacement of its admission policy.
Revisit the existing 605 conservative observations by their 14 causal groups;
counts are role observations, not unique defects or a precision measurement.
Preserve public and private evidence boundaries throughout implementation,
reviews, repeated corpus checks, publication and cleanup.

### Requirement Traceability

| Requirement | Requested outcome | Work | Status |
| --- | --- | --- | --- |
| REQ-001 | Strict complete datetime interpretation without contact/secret bypasses | WQ-03, WQ-05 | pending |
| REQ-002 | Bounded streaming immutable-source proof for short excerpts in large files | WQ-04, WQ-05 | pending |
| REQ-003 | Source-free proof diagnoses and causal replay of remaining DLP groups | WQ-03, WQ-04, WQ-06 | pending |
| REQ-004 | Evaluate focused model-free library additions and retain concrete comparative tests | WQ-03, WQ-05 | pending |
| REQ-005 | Qualify adjacent OCR 1.13.4/1.13.5 and actual consumed capabilities | WQ-02, WQ-05 | pending |
| REQ-006 | Restore weekly qualification, bounded dispatch and effective hosted execution | WQ-02, WQ-07 | pending |
| REQ-007 | Remove unreachable live legacy and establish cohesive qualification owners | WQ-02 | pending |
| REQ-008 | Improve branch/semantic coverage, property diversity and resource evidence | WQ-05, WQ-06 | pending |
| REQ-009 | Reconcile instructions, architecture, contracts, threat model and backlog | WQ-01, WQ-05, WQ-06 | in_progress |
| REQ-010 | Signed PRs, aggregate/security/native review, stable release and external closure | WQ-01, WQ-06, WQ-07, WQ-08 | in_progress |
| REQ-011 | Private-safe corpora, unchanged originals and task-owned cleanup | WQ-03, WQ-06, WQ-08 | pending |

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
  preserve necessary source-free reports and release/security evidence.

### Inputs And Sources

- Approved implementation plan and subsequent clarification: libraries supplement
  selected DLP stages; do not require replacing the toolkit detector.
- Current owners: AGENTS.md; project principles; development/release guides;
  security, local, diagram, context, audit and compatibility contracts; decision
  flow and test evidence matrix. Instruction contract version 3 is valid.
- compatibility/ocr-support.json recommends 1.13.3; upstream adjacent stable
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
not new-run evidence. No implementation changes have yet been made.

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
| WQ-01 | REQ-009, REQ-010 | Materialize/critique plan, reconcile routes, signed plan push/draft PR and scoped issue tracking | in_progress |
| WQ-02 | REQ-005, REQ-006, REQ-007 | Characterize/extract qualification owners, remove unreachable legacy, qualify adjacent candidates/capabilities and restore weekly workflow | pending |
| WQ-03 | REQ-001, REQ-003, REQ-004, REQ-011 | Freeze replay baseline, implement strict datetime fix, inspect causal groups and retain focused library comparisons/synthetic regressions | pending |
| WQ-04 | REQ-002, REQ-003 | Implement shared bounded excerpt acquisition/proof and closed audit diagnoses across real callers | pending |
| WQ-05 | REQ-001, REQ-002, REQ-004, REQ-005, REQ-008, REQ-009 | Integrate handoffs, improve coverage/properties, installed checks and synchronize contracts/routes/docs | pending |
| WQ-06 | REQ-003, REQ-008, REQ-009, REQ-010, REQ-011 | Aggregate self-review, one Security scan/threat-model reconciliation, actual native review/diagram, scoped fixes and complete corpus/resource replays | pending |
| WQ-07 | REQ-006, REQ-010 | Final quality/secret/dependency gates, attach exact diagram, final feature push, hosted dispatch/protected CI, merge/dev publication | pending |
| WQ-08 | REQ-010, REQ-011 | Signed release PR with checked plan archive/reset, stable/external receipt readback, issue/site/main reconciliation and cleanup | pending |

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

**Consumed OCR changes.** Check 1.13.4 missing/mixed diff reads. Check 1.13.5
max-tools omitted/0 default, 49 normalization to 50, exact 50/75/100/125 behavior,
grace completion and warnings/coverage through a real deterministic peer. Check
new language/Rules inventory, complex ` b/` paths, rename/copy and blank-line
anchors. Qualify both diagram variants/grouping, actual evidence/federation MCP
and partial gitlink handoffs. Promote all pins/checksums/monitoring together only
after admission. Release fragments distinguish maintenance, runtime fixes,
workflow behavior and Rules changes accurately.

**Weekly workflow.** Remove the obsolete date gate and dependent conditions;
cron `15 7 * * 1` is Monday 07:15 UTC. Preserve bounded discovery, mutually
exclusive manual tag/through_tag, issue idempotency and protected promotion.
Actual hosted acceptance uses a v1.13.5 ceiling and checks real work, not just
workflow success. No automatic stable release is introduced.

**Coverage/resources.** Preserve >=90% individual affected DLP/audit/new-owner
floors and existing higher results. Hypothesis defaults 100 examples/property;
extended local 1000 with independent seeds/minimized synthetic regressions.
Improve posting group to >=87% before raising its gate to 85%; raise total gate
to 88% only after >=89% on CI-owner Python 3.14. Never waive a required check to
meet a number. Compare complete replay CPU/wall/RSS with installed 0.14.4 under
the same Python/environment/input; profile substantial regressions. Keep audit
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

### Latest Validation Results

Planning-only observations above; manifest validation and instruction-contract
checks passed on the unchanged baseline. Materialized-plan semantic review,
instruction/privacy checks and pre-push dependency audit passed. No new implementation, Security scan,
actual model review, hosted qualification or publication has completed.
Successful own-tool reviews in this cycle: 0/2. Aggregate Security scans: 0/1.

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

### Resume Point

WQ-01: review the materialized plan against all approved requirements, perform
applicable plan/instruction/privacy guards, create the codex feature branch and
signed plan commit, run pre-push gates, push once and open the draft PR. Then
proceed to characterization/extraction and qualification in WQ-02.

### Plan Fidelity Check

- [x] Requested outcomes map to requirements, queue and verification.
- [x] Supplemental-library clarification and concrete planning probes preserved.
- [x] Privacy, source/sink, resource, capability and review limits recorded.
- [x] Qualification/frozen-history ordering avoids invalidating predecessor proof.
- [x] Release-required target, archive owner and external closure are explicit.
- [x] No omitted outcome is disguised as a non-goal; resume point is actionable.

### Reconciliation Check

- [x] Baseline code, manifest, workflow and plan state inspected.
- [x] Historical verification distinguished from current evidence.
- [ ] Implementation/docs/backlog/issue and final verification state agree.
- [ ] Final repository and external delivery state agree.

### Closure Gate

- [ ] All in-scope requirements and queue items terminal with applicable evidence.
- [ ] Aggregate/security/native review findings resolved and diagram verified.
- [ ] Final gates, exact corpus transitions and raw cleanup verified.
- [ ] Release PR contains checked archive/reset, metadata and truthful handoff.

### Post-Close Delivery

Repository plan remains active through feature delivery and release preparation.
The release PR archives the final repository state using the checked lifecycle;
registry/provenance/install/tag/immutable receipt/issue/site readback remains
required external delivery. Do not mark the objective complete before that
independent reconciliation. No extra closure PR follows stable publication.

### Handoff Notes

Use current plan and verified repository/private artifacts rather than replaying
prior command transcripts. Private ledger/state locators and any source-bearing
debug artifacts are deliberately absent from this public plan. Root maintains
the exact current queue item, review allowances and cleanup ownership as work
progresses. Future unselected libraries need concrete activation evidence.

## Recently Completed

- [x] 2026-10-31: Completed Toolkit 0.14.4 systematic DLP corrections and diagram source validation; [full archived plan](docs/engineering/execution_history/plans/2026-10-31-toolkit-0-14-4-systematic-dlp-corrections-and-diagram-source-validation.md).
- [x] 2026-10-30: Completed Toolkit 0.14.3 source-aware DLP and private corpus audits; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-3-source-aware-dlp-and-private-corpus-audits.md).
- [x] 2026-10-30: Completed Toolkit 0.14.2 compact bootstrap, diagram-only reports and DLP corrections; [full archived plan](docs/engineering/execution_history/plans/2026-10-30-toolkit-0-14-2-compact-bootstrap-diagram-only-reports-and-dlp-corrections.md).
- [x] 2026-10-29: Completed Toolkit 0.14.1 grouped diagrams and private debug qualification; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-1-grouped-diagrams-and-private-debug-qualification.md).
- [x] 2026-10-29: Completed Toolkit 0.14.0 range identity, typed diagrams, DLP qualification and Python 3.15; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-0-range-identity-typed-diagrams-dlp-qualification-and-python-3-15.md).
- [x] 2026-10-25: Completed Two-day GitHub Actions retention; [full archived plan](docs/engineering/execution_history/plans/2026-10-25-two-day-github-actions-retention.md).
- [x] 2026-10-23: Completed Toolkit 0.13.1 partial review of changes containing gitlinks; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-1-partial-review-of-changes-containing-gitlinks.md).
- [x] 2026-10-23: Completed Toolkit 0.13.0 protected default-policy fallback for single-MR review; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-0-protected-default-policy-fallback-for-single-mr-review.md).
