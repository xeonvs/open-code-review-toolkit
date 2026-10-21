# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### v0.11.4 — OCR 1.13.0–1.13.2 and external-tool context

- **Goal:** qualify the adjacent OCR chain, improve MR-to-tool discoverability,
  and complete protected stable publication and external reconciliation.
- **Plan Origin:** `plan_mode_approved`; **Status:** active.
- **Release classification:** release-required; stable 0.11.4; next development 0.12.0.
- **Baseline:** clean synchronized main `d8354305c9dba42865205d13cc2ace45654e4e4e`;
  stable/reconciled 0.11.3, recommended/local OCR 1.12.13; no open issues or PRs.
- **Sources:** approved conversation plan; development/release guides; project
  principles; M7 federation, MR-context and review-flow owners; upstream exact tags.

#### Requirements and locked decisions

- REQ-001: qualify 1.12.13 → 1.13.0 → 1.13.1 → 1.13.2; upper bound fixed at
  v1.13.2. Review config/provider/auth isolation, deleted-file tools and shared
  grace-round behavior. Scan-only, ACP, npm and extension changes are unconsumed.
- REQ-002: extend existing max-tools probe for successful/unsuccessful grace
  completion and preserved limit warning from 1.13.1. Extend selection/Rules for
  PowerShell, Nushell, shader and OpenTofu from 1.13.2, preserving prior epochs,
  including the previously allowed PowerShell script with default rule.
- REQ-003: one Linux amd64 qualification per candidate in local Docker using
  verified image/binary identities, pinned uv and locked dependencies. Preserve
  historical evidence bytes. Fix owning failures and repeat only affected probes.
  Create honest local-qualification issues and use existing cumulative promotion
  with explicit source conclusions. No fabricated hosted-run provenance.
- REQ-004: recommend/pin 1.13.2; supported 1.12/1.13, deprecated 1.11, reject
  below 1.11 and unqualified patches. Install verified Darwin arm64 1.13.2 and
  atomically replace only the confirmed old OCR executable.
- REQ-005: improve bootstrap navigation to MR context and relevant allowlisted
  external tools. Preserve required evidence instructions, an opaque direct MR
  record pointer and external-capability availability through clipping. Keep
  complete tool definitions in the existing MCP inventory. OCR selects calls.
- REQ-006: preserve mode off by default, DLP, frozen tool/schema allowlists,
  argument authorization, receipts and approval gates. No tracker-specific
  client, project-key regex, automatic acquisition loop or new public schema/CLI.
  Use only synthetic examples; user-private identifier examples are not retained.
- REQ-007: self-review logical slices, independent aggregate architecture and
  regression review, focused tests, one full local quality run; rerun affected
  checks only. CI owns wheel/sdist install and publication verification.
- REQ-008: signed plan-only push, then local work until completed feature push;
  draft feature PR → protected merge → verified TestPyPI development → separate
  draft release PR → protected merge → stable publication/readback → milestone
  closure → one no-release documentation closure PR → clean synchronized main.
- REQ-009: verify current engineering-toolkit installation and repository
  instructions through the latest skill's report-first path; apply necessary
  reviewed instruction/documentation improvements without replacing local release
  ownership. Use tgrep appropriately, delegate independent tasks, split logical
  commits, review each before commit and review the aggregate final diff.
- REQ-010: review all backlog, diagrams, milestone/status owners and user
  documentation for consistency with implementation and this release; correct
  substantive findings while preserving historical receipts and established M7.

#### Ordered work queue and verification

