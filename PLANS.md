# Execution Plans

## Active Plan: Correct grouped diagram requests and verify real-model delivery

plan_schema_version: 2
Status: active
Owner: root
Last Updated: 2026-10-29
Release classification: release-required, target v0.14.1 for the grouped diagram request correction; if runtime correction proves unnecessary, deliver only the instruction/evidence documentation PR without release artifacts.

### Goal

Diagnose and correct the grouped diagram request protocol, close the missing real-model acceptance evidence with the one additionally authorized own-tool review without an aggregate token ceiling, and deliver the necessary correction through protected PRs. Release v0.14.1 only when runtime changes are needed; documentation-only correction does not publish artifacts.

### Plan Origin

`direct_execution`

### Requested Scope

Diagnose the retained two self-reviews and the entire upstream selection/group/plan/main/round/aggregation route before choosing a correction. Assess whether one designated group can obtain sufficient bounded immutable cross-group context; a group-local view is not an accepted basis for a whole-range summary. Evaluate explicit output instructions and closed run-owned status across fresh round contexts without another model pass or weakening the collector. Correct engineering instructions so a local acceptance run with budget exhaustion warnings is not accepted even when native coverage is complete. Reserve exactly one additional successful `ocr-ci review --local` with ChatGPT high, diagram mode local and aggregate token budget zero for the finished qualified candidate. Preserve prior evidence; absence or insufficient cross-group context remains unfinished acceptance.

Follow the usual signed plan/draft feature PR, local implementation and per-commit self-review, final quality/security and own-tool gates, protected feature/development verification, then conditional release PR. That release PR owns plan archival/reset; external publication/site reconciliation follows without a later toolkit closure PR. Coordinate site changes only after implementation is verified and before the release-branch push.

### Requirement Traceability

| Requirement | Outcome | Queue | Status |
| --- | --- | --- | --- |
| REQ-001 | Preserve published v0.14.0 identity and truthful prior evidence; no retroactive reclassification of the earlier successful runs | WQ-01 | done |
| REQ-002 | Verify qualified OCR, auth/model readiness, physical private artifact paths and supported flags before the additional review | WQ-01, WQ-05 | in_progress |
| REQ-003 | Execute the reviewed range through the final corrective candidate with diagram local, ChatGPT high and unlimited aggregate tokens, within the one additional successful-run authorization | WQ-05 | pending |
| REQ-004 | Inspect terminal result, range, complete coverage, warnings, findings and failed auxiliary reads; classify and verify any findings separately | WQ-05 | pending |
| REQ-005 | Require actual real-model submission, admitted graph, source references and private Mermaid/text before claiming the graph acceptance gap closed | WQ-05 | pending |
| REQ-006 | Reconcile resulting evidence and correction classification; do not release artifacts for documentation-only work | WQ-06, WQ-07 | pending |
| REQ-007 | Qualify complete selection/group/round/context handoffs before choosing an actionable output-call protocol; preserve cross-group context, conflict/budget/DLP and optional-only failure behavior | WQ-02, WQ-03 | in_progress |
| REQ-008 | Treat budget-exhaustion warnings as unsuccessful local engineering acceptance and default own-tool qualification to unlimited aggregate tokens | WQ-03 | pending |
| REQ-009 | Validate actual prompt/MCP/collector/report handoffs, repeated rounds and non-owner groups; complete final quality and one security scan of the correction diff | WQ-03, WQ-04 | pending |
| REQ-010 | Reconcile public contracts, decision flow, evidence matrix, changelog and inactive backlog only where changed; preserve historical facts | WQ-03, WQ-06 | pending |
| REQ-011 | Complete protected feature/development verification and conditional v0.14.1 release PR with full plan archival/reset and no later closure PR | WQ-06, WQ-07 | pending |
| REQ-012 | Verify stable receipts/registries/installs/tag, issue/milestone, site update and synchronized clean main after a required release | WQ-08; Post-Close Delivery | pending |

### Explicit Non-Goals

No tag, distribution, immutable Release or receipt rewriting; no automatic new version merely to repair historical wording; no invented diagram, injected response in the actual model acceptance run, hidden extra model pass, upstream OCR modification, global DLP relaxation, new diagram-mode setting or substitution of synthetic output for a natural-model result. No repeat aggregate scan of unchanged 0.14.0 runtime; a new correction diff has its own single security review. No additional successful model review beyond the one just authorized. No original-release housekeeping PR.

### Constraints

