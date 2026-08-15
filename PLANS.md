# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Deliver protected-target policy and bounded MR intent in v0.6.1

- **Status:** active
- **Release classification:** `release-required`
- **Target stable version:** `0.6.1`
- **Tracking:** #87, #88, #89, #90
- **Objective:** keep the forge-defined review range unchanged while sourcing policy from the current protected target, retain changed template evidence under existing limits, expose bounded untrusted merge-request intent, add top-level version reporting, qualify OCR 1.9.4 with its telemetry/backlog impact, add public scanner badges, then publish and independently verify stable v0.6.1.

#### Boundaries and decisions

- GitLab provider acquisition owns one bounded point-in-time MR snapshot. Protected target branch/SHA selection and author-controlled intent are separate trust projections; only the former may select policy.
- Evidence schema v4 adds a distinct immutable policy snapshot/ref while preserving v1-v3 readback. Policy applicability continues to use paths changed by the original diff-base-to-head range.
- Repository-owned OCR `--rule` content is never generated, parsed, or merged. The exact blob at the captured policy SHA is materialized privately and replaces only an in-repository rule argument; explicit external operator-owned rule paths remain untouched.
- Template plugins receive one immutable bounded changed-path set and prioritize changed template objects without increasing the per-ref or shared per-kind budgets.
- MR title, description, labels, and optional source-branch hint are invocation-trust data, never policy. Raw provider text stays out of bootstrap, argv, environment, logs, and receipts; admitted intent blocks automatic approval but not comment publication.
- The external-reference attack path is documented without implementing reference extraction, content prefetch, generic URL access, provider-specific MCP adapters, or external writes. Existing configured read-only allowlisted MCP tools remain the only retrieval route.
- Runtime remains standard-library-only; fixtures and public examples remain synthetic and private-safe.
- After OCR 1.9.4 qualification, map every #87-#90 acceptance criterion and every touched boundary to production-path evidence. A test double may replace an external collaborator only beyond the claimed boundary; it cannot replace the production owner being verified. Wiring-only tests remain unit evidence and must be paired with real Git, local HTTP, private artifact, hostile store reload, stdio MCP, installed wheel/sdist, subprocess, and actual OCR-consumer paths where those contracts are claimed.

#### Delivery checklist

1. [x] Verify synchronized clean `main`, open issues #87-#89, stable v0.6.0 receipts, current OCR 1.9.3, and no newer stable OCR release.
2. [x] Activate the v0.6.1 plan and mark M4 Established from independently verified v0.6.0 delivery.
3. [x] Open and maintain early Draft PR #91 after the first signed planning commit; avoid further pushes until the local feature is ready.
4. [x] Prioritize changed template evidence and add installed-artifact coverage.
5. [x] Add centralized `ocr-ci --version` source/wheel/sdist coverage.
6. [x] Add policy ref/schema v4, protected GitLab target acquisition, bounded object fetch, exact policy rules transport, and compatibility/failure tests.
7. [x] Add bounded MR intent, hostile readback, toolkit-authored trust guidance, receipt-v2 approval blocker, and external-MCP attack-path coverage.
8. [x] Add verified README security badges, public contracts, Towncrier fragments, and integration tests.
9. [x] Run focused gates for each commit, complete Python 3.12-3.14 quality/security/package validation, deterministic double builds, installed wheel/sdist tests, and Gitleaks.
10. [x] After completing #87-#89 and before the README/documentation pass, qualify OCR 1.9.4 through #90, analyze telemetry and backlog impact, update the local binary and compatibility contract, and use 1.9.4 thereafter; include any newer intervening stable release if one appears.
11. [x] Audit every #87-#90 acceptance criterion and touched boundary first, then audit the complete test suite: record each claimed production owner and test entry point, permit doubles only beyond that owner, and replace mock-selected success/rejection with real Git, local HTTP, persistence, MCP, installed-artifact, subprocess, and OCR-consumer paths before relying on integration coverage. The matrix covers all 38 test modules; model-dependent #89 intent calibration is explicitly not claimed by a fake LLM and remains a qualification assertion for the final OCR gate.
12. [ ] Run exactly one completed local OCR review over the exact feature range, including the remaining model-dependent #89 calibration assertion, remediate findings, and repeat self-review plus architecture review without routinely rerunning OCR.
13. [ ] Push the complete feature history, pass required checks, merge the protected feature PR, and independently verify the resulting TestPyPI development artifacts.
14. [ ] Prepare and merge exact `Release v0.6.1`, then independently verify TestPyPI/PyPI bytes, provenance/attestations, supported-Python installs, annotated tag, immutable GitHub Release, and receipt.
15. [ ] Confirm only Actions-owned release receipts close #87-#90 and synchronize a clean local `main`.

#### Pre-OCR validation receipt

- The complete quality gate and independent Homebrew Python 3.12.14, 3.13.15,
  and 3.14.7 matrices each pass 806 tests plus 102 subtests with at least 81%
  coverage. Ruff formatting/lint, mypy, Bandit, dependency audit, compatibility
  manifest validation, Towncrier rendering, `git diff --check`, and pinned
  full-feature-history Gitleaks pass.
- Checksum-verified local OCR 1.9.4 passes version, help, JSON preview/result,
  additive comment, manifest, and real protected-target rule-selection probes;
  bounded discovery reports no unseen stable OCR release before the final review.
- Two source-epoch-controlled `0.6.1.dev0` builds are byte-identical and pass
  Twine plus closed archive-content checks. The wheel SHA-256 is
  `a14c4e6807dbbf9b1be67bf1a4fb82a94d37f2bb4528b738ebc3bcae646791c0` and
  the sdist SHA-256 is
  `aa6b99427c353d2a10614048ee617bf64fde03495b22b22d3b2adb32a76031d3`.
  Real installed wheel and sdist-to-wheel policy/MR-context/stdin-MCP E2E passes,
  as do clean restricted-path wheel installs on Python 3.12/3.13 and the sdist
  on Python 3.14 with exact centralized `ocr-ci --version` output.

#### Commit discipline

Before every logical commit: update status-bearing text to post-commit truth, run focused validation, inspect the complete staged diff, run `git diff --check`, and perform self-review plus architecture review for ownership, dependency direction, bounds, trust transitions, hostile readback, and unnecessary abstraction. Fix findings before signing the commit.
