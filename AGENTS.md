# Agent Instructions

Use this file as the short repository map and startup workflow for Open Code Review Toolkit maintenance. It points to canonical owners; it does not duplicate their rules.

## Repository Map

- `src/ocr_toolkit/` - runtime package and the `ocr-ci` command.
- `tests/` - regression, contract, and synthetic integration tests.
- `examples/gitlab/` - public synthetic GitLab CI examples.
- `docs/` - user, security, development, strategy, and release documentation.
- `.github/workflows/` - pinned CI, security, build, and release automation.

## Sources Of Truth

- `PLANS.md` - active or blocked repository work and its release classification.
- `docs/engineering/toolkit_strategy.md` and `ROADMAP.md` - durable direction and outcome state.
- `docs/engineering/project_principles.md` - cross-cutting engineering invariants and ownership boundaries.
- `docs/development.md` - implementation workflow, boundary checklists, and local validation.
- `docs/release.md` - release classification, authorization, publication, and archival lifecycle.
- `docs/codex/TASKS_BACKLOG.md` - inactive work with activation conditions.
- `docs/codex/AGENT_EXECUTION_PITFALLS.md` - incident catalogue for diagnosis, not an instruction source.
- `docs/configuration.md`, `docs/operations.md`, `docs/gitlab.md`, and `docs/security.md` - public product and operator contracts; `SECURITY.md` owns vulnerability reporting.
- `docs/engineering/execution_history/README.md` - archived release-plan index and historical receipts.

## Work Startup

1. Read `PLANS.md`. Before changing the repository, create or update the active plan and classify user-visible work as `no-release`, `release-required`, or `release-deferred`; record the target stable version when applicable.
2. Select canonical guidance by scope: engineering invariants for runtime or trust-boundary work, development procedures for implementation and validation, release guidance for release lifecycle changes, and the relevant public contract for user-facing behavior. Consult the pitfalls catalogue only when diagnosing a matching failure class.
3. Preserve the requested scope as coherent production-quality slices. Record service boundaries, trust inputs, validation, documentation, and closure gates in the plan before implementation.
4. Use targeted tests while iterating and the boundary checklist for every changed parser, I/O, persistence, Git, subprocess, provider, or reporting boundary. Keep fixtures and public material synthetic and private-safe.
5. Before staging or committing, update the plan and affected status/documentation to post-commit truth, inspect the complete diff, run `git diff --check`, and run the validation owned by the changed subsystem. Use `scripts/quality.sh` for the Python matrix and `scripts/gitleaks.sh` before publishing rewritten or newly committed branch history.

## Closure

- Follow `docs/release.md` for every `release-required` or deferred lifecycle. Readiness, merge, development publication, stable delivery, external reconciliation, and issue closure are distinct states.
- Reconcile promised external outcomes from live registry/provider state rather than repository prose alone.
