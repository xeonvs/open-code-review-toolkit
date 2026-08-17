# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Plan: Qualify OCR 1.9.5 and release toolkit v0.6.2

Status: in progress
Owner: Codex
Last Updated: 2026-08-17
Release Classification: release-required
Target Stable Version: 0.6.2
Tracking Issue: #93

#### Objective

Qualify checksum-verified Open Code Review 1.9.5 against every toolkit-consumed boundary, promote it as the tested and recommended baseline, expose its existing aggregate review-token budget as an explicit operator-controlled GitLab example setting without adopting full-repository scan behavior, reconcile the affected profile and measurement backlog, and publish and independently verify stable toolkit v0.6.2.

#### Scope and decisions

- Preserve the product boundary: the toolkit invokes `ocr review`, not `ocr scan`. OCR 1.9.5's new `scan` `summary.budget_exceeded` emission is compatible upstream telemetry but does not justify a scan adapter, result special case, or second telemetry implementation.
- Adopt `--max-tokens-budget` as a required qualified review flag and expose one optional non-negative `OCR_MAX_TOKENS_BUDGET` value in the synthetic GitLab example. It is passed directly to the pinned OCR process; `0` remains OCR's unlimited default. Existing result normalization, partial-result publication, coverage diagnostics, and automatic-approval rejection remain the single budget-stop lifecycle.
- Keep budget independent from future named profiles. BL-016 must not let `economy`, `standard`, or `strong` silently change review completeness through an aggregate cap; explicit operator budget is a separate ceiling. BL-017 must classify scan-only budget output as upstream-owned and outside the toolkit review signal inventory.
- Treat Swift built-in guidance and its changed default test exclusions as an effective recommended-OCR rules contract change and include a `Rules` release entry. Do not add a Swift evidence pack without a demonstrated toolkit evidence gap.
- Treat cross-file comment re-filing as an upstream positioning improvement compatible with the toolkit's normalized path/range and suggestion proof boundaries. Treat the conservative tool-based review filter as upstream finding-generation behavior: its internal tools do not become configured MCP capabilities or toolkit authority. Provider preset, marketplace, viewer, and CLI documentation changes require no toolkit runtime adaptation.
- Use only public upstream data and synthetic fixtures. Install only the official checksum-verified Darwin arm64 OCR 1.9.5 binary locally. No test double may replace the OCR executable, subprocess launcher, result parser, or other boundary cited as qualification evidence.

#### Service boundaries

- `scripts/ocr_compat.py` owns deterministic candidate execution and required CLI/result contracts; the official OCR binary is the external peer.
- `compatibility/ocr-support.json` and `compatibility/evidence/ocr-1.9.5.json` own the reviewed version, assets, capabilities, and human conclusion.
- `examples/gitlab/ocr-review.gitlab-ci.yml` owns the public synthetic executable pin, checksum, and aggregate review budget example; `docs/configuration.md`, `docs/gitlab.md`, and `docs/operations.md` own operator semantics.
- `src/ocr_toolkit/result_contract.py` and posting remain unchanged unless real 1.9.5 output disproves the existing partial-budget contract.
- `docs/codex/TASKS_BACKLOG.md`, `ROADMAP.md`, and strategy retain future-work ownership; only proven stale budget/profile/measurement wording changes.

#### Work queue

1. [x] Read current plans, strategy, backlog, engineering/release contracts, #93, hosted workflow evidence, and the complete upstream v1.9.4...v1.9.5 source/release delta.
2. [x] Download and checksum-verify the official Darwin arm64 binary, update the local OCR installation to 1.9.5, and run version/help plus deterministic local compatibility probes.
3. [x] Promote 1.9.5 in compatibility evidence, preflight, synthetic GitLab version/checksum, and tests; require the aggregate review-budget flag in future qualification.
4. [x] Add the explicit synthetic GitLab aggregate budget control and document its independent partial-result, coverage, and approval behavior.
5. [ ] Reconcile BL-016 and BL-017 plus roadmap/strategy wording so profiles cannot hide coverage limits and scan-only telemetry does not create toolkit scope.
6. [x] Add Towncrier feature/rules entries and record the human conclusion for every upstream change.
7. [x] Run focused tests, real executable probes, the complete quality/security/package matrix, requirement-to-evidence anti-mock review, architecture/self-review, full diff and privacy checks; correct every actionable finding.
8. [ ] Merge the protected feature PR after exact-head checks and independently verify its TestPyPI development artifacts and supported-Python installs.
9. [ ] Prepare and merge the protected `Release v0.6.2` PR as the final repository mutation, then independently verify stable registries, hashes, provenance/attestations, annotated tag, immutable GitHub Release, receipt, supported-Python installs, and issue closure.

