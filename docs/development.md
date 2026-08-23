# Development

Install [uv](https://docs.astral.sh/uv/) and use the committed lockfile:

```console
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run mypy src/ocr_toolkit
uv run bandit -r src/ocr_toolkit --severity-level medium --confidence-level medium
uv run pytest --cov=ocr_toolkit --cov-report=term-missing --cov-fail-under=70
uv run python -m build
uv run twine check dist/*
```

For routine agent and contributor checks, prefer `scripts/quality.sh check`. It captures successful output under ignored `.quality-logs/` and prints only a short status; on failure it prints the last 80 lines. Individual modes are `format`, `lint`, `test`, `coverage`, `types`, and `security`. The Bandit gate scans only the supported runtime package at medium-or-higher severity and confidence; tests and synthetic fixtures are intentionally outside that bounded gate.

Runtime code must remain compatible with Python 3.12-3.14 and standard-library-only. Tests must use synthetic data; public examples must use safe placeholder hosts and credentials while describing the real operating behavior rather than labelling the feature itself as synthetic. User-visible changes require a fragment in `changelog.d/`.
Repository-only qualification tools and evidence live under `scripts/` and `compatibility/`; they are excluded from both published distributions. Validate the manifest with `PYTHONPATH=src python scripts/ocr_compat.py validate`.

For artifact smoke tests, install the wheel and sdist into separate temporary virtual environments and run `ocr-ci --help`. Generic secret scanning uses Gitleaks; dependency auditing uses `pip-audit`. Install the exact Gitleaks version printed by `scripts/gitleaks.sh --version`, then run `scripts/gitleaks.sh` before pushing and `scripts/quality.sh check` for the Python quality matrix. The wrapper fails closed when the scanner version or base ref is unavailable, scans the complete first-parent feature history, and is also the single source for the hosted security job's version pin. TestPyPI and stable-release workflows do not duplicate that dedicated security job.

`tests/test_installed_policy_e2e.py` builds both the direct wheel path and the sdist-to-wheel path, installs each into a clean environment, and exercises target decisions and nested guidance through the real stdio MCP. It runs with a hostile repository shadow package, restricted `PATH`, owner-only artifacts, and the installed console entry point; keep package-boundary changes inside that test rather than replacing it with editable-install mocks.

GitHub Actions storage is repository-owned infrastructure. CI restores setup-uv caches on pull requests but saves them only from `main`; CodeQL TRAP caching and the separately controlled v4 overlay-database mode are disabled, so the small repository receives a full analysis without per-run CodeQL cache writes. Workflow artifacts use a seven-day handoff window. The weekly **Actions storage maintenance** workflow grants `actions: write` only to its cleanup job and deletes all CodeQL caches, non-main or superseded setup-uv caches, superseded Gitleaks caches, artifacts older than seven days, ordinary logs older than 14 days, and release/TestPyPI logs older than 30 days. It also deletes completed TestPyPI development/preview runs after 14 days, ordinary completed runs after 30 days, and stable Release runs after 60 days; deleting a run removes that run's metadata while active and newer runs remain untouched. The scheduled collector reads a closed 74-day UTC window in daily shards, retaining a fail-closed ten-page limit per day instead of applying that limit to the aggregate run history. Scheduled log cleanup uses a bounded 14-day retry window so immutable run history does not get scanned and retried forever. Manual dispatch is a dry run unless `execute` is selected; the same plan is available locally with `python scripts/actions_cleanup.py`, requires `--execute` for deletion, and accepts `--include-all-old-logs` for a deliberate one-time historical log cleanup.

## Planning and documentation lifecycle

`PLANS.md` contains complete active or blocked repository work, including release classification, target version, service boundaries, validation, and exact resume state. Before a logical commit, update the plan and every directly affected status-bearing document to describe post-commit truth. A milestone closes only after current implementation and tests prove its own outcome; reconcile the roadmap table and diagram, backlog, strategy, and README without deleting unfinished adjacent scope.

Historical wording is evidence, not a specification. Rebuild a capability matrix from current code, tests, and published behavior before retaining backlog work or dependency edges. Keep implementation, safety, and rollout dependencies distinct so conditional future work does not block an independently safe capability. Completed stable plans follow the archive lifecycle owned by [the release guide](release.md#external-reconciliation-and-plan-archiving).

When a failure recurs, classify its cause before changing guidance: add or repair the canonical requirement when it is missing or conflicting, correct startup selection when it was not loaded, and otherwise add or repair the concrete subsystem control. Add a pitfalls entry only for a distinct reusable incident class with historical evidence; the catalogue itself does not own the correction.

## Long-running command waits

Wait for a long-running local command through one completion-driven waiter when the execution environment exposes a persistent process or session identity. The waiter stays attached until exit, cancellation, or the command's overall deadline and returns as soon as that terminal state occurs. Internal infrastructure waits must not yield periodic empty observations back to the model: repeated model-driven `status`, terminal, or process polls add tool results and task history without changing a decision. The waiter is a completion signal, never the only copy of command output or a required result: its transport or model-facing output can be truncated, discarded after completion, or lost with the session.

Keep the wait bounded and diagnosable:

- assign an overall command deadline and preserve a cancellation path; terminate and clean up owned child processes when either is reached;
- before starting the process, choose explicit ignored owner-only paths outside any transient directory that the command cleans up, remove or reject stale owned artifacts, and have the process atomically publish every result required for later validation;
- redirect potentially large stdout and stderr to ignored private files and preserve them until their focused inspection is complete; return from the waiter only the exit status, elapsed time, artifact paths, digests, and a bounded diagnostic tail or structured summary;
- validate the persisted artifact's type, ownership/permissions, size, completion marker or exact schema, and digest before trusting it; a missing or invalid artifact is a failed/inconclusive run, not permission to reconstruct the result from a truncated waiter transcript;
- retain enough process or session identity to distinguish completion from a lost waiter, but do not expose credentials, inherited environment, unbounded logs, or result bodies through the waiter;
- let the outer wait return immediately on process completion even when its maximum deadline is much longer; and
- inspect full logs only after a concrete failure makes a focused range relevant.

Use periodic polling only when no completion notification or persistent waiter exists, when the process can require interactive input, or when intermediate state can change an authorized operational decision. In that fallback, choose an interval proportionate to expected duration, suppress unchanged observations, and increase the interval for stable work. Delete preserved private artifacts only after the relevant evidence has been extracted and verified. This discipline reduces redundant model turns and context growth; it does not waive required monitoring, validation evidence, timeouts, cleanup, or the cost of analyzing the eventual result, and it makes no exact subscription-billing claim.

## Local validation

Select checks from the changed boundary rather than from an ever-growing generic prohibition list. Start with the narrowest reproducer, then run the applicable contract tests and the complete quality gate before release handoff. In particular:

- parser changes exercise the semantic grammar and bounded degradation;
- repository, persistence, subprocess, network, provider-write, and report changes use the [cross-cutting trust invariants](engineering/project_principles.md#trust-boundary-invariants) and the checklist below;
- package or executable-integration changes include clean wheel and sdist validation rather than mocks alone;
- public-source changes keep private audit material untracked and run the pinned complete-range Gitleaks wrapper before push; and
- release changes run the release authorization, receipt, workflow, artifact, and documentation suites owned by `docs/release.md`.

Safe bounded read-only diagnostics are allowed. A boundary rule prohibits the unsafe acquisition, trust transition, or mutation mechanism, not HTTP, subprocesses, provider APIs, file cleanup, or debugging as whole categories.

For every boundary or integration claim, write down the production owner, the entry point exercised, the observable result, and any external collaborator replaced by a test double. The double must sit beyond the claimed boundary: do not mock the Git reader to prove Git isolation, the HTTP adapter to prove redirect or byte limits, the store loader to prove hostile readback, the subprocess launcher to prove argv or descriptor behavior, or the MCP dispatcher to prove stdio protocol behavior. A mocked-owner test may prove orchestration only and must be paired with a production-path test before the broader claim is accepted. Prefer real temporary repositories, local HTTP peers, child processes, persisted files, stdio clients, and clean installed wheel/sdist environments. Make hostile cases traverse the same owner and assert the intended rejection branch rather than an earlier mock-selected failure.
The maintained [test evidence matrix](engineering/test_evidence_matrix.md) records those owners, entry points, external qualifications, and non-claims across the complete suite. Update it when a new boundary claim is introduced or when a test double moves across an existing owner.

Treat one confirmed boundary or parser defect as a risk class: inspect sibling implementations, make negative tests reach the intended rejection or degradation branch, and assert that contract rather than an unrelated earlier failure. Before implementing a new parser or trust boundary, record its grammar, normalization, degradation, budget units, inherited-process state, and adversarial fixtures in the active plan or focused tests.

New runtime modules, classes, and functions need purpose-focused docstrings. Comments at non-obvious security, compatibility, ownership, and state-transition boundaries explain why the constraint exists rather than narrating the code. Do not add legacy namespace shims or historical integrations outside the public contract.

Apply the [cohesive-module invariant](engineering/project_principles.md#product-and-architecture) during self-review. Prefer an extract-and-delegate refactor that moves already characterized functions or classes intact, preserves the intentional package facade, and reruns the same contract suite before and after each move. Split on distinct responsibility and dependency direction, not an arbitrary line count; do not rewrite a working algorithm merely to make a file shorter. Architecture tests should protect required owners and forbidden upward dependencies without freezing every future helper-module name.

## Extending ecosystem evidence

Normalized source adapters live under `src/ocr_toolkit/evidence/ecosystems/`. Shared parser result contracts belong in `ecosystems/contracts.py`; Python, JavaScript, Go, and PHP package metadata each have one adapter module. Ansible keeps Galaxy requirements and topology/inventory analysis as separate modules under `ecosystems/ansible/`. These adapters consume text or already bounded metadata and return normalized facts: they do not own Git or filesystem reads, subprocesses, network access, framework derivation, persistence, or MCP lifecycle.

The `evidence/collectors/` package is the bounded immutable acquisition boundary. `registry.py` owns path-to-adapter registration, `sources.py` owns small cross-ecosystem CI/container source projections, `graphs.py` owns local include-graph reads, `projections.py` owns record/coverage/delta projection, and `orchestration.py` coordinates one immutable ref. Pure helper modules must not import orchestration, persistence, MCP, or higher policy/framework lifecycles. The package `__init__.py` is the intentional runtime facade; do not recreate a flat compatibility module.

Do not add a flat compatibility module when moving or adding an adapter. Parser changes need semantic-variant fixtures, explicit item/include bounds, malformed-input behavior, redaction checks, and collector/delta/MCP coverage where applicable. A new framework that interprets those normalized facts belongs in `evidence/frameworks/`, not in the source adapter.

## Extending repository policy evidence

Pure policy contracts, accepted-decision parsing, safe scope matching, and guidance applicability live under `src/ocr_toolkit/evidence/policy/`. Register providers statically; do not use entry points or repository-controlled imports. Policy code consumes bounded immutable text and normalized changed paths only. Git/tree/blob reads remain in `evidence.collectors`, compact hints remain in `evidence.project`, and transport remains in the single built-in evidence MCP.

The `evidence/store/` package is the persistence boundary. `contracts.py` owns versions, kinds, limits, and errors; `values.py` owns recursive redaction and value normalization; `core.py` owns in-memory admission, ordering, and serialization; `atomic.py` owns owner-only replacement; and `readback.py` owns hostile envelope decoding and cross-reference reconstruction. `EvidenceStore.read()` and `write()` stay thin delegates, and the package facade preserves the supported `EvidenceStore`, `EvidenceStoreError`, and `EvidenceStoreLimits` imports. Readback must not import the concrete core implementation back or bypass its admission and policy-binding controls.

Parser changes need legacy-format, duplicate-ID, malformed-field, unknown-field, scope, date, applicability, precedence, rename, unsafe-object, multibyte-boundary, and redaction fixtures. New policy values require exact kind-specific persisted schemas, snapshot/provenance correlation, and impossible-state rejection. Select applicable guidance before content reads and isolate policy truncation from unrelated evidence domains. Repository guidance is untrusted evidence and must never become executable instructions or an authorization channel; bootstrap renderers must use shared delimiter-aware Markdown helpers for repository-derived values.

## Extending bounded review context

`src/ocr_toolkit/context/` is independent from `ocr_toolkit.evidence`: contracts and normalization point downward; protected policy and fixed recognizers are pure; `adapters.py` owns exact stdio/HTTPS transport; `broker.py` composes authorization, DLP, limits, and admission; `store.py` owns separate atomic hostile-read persistence and handle binding; `mcp.py` serves only the committed local store. `providers/gitlab_discussions.py` owns forge pagination, stable repeated snapshots, provider account classification, and run-local pseudonyms. `review_runner.py` is the sole orchestration owner that combines repository evidence and context into one OCR execution.

A new context source must keep provider acquisition before OCR, use the existing `authorize_and_resolve` protocol and `issue|document` classes unless a separately reviewed common-contract change is required, and enter the same broker/store/handle/MCP/publication/cleanup lifecycle. Do not add vendor tool schemas, model-loop network, arbitrary identifiers/URLs, a second store budget charged to evidence, or a second OCR/model pass. Schema discriminators on policy, protocol, store, status, and receipt boundaries prevent cross-contract interpretation; ephemeral M5 state has no migration path.

Boundary evidence must cross the production owner with a real Git repository, child process, local TLS peer, atomic file, stdio MCP client, installed artifact, or actual OCR as appropriate. Keep unavailable outcomes uniform across denial/not-found/foreign-tenant cases, and preserve explicit non-claims for adapter truth, broader service credentials, host compromise, semantic paraphrase, and model judgment. Update the public [bounded-context contract](review-context.md), threat model, test-evidence matrix, strategy, roadmap status, and Towncrier fragments whenever this lifecycle changes.

## Extending framework evidence

Framework support lives under `src/ocr_toolkit/evidence/frameworks/`. Add an ecosystem declaration under `frameworks/providers/` and register it explicitly in `frameworks/registry.py`; keep Jinja2 first in the bounded priority order. Reuse the generic package detector where its direct-declaration and resolution semantics fit. Extend the closed schema and generic detector deliberately when a demonstrated provider needs different normalized semantics. Do not add entry-point discovery, compatibility shims, repository reads, filesystem access, subprocesses, network calls, mutation, or another MCP lifecycle to this package. Git/tree/manifest collection, storage, and serving remain core-owned boundaries.

Every provider change needs synthetic tests for direct activation, lock-only non-activation, component ownership, malformed and bounded source degradation, fact/configuration limits, schema reload, base/head deltas, and the existing MCP projection as applicable. Template engines also need explicit OCR include/rule fixtures because evidence collection does not alter OCR file selection. Update the strategy and changelog when the supported public behavior changes.

Provider results are admitted atomically: facts, coverage observations, and notices must all satisfy their package limits and immutable contracts before any of them reach shared registry output. Use `.` for a declaration manifest at the repository root; never overload a valid path such as `repository` as a root sentinel. Keep identifier/path bounds separate from longer manifest-derived scalar bounds, and validate plugin records only after the store applies its persistence redaction and total-value budget.

## Boundary-focused test checklist

Before closing a parser, repository reader, persisted schema, network helper, provider mutation, subprocess, or report-rendering change, apply the canonical [trust-boundary invariants](engineering/project_principles.md#trust-boundary-invariants) and add the applicable tests:

- exercise byte limits with multibyte input and prove reading or writing stops at the boundary instead of checking only after full capture;
- reload persisted artifacts as hostile input and verify schema, size, redaction, control-character, and cross-reference invariants again;
- vary valid parser syntax, including key order, indentation, scalar versus mapping forms, optional fields, markers, URLs, digests, and Git status letters;
- clear Git process, global/system, repository, object-store, and replacement-ref controls in subprocess tests, then verify immutable refs remain bound to the validated work tree;
- parse Git path-bearing output with NUL-delimited records and transfer raw file-descriptor ownership exactly once;
- run installed wheel and sdist entrypoints with a restricted environment and a repository-local shadow package; and
- assert mandatory fields for skipped, clean, warning, error, and finding summaries through one shared outcome matrix.

Performance evidence must separate cold-start validation from steady-state requests. Profile realistic bounded stores and report wall time plus dominant cumulative functions; optimize the measured bottleneck.
