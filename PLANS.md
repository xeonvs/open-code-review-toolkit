# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Release 0.8.1: completion cap and safe LLM provider failures

Status: implementation complete, final exact-head validation pending; `release-required`. Target stable version: `0.8.1`.

#### Outcome and scope

- Add optional `OCR_LLM_MAX_COMPLETION_TOKENS`; its exact default is unset and therefore inherits the qualified OCR behavior. It controls only the per-request completion/output cap through the protocol-specific `llm.extra_body` key and does not change OCR prompt/context `max_tokens`, `OCR_MAX_TOKENS_BUDGET`, receipt v5, DLP, telemetry, severity, findings, or approval contracts.
- Canonicalize provider URL, protocol, headers, auxiliary `/models` URL, and request-body controls in one provider-neutral runtime owner shared by `configure` and `preflight`.
- Project private OCR retry diagnostics into a closed provider-neutral failure reason and toolkit-authored GitLab guidance. Raw provider bodies, messages, codes, URLs, models, request IDs, paths, warnings, credentials, and stderr remain private.
- Keep OCR `1.9.10` as the exact qualified dependency. Do not promote unreleased upstream defaults or derive a completion cap from `/models` metadata.
- Remove repeated validation that crosses no new owner or artifact boundary: one PR job owns coverage, one owns packages, protected-main TestPyPI owns development artifact publication/readback, and stable release keeps its exact trusted-boundary gates.

#### Trust and data flow

1. Operator environment enters a single provider-config parser. It accepts an explicit closed protocol, bounded positive decimal completion cap, valid header objects, and absolute HTTPS URLs without credentials or fragments. The parser normalizes API root and terminal inference endpoint, preserves an unambiguous query for inference, and requires explicit `OCR_LLM_MODELS_URL` when an auxiliary URL cannot be derived safely.
2. `configure` projects only the validated inference settings into the private OCR configuration. A completion cap maps to `max_completion_tokens` for `openai`, `max_output_tokens` for `openai-responses`, and `max_tokens` for `anthropic`. An equal value already present in `OCR_LLM_EXTRA_BODY` is deduplicated; a different value fails closed.
3. `preflight` consumes the same canonical configuration and derives `/models` only from its normalized API root. Explicit protocol remains authoritative; a terminal endpoint for another protocol is rejected rather than changing protocol implicitly.
4. On a non-zero OCR exit, posting hostile-reads the bounded result artifact only for `ocr.llm-retry-report/v1`. A strict parser admits only allowlisted error class, failure phase, terminal outcome, and HTTP status into a closed reason. Normal findings and every raw/provider-controlled field are ignored.
5. The GitLab note is generated entirely from toolkit-owned static text. Classified failures suppress `OCR_POST_ERROR_DETAILS`; malformed, oversized, missing, or ambiguous diagnostics retain the existing generic note. Previous successful review notes remain, no normal findings are posted, and auto-approval is unreachable.

#### Logical slices and commit gates

1. **Plan and coordination.** Create `codex/v0.8.1-provider-failures`, this planning commit, milestone `v0.8.1`, a completion-cap issue linked with #129, updated #129 acceptance criteria, and a Draft PR. Before commit: plan/self-review, requirement and boundary mapping, `git diff --check`.
2. **Completion-cap contract.** Implement parsing, protocol mapping, conflict behavior, environment/generated-config/installed-artifact tests, and an exact checksum-verified OCR 1.9.10 no-LLM wire probe proving inherited `58888` and explicit `4096`. If the probe does not prove the override, omit the public setting and continue only the diagnostics work. Before commit: focused tests, full diff and trust review, `git diff --check`.
3. **Canonical provider configuration.** Share one provider-neutral owner between configure and preflight; cover API roots, terminal endpoints, trailing slash, query, credentials, fragments, protocol mismatch, and explicit models URL. Before commit: focused tests, URL/header/data-flow review, `git diff --check`.
4. **Failure projection and GitLab.** Add the bounded retry-report parser, closed reason mapping, static hints, and one renderer for non-zero retry reports and existing successful-result billing/quota warnings. Cover HTTP 400/401/402/403/404/408/409/413/422/429/5xx/529, timeout, network, decode, mixed, malformed, oversized, raw-data absence, previous-review preservation, no findings/approval, and strict/advisory behavior. Before commit: focused tests, privacy/approval/rollback review, `git diff --check`.
5. **Documentation and release handoff.** Document exact defaults, mappings, conflicts, the `4096` workaround, the three distinct token ceilings, possible provider cost reservation, and the limits of `/models`; add separate feature and bug-fix Towncrier fragments. Reconcile strategy/roadmap only where the implemented outcome changes them. Before commit: documentation/version consistency, Towncrier draft, full diff review, `git diff --check`.
6. **Validation ownership deduplication.** Keep all five OS/Python full-test jobs but instrument coverage only on Ubuntu 3.14; keep packaging only in `Build artifacts`; stop generic workflow reruns on protected-main push; and keep TestPyPI development focused on its distinct versioned artifact/publication/readback boundary. Release-PR and post-merge stable gates remain unchanged. Update workflow contract tests, development/release guidance, issue #132, and a maintenance fragment. Before commit: focused workflow tests, trigger/check-name and trusted-boundary review, actionlint-equivalent YAML/static validation through existing tests, rendered Towncrier, and `git diff --check`.

