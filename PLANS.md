# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### v0.11.2 — dependency consistency, rejection diagnostics and OCR qualification

- Classification: `release-required`; target `v0.11.2`; next development line
  remains `0.12.0`. Work stays on this host and normal GitHub CI.
- Scope: issues #223, #224, #227, #228 and updates from PRs #225, #226.
  Integrate the bot updates into one feature branch and close those PRs as
  superseded only after the feature PR merges.
- Apply the Pareto principle: prioritize shared dependency/CI failure causes and
  publication-safety regressions; reuse unchanged evidence and CI-owned package
  checks. Efficiency never removes the required quality or security gates.
- Delivery: `codex/v0.11.2` from synchronized main; signed plan-only commit and
  push first; no implementation pushes before the completed feature PR is ready.
  Protected feature merge, development publication, draft `release/v0.11.2` PR,
  protected release merge, immutable publication/receipt, then one no-release
  reconciliation PR. Release CI owns issue closure after receipt readback.

#### Implementation and boundaries

1. Incorporate reviewed action SHA updates and setuptools-scm update. Replace
   the pip Dependabot owner with uv, retaining applicable schedule/grouping.
   Validate manifest/lock consistency in existing setup paths with locked sync;
   downstream commands consume the checked environment without synchronization.
   Runtime exports use the checked lock. Remove copied action SHA assertions in
   favor of identity, full-pin and execution/permission boundary contracts.
2. Verify current dependency advisories and narrowly remediate PyJWT/urllib3,
   including required parents and runtime constraints that protect fresh resolver
   installs. Keep dependency audit blocking and preserve its development inputs.
3. Give mandatory-evidence rejection a typed, stable reason and bounded validated
   facts. Distinguish explicit zero, unavailable and malformed telemetry; keep
   positive-call/summary-attribution failure separate. Emit safe diagnostics before
   cleanup without inferring model action or MCP outage. Preserve fail-closed
   publication, local-report and approval gates. Extend the existing authorized
   local private-artifact mechanism; retained rejected results remain ineligible
   even through receipt-less posting. Retention errors cannot hide rejection.
   GitLab CI retains safe facts and its existing private-retention restriction;
   failure-note success and advisory green never mean review acceptance.
4. Review the adjacent upstream chain from qualified OCR 1.12.9 through 1.12.11;
   qualify both candidates through the existing deterministic real-boundary suite.
   Review configuration, telemetry, selection and Rules changes including Jinja.
   Promote only complete compatible evidence. Install a checksum-verified latest
   compatible Darwin arm64 binary locally. After successful replacement remove
   confirmed obsolete Open Code Review executables/backups, preserving historical
   qualification evidence and unrelated OCR products. Recheck latest stable once
   before feature finalization; qualify additional releases with an exact bound.
5. Update changed public contracts, decision flow, evidence matrix, strategy/status
   documents and changelog fragments where their recorded behavior changes.
   Preserve existing automated scheduling behavior without adding documentation.

#### Validation and review

- Focused tests and semantic self-review per logical slice; format Python before
  review and require repository-wide format check before every Python commit.
- Diagnostics cover zero/missing/malformed counts, missing mandatory attribution,
  clean/warning/partial/no-work, local/CI paths, retention failure and rejection
  through posting. Use synthetic results and real boundary owners, no paid retries.
- Dependency tests cover manifest-only rejection before expensive work, coherent
  graph acceptance, unchanged downstream lock, valid replacement SHA acceptance,
  invalid/mutable pin rejection and blocking current audit. Verify the runtime
  floor through a resolver check.
- OCR uses production-equivalent deterministic probes and hostile verifier tests;
  extend probes only for consumed contract changes. No external handoff required.
- Run `scripts/quality.sh check` once on the completed feature head; repeat only
  checks affected by later changes. CI owns wheel/sdist clean-install proof.
  Linux Python 3.12 gates the remaining parallel supported matrix.
- Review the aggregate diff for system design, ownership, trust boundaries and
  regressions. Run staged Gitleaks before commits, tree/history Gitleaks before
  every push. Required CI binds the final feature/release PR heads.

#### Release acceptance and recovery

- Feature merge and successful TestPyPI development workflow precede release PR.
- Release PR owns version/epoch/authorization, Towncrier, notes and plan archive
  with external delivery pending. Issue references must not auto-close on merge.
- CI verifies registries, provenance, all supported Python installs, six immutable
  Release assets and receipt. Operator checks provider state and issue/milestone
  closure without redundant local artifact downloads/installations.
- Closure PR records exact external receipts and reconciles the marker; finish
  with clean synchronized main. On a local blocker, stop its dependent stage and
  report it; do not use another host or weaken checks.

#### Current checkpoint

- Milestone v0.11.2 (17) contains #223, #224, #227, #228. Feature branch is
  `codex/v0.11.2`; signed plan-only commit `5e368d2` was pushed after all secret
  gates. Implementation commits remain local until the ready feature PR.
- Dependency/CI implementation and independent review complete. PyJWT 2.15.1,
  urllib3 2.8.0 and setuptools-scm 10.3.4 are locked; runtime floor protects
  resolver installs. Current audit is clean; Python 3.12 resolver chooses the
  fixed PyJWT and rejects forced 2.14.0. Workflow tests: 51 passed; corrected
  quality-wrapper assertions: seven passed.
- Rejection implementation and independent review complete. Explicit null remains
  malformed; missing telemetry and explicit zero are distinct typed rejections.
  Retained successful/private and rejected/nonzero results cannot enter posting
  or successful reports. Unsafe retention preserves original failure and removes
  raw handoff. Safe logs distinguish retained session artifacts from result data.
  Focused runtime/CLI/docs: 250 passed; later boundary additions: 12 orchestration
  and 40 rejection tests passed. Scoped mypy/Ruff passed.
- OCR 1.12.11 is installed and recommended, with verified Linux/Darwin identity
  and required real-boundary qualification including Jinja selection/Rules.
  Reused valid hosted 1.12.10 evidence; 142 compatibility tests and current
  manifest validation passed. Latest stable recheck remains 1.12.11. Confirmed
  old executable/backup and task binary downloads removed; historical evidence
  preserved. Disposable container removed. Its earlier attempts failed because
  Git 2.39.5 was below OCR's floor; successful container used Git 2.47.3.
- Aggregate review corrected stale pin documentation and covered dependency,
  diagnosis, retention, posting and qualification interactions. No remaining
  actionable blocker. Full quality passed: 1830 tests, two skips, 339 subtests,
  86% combined coverage and all boundary floors; Ruff, mypy and Bandit passed.
  Final affected focused checks passed (250 tests).
- Feature PR #229 is open. Build/install, audit, security, quality and CodeQL
  passed. Python 3.12 rejected the late-added compatibility paragraph because it
  named a removed public configuration variable. Removed that stale literal
  without weakening the configuration guard; affected document tests rerun.
- Next action: push the scoped documentation correction after secret gates,
  await exact-head feature CI, then protected publication and reconciliation.
