# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and
before handoff or commit. Completed stable plans are indexed in
[the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### v0.11.3 — OCR 1.12.12–1.12.13 qualification and delivery

- Plan Origin: `plan_mode_approved`; status: active.
- Classification: `release-required`; target `v0.11.3`; next development `0.12.0`.
- Scope: contiguous OCR 1.12.11 → 1.12.12 → 1.12.13; recommend 1.12.13
  only after complete qualified evidence and adjacent source review. Upper tag
  is fixed at `v1.12.13`. Current host and normal GitHub CI only.
- Delivery: branch `codex/v0.11.3` from synchronized main; one signed plan-only
  push first, then no implementation push until the complete feature is ready.
  Draft feature PR, protected merge, development publication, separate draft
  `release/v0.11.3` PR, stable publication, and one documentation-only closure PR.

#### Ordered work and acceptance

1. Create milestone and dispatch existing OCR compatibility workflow once with
   `through_tag=v1.12.13`. Reuse its canonical issues and evidence. Failed
   candidates block promotion; diagnose the concrete owning failure without
   bypassing checks or using another host.
2. Review builtin/custom-provider overrides, changed timeout reasons and partial
   coverage semantics. Treat scan-path and README changes as unconsumed context.
   Use the existing bounded no-LLM harness; add probes only for demonstrated
   changed consumed contracts. Do not recreate upstream tests or wait through
   slow real timeouts. Preserve historical evidence and rolling support policy.
3. Use the existing promotion path for the manifest, evidence, recommendation,
   runtime identity and checksum-pinned example. Add Maintenance changelog;
   add a separate Bug Fix only for a demonstrated toolkit defect. Avoid API,
   schema and roadmap feature expansion without evidence.
4. Install checksum-verified Darwin arm64 OCR 1.12.13 locally, verify identity,
   then remove only the confirmed previous installed OCR executable. Do not
   repeat the hosted full qualification locally or remove historical evidence.
5. Run focused compatibility/preflight/result-contract tests, preserving timeout
   reasons without granting publication or approval authority. Self-review each
   slice; independently review aggregate boundaries, architecture and regressions.
   Run the full local quality wrapper once; repeat only affected checks after fixes.
   CI owns distribution builds and clean-installed runtime verification.
6. Stage Gitleaks before signed commits; tree/history Gitleaks before every push.
   Create draft feature PR when implementation is ready. Require final-head
   protected checks and all three Linux gates: 3.12 first, then the parallel matrix.
   Merge and confirm TestPyPI development publication.
7. Prepare release markers, source epoch, issue authorization, Towncrier and notes;
   archive repository-complete work with external delivery pending and reset active
   plans. Keep next development 0.12.0 and reconciliation at 0.11.2. Create draft
   release PR, complete review/checks and protected merge.
8. Confirm successful TestPyPI/PyPI, provenance, installed-runtime matrix and
   immutable six-asset Release/receipt through CI and provider metadata. Release
   workflow closes issues only after receipt readback; then close milestone.
   No duplicate local artifact downloads or installs.
9. One protected no-release closure PR records exact external receipts, completed
   roadmap/archive status and reconciliation marker. Verify its development build;
   finish on clean synchronized main. Preserve published identities and assets.

#### Current checkpoint

Baseline main `171056645ae0d02200b3474458773de0a102e18f` is clean and
synchronized. Recommended and local OCR are 1.12.11. No open issue or PR at
activation. Resume: finish plan-only signed push, create milestone, dispatch
bounded qualification. Apply Pareto: reuse evidence, narrow changed-boundary
checks and one full quality run; never weaken required gates.
