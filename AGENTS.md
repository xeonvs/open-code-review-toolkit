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
- Give every new runtime module, class, and function a purpose-focused docstring. Add concise comments at non-obvious security, compatibility, and state-transition boundaries; explain why the constraint exists rather than narrating the code.
- Use only synthetic names, hosts, repositories, and payloads in public tests, docs, and examples.
- Do not add legacy namespace shims or historical integrations that are outside the public contract.
- Prefer targeted validation while iterating; run the complete validation matrix before release or commit gates.
- When qualifying an upstream release, classify every changelog item as a toolkit-owned contract change, a future-backlog impact, or release-note-only context. Do not create toolkit code or roadmap work for upstream capabilities the toolkit does not consume.
- Use `scripts/quality.sh` for routine lint, type, coverage, and test runs so successful tool output stays in ignored `.quality-logs/`.

## Change Closure

- Add a Towncrier fragment for every user-visible change during the 0.x line.
- At plan start, classify every user-visible change as `no-release`, `release-required`, or `release-deferred`; record the classification and target stable version in `PLANS.md`. Removed or incompatibly changed CLI, environment, schema, reviewer-command, or documented integration behavior is always `release-required`.
- For `release-required` work, keep the plan active across feature PR, merge, TestPyPI development verification, release PR, stable TestPyPI/PyPI publication, tag/immutable GitHub Release, provenance/hash checks, and supported-Python smoke installs. A feature merge or `.devN` build is an intermediate checkpoint, not closure.
- Publication can stop before a stable release only when the user explicitly defers it. Record the deferral reason, target version, completed checkpoints, and exact resume action in `PLANS.md`; do not mark the release objective completed.
- Before handoff, reconcile the promised outcome against external state rather than local files alone: read PyPI/TestPyPI versions, GitHub tag/Release, Actions conclusions, and artifact attestations when those systems are in scope.
- Before staging or committing, update `PLANS.md` and promoted backlog items to post-commit truth.
- Run `git diff --check` and the validation appropriate to the changed subsystem.
- Compact or archive completed plan detail only after validation and handoff are recorded.
