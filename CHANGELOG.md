## 0.8.7 - 2026-09-01

### 🚀 Features

- Add two fixed read-only built-in MCP tools for bounded literal evidence search and exact scoped coverage checks. OCR now receives concise summary/list/search/get/coverage routing, while action receipt v2 and toolkit receipt v6 reconcile all five actions to OCR's per-tool counts. Search applies the same public delta-kind semantics as list, rejects compatibility-normalized operators, and authoritative absence requires an exact component/path scope with no evidence-store admission limit, ambiguous or oversized omission, or incomplete semantic comparison. Evidence admission performs one live secret-value scan per scalar instead of repeating the same scan within a redaction pass. Only non-zero numeric counts may reach GitLab; queries, scopes, matched values, IDs, and results remain private, and incomplete coverage can never prove absence or authorize automatic approval. ([#160](https://github.com/xeonvs/open-code-review-toolkit/issues/160))
- Add protected review-context policy v3 for bounded same-revision CI outcomes. Operators may map exact GitLab job names to protected path prefixes; the toolkit twice reads exact-head pipeline/job metadata, ignores unrelated jobs, treats provider response ordering as non-semantic, selects the unambiguously newest requested retry, and exposes only closed status, required/advisory classification, current-or-same-revision provenance, scope, and completion time through the existing private context MCP. Hostile persisted scopes are revalidated against the protected repository-relative path grammar, and optional record rejection does not become required-source degradation. Logs, artifacts, URLs, provider IDs, identities, variables, and raw payloads remain private and unpersisted. CI outcomes provide review context only: they cannot suppress findings, prove unrelated absence, change severity/lifecycle, or authorize approval. Policies v1/v2 remain valid without `ci_outcomes`. ([#161](https://github.com/xeonvs/open-code-review-toolkit/issues/161))

### 🐛 Bug Fixes

- Prevent incomplete base/head evidence admission from manufacturing dependency deltas. Once admission for a fact kind is incomplete, all semantic deltas for that kind are omitted with an explicit diagnostic because the missing value cannot be attributed safely to one identity. ([#159](https://github.com/xeonvs/open-code-review-toolkit/issues/159))
- Keep OCR review-filter survivors unverified across multiple review rounds. The mandatory evidence guidance now requires every prior claim to be checked again against current code, tests, and trusted evidence without changing finding, DLP, receipt, or approval schemas. ([#162](https://github.com/xeonvs/open-code-review-toolkit/issues/162))

### 🛠 Maintenance

- Target checksum-verified Open Code Review 1.11.1 as the sole supported runtime for toolkit 0.8.7.

  Changed: small change sets use OCR-owned local grouping below four files, while threshold-crossing changes retain semantic grouping; project `rule.json` file references are confined to the canonical repository root; selected session files follow manifest coverage.

  Unchanged: result and manifest schemas, inherited completion cap `16384`, explicit positive completion-cap transport, default `medium` effort, effective max-tools, private reasoning/session data, DLP, receipts, telemetry ownership, and approval authority.

  Deployment: install OCR 1.11.1 directly and verify the platform checksum from the compatibility manifest; OCR 1.11.0 is historical comparison evidence, not a runtime fallback. ([#158](https://github.com/xeonvs/open-code-review-toolkit/issues/158))
- Update the pinned CI, CodeQL, TestPyPI, release, and build-provenance actions used by protected workflows. ([#165](https://github.com/xeonvs/open-code-review-toolkit/issues/165))

### 📖 Documentation

- Add dynamic stable PyPI version, supported-Python, and Apache-2.0 license badges to the root README. The badges derive product metadata from the supported distribution instead of a hardcoded release or the development-only TestPyPI index. ([#157](https://github.com/xeonvs/open-code-review-toolkit/issues/157))

### 🧩 Rules

- Review Pug (`.pug`), Verilog/SystemVerilog (`.v`, `.vh`, `.sv`), and VHDL (`.vhd`, `.vhdl`) through the built-in OCR 1.11.1 allowlist and language-specific Rules. The upstream allowlist does not include `.svh`. ([#158](https://github.com/xeonvs/open-code-review-toolkit/issues/158))


## 0.8.6 - 2026-08-28

### 🐛 Bug Fixes

- Correct reviewer-guide security classification:

  - **Fixed:** command/shell, SQL/NoSQL, code, template, prompt, LDAP, XPath, CRLF/header, log, HTML/script, and expression injection require explicit vulnerability context; the standalone word `injection` is no longer promoted.
  - **Changed:** neutral phrases such as knowledge or dependency injection no longer inflate the published security count or estimated review effort.
  - **Unchanged:** finding severity, lifecycle, suppression, and approval behavior.

  ([#153](https://github.com/xeonvs/open-code-review-toolkit/issues/153))
- Contain provider-private OCR state at the publication boundary:

  - **Fixed:** reasoning, encrypted/native replay payloads, and request `tool_choice` fields are removed before the canonical OCR result is persisted or receipt v5 is bound.
  - **Changed:** private-only removal preserves a byte-equivalent review projection and approval eligibility; the same fields laundered through findings or warnings become `publication-filtered`.
  - **Unchanged:** receipt v5, public tool-call and reasoning-token counters, DLP reason counts for private-only state, and approval rules.

  ([#155](https://github.com/xeonvs/open-code-review-toolkit/issues/155))

### 🛠 Maintenance

- Qualify the toolkit 0.8.6 OCR dependency:

  - **Changed:** Open Code Review 1.11.0 is the sole accepted runtime; grouping inventory is status-first with churn and the GitLab job timeout is 45 minutes for the default-medium/highest supported round envelope.
  - **Added:** checksum-verified Linux and Darwin evidence plus strict historical-1.10.x-old/1.11.0-new qualification fixtures.
  - **Migration:** deploy toolkit 0.8.6 directly with OCR 1.11.0. OCR 1.10.2 is comparison evidence only, not a supported fallback.
  - **Unchanged:** result/manifest, inherited completion cap `16384`, support for an operator-selected positive completion-cap override, default effort `medium`, receipt v5, DLP, telemetry, summary, and approval contracts. The toolkit leaves that override unset by default and does not recommend a provider-specific value. OCR 1.11.0 corrects max-tools help text only: effective omitted/`0`/`49`/`50` remains `100`, while `101` raises the cap to `101`.

  ([#155](https://github.com/xeonvs/open-code-review-toolkit/issues/155))

### 📖 Documentation

- Refresh installation and operating guidance:

  - **Changed:** Python 3.12–3.14 uses `uv tool install` by default or `pip` only in an activated virtual environment; OCR is installed separately as checksum-verified 1.11.0 and verified with `ocr --version` plus `ocr-ci --help`.
  - **Clarified:** max-tools runtime is unchanged despite corrected help text; reasoning and `tool_choice` stay private; reviewer-guide injection matching is contextual; Ruff formatting is applied and checked before each Python commit.

  ([#155](https://github.com/xeonvs/open-code-review-toolkit/issues/155))

### 🧩 Rules

- **Added:** review Handlebars (`.hbs`) and Mustache (`.mustache`) files through OCR 1.11.0's built-in allowlist and language-specific Rules. Toolkit evidence and publication authority are unchanged. ([#155](https://github.com/xeonvs/open-code-review-toolkit/issues/155))


## 0.8.5 - 2026-08-27

### 🚀 Features

- Classified LLM-provider failures now emit at most one toolkit-authored CI diagnostic line with closed HTTP detail and non-zero aggregate retry counts from a fully validated `ocr.llm-retry-report/v1`.

  - **Added:** HTTP `402` is shown as `http-payment-required`, HTTP `429` as `http-rate-limited`, a uniform status is shown only when all terminal failures share it, and mixed details are deterministically count-aggregated.
  - **Changed:** The `rate-or-spending-limit` GitLab remediation now recommends lowering `OCR_REVIEW_CONCURRENCY` and/or `OCR_LLM_MAX_COMPLETION_TOKENS`, starting a new merge request pipeline, and checking provider request/account limits without claiming either setting caused the failure.
  - **Unchanged:** The GitLab summary/reason, previous-review preservation, DLP, receipt v5, toolkit telemetry, and automatic-approval contracts are unchanged; raw provider-controlled fields and stderr remain private.

  ([#149](https://github.com/xeonvs/open-code-review-toolkit/issues/149))

### 🐛 Bug Fixes

- OCR compatibility classification now sends feature-bearing patch releases to human review instead of allowing adjacent maintenance keywords to misclassify them as `automatic-safe`. ([#151](https://github.com/xeonvs/open-code-review-toolkit/issues/151))

### 🛠 Maintenance

- Open Code Review 1.10.2 is the checksum-pinned runtime dependency for toolkit 0.8.5.

  - **Changed:** The current GitLab example, runtime preflight, compatibility manifest, and qualification evidence move from OCR 1.10.1 to 1.10.2. The inherited OpenAI completion cap remains `16384`, but OCR grouping requests now use that template-owned cap instead of a separate `4096`; an explicit `OCR_LLM_MAX_COMPLETION_TOKENS` continues to override every request.
  - **Changed:** Daily OCR compatibility discovery moves from `05:41 UTC` to `07:15 UTC`; exact-tag manual dispatch remains the recovery path when GitHub delays or omits a scheduled run.
  - **Unchanged:** OCR result and manifest schemas, default `medium` effort, effective max-tools behavior, DLP, receipt v5, toolkit telemetry ownership, and approval contracts are unchanged.

  ([#151](https://github.com/xeonvs/open-code-review-toolkit/issues/151))

### 🧩 Rules

- The recommended OCR 1.10.2 built-in Rules and reviewable-file allowlist now cover Solidity (`.sol`) and Vyper (`.vy`). ([#151](https://github.com/xeonvs/open-code-review-toolkit/issues/151))


## 0.8.4 - 2026-08-26

### 🐛 Bug Fixes

- Correct GitLab review summaries by keeping OCR coverage, publication integrity, findings, and OCR core advisories as independent signals.

  - **Added:** accepted OCR background recommendations are projected as a receipt-bound numeric `ocr.toolkit-advisory/v1` line under Technical details, including failed-result summaries; they no longer become OCR warnings or approval blockers.
  - **Fixed:** complete OCR coverage followed by publication filtering now renders `Review complete with publication filtering`, preserves only exhaustively validated original outcome/count combinations, and does not invent partial-coverage or pathless failed-item diagnostics.
  - **Changed:** horizontal tabs are retained only in `existing_code` and `suggestion_code` after the unchanged value passes all secret, PII, forbidden-value, laundering, and budget checks, and Recommended focus areas are shown only for two or more published findings.
  - **Unchanged:** publication filtering remains warning-bearing and automatic-approval-ineligible; receipt v5, publication-DLP signal v2, manifest/result schemas, secret/PII/laundering/budget checks, ordinary OCR warnings, real partial/budget outcomes, and the existing non-zero tool-call/token summary format remain authoritative.

  ([#145](https://github.com/xeonvs/open-code-review-toolkit/issues/145))

### 🛠 Maintenance

- Qualify and promote checksum-pinned Open Code Review 1.10.1 for toolkit 0.8.4.

  - **Added:** canonical qualification evidence records the hosted OCR 1.10.1 result, completion-cap, medium-effort, and max-tools probes.
  - **Changed:** preflight, the compatibility manifest, and the GitLab example now require OCR 1.10.1. SHA-256 pins are Linux AMD64 `8b806c221d409727a21611b4a7952d8e15edadbbc25f5affccaeb8f677e4055c`, Darwin ARM64 `8fc24bd825c9d918b894be05c0cf27fac8d30bc549257c812d87337167c7563c`, and upstream `sha256sum.txt` `ec72bda51f1227f412ee00602d952868efc57d847cce0ae1586fb97069d4139d`.
  - **Consumed:** bounded private session-cache keys reduce upstream cache-key risk without adding a toolkit receipt or telemetry field.
  - **Unchanged:** result and manifest schemas, inherited OpenAI completion cap `16384`, explicit `4096` override, default `medium` effort, and behaviorally qualified max-tools semantics remain unchanged.
  - **Not consumed:** the upstream GitHub Action, delegate skill, npm launcher, provider preset, and repository-local `providers.go` rule do not alter the toolkit's native-binary, explicit-protocol integration.
  - **Deployment:** update directly from OCR 1.10.0 to 1.10.1; no intermediate OCR version is required.

  ([#146](https://github.com/xeonvs/open-code-review-toolkit/issues/146))

### 🧩 Rules

- OCR 1.10.1 adds `.m` files to its review allowlist and selects MATLAB or Objective-C built-in rules from file content. The upstream repository-local `providers.go` rule is not a toolkit-wide rule. ([#146](https://github.com/xeonvs/open-code-review-toolkit/issues/146))


## 0.8.3 - 2026-08-26

### 🚀 Features

- GitLab technical details now make OCR review activity easier to explain without implying unsupported token attribution.

  - **Added:** the existing inline `all OCR tool calls` line shows every non-zero counter from the closed OCR inspection, review-output, and toolkit context/evidence set instead of collapsing entries after the six most frequent tools.
  - **Unchanged:** aggregate input/output/cache token usage remains separate because OCR does not report per-tool token consumption; raw call arguments, results, dynamic external MCP tool names, receipt v5, DLP, findings, severity, and automatic approval are unchanged.

  ([#142](https://github.com/xeonvs/open-code-review-toolkit/issues/142))

### 🐛 Bug Fixes

- Made OCR compatibility failure publication authoritative and recoverable. The workflow now selects closed status or evidence from the actual qualification outcome, atomically replaces output handoffs, and can publish a failure status without loading unrelated support metadata. It still publishes the bounded issue and diagnostic artifact before returning a red job, while aggregate promotion remains blocked and raw diagnostics remain private. ([#139](https://github.com/xeonvs/open-code-review-toolkit/issues/139))
- Fixed the GitLab example's stale positive `OCR_MAX_TOOLS` default by delegating with sentinel `0`. Added exact parsing for OCR's supported max-tools normalization notice and behavior-based compatibility evidence for numeric CLI boundaries, including the effective template-owned tool-loop value. The notice remains operator-only: raw OCR stderr, findings, result warnings, receipts, DLP, telemetry, lifecycle commands, and automatic-approval semantics are unchanged. ([#140](https://github.com/xeonvs/open-code-review-toolkit/issues/140))

### 🛠 Maintenance

- Keep both macOS endpoint CI jobs as visible best-effort compatibility diagnostics while retaining Linux, coverage, quality, security, dependency, package, and CodeQL checks as release-blocking gates. ([#143](https://github.com/xeonvs/open-code-review-toolkit/issues/143))


## 0.8.2 - 2026-08-25

### 🚀 Features

- Expose OCR 1.10.0 review depth and grouping with explicit operator ownership.

  - **Added:** `OCR_REVIEW_EFFORT` is a closed `low|medium|high` setting written to OCR's root `effort` key. Its exact default is `medium`, selecting up to two review rounds; `low` selects one and `high` selects three. A caller-supplied OCR `--effort` remains the per-run override, and merge-request text cannot select it.
  - **Changed:** OCR may semantically group related changed files and filter findings per group before additional rounds. Group labels, path-derived keys, membership, and round diagnostics remain untrusted private result data and cannot change findings, severity, fingerprints, lifecycle commands, receipt v5, toolkit telemetry, posting, or automatic approval.

  ([#135](https://github.com/xeonvs/open-code-review-toolkit/issues/135))

### 🐛 Bug Fixes

- **Fixed:** Reject caller-owned OCR `--output`, `--output=...`, `-o`, and attached short forms before preview so the new upstream output flag cannot bypass the toolkit-owned result descriptor, atomic validation, DLP, cleanup, or posting handoff. Also make successful compatibility promotion report a caller-supplied relative manifest path without crashing after the update was written. ([#135](https://github.com/xeonvs/open-code-review-toolkit/issues/135))
- **Fixed:** A failed OCR compatibility qualification now still updates the canonical version issue and uploads a bounded `ocr-toolkit.compatibility-status/v1` artifact before the job returns red. Public coordination receives only closed phase, reason, version, and run identity; raw exceptions remain in the private job log, and aggregate promotion stays blocked. ([#136](https://github.com/xeonvs/open-code-review-toolkit/issues/136))

### 🛠 Maintenance

- Qualify and promote the next OCR runtime without losing predecessor or deployment context.

  - **OCR 1.9.10 — inherited predecessor:** Toolkit 0.8.0 and 0.8.1 used exact OCR 1.9.10, whose unset OpenAI completion cap was observed as `max_completion_tokens=58888`. Its checksum-pinned evidence remains unchanged; toolkit 0.8.2 does not require installing or requalifying it.
  - **OCR 1.10.0 — changed target:** Toolkit 0.8.2 preflight and the GitLab example now require checksum-verified OCR 1.10.0. Qualification covers semantic file grouping, path-aware comments, group filtering, one/two/three review rounds, partial-budget reporting, tool/token accounting, the new `--output` flag, private git diagnostics, and the new inherited OpenAI completion cap `max_completion_tokens=16384`. Linux amd64 SHA-256 is `f8f99ea071bed77dbcaa15fdd2083287bb8ae408d5928b3943ebe0788d191b6b`.
  - **Telemetry:** OCR remains authoritative for provider, request, latency, cost, grouping, round, and tool telemetry. OCR 1.10.0 group spans can contain sorted changed paths and model-produced labels; the toolkit defaults OCR telemetry off, does not ingest those values, and adds no exporter or approval/routing signal.
  - **Deployment/Migration:** Deploy toolkit 0.8.2 directly with OCR 1.10.0; do not install OCR 1.9.10 as an intermediate step. Unset `OCR_LLM_MAX_COMPLETION_TOKENS` inherits `16384`; set an explicit value such as `4096` when a gateway-specific invariant is required. Caller `--output`/`-o` remains unsupported because `ocr-ci review --result` owns the private result lifecycle.

  ([#135](https://github.com/xeonvs/open-code-review-toolkit/issues/135))
- **Changed:** Complete the BL-017 review-signal ownership audit with a `no-new-layer` result. OCR retains provider/review telemetry ownership; toolkit receipt, context, DLP, posting, and approval projections retain deterministic lifecycle ownership. No exporter, automatic routing, developer scoring, or duplicate group/round metric schema is added. ([#137](https://github.com/xeonvs/open-code-review-toolkit/issues/137))


## 0.8.1 - 2026-08-24

### 🚀 Features

- Operators can now control the LLM request's completion/output cap independently of OCR context and aggregate review budgets:

  - **Added:** optional `OCR_LLM_MAX_COMPLETION_TOKENS`, accepting decimal integers from `1` through `1000000`. Its exact default is unset, so toolkit 0.8.1 inherits the qualified OCR behavior.
  - **Protocol mapping:** `openai` writes `llm.extra_body.max_completion_tokens`, `openai-responses` writes `max_output_tokens`, and `anthropic` writes `max_tokens`.
  - **Migration:** an equal JSON integer already owned by `OCR_LLM_EXTRA_BODY` is deduplicated; a different or non-integer value fails configuration. Remove the duplicate field or keep the same integer in both inputs.
  - **Deployment:** toolkit 0.8.1 remains on OCR 1.9.10. For a gateway that accepts short probes but rejects a full review before generation, try an explicit value such as `4096`; the toolkit does not derive it from `/models.max_completion_tokens`.
  - **Unchanged:** `OCR_MAX_TOKENS_BUDGET`, OCR prompt/context `max_tokens`, receipt v5, DLP, telemetry, review outcomes, severity, findings, and approval policy are unaffected.

  ([#130](https://github.com/xeonvs/open-code-review-toolkit/issues/130))

### 🐛 Bug Fixes

- Provider configuration and failed-review diagnostics now share one safe boundary:

  - **Fixed:** `ocr-ci configure` and `ocr-ci preflight` now use the same explicit `OCR_LLM_PROTOCOL`, normalized credential-free HTTPS API root, headers, request controls, and auxiliary models URL. Protocol-mismatched terminal endpoints, embedded credentials, fragments, and ambiguous queried `/models` derivation fail closed.
  - **Changed:** a non-zero OCR result with a valid bounded `ocr.llm-retry-report/v1` now produces a toolkit-authored provider-neutral GitLab reason and remediation hint. Runtime `404` remains `endpoint-or-model-not-found`; `429` lists throttling, spending limits, and requested-output cost reservation as possibilities without claiming which occurred.
  - **Privacy:** classified failures ignore normal findings and raw provider/model identities, response bodies, codes/messages, request IDs, paths, warnings, and stderr. `OCR_POST_ERROR_DETAILS=1` does not override this boundary.
  - **Unchanged:** the previous successful review is preserved, automatic approval is not attempted, and receipt v5, DLP, telemetry, severity, finding, and posting-transaction contracts do not change.

  ([#129](https://github.com/xeonvs/open-code-review-toolkit/issues/129))

### 🛠 Maintenance

- Protected validation now assigns each repeated check to one explicit owner:

  - **Changed:** all five supported OS/Python pull-request jobs still run the complete functional suite, while Ubuntu on the newest supported Python is the single owner of combined and risk-group coverage floors.
  - **Removed:** generic `main`-push reruns of CI, package build, Security, and CodeQL; duplicate wheel/sdist construction inside the CI quality job; and duplicate source quality and dependency-audit runs inside the TestPyPI development workflow.
  - **Unchanged:** pull-request Security, CodeQL, Dependency Review, and `Build artifacts` gates; scheduled security analysis; TestPyPI artifact publication, provenance, bounded registry readback, and clean installs; release-pull-request checks; and the complete post-merge stable-release validation.

  ([#132](https://github.com/xeonvs/open-code-review-toolkit/issues/132))


## 0.8.0 - 2026-08-24

### 🚀 Features

- Extends bounded review context while preserving existing policy documents:

  - **Added:** `ocr.review-context-policy/v2` accepts optional `remediation_threads`; `context_list`/`context_get` expose admitted records as opaque `remediation_thread` resources from the ephemeral `ocr.context-store/v2`.
  - **Added:** the checksum-pinned GitLab example exposes `OCR_MAX_TOOLS` with default `30`, matching OCR 1.9.10, and passes it explicitly to each review so integrations can raise the per-file tool-round bound deliberately.
  - **Changed:** rollout guidance separates optional `/models` metadata validation from `ocr llm test` connectivity and from a completed review, and warns that an allowed-to-fail OCR job can leave a pipeline green without usable review evidence.
  - **Changed:** a remediation root now requires the authenticated live bot ID plus a valid toolkit marker/fingerprint, is excluded from generic discussion and reference projections, and always makes the review comment-only. DLP-clean metadata, generic discussions, and adapter records do not independently block automatic approval; DLP rejection and required-source degradation remain blocking.
  - **Migration:** existing `ocr.review-context-policy/v1` documents remain accepted for generic discussions and references. Use policy v2 only when selecting `remediation_threads`; ephemeral stores are rebuilt per run and have no migration step.

  ([#120](https://github.com/xeonvs/open-code-review-toolkit/issues/120))
- Adds live-username lifecycle commands without changing slash-command semantics:

  - **Added:** reviewer lifecycle commands accept exact whole replies `@<live-bot-username> suppress` and `@<live-bot-username> resolve`, using the username returned by authenticated GitLab `GET /user`.
  - **Changed:** existing `/ocr suppress` and `/ocr resolve` behavior is unchanged; typo, prose, code-block, wrong-user, bot/system, `retest`, and non-toolkit-discussion replies remain non-commands, and the newest recognized human command wins.

  ([#125](https://github.com/xeonvs/open-code-review-toolkit/issues/125))

### 🐛 Bug Fixes

- Malformed context policies, provider projections, and persisted remediation counts now fail closed at their owned contract boundaries; exclusive GitLab discussion/remediation limits and omitted reply counts now reflect only the applicable records. Operator adapters cannot request the internal remediation resource class, publishable discussion/reference text gets publication-specific DLP, and per-record text limits remain budget omissions rather than invalid-content failures.
  Toolkit-generated OCR background is now qualified by the installed, preflight-supported OCR executable under `review --preview` before model execution, with the exact production refs, rules, and selection inputs. OCR remains the sole owner of its current thresholds: a recognized soft warning enters the CI log and finalized result summary, while a recognized hard character/file-size rejection produces only an identity-bound closed numeric failure summary. Unknown preview failures remain generic and fail closed; detailed evidence stays available through the built-in MCP, and explicit truncation preserves the mandatory evidence-call instruction.
  Ordinary reviews now remove toolkit-generated evidence, bootstrap, protected rules, context, action receipts, and local DLP diagnostics after both OCR success and failure; only the closed static pre-execution status remains available for the posting handoff when OCR rejects input before model execution.
  If OCR rejects a generated background and preview cleanup also fails, the closed OCR rejection now remains available to the static posting handoff; a cleanup-only failure still blocks model execution and publication. Provider compatibility entry points also convert impossible missing projections into explicit closed errors instead of relying on runtime assertions.
  Repeated `scripts/quality.sh coverage|check` invocations now replace their own log before running, so a current result cannot include stale output from an earlier interrupted or failed invocation. ([#120](https://github.com/xeonvs/open-code-review-toolkit/issues/120))

### 🛠 Maintenance

- **Changed:** Actions storage maintenance now shards its bounded completed-run lookup by UTC day, retaining the ten-page fail-closed limit per shard. It removes completed TestPyPI preview runs after 14 days, TestPyPI development and ordinary runs after 30 days, and stable `Release` runs after 60 days; active and newer runs remain untouched. A run is no longer removed before the longer log-retention promise for its workflow. No operator migration is required. ([#120](https://github.com/xeonvs/open-code-review-toolkit/issues/120))
- Removes obsolete environment and example-only configuration surface:

  - **Removed:** `OCR_GITLAB_BOT_USER_ID`; bot ID and username now come only from authenticated GitLab `GET /user`, with no replacement variable.
  - **Removed:** compatibility alias `OCR_USE_ANTHROPIC`; set `OCR_LLM_PROTOCOL=anthropic`. Any presence of the removed alias now fails configuration instead of silently falling back to the default `openai` protocol.
  - **Removed:** example-only `OCR_RUN_HELPER_TESTS`; run repository tests in the normal lint/test job, not the production review job.
  - **Removed:** documentation-only `OCR_LLM_SUPPORTS_FUNCTION_CALLING`, `OCR_LLM_SUPPORTS_REASONING`, and `OCR_CONFIG_PATH`; these had no supported runtime semantics and have no replacement.

  ([#124](https://github.com/xeonvs/open-code-review-toolkit/issues/124))
- **OCR 1.9.9 — inherited**

  Toolkit 0.7.1 already qualified OCR 1.9.9. Its background-ownership and bounded main-loop diagnostic contracts remain inherited evidence; toolkit 0.8.0 does not require installing or requalifying this predecessor.

  **OCR 1.9.10 — changed**

  - **Changed:** toolkit preflight and `examples/gitlab/ocr-review.gitlab-ci.yml` now accept/pin only OCR 1.9.10 instead of 1.9.9. The Linux amd64 binary is pinned to SHA-256 `359e5bafda1438a47ef389399f4994350e1016371eac1dc17a2c428acb228e6c`.
  - **Changed:** OCR terminal retry diagnostics are grouped by review stage. Structured `ocr.llm-retry-report/v1`, the review result, and `ocr.run-manifest/v1` remain unchanged; `ocr scan` background-wait/resume fixes and the VS Code merge-file change do not affect the toolkit's `ocr review` path.

  **Telemetry**

  The retry report remains private OCR diagnostics. Toolkit 0.8.0 does not ingest it as telemetry or use it for DLP admission, receipts, finding severity, review outcome, or automatic approval.

  **Deployment/Migration**

  Install OCR 1.9.10 directly for toolkit 0.8.0 and update the verified binary checksum. Do not install OCR 1.9.9 as an intermediate step. Any other OCR version fails toolkit preflight.

  ([#126](https://github.com/xeonvs/open-code-review-toolkit/issues/126))
- **Coverage and boundary gates**

  - **Changed:** the combined branch-aware coverage floor increases from 70% to 85%.
  - **Added:** CI and `scripts/quality.sh coverage`/`check` enforce four risk-group floors after the same test run: result/preflight and GitLab posting transactions at 80%; review/context/DLP/approval and MCP/provider/policy/result contracts at 85%.
  - **Added:** fault tests cover bounded result and HTTP parsing, atomic replacement, GitLab read/write retry separation, exact publication and rollback identities, context admission/DLP/approval independence, and provider-neutral discussion contracts.

  No new coverage configuration format or standalone parser is introduced. Deployment agents should run the existing quality wrapper; a group failure identifies the trust boundary that needs regression coverage rather than permitting the combined percentage to mask it.

  ([#127](https://github.com/xeonvs/open-code-review-toolkit/issues/127))

### 📖 Documentation

- **Added:** navigation-only indexes at `docs/README.md`, `docs/codex/README.md`, and `docs/engineering/README.md` route users and maintainers to existing canonical contracts without changing their ownership. ([#123](https://github.com/xeonvs/open-code-review-toolkit/issues/123))
- Reworks the GitLab operator documentation for direct deployment:

  - **Added:** `examples/gitlab/README.md` selects identity-only, metadata, enriched-discussion, enriched-adapter, or direct-MCP operation and documents automatic-approval posture.
  - **Added:** the environment reference lists every supported variable with owner, requirement, exact default, and behavior; the discussion-policy guide explains when to select generic discussions, verified remediation history, both, or adapters.
  - **Added:** `examples/gitlab/accepted-decisions.md` and the later-merge-request `ocr_toolkit_evidence` `list`/`get` walkthrough show both creation and use of accepted decisions.
  - **Migration:** context recipes moved from `examples/context/` to `examples/gitlab/context/` and split into `policy-discussions.json` and `policy-adapters.json`; the runtime protected-target path remains `.opencodereview/review-context-policy.json`.

  ([#124](https://github.com/xeonvs/open-code-review-toolkit/issues/124))

### Security

- `ocr-ci review --preserve-private-artifacts` can retain owner-only OCR session/context state for local diagnosis without creating a posting receipt. It also writes a bounded, value-free `ocr.private-dlp-decisions/v1` sidecar with JSON path, detector subtype, size units, SHA-256, and explicit truncation counts so operators can diagnose conservative false-positive classes locally. Ordinary and validated GitLab merge-request execution never retain this attribution; the latter rejects the flag before OCR starts and keeps deterministic cleanup mandatory. ([#120](https://github.com/xeonvs/open-code-review-toolkit/issues/120))


## 0.7.1 - 2026-08-21

### 🚀 Features

- Expose semantically distinct all-OCR tool totals, verified MCP-server calls, reconciled count-only `summary`/`list`/`get` evidence actions, and closed provider-neutral token buckets without publishing arguments or provider payloads. ([#116](https://github.com/xeonvs/open-code-review-toolkit/issues/116))
- Recommended focus areas now ranks already-published findings deterministically by severity, category, safe repository location, and stable identity before applying its existing display cap. ([#117](https://github.com/xeonvs/open-code-review-toolkit/issues/117))
- Target checksum-verified Open Code Review 1.9.9 after adapting toolkit-owned background handling and qualifying named main-loop failure reasons. ([#118](https://github.com/xeonvs/open-code-review-toolkit/issues/118))

### 📖 Documentation

- Correct the v0.7.0 release-note classification and document how qualified OCR maintenance, compatibility-driven fixes, adopted upstream capabilities, rules changes, and CI impact receive distinct changelog categories. ([#114](https://github.com/xeonvs/open-code-review-toolkit/issues/114))

### Security

- Introduce receipt v5 with distinct `passed`, `private-sanitized`, and `publication-filtered` states. Private-only redaction may continue through existing approval gates only when the canonical publication and approval projection is byte-equivalent; changed, malformed, or incomparable projections remain partial and ineligible. ([#115](https://github.com/xeonvs/open-code-review-toolkit/issues/115))


## 0.7.0 - 2026-08-20

### 🚀 Features

- Add protected-policy bounded review enrichment with stable GitLab discussions, authorized stdio or HTTPS adapter records, opaque local context handles, publication DLP, isolated OCR sessions, receipt v4, and conservative approval gates. DLP atomically destroys rejected values: unsafe publication sinks yield an explicit safe partial review, while private-only fields are sanitized without losing a still-valid manifest or safe findings. Filtered runs preserve prior findings, match duplicates one-for-one, block approval, and emit closed summary/log signals for optional alerting. ([#112](https://github.com/xeonvs/open-code-review-toolkit/issues/112))

### 🐛 Bug Fixes

- Publish a closed protected-target setup-pending result when a merge request safely introduces the configured repository-owned OCR rules path, without trusting source contents or exposing private diagnostics. ([#107](https://github.com/xeonvs/open-code-review-toolkit/issues/107))
- Reject completed non-skipped reviews unless OCR recorded an `ocr_toolkit_evidence(action=summary)` call, fixing the bootstrap and acceptance path that could otherwise finish without model evidence use. A toolkit self-query does not count. ([#111](https://github.com/xeonvs/open-code-review-toolkit/issues/111))
- Preserve useful review output when DLP rejects only part of an OCR result: unsafe publication units become an explicit safe partial review, while unsafe private-only fields are atomically sanitized without discarding the original manifest or safe findings. Retain prior findings without duplicate reposting, count repeated fingerprints correctly, replace repeated setup-pending notes, avoid PII false positives for SHA/build identifiers, and bind DLP inspection, projection, receipt attachment, and result replacement to one inode-checked operation.

  Harden the new bounded-context boundaries found during final real-OCR review: reject malformed URL authorities, cursors, mixed-type adapter configuration, recursive stores, hidden HTML/entity output, changed duplicate objects, and repository-owned OCR executables; cover stdio request delivery with the adapter deadline; apply admission budgets after authorization and deduplication; stop GitLab pagination at the protected thread bound; and preserve the mandatory evidence instruction under the smallest supported bootstrap budget. ([#112](https://github.com/xeonvs/open-code-review-toolkit/issues/112))

### 🛠 Maintenance

- Qualify Open Code Review 1.9.7 as the adjacent compatibility baseline after verifying review, result, manifest, MCP, and session contracts and confirming that no toolkit runtime or CI adaptation was required. ([#109](https://github.com/xeonvs/open-code-review-toolkit/issues/109))
- Promote the recommended OCR release to checksum-verified 1.9.8 after qualifying its Bedrock provider addition, human-audience progress routing to stderr, and native-severity skill guidance as compatible changes that the toolkit does not consume. The OCR promotion required only version and checksum pin changes in toolkit CI. ([#108](https://github.com/xeonvs/open-code-review-toolkit/issues/108))

### 📖 Documentation

- Document context modes, policy and proxy schemas, adapter authorization, completeness, handles, publication and retention boundaries, cleanup, migration, and synthetic deployment recipes. ([#112](https://github.com/xeonvs/open-code-review-toolkit/issues/112))

### 🧩 Rules

- Preserve unknown GitLab CI effective values across unresolved `extends` and includes unless an explicit local override or bounded compiled fact proves them. ([#110](https://github.com/xeonvs/open-code-review-toolkit/issues/110))

### Security

- Close publication-source laundering and local execution paths in M5 by scanning decoded HTML source before rendered-text stripping, accepting marker identities only in toolkit-owned note preambles, bounding stdio request delivery, and refusing relative or repository-owned OCR executable resolution. Unsafe private-only OCR fields are redacted in the atomic result transform and emit the same closed receipt, summary, and log signal without retaining rejected values or locations. ([#112](https://github.com/xeonvs/open-code-review-toolkit/issues/112))


## 0.6.3 - 2026-08-18

### 🚀 Features

- Add bounded GitLab merge-request context selection and receipt-v3 approval controls: identity-only mode is the default, optional complete metadata remains eligible, degraded context or external MCP stays comment-only, and source/author movement or self-approval performs no approval write. ([#100](https://github.com/xeonvs/open-code-review-toolkit/issues/100))
- Recover an ambiguous GitLab inline create only from one complete author-bound marker match, without retrying or falling back, and track recovered draft/discussion identities for exactly-once publication and baseline-guarded rollback. ([#101](https://github.com/xeonvs/open-code-review-toolkit/issues/101))

### 🧩 Rules

- Target checksum-verified Open Code Review 1.9.6 after qualifying 1.9.6. ([#105](https://github.com/xeonvs/open-code-review-toolkit/issues/105))


## 0.6.2 - 2026-08-17

### 🚀 Features

- Target checksum-verified Open Code Review 1.9.5 and expose its aggregate review-token budget as an explicit synthetic GitLab CI setting while preserving partial findings and incomplete-coverage reporting. ([#93](https://github.com/xeonvs/open-code-review-toolkit/issues/93))

### 🐛 Bug Fixes

- Verify development TestPyPI PEP 740 attestations against the exact `testpypi.yml` publisher and artifact subjects, and isolate repeated registry verification by version so stale artifacts cannot enter install evidence. ([#93](https://github.com/xeonvs/open-code-review-toolkit/issues/93))

### 🧩 Rules

- The recommended OCR built-in rules now add Swift-specific review guidance and exclude conventional Swift test files by default. ([#93](https://github.com/xeonvs/open-code-review-toolkit/issues/93))


## 0.6.1 - 2026-08-15

### 🚀 Features

- Add top-level `ocr-ci --version` reporting from the installed package version metadata. ([#88](https://github.com/xeonvs/open-code-review-toolkit/issues/88))
- Expose bounded redacted merge-request title, description, labels, and source-branch context as untrusted invocation evidence while blocking automatic approval for runs that admit mutable author-controlled intent. ([#89](https://github.com/xeonvs/open-code-review-toolkit/issues/89))
- Target checksum-verified Open Code Review 1.9.4 after human qualification of its unchanged JSON result contract and terminal-only session correlation output. ([#90](https://github.com/xeonvs/open-code-review-toolkit/issues/90))

### 🐛 Bug Fixes

- Derive every release URL and wheel path in the synthetic GitLab example from its single toolkit version pin. ([#86](https://github.com/xeonvs/open-code-review-toolkit/issues/86))
- Use the current protected GitLab target commit for repository-owned OCR rules, accepted decisions, and project guidance without changing the forge-defined review range. ([#87](https://github.com/xeonvs/open-code-review-toolkit/issues/87))
- Prioritize changed templates on both immutable review refs before unchanged inventory, preserving typed template evidence under the existing bounded fact limits. ([#88](https://github.com/xeonvs/open-code-review-toolkit/issues/88))

### 📖 Documentation

- Adopt Contributor Covenant 2.1 with a confidential conduct-reporting route and links from the public contributor documentation. ([#86](https://github.com/xeonvs/open-code-review-toolkit/issues/86))
- Add repository-specific OpenSSF Scorecard and CodeQL status badges to the README. ([#91](https://github.com/xeonvs/open-code-review-toolkit/issues/91))


## 0.6.0 - 2026-08-14

### 🚀 Features

- Improve repository-aware reviews and their GitLab result presentation:

  - Add target-branch structured accepted decisions and nested project guidance through the existing read-only evidence MCP, with deterministic scopes, applicability, staleness, precedence, and self-authorization safeguards.
  - Isolate malformed or oversized policy entries, preserve global root guidance when changed-path identity is empty, and keep complete multibyte or redaction-expanded policy values within persistence and MCP budgets.
  - Separate collection and persistence responsibilities into explicit internal packages while retaining the supported evidence API and one collector/store/MCP lifecycle.
  - Preserve source provenance when semantic facts collide, reject ambiguous post-redaction mappings, validate snapshot indexes before serialization, and make atomic store replacement durable where the platform supports directory synchronization.
  - Combine review health and finding publication into one clear outcome line while preserving warning, incomplete-coverage, posting-limit, suppression, and failure states, and add opt-in closed-enum Shields badges for individual GitLab findings with a private-safe text fallback.

  ([#81](https://github.com/xeonvs/open-code-review-toolkit/issues/81))
- Target checksum-verified Open Code Review 1.9.3 after adjacent compatibility qualification. ([#82](https://github.com/xeonvs/open-code-review-toolkit/issues/82))

### 📖 Documentation

- Document the repository threat model and security-review calibration so contributors, researchers, and automated security scans share the same assets, attacker capabilities, trust boundaries, and reportability context. ([#81](https://github.com/xeonvs/open-code-review-toolkit/issues/81))

### Security

- Scope the destructive GitHub Actions storage permission to the cleanup job, and harden repository policy evidence against Markdown delimiter injection, irrelevant-guidance saturation, forged schema-v3 provenance/applicability, and legacy trust-label confusion. ([#81](https://github.com/xeonvs/open-code-review-toolkit/issues/81))


## 0.5.0 - 2026-08-12

### 🚀 Features

- Add a bounded ecosystem-adapter layer plus framework and template evidence plugins for Jinja2, Go web frameworks, Symfony/PHP, and React/TypeScript, including unambiguous root components, applicability-aware Go replacements, include-graph completeness, fail-closed provider isolation, scoped coverage, and first-class redacted delta queries through the built-in evidence MCP. ([#77](https://github.com/xeonvs/open-code-review-toolkit/issues/77))
- Target checksum-verified Open Code Review 1.9.2 after adjacent compatibility qualification. ([#78](https://github.com/xeonvs/open-code-review-toolkit/issues/78))

### 🐛 Bug Fixes

- Make stable release recovery idempotent across private draft Releases, already-published registry artifacts, and exact issue-receipt comment readback, while binding release notes, assets, and issue evidence to their validated file descriptors. ([#76](https://github.com/xeonvs/open-code-review-toolkit/issues/76))

### 🧩 Rules

- Make Jinja and Twig templates reviewable through explicit additive includes and template-specific rules in the synthetic GitLab rules pack. ([#77](https://github.com/xeonvs/open-code-review-toolkit/issues/77))


## 0.4.7 - 2026-08-11

### 🚀 Features

- Add default-on `OCR_AUTO_APPROVE` for conservative, exact-SHA GitLab approval after every current review note publishes, with an explicit fail-closed opt-out and bounded status readback.
  Limit eligibility to complete manifest-backed reviews with at most three low-severity style, documentation, or maintainability findings, while preserving every existing approval when a later review is ineligible or disabled. ([#71](https://github.com/xeonvs/open-code-review-toolkit/issues/71))
- Target checksum-verified Open Code Review 1.9.1 after qualifying 1.9.0 through 1.9.1. ([#72](https://github.com/xeonvs/open-code-review-toolkit/issues/72))

### 🐛 Bug Fixes

- Publish an actionable GitLab suggestion only when `existing_code` proves that the replacement applies to one contiguous range in the immutable reviewed head.
  Retain the explanatory finding, with a bounded non-sensitive omission reason, when a replacement is stale, malformed, multi-region, diff-prefixed, or otherwise unverifiable. ([#70](https://github.com/xeonvs/open-code-review-toolkit/issues/70))

### 📖 Documentation

- Document the established evidence and MCP architecture, reconcile the completed 0.4.6 lifecycle and remaining backlog with current code, and index archived execution history by stable release tag.
  Make the release pull request the final repository mutation while exact-tree authorization, registry and provenance verification, an immutable machine-readable receipt, and idempotent issue closure prove external delivery after merge. ([#69](https://github.com/xeonvs/open-code-review-toolkit/issues/69))

### 🧩 Rules

- The recommended OCR built-in rules and reviewable-file allowlist now include Nim source, script, and package files. ([#73](https://github.com/xeonvs/open-code-review-toolkit/issues/73))


## 0.4.6 - 2026-08-08

### 🚀 Features

- Target checksum-verified Open Code Review 1.8.10 after reviewing the complete 1.8.9 through 1.8.10 compatibility chain; valid toolkit CLI, result, MCP, configuration, and GitLab contracts remain compatible. ([#66](https://github.com/xeonvs/open-code-review-toolkit/issues/66))


## 0.4.5 - 2026-08-05

### 🚀 Features

- Target checksum-verified Open Code Review 1.8.8 after reviewing the complete 1.8.7 through 1.8.8 compatibility chain and recording per-run provider/model and result-identity capabilities. ([#61](https://github.com/xeonvs/open-code-review-toolkit/issues/61))

### 🔧 Refactoring

- Qualify consecutive OCR patch releases as one ordered chain, keeping adjacent release comparisons separate from the currently tested baseline and preparing an automatic update only when every release is safe. ([#60](https://github.com/xeonvs/open-code-review-toolkit/issues/60))

### 🧩 Rules

- Accept OCR 1.8.8's Nix and Haskell allowlist and built-in rule support as an effective review-scope expansion; toolkit evidence-pack backlog items remain separate and unfinished. ([#61](https://github.com/xeonvs/open-code-review-toolkit/issues/61))


## 0.4.4 - 2026-08-03

### 🚀 Features

- Redesign GitLab summaries around independent review health, published findings, and bounded failed-file coverage diagnostics, with aggregate finding emoji and operational metadata under technical details. ([#42](https://github.com/xeonvs/open-code-review-toolkit/issues/42))

### 🐛 Bug Fixes

- Represent scoped evidence completeness explicitly, distinguish static, dynamic, and executable Ansible inventory sources, collect supported recursive role defaults and vars without execution, and omit exact no-op suggestions while retaining their findings. ([#41](https://github.com/xeonvs/open-code-review-toolkit/issues/41))


## 0.4.3 - 2026-08-03

### 🚀 Features

- Target checksum-verified Open Code Review 1.8.6, support its versioned run manifest, keep one compatibility issue per upstream version with release-change context and bounded transient download retries, and bound GitHub Actions cache, artifact, and log retention. ([#49](https://github.com/xeonvs/open-code-review-toolkit/issues/49))

### 🧩 Rules

- Adopt OCR 1.8.6 default review exclusions for snapshots, testdata, fixtures, and generated files. ([#49](https://github.com/xeonvs/open-code-review-toolkit/issues/49))


## 0.4.2 - 2026-07-31

### 🚀 Features

- Qualify OCR 1.8.3 after its per-file terminal-state and Cobra CLI changes, recommend it with exact checksums, and retain the existing toolkit result, command, and rules contracts. ([#38](https://github.com/xeonvs/open-code-review-toolkit/issues/38))


## 0.4.1 - 2026-07-31

### 🚀 Features

- Qualify OCR 1.8.1 and 1.8.2, recommend OCR 1.8.2 with exact checksums, and preserve findings and usage metadata when OCR returns a token-budget-limited partial review. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))

### 🐛 Bug Fixes

- Authenticate scheduled GitHub release-metadata checks without forwarding credentials to public asset downloads, preventing anonymous API rate limits from interrupting compatibility monitoring. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))

### 📖 Documentation

- Use conditional emoji headings in changelogs and append an exact comparison link to GitHub Release notes. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))

### 🧩 Rules

- **OCR allowlist:** Add Prisma schema review support from OCR 1.8.1. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))
- **OCR built-in rules:** Add PHP and Composer review guidance from OCR 1.8.2. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))
- **Toolkit rules:** `examples/gitlab/rules.json` is unchanged; integrations receive these additions by updating OCR rather than copying a new toolkit rules file. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))
- **OCR built-in rules:** Add comprehensive Go review guidance from OCR 1.8.1. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))
- **OCR allowlist:** Add Protocol Buffers (`.proto`) review support from OCR 1.8.2. ([#35](https://github.com/xeonvs/open-code-review-toolkit/issues/35))


## 0.4.0 - 2026-07-31

### Features

- Add the repository evidence architecture for OCR reviews:

  - collect schema-versioned facts and immutable base/head deltas through bounded Git reads;
  - prepare private evidence, compact bootstrap, and composed MCP configuration automatically in `ocr-ci review`;
  - expose detailed context on demand through the built-in read-only evidence MCP instead of embedding legacy Markdown;
  - preserve Ansible Galaxy role and collection declarations, optional sources and versions, and bounded requirement includes as typed immutable evidence with explicit degradation diagnostics;
  - preserve Python declarations, runtime constraints, dependency groups, recursive requirements includes, and resolved uv, Poetry, Pipenv, and standardized lock facts as bounded typed evidence available through the built-in MCP;
  - require Python 3.12 or newer for toolkit 0.4 while retaining tested support through Python 3.14;
  - preserve JavaScript runtime and package-manager constraints, scoped package declarations, and resolved npm, Yarn, and pnpm lock facts as bounded typed evidence;
  - preserve Go module identity, language and toolchain declarations, direct/indirect requirements, replacements, exclusions, and resolved `go.sum` checksums as bounded typed evidence;
  - preserve Composer/PHP package identity, production/development links, virtual-platform constraints, safe repository-source classifications, resolution policy, and resolved lock metadata as bounded typed evidence;
  - preserve application and infrastructure version pins, nested container images, and Ansible role vars as bounded typed evidence with safe exclusions and immutable deltas; and
  - bind a safe review-time MCP-use receipt to the private OCR result and report independently configured servers that OCR actually used while omitting unused servers and sensitive connection details.

  ([#30](https://github.com/xeonvs/open-code-review-toolkit/issues/30))

### Bug fixes

- Improve GitLab review summaries:

  - distinguish skipped, clean, warning, error, and finding outcomes;
  - omit zero-value counters that do not help the reviewer;
  - add severity and category emoji that can be disabled through configuration;
  - refresh the development toolchain and immutable GitHub Actions pins, and cover every supported Python minor in CI;
  - negotiate the MCP 2025-11-25 revision used by Open Code Review 1.8.0 while retaining the older supported revisions;
  - launch the built-in evidence MCP through the toolkit's current Python installation so reviews do not depend on the caller's executable search path;
  - keep evidence records and deltas recursively immutable, and revalidate persisted values, metadata, diagnostics, and limits before serving them through MCP;
  - preserve semantic dependency and infrastructure facts across supported Ansible, Python/Poetry, JavaScript, Go, Composer, lockfile, URL, variable, tag, and digest variants, with explicit bounded-traversal notices;
  - harden evidence parsing and persistence against type-confused JSON, unusual Git paths, nested manifest variants, duplicate identities, descriptor reuse, and provider-controlled summary text;
  - keep repository evidence snapshots, private artifacts, bootstrap diagnostics, MCP requests, immutable OCR refs, result reads, and fallback Markdown safe and atomic at their trust boundaries;
  - bind evidence and GitLab remap reads to authenticated Git objects despite repository replacement refs or inherited Git configuration, and bound existing OCR configuration before parsing it; and
  - add a pinned, history-aware local Gitleaks gate so secret-shaped content is rejected before branch publication as well as in CI.

  ([#30](https://github.com/xeonvs/open-code-review-toolkit/issues/30))


## 0.3.1 - 2026-07-28

### Features

- Qualify Open Code Review 1.8.0 as the tested and recommended baseline, add native HTTPS Streamable HTTP MCP servers with environment-backed headers while preserving stdio fallback, and run OCR through a private-artifact wrapper that emits bounded redacted failure diagnostics to CI logs without posting. Repair interrupted package metadata only inside the disposable quality environment and avoid repeated synchronization noise. ([#24](https://github.com/xeonvs/open-code-review-toolkit/issues/24))


## 0.3.0 - 2026-07-28

### Features

- Add a bounded Bandit security gate and checksum-verified OCR compatibility qualification without automatic upstream upgrades. ([#19](https://github.com/xeonvs/open-code-review-toolkit/issues/19))

### Documentation

- Correct roadmap dependencies and rollout invariants for external MCP, repository evidence, compact bootstrap, and framework selection. ([#17](https://github.com/xeonvs/open-code-review-toolkit/issues/17))


## 0.2.1 - 2026-07-27

### Features

- Target Open Code Review 1.7.17 in preflight validation and the checksum-pinned GitLab CI example. ([#12](https://github.com/xeonvs/open-code-review-toolkit/issues/12))

### Documentation

- Document the durable toolkit strategy, milestone roadmap, and reconciled implementation backlog. ([#13](https://github.com/xeonvs/open-code-review-toolkit/issues/13))


## 0.2.0 - 2026-07-21

### Features

- Target Open Code Review 1.7.14 in preflight validation and the checksum-pinned GitLab CI example. ([#11](https://github.com/xeonvs/open-code-review-toolkit/issues/11))
- Replace the ambiguous `/ocr keep` and `/ocr skip` discussion replies with `/ocr resolve` and `/ocr suppress`, preserve human-owned deduplication, and document the complete GitLab review lifecycle for developers and CI operators. ([#8](https://github.com/xeonvs/open-code-review-toolkit/issues/8))

### Bug fixes

- Allow stable release verification to coexist with previously published development builds of the same base version on TestPyPI. ([#10](https://github.com/xeonvs/open-code-review-toolkit/issues/10))
- Treat ordinary merged pull requests as a successful no-op in the production release workflow while keeping release-branch authorization fail-closed. ([#7](https://github.com/xeonvs/open-code-review-toolkit/issues/7))

### Security

- Mark every source-distribution smoke install as hash-required while retaining the no-dependency boundary, and document the single-maintainer security posture and Scorecard triage policy. ([#6](https://github.com/xeonvs/open-code-review-toolkit/issues/6))

### Documentation

- Reduce the routine Ubuntu CI matrix to the supported Python 3.10 and 3.14 endpoints, matching the macOS matrix. ([#10](https://github.com/xeonvs/open-code-review-toolkit/issues/10))
- Document accepted project decisions, their optional `ocr-accept` marker convention, and the guard that prevents a merge request from whitelisting its own findings. ([#11](https://github.com/xeonvs/open-code-review-toolkit/issues/11))


## 0.1.0 - 2026-07-20

### Features

- Publish one deterministic, checksum-verified TestPyPI development build after every merge into `main`, with bounded registry downloads and idempotent reruns. ([#4](https://github.com/xeonvs/open-code-review-toolkit/pull/4))
- Target Open Code Review 1.7.13 in preflight validation and the pinned GitLab CI example. ([#4](https://github.com/xeonvs/open-code-review-toolkit/pull/4))
- Support and continuously test Python 3.14 while retaining Python 3.10-3.13 compatibility. ([#4](https://github.com/xeonvs/open-code-review-toolkit/pull/4))
- Publish reproducible 0.1.0 distributions to TestPyPI and PyPI with exact hash verification, provenance attestations, and immutable GitHub Release assets.
- Introduce the standalone `ocr-ci` toolkit with safe context generation, GitLab posting, runtime configuration, MCP configuration, and preflight checks.

### Bug fixes

- Bind production release smoke tests to the exact reviewed wheel and sdist hashes, with bounded HTTPS downloads from TestPyPI and PyPI. ([#4](https://github.com/xeonvs/open-code-review-toolkit/pull/4))
- Use `OCR_REVIEW_LANGUAGE` as the single safe language setting for OCR configuration and generated review context, with English as the default and Russian as an explicit option. ([#4](https://github.com/xeonvs/open-code-review-toolkit/pull/4))
- Preserve bounded context and version discovery with a 7,950-character ceiling, improve provider billing classification, and prevent cross-file remapping of findings that already name a path. ([#3](https://github.com/xeonvs/open-code-review-toolkit/pull/3))

### Security

- Require secure credential endpoints, block unsafe GitLab redirects, redact secret-shaped environment values, and reduce GitHub Actions credential persistence and permissions. ([#3](https://github.com/xeonvs/open-code-review-toolkit/pull/3))

### Documentation

- Document the checksum-verified TestPyPI prerelease path used before the public stable release. ([#2](https://github.com/xeonvs/open-code-review-toolkit/pull/2))


# Changelog

Changes for each release are assembled from `changelog.d/` by Towncrier.
