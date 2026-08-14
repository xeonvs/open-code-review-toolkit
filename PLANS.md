# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Deliver protected-target policy and bounded MR intent in v0.6.1

- **Status:** active
- **Release classification:** `release-required`
- **Target stable version:** `0.6.1`
- **Tracking:** #87, #88, #89
- **Objective:** keep the forge-defined review range unchanged while sourcing policy from the current protected target, retain changed template evidence under existing limits, expose bounded untrusted merge-request intent, add top-level version reporting and public scanner badges, then publish and independently verify stable v0.6.1.

#### Boundaries and decisions

- GitLab provider acquisition owns one bounded point-in-time MR snapshot. Protected target branch/SHA selection and author-controlled intent are separate trust projections; only the former may select policy.
- Evidence schema v4 adds a distinct immutable policy snapshot/ref while preserving v1-v3 readback. Policy applicability continues to use paths changed by the original diff-base-to-head range.
- Repository-owned OCR `--rule` content is never generated, parsed, or merged. The exact blob at the captured policy SHA is materialized privately and replaces only an in-repository rule argument; explicit external operator-owned rule paths remain untouched.
- Template plugins receive one immutable bounded changed-path set and prioritize changed template objects without increasing the per-ref or shared per-kind budgets.
- MR title, description, labels, and optional source-branch hint are invocation-trust data, never policy. Raw provider text stays out of bootstrap, argv, environment, logs, and receipts; admitted intent blocks automatic approval but not comment publication.
- The external-reference attack path is documented without implementing reference extraction, content prefetch, generic URL access, provider-specific MCP adapters, or external writes. Existing configured read-only allowlisted MCP tools remain the only retrieval route.
- Runtime remains standard-library-only; fixtures and public examples remain synthetic and private-safe.

#### Delivery checklist

1. [x] Verify synchronized clean `main`, open issues #87-#89, stable v0.6.0 receipts, current OCR 1.9.3, and no newer stable OCR release.
2. [x] Activate the v0.6.1 plan and mark M4 Established from independently verified v0.6.0 delivery.
3. [ ] Open and maintain an early Draft feature PR after the first signed planning commit; avoid further pushes until the local feature is ready.
4. [ ] Prioritize changed template evidence and add installed-artifact coverage.
5. [ ] Add centralized `ocr-ci --version` source/wheel/sdist coverage.
6. [ ] Add policy ref/schema v4, protected GitLab target acquisition, bounded object fetch, exact policy rules transport, and compatibility/failure tests.
7. [ ] Add bounded MR intent, hostile readback, toolkit-authored trust guidance, receipt-v2 approval blocker, and external-MCP attack-path coverage.
8. [ ] Add verified README security badges, public contracts, Towncrier fragments, and integration tests.
9. [ ] Run focused gates for each commit, complete Python 3.12-3.14 quality/security/package validation, deterministic double builds, installed wheel/sdist tests, and Gitleaks.
10. [ ] Recheck upstream OCR. If 1.9.4 or later is stable, qualify every intervening release, update the local binary and compatibility contract, and use the newest qualified version thereafter.
11. [ ] Run exactly one completed local OCR review over the exact feature range, remediate findings, and repeat self-review plus architecture review without routinely rerunning OCR.
12. [ ] Push the complete feature history, pass required checks, merge the protected feature PR, and independently verify the resulting TestPyPI development artifacts.
13. [ ] Prepare and merge exact `Release v0.6.1`, then independently verify TestPyPI/PyPI bytes, provenance/attestations, supported-Python installs, annotated tag, immutable GitHub Release, and receipt.
14. [ ] Confirm only Actions-owned release receipts close #87-#89 and synchronize a clean local `main`.

#### Commit discipline

Before every logical commit: update status-bearing text to post-commit truth, run focused validation, inspect the complete staged diff, run `git diff --check`, and perform self-review plus architecture review for ownership, dependency direction, bounds, trust transitions, hostile readback, and unnecessary abstraction. Fix findings before signing the commit.
