# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

## Active Plan: v0.7.1 bounded result semantics and OCR 1.9.9

Status: active
Owner: Codex
Release classification: `release-required`
Target stable version: `0.7.1`
Last Updated: 2026-08-21

### Goal

Deliver one ordinary stable v0.7.1 release that distinguishes private-only
result sanitization from publication filtering, reconciles count-only evidence
actions and normalized token usage, prioritizes the bounded reviewer guide
deterministically, and qualifies/adopts OCR 1.9.9. Complete the protected
feature, TestPyPI development, release-PR, stable publication, independent
readback, issue closure, and milestone closure lifecycle as one objective.

### Tracked Scope

- [#115](https://github.com/xeonvs/open-code-review-toolkit/issues/115):
  replace ambiguous legacy result-DLP receipts with one closed receipt-v5
  contract for `passed`, `private-sanitized`, and `publication-filtered`.
- [#116](https://github.com/xeonvs/open-code-review-toolkit/issues/116):
  distinguish OCR-native tool totals from verified MCP-server use, reconcile
  the built-in evidence actions `summary`, `list`, and `get`, and render only
  validated normalized token buckets.
- [#117](https://github.com/xeonvs/open-code-review-toolkit/issues/117):
  sort only the already-published copy used by Recommended focus areas with a
  closed severity/category/location/identity order before the existing cap.
- [#118](https://github.com/xeonvs/open-code-review-toolkit/issues/118):
  qualify and adopt OCR 1.9.9 with checksum-pinned evidence and the required
  background-input adaptation.
- Include the existing `changelog.d/114.doc.md` documentation correction in
  v0.7.1 without treating closed PR #114 as a tracked release issue.

The stable release workflow issue set is exactly `[115, 116, 117, 118]`. No
umbrella issue is created. The GitHub milestone is `v0.7.1`; it closes only
after the ordinary stable release and independent external readback complete.

### Service and Trust Boundaries

- `review_runner.py` remains the orchestration owner for OCR invocation, result
  finalization, publication DLP, and toolkit-managed bootstrap arguments.
- `ocr_result.py` owns the closed receipt-v5 producer/loader contract. Receipt
  versions 1-4 are removed rather than supported; unrelated evidence-store,
  OCR outcome, fingerprint, provider, and direct-posting compatibility remains
  out of scope.
- One pure canonical publication/approval projection covers normalized outcome
  and message, ordered findings and warnings, manifest/coverage state, displayed
  counters, normalized token telemetry, omission/completeness, and all approval
  inputs. Byte-equivalence after sanitization is required for
  `private-sanitized`; any changed, malformed, or incomparable projection is
  `publication-filtered`, partial, and approval-ineligible. Rejected values,
  original locations, and raw DLP diagnostics are never retained.
- The built-in evidence MCP persists an owner-only atomic count receipt only for
  completed model-time `summary`, `list`, and `get` calls. Preflight self-query
  is excluded. The parent reads it before cleanup and requires its total to
  match `tool_calls.by_tool["ocr_toolkit_evidence"]`; absence, malformed data,
  races, or mismatch render action attribution unavailable rather than zero.
  This is not a new approval blocker and cannot weaken the mandatory-summary
  gate.
- Supported token telemetry is closed to input, output, cached, reasoning, an
  optional validated total, and a mathematically derived other bucket. Cached
  is a subset of input and reasoning a subset of output; unknown provider keys
  are not published. Telemetry is never described as review quality,
  effectiveness, or return on investment.
- Recommended focus areas sorts a copy after suppression and posting cap,
  immediately before the guide top-N cap. It does not change discussion order,
  suppression, approval, counts, security focus, or omitted messaging. Stable
  ties use severity, category, valid case-sensitive Git path, range,
  occurrence-aware fingerprint, then a deterministic canonical fallback and
  ordinal.
- OCR 1.9.9 caller-provided `--background` and `--background-file` are both
  rejected, including split and `--flag=value` forms. The toolkit supplies only
  its own bootstrap with `--background-file`. The new failed-item stop reason is
  mapped through manifest/result/posting/DLP; upstream `tool_choice` test changes
  do not alter a consumed wire contract.

### Locked Decisions

- Backward compatibility is not required for the result receipt/posting
  contract, and no v1-v4 fallback remains. This is not authorization for a broad
  legacy purge outside the active result contract.
- OCR 1.9.9 qualification workflow run
  [32476604710](https://github.com/xeonvs/open-code-review-toolkit/actions/runs/32476604710)
  completed successfully and created canonical issue #118. It classified the
  release as compatible but human-review-required. No competing
  `automation/ocr-1.9.9` pull request exists.
- Verified OCR 1.9.9 checksums used by the public Linux example and local Darwin
  qualification are respectively
  `52f993c615a6b456cb1c36fc135fec6b8da19cb88da7f305bd2726c3d72f1cf0`
  and
  `271daa462c46c514ac535ae48f9d840cb58e450897e4e66297294188071efefa`.
- The first signed commit activates this plan and tracking truth. It is pushed
  once to open a draft feature PR. No later commit is pushed until all local
  implementation, bounded review, and final gates finish.
- After implementation and an explicit audit of all plan, issue, documentation,
  test, and changelog tails, there is at most one justified Codex Security diff
  scan, followed by repairs and a full self-review. Before the single local OCR
  1.9.9 review, evaluate whether repository-owned OCR review rules and a narrow
  suppressor are justified for permanent toolkit-local use. Add maintained
  files, tests, and instructions only when repository evidence supports them;
  otherwise record the no-change decision. Then run OCR once, repair its
  findings, and perform a second full self-review without another OCR or Codex
  Security run.
- If hosted checks after the final feature push require a code change, stop and
  request authorization for another push. Squash merge remains human-gated.
- The separate `Release v0.7.1` PR is the final repository mutation. Stable
  publication, issue closure, and milestone closure occur externally without a
  closure PR.

### Work Queue

1. [x] Reconcile live `main`, issues #115-#118, milestone v0.7.1, OCR 1.9.9
   release metadata, workflow qualification, and competing automation state.
2. [x] Commit and push this active plan, open the draft feature PR, assign it to
   `xeonvs`, and record its URL without pushing another plan-only commit.
3. [x] Implement receipt v5 and canonical publication/approval projection;
   remove only result receipt/posting v1-v4 compatibility and add private-safe
   regression coverage and documentation.
4. [x] Implement owner-only evidence-action receipts, parent reconciliation,
   closed normalized usage-accounting tests, and public
   operator documentation.
5. [x] Implement deterministic guide ranking with malformed-metadata, stable
   tie, truncation, and Markdown-safety tests while preserving finding flow.
6. [x] Qualify/adopt OCR 1.9.9 from workflow evidence, adapt toolkit-managed
   background handling, update pins/evidence/docs/tests/changelog, and close the
   human checklist in #118 through the protected feature PR.
7. [ ] Complete logical signed local commits with per-commit self-review. Audit
   every plan, issue, documentation, test, and changelog tail and repair partial
   closure before running the single permitted Codex Security diff scan if the
   finished security boundary warrants it; fix every validated finding.
8. [ ] Perform the first complete aggregate self-review. Decide from the actual
   integrated review contract and false-positive evidence whether permanent
   repository-owned OCR rules and a narrow suppressor are warranted; if so, add
   their files, tests, and future-maintenance instructions, otherwise record the
   no-change decision. Then run exactly one local OCR 1.9.9 review, fix its
   actionable findings, and perform the second complete aggregate self-review
   without rerunning OCR or Codex Security.
9. [ ] Run focused contracts plus deterministic quality, privacy, dependency,
   workflow, package, two-build reproducibility, clean Python 3.12-3.14 install,
   CLI, and complete-history Gitleaks gates; update this plan to exact feature
   readiness and make the one final feature push.
10. [ ] Verify the exact hosted PR head, required checks, unresolved threads,
    privacy/license gate, and merge policy; obtain the human squash merge, then
    independently verify the resulting deterministic TestPyPI development
    wheel/sdist bytes, provenance, and smoke installs.
11. [ ] Create `release/v0.7.1` from synchronized `main`; set
    `.release-version=0.7.1`, `.next-version=0.7.2`, deterministic source epoch,
    `.release-metadata.json`, Towncrier changelog/release notes, plan archive and
    index, affected roadmap/strategy/backlog/README truth, and reset `PLANS.md`.
12. [ ] Open the exact `Release v0.7.1` PR as the final repository mutation,
    verify its exact reviewed tree/checks/threads, and obtain the human squash
    merge publication gate.
13. [ ] Independently read back TestPyPI, PyPI, workflow, and GitHub Release
    byte/hash equality; registry/GitHub provenance and attestations; Python
    3.12-3.14 clean installs; annotated tag target; immutable Release and full
    assets; `release-receipt.json`; Actions-owned issue receipts/closure; closed
    milestone v0.7.1; and clean synchronized `main`.

### Validation and Review Contract

- Iterate with the narrowest tests owned by each changed parser, persistence,
  subprocess, DLP, posting, formatting, and compatibility boundary.
- Before every logical commit: update post-commit plan/status truth, inspect the
  complete staged diff, run `git diff --check`, and run subsystem validation.
- The first complete self-review covers every branch diff, schema owner, trust
  transition, failure path, concurrency/cleanup edge, privacy sink, docs and
  changelog statement, and test omission. Incorporate every finding before OCR.
- The single OCR run exercises the actual integrated repository path with OCR
  1.9.9. Preserve its complete private result outside tracked files, repair its
  findings once, and do not rerun it.
- The second complete self-review rechecks the repaired aggregate branch and
  explicitly compensates for the no-rerun rule with code/test/evidence analysis.
- Final deterministic gates include `scripts/quality.sh check`, pinned
  Gitleaks, dependency audit, workflow/YAML/action checks, lock validation,
  Towncrier draft, two byte-identical builds, Twine/archive inspection, and
  clean wheel/sdist installs and CLI smokes for every supported Python minor.
- No feature or release PR body uses auto-close keywords. The stable workflow
  closes issues only after immutable external readback.

### Current Evidence and Resume Point

- Base: synchronized clean `main` at
  `a8930cbb923bd618b783e9204e2fe01d81252635`.
- Issues #115, #116, #117, and #118 are open, assigned to `xeonvs`, and attached
  to open milestone v0.7.1.
- Signed plan commit `f0f2f600f5d35017f291961c6fa78a02e0f62e3f` opened
  assigned draft PR [#119](https://github.com/xeonvs/open-code-review-toolkit/pull/119).
  The published branch remains exactly at that commit; keep every implementation
  commit local until the final feature push gate.
- Historical failed Actions run `32477387526`, whose Gitleaks alert came from
  token-shaped plan prose rather than a credential, was deleted after the branch
  history was rewritten; run `32477938275` passed on the published plan head.
- Receipt-v5 implementation is complete locally: pre-v5 toolkit receipts are
  rejected while receipt-less direct posting remains supported; conservative
  warning-object DLP covers rendering, coverage, and billing consumers; focused
  validation passed with 286 tests and 141 subtests. The shared closed token
  normalizer is present because canonical projection must compare the exact
  telemetry that #116 renders.
- Evidence-action attribution for #116 is complete locally: the built-in MCP
  records only completed closed-enum action counts in an owner-only atomic
  receipt, the parent removes it and publishes counts only after exact OCR-total
  reconciliation, and missing, malformed, raced, or mismatched receipts remain
  explicitly unavailable. Focused validation passed with 318 tests and 141
  subtests; focused Ruff and `git diff --check` passed.
- Deterministic Recommended focus ranking for #117 is complete locally. It
  sorts only a copied published-finding sequence before the existing guide cap,
  preserves discussion order and other posting semantics, and covers malformed
  metadata, case-sensitive paths, occurrence fingerprints, truncation, stable
  output, and existing Markdown neutralization.
- OCR 1.9.9 adoption for #118 is complete locally from workflow run
  `32476604710` and its canonical evidence artifact. Version/checksum pins and
  compatibility evidence are promoted; both caller background options are
  rejected in split and equals forms; named main-loop stop reasons are covered
  through result projection, DLP, and posting diagnostics. Focused validation
  passed with 353 tests and 93 subtests; Ruff, manifest validation, and
  `git diff --check` passed. The one allowed local OCR run remains unused.