- The published baseline is immutable b81b4a15bb5212ece78c398665a9d576537ab404..ab2f412600042df56093a9281cb310d2b6780258. The owner's subsequent corrective-delivery objective extends the final acceptance head to the finished correction so the one authorized run covers the fix as well. Record exact SHA endpoints before launch.
- Use checksum-verified native OCR 1.13.3 and the existing toolkit launcher, MCP output collector, admission, cleanup and report path. The actual acceptance run uses no test doubles or ad-hoc prompt injection; focused deterministic tests may replace only the far-side model.
- Use `OCR_REVIEW_DIAGRAM_MODE=local`, explicit ChatGPT model/high and native `--max-tokens-budget 0`. This aggregate default is already unlimited in the public GitLab example; do not conflate it with per-request completion or per-group context limits.
- One additional successful review was explicitly approved after the original two-run allowance was exhausted. Infrastructure or failed attempts require terminal evidence before any retry and do not become successful acceptance.
- Keep credentials in the native private registration. Use the normal isolated session/link lifecycle; never read or copy credential contents. Outputs remain in a fresh physical private directory outside tracked source.
- Preserve checkout HEAD, index and unrelated files. Reporting and cleanup failures, incomplete native state, warnings and material failed auxiliary reads must be assessed before completion claims.
- Optional diagram absence never changes the user's finding outcome or approval contract. That runtime rule does not waive this separate graph acceptance criterion.
- A designated group is only a proposed coordination mechanism. Do not implement it until actual native protocol evidence shows how it obtains sufficient cross-group immutable context within bounds. Ownership cannot manufacture graph completeness or relax the independent selected-file review. Unexpected submissions still pass untrusted admission and conflicts never select a winner.
- Closed submission status contains no candidate labels, references or private content. It remains separate from evidence completeness and cannot create tool, publication or approval authority. Its read failures must leave mandatory evidence usable.
- If a correction is needed, record its exact boundary, tests and release classification before changing code. Already successful unchanged checks remain applicable.

### Inputs And Sources

- Owner feedback on the premature acceptance claim and explicit authorization for one additional unlimited-token review.
- Published v0.14.0 and its immutable v2 receipt; the archived original release plan remains a prepublication historical record.
- Retained private Markdown/JSON/debug artifacts from the first two own-tool reviews.
- Current development/local/diagram guides, project principles, release owner and installed planning lifecycle.
- Qualified upstream OCR 1.13.3 source at 375f64cd6f67a48a135da83cfcf59c52669a09cb, including review-group prompts and MCP registration; these are diagnostic evidence, not authority to alter toolkit policy.

### User Decisions And Answers

The owner challenged the completed acceptance claim because the first review had budget warnings and neither real self-review generated a graph. The owner explicitly approved one additional successful own-tool run with diagram local, ChatGPT high and no aggregate token limit, then requested a sustained objective covering diagnosis, necessary corrections and complete delivery. Reserve that run for the final corrective candidate. This extends the earlier two-run allowance without retroactively changing their recorded terminal states.

The owner clarified that a budget-exhaustion warning counts as unsuccessful local engineering acceptance and that instructions must say so. This acceptance rule does not change native JSON history or silently reset the consumed run allowance. The owner also made release conditional: runtime changes use the corrective release path; instruction-only changes use an ordinary documentation PR with no release artifacts.

### Completed Baseline State

Main and origin/main are clean at ab2f412600042df56093a9281cb310d2b6780258, also the peeled v0.14.0 tag. Stable publication, registries, supported-Python installs, provenance, immutable Release/receipt and tracked issue/milestone closure were independently verified. No corrective runtime change exists.

The original first review completed 46/46 selected items with four aggregate-budget grace warnings and zero findings. The second completed the same selected set without warnings or tool failures, used 1987605 tokens under a 3000000 cap, and found one release-matrix bug that was corrected before publication. Both recorded zero diagram-tool calls and not-generated. Controlled native/installed graph tests exist but do not substitute for this missing natural-model acceptance result.

### Current Work Queue

