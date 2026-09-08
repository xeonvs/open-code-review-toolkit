# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Toolkit 0.9.2 — local provider, diagnostics and OCR controls

- **Status:** active
- **Plan Origin:** plan_mode_approved
- **Release classification:** release-required; stable delivery release-deferred
- **Target stable version:** 0.9.2
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
Local delivery is tracked by #182; both issues belong to milestone v0.9.2.
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
| WQ-01 | in_progress | Plan and milestone recorded; #181/#182 assigned; planning push/Draft pending |
| WQ-02 | pending | Shared report model/formatting and local provider |
| WQ-03 | pending | Explicit local preflight/review and end-to-end path |
| WQ-04 | pending | Fresh private debug bundle and actual decision journal |
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

#### Validation And Commit Gates

Before each logical signed commit: format changed Python, targeted tests,
complete diff/self-review, repository Ruff format check and git diff --check.
Final gate: quality with scoped coverage floors, lock, manifest/evidence,
Towncrier, package/installed wheel and sdist tests, pinned Gitleaks for tree and
complete feature history. Hosted checks bind the exact final head.

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

Materialize tracking and signed planning Draft, then implement WQ-02. Keep
the plan active through deferred stable delivery and record precise checkpoints.

#### Closure Gate

- [ ] All scoped implementation and required local verification complete.
- [ ] Full self-review and signed commits; current Draft checks green.
- [ ] Local and remote heads agree, tree clean, temporary owned data cleaned.
- [ ] External qualification checklist recorded; issues/milestone remain open.