#### Validation and delivery

- Focused contract, configuration, preflight, result, posting, approval, environment, installed-artifact, and compatibility tests.
- Full `scripts/quality.sh check` including combined and risk-group coverage floors; `PYTHONPATH=src python scripts/ocr_compat.py validate`; lock/manifest tests; `scripts/gitleaks.sh`; Towncrier draft; reproducible wheel/sdist, Twine, and clean installs on Python 3.12-3.14.
- Overall requirements, provider-boundary, privacy, DLP/approval, telemetry, rollback, and documentation self-review before push.
- Push the complete feature history to the Draft PR, wait for hosted checks, address evidence-driven failures through the same commit gate, then mark ready and merge through protected review.
- Verify the deterministic TestPyPI development build, then prepare and merge the protected `Release v0.8.1` PR. Monitor stable TestPyPI/PyPI publication, tag, immutable GitHub Release, provenance, attestations, supported-Python installs, and immutable receipt; close tracked issues only after independent external reconciliation.

Resume point: run one final exact-head local gate, commit and push the reviewed validation-ownership slice, update Draft PR #131 and issue #132, then require the hosted owners to pass.

#### Current implementation evidence

- Coordination: milestone `v0.8.1`, completion-cap issue #130, provider-diagnostics issue #129, and Draft PR #131 are open.
- Exact OCR 1.9.10 Darwin arm64 asset SHA-256 `c626347bafcdbf25cf058af403d16568a3a9ffa1814046ff7c9d1e6becaf60d2` was verified before execution. The isolated production-config-path probe observed `max_completion_tokens=58888` when unset and `max_completion_tokens=4096` when explicitly configured; all temporary binary, config, repository, HOME, and receipt paths were removed.
- Completion-cap parsing, protocol mapping, collision rules, environment defaults, generated config, wheel/sdist installed paths, and the reusable exact wire probe are implemented and focused-green.
- Canonical provider configuration now gives `configure` and `preflight` one environment snapshot and one owner for explicit protocol, API-root normalization, terminal-endpoint compatibility, secret-bearing headers, request-body controls, and auxiliary metadata URLs. Queried inference URLs require an explicit models URL; metadata-disabled preflight remains compatible.
- Provider failure projection now hostile-reads the bounded private result, validates retry-report v1 counters and terminal attempt facts, and emits only a closed provider-neutral reason. Non-zero classified runs use one static GitLab renderer, keep stderr/provider fields private, preserve the previous review, publish no findings, and never reach approval; legacy billing warnings use the same renderer. The focused gate passed Ruff, full package mypy, 302 tests, and 119 subtests.
- Public configuration, GitLab operations, security boundaries, and the test-evidence matrix now distinguish the per-request completion cap, OCR-owned prompt/context ceiling, and aggregate review budget; document the `/models` non-claim and the safe 404/429 projection; and preserve the generic fallback boundary. Separate #130 feature and #129 bug-fix fragments enumerate added, changed, migration, privacy, deployment, and unchanged contracts. The documentation gate passed 49 tests, Ruff, `git diff --check`, and the rendered 0.8.1 Towncrier section.
- Overall parser-boundary review found and closed three narrow fail-closed gaps before publication: completion-cap length is bounded before integer conversion, embedded URL whitespace is rejected before `urllib` normalization, and JSON booleans cannot satisfy retry attempt numbering. Ruff, full package mypy, 135 focused tests, 100 subtests, and `git diff --check` pass for the correction.
- Issue #132 owns the user-requested validation deduplication. The retained boundaries are five full functional matrix jobs, one PR coverage owner, PR security, one PR package owner, protected-main development artifact publication/readback, release-PR review, and the unchanged post-merge stable release pipeline. Its focused workflow contract passed 46 tests and YAML parsing for all five edited workflows; the complete handoff gate passed 1,231 tests plus 306 subtests, 86.13% combined branch coverage, all four risk floors (84/82/85/87), Ruff, mypy, Bandit, lock and OCR-manifest validation, rendered Towncrier, and `git diff --check`. Live ruleset readback confirmed the required check contexts and strict protected-head policy remain aligned with the unchanged job names.
