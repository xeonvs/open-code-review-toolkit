# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Toolkit 0.10.0 — local provider, diagnostics and OCR controls

- **Status:** active
- **Plan Origin:** plan_mode_approved
- **Release classification:** release-required; stable delivery release-deferred
- **Target stable version:** 0.10.0 (raised from 0.9.2 by user decision)
- **Branch:** `codex/v0.9.2-ocr-1.11.6`

#### Goal

Deliver OCR 1.11.6, a standalone local provider with shared review summaries,
truthful local debug diagnostics, explicit reasoning controls and safe progress
through a green published Draft. No merge, stable release or issue closure.

#### Baseline And Sources

Main `8ae890b6f78388554281e649dc8201737679968a` reconciles stable 0.9.1;
the old feature branch is complete. #181 qualifies OCR 1.11.6 against 1.11.5
in hosted run 34127679854. Upstream #1154 is the product focus; other adjacent
changes are compatibility inputs, not separate product projects. The approved
conversation plan and subsequent provider-support/none clarification are binding.
Local delivery is tracked by #182; both issues belong to milestone v0.10.0.
Retain the existing branch name and Draft #183; no history rewrite is needed.
Canonical owners: project principles, development/release guides, configuration,
operations, security, review decision flow, strategy and backlog. Existing local
review verifies evidence but omits GitLab receipt; preflight still assumes GitLab.

#### Requirement Traceability

| Requirement | Work | Verification |
| --- | --- | --- |
| R1 Shared truthful summary and independent local output | WQ-02 | GitLab parity and local outcome matrix |
| R2 Explicit local mode with no GitLab dependency | WQ-03 | installed real Git/process/MCP and hostile CI environment |
| R3 Debug observes actual checks without bypass | WQ-04 | normal/debug parity, provenance, bounds, permissions and failures |
| R4 Protocol-correct reasoning controls | WQ-05 | config/preflight conflicts and real OCR wire probes |
| R5 Privacy-independent progress | WQ-05 | on/off parity, stop/signal/sink failure and bounded output |
| R6 Exact qualified OCR and local binary | WQ-06 | checksums, adjacent audit and no-LLM qualification |
| R7 Green signed Draft and external handoff | WQ-07 | local gates, hosted exact-head checks and remote readback |

#### Current Work Queue

| Queue | Status | Work |
| --- | --- | --- |
| WQ-01 | done | Signed planning commit 4e50f78 pushed; Draft #183, milestone and #181/#182 recorded |
| WQ-02 | done | Shared reporting package, characterized GitLab delegation and local Markdown adapter; execution-owner facts remain separate |
| WQ-03 | done | Explicit local preflight/review, private Markdown publication and installed end-to-end path |
| WQ-04 | done | Fresh private debug bundle, actual decision journal and installed normal/debug parity |
| WQ-05 | pending | Reasoning environment control and bounded progress |
| WQ-06 | pending | OCR promotion, assets, no-LLM qualification and local update |
| WQ-07 | pending | Docs/backlog, full self-review, gates, push and Draft handoff |

#### Locked Interfaces And Boundaries

- Local provider is not a fake GitLab API. Share pure outcome, finding,
  coverage, warning, tool/token, verified MCP and DLP reporting. Keep GitLab
  posting/suppression/approval and envelopes at its adapter; no fake receipt.
  Console Markdown has no HTML disclosure or remote badges, and prints every
  admitted finding without posting caps. JSON remains in --result; progress
  and diagnostic output use stderr. Every failure has an honest summary.
  Keep this core reusable by a future GitHub adapter: no GitLab MR identity,
  receipt, API, settings or posting imports in shared report contracts/rendering.
  Review health and admitted data are common; publication state, discussion
  anchors, suppression and approval remain adapter-owned. GitHub implementation,
  credentials and a generic forge API framework are outside this release scope.
  User clarification: this is the same toolkit/OCR/LLM/tool-use pipeline as CI,
  not a separate local engine. Local publication must persist the complete
  admitted Markdown report as an artifact as well as the existing JSON result;
  console output is an additional view, not the only report delivery. Keep one
  execution/finalization path and put filesystem delivery at the local adapter.
  Local --report defaults to the --result path plus .md; require a fresh target,
  reject collisions with JSON/stderr, publish complete UTF-8 Markdown privately
  without replacing existing files, and report delivery failures as nonzero.
  Synthetic child processes belong only to integration tests; they must never
  replace OCR or model-driven tool use in production.