#### Implementation checkpoint

- Official Darwin arm64 OCR 1.9.5 is installed at the active `command -v ocr` path; version output and SHA-256 `459d3986e59fed5ed8ad6a97bc02d2eb995a89106b3fe6a6fcf74bb69cab1b73` match upstream metadata and `sha256sum.txt`.
- Hosted run `32000131436` verified every official asset and the existing Linux amd64 contracts. The extended local real-executable probe additionally verifies `--max-tokens-budget`: two of three files complete, their findings survive, and the third is represented by `summary.budget_exceeded`, `token_budget_reached`, and manifest `failed(budget)` coverage normalized as partial.
- The controlled HTTP peer is beyond the production OCR boundary; no mock replaces OCR, its launcher, dispatch, accounting, manifest, JSON serialization, or toolkit parser. The test evidence matrix records the exact claim limits.
- OCR 1.9.5 is promoted in the manifest, preflight, and synthetic executable pin. The example exposes `OCR_MAX_TOKENS_BUDGET=0` and passes it as a quoted OCR argument; documentation keeps it independent from profiles and explains approximate enforcement, partial findings, coverage, and approval ineligibility.

#### Review and validation checkpoint

- Requirement-to-evidence review maps the official OCR executable, real local HTTP peer, production subprocess launcher, manifest/result parser, and posting/approval policy separately. Mocks remain only in unit/error-policy tests and are not cited for OCR integration; the matrix documents every replaced collaborator and non-claim.
- Self-review found and fixed a stale mocked preflight version plus an insufficient direct assertion for raw `summary.budget_exceeded`. Architecture review keeps the new executable probe in the existing repository-only compatibility harness, leaves runtime dependencies and `ocr scan` untouched, and preserves OCR as token/budget telemetry owner.
- Focused compatibility, runner, result, posting, documentation, and anti-mock tests pass. Clean sequential full suites pass on Python 3.12.14 and 3.13.15 with 813 tests plus 105 subtests at 81.20% coverage, and on Python 3.14.7 with the same counts at 81.21%; each suite retains the real nested-venv wheel/sdist and stdio-MCP integration test. The first 3.13 attempt exposed a reproducible `ensurepip` abort in the old uv-managed CPython 3.13.4 experimental-JIT build itself; an isolated `venv` reproducer failed there and passed on Homebrew CPython 3.13.15 before the complete matrix was rerun unchanged. Ruff, mypy, Bandit, and pip-audit pass, with no known dependency vulnerabilities.
- Two source-epoch-controlled `0.6.2` builds are byte-identical: wheel SHA-256 `d351f233558e3a9a70f729f41546d37880a02ecfbe6a08b4bf04c8b58f10af1e` and sdist SHA-256 `ead296f579c33282364e78d9e5e1149c052f46497ba4177bc3987c85440facd8`. Twine accepts both sets; clean hash-locked wheel and sdist installs on Python 3.12, 3.13, and 3.14 pass isolated version/help/import and `pip check` smoke tests.
- Pinned Gitleaks 8.24.3, workflow/example YAML parsing, manifest validation, Towncrier 0.6.2 draft rendering, and `git diff --check` pass. Public material remains synthetic and contains no private provider/repository data. Gitleaks and reproducible package checks are repeated after feature commits so committed history and the final source epoch are the evidence used for publication.

#### Validation and closure gates

- Official 1.9.5 asset digest agrees with GitHub metadata, upstream `sha256sum.txt`, the committed evidence, and the installed binary; `command -v ocr`, `ocr --version`, and the digest identify the same executable.
- Real OCR 1.9.5 passes version/help, JSON preview, target-rule selection, deterministic local-gateway review/result consumer, and an actual budget-limited review contract probe; mocks are not accepted as OCR integration evidence.
- Synthetic tests prove configured `0` and a positive budget reach the real child argv through the production subprocess launcher; result/parser tests continue to prove partial findings, budget attribution, and ineligible approval.
- `scripts/quality.sh check`, pinned Gitleaks, `git diff --check`, manifest/workflow/Towncrier validation, dependency/security checks, reproducible wheel/sdist builds, Twine, and clean Python 3.12-3.14 installed-artifact smokes pass.
- Stable completion requires live external readback of all release surfaces and the immutable receipt; feature merge or development publication alone is not completion.