| Queue | Requirements | Exit evidence | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-001, REQ-002 | Source/artifact diagnosis, binary checksum, model discovery, local preflight and reviewed initial plan/draft | in_progress |
| WQ-02 | REQ-007 | Complete source/controlled-native analysis of selection, grouping, group-local plans/main, cross-group context, compression, rounds, failures and aggregation; reviewed design decision | in_progress |
| WQ-03 | REQ-007, REQ-008, REQ-009, REQ-010 | Scoped implementation, instructions/public docs, real boundary regressions and self-reviewed logical commits | pending |
| WQ-04 | REQ-009 | Aggregate self-review, final quality/installed/native checks and one correction-diff security scan | pending |
| WQ-05 | REQ-002, REQ-003, REQ-004, REQ-005 | One additional actual own-tool run, exact result/graph assessment and focused correction validation | pending |
| WQ-06 | REQ-006, REQ-010, REQ-011 | Final feature push, protected CI/merge, development publication and final site-contract handoff | pending |
| WQ-07 | REQ-006, REQ-011 | Conditional v0.14.1 markers/authorization/notes/pins and plan archive/reset in release PR, or no-release documentation delivery | pending |
| WQ-08 | REQ-012 | Required stable external readback, issue/milestone/site reconciliation and clean main without another closure PR | pending |

### Locked Decisions

The unlimited product default needs no change. The failed engineering acceptance warning came from an explicit operator cap. Source inspection confirms that OCR 1.13.3 injects the same background into every group and rebuilds round contexts; it does not invoke optional MCP tools automatically. Making all groups submit is not a valid correction, but designating one group alone is also insufficient. The owner explicitly requires comprehensive grouping/context analysis before the actual-model run. No runtime protocol design is accepted yet.

Source facts at immutable OCR 1.13.3:

- Selection seals the native reviewed set before semantic grouping; deleted files are retained as context, not reviewed items. Grouping uses path/status/change counts, with no diff content and no MCP tool request; it can fall back to per-file groups and split oversized groups.
- Plan is optional and group-local. Its request has no actual tool definitions; tool documentation appears only as prompt text. There is no guaranteed global plan or final summary-model phase to reuse.
- Main receives full diffs for its own group and metadata for other kept files. It may obtain other file diffs through the shared frozen `file_read_diff` map; `path_array` can request more than one file. That map is built before selection from the same parsed range, so context access must not accidentally preload excluded files.
- Every review round builds new messages. Shared status can prevent repeat submissions, but it does not deliver source context or prove completeness. Native compression can summarize prior tool results; selected-file completion does not establish graph-context coverage.
- Findings aggregate after concurrent subtasks without another model stage. Automatic graph-fragment union, forced single-group reviewing and a new summary-model pass remain outside the approved correction until explicitly reconsidered.

| Candidate | Cross-group consequence | Current disposition |
| --- | --- | --- |
| Explicit tool call in every group | Competing candidates and repeated rounds can exhaust or invalidate the collector | rejected |
| One owner using only its initial group prompt | Other-file metadata is insufficient for behavior/interactions | rejected |
| One owner with explicit bounded immutable cross-group acquisition and shared status | Potentially fits the existing run; must prove context delivery, filters, limits/compression and optional failure isolation | under analysis |
| Automatic union of per-group graph fragments | Structural merging cannot prove semantic consistency or complete interactions | rejected under existing constraints |
| Separate whole-range summary model phase or forced global review group | Changes the approved model-pass/engine contract | not authorized |

### Verification

- Binary: match the qualified 1.13.3 SHA-256, then verify account-specific model discovery and local structural preflight with API-only variables removed from the child environment.
- Invocation: exact immutable range, public local flags, fresh physical private paths, native authentication, high reasoning, aggregate budget zero, unchanged production runtime and collector.
- Result: successful toolkit exit and report, exact native identity, selected/completed/reused/failed/waived, warnings, DLP and every finding; inspect native raw result for material auxiliary failures.
- Graph: count actual output calls, inspect admitted state, compare Mermaid and complete text with the typed candidate and immutable source references. A not-generated, invalid or not-applicable result does not prove this graph acceptance criterion. Deterministic grouped/repeated-round peers verify producer/consumer wiring separately from the one actual-model run.
- State: preserve HEAD/index and plan bytes through review, remove owned temporary auth links, and leave no active process. Review any correction before a commit; no repeated broad scan or unrelated quality expansion.

### Latest Validation Results

2026-10-29 read-only diagnosis reconfirmed both prior native terminal states as complete, 46 completed and zero failed/reused/waived items each. The second has no warnings; neither run called the diagram tool. Public configuration and numeric qualification preserve omitted/zero aggregate budget as unlimited. The qualified OCR binary SHA-256 is fa9b8530c0a35e6106a9ab2e81c21d98ef26d3f31c1f39ad3ef4c2528047c4f4. No additional model review has started. Recovery allowance: zero of one additional successful run used.