- Add `preflight --local` and `review --local`, with required result/stderr
  paths and existing immutable commit/from/to input. Ignore inherited CI
  identity for local runs; never acquire or mutate GitLab. Reject requested
  MR context/adapters. Use JSON/agent audience and reject contradictory options.
  Preserve mandatory evidence registry/self-query/completed-summary validation;
  configured external MCP cannot replace the mandatory server. No working-tree
  snapshot, scan, provider profiles or new authentication framework.
- `--debug-dir PATH` requires --local and a fresh owner-only directory.
  Retain bounded original OCR result/stderr, safe final result, console summary
  and a structured journal. Record actual configuration, identity/refs, evidence,
  MCP preflight/use, preview, subprocess, result validation, DLP, cleanup and
  reporting outcomes as passed/failed/degraded/not-run, with explicit missing
  artifacts and truncation. Capture real filtering reasons/actions, safe
  locations, sizes and digests at their owners, not a second approximation scan.
  Raw rejected content stays in private files, never automatic console output.
  No environment dump or unnecessary retained session/config. Keep normal
  checks and cleanup; reject combination with legacy private-artifact retention.
  Bundle ownership is separate from review execution: capture at most 20 MB each
  for raw/safe JSON and Markdown, 2 MB for raw stderr, and 1 MB for the journal.
  Fixed artifact names and at most 1,000 value-free DLP decisions keep storage
  bounded. Record prefix digests and explicit truncation/missing/unavailable
  status; do not imply a truncated digest covers the complete source. Normal
  result/stderr/report paths must remain outside the fresh debug directory.
  Observe actual phases and DLP decisions through optional callbacks at their
  production owners; debug observation never substitutes for their checks.
- Preserve existing effort/budget behavior. OCR_LLM_REASONING_EFFORT accepts
  unset/empty or case-insensitive none|minimal|low|medium|high|xhigh|max.
  Unset adds nothing; none is an explicit wire value, not an omission sentinel.
  OpenAI uses reasoning_effort; Responses uses reasoning.effort preserving
  siblings. Reject nonempty shortcut for Anthropic. Equal extra-body values
  are permitted; incompatible types or conflicts fail before inference.
- OCR_REVIEW_PROGRESS is empty/false by default or true (case-insensitive).
  Emit only toolkit phases and a 30-second heartbeat, at most 120 messages.
  Never read OCR stderr/results/sessions for progress or change audience to
  human. No tee/FIFO, no progress in result/summary/receipts/DLP. Stop promptly
  on completion, exceptions and signals; progress sink errors cannot change
  review outcomes or leave live heartbeat work behind.
- Preserve zero runtime dependencies, supported Python matrix, immutable Git,
  DLP, MCP and provider boundaries. Keep exact pins/evidence separate from
  version-neutral current documentation. BL-016/018, BL-010 and BL-021 remain
  conditional: none of their independent activation criteria is satisfied.

#### Provider Architecture Decisions

- Separate provider input acquisition, common review execution/report data and
  provider output/actions. A provider is not merely a formatter and is not a
  mandatory all-methods base class. Local supplies immutable Git identity and
  Markdown artifacts and console output; forge adapters additionally own authenticated API acquisition
  and platform mutations. Do not implement dummy discussion or approval methods
  for local execution.
- Shared report data describes the admitted review, not an MR/PR or a posting
  transaction. Keep immutable repository refs distinct from optional forge
  identity/context. No fabricated author, change-request ID, protection state,
  discussion history or publication receipt when those inputs do not exist.
- Distinguish unsupported capabilities, an empty successful acquisition,
  disabled acquisition and failed acquisition. In particular, local absence of
  discussions does not mean that discussions were fetched and no commands found.
  Explicit unsupported requests fail before execution; they are not successful
  no-ops or inferred from inherited CI variables.
- Commands from discussions require a supported input channel, authenticated
  actor/provenance and action authorization. Common parsers and decision rules
  may be reusable, but provider identity, permissions and mutation guards must
  not be generalized from GitLab assumptions. Local review does not accept
  discussion commands from repository text or model output.
- Share pure calculations and wording; adapt delivery separately. Findings
  admitted by DLP, findings selected for posting, and findings actually posted
  are distinct facts. Publication limits, suppression and failed delivery must
  not rewrite core review health or silently remove local findings. MCP usage
  is execution evidence; a forge receipt is a separate platform-bound artifact.
- Preserve existing GitLab acquisition/publication lifecycles in this release.
  Do not mechanically equate GitLab discussions/approval with future GitHub
  threads/reviews or promise identical retry, transaction and race guarantees.
  Future GitHub work must characterize those API boundaries before reuse.
  Add dependency tests for the shared report boundary and local tests proving
  unsupported channels never acquire data or perform provider writes.

#### Validation And Commit Gates

