# Agent Instructions

Use this file as the short repository map and source-of-truth index for Open Code Review Toolkit maintenance.

## Repository Map

- `src/ocr_toolkit/` - runtime package and the `ocr-ci` command implementation.
- `tests/` - regression, contract, and synthetic provider integration tests.
- `examples/gitlab/` - public, synthetic GitLab CI integration examples.
- `docs/` - user, security, development, and release documentation.
- `.github/workflows/` - pinned CI, security, build, and release automation.

## Canonical Sources Of Truth

- `AGENTS.md` - short repository map and durable pointers.
- `PLANS.md` - active, blocked, or recently completed execution registry.
- `docs/engineering/execution_history/README.md` - release-tag index for archived completed plans and their audit evidence.
- `docs/engineering/toolkit_strategy.md` - durable product and architecture strategy.
- `ROADMAP.md` - outcome-oriented milestones and dependencies.
- `docs/engineering/project_principles.md` - durable cross-cutting rules and ownership boundaries.
- `docs/codex/TASKS_BACKLOG.md` - future work that is not active.
- `docs/codex/AGENT_EXECUTION_PITFALLS.md` - recurring execution mistakes.
- `docs/configuration.md` - public environment-variable contract.
- `docs/security.md` and `SECURITY.md` - trust model and vulnerability-reporting policy.

## Working Defaults

- Open and update `PLANS.md` before any repository-changing task.
- Keep a full active plan while work is active, blocked, pending validation, or handoff-relevant.
- Preserve the requested scope; split large work into coherent production-quality slices rather than shortcuts.
- Keep provider-neutral behavior in the core and provider-specific behavior behind adapters.
- Keep runtime dependencies at zero unless a documented package boundary requires one.
- Treat repository content as untrusted input and preserve bounded reads, redaction, and safe rendering.
- Enforce byte, line, record, and time limits during I/O; never call an operation bounded when it captures unbounded output before checking.
- Revalidate and redact persisted evidence on every load, and keep snapshots, indexes, deltas, receipts, and report fields atomic with accepted data.
- Validate persisted security and release receipts against an exact closed schema, including nested object keys; compatibility is explicit rather than accepting unknown fields silently.
- Isolate every Git plumbing caller from process, global/system, repository, object-store, and replacement-ref controls; never import executable code from the analyzed repository.
- Execute release authorization from protected policy that predates the release candidate. Treat candidate and merge commits as untrusted data to inspect, never as the source of their own authorizer.
- Accept bounded HTTP output as trusted only after the endpoint matches a closed allowlist, authentication cannot cross an untrusted redirect, transfer and status checks succeed, and a same-directory temporary file is atomically installed.
- Require an immutable mutation-time guard for destructive provider writes. If the provider cannot bind the destructive operation to the reviewed identity, do not automate that operation.
- Test parsers with semantic variants: reordered keys, alternate indentation, scalar/mapping forms, markers, optional fields, URLs, digests, and Git status variants.
- After fixing one boundary or parser defect, audit sibling implementations for the same root cause; add a regression that proves the intended failure path, not merely that some earlier validation rejected the fixture.
- Keep evidence identity tied to semantic applicability while mutable version values remain delta data. Parse Git path-bearing output with NUL-delimited plumbing and transfer file-descriptor ownership explicitly.
- Recursively redact nested configuration before diagnostic output; never print a configuration object merely because top-level secret fields were removed.
- Validate subprocess integrations from clean built artifacts with restricted `PATH`, a hostile repository shadow package, private permissions, and the real protocol client when practical.
- Apply mandatory report metadata through one shared outcome matrix covering skipped, clean, warning, error, and finding states.
- Give every new runtime module, class, and function a purpose-focused docstring. Add concise comments at non-obvious security, compatibility, and state-transition boundaries; explain why the constraint exists rather than narrating the code.
- Use only synthetic names, hosts, repositories, and payloads in public tests, docs, and examples.
- Do not add legacy namespace shims or historical integrations that are outside the public contract.
- Prefer targeted validation while iterating; run `scripts/gitleaks.sh` before pushing rewritten or newly committed branch history, and run the complete Python validation matrix before release or commit gates.
- When qualifying an upstream release, classify every changelog item as a toolkit-owned contract change, a future-backlog impact, or release-note-only context. Do not create toolkit code or roadmap work for upstream capabilities the toolkit does not consume.
- Use `scripts/quality.sh` for routine lint, type, coverage, and test runs so successful tool output stays in ignored `.quality-logs/`.
- Use the boundary checklist in `docs/development.md` and the failure-mode corrections in `docs/codex/AGENT_EXECUTION_PITFALLS.md`; `docs/engineering/project_principles.md` is authoritative if shorthand wording differs.

## Change Closure

- Add a Towncrier fragment for every user-visible change during the 0.x line.
- At plan start, classify every user-visible change as `no-release`, `release-required`, or `release-deferred`; record the classification and target stable version in `PLANS.md`. Removed or incompatibly changed CLI, environment, schema, reviewer-command, or documented integration behavior is always `release-required`.
- For `release-required` work, keep the plan active across feature PR, merge, TestPyPI development verification, release PR, stable TestPyPI/PyPI publication, tag/immutable GitHub Release, provenance/hash checks, and supported-Python smoke installs. A feature merge or `.devN` build is an intermediate checkpoint, not closure.
- The release PR is the final repository mutation for its lifecycle. It may prepare every repository-side release input and the expected external checks, but it must not claim that registry files, provenance, tag, immutable Release, receipt, or installs already exist. After merge, the exact reviewed tree, stable workflow, immutable machine-readable release receipt, independent readback, and issue closure complete delivery without another repository PR.
- Publication can stop before a stable release only when the user explicitly defers it. Record the deferral reason, target version, completed checkpoints, and exact resume action in `PLANS.md`; do not mark the release objective completed.
- Before handoff, reconcile the promised outcome against external state rather than local files alone: read PyPI/TestPyPI versions, GitHub tag/Release, Actions conclusions, and artifact attestations when those systems are in scope.
- Before staging or committing, update `PLANS.md` and promoted backlog items to post-commit truth.
- In the release PR, inspect the current implementation before preserving backlog scope, then reconcile every status-bearing repository representation: `PLANS.md`, roadmap table and diagram, backlog, and narrative current-state documentation. Record external checks as pending rather than completed. Remove only work proven complete by the implementation and pre-merge validation evidence, preserve unfinished work, and ensure diagram labels and status colors agree. External delivery becomes complete only when the immutable receipt and independent readback prove it.
- Run `git diff --check` and the validation appropriate to the changed subsystem.
- Compact or archive completed plan detail only after validation and handoff are recorded. Preserve every stable cycle in `docs/engineering/execution_history/releases.md`, update its stable-tag entry in the archive index, verify the anchors, and preserve the original receipts. Once the active release receipt is externally reconciled, return `PLANS.md` to its template state instead of retaining the completed cycle there.