Native model discovery lists gpt-6.1-sol; local ChatGPT preflight passes with the qualified binary and API-only variables removed from the child environment. Upstream immutable source confirms direct background substitution in main-task prompts, full selected non-deleted inventory plus deletion context in other_changed_files, per-group completion and fresh round messages. The original corrective verification plan and active pointer are materialized locally. No implementation commit, feature push or additional model review has occurred.

Initial plan critique identified eight-submission and repeated-round risks. Owner feedback then exposed the missing cross-group context proof; the proposed one-group design is withdrawn as a locked solution. The complete upstream route is being examined before implementation. MCP transport would own any optional status I/O, while pure evidence summaries and reporting remain separate. Mandatory evidence must stay usable on optional faults, and the collector keeps its conflict/hostile-input rules. Queue mappings list every requirement explicitly. The single actual-model run is unspent and reserved for a fully qualified design.

### Risks And Recovery

Do not turn optional product behavior into a false acceptance claim. A repeated graph omission leaves the graph gap unresolved and requires source-backed diagnosis before any further request. Provider failure or capacity limits preserve private evidence and do not justify changing model, credentials or budget silently. A real defect receives a narrow reproducer and classified correction; immutable 0.14.0 artifacts stay unchanged.

### Resume Point

WQ-02: finish source and controlled-native cross-group context analysis, including selected/deleted/excluded files, grouping fallback/splitting, optional group plans, fresh rounds, compression/tool limits and failure accounting. Choose a design only after its global context and optional failure boundaries are proved. Re-review the initial plan/index before its signed draft push; no implementation or real-model run has started. Keep release conditional on runtime scope.

### Plan Fidelity Check

- [x] The added authorization, exact range and successful-run limit are explicit.
- [x] Code-review completion and real-model graph acceptance have separate criteria.
- [x] Budget controls, auth isolation, publication boundaries and diagnostic hypotheses are distinguished.
- [x] Every requirement has an ordered queue item and verification owner.
- [x] Conditional release, owner clarification, repeated-round behavior and final external/site delivery are represented.

### Reconciliation Check

- [x] Current main/tag state and retained results agree with the baseline.
- [x] Prior acceptance overclaim is acknowledged without changing historical artifacts.
- [ ] Final additional-run result and acceptance/correction disposition agree.

### Closure Gate

- [ ] The authorized run has terminal evidence and every result/finding/failed-read assessment is complete.
- [ ] Real-model diagram acceptance is proved, or a genuine remaining gap is explicitly retained as unfinished work.
- [ ] Repository state, private cleanup, evidence and next action agree with the final disposition.
- [ ] Required feature/release delivery is complete or truthfully transferred to Post-Close Delivery at the release-PR boundary.

### Post-Close Delivery

Runtime correction uses protected v0.14.1 delivery. The release PR archives the complete plan with required external publication pending; afterward verify registries, installs, provenance, annotated tag, immutable Release/receipt, tracked issue/milestone, site content/version and clean main. No later toolkit closure PR. Documentation-only work instead closes through an ordinary no-release PR and publishes no distribution. Original v0.14.0 artifacts/receipts stay immutable; closure cannot imply graph creation without an actual-model result.

### Handoff Notes

Root owns the corrective verification. Private prior-run evidence remains outside public source. No subagent or separate model pass is required for the authorized review. Preserve the original two successful runs plus the separate one-run extension in all status reporting.

## Recently Completed

- [x] 2026-10-29: Completed Toolkit 0.14.0 range identity, typed diagrams, DLP qualification and Python 3.15; [full archived plan](docs/engineering/execution_history/plans/2026-10-29-toolkit-0-14-0-range-identity-typed-diagrams-dlp-qualification-and-python-3-15.md).
- [x] 2026-10-25: Completed Two-day GitHub Actions retention; [full archived plan](docs/engineering/execution_history/plans/2026-10-25-two-day-github-actions-retention.md).
- [x] 2026-10-23: Completed Toolkit 0.13.1 partial review of changes containing gitlinks; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-1-partial-review-of-changes-containing-gitlinks.md).
- [x] 2026-10-23: Completed Toolkit 0.13.0 protected default-policy fallback for single-MR review; [full archived plan](docs/engineering/execution_history/plans/2026-10-23-toolkit-0-13-0-protected-default-policy-fallback-for-single-mr-review.md).