Before each logical signed commit: format changed Python, targeted tests,
complete diff/self-review, repository Ruff format check and git diff --check.
Final gate: quality with scoped coverage floors, lock, manifest/evidence,
Towncrier, package/installed wheel and sdist tests, pinned Gitleaks for tree and
complete feature history. Hosted checks bind the exact final head.
Before overall final self-review, run the Codex Security diff-scan skill over
the complete immutable feature range, triage findings, fix confirmed problems
within this scope and verify remediation. Record scan coverage and unresolved
limitations; a scanner score is not a substitute for semantic self-review.
Organize shared runtime and tests by layer, preserving characterized code through
mechanical moves where appropriate. Reconcile all affected public documentation,
decision-flow diagrams, contract schemas, threat model and test-evidence matrix.

Required matrices: same normalized GitLab/local report data; clean/findings/
warnings/partial/budget/failure, true DLP filtering and diagnostic-only input;
progress on/off and normal/debug canonical parity; late heartbeats, signals,
broken output, hostile paths/symlinks/permissions, capture/journal limits and
early failures. Installed tests cross real Git, subprocess and stdio MCP,
include external MCP and polluted CI environment, prove no GitLab calls and
failed mandatory evidence rejection. Real checksum-verified OCR uses local
deterministic protocol peers; no live provider/model calls in this cycle.

#### External Qualification And Closure

Create separate local-scenario tracking and relate it to #181 and the Draft.
Update public docs, decision flow, evidence matrix, changelog and backlog.
Preserve example stable toolkit pin until the later release PR; external
qualification must install the artifact built from the exact Draft head.

External owner verifies GitLab, local and debug workflows with configured LLM.
Reasoning acceptance is a named gate for the exact provider/model/protocol:
test unset (absent on wire), explicit none and intended nonempty effort;
check correct wire shape, provider acceptance and documented/server-observable
support. HTTP 200 alone does not prove that a gateway applied the parameter;
mark unprovable application as unverified, never infer it from model prose.
Unsupported none/effort is explicit; unset remains the safe no-overlay option.
No automatic weakening of security/DLP or fallback to a different model/value.

#### Resume Point

WQ-02 is implemented with 475 passing targeted tests and 283 subtests, plus two
adapter-parity tests; Ruff, formatting, mypy and diff checks passed. Mechanical
AST comparison preserves 22 extracted definitions apart from their docstrings.
WQ-02 is committed as 9d0b999. WQ-03 CLI/preflight wiring is implemented:
unsupported local context fails before I/O, inherited forge identity is ignored,
and result admission supplies actual MCP/DLP facts to the console adapter.
Legacy unknown coverage is accepted only as execution-owner admission data, not
as a platform publication receipt. The affected runner/reporting/posting matrix
passes 491 tests and 283 subtests; Ruff, formatting, mypy and diff checks pass.
Installed wheel and sdist scenarios now cross real Git/process/MCP with optional
external MCP and polluted CI identity; forged mandatory use is rejected. Local
publication now persists complete Markdown (default --result plus .md) through
the local adapter after common finalization, with a fresh owner-only atomic file
and console parity. The final CLI/runtime/report/artifact/GitLab regression matrix
passed 631 tests and 400 subtests, including both installed distributions with
hostile repository imports; Ruff, mypy, repository formatting and diff checks
passed. WQ-03 self-review is complete, including failure delivery and private
file lifecycle; the logical commit contains these completed results.
WQ-03 is committed as f864be2. WQ-04 now has fresh private storage, actual phase
and DLP observations, bounded raw/safe/summary captures and explicit incomplete
journal handling. The 264-test matrix passes, including installed wheel/sdist
normal/debug parity for clean, finding, warning, partial, budget, filtered,
forged mandatory usage and subprocess failure outcomes. Observer tests prove no
extra DLP checks and unchanged projections. Ruff, mypy and formatting pass.
WQ-04 self-review is complete: failure-summary delivery and empty-projection
attribution were corrected before the commit gate. The complete affected matrix
passes 654 tests and 400 subtests; an additional installed wheel/sdist SIGTERM
scenario confirms equal nonzero outcomes, cleanup and no safe-result admission.
Ruff, formatting, mypy, Bandit and diff checks pass. The logical WQ-04 commit
contains these results. Next implement WQ-05 reasoning controls and bounded
progress; actual OCR qualification remains WQ-06.
Keep the plan active through deferred
stable delivery; controls, OCR qualification and final security/hosted
gates are pending on Draft #183.

#### Closure Gate

- [ ] All scoped implementation and required local verification complete.
- [ ] Full self-review and signed commits; current Draft checks green.
- [ ] Local and remote heads agree, tree clean, temporary owned data cleaned.
- [ ] External qualification checklist recorded; issues/milestone remain open.