| Queue | Requirements | Work and acceptance | Status |
| --- | --- | --- | --- |
| WQ-01 | REQ-008 | Milestone, signed plan commit, staged/tree/history Gitleaks and plan-only push | done |
| WQ-02 | REQ-001–003 | Source review, epoch/probe changes and focused adversarial tests | in_progress |
| WQ-03 | REQ-005–006 | Bootstrap navigation, bounded clipping and operator documentation | in_progress |
| WQ-03a | REQ-009–010 | Latest engineering-workflow report; backlog/diagrams/status/user-doc audit and necessary reviewed corrections | done |
| WQ-04 | REQ-003–004 | Local Docker qualification, issues, promotion and verified local OCR replacement | pending |
| WQ-05 | REQ-005–007 | One targeted real MCP/gateway/model-peer integration with synthetic MR context; aggregate review and full quality | pending |
| WQ-06 | REQ-007–008 | Signed completed feature, draft PR, exact-head required checks and all Linux gates, merge and dev publication | pending |
| WQ-07 | REQ-008 | Release metadata/epoch/Towncrier/notes/archive, draft release PR, checks, protected merge | pending |
| WQ-08 | REQ-008 | Registry/provenance/install jobs and immutable six-asset Release/receipt API readback, workflow issue closure and milestone closure | pending |
| WQ-09 | REQ-008 | One documentation-only reconciliation PR, dev verification, clean synchronized main | pending |

Focused cases cover grace completion/non-completion, warnings, selection/Rules
epochs, support-window gates, promotion; MR title-only/description-only/multiple
synthetic references, absent/degraded/off context, no tools, large inventory and
injection/DLP boundaries. The controlled model peer must read context through
production evidence MCP before using the real gateway; this proves transport and
availability, not natural real-model choice. Keep unused versus denied/failed
tools distinct. Linux Python 3.12 gates the parallel remaining CI matrix.

#### Risks, recovery and evidence

- Project-specific non-use cannot be diagnosed conclusively without its trace;
  confirmed generic gaps are indirect MR navigation and capability clipping.
- Preserve historical evidence and configured policy; no security weakening to
  accept a candidate. A failed candidate blocks promotion until its cause is fixed.
- Current host/local Docker and normal GitHub CI only; stop dependent work and
  report a local blocker rather than switching environments.
- Long commands keep private bounded logs, process identities and terminal exit
  status. Clean only owned resources. No duplicate published-artifact installs.
- Latest validation: plan staged/tree/history Gitleaks passed; signed plan commit
  `a5c2cf6` pushed. Milestone v0.11.4 is number 19. Docker local socket available;
  configured signing key present. No binary qualification yet.
- Engineering audit: installed/distributed/source skill 0.10.0 agree; mandatory
  instruction contract v3 valid. Historical target version stamp alone does not
  warrant generic migration. tgrep-search skill 1.0.3 current; working tgrep
  1.2.3 used for narrow non-indexed searches, rg for current-file fallback.
- Documentation audit: corrected conditional extension/authentication ownership
  to M8, removed obsolete direct-passthrough/OAuth fallback and draft wording,
  refreshed two managed indexes and the M7 contract map. Architecture/status
  diagrams otherwise match code; M7 stays established. Navigation and instruction
  checks passed; independent scoped review found no doc/context issue.
- Harness focused validation: 175 tests, formatting/lint and manifest readback
  pass. Independent review exposed frozen-epoch fresh execution ambiguity;
  explicit early rejection now preserves readback-only history without selecting
  old behavioral probes. Binary qualification of 1.13.0 passed in local Docker;
  remaining candidates are running in the same owned container.
- Delegation: `ocr_0114_harness` owns qualification scripts/tests and its narrow
  development subsection; `context_0114` owns bootstrap/context docs/tests and
  targeted integration; `workflow_0114` owns report-first instruction audit.
  Root owns shared plan/state, source integration, qualification and delivery.

#### Fidelity, closure and resume

- Plan fidelity: requested outcomes, constraints, sources, decisions, ordered
  dependencies, tests and recovery are represented above; no unresolved choice.
- Reconciliation: repository guide owns release archive and lifecycle; generic
  workflow migration/archive machinery is not activated by ordinary release work.
- Closure requires completed stable delivery, immutable receipt readback, tracked
  issue/milestone closure and protected external reconciliation. Feature merge or
  local green alone is not completion.
- Post-close delivery: none; publication and reconciliation remain in scope.
- Resume Point: WQ-02/WQ-03 — integrate independent harness/context slices;
  root prepares Docker and bounded upstream source review while workers execute.
