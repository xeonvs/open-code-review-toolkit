# Execution Plans

Use this file for active or blocked repository work. Update it before implementation and before handoff or commit. Completed stable plans are indexed in [the execution-history archive](docs/engineering/execution_history/README.md).

## Active Work

### Release 0.8.1: completion cap and safe LLM provider failures

Status: active, `release-required`. Target stable version: `0.8.1`.

#### Outcome and scope

- Add optional `OCR_LLM_MAX_COMPLETION_TOKENS`; its exact default is unset and therefore inherits the qualified OCR behavior. It controls only the per-request completion/output cap through the protocol-specific `llm.extra_body` key and does not change OCR prompt/context `max_tokens`, `OCR_MAX_TOKENS_BUDGET`, receipt v5, DLP, telemetry, severity, findings, or approval contracts.
- Canonicalize provider URL, protocol, headers, auxiliary `/models` URL, and request-body controls in one provider-neutral runtime owner shared by `configure` and `preflight`.
- Project private OCR retry diagnostics into a closed provider-neutral failure reason and toolkit-authored GitLab guidance. Raw provider bodies, messages, codes, URLs, models, request IDs, paths, warnings, credentials, and stderr remain private.
- Keep OCR `1.9.10` as the exact qualified dependency. Do not promote unreleased upstream defaults or derive a completion cap from `/models` metadata.

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

#### Validation and delivery

- Focused contract, configuration, preflight, result, posting, approval, environment, installed-artifact, and compatibility tests.
- Full `scripts/quality.sh check` including combined and risk-group coverage floors; `PYTHONPATH=src python scripts/ocr_compat.py validate`; lock/manifest tests; `scripts/gitleaks.sh`; Towncrier draft; reproducible wheel/sdist, Twine, and clean installs on Python 3.12-3.14.
- Overall requirements, provider-boundary, privacy, DLP/approval, telemetry, rollback, and documentation self-review before push.
- Push the complete feature history to the Draft PR, wait for hosted checks, address evidence-driven failures through the same commit gate, then mark ready and merge through protected review.
- Verify the deterministic TestPyPI development build, then prepare and merge the protected `Release v0.8.1` PR. Monitor stable TestPyPI/PyPI publication, tag, immutable GitHub Release, provenance, attestations, supported-Python installs, and immutable receipt; close tracked issues only after independent external reconciliation.

Resume point: create the feature branch and signed planning commit, then perform the exact OCR 1.9.10 wire probe before exposing `OCR_LLM_MAX_COMPLETION_TOKENS`.
